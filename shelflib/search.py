# -*- coding: utf-8 -*-
"""Arama katmanı: indeks (FTS5) ve indekssiz (canlı tarama) arka uçları."""

import os
import re
from dataclasses import dataclass, field

from . import index as idx


@dataclass
class Result:
    path: str
    relpath: str
    name: str
    category: str = ""
    subcategory: str = ""
    size: int = 0
    pages: int = 0
    snippet: str = ""
    rank: float = 0.0
    matched_content: bool = False
    ai_score: int = 0
    ai_reason: str = ""
    _preview: str = field(default="", repr=False)


def tokenize(query):
    """Sorguyu arama terimlerine ayırır (tırnaklı ifadeleri korur)."""
    terms = re.findall(r'"([^"]+)"|(\S+)', query)
    return [(a or b).strip() for a, b in terms if (a or b).strip()]


def build_match(query, columns=None, operator="AND"):
    """Kullanıcı sorgusunu güvenli bir FTS5 MATCH ifadesine çevirir."""
    parts = []
    for term in tokenize(query):
        cleaned = term.replace('"', " ").strip()
        if not cleaned or not re.search(r"\w", cleaned):
            continue
        # Tırnak içine alınca özel karakterler (-, :, *) ifade değil metin sayılır
        parts.append(f'"{cleaned}"*')
    if not parts:
        return ""
    expr = f" {operator} ".join(parts)
    if columns:
        expr = "{" + " ".join(columns) + "} : (" + expr + ")"
    return expr


def search_index(cfg, query, content=False, category=None, subcategory=None,
                 limit=200, operator="AND"):
    """İndeks üzerinden arama yapar."""
    columns = None if content else ["name", "relpath"]
    match = build_match(query, columns, operator)
    con = idx.connect(cfg["index_path"])
    try:
        where = []
        params = []
        if match:
            where.append("files_fts MATCH ?")
            params.append(match)
        if category:
            where.append("f.category = ?")
            params.append(category)
        if subcategory:
            where.append("f.subcategory = ?")
            params.append(subcategory)

        if match:
            sql = (
                "SELECT f.path, f.relpath, f.name, f.category, f.subcategory, f.size, f.pages, "
                "snippet(files_fts, 2, '\x01', '\x02', ' … ', 14) AS snip, "
                "bm25(files_fts, 12.0, 6.0, 1.0) AS rank "
                "FROM files_fts JOIN files f ON f.id = files_fts.rowid "
                "WHERE " + " AND ".join(where) + " ORDER BY rank LIMIT ?"
            )
        else:
            # Sorgu yoksa: kategoriye göre listele
            sql = (
                "SELECT f.path, f.relpath, f.name, f.category, f.subcategory, f.size, f.pages, "
                "'' AS snip, 0.0 AS rank FROM files f"
                + (" WHERE " + " AND ".join(where) if where else "")
                + " ORDER BY f.relpath LIMIT ?"
            )
        # limit 0 = sınırsız; SQLite'ta bunun karşılığı LIMIT -1
        params.append(limit if limit else -1)
        rows = con.execute(sql, params).fetchall()
    except Exception:
        return []
    finally:
        con.close()

    results = []
    for r in rows:
        snip = r["snip"] or ""
        results.append(Result(
            path=r["path"], relpath=r["relpath"], name=r["name"],
            category=r["category"], subcategory=r["subcategory"],
            size=r["size"], pages=r["pages"],
            snippet=snip, rank=r["rank"],
            # FTS5 yalnızca gerçekten eşleşen terimleri işaretler; işaret yoksa
            # snippet sadece bağlam olarak gösterilen ilk satırlardır
            matched_content="\x01" in snip,
        ))
    return results


def search_live(cfg, query, content=False, category=None, subcategory=None, limit=200):
    """İndeks olmadan, diski tarayarak arama yapar (yavaş yol)."""
    archive = cfg["archive_dir"]
    terms = [t.lower() for t in tokenize(query)]
    results = []
    for path, relpath in idx.scan_files(archive, cfg["extensions"]):
        cat, sub = idx.split_category(relpath)
        if category and cat != category:
            continue
        if subcategory and sub != subcategory:
            continue
        hay = relpath.lower()
        path_match = all(t in hay for t in terms) if terms else True
        content_match = False
        snippet = ""
        if content and not path_match and terms:
            text, _ = idx.extract_text(path, 20000, 10)
            low = text.lower()
            if all(t in low for t in terms):
                content_match = True
                pos = low.find(terms[0])
                snippet = text[max(0, pos - 60):pos + 140]
        if path_match or content_match:
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            results.append(Result(
                path=path, relpath=relpath, name=os.path.basename(path),
                category=cat, subcategory=sub, size=size,
                snippet=snippet, matched_content=content_match,
            ))
            if limit and len(results) >= limit:
                break
    return results


def search(cfg, query, content=False, category=None, subcategory=None, limit=200):
    """Uygun arka uçla arama yapar. (sonuçlar, kullanılan_arka_uç) döner.

    Arka uç adı, tüm terimleri içeren sonuç bulunamayıp herhangi birini içerenlere
    düşüldüğünde "index-or" olur.
    """
    if not idx.exists(cfg["index_path"]):
        return search_live(cfg, query, content, category, subcategory, limit), "live"

    results = search_index(cfg, query, content, category, subcategory, limit)
    if results or len(tokenize(query)) < 2:
        return results, "index"

    # Tüm terimleri içeren yok: herhangi birini içerenlere gevşet
    loose = search_index(cfg, query, content, category, subcategory, limit, operator="OR")
    if loose:
        return loose, "index-or"
    return results, "index"


def preview_text(cfg, result, max_chars=4000):
    """Sonuç için önizleme metnini indeksten ya da dosyadan alır."""
    if result._preview:
        return result._preview
    text = ""
    if idx.exists(cfg["index_path"]):
        con = idx.connect(cfg["index_path"])
        try:
            row = con.execute(
                "SELECT content FROM files_fts WHERE rowid = "
                "(SELECT id FROM files WHERE path = ?)", (result.path,)).fetchone()
            if row:
                text = row[0] or ""
        except Exception:
            text = ""
        finally:
            con.close()
    if not text:
        text, _ = idx.extract_text(result.path, max_chars, 5)
    result._preview = text[:max_chars]
    return result._preview


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} GB"
