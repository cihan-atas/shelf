# -*- coding: utf-8 -*-
"""Kopya dosya bulucu.

duplicate_finder.py'nin yerini alır. Tüm arşivi hash'lemek yerine önce dosya
boyutuna göre gruplar; yalnızca aynı boyuttaki adaylar okunur, bu da 9 GB'lık
bir arşivde işi dakikalardan saniyelere indirir.
"""

import os
from collections import defaultdict

from .organize import file_hash


def find(paths, progress=None):
    """Aynı içeriğe sahip dosya gruplarını bulur.

    [(hash, [yol, ...]), ...] döner; gruplar toplam israf edilen alana göre sıralı.
    """
    by_size = defaultdict(list)
    for path in paths:
        try:
            by_size[os.path.getsize(path)].append(path)
        except OSError:
            continue

    # Boyutu benzersiz olan dosyanın kopyası olamaz
    candidates = [(size, group) for size, group in by_size.items() if len(group) > 1]
    total = sum(len(g) for _, g in candidates)

    groups = defaultdict(list)
    done = 0
    for size, group in candidates:
        for path in group:
            done += 1
            if progress:
                progress(done, total, os.path.basename(path))
            digest = file_hash(path)
            if digest:
                groups[(digest, size)].append(path)

    duplicates = [(digest, sorted(paths_))
                  for (digest, _size), paths_ in groups.items() if len(paths_) > 1]
    duplicates.sort(key=lambda item: -_wasted(item[1]))
    return duplicates, {"scanned": len(paths), "hashed": total}


def _wasted(paths):
    """Bir grupta ilk kopya dışındakilerin kapladığı toplam alan."""
    try:
        return os.path.getsize(paths[0]) * (len(paths) - 1)
    except OSError:
        return 0


def wasted_bytes(duplicates):
    return sum(_wasted(paths) for _, paths in duplicates)


def pick_keeper(paths):
    """Bir gruptan hangisinin saklanacağını seçer: en kısa yol, sonra en kısa ad."""
    return min(paths, key=lambda p: (p.count(os.sep), len(os.path.basename(p)), p))


def prune(duplicates, dry_run=True, progress=None):
    """Her gruptan birini bırakıp diğerlerini siler. (silinen, kazanılan_bayt, hatalar)"""
    removed = 0
    freed = 0
    errors = []
    total = sum(len(p) - 1 for _, p in duplicates)
    done = 0
    for _, paths in duplicates:
        keeper = pick_keeper(paths)
        for path in paths:
            if path == keeper:
                continue
            done += 1
            if progress:
                progress(done, total, os.path.basename(path))
            try:
                size = os.path.getsize(path)
                if not dry_run:
                    os.remove(path)
                removed += 1
                freed += size
            except OSError as e:
                errors.append((path, str(e)))
    return removed, freed, errors
