# -*- coding: utf-8 -*-
"""Kategorisiz dosyalardan yeni anahtar kelime adayları önerir.

keyword_analyzer.py'nin yerini alır; artık dosya adlarına ek olarak indekslenmiş
PDF içeriklerinden de aday çıkarabilir.
"""

import os
import re
from collections import Counter

STOP_WORDS = {
    "pdf", "the", "and", "for", "guide", "with", "author", "vol", "volume", "edition",
    "part", "com", "org", "net", "www", "http", "https", "by", "of", "an", "to", "in",
    "is", "it", "on", "that", "this", "from", "as", "at", "are", "be", "or", "you",
    "your", "can", "will", "not", "has", "have", "was", "were", "which", "their",
    "may", "all", "any", "use", "used", "using", "new", "one", "two", "more", "also",
    "such", "when", "how", "what", "who", "its", "into", "than", "then", "there",
    "these", "those", "they", "them", "but", "about", "other", "some", "only", "each",
    "ve", "ile", "bir", "bu", "icin", "için", "olan", "daha", "gibi", "olarak",
    "chapter", "page", "figure", "table", "example", "note", "notes", "introduction",
    "copyright", "rights", "reserved", "inc", "ltd",
    # Her dökümanda geçen, kategori ayırt etmeyen yayın terimleri
    "techniques", "technique", "fundamentals", "handbook", "textbook", "tutorial",
    "course", "module", "modules", "reference", "complete", "essential", "practical",
    "overview", "cheat", "sheet", "edition", "press", "book", "books", "series",
    "questions", "answers", "summary", "lab", "labs", "slides", "presentation",
}

# Dosya adlarındaki kategori önekleri (CERT_, AG_SIZMA_, DIGER_ …) konu bildirmez;
# kural dosyasındaki kategori kodlarından ve klasör adlarından türetilir.
_STRUCTURAL = re.compile(r"[a-zA-Z]{3,}")

WORD = re.compile(r"[a-zA-Z][a-zA-Z0-9+#\-]{2,}")


def structural_tokens(rules):
    """Kategori kodlarında ve klasör adlarında geçen yapısal kelimeleri döner."""
    tokens = set()
    for code, path in rules.dir_structure.items():
        for word in _STRUCTURAL.findall(code + " " + path):
            tokens.add(word.lower())
    return tokens


def suggest(entries, rules, top=40, min_count=2, use_content=False):
    """Kategorisiz kalan dosyalardan sık geçen yeni terimleri döner.

    entries: (dosya_adı, içerik_metni) çiftleri.
    [(terim, adet, örnek_dosya)] döner.
    """
    known = {k.lower() for k in rules.all_keywords()}
    # Çok kelimeli anahtar kelimelerin parçalarını da bilinen say
    for keyword in list(known):
        known.update(keyword.split())
    known |= structural_tokens(rules)

    counts = Counter()
    samples = {}
    for name, text in entries:
        haystack = os.path.splitext(name)[0]
        if use_content and text:
            haystack += " " + text
        seen = set()
        for match in WORD.finditer(haystack):
            word = match.group().lower().strip("-+#")
            if len(word) < 3 or word.isdigit():
                continue
            if word in STOP_WORDS or word in known:
                continue
            if word in seen:
                continue          # aynı dosyada tekrar sayma
            seen.add(word)
            counts[word] += 1
            samples.setdefault(word, name)

    return [(word, count, samples[word])
            for word, count in counts.most_common(top) if count >= min_count]


def uncategorized(entries, rules, threshold=12):
    """Kural puanı eşiğin altında kalan (ad, metin) çiftlerini süzer."""
    out = []
    for name, text in entries:
        _, score, _ = rules.score(name, text or "")
        if score < threshold:
            out.append((name, text))
    return out
