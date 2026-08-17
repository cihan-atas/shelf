# -*- coding: utf-8 -*-
"""Kategori kuralları: klasör şeması ve puanlı anahtar kelime haritası."""

import json
import os
import re
from collections import defaultdict

DEFAULT_RULES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.json")
# Alt çizgi ve tire regex'te kelime karakteri sayılır; \b sınırlarının çalışması için
# dosya adlarındaki ayraçları boşluğa çeviririz.
_SEPARATORS = re.compile(r"[_\-\.\(\)\[\]/,+]+")


def _frequency_bonus(count):
    """Bir terimin metinde kaç kez geçtiğini kademeli bir çarpana çevirir.

    Tek geçiş çoğu zaman rastlantı; onlarca geçiş dökümanın konusunu belli eder.
    Doğrusal saymak yaygın kelimeleri aşırı ödüllendirdiği için kademelendirilir.
    """
    if count >= 10:
        return 3
    if count >= 3:
        return 2
    return 1
UNCATEGORIZED = "KATEGORISIZ"
FALLBACK_DIR = "05_OZEL_KONULAR_VE_RAPORLAR/99_Kategorisiz_ve_Genel"


class RulesError(Exception):
    pass


class Rules:
    """DIR_STRUCTURE + KEYWORD_MAP ikilisini sarmalar ve puanlama yapar."""

    def __init__(self, dir_structure, keyword_map):
        self.dir_structure = dir_structure
        self.keyword_map = keyword_map
        # Anahtar kelime desenlerini bir kez derle
        self._patterns = {}
        for category, keywords in keyword_map.items():
            compiled = []
            for keyword, weight in keywords.items():
                pattern = re.compile(r"\b" + re.escape(keyword.lower()) + r"\b")
                compiled.append((pattern, int(weight), keyword))
            self._patterns[category] = compiled

    # ---------- yükleme ----------

    @classmethod
    def load(cls, path=None):
        path = path or DEFAULT_RULES
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise RulesError(f"Kural dosyası bulunamadı: {path}")
        except json.JSONDecodeError as e:
            raise RulesError(f"Kural dosyası geçerli JSON değil: {path} ({e})")

        dir_structure = data.get("DIR_STRUCTURE")
        keyword_map = data.get("KEYWORD_MAP")
        if not dir_structure or not keyword_map:
            raise RulesError(f"'{path}' içinde DIR_STRUCTURE veya KEYWORD_MAP eksik.")

        # Puanlı olmayan (eski liste formatı) haritaları normalize et
        normalized = {}
        for category, keywords in keyword_map.items():
            if isinstance(keywords, dict):
                normalized[category] = {k: int(v) for k, v in keywords.items()}
            else:
                normalized[category] = {k: 1 for k in keywords}
        return cls(dir_structure, normalized)

    # ---------- puanlama ----------

    def score(self, filename_text, content_text="", filename_weight=3):
        """Metni puanlar. (kategori, puan, ayrıntı_sözlüğü) döner.

        Dosya adındaki eşleşmeler içerik eşleşmelerinden daha güçlü kabul edilir,
        çünkü arşivdeki adlandırma zaten konuyu özetliyor.
        """
        name_low = " " + _SEPARATORS.sub(" ", filename_text.lower()) + " "
        content_low = content_text.lower()
        scores = defaultdict(int)
        hits = defaultdict(list)

        for category, patterns in self._patterns.items():
            for pattern, weight, keyword in patterns:
                if pattern.search(name_low):
                    scores[category] += weight * filename_weight
                    hits[category].append(f"ad:{keyword}")
                if content_low:
                    n = len(pattern.findall(content_low))
                    if n:
                        scores[category] += weight * _frequency_bonus(n)
                        hits[category].append(f"{keyword}×{n}")

        if not scores:
            return UNCATEGORIZED, 0, {}
        best = max(scores, key=scores.get)
        return best, scores[best], dict(hits)

    def ranked(self, filename_text, content_text="", filename_weight=3, top=3):
        """En yüksek puanlı ilk `top` kategoriyi (kategori, puan) olarak döner."""
        name_low = " " + _SEPARATORS.sub(" ", filename_text.lower()) + " "
        content_low = content_text.lower()
        scores = defaultdict(int)
        for category, patterns in self._patterns.items():
            for pattern, weight, keyword in patterns:
                if pattern.search(name_low):
                    scores[category] += weight * filename_weight
                if content_low:
                    n = len(pattern.findall(content_low))
                    if n:
                        scores[category] += weight * _frequency_bonus(n)
        return sorted(scores.items(), key=lambda kv: -kv[1])[:top]

    # ---------- yol çözümleme ----------

    def folder_for(self, category):
        """Kategori koduna karşılık gelen göreli klasör yolunu döner."""
        suffix = self.dir_structure.get(category)
        if not suffix:
            suffix = self.dir_structure.get(UNCATEGORIZED, FALLBACK_DIR)
        return os.path.join(*suffix.split("/"))

    def categories(self):
        """(kod, klasör, açıklama) üçlülerini döner."""
        out = []
        for code, path in self.dir_structure.items():
            label = path.split("/")[-1].replace("_", " ")
            label = re.sub(r"^\d+\s*", "", label)
            out.append((code, path, label))
        return out

    def all_keywords(self):
        return {k for keywords in self.keyword_map.values() for k in keywords}

    def prompt_catalog(self, skip_uncategorized=True):
        """AI'a verilecek kategori listesini metin olarak hazırlar."""
        lines = []
        for code, path, label in self.categories():
            if skip_uncategorized and code == UNCATEGORIZED:
                continue
            lines.append(f"- {code}: {label}")
        return "\n".join(lines)
