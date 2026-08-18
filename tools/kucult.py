#!/usr/bin/env python3
"""Arşivdeki PDF'leri Ghostscript ile küçültür — yalnızca kazanç varsa.

Ghostscript her dosyada kazandırmaz; görsel ağırlıklı taramalarda %80+ düşerken
zaten iyi sıkıştırılmış metin PDF'lerini iki katına çıkarabilir. Bu araç her
dosyayı dönüştürür, sonucu doğrular ve **yalnızca gerçekten küçüldüyse** kabul eder.

Orijinaller asla değiştirilmez; çıktı ayrı bir dizin ağacına yazılır.

    python3 tools/kucult.py ARSIV HEDEF                 # ne olacağını göster
    python3 tools/kucult.py ARSIV HEDEF --uygula
    python3 tools/kucult.py ARSIV HEDEF --uygula -j 8 --kalite ebook
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

KALITELER = ("screen", "ebook", "printer", "prepress")
# kabul eşiği: en az bu kadar küçülmeyen dosya için orijinal korunur
ASGARI_KAZANC = 0.05


def insanca(n: float) -> str:
    for ek in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024 or ek == "GB":
            return f"{n:.1f} {ek}"
        n /= 1024
    return f"{n:.1f} GB"


@dataclass
class Sonuc:
    kaynak: Path
    once: int
    sonra: int
    kabul: bool
    not_: str = ""

    @property
    def kazanc(self) -> int:
        return self.once - self.sonra if self.kabul else 0


def _sayfa_sayisi(yol: Path) -> int | None:
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore
        except ImportError:
            return None
    try:
        with pymupdf.open(yol) as d:
            return len(d)
    except Exception:
        return None


def isle(gorev: tuple[Path, Path, Path, str, bool]) -> Sonuc:
    kaynak, kok, hedef_kok, kalite, uygula = gorev
    bagil = kaynak.relative_to(kok)
    hedef = hedef_kok / bagil
    once = kaynak.stat().st_size

    if not uygula:
        hedef = Path(f"/tmp/kucult_deneme_{abs(hash(str(kaynak)))}.pdf")
    else:
        hedef.parent.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            ["gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.5",
             f"-dPDFSETTINGS=/{kalite}", "-dNOPAUSE", "-dQUIET", "-dBATCH",
             "-dAutoRotatePages=/None", f"-sOutputFile={hedef}", str(kaynak)],
            check=True, capture_output=True, timeout=900,
        )
    except subprocess.TimeoutExpired:
        return _geri_al(kaynak, hedef, once, uygula, "zaman aşımı")
    except subprocess.CalledProcessError as e:
        return _geri_al(kaynak, hedef, once, uygula,
                        f"gs hatası: {e.stderr.decode('utf8', 'replace')[:80]}")

    if not hedef.exists():
        return _geri_al(kaynak, hedef, once, uygula, "çıktı yok")

    sonra = hedef.stat().st_size

    # doğrulama: sayfa sayısı korunmalı
    a, b = _sayfa_sayisi(kaynak), _sayfa_sayisi(hedef)
    if a is not None and b is not None and a != b:
        return _geri_al(kaynak, hedef, once, uygula, f"sayfa {a}!={b}")

    if sonra >= once * (1 - ASGARI_KAZANC):
        return _geri_al(kaynak, hedef, once, uygula, "kazanç yok")

    if not uygula:
        hedef.unlink(missing_ok=True)
    return Sonuc(kaynak, once, sonra, True)


def _geri_al(kaynak: Path, hedef: Path, once: int, uygula: bool, not_: str) -> Sonuc:
    """Dönüşüm işe yaramadı: orijinali olduğu gibi kopyala."""
    hedef.unlink(missing_ok=True)
    if uygula:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(kaynak, hedef)
    return Sonuc(kaynak, once, once, False, not_)


def main() -> int:
    ap = argparse.ArgumentParser(description="PDF arşivini güvenli şekilde küçültür")
    ap.add_argument("arsiv", type=Path)
    ap.add_argument("hedef", type=Path)
    ap.add_argument("--uygula", action="store_true", help="yaz (yoksa yalnızca ölç)")
    ap.add_argument("--kalite", choices=KALITELER, default="ebook")
    ap.add_argument("-j", "--is-parcacigi", type=int, default=4)
    ap.add_argument("--limit", type=int, help="ilk N dosya (deneme için)")
    a = ap.parse_args()

    if not a.arsiv.is_dir():
        print(f"hata: dizin yok: {a.arsiv}", file=sys.stderr)
        return 1
    if a.uygula and a.hedef.resolve() == a.arsiv.resolve():
        print("hata: hedef kaynakla aynı olamaz", file=sys.stderr)
        return 1

    dosyalar = sorted(p for p in a.arsiv.rglob("*.pdf") if p.is_file())
    if a.limit:
        dosyalar = dosyalar[: a.limit]
    if not dosyalar:
        print("PDF bulunamadı")
        return 1

    kip = "UYGULA" if a.uygula else "DENEME (hiçbir şey yazılmıyor)"
    print(f"{len(dosyalar)} PDF, kalite=/{a.kalite}, {kip}\n")

    gorevler = [(p, a.arsiv, a.hedef, a.kalite, a.uygula) for p in dosyalar]
    sonuclar: list[Sonuc] = []
    with ProcessPoolExecutor(max_workers=a.is_parcacigi) as hav:
        gelecekler = {hav.submit(isle, g): g[0] for g in gorevler}
        for i, gel in enumerate(as_completed(gelecekler), 1):
            s = gel.result()
            sonuclar.append(s)
            isaret = "✓" if s.kabul else "·"
            oran = f"%{100 - s.sonra / s.once * 100:.0f}" if s.kabul else s.not_ or "—"
            print(f"[{i}/{len(dosyalar)}] {isaret} {oran:>10}  {s.kaynak.name[:64]}",
                  flush=True)

    once = sum(s.once for s in sonuclar)
    sonra = sum(s.sonra for s in sonuclar)
    kabul = sum(1 for s in sonuclar if s.kabul)
    print(f"\n{'-' * 60}")
    print(f"küçülen dosya : {kabul}/{len(sonuclar)}")
    print(f"önce          : {insanca(once)}")
    print(f"sonra         : {insanca(sonra)}")
    if once:
        print(f"kazanç        : {insanca(once - sonra)}  (%{100 - sonra / once * 100:.1f})")
    if not a.uygula:
        print("\n(deneme kipi — yazmak için --uygula ekleyin)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
