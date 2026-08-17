# Kullanım kılavuzu

## İçindekiler

- [Kavramlar](#kavramlar)
- [İndeks](#indeks)
- [Arama](#arama)
- [İnteraktif arayüz](#interaktif-arayuz)
- [organize — dökümanları yerleştirme](#organize--dokumanlari-yerlestirme)
- [duplicates — kopya bulma](#duplicates--kopya-bulma)
- [keywords — kural önerisi](#keywords--kural-onerisi)
- [Ayarlar](#ayarlar)
- [Sorun giderme](#sorun-giderme)

## Kavramlar

**Arşiv**, dökümanlarınızın bulunduğu kök dizindir. `shelf` bu dizinin altındaki
klasör yapısını kategori olarak yorumlar: ilk seviye ana kategori, ikinci seviye
alt kategoridir.

```
arsiv/
├── 01_OFANSIF_GUVENLIK/
│   ├── 02_Ag_Sizma_Testleri/     ← alt kategori
│   └── 04_Active_Directory/
└── 02_DEFANSIF_GUVENLIK/
    └── 01_SOC_ve_Olay_Mudahelesi/
```

**İndeks**, dökümanlardan çıkarılmış metnin arama için saklandığı SQLite
veritabanıdır. Arşivin kendisine dokunmaz, `~/.local/share/shelf/index.db`
altında durur ve istediğiniz zaman silinip yeniden kurulabilir.

## İndeks

```bash
shelf index              # kurar veya değişenleri günceller
shelf index --rebuild    # sıfırdan kurar
shelf index --info       # durumunu gösterir
shelf index -v           # her dosyayı tek tek listeler
```

Artımlı çalışır: bir dosyanın değişiklik zamanı indekstekiyle aynıysa dosya
yeniden okunmaz. Bu yüzden arşive birkaç döküman ekledikten sonraki `shelf index`
çağrısı saniyenin altında biter.

Arşivden silinmiş dosyaların kayıtları da bu sırada indeksten düşürülür.

Bir PDF'ten en fazla `index_max_pages` sayfa ve `index_max_chars` karakter okunur.
Varsayılanlar (40 sayfa / 60.000 karakter) tipik bir kitabın konusunu belirlemeye
fazlasıyla yeter ve indeksi makul boyutta tutar.

## Arama

### Tek seferlik

```bash
shelf -q kerberos                  # dosya adı ve yolunda arar
shelf -q kerberos -c               # döküman içeriğinde de arar
shelf -q "golden ticket" -c        # birebir ifade
shelf -q "sql injection" -n 50     # en fazla 50 sonuç
shelf -q xss --json                # JSON çıktı
```

**Terim mantığı:** birden çok terim verildiğinde hepsini birden içeren dökümanlar
aranır. Hiçbiri bulunamazsa arama otomatik olarak "terimlerden herhangi biri"ne
gevşer ve çıktıda `gevşek eşleşme` diye belirtilir. Bu, Türkçe sorguların İngilizce
dökümanlarda boş dönmesini engeller.

**Kategori sınırlama:**

```bash
shelf -q forensics -c -k 02_DEFANSIF_GUVENLIK_'(BLUE_TEAM)'
```

Kategori adı arşivdeki klasör adının aynısıdır; `shelf rules` ile listeleyebilirsiniz.

### AI ile sıralama

```bash
shelf -q "domain controller ele geçirme" -c --ai
```

Bulunan ilk `ai_max_candidates` (varsayılan 20) döküman AI'a gönderilir, her biri
1–10 arası puanlanır ve gerekçesiyle birlikte puana göre sıralanır. Sorgunuzu
Türkçe yazabilirsiniz; gerekçeler de Türkçe döner.

Bu işlem döküman başına bir API çağrısı yapar. Geniş sonuç kümelerinde önce `-n`
ile aday sayısını daraltmak hem hızlı hem ucuzdur.

### JSON çıktı

`--json` her sonucu tam yol, kategori, boyut, sayfa sayısı, eşleşme parçası ve
(varsa) AI puanıyla birlikte verir. Sonuç bulunamazsa çıkış kodu 1'dir, bu da
kabuk betiklerinde koşul olarak kullanılabilir:

```bash
if shelf -q "CVE-2021-44228" -c --json > sonuc.json; then
    jq -r '.[].path' sonuc.json
fi
```

## İnteraktif arayüz

Argümansız `shelf` (veya `shelf <sorgu>`) tam ekran arayüzü açar.

**Düzen:** solda kategori ağacı ve dosya sayıları, ortada sonuçlar, sağda seçili
dökümanın önizlemesi. Arama kutusuna yazdıkça sonuçlar daralır.

**Gezinme:** `↑` `↓` odak arama kutusundayken bile sonuçlar arasında gezer, böylece
yazmayı bırakmadan listede dolaşabilirsiniz. `Tab` panellere geçer.

**Kategori filtresi:** soldaki ağaçtan bir dal seçtiğinizde arama o dala daralır.
`Esc` filtreyi temizler, ikinci `Esc` arama kutusuna döner.

**Arka plan işleri:** arama, önizleme yükleme, indeksleme ve AI analizi ayrı
iş parçacıklarında çalışır; hiçbiri arayüzü kilitlemez. Durum çubuğu o an ne
yapıldığını gösterir.

Kısayolların tam listesi için `F1`.

## organize — dökümanları yerleştirme

```bash
shelf organize ~/Indirilenler -n              # kuru çalıştırma: ne olacağını göster
shelf organize ~/Indirilenler                 # arşive kopyala
shelf organize ~/Indirilenler --move          # kopyalamak yerine taşı
shelf organize ~/Indirilenler --rename        # dosya adlarını da AI yazsın
shelf organize ~/Indirilenler --no-ai         # sadece kural puanlaması kullan
shelf organize ~/Indirilenler -r              # alt klasörleri de tara
shelf organize ~/Indirilenler -t /baska/yol   # başka bir hedefe yerleştir
```

**Karar zinciri**, her döküman için sırayla:

1. Dosya adı ve içerikten anahtar kelime puanı hesaplanır.
2. Puan eşiğin (`organize_threshold`, varsayılan 15) üstündeyse kategori budur.
3. Değilse döküman AI'a gönderilir, kategori kodu sorulur.
4. AI da karar veremezse döküman `KATEGORISIZ` klasörüne gider.

Çıktıda her dosyanın kararını kimin verdiği görünür: `[kural]`, `[AI]` veya `[?]`.

**Güvenlik davranışları:**

- Varsayılan işlem kopyalamadır, taşıma değil. Kaynak dizin olduğu gibi kalır.
- Hedefte aynı adla bir dosya varsa içerikleri karşılaştırılır. Birebir aynıysa
  işlem atlanır ve `kopya` olarak sayılır; farklıysa yeni dosyanın adına zaman
  damgası eklenir. Aynı komutu iki kez çalıştırmak arşivi bozmaz.
- `-n` hiçbir dosyaya dokunmadan tüm planı gösterir.

Hedef, ayarlardaki arşiv dizini ise işlem sonunda indeks otomatik güncellenir
(`--no-reindex` ile kapatılabilir).

## duplicates — kopya bulma

```bash
shelf duplicates                 # kopyaları listele
shelf duplicates -d /baska/yol   # başka bir dizini tara
shelf duplicates --all-files     # sadece dökümanları değil her dosyayı tara
shelf duplicates --prune -n      # neyin silineceğini göster
shelf duplicates --prune         # fazlalıkları sil (onay ister)
```

Önce dosyalar boyutlarına göre gruplanır; boyutu benzersiz olan bir dosyanın
kopyası olamayacağı için yalnızca aynı boyuttaki adaylar okunup SHA-256'lanır.
Bu yüzden gigabaytlarca arşivde tarama saniyeler sürer.

Her grupta **saklanacak** dosya, yolu en kısa ve adı en sade olandır. `--prune`
kalanları siler; silmeden önce listeyi gösterir ve `evet` yazmanızı ister.
Terminal dışı bir ortamda (betik, boru hattı) onay alınamayacağı için işlem
reddedilir.

## keywords — kural önerisi

```bash
shelf keywords                   # dosya adlarından
shelf keywords --content         # indekslenmiş döküman içeriklerinden de
shelf keywords --top 60          # daha fazla aday
shelf keywords --min-count 5     # en az 5 dosyada geçenler
```

Kural puanı eşiğin altında kalan dökümanlar süzülür, bunlarda sık geçen ama kural
setinde bulunmayan terimler sayılır. Yaygın yayın terimleri ("handbook", "module",
"chapter") ve arşivin kendi dosya adı önekleri (kategori kodlarından türetilir)
elenir.

Beğendiğiniz terimleri `shelflib/rules.json` içindeki ilgili kategorinin
`KEYWORD_MAP` bölümüne bir puanla ekleyin; puanlamanın nasıl çalıştığı için
[kurallar.md](kurallar.md).

## Ayarlar

```bash
shelf config --show
shelf config --archive ~/arsiv
shelf config --model gemini-flash-latest
shelf config --index-path /baska/yol/index.db
shelf config --limit 100
```

Ayarlar `~/.shelfrc` içinde JSON olarak durur; yalnızca varsayılandan farklı
olanlar yazılır, dolayısıyla dosya kısa kalır ve varsayılanlar sürümle birlikte
güncellenir.

Tek seferlik geçersiz kılmalar için komut satırı bayrakları kullanılabilir:
`-d/--dir` arşiv dizinini, `-m/--model` modeli, `-n/--limit` sonuç sayısını,
`--threshold` düzenleme eşiğini o çalıştırma için değiştirir.

## Sorun giderme

**"command not found: shelf"** — zsh komut yollarını önbelleğe alır; açık bir
oturumda bir kez `rehash` yazın.

**"Arşiv dizini bulunamadı"** — `shelf config --archive /yol/to/arsiv` ile tanıtın.

**"İndeks yok" uyarısı** — `shelf index` çalıştırın. İndeks olmadan da arama
yapılır ama her sorguda disk taranır ve içerik araması çok yavaştır.

**"API kotası aşıldı"** — Google AI Studio'nun ücretsiz katmanı dakika ve gün
başına istek sınırı koyar. Araç geçici hatalarda geri çekilerek yeniden dener;
sınır kalıcıysa AI adımı atlanır, arama ve kural puanlaması etkilenmez.

**"Model bulunamadı"** — modeller zamanla emekliye ayrılır. Kullanılabilir
modelleri listeleyip `shelf config --model <ad>` ile geçin.

**Metin çıkarılamayan PDF'ler** — taranmış (resim tabanlı) dökümanlarda metin
katmanı yoktur. Bunlar indekste yer alır ve dosya adıyla bulunur, ama içerik
aramasına girmez. `shelf index` kaç dosyada bu durumun oluştuğunu bildirir; bu
dosyalara OCR uygulamak ayrı bir iştir.
