# -*- coding: utf-8 -*-
"""~/.shelfrc yapılandırma yönetimi."""

import json
import os

CONFIG_PATH = os.path.expanduser("~/.shelfrc")
DATA_DIR = os.path.expanduser("~/.local/share/shelf")
DEFAULT_INDEX = os.path.join(DATA_DIR, "index.db")

DEFAULTS = {
    "archive_dir": "",
    "index_path": DEFAULT_INDEX,
    "extensions": [".pdf", ".md", ".txt", ".epub"],
    "index_max_chars": 60000,
    "index_max_pages": 40,
    "limit": 200,
    "ai_model": "gemini-flash-latest",
    "ai_max_candidates": 20,
    # Kural puanı bu eşiğin altında kalırsa karar AI'a devredilir. 1180 dosyalık
    # arşive karşı ölçüldü: 15'te dosyaların ~%76'sına kural karar veriyor.
    "organize_threshold": 15,
}

# Ayarlarda arşiv yolu yoksa denenen yaygın konumlar. Kendi yolunuzu kalıcı
# olarak tanıtmak için: shelf config --archive /yol/to/arsiv
_GUESSES = [
    "~/Documents/Cyber_Archive",
    "~/Documents/arsiv",
    "~/Cyber_Archive",
    "~/arsiv",
    "~/archive",
]


def _guess_archive():
    for g in _GUESSES:
        p = os.path.expanduser(g)
        if os.path.isdir(p):
            return p
    return ""


def load():
    """Yapılandırmayı yükler; eksik anahtarları varsayılanlarla tamamlar."""
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user = json.load(f)
        if isinstance(user, dict):
            cfg.update({k: v for k, v in user.items() if v is not None})
    except FileNotFoundError:
        pass
    except (json.JSONDecodeError, OSError):
        pass
    if not cfg.get("archive_dir"):
        cfg["archive_dir"] = _guess_archive()
    cfg["archive_dir"] = os.path.expanduser(cfg["archive_dir"] or "")
    cfg["index_path"] = os.path.expanduser(cfg["index_path"] or DEFAULT_INDEX)
    return cfg


def save(cfg):
    """Yapılandırmayı ~/.shelfrc dosyasına yazar."""
    os.makedirs(os.path.dirname(CONFIG_PATH) or ".", exist_ok=True)
    slim = {k: v for k, v in cfg.items() if DEFAULTS.get(k) != v}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(slim, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return CONFIG_PATH


def set_key(key, value):
    cfg = load()
    cfg[key] = value
    save(cfg)
    return cfg
