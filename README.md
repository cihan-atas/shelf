# shelf

Yerel bir siber güvenlik döküman arşivini aranabilir, düzenli ve gezilebilir hâle
getiren terminal aracı. Binlerce PDF'i saniyeler içinde tam metin arar, tam ekran
bir arayüzde gezdirir ve yeni gelen dökümanları kural + yapay zekâ ile kategorilere
yerleştirir.

```
┌─ shelf ───────────────────────────────────────────────┐
│ Ara: kerberos▏                          [AI ✓] 12 sonuç│
├────────────────┬──────────────────────┬───────────────┤
│ ▸ 01 OFANSIF   │ ▶ Kerberoasting.pdf  │ ÖNİZLEME      │
│   ▸ 04 AD  (50)│   AD_Attacks.pdf     │               │
│ ▸ 02 DEFANSIF  │   Golden_Ticket.pdf  │ Kerberos is a │
│ ▸ 03 TEMEL     │   Rubeus_Guide.pdf   │ network auth  │
│ ▸ 04 SERTIFIKA │   ...                │ protocol...   │
│                │                      │ ─────────────  │
│                │                      │ AI: 9/10      │
├────────────────┴──────────────────────┴───────────────┤
│ ↑↓ gez  ⏎ aç  ^A AI  F2 içerik  F5 indeks  ? yardım   │
└───────────────────────────────────────────────────────┘
```

## Ne yapar

- **Tam metin arama** — PDF içeriklerini SQLite FTS5 indeksine alır. 1180 dökümanlık
  bir arşivde içerik araması ~0.15 saniye sürer.
- **Tam ekran arayüz** — yazdıkça daralan sonuçlar, kategori ağacı, yan panelde
  döküman önizlemesi, aranan terimlerin vurgulanması.
- **AI ile anlamsal sıralama** — sonuçları "bu sorguya ne kadar uyuyor" diye
  puanlatıp yeniden sıralar, gerekçesini yazar.
- **Otomatik düzenleme** — yeni dökümanları ağırlıklı anahtar kelime puanlamasıyla
  kategorilere yerleştirir; puan zayıfsa kararı AI'a devreder, isteğe bağlı olarak
  dosya adlarını da yeniden yazar.
- **Kopya bulma** — aynı içerikli dosyaları tespit eder. Önce boyuta göre eleyip
  yalnızca adayları okuduğu için gigabaytlarca arşivde bile saniyeler sürer.
- **Kural önerisi** — hiçbir kategoriye oturmayan dosyalardan sık geçen terimleri
  çıkarıp kural setine eklenecek adayları listeler.

Arama ve düzenlemenin kural tarafı **API anahtarı olmadan da tam olarak çalışır**;
anahtar yalnızca AI özelliklerini açar.

## Kurulum

```bash
git clone https://github.com/cihan-atas/shelf.git
cd shelf

python3 -m venv shelf-env
./shelf-env/bin/pip install -r requirements.txt

# Her yerden çağırabilmek için
ln -s "$PWD/shelf" ~/.local/bin/shelf
```

`shelf` betiği yanındaki `shelf-env/` sanal ortamını kendisi bulur; sembolik
bağlantı üzerinden çağrıldığında da doğru dizini çözer. Sanal ortam yoksa sistem
`python3`'üne düşer.

AI özelliklerini kullanacaksanız:

```bash
cp .env.example .env
$EDITOR .env          # GOOGLE_API_KEY satırını doldurun
```

## İlk çalıştırma

```bash
shelf config --archive ~/arsiv    # arşiv dizinini bir kez tanıt
shelf index                       # dökümanları indeksle
shelf                             # arayüzü aç
```

İndeksleme 1180 PDF'lik bir arşivde ~85 saniye sürer. Sonraki `shelf index`
çağrıları yalnızca değişen dosyaları işler ve saniyenin altında biter.

## Kullanım

### İnteraktif arayüz

`shelf` yazıp Enter'a basın, sonra aramaya başlayın.

| Tuş | İşlev |
|---|---|
| `↑` `↓` | Sonuçlar arasında gezinir (arama kutusundayken de çalışır) |
| `Enter` | Seçili dökümanı varsayılan uygulamada açar |
| `F2` | İçerik aramasını açar/kapatır (dosya adı ↔ döküman içeriği) |
| `Ctrl+A` | Sonuçları AI ile alaka puanına göre sıralar |
| `F5` | Arşivi yeniden indeksler |
| `Ctrl+O` | Seçili dosyanın klasörünü açar |
| `Ctrl+Y` | Seçili dosyanın tam yolunu panoya kopyalar |
| `Esc` | Arama kutusuna döner / kategori filtresini temizler |
| `F1` veya `?` | Yardım ekranı |
| `Ctrl+C` | Çıkış |

Soldaki ağaçtan bir kategori seçerek aramayı o dala daraltabilirsiniz.

> `Ctrl+T` ve `Ctrl+R` de sırasıyla içerik ve indeksleme kısayollarıdır, ancak
> birçok terminal emülatörü bu tuşları kendisi kullandığı için uygulamaya
> ulaşmayabilir. `F2` ve `F5` her yerde çalışır.

### Komut satırı

```bash
shelf kerberos                     # arayüzü bu sorguyla açar
shelf -q kerberos                  # tek seferlik arama, basar ve çıkar
shelf -q "CVE-2021-44228" -c       # içerikte arar
shelf -q "domain controller" --ai  # AI sıralamalı
shelf -q ldap --json               # script/pipe için JSON çıktı
shelf -q xss -k 01_OFANSIF_GUVENLIK_'(RED_TEAM)'   # kategoriyle sınırlar
```

Birden çok terim verildiğinde hepsini birden içeren dökümanlar aranır. Hiçbiri
bulunamazsa arama otomatik olarak "terimlerden herhangi biri"ne gevşer ve bunu
çıktıda belirtir. Tırnak içindeki ifadeler birebir aranır.

### Arşiv bakımı

```bash
shelf organize ~/Indirilenler      # dökümanları kategorilere yerleştirir
shelf organize ~/Indirilenler -n   # önce ne yapacağını gösterir
shelf organize ~/Indirilenler --move --rename
shelf duplicates                   # kopya dosyaları bulur
shelf duplicates --prune -n        # fazlalıkları listeler (silmez)
shelf keywords --content           # yeni kural adayları önerir
shelf rules -k                     # kategori şemasını ve kurallarını gösterir
```

`organize` varsayılan olarak **kopyalar**, taşımaz; `--move` ile taşır. Her zaman
önce `-n` (kuru çalıştırma) ile ne olacağını görün. `duplicates --prune` gerçekten
siler ve onay ister.

Ayrıntılar için [docs/kullanim.md](docs/kullanim.md).

## Nasıl çalışır

| Katman | Dosya | Sorumluluk |
|---|---|---|
| Başlatıcı | `shelf` | Sanal ortamı bulur, paketi çalıştırır |
| Ayarlar | `shelflib/config.py` | `~/.shelfrc`, arşiv yolu tespiti |
| İndeks | `shelflib/index.py` | SQLite FTS5, artımlı güncelleme |
| Arama | `shelflib/search.py` | İndeksli ve indekssiz arka uçlar |
| Kurallar | `shelflib/rules.py` | Kategori şeması, ağırlıklı puanlama |
| Düzenleme | `shelflib/organize.py` | Kategorilendirme, yeniden adlandırma |
| Kopyalar | `shelflib/duplicates.py` | Boyut eleme + SHA-256 |
| Kural önerisi | `shelflib/keywords.py` | Terim çıkarımı |
| AI | `shelflib/ai.py` | Sağlayıcı arayüzü, yeniden deneme |
| Arayüz | `shelflib/tui.py` | Textual uygulaması |
| CLI | `shelflib/cli.py` | Argüman ayrıştırma, alt komutlar |

Mimari notları: [docs/mimari.md](docs/mimari.md).

## Kategori kuralları

Kategori şeması ve anahtar kelimeler `shelflib/rules.json` içinde durur: 29
kategori, 243 puanlı anahtar kelime. Kendi arşivinize uyarlamak için bu dosyayı
düzenleyin veya `--rules kendi_kurallarim.json` ile başkasını verin.

Puanlama, dosya adındaki eşleşmeleri içerikteki eşleşmelerden daha güçlü sayar ve
bir terimin metinde kaç kez geçtiğini kademeli bir çarpana çevirir. Kural puanı
eşiğin (varsayılan 15) altında kalırsa karar AI'a devredilir.

Ayrıntılar: [docs/kurallar.md](docs/kurallar.md).

## Ayarlar

`~/.shelfrc` (JSON). Yalnızca varsayılandan farklı olanlar yazılır.

| Anahtar | Varsayılan | Anlamı |
|---|---|---|
| `archive_dir` | otomatik tespit | Arşivin kök dizini |
| `index_path` | `~/.local/share/shelf/index.db` | İndeks veritabanı |
| `ai_model` | `gemini-flash-latest` | Kullanılacak model |
| `limit` | `200` | Maksimum sonuç sayısı |
| `ai_max_candidates` | `20` | AI'a gönderilecek en fazla aday |
| `organize_threshold` | `15` | Bu puanın altında karar AI'a geçer |
| `index_max_pages` | `40` | Bir PDF'ten okunacak en fazla sayfa |
| `index_max_chars` | `60000` | Bir dökümandan indekslenecek en fazla karakter |
| `extensions` | `.pdf .md .txt .epub` | İndekslenecek dosya türleri |

`shelf config --show` mevcut değerleri gösterir.

## Gereksinimler

- Python 3.9+
- PDF metin çıkarma için PyMuPDF
- AI özellikleri için bir Google AI Studio API anahtarı (isteğe bağlı)

Taranmış (resim tabanlı) PDF'lerden metin çıkarılamaz; bu dosyalar indekste yer
alır ama yalnızca dosya adıyla bulunur. `shelf index` kaç dosyada bu durumun
oluştuğunu bildirir.

## Bilinen sınırlar

- AI sağlayıcısı şimdilik yalnızca Google Gemini.
- Ücretsiz API kotası dar; çok sayıda dökümanı AI ile işlerken kota sınırına
  takılabilirsiniz. Araç bu durumda geri çekilerek yeniden dener ve sonunda
  anlaşılır bir mesaj verir, işlem kural puanlarıyla devam eder.
- Kategori kuralları Türkçe/İngilizce karışık bir siber güvenlik arşivi için
  yazıldı; başka bir alan için `rules.json` baştan yazılmalıdır.

## Lisans

MIT — bkz. [LICENSE](LICENSE).
