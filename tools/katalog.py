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

    # --- özet tablo ---
    sat.append("| Kategori | Belge | Boyut |")
    sat.append("| --- | ---: | ---: |")
    for ust, altlar in agac.items():
        adet = sum(len(v) for v in altlar.values())
        boyut = sum(b for v in altlar.values() for _, b in v)
        sat.append(f"| {baslik(ust)} | {adet} | {insanca(boyut)} |")
    sat.append(f"| **Toplam** | **{toplam_adet}** | **{insanca(toplam_boyut)}** |")
    sat.append("")

    # --- klasör iskeleti: belge adları olmadan, tek bakışta yapı ---
    sat.append("### Klasör yapısı")
    sat.append("")
    sat.append("```")
    ust_adlar = list(agac)
    for i, ust in enumerate(ust_adlar):
        son_ust = i == len(ust_adlar) - 1
        sat.append(f"{'└── ' if son_ust else '├── '}{ust}/")
        devam = "    " if son_ust else "│   "
        alt_adlar = list(agac[ust])
        for j, alt in enumerate(alt_adlar):
            son_alt = j == len(alt_adlar) - 1
            sat.append(f"{devam}{'└── ' if son_alt else '├── '}{alt}/"
                       f"  ({len(agac[ust][alt])})")
    sat.append("```")
    sat.append("")

    # --- açılır kapanır tam liste ---
    sat.append("### Belgeler")
    sat.append("")
    sat.append("Başlıklar açılıp kapanır: önce ana kategoriye, sonra alt kategoriye tıklayın.")
    sat.append("")
    for ust, altlar in agac.items():
        adet = sum(len(v) for v in altlar.values())
        boyut = sum(b for v in altlar.values() for _, b in v)
        sat.append("<details>")
        sat.append(f"<summary>📁 <b>{baslik(ust)}</b> — {adet} belge · "
                   f"{insanca(boyut)}</summary>")
        sat.append("")
        for alt, kitaplar in altlar.items():
            alt_boyut = sum(b for _, b in kitaplar)
            sat.append("<blockquote>")
            sat.append("<details>")
            sat.append(f"<summary>📂 <b>{baslik(alt)}</b> — {len(kitaplar)} belge · "
                       f"{insanca(alt_boyut)}</summary>")
            sat.append("")
            sat.append("```")
            sat.append(f"{baslik(alt)}/")
            for j, (ad, boyut2) in enumerate(kitaplar):
                uc = "└── " if j == len(kitaplar) - 1 else "├── "
                sat.append(f"{uc}{ad}  ({insanca(boyut2)})")
            sat.append("```")
            sat.append("")
            sat.append("</details>")
            sat.append("</blockquote>")
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
