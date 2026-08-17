# -*- coding: utf-8 -*-
"""SQLite FTS5 tabanlı arşiv indeksi."""

import os
import re
import sqlite3
import time

try:
    # Modern isim pymupdf; eski kurulumlarda yalnızca fitz bulunur
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz
    PYMUPDF_AVAILABLE = True
    try:
        # MuPDF'in bozuk PDF'ler için stderr'e bastığı uyarıları sustur
        fitz.TOOLS.mupdf_display_errors(False)
    except Exception:
        pass
except ImportError:
    PYMUPDF_AVAILABLE = False

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS files(
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    relpath TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    subcategory TEXT NOT NULL DEFAULT '',
    ext TEXT NOT NULL DEFAULT '',
    size INTEGER NOT NULL DEFAULT 0,
    mtime REAL NOT NULL DEFAULT 0,
    pages INTEGER NOT NULL DEFAULT 0,
    chars INTEGER NOT NULL DEFAULT 0,
    indexed_at REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_files_cat ON files(category, subcategory);
CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
    name, relpath, content,
    tokenize='unicode61 remove_diacritics 2'
);
"""


def connect(index_path):
    os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)
    con = sqlite3.connect(index_path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def exists(index_path):
    return os.path.isfile(index_path) and os.path.getsize(index_path) > 0


def split_category(relpath):
    """Göreli yoldan (kategori, alt kategori) çıkarır."""
    parts = relpath.split(os.sep)
    category = parts[0] if len(parts) > 1 else ""
    subcategory = parts[1] if len(parts) > 2 else ""
    return category, subcategory


def extract_text(path, max_chars, max_pages):
    """Dosyadan düz metin çıkarır. (metin, sayfa_sayısı) döner."""
    if path.lower().endswith(".pdf"):
        if not PYMUPDF_AVAILABLE:
            return "", 0
        try:
            with fitz.open(path) as doc:
                pages = doc.page_count
                chunks = []
                total = 0
                for i in range(min(max_pages, pages)):
                    t = doc[i].get_text("text")
                    chunks.append(t)
                    total += len(t)
                    if total >= max_chars:
                        break
                text = re.sub(r"\s+", " ", "".join(chunks)[:max_chars]).strip()
                return text, pages
        except Exception:
            return "", 0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return re.sub(r"\s+", " ", f.read(max_chars)).strip(), 0
    except OSError:
        return "", 0


def scan_files(archive_dir, extensions):
    """Arşivdeki uygun dosyaların (tam_yol, göreli_yol) listesini döner."""
    exts = tuple(e.lower() for e in extensions)
    found = []
    for root, dirs, files in os.walk(archive_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name.startswith("."):
                continue
            if not name.lower().endswith(exts):
                continue
            full = os.path.join(root, name)
            found.append((full, os.path.relpath(full, archive_dir)))
    found.sort(key=lambda x: x[1])
    return found


def build(cfg, progress=None, rebuild=False):
    """İndeksi kurar/günceller. İstatistik sözlüğü döner."""
    archive_dir = cfg["archive_dir"]
    con = connect(cfg["index_path"])
    if rebuild:
        con.executescript("DELETE FROM files; DELETE FROM files_fts;")
        con.commit()

    known = {r["path"]: (r["id"], r["mtime"]) for r in con.execute("SELECT id, path, mtime FROM files")}
    disk = scan_files(archive_dir, cfg["extensions"])
    disk_paths = {p for p, _ in disk}

    stats = {"total": len(disk), "added": 0, "updated": 0, "removed": 0, "skipped": 0, "no_text": 0}

    # Diskten silinmiş kayıtları temizle
    for path, (fid, _) in known.items():
        if path not in disk_paths:
            con.execute("DELETE FROM files WHERE id = ?", (fid,))
            con.execute("DELETE FROM files_fts WHERE rowid = ?", (fid,))
            stats["removed"] += 1

    max_chars = cfg["index_max_chars"]
    max_pages = cfg["index_max_pages"]

    for i, (path, relpath) in enumerate(disk, 1):
        try:
            st = os.stat(path)
        except OSError:
            continue
        prev = known.get(path)
        if prev and abs(prev[1] - st.st_mtime) < 1e-6:
            stats["skipped"] += 1
            if progress:
                progress(i, len(disk), relpath, "atlandı")
            continue

        if progress:
            progress(i, len(disk), relpath, "okunuyor")

        text, pages = extract_text(path, max_chars, max_pages)
        if not text:
            stats["no_text"] += 1
        name = os.path.basename(path)
        category, subcategory = split_category(relpath)
        ext = os.path.splitext(name)[1].lower()
        # FTS için yoldaki ayraçları boşluğa çevir ki kelimeler ayrışsın
        searchable_rel = re.sub(r"[/_\-\.]+", " ", relpath)
        searchable_name = re.sub(r"[_\-\.]+", " ", name)
        row = (relpath, name, category, subcategory, ext, st.st_size,
               st.st_mtime, pages, len(text), time.time())

        if prev:
            fid = prev[0]
            con.execute(
                "UPDATE files SET relpath=?, name=?, category=?, subcategory=?, ext=?, "
                "size=?, mtime=?, pages=?, chars=?, indexed_at=? WHERE id=?",
                row + (fid,))
            con.execute("DELETE FROM files_fts WHERE rowid=?", (fid,))
            stats["updated"] += 1
        else:
            cur = con.execute(
                "INSERT INTO files(path, relpath, name, category, subcategory, ext, "
                "size, mtime, pages, chars, indexed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (path,) + row)
            fid = cur.lastrowid
            stats["added"] += 1

        con.execute("INSERT INTO files_fts(rowid, name, relpath, content) VALUES (?,?,?,?)",
                    (fid, searchable_name, searchable_rel, text))
        if i % 50 == 0:
            con.commit()

    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('archive_dir', ?)", (archive_dir,))
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('built_at', ?)", (str(time.time()),))
    con.commit()
    con.close()
    return stats


def info(index_path):
    """İndeks hakkında özet bilgi döner."""
    if not exists(index_path):
        return None
    con = connect(index_path)
    try:
        n = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        with_text = con.execute("SELECT COUNT(*) FROM files WHERE chars > 0").fetchone()[0]
        built = con.execute("SELECT value FROM meta WHERE key='built_at'").fetchone()
        archive = con.execute("SELECT value FROM meta WHERE key='archive_dir'").fetchone()
        return {
            "files": n,
            "with_text": with_text,
            "built_at": float(built[0]) if built else 0.0,
            "archive_dir": archive[0] if archive else "",
            "size": os.path.getsize(index_path),
        }
    finally:
        con.close()


def categories(index_path):
    """(kategori, alt_kategori, adet) üçlülerini döner."""
    if not exists(index_path):
        return []
    con = connect(index_path)
    try:
        return [(r[0], r[1], r[2]) for r in con.execute(
            "SELECT category, subcategory, COUNT(*) FROM files "
            "GROUP BY category, subcategory ORDER BY category, subcategory")]
    finally:
        con.close()
