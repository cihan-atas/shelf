# -*- coding: utf-8 -*-
"""API anahtarı saklama.

Anahtarlar ~/.config/shelf/keys.env dosyasında, yalnızca kullanıcının
okuyabileceği izinlerle (0600) tutulur. Bilinçli olarak ~/.shelfrc'den ayrı:
yapılandırma paylaşılabilir, anahtarlar paylaşılamaz.

Arama sırası — ilki kazanır:
  1. ortam değişkeni       (GROQ_API_KEY gibi; CI ve tek seferlik kullanım)
  2. ~/.config/shelf/keys.env
  3. arşiv/proje dizinindeki .env   (eski kurulumlarla uyumluluk)
"""

import os
import re

from .providers import PROVIDERS

CONFIG_DIR = os.path.expanduser("~/.config/shelf")
KEYS_PATH = os.path.join(CONFIG_DIR, "keys.env")

_SATIR = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")


def _coz(deger):
    """Tırnakları soyar."""
    if len(deger) >= 2 and deger[0] == deger[-1] and deger[0] in "\"'":
        return deger[1:-1]
    return deger


def _oku(yol):
    """Bir .env dosyasını sözlüğe okur. Dosya yoksa boş sözlük döner."""
    veri = {}
    try:
        with open(yol, "r", encoding="utf-8") as f:
            for satir in f:
                satir = satir.strip()
                if not satir or satir.startswith("#"):
                    continue
                m = _SATIR.match(satir)
                if m:
                    veri[m.group(1)] = _coz(m.group(2))
    except (OSError, UnicodeDecodeError):
        pass
    return veri


def _dosya_anahtarlari():
    return _oku(KEYS_PATH)


def _env_dosyalari():
    """Uyumluluk için taranan eski .env konumları."""
    from . import config as config_mod

    yollar = []
    cfg_arsiv = config_mod.load().get("archive_dir")
    if cfg_arsiv:
        yollar.append(os.path.join(cfg_arsiv, ".env"))
        yollar.append(os.path.join(os.path.dirname(cfg_arsiv.rstrip("/")), ".env"))
    yollar.append(os.path.join(os.getcwd(), ".env"))
    proje = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    yollar.append(os.path.join(proje, ".env"))
    return yollar


def get(saglayici):
    """Sağlayıcının API anahtarını döner; yoksa None."""
    spec = PROVIDERS.get(saglayici)
    if spec is None:
        return None
    ad = spec.env_var

    deger = os.environ.get(ad)
    if deger:
        return deger.strip()

    deger = _dosya_anahtarlari().get(ad)
    if deger:
        return deger.strip()

    gorulen = set()
    for yol in _env_dosyalari():
        yol = os.path.abspath(yol)
        if yol in gorulen:
            continue
        gorulen.add(yol)
        deger = _oku(yol).get(ad)
        if deger:
            return deger.strip()
    return None


def kaynak(saglayici):
    """Anahtarın nereden geldiğini açıklar (tanı çıktısı için)."""
    spec = PROVIDERS.get(saglayici)
    if spec is None:
        return None
    ad = spec.env_var
    if os.environ.get(ad):
        return "ortam değişkeni"
    if _dosya_anahtarlari().get(ad):
        return KEYS_PATH
    for yol in _env_dosyalari():
        if _oku(yol).get(ad):
            return yol
    return None


def maskele(anahtar):
    """Anahtarı günlüğe/ekrana basılabilir hale getirir."""
    if not anahtar:
        return "—"
    if len(anahtar) <= 10:
        return anahtar[:2] + "…"
    return f"{anahtar[:6]}…{anahtar[-4:]}"


def set_(saglayici, anahtar):
    """Anahtarı keys.env dosyasına yazar. Dosya 0600 izinle oluşturulur."""
    spec = PROVIDERS.get(saglayici)
    if spec is None:
        raise KeyError(saglayici)
    anahtar = (anahtar or "").strip()
    if not anahtar:
        raise ValueError("boş anahtar")

    veri = _dosya_anahtarlari()
    veri[spec.env_var] = anahtar
    _yaz(veri)
    return KEYS_PATH


def remove(saglayici):
    """Anahtarı dosyadan siler. Silindiyse True döner."""
    spec = PROVIDERS.get(saglayici)
    if spec is None:
        raise KeyError(saglayici)
    veri = _dosya_anahtarlari()
    if spec.env_var not in veri:
        return False
    del veri[spec.env_var]
    _yaz(veri)
    return True


def _yaz(veri):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, 0o700)
    except OSError:
        pass

    gecici = KEYS_PATH + ".tmp"
    # İzinleri baştan dar tut: anahtar hiçbir an dünyaya açık olmasın
    bayrak = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(gecici, bayrak, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("# shelf API anahtarları — bu dosyayı paylaşmayın\n")
            for ad in sorted(veri):
                f.write(f"{ad}={veri[ad]}\n")
    except Exception:
        os.unlink(gecici)
        raise
    os.replace(gecici, KEYS_PATH)
    try:
        os.chmod(KEYS_PATH, 0o600)
    except OSError:
        pass


def durum():
    """Her sağlayıcı için (ad, spec, anahtar_var_mı, kaynak) listesi."""
    satirlar = []
    for ad, spec in PROVIDERS.items():
        anahtar = get(ad)
        satirlar.append((ad, spec, anahtar, kaynak(ad) if anahtar else None))
    return satirlar
