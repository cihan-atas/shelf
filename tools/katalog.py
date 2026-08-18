#!/usr/bin/env python3
"""Arşivdeki kitapları tarayıp README'nin katalog bölümünü üretir.

Kullanım:
    python3 tools/katalog.py /yol/arsiv/hacking            # ekrana bas
    python3 tools/katalog.py /yol/arsiv/hacking --yaz      # README.md içine göm

README'de bölüm şu iki işaret arasına yazılır:
    <!-- KATALOG:BASLANGIC --> ... <!-- KATALOG:BITIS -->
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BASLANGIC = "<!-- KATALOG:BASLANGIC -->"
BITIS = "<!-- KATALOG:BITIS -->"
UZANTILAR = {".pdf", ".epub", ".md", ".txt"}


def insanca(boyut: int) -> str:
    birim = float(boyut)
    for ek in ("B", "KB", "MB", "GB"):
        if birim < 1024 or ek == "GB":
            return f"{birim:.0f} {ek}" if ek in ("B", "KB") else f"{birim:.1f} {ek}"
        birim /= 1024
    return f"{birim:.1f} GB"


def baslik(ad: str) -> str:
    """01_OFANSIF_GUVENLIK_(RED_TEAM) -> Ofansif Guvenlik (Red Team)"""
    ad = re.sub(r"^\d+[_-]", "", ad)
    ad = ad.replace("_", " ").strip()
    return ad


def kitap_adi(dosya: Path) -> str:
    ad = dosya.stem
    ad = re.sub(r"_\d{10,}$", "", ad)          # dönüştürücü zaman damgaları
    return ad.replace("_", " ").strip()


def topla(kok: Path):
    """{ust_kategori: {alt_kategori: [(ad, boyut), ...]}} döndürür."""
    agac: dict[str, dict[str, list[tuple[str, int]]]] = {}
    for dosya in sorted(kok.rglob("*")):
        if not dosya.is_file() or dosya.suffix.lower() not in UZANTILAR:
            continue
        bagil = dosya.relative_to(kok).parts
        ust = bagil[0] if len(bagil) > 1 else "(kök)"
        alt = bagil[1] if len(bagil) > 2 else "(doğrudan)"
        agac.setdefault(ust, {}).setdefault(alt, []).append(
            (kitap_adi(dosya), dosya.stat().st_size)
        )
    return agac


def uret(kok: Path) -> str:
    agac = topla(kok)
    toplam_adet = sum(len(v) for a in agac.values() for v in a.values())
    toplam_boyut = sum(b for a in agac.values() for v in a.values() for _, b in v)

    sat: list[str] = []
    sat.append("## Arşiv kataloğu")
    sat.append("")
    sat.append(
        f"Bu araç için referans arşiv **{toplam_adet} belge** ve "
        f"**{insanca(toplam_boyut)}** büyüklüğünde, {len(agac)} ana kategoriye ayrılmış. "
        "Belgelerin kendisi bu depoda **yer almaz** (telif); aşağıdaki liste yalnızca "
        "`shelf` ile üretilen dizin yapısını gösterir."
    )
    sat.append("")
    sat.append("| Kategori | Belge | Boyut |")
    sat.append("| --- | ---: | ---: |")
    for ust, altlar in agac.items():
        adet = sum(len(v) for v in altlar.values())
        boyut = sum(b for v in altlar.values() for _, b in v)
        sat.append(f"| {baslik(ust)} | {adet} | {insanca(boyut)} |")
    sat.append(f"| **Toplam** | **{toplam_adet}** | **{insanca(toplam_boyut)}** |")
    sat.append("")

    for ust, altlar in agac.items():
        adet = sum(len(v) for v in altlar.values())
        sat.append(f"<details>")
        sat.append(f"<summary><b>{baslik(ust)}</b> — {adet} belge</summary>")
        sat.append("")
        sat.append("```")
        sat.append(baslik(ust))
        alt_adlar = list(altlar)
        for i, alt in enumerate(alt_adlar):
            son_alt = i == len(alt_adlar) - 1
            dal = "└── " if son_alt else "├── "
            devam = "    " if son_alt else "│   "
            sat.append(f"{dal}{baslik(alt)}/")
            kitaplar = altlar[alt]
            for j, (ad, boyut) in enumerate(kitaplar):
                uc = "└── " if j == len(kitaplar) - 1 else "├── "
                sat.append(f"{devam}{uc}{ad}  ({insanca(boyut)})")
        sat.append("```")
        sat.append("")
        sat.append("</details>")
        sat.append("")
    return "\n".join(sat).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="README katalog bölümünü üretir")
    ap.add_argument("arsiv", type=Path, help="taranacak arşiv kökü")
    ap.add_argument("--yaz", action="store_true", help="README.md içine göm")
    ap.add_argument("--readme", type=Path, default=Path(__file__).resolve().parent.parent / "README.md")
    a = ap.parse_args()

    if not a.arsiv.is_dir():
        print(f"hata: dizin yok: {a.arsiv}", file=sys.stderr)
        return 1

    bolum = uret(a.arsiv)
    if not a.yaz:
        print(bolum)
        return 0

    metin = a.readme.read_text(encoding="utf-8")
    yeni = f"{BASLANGIC}\n\n{bolum}\n{BITIS}"
    if BASLANGIC in metin and BITIS in metin:
        metin = re.sub(
            re.escape(BASLANGIC) + r".*?" + re.escape(BITIS), yeni, metin, flags=re.S
        )
    else:
        metin = metin.rstrip() + "\n\n" + yeni + "\n"
    a.readme.write_text(metin, encoding="utf-8")
    print(f"yazıldı: {a.readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
