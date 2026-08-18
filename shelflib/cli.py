# -*- coding: utf-8 -*-
"""shelf komut satırı arayüzü — hem tek seferlik hem interaktif mod."""

import argparse
import os
import sys
import time

from . import __version__
from . import ai as ai_mod
from . import config as config_mod
from . import index as idx
from . import keys as keys_mod
from . import providers
from . import search as search_mod
from .rules import Rules, RulesError

EPILOG = """\
ÖRNEK KULLANIMLAR:
------------------
  shelf                              İnteraktif arayüzü açar (varsayılan arşivde)
  shelf kerberos                     İnteraktif arayüzü bu sorguyla açar
  shelf -q kerberos                  Tek seferlik arama, sonucu basar ve çıkar
  shelf -q "CVE-2021-44228" -c       İçerikte arar (indeks varsa anında)
  shelf -q kerberos --ai             Sonuçları yapay zeka ile sıralar
  shelf -q ldap --json               Çıktıyı JSON olarak verir (pipe/script için)

  shelf index                        Arşivi indeksler (ilk kurulumda bir kez)
  shelf index --rebuild              İndeksi sıfırdan kurar
  shelf index --info                 İndeks durumunu gösterir
  shelf config --archive ~/arsiv     Varsayılan arşiv dizinini ayarlar
  shelf config --show                Mevcut ayarları gösterir

ARŞİV BAKIMI:
-------------
  shelf organize ~/Indirilenler      Yeni dökümanları kategorilere yerleştirir
  shelf organize ~/Indirilenler -n   Önce ne yapacağını gösterir (kuru çalıştırma)
  shelf duplicates                   Kopya dosyaları bulur
  shelf keywords                     Kategorisiz dosyalardan yeni kural önerir
  shelf rules                        Kategori şemasını listeler

YAPAY ZEKA:
-----------
  shelf keys                         Anahtar durumunu gösterir
  shelf keys --set groq              Groq anahtarını kaydeder
  shelf keys --test                  Kayıtlı anahtarları gerçek istekle dener
  shelf models                       Kullanılabilir modelleri listeler
  shelf models -p openrouter --free  Yalnızca ücretsiz modelleri gösterir
  shelf config --model groq:llama-3.3-70b-versatile
"""


def _c(text, color=None, bold=False):
    """Terminal renklendirme (TTY değilse düz metin)."""
    if not sys.stdout.isatty():
        return text
    codes = {"red": 31, "green": 32, "yellow": 33, "blue": 34,
             "magenta": 35, "cyan": 36, "grey": 90}
    parts = []
    if bold:
        parts.append("1")
    if color in codes:
        parts.append(str(codes[color]))
    if not parts:
        return text
    return f"\033[{';'.join(parts)}m{text}\033[0m"


def _err(msg):
    print(_c("Hata: ", "red", True) + msg, file=sys.stderr)


COMMANDS = ("index", "config", "organize", "duplicates", "keywords", "rules",
            "keys", "models")


def build_parser(with_subcommands=True):
    """Ayrıştırıcıyı kurar.

    Serbest arama terimleri (`shelf kerberos`) ile alt komut adları argparse'ta
    aynı konumu paylaşamadığı için iki varyant üretilir: alt komutlu olan
    yardım ve komut yönlendirmesi, alt komutsuz olan arama için kullanılır.
    """
    parser = argparse.ArgumentParser(
        prog="shelf",
        description="shelf - AI Destekli Siber Güvenlik Arşiv Arama Motoru",
        epilog=EPILOG,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    if not with_subcommands:
        parser.add_argument("terms", nargs="*",
                            help="Aranacak kelimeler. Verilmezse interaktif arayüz açılır.")
    parser.add_argument("-q", "--query", dest="oneshot", metavar="SORGU",
                        help="Tek seferlik arama yapar, sonucu basar ve çıkar.")
    parser.add_argument("-d", "--dir", dest="archive_dir", metavar="YOL",
                        help="Bu çalıştırma için arşiv dizini (varsayılanı geçersiz kılar).")
    parser.add_argument("-c", "--content", action="store_true",
                        help="Dosya içeriklerinde de arar.")
    parser.add_argument("-k", "--category", help="Aramayı bir üst kategoriyle sınırlar.")
    parser.add_argument("-n", "--limit", type=int, help="Maksimum sonuç sayısı.")
    parser.add_argument("--ai", action="store_true",
                        help="Sonuçları yapay zeka ile alaka puanına göre sıralar.")
    parser.add_argument("--ai-limit", dest="ai_limit", metavar="N",
                        help="AI'ın inceleyeceği sonuç sayısı. 'hepsi' ya da 0 "
                             "tüm sonuçları tarar. (Ayarlardan: ai_max_candidates)")
    parser.add_argument("-m", "--model", help="Kullanılacak AI modeli.")
    parser.add_argument("--json", action="store_true", help="Çıktıyı JSON olarak verir.")
    parser.add_argument("-V", "--version", action="version", version=f"shelf {__version__}")

    if not with_subcommands:
        return parser

    sub = parser.add_subparsers(dest="command", metavar="KOMUT")

    p_index = sub.add_parser("index", help="Arşiv indeksini kurar/günceller.",
                             description="Arşivdeki dosyaları tarayıp aranabilir indekse alır.")
    p_index.add_argument("-d", "--dir", dest="archive_dir", help="İndekslenecek arşiv dizini.")
    p_index.add_argument("--rebuild", action="store_true", help="İndeksi sıfırdan kurar.")
    p_index.add_argument("--info", action="store_true", help="İndeks durumunu gösterir.")
    p_index.add_argument("-v", "--verbose", action="store_true", help="Her dosyayı listeler.")

    p_cfg = sub.add_parser("config", help="Ayarları görüntüler/değiştirir.",
                           description=f"Ayar dosyası: {config_mod.CONFIG_PATH}")
    p_cfg.add_argument("--archive", help="Varsayılan arşiv dizinini ayarlar.")
    p_cfg.add_argument("--model", help="Varsayılan AI modelini ayarlar.")
    p_cfg.add_argument("--index-path", help="İndeks veritabanının yolunu ayarlar.")
    p_cfg.add_argument("--limit", type=int, help="Varsayılan sonuç limitini ayarlar.")
    p_cfg.add_argument("--ai-limit", dest="ai_limit", metavar="N",
                       help="AI'ın inceleyeceği sonuç sayısı ('hepsi' = sınırsız).")
    p_cfg.add_argument("--show", action="store_true", help="Mevcut ayarları gösterir.")

    p_org = sub.add_parser(
        "organize", help="Dökümanları kategorilere ayırıp arşive yerleştirir.",
        description="Kural tabanlı puanlama ve (gerekirse) AI ile kategorilendirir.",
        formatter_class=argparse.RawTextHelpFormatter)
    p_org.add_argument("source_dir", help="Düzenlenecek dosyaların bulunduğu dizin.")
    p_org.add_argument("-t", "--target", dest="target_dir",
                       help="Hedef arşiv dizini. (Varsayılan: ayarlardaki arşiv)")
    p_org.add_argument("-n", "--dry-run", action="store_true",
                       help="Hiçbir dosyaya dokunmadan ne yapılacağını gösterir.")
    p_org.add_argument("--move", action="store_true",
                       help="Dosyaları kopyalamak yerine taşır.")
    p_org.add_argument("-r", "--recursive", action="store_true",
                       help="Kaynak dizinin alt klasörlerini de tarar.")
    p_org.add_argument("--ai-only", action="store_true", dest="ai_only",
                       help="Kural puanlamasını yok sayar, her dosyayı AI'a sorar. "
                            "(Kategori listesi yine kurallardan gelir.)")
    p_org.add_argument("--no-ai", action="store_true",
                       help="Kural puanı düşük kalsa bile AI'a sormaz.")
    p_org.add_argument("--rename", action="store_true",
                       help="Dosya adlarını da AI ile yeniden yazar.")
    p_org.add_argument("--threshold", type=int,
                       help="AI'a devredilme eşiği. (Ayarlardan: organize_threshold)")
    p_org.add_argument("--no-reindex", action="store_true",
                       help="İşlem sonrası indeksi güncellemez.")
    p_org.add_argument("-m", "--model", help="Kullanılacak AI modeli.")
    p_org.add_argument("--rules", help="Kullanılacak kural dosyası (JSON).")

    p_dup = sub.add_parser("duplicates", help="Kopya dosyaları bulur.",
                           description="Aynı içeriğe sahip dosyaları tespit eder.")
    p_dup.add_argument("-d", "--dir", dest="archive_dir",
                       help="Taranacak dizin. (Varsayılan: ayarlardaki arşiv)")
    p_dup.add_argument("--prune", action="store_true",
                       help="Her gruptan birini bırakıp fazlalıkları SİLER.")
    p_dup.add_argument("-n", "--dry-run", action="store_true",
                       help="--prune ile: neyin silineceğini gösterir, silmez.")
    p_dup.add_argument("--all-files", action="store_true",
                       help="Sadece döküman türlerini değil, tüm dosyaları tarar.")

    p_kw = sub.add_parser("keywords", help="Yeni anahtar kelime adayları önerir.",
                          description="Kategorisiz kalan dosyalardan sık geçen terimleri çıkarır.")
    p_kw.add_argument("-d", "--dir", dest="archive_dir",
                      help="Taranacak dizin. (Varsayılan: ayarlardaki arşiv)")
    p_kw.add_argument("--content", action="store_true",
                      help="Dosya adlarına ek olarak indekslenmiş içerikleri de tarar.")
    p_kw.add_argument("--top", type=int, default=40, help="Gösterilecek terim sayısı.")
    p_kw.add_argument("--min-count", type=int, default=2,
                      help="Bir terimin önerilmesi için gereken en az dosya sayısı.")
    p_kw.add_argument("--threshold", type=int,
                      help="Kategorisiz sayılma eşiği. (Ayarlardan: organize_threshold)")
    p_kw.add_argument("--rules", help="Kullanılacak kural dosyası (JSON).")

    p_rules = sub.add_parser("rules", help="Kategori şemasını ve kuralları gösterir.")
    p_rules.add_argument("--rules", help="Kullanılacak kural dosyası (JSON).")
    p_rules.add_argument("-k", "--keywords", action="store_true",
                         help="Her kategorinin anahtar kelimelerini de listeler.")

    p_keys = sub.add_parser(
        "keys", help="API anahtarlarını yönetir.",
        description="API anahtarlarını ~/.config/shelf/keys.env içinde saklar (izin 0600).")
    p_keys.add_argument("--set", metavar="SAGLAYICI", dest="set_provider",
                        choices=list(providers.PROVIDERS),
                        help="Anahtar ekler/günceller (değer gizli olarak sorulur).")
    p_keys.add_argument("--remove", metavar="SAGLAYICI", dest="remove_provider",
                        choices=list(providers.PROVIDERS), help="Anahtarı siler.")
    p_keys.add_argument("--test", action="store_true",
                        help="Kayıtlı anahtarları gerçek istekle dener.")

    p_models = sub.add_parser(
        "models", help="Sağlayıcıların modellerini listeler.",
        description="Sağlayıcıdan canlı model listesi çeker; ücretsizleri işaretler.")
    p_models.add_argument("-p", "--provider", choices=list(providers.PROVIDERS),
                          help="Yalnızca bu sağlayıcı (öntanımlı: anahtarı olan hepsi).")
    p_models.add_argument("--free", action="store_true",
                          help="Yalnızca ücretsiz modelleri göster.")
    p_models.add_argument("-a", "--all", action="store_true",
                          help="Sohbet dışı modelleri de göster (gömme, ses, görüntü).")

    return parser


def load_rules(args):
    try:
        return Rules.load(getattr(args, "rules", None))
    except RulesError as e:
        _err(str(e))
        return None


def _ai_limit_coz(deger):
    """--ai-limit değerini sayıya çevirir. 'hepsi'/'all'/0 -> sınırsız."""
    if deger is None:
        return None
    metin = str(deger).strip().lower()
    if metin in ("hepsi", "all", "tum", "tümü", "0"):
        return 0
    try:
        n = int(metin)
    except ValueError:
        raise ValueError(f"--ai-limit sayı olmalı ya da 'hepsi': {deger}")
    if n < 0:
        raise ValueError("--ai-limit negatif olamaz.")
    return n


def resolve_cfg(args):
    cfg = config_mod.load()
    if getattr(args, "archive_dir", None):
        cfg["archive_dir"] = os.path.expanduser(args.archive_dir)
    if getattr(args, "model", None):
        cfg["ai_model"] = args.model
    if getattr(args, "limit", None):
        cfg["limit"] = args.limit
    if getattr(args, "ai_limit", None) is not None:
        try:
            cfg["ai_max_candidates"] = _ai_limit_coz(args.ai_limit)
        except ValueError as e:
            _err(str(e))
            raise SystemExit(1)
    if getattr(args, "threshold", None):
        cfg["organize_threshold"] = args.threshold
    return cfg


# ---------- alt komutlar ----------

def cmd_index(args):
    cfg = resolve_cfg(args)
    if args.info:
        meta = idx.info(cfg["index_path"])
        if not meta:
            print("İndeks bulunamadı. 'shelf index' ile oluşturabilirsiniz.")
            return 1
        age = time.time() - meta["built_at"]
        print(f"{_c('İndeks:', 'cyan', True)} {cfg['index_path']}")
        print(f"  Arşiv          : {meta['archive_dir']}")
        print(f"  Dosya sayısı   : {meta['files']}")
        print(f"  Metni çıkarılan: {meta['with_text']}")
        print(f"  Boyut          : {search_mod.human_size(meta['size'])}")
        print(f"  Son güncelleme : {time.strftime('%Y-%m-%d %H:%M', time.localtime(meta['built_at']))}"
              f" ({age / 3600:.1f} saat önce)")
        return 0

    if not cfg["archive_dir"] or not os.path.isdir(cfg["archive_dir"]):
        _err(f"Arşiv dizini bulunamadı: {cfg['archive_dir'] or '(ayarlanmamış)'}")
        print("  'shelf config --archive /yol/to/arsiv' ile ayarlayın.", file=sys.stderr)
        return 1
    if not idx.PYMUPDF_AVAILABLE:
        print(_c("Uyarı: PyMuPDF kurulu değil, PDF içerikleri indekslenmeyecek.", "yellow"))

    print(f"{_c('Arşiv:', 'blue', True)} {cfg['archive_dir']}")
    print(f"{_c('İndeks:', 'blue', True)} {cfg['index_path']}\n")

    started = time.time()
    is_tty = sys.stdout.isatty()

    def progress(i, total, relpath, state):
        if args.verbose:
            print(f"[{i}/{total}] {state}: {relpath}")
        elif is_tty:
            pct = i / total * 100
            bar_len = 28
            filled = int(bar_len * i / total)
            bar = "█" * filled + "░" * (bar_len - filled)
            name = os.path.basename(relpath)[:38].ljust(38)
            print(f"\r  {bar} {pct:5.1f}%  {i}/{total}  {name}", end="", flush=True)

    stats = idx.build(cfg, progress=progress, rebuild=args.rebuild)
    if is_tty and not args.verbose:
        print("\r" + " " * 100 + "\r", end="")

    print(_c("İndeksleme tamamlandı.", "green", True))
    print(f"  Toplam dosya   : {stats['total']}")
    print(f"  Yeni eklenen   : {stats['added']}")
    print(f"  Güncellenen    : {stats['updated']}")
    print(f"  Değişmemiş     : {stats['skipped']}")
    print(f"  Silinmiş kayıt : {stats['removed']}")
    if stats["no_text"]:
        print(f"  {_c('Metin çıkarılamayan', 'yellow')}: {stats['no_text']} (taranmış/korumalı PDF olabilir)")
    print(f"  Süre           : {time.time() - started:.1f} sn")
    return 0


def cmd_config(args):
    cfg = config_mod.load()
    changed = False
    if args.archive:
        path = os.path.expanduser(args.archive)
        if not os.path.isdir(path):
            _err(f"Dizin bulunamadı: {path}")
            return 1
        cfg["archive_dir"] = path
        changed = True
    if args.model:
        cfg["ai_model"] = args.model
        changed = True
    if args.index_path:
        cfg["index_path"] = os.path.expanduser(args.index_path)
        changed = True
    if args.limit:
        cfg["limit"] = args.limit
        changed = True
    if getattr(args, "ai_limit", None) is not None:
        try:
            cfg["ai_max_candidates"] = _ai_limit_coz(args.ai_limit)
        except ValueError as e:
            _err(str(e))
            return 1
        changed = True

    if changed:
        path = config_mod.save(cfg)
        print(_c(f"Ayarlar kaydedildi: {path}", "green"))

    if args.show or not changed:
        print(f"{_c('Ayar dosyası:', 'cyan', True)} {config_mod.CONFIG_PATH}"
              f"{'' if os.path.exists(config_mod.CONFIG_PATH) else _c('  (henüz yok)', 'grey')}")
        for key in ("archive_dir", "index_path", "ai_model", "limit",
                    "ai_max_candidates", "organize_threshold",
                    "index_max_pages", "index_max_chars"):
            val = cfg.get(key)
            if key == "ai_max_candidates" and not val:
                val = "hepsi (sınırsız)"
            marker = "" if val == config_mod.DEFAULTS.get(key) else _c(" *", "yellow")
            print(f"  {key:<18}: {val}{marker}")
        print(f"  {'extensions':<18}: {', '.join(cfg['extensions'])}")
        if not idx.exists(cfg["index_path"]):
            print(_c("\n  İndeks henüz oluşturulmamış — 'shelf index' çalıştırın.", "yellow"))
    return 0


def _bar(i, total, label, width=26):
    """Tek satırlık ilerleme çubuğu basar (yalnızca TTY'de)."""
    if not sys.stdout.isatty() or not total:
        return
    filled = int(width * i / total)
    bar = "█" * filled + "░" * (width - filled)
    print(f"\r  {bar} {i / total * 100:5.1f}%  {i}/{total}  {label[:34].ljust(34)}",
          end="", flush=True)


def _bar_done():
    if sys.stdout.isatty():
        print("\r" + " " * 92 + "\r", end="")


# ---------- organize ----------

def cmd_organize(args):
    from . import ai as ai_mod
    from . import organize as org

    rules = load_rules(args)
    if rules is None:
        return 1

    if getattr(args, "ai_only", False) and args.no_ai:
        _err("--ai-only ile --no-ai birlikte kullanılamaz.")
        return 1

    cfg = resolve_cfg(args)
    source = os.path.expanduser(args.source_dir)
    if not os.path.isdir(source):
        _err(f"Kaynak dizin bulunamadı: {source}")
        _yol_ipucu(source)
        return 1

    target = os.path.expanduser(args.target_dir) if args.target_dir else cfg["archive_dir"]
    if not target:
        _err("Hedef arşiv belirlenemedi. -t ile verin veya 'shelf config --archive' ayarlayın.")
        return 1

    files = org.list_source_files(source, recursive=args.recursive)
    if not files:
        print(f"'{source}' içinde işlenecek döküman bulunamadı.")
        return 1

    provider = None
    if not args.no_ai:
        try:
            provider = ai_mod.get_provider(cfg["ai_model"])
        except ai_mod.AIError as e:
            print(_c(f"Uyarı: AI devre dışı — {e}", "yellow"))
            print(_c("       Sadece kural tabanlı kategorilendirme yapılacak.", "yellow"))
    if args.rename and provider is None:
        print(_c("Uyarı: --rename için AI gerekli, dosya adları değiştirilmeyecek.", "yellow"))

    action_word = "taşınacak" if args.move else "kopyalanacak"
    print(f"{_c('Kaynak:', 'blue', True)} {source}  ({len(files)} dosya)")
    print(f"{_c('Hedef :', 'blue', True)} {target}")
    print(f"{_c('İşlem :', 'blue', True)} Dosyalar {action_word}"
          f"{', adlar AI ile yenilenecek' if args.rename and provider else ''}.")
    if args.dry_run:
        print(_c("\n--- KURU ÇALIŞTIRMA: hiçbir dosyaya dokunulmayacak ---", "yellow", True))
    print()

    def progress(i, total, name, state):
        _bar(i, total, f"{state}: {name}")

    actions, ai_errors = org.plan(files, rules, target, provider=provider,
                                  threshold=cfg["organize_threshold"],
                                  ai_only=getattr(args, "ai_only", False),
                                  rename=args.rename, progress=progress)
    _bar_done()

    if ai_errors:
        from collections import Counter
        print(_c(f"AI {len(ai_errors)} kez sonuç veremedi:", "yellow", True))
        for reason, count in Counter(ai_errors).most_common(3):
            print(_c(f"  {count}×  {reason}", "yellow"))
        print(_c("  Bu dosyalar kural puanına göre yerleştirildi.\n", "grey"))

    stats = org.apply(actions, move=args.move, dry_run=args.dry_run, progress=progress)
    _bar_done()

    # Kategori özeti
    print(_c("--- Kategori dağılımı ---", "cyan", True))
    summary = org.summarize(actions)
    for category, info in summary.items():
        folder = rules.dir_structure.get(category, "?")
        by = []
        if info.get("kural"):
            by.append(f"{info['kural']} kural")
        if info.get("ai"):
            by.append(f"{info['ai']} AI")
        if info.get("kategorisiz"):
            by.append(f"{info['kategorisiz']} eşleşmedi")
        color = "yellow" if category == "KATEGORISIZ" else None
        count = _c(str(info["count"]).rjust(4), color, True)
        detail = _c("(" + ", ".join(by) + ")", "grey")
        print(f"  {count}  {category:<22} {detail}")
        if args.dry_run:
            print(f"        {_c(folder, 'grey')}")

    # Kuru çalıştırmada tek tek ne olacağını göster
    if args.dry_run:
        print(_c("\n--- Planlanan işlemler ---", "cyan", True))
        for a in actions:
            tag = {"ai": _c("[AI]", "magenta"), "kural": _c("[kural]", "blue"),
                   "kategorisiz": _c("[?]", "yellow")}[a.decided_by]
            print(f"  {tag} {a.name}")
            rel = os.path.relpath(a.dest, target)
            renamed = "" if a.new_name == a.name else _c("  (yeniden adlandırıldı)", "magenta")
            print(f"        -> {rel}{renamed}")
            if a.note:
                print(f"        {_c(a.note, 'grey')}")
    else:
        print(_c("\n--- Sonuç ---", "cyan", True))
        for key in ("kopyalandı", "taşındı", "kopya", "hata"):
            if stats.get(key):
                color = "red" if key == "hata" else "yellow" if key == "kopya" else "green"
                print(f"  {_c(str(stats[key]).rjust(4), color, True)}  {key}")
        for a in actions:
            if a.status == "hata":
                print(f"  {_c('HATA', 'red')} {a.name}: {a.note}")

        moved_into_archive = os.path.abspath(target) == os.path.abspath(cfg["archive_dir"])
        if moved_into_archive and not args.no_reindex and (stats["kopyalandı"] or stats["taşındı"]):
            print(_c("\nİndeks güncelleniyor…", "blue"))
            istats = idx.build(cfg)
            print(f"  {istats['added']} yeni kayıt eklendi.")

    if args.dry_run:
        print(_c(f"\nGerçekten uygulamak için -n bayrağını kaldırın.", "yellow"))
    return 0


# ---------- duplicates ----------

def _yol_ipucu(yol):
    """Yaygın kabuk alıntılama hatalarını teşhis edip ipucu basar.

    En sık görüleni: tırnak İÇİNDE ters bölü ile kaçış. Kabuk tırnak içindeki
    '\\ ' dizisini boşluğa çevirmez, ters bölü dosya adının parçası olur.
    """
    if "\\" not in yol:
        return
    duzeltilmis = yol.replace("\\", "")
    if os.path.isdir(duzeltilmis):
        print("  Yol ters bölü içeriyor; tırnak içinde kaçışa gerek yok.",
              file=sys.stderr)
        print(f"  Şunu deneyin: {_c(chr(34) + duzeltilmis + chr(34), 'green')}",
              file=sys.stderr)
    else:
        print("  Yolda ters bölü var. Tırnak kullanıyorsanız kaçış eklemeyin;"
              " kaçış kullanıyorsanız tırnak koymayın.", file=sys.stderr)


def cmd_duplicates(args):
    from . import duplicates as dup
    from . import organize as org

    cfg = resolve_cfg(args)
    root = cfg["archive_dir"]
    if not root or not os.path.isdir(root):
        _err(f"Taranacak dizin bulunamadı: {root or '(ayarlanmamış)'}")
        return 1

    print(f"{_c('Taranıyor:', 'blue', True)} {root}")
    if args.all_files:
        paths = [os.path.join(r, f) for r, _, fs in os.walk(root) for f in fs
                 if not f.startswith(".")]
    else:
        paths = org.list_source_files(root, recursive=True)
    print(f"  {len(paths)} dosya bulundu. Boyutu benzersiz olanlar eleniyor…\n")

    groups, meta = dup.find(paths, progress=lambda i, t, n: _bar(i, t, n))
    _bar_done()

    if not groups:
        print(_c(f"Kopya dosya bulunamadı. ({meta['hashed']} aday okundu)", "green"))
        return 0

    wasted = dup.wasted_bytes(groups)
    print(_c(f"{len(groups)} kopya grubu bulundu — "
             f"{search_mod.human_size(wasted)} gereksiz yer kaplıyor.\n", "yellow", True))

    for i, (digest, paths_) in enumerate(groups, 1):
        keeper = dup.pick_keeper(paths_)
        size = os.path.getsize(paths_[0])
        print(f"  {_c(f'[{i}]', 'cyan')} {len(paths_)} kopya · "
              f"{search_mod.human_size(size)} · {digest[:12]}")
        for path in paths_:
            rel = os.path.relpath(path, root)
            mark = _c("saklanacak", "green") if path == keeper else _c("fazlalık", "grey")
            print(f"        {rel}  [{mark}]")
        print()

    if not args.prune:
        print(_c("Fazlalıkları silmek için: shelf duplicates --prune "
                 "(önce -n ile deneyin)", "grey"))
        return 0

    if not args.dry_run:
        doomed = sum(len(paths_) - 1 for _, paths_ in groups)
        print(_c(f"{doomed} dosya KALICI OLARAK SİLİNECEK "
                 f"({search_mod.human_size(wasted)} kazanılacak).", "red", True))
        print(_c("Her gruptan yukarıda 'saklanacak' işaretli olan kalır.", "grey"))
        if not sys.stdin.isatty():
            _err("Onay alınamıyor (terminal değil). Önce -n ile listeyi inceleyin.")
            return 1
        try:
            answer = input(_c("Devam etmek için 'evet' yazın: ", "yellow"))
        except (EOFError, KeyboardInterrupt):
            answer = ""
        if answer.strip().lower() not in ("evet", "e", "yes", "y"):
            print(_c("İptal edildi, hiçbir dosya silinmedi.", "green"))
            return 0

    removed, freed, errors = dup.prune(groups, dry_run=args.dry_run,
                                       progress=lambda i, t, n: _bar(i, t, n))
    _bar_done()
    verb = "silinecek" if args.dry_run else "silindi"
    print(_c(f"{removed} dosya {verb}, {search_mod.human_size(freed)} "
             f"{'kazanılacak' if args.dry_run else 'kazanıldı'}.",
             "yellow" if args.dry_run else "green", True))
    for path, msg in errors:
        print(f"  {_c('HATA', 'red')} {path}: {msg}")
    if not args.dry_run and removed:
        print(_c("\nİndeks güncelleniyor…", "blue"))
        istats = idx.build(cfg)
        print(f"  {istats['removed']} kayıt indeksten düşürüldü.")
    return 0


# ---------- keywords ----------

def cmd_keywords(args):
    from . import keywords as kw

    rules = load_rules(args)
    if rules is None:
        return 1
    cfg = resolve_cfg(args)
    root = cfg["archive_dir"]
    if not root or not os.path.isdir(root):
        _err(f"Taranacak dizin bulunamadı: {root or '(ayarlanmamış)'}")
        return 1

    entries = []
    if args.content:
        if not idx.exists(cfg["index_path"]):
            _err("--content için indeks gerekli. Önce 'shelf index' çalıştırın.")
            return 1
        con = idx.connect(cfg["index_path"])
        try:
            rows = con.execute(
                "SELECT f.name, files_fts.content FROM files f "
                "JOIN files_fts ON files_fts.rowid = f.id").fetchall()
            entries = [(r[0], r[1] or "") for r in rows]
        finally:
            con.close()
    else:
        from . import organize as org
        entries = [(os.path.basename(p), "") for p in org.list_source_files(root, recursive=True)]

    threshold = cfg["organize_threshold"]
    uncat = kw.uncategorized(entries, rules, threshold=threshold)
    print(f"{_c('Taranan dosya:', 'blue', True)} {len(entries)}")
    print(f"{_c('Kategorisiz  :', 'blue', True)} {len(uncat)} "
          f"(kural puanı {threshold} altında)\n")
    if not uncat:
        print(_c("Her dosya bir kategoriye oturuyor — yeni kurala gerek yok.", "green"))
        return 0

    suggestions = kw.suggest(uncat, rules, top=args.top,
                             min_count=args.min_count, use_content=args.content)
    if not suggestions:
        print(_c("Yeterince sık geçen yeni terim bulunamadı.", "yellow"))
        return 0

    print(_c("--- Anahtar kelime adayları ---", "cyan", True))
    print(_c(f"{'terim':<24} {'dosya':>6}   örnek", "grey"))
    for word, count, sample in suggestions:
        print(f"  {word:<22} {count:>6}   {_c(sample[:52], 'grey')}")
    from .rules import DEFAULT_RULES
    rules_path = getattr(args, "rules", None) or DEFAULT_RULES
    print(_c("\nBeğendiklerinizi kural dosyasındaki KEYWORD_MAP'e ekleyin:", "grey"))
    print(_c(f"  {rules_path}", "grey"))
    return 0


# ---------- rules ----------

def cmd_rules(args):
    rules = load_rules(args)
    if rules is None:
        return 1
    from .rules import DEFAULT_RULES
    print(f"{_c('Kural dosyası:', 'cyan', True)} {getattr(args, 'rules', None) or DEFAULT_RULES}")
    print(f"  {len(rules.dir_structure)} kategori · {len(rules.all_keywords())} anahtar kelime\n")
    for code, path, label in rules.categories():
        print(f"  {_c(code, 'cyan'):<32} {path}")
        if args.keywords:
            words = rules.keyword_map.get(code, {})
            if words:
                top = sorted(words.items(), key=lambda kv: -kv[1])
                line = ", ".join(f"{w}({s})" for w, s in top)
                print(f"      {_c(line, 'grey')}")
    return 0


# ---------- tek seferlik arama ----------

def cmd_oneshot(args, cfg, query):
    if not cfg["archive_dir"] or not os.path.isdir(cfg["archive_dir"]):
        _err(f"Arşiv dizini bulunamadı: {cfg['archive_dir'] or '(ayarlanmamış)'}")
        return 1

    results, backend = search_mod.search(
        cfg, query, content=args.content, category=args.category, limit=cfg["limit"])

    if args.ai and results:
        try:
            provider = ai_mod.get_provider(cfg["ai_model"])
        except ai_mod.AIError as e:
            _err(str(e))
            return 1
        azami = cfg["ai_max_candidates"]
        subset = results if not azami else results[:azami]
        is_tty = sys.stderr.isatty()

        def progress(i, total, name):
            if is_tty:
                print(f"\r  AI analizi {i}/{total}…", end="", file=sys.stderr, flush=True)

        ai_mod.rank(provider, query, subset,
                    lambda r: search_mod.preview_text(cfg, r, 2500), progress)
        if is_tty:
            print("\r" + " " * 40 + "\r", end="", file=sys.stderr)
        results = subset + ([] if not azami else results[azami:])

    if args.json:
        import json
        print(json.dumps([{
            "path": r.path, "relpath": r.relpath, "name": r.name,
            "category": r.category, "subcategory": r.subcategory,
            "size": r.size, "pages": r.pages,
            "matched_content": r.matched_content,
            "snippet": r.snippet.replace("\x01", "[").replace("\x02", "]"),
            "ai_score": r.ai_score, "ai_reason": r.ai_reason,
        } for r in results], ensure_ascii=False, indent=2))
        return 0 if results else 1

    if not results:
        print(_c(f"'{query}' için sonuç bulunamadı.", "yellow"))
        return 1

    src = {"index": "indeks", "index-or": "indeks, gevşek eşleşme",
           "live": "canlı tarama"}.get(backend, backend)
    print(_c(f"\n'{query}' için {len(results)} sonuç ({src}):\n", "green", True))
    for i, r in enumerate(results, 1):
        num = _c(f"[{i}]", "cyan")
        line = f"  {num} {r.relpath}"
        if r.ai_score:
            color = "green" if r.ai_score >= 7 else "yellow" if r.ai_score >= 4 else "red"
            line += "  " + _c(f"AI {r.ai_score}/10", color, True)
        print(line)
        if r.ai_reason and r.ai_score:
            print("      " + _c(r.ai_reason, "grey"))
        elif r.snippet.strip():
            snip = r.snippet.replace("\x01", "").replace("\x02", "")
            print("      " + _c(" ".join(snip.split())[:150], "grey"))
    print()
    return 0


# ---------- giriş noktası ----------

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    first_positional = next((a for a in argv if not a.startswith("-")), None)

    if first_positional not in COMMANDS:
        # Alt komut yok: kalan her şey arama sorgusu
        args = build_parser(with_subcommands=False).parse_args(argv)
        args.command = None
        return _run_search(args)

    args = build_parser().parse_args(argv)

    if args.command == "index":
        return cmd_index(args)
    if args.command == "config":
        return cmd_config(args)
    if args.command == "organize":
        return cmd_organize(args)
    if args.command == "duplicates":
        return cmd_duplicates(args)
    if args.command == "keywords":
        return cmd_keywords(args)
    if args.command == "rules":
        return cmd_rules(args)
    if args.command == "keys":
        return cmd_keys(args)
    if args.command == "models":
        return cmd_models(args)
    return 0


def cmd_keys(args):
    """API anahtarlarını gösterir, ekler, siler veya dener."""
    if args.set_provider:
        return _keys_set(args.set_provider)
    if args.remove_provider:
        spec = providers.PROVIDERS[args.remove_provider]
        if keys_mod.remove(args.remove_provider):
            print(_c(f"{spec.label} anahtarı silindi.", "green"))
            return 0
        _err(f"{spec.label} için kayıtlı anahtar yok.")
        return 1

    print(f"{_c('Anahtar dosyası:', 'cyan', True)} {keys_mod.KEYS_PATH}"
          f"{'' if os.path.exists(keys_mod.KEYS_PATH) else _c('  (henüz yok)', 'grey')}\n")

    eksik = []
    for ad, spec, anahtar, kaynak in keys_mod.durum():
        if anahtar:
            isaret = _c("✓", "green", True)
            deger = _c(keys_mod.maskele(anahtar), "green")
            nere = _c(f"({kaynak})", "grey")
        else:
            isaret = _c("·", "grey")
            deger = _c("yok", "grey")
            nere = ""
            eksik.append((ad, spec))
        print(f"  {isaret} {_c(spec.label.ljust(16), None, True)} {deger:<22} {nere}")
        print(f"    {_c(spec.free_note, 'grey')}")

    if args.test:
        print()
        return _keys_test()

    if eksik:
        print(_c("\nAnahtarı olmayan sağlayıcılar:", "yellow", True))
        for ad, spec in eksik:
            print(f"  {spec.label:<16} {_c(spec.signup_url, 'blue')}")
            print(f"    {_c(f'shelf keys --set {ad}', 'grey')}")
    return 0


def _keys_set(saglayici):
    import getpass

    spec = providers.PROVIDERS[saglayici]
    print(f"{_c(spec.label, 'cyan', True)}")
    print(f"  {spec.free_note}")
    print(f"  Anahtar alın: {_c(spec.signup_url, 'blue')}\n")
    if not sys.stdin.isatty():
        _err("Anahtar girişi terminal gerektirir.")
        return 1
    try:
        anahtar = getpass.getpass(f"{spec.env_var} (girdi gizlidir): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nİptal edildi.")
        return 1
    if not anahtar:
        _err("Boş anahtar — bir şey kaydedilmedi.")
        return 1
    yol = keys_mod.set_(saglayici, anahtar)
    print(_c(f"Kaydedildi: {yol}", "green", True) + _c("  (izin 0600)", "grey"))

    print("Deneniyor...", end=" ", flush=True)
    ok, mesaj = _dene(saglayici)
    print(_c("çalışıyor", "green", True) if ok else _c(mesaj, "red"))
    if ok:
        varsayilan = providers.format_model(saglayici, spec.default_model) \
            if spec.default_model else None
        if varsayilan:
            print(_c(f"  Kullanmak için: shelf config --model {varsayilan}", "grey"))
        else:
            print(_c(f"  Model seçmek için: shelf models -p {saglayici} --free", "grey"))
    return 0 if ok else 1


def _dene(saglayici):
    """Sağlayıcıya küçük bir istek atar. (basarili, mesaj) döner."""
    spec = providers.PROVIDERS[saglayici]
    anahtar = keys_mod.get(saglayici)
    if not anahtar:
        return False, "anahtar yok"
    try:
        model = providers.canli_model_sec(saglayici, anahtar, spec.default_model)
    except Exception as e:
        return False, ai_mod.explain(e)
    try:
        p = providers.build(saglayici, anahtar, model)
        yanit = ai_mod.complete(p, "Yalnızca 'tamam' yaz.", retries=1)
        return bool(yanit), yanit[:40] or "boş yanıt"
    except Exception as e:
        return False, ai_mod.explain(e, locals().get("p"))


def _keys_test():
    kayitli = [(ad, spec) for ad, spec, k, _ in keys_mod.durum() if k]
    if not kayitli:
        _err("Kayıtlı anahtar yok.")
        return 1
    print(_c("--- Anahtar denemesi ---", "cyan", True))
    hata = 0
    for ad, spec in kayitli:
        print(f"  {spec.label:<16} ", end="", flush=True)
        ok, mesaj = _dene(ad)
        if ok:
            print(_c("✓ çalışıyor", "green"))
        else:
            print(_c(f"✗ {mesaj}", "red"))
            hata += 1
    return 1 if hata else 0


def cmd_models(args):
    """Sağlayıcıların model listesini çeker."""
    if args.provider:
        hedefler = [args.provider]
    else:
        hedefler = [ad for ad, _, k, _ in keys_mod.durum() if k]
        if not hedefler:
            _err("Hiçbir sağlayıcı için anahtar yok.")
            print("  'shelf keys' ile durumu görün.", file=sys.stderr)
            return 1

    cfg = config_mod.load()
    etkin_s, etkin_m = providers.parse_model(cfg.get("ai_model"))
    hata = 0

    for ad in hedefler:
        spec = providers.PROVIDERS[ad]
        anahtar = keys_mod.get(ad)
        print(f"\n{_c(spec.label, 'cyan', True)}  {_c(spec.base_url, 'grey')}")
        if not anahtar:
            print(_c(f"  anahtar yok — shelf keys --set {ad}", "yellow"))
            hata += 1
            continue
        try:
            p = providers.build(ad, anahtar, spec.default_model or "x")
            modeller = p.list_models()
        except Exception as e:
            print(_c(f"  liste alınamadı — {ai_mod.explain(e)}", "red"))
            hata += 1
            continue

        if not args.all:
            modeller = [m for m in modeller if providers.looks_like_chat_model(m)]
        if args.free:
            modeller = [m for m in modeller if providers.is_free(ad, m)]
        if not modeller:
            print(_c("  (eşleşen model yok)", "grey"))
            continue

        for m in modeller:
            bedava = providers.is_free(ad, m)
            etiket = _c(" ücretsiz", "green") if bedava else ""
            onerilen = _c(" ★", "yellow") if m in spec.recommended else ""
            simdiki = _c(" ← etkin", "magenta", True) if (ad == etkin_s and m == etkin_m) else ""
            print(f"  {providers.format_model(ad, m)}{etiket}{onerilen}{simdiki}")
        print(_c(f"  {len(modeller)} model", "grey"))

    print(_c("\nSeçmek için: shelf config --model SAGLAYICI:MODEL", "grey"))
    return 1 if hata and len(hedefler) == hata else 0


def _run_search(args):
    cfg = resolve_cfg(args)
    query = args.oneshot if args.oneshot is not None else " ".join(args.terms)

    if args.oneshot is not None or args.json:
        if not query.strip():
            _err("Arama sorgusu boş.")
            return 1
        return cmd_oneshot(args, cfg, query)

    # İnteraktif mod
    if not cfg["archive_dir"] or not os.path.isdir(cfg["archive_dir"]):
        _err(f"Arşiv dizini bulunamadı: {cfg['archive_dir'] or '(ayarlanmamış)'}")
        print("  'shelf config --archive /yol/to/arsiv' ile ayarlayın.", file=sys.stderr)
        return 1
    if not sys.stdout.isatty():
        _err("İnteraktif mod bir terminal gerektirir. Tek seferlik arama için -q kullanın.")
        return 1

    from . import tui
    tui.run(cfg, query=query, content=args.content, ai=args.ai)
    return 0
