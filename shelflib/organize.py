# -*- coding: utf-8 -*-
"""Arşiv düzenleyici: kural tabanlı puanlama + AI kategorilendirme ve yeniden adlandırma.

organizer.py, ai_organizer.py, ai_librarian.py ve ai_librarian_with_config.py
script'lerinin birleştirilmiş halidir.
"""

import hashlib
import os
import re
import shutil
import time
from dataclasses import dataclass, field

from . import index as idx
from .rules import UNCATEGORIZED

# Metni okunabilen türler; diğerleri yalnızca dosya adından kategorilendirilir
TEXT_EXTS = (".pdf", ".txt", ".md")
DEFAULT_SOURCE_EXTS = (".pdf", ".txt", ".md", ".epub", ".docx", ".pptx", ".doc", ".ppt")

CATEGORY_PROMPT = """You are an expert cybersecurity librarian. Analyze the text below.
Choose the SINGLE BEST category code from this list. Respond with ONLY the code.

Categories:
{catalog}

Filename: {name}
Document structure (table of contents if available, otherwise opening text):
---
{text}
---
The best category code is:"""

RENAME_PROMPT = """You are cataloguing a cybersecurity archive. Write a filename that
tells a reader exactly what this document contains, without opening it.

The name must answer: what technology/target, and what aspect of it?
Weak:   VMware_Escape.pdf
Strong: BULUT_VMware_Workstation_USB_Controller_VM_Escape_Exploit.pdf
Weak:   Networking_Zine.pdf
Strong: AG_TEMELLERI_TCP_IP_Packet_Flow_Illustrated_Guide.pdf

Rules:
- Start with the category code '{category}', then an underscore.
- English, Title_Case_With_Underscores, no spaces, no punctuation except _ and .
- Be specific: name the tool, protocol, CVE, technique or exam code when the
  document is about one. Prefer 6-10 meaningful words over a short vague name.
- Do not invent facts. If the document is a broad reference, say so
  (e.g. Complete_Reference, Field_Manual, Cheatsheet).
- 40-100 characters, then the original extension.
- No dates, no edition numbers, no publisher names.

Respond with the filename on a single line and nothing else.

Current filename: {name}
Document text:
---
{text}
---"""


@dataclass
class Action:
    source: str
    name: str
    category: str = UNCATEGORIZED
    score: int = 0
    decided_by: str = "kural"          # kural | ai | kategorisiz
    dest: str = ""
    new_name: str = ""
    status: str = "planlandı"          # planlandı | kopyalandı | taşındı | kopya | hata | atlandı
    note: str = ""
    _text: str = field(default="", repr=False)


def sanitize_filename(name):
    """Dosya sistemi için güvenli bir ad üretir."""
    if not isinstance(name, str) or not name.strip():
        return "Isimsiz"
    name = os.path.basename(name.strip().strip('"').strip("`"))
    name = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "", name)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name).strip("._ ")
    return name or "Isimsiz"


def file_hash(path, block_size=1 << 20):
    """Dosyanın SHA-256 özetini döner; okunamazsa None."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(block_size), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def list_source_files(source_dir, extensions=DEFAULT_SOURCE_EXTS, recursive=False):
    """Kaynak dizindeki işlenecek dosyaları listeler."""
    exts = tuple(e.lower() for e in extensions)
    found = []
    if recursive:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in sorted(files):
                if not name.startswith(".") and name.lower().endswith(exts):
                    found.append(os.path.join(root, name))
    else:
        for name in sorted(os.listdir(source_dir)):
            full = os.path.join(source_dir, name)
            if os.path.isfile(full) and not name.startswith(".") and name.lower().endswith(exts):
                found.append(full)
    return found


# ---------- içindekiler çıkarma ----------

# Kitapların içindekiler sayfasını yakalayan başlıklar (İngilizce + Türkçe)
_TOC_BASLIK = re.compile(
    r"^\s*(table\s+of\s+contents|contents|içindekiler|icindekiler|"
    r"table\s+des\s+matières|inhalt)\s*$", re.I | re.M)

# "Bölüm adı .......... 42" biçimindeki içindekiler satırları
_TOC_SATIR = re.compile(r"^.{3,90}?[\.\s]{4,}\d{1,4}\s*$", re.M)


def _toc_gomulu(path, max_headings=120):
    """PDF'in gömülü yer imi ağacından içindekiler üretir. Yoksa '' döner."""
    if not idx.PYMUPDF_AVAILABLE:
        return ""
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            return ""
    try:
        with pymupdf.open(path) as doc:
            toc = doc.get_toc()
    except Exception:
        return ""
    if not toc:
        return ""
    satirlar = []
    for seviye, baslik, _sayfa in toc[:max_headings]:
        baslik = " ".join(str(baslik).split())
        if baslik:
            satirlar.append("  " * (max(1, int(seviye)) - 1) + baslik)
    return "\n".join(satirlar)


def _toc_sayfadan(path, tara_sayfa=25):
    """Baştaki sayfalarda 'Contents' başlıklı sayfayı arar. Yoksa '' döner."""
    if not idx.PYMUPDF_AVAILABLE:
        return ""
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            return ""
    try:
        with pymupdf.open(path) as doc:
            parcalar = []
            for no in range(min(tara_sayfa, len(doc))):
                try:
                    metin = doc[no].get_text()
                except Exception:
                    continue
                if not metin:
                    continue
                # Ya "Contents" başlığı ya da nokta dolgulu satır yoğunluğu
                if _TOC_BASLIK.search(metin) or len(_TOC_SATIR.findall(metin)) >= 5:
                    parcalar.append(metin)
                elif parcalar:
                    break   # içindekiler bitti
                if len(parcalar) >= 6:
                    break
    except Exception:
        return ""
    return "\n".join(parcalar).strip()


def icindekiler(path, max_chars=3000):
    """Sınıflandırma için dökümanın en bilgilendirici özetini döner.

    Sırasıyla denenir:
      1. PDF'in gömülü yer imleri (en temiz — arşivin ~%42'sinde var)
      2. Baştaki sayfalarda 'Contents' başlıklı içindekiler sayfası
      3. '' (çağıran ilk sayfalara düşer)

    Tüm PDF'i taramak yerine yalnızca yapıya bakmak hem çok daha hızlı hem de
    AI'a gönderilen bağlamı daraltıp isabeti artırır.
    """
    if not path.lower().endswith(".pdf"):
        return ""
    metin = _toc_gomulu(path)
    if not metin:
        metin = _toc_sayfadan(path)
    return metin[:max_chars].strip()


def _ai_category(provider, rules, name, text, errors=None):
    """AI'dan kategori kodu ister. (kod_veya_None) döner, hatayı errors'a yazar."""
    from . import ai as ai_mod
    prompt = CATEGORY_PROMPT.format(
        catalog=rules.prompt_catalog(), name=name, text=text[:3000])
    try:
        raw = ai_mod.complete(provider, prompt)
    except Exception as e:
        if errors is not None:
            errors.append(ai_mod.explain(e, provider))
        return None
    code = re.sub(r"[^A-Z_0-9]", "", raw.strip().upper())
    if code in rules.dir_structure:
        return code
    if errors is not None:
        errors.append(f"AI geçersiz kategori döndürdü: {code[:30] or '(boş)'}")
    return None


# Dosya adına benzeyen satır: uzantıyla biten, boşluksuz, makul uzunlukta
_AD_ADAYI = re.compile(r"[A-Za-z0-9][\w.+&()\-]{7,}\.[A-Za-z0-9]{2,5}$")


def _ad_ayikla(raw):
    """AI yanıtından dosya adını çıkarır.

    Modeller adı bazen açıklama satırlarının arasına, bazen ters tırnak ya da
    markdown içine koyar. İlk satırı körü körüne almak yerine dosya adına
    benzeyen satırlar aranır ve en bilgilendirici olan seçilir.
    """
    if not raw:
        return None
    adaylar = []
    for satir in raw.splitlines():
        satir = satir.strip().strip("`").strip("*").strip().strip('"').strip("'")
        satir = re.sub(r"^(filename|file name|answer|output)\s*[:\-]\s*", "",
                       satir, flags=re.I).strip()
        if not satir or " " in satir.strip() and not _AD_ADAYI.search(satir):
            # boşluklu satır yalnızca ad gibi bitiyorsa değerlendirilir
            parcalar = satir.split()
            satir = parcalar[-1] if parcalar else ""
        if _AD_ADAYI.search(satir):
            adaylar.append(satir)
    if not adaylar:
        # hiç uzantılı aday yok: tek satırlık düz yanıt olabilir
        ilk = raw.strip().splitlines()[0].strip().strip("`") if raw.strip() else ""
        temiz = sanitize_filename(ilk)
        return temiz if len(temiz) >= 8 else None
    # en uzun aday genelde en açıklayıcı olanıdır
    en_iyi = max(adaylar, key=len)
    temiz = sanitize_filename(en_iyi)
    return temiz if len(temiz) >= 8 else None


def _ai_rename(provider, category, name, text, errors=None):
    """AI'dan yeni dosya adı ister; alınamazsa None döner."""
    from . import ai as ai_mod
    prompt = RENAME_PROMPT.format(category=category, name=name, text=text[:2500])
    try:
        raw = ai_mod.complete(provider, prompt)
    except Exception as e:
        if errors is not None:
            errors.append(ai_mod.explain(e, provider))
        return None
    candidate = _ad_ayikla(raw)
    if not candidate:
        return None
    original_ext = os.path.splitext(name)[1]
    if not os.path.splitext(candidate)[1]:
        candidate += original_ext
    return candidate


def plan(source_files, rules, target_dir, provider=None, threshold=12,
         rename=False, max_pages=10, max_chars=8000, progress=None,
         ai_only=False):
    """Her dosya için nereye gideceğine karar verir. (actions, ai_hataları) döner.

    ai_only=True ise anahtar kelime puanlaması karar için kullanılmaz; her dosya
    AI'a sorulur. Kategori listesi ve klasör eşlemesi yine kurallardan gelir —
    devre dışı kalan yalnızca puanlama. AI karar veremezse dosya Kategorisiz'e
    düşer, kural puanına geri dönülmez.
    """
    actions = []
    ai_errors = []
    total = len(source_files)
    for i, path in enumerate(source_files, 1):
        name = os.path.basename(path)
        if progress:
            progress(i, total, name, "inceleniyor")

        text = ""
        ai_ozet = ""      # bu dosya için AI'a giden özet; her turda sıfırlanır
        if name.lower().endswith(TEXT_EXTS):
            text, _ = idx.extract_text(path, max_chars, max_pages)

        category, score, _ = rules.score(name, text)
        decided_by = "kural"

        # Kural puanı eşiğin altındaysa karar AI'a, o da yoksa Kategorisiz'e devredilir
        if ai_only or score < threshold:
            ai_code = None
            if provider is not None:
                if progress:
                    progress(i, total, name, "içindekiler okunuyor")
                # AI'a tüm metin yerine dökümanın iskeleti gönderilir: içindekiler
                # konuyu ilk sayfalardan çok daha yoğun anlatır ve bağlamı daraltır.
                ozet = icindekiler(path)
                if ozet:
                    ozet = "TABLE OF CONTENTS:\n" + ozet
                else:
                    ozet = text[:3000]
                if progress:
                    progress(i, total, name, "AI'a soruluyor")
                ai_ozet = ozet
                ai_code = _ai_category(provider, rules, name, ozet or name, ai_errors)
            if ai_code:
                category, decided_by = ai_code, "ai"
            else:
                category, decided_by = UNCATEGORIZED, "kategorisiz"

        new_name = name
        if rename and provider is not None and text:
            if progress:
                progress(i, total, name, "AI ad öneriyor")
            kaynak_metin = ai_ozet or icindekiler(path) or text
            suggested = _ai_rename(provider, category, name, kaynak_metin, ai_errors)
            if suggested:
                new_name = suggested

        dest = os.path.join(target_dir, rules.folder_for(category), new_name)
        actions.append(Action(source=path, name=name, category=category, score=score,
                              decided_by=decided_by, dest=dest, new_name=new_name,
                              _text=text))
    return actions, ai_errors


def apply(actions, move=False, dry_run=False, skip_duplicates=True, progress=None):
    """Planı uygular. İstatistik sözlüğü döner."""
    stats = {"kopyalandı": 0, "taşındı": 0, "kopya": 0, "hata": 0, "atlandı": 0}
    total = len(actions)
    for i, action in enumerate(actions, 1):
        if progress:
            progress(i, total, action.name, "uygulanıyor")

        dest = action.dest
        folder = os.path.dirname(dest)

        # Hedefte aynı adla dosya varsa: içerik aynıysa kopya, değilse yeni ad
        if os.path.exists(dest):
            if skip_duplicates and file_hash(dest) == file_hash(action.source):
                action.status = "kopya"
                action.note = "hedefte birebir aynısı zaten var"
                stats["kopya"] += 1
                continue
            base, ext = os.path.splitext(dest)
            dest = f"{base}_{int(time.time())}{ext}"
            action.dest = dest
            action.note = "ad çakışması, sonuna zaman damgası eklendi"

        if dry_run:
            action.status = "planlandı"
            continue

        try:
            os.makedirs(folder, exist_ok=True)
            if move:
                shutil.move(action.source, dest)
                action.status = "taşındı"
                stats["taşındı"] += 1
            else:
                shutil.copy2(action.source, dest)
                action.status = "kopyalandı"
                stats["kopyalandı"] += 1
        except Exception as e:
            action.status = "hata"
            action.note = f"{type(e).__name__}: {e}"
            stats["hata"] += 1
    return stats


def summarize(actions):
    """Kategori bazında (kategori, adet, karar_dağılımı) özetini döner."""
    by_category = {}
    for a in actions:
        entry = by_category.setdefault(a.category, {"count": 0, "kural": 0, "ai": 0, "kategorisiz": 0})
        entry["count"] += 1
        entry[a.decided_by] = entry.get(a.decided_by, 0) + 1
    return dict(sorted(by_category.items(), key=lambda kv: -kv[1]["count"]))
