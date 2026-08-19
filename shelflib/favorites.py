# -*- coding: utf-8 -*-
"""Favori dökümanlar.

Favoriler ~/.local/share/shelf/favorites.json içinde, arşiv köküne GÖRELİ
yolla saklanır. Mutlak yol yerine göreli yol tutulması bilinçlidir: arşiv
dizini taşınsa ya da yeniden adlandırılsa favoriler bozulmaz.

Dosya biçimi:
    {"version": 1, "items": {"<göreli/yol.pdf>": {"added": "2026-08-19T12:00:00"}}}
"""

import json
import os
from datetime import datetime

DATA_DIR = os.path.expanduser("~/.local/share/shelf")
FAV_PATH = os.path.join(DATA_DIR, "favorites.json")
SURUM = 1


def _bagil(path, archive_dir):
    """Mutlak yolu arşiv köküne göreli hale getirir; dışarıdaysa mutlak bırakır."""
    if not archive_dir:
        return os.path.abspath(path)
    try:
        ortak = os.path.commonpath(
            [os.path.abspath(path), os.path.abspath(archive_dir)])
    except ValueError:      # farklı sürücüler (Windows)
        return os.path.abspath(path)
    if ortak != os.path.abspath(archive_dir):
        return os.path.abspath(path)
    return os.path.relpath(os.path.abspath(path), os.path.abspath(archive_dir))


def _mutlak(anahtar, archive_dir):
    if os.path.isabs(anahtar):
        return anahtar
    return os.path.join(archive_dir or "", anahtar)


def yukle():
    """Favori sözlüğünü döner: {gorel_yol: {"added": ...}}"""
    try:
        with open(FAV_PATH, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    if not isinstance(veri, dict):
        return {}
    ogeler = veri.get("items")
    return ogeler if isinstance(ogeler, dict) else {}


def _kaydet(ogeler):
    os.makedirs(DATA_DIR, exist_ok=True)
    gecici = FAV_PATH + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump({"version": SURUM, "items": ogeler}, f,
                  indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(gecici, FAV_PATH)     # atomik: yarım dosya oluşmaz


def favori_mi(path, archive_dir):
    return _bagil(path, archive_dir) in yukle()


def ekle(path, archive_dir):
    """Favoriye ekler. Zaten varsa False döner."""
    anahtar = _bagil(path, archive_dir)
    ogeler = yukle()
    if anahtar in ogeler:
        return False
    ogeler[anahtar] = {"added": datetime.now().isoformat(timespec="seconds")}
    _kaydet(ogeler)
    return True


def cikar(path, archive_dir):
    """Favoriden çıkarır. Yoksa False döner."""
    anahtar = _bagil(path, archive_dir)
    ogeler = yukle()
    if anahtar not in ogeler:
        return False
    del ogeler[anahtar]
    _kaydet(ogeler)
    return True


def degistir(path, archive_dir):
    """Favori durumunu tersine çevirir. Yeni durumu (True=favori) döner."""
    if favori_mi(path, archive_dir):
        cikar(path, archive_dir)
        return False
    ekle(path, archive_dir)
    return True


def temizle():
    """Tüm favorileri siler. Silinen sayısını döner."""
    n = len(yukle())
    _kaydet({})
    return n


def liste(archive_dir, sadece_mevcut=False):
    """(mutlak_yol, bagil_yol, eklenme, var_mi) listesi döner, eklenme sırasına göre."""
    satirlar = []
    for anahtar, meta in yukle().items():
        mutlak = _mutlak(anahtar, archive_dir)
        var = os.path.exists(mutlak)
        if sadece_mevcut and not var:
            continue
        satirlar.append((mutlak, anahtar, meta.get("added", ""), var))
    satirlar.sort(key=lambda s: s[2])
    return satirlar


def anahtar_kumesi():
    """Hızlı üyelik testi için favori anahtarlarının kümesi."""
    return set(yukle())


def budala(archive_dir):
    """Artık diskte olmayan favorileri temizler. Silinen sayısını döner."""
    ogeler = yukle()
    olmayan = [a for a in ogeler if not os.path.exists(_mutlak(a, archive_dir))]
    for a in olmayan:
        del ogeler[a]
    if olmayan:
        _kaydet(ogeler)
    return len(olmayan)
