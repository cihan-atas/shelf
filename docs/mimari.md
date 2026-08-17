# Mimari notları

## Genel yapı

`shelf` bir POSIX kabuk betiği, gerçek uygulama `shelflib` paketidir.

```
shelf                 → shelf-env/bin/python -m shelflib "$@"
└── shelflib/
    ├── __main__.py   → cli.main()
    ├── cli.py        argüman ayrıştırma, alt komutlar, terminal çıktısı
    ├── tui.py        Textual uygulaması
    ├── search.py     arama arka uçları
    ├── index.py      SQLite FTS5 indeksi, metin çıkarma
    ├── rules.py      kategori şeması ve puanlama
    ├── organize.py   kategorilendirme ve yerleştirme
    ├── duplicates.py kopya tespiti
    ├── keywords.py   kural adayı çıkarımı
    ├── ai.py         AI sağlayıcı arayüzü
    ├── config.py     ~/.shelfrc
    └── rules.json    varsayılan kural seti
```

Başlatıcı betik kendi konumunu (sembolik bağlantıları çözerek) bulur, yanındaki
`shelf-env/` sanal ortamını arar, bulamazsa sistem `python3`'üne düşer ve paketin
bulunabilmesi için `PYTHONPATH`'i ayarlar. Kabuk betiği olması, dizin adında boşluk
ve Türkçe karakter bulunduğunda shebang'in kırılmasını önler.

## İndeks

SQLite FTS5 sanal tablosu, `unicode61 remove_diacritics 2` sözcükleyicisiyle:

```sql
CREATE TABLE files(id, path UNIQUE, relpath, name, category, subcategory,
                   ext, size, mtime, pages, chars, indexed_at);
CREATE VIRTUAL TABLE files_fts USING fts5(name, relpath, content,
                   tokenize='unicode61 remove_diacritics 2');
```

`files_fts.rowid` ile `files.id` eşleşir; metin verisi ve meta veri böylece ayrı
tutulur, meta veri üzerinde normal indeksler kullanılabilir.

**Artımlı güncelleme** dosyanın `mtime` değerine bakar. Değişmemiş dosya yeniden
okunmaz — PDF metin çıkarma pahalı olduğu için asıl kazanç buradadır. Diskten
silinmiş dosyaların kayıtları da her çalıştırmada düşürülür.

**Sıralama** `bm25(files_fts, 12.0, 6.0, 1.0)` ile yapılır: dosya adındaki
eşleşme yoldakinin iki katı, yoldaki eşleşme içeriktekinin altı katı ağırlıklıdır.

**Sorgu çevirisi** kullanıcı girdisini güvenli bir FTS5 `MATCH` ifadesine dönüştürür.
Her terim tırnak içine alınır — böylece `CVE-2021-44228` gibi girdilerdeki `-`
karakteri "hariç tut" operatörü olarak yorumlanmaz — ve sonuna `*` eklenerek önek
eşleşmesi sağlanır. Terimler önce `AND` ile bağlanır; sonuç boş dönerse aynı sorgu
`OR` ile tekrarlanır ve arayüz bunu "gevşek eşleşme" olarak bildirir.

## Arama arka uçları

İki arka uç aynı `Result` tipini döner:

- **`search_index`** — indeks varsa kullanılır, tek SQL sorgusu.
- **`search_live`** — indeks yoksa diski gezer. İçerik araması burada her dosyayı
  tek tek açtığı için çok yavaştır; yalnızca ilk kurulum öncesi için vardır.

Bu ayrım sayesinde araç indeks kurulmadan da çalışır, arayüz yalnızca durum
çubuğunda hangi arka ucun kullanıldığını gösterir.

## Arayüz

Textual uygulaması. Uzun süren her iş (`arama`, `önizleme`, `indeksleme`,
`AI analizi`) `@work(thread=True)` ile ayrı bir iş parçacığında çalışır ve
sonucunu `call_from_thread` ile arayüze aktarır; olay döngüsü hiç bloklanmaz.
İşler `exclusive=True` ve gruplandırılmış olduğundan, kullanıcı yazmaya devam
ettiğinde eski arama iptal edilir.

Arama girdisi 280 ms geciktirilir (`set_timer`), böylece her tuş vuruşu ayrı bir
sorgu başlatmaz.

**Sonuç satırları** genişliğe göre elle kısaltılır. Textual'ın `OptionList`'i
Rich'in `no_wrap` ayarını dikkate almadığı için, her satır widget'ın o anki
içerik genişliğine göre üç noktayla kesilir ve pencere yeniden boyutlandığında
liste yeniden çizilir.

**Kısayol çakışmaları:** `Input` widget'ı `ctrl+a` (satır başı) ve `ctrl+c`
(kopyala) tuşlarını kendi üzerine bağlar ve bu bağlar uygulama seviyesindeki
`priority` bağlarını gölgeler. Arama kutusu bu yüzden `Input`'tan türetilip iki
tuş açıkça geri alınır. Ayrıca `ctrl+q` ve `ctrl+t` birçok terminal emülatörü
tarafından pencere/sekme kısayolu olarak yakalandığından, birincil kısayollar
`ctrl+c` (çıkış) ve `F2`/`F5`'tir; eskileri gizli takma ad olarak durur.

## Puanlama

Anahtar kelime desenleri başlatmada bir kez derlenir. Dosya adı taranmadan önce
ayraçlar boşluğa çevrilir, çünkü regex'te `_` bir kelime karakteridir ve `\b`
sınırı `AD_PENTEST_Kerberos` içindeki terimi görmez.

Dosya adı eşleşmeleri sabit bir çarpanla, içerik eşleşmeleri geçiş sayısına bağlı
kademeli bir çarpanla ağırlıklandırılır. Ayrıntılar: [kurallar.md](kurallar.md).

## AI katmanı

`ai.py` sağlayıcıyı `complete(prompt) -> str` arayüzünün arkasına gizler. Üst
katmanlar (arama sıralaması, kategorilendirme, yeniden adlandırma) yalnızca bu
arayüzü bilir; yeni bir sağlayıcı eklemek `complete` uygulayan bir sınıf yazıp
`get_provider`'a bağlamaktan ibarettir.

`complete()` sarmalayıcısı geçici hatalarda (429, 503, zaman aşımı) 2 ve 4 saniye
bekleyerek yeniden dener. `explain()` istisnaları kullanıcıya gösterilecek kısa
Türkçe mesajlara çevirir. Kategorilendirme sırasında oluşan AI hataları yutulmaz,
toplanıp çalıştırma sonunda özetlenir — kullanıcı bir dökümanın neden kural
puanıyla yerleştiğini görebilir.

## Kopya tespiti

Naif yaklaşım her dosyayı hash'ler. Bunun yerine dosyalar önce boyuta göre
gruplanır: boyutu benzersiz olan bir dosyanın birebir kopyası olamaz, dolayısıyla
okunmasına gerek yoktur. Yalnızca aynı boyuttaki adaylar SHA-256'lanır. Zaten
tekilleştirilmiş bir arşivde bu, okunan veriyi gigabaytlardan birkaç megabayta
indirir.

## Test

Arayüz Textual'ın `run_test()` pilotuyla başsız sürülür: tuş basımları, arama
akışı, kategori filtresi, yardım ekranı ve boş sonuç durumu programatik olarak
doğrulanır. Kural puanlaması ise arşivin mevcut yerleşimine karşı ölçülür —
kuralın verdiği kategori ile dosyanın gerçekte bulunduğu klasör karşılaştırılarak
eşik kalibre edilir.
