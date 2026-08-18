# -*- coding: utf-8 -*-
"""Konu bazlı ayrıntılı yardım metinleri.

`shelf --help` kısa kalsın diye derin anlatım buraya taşındı:
`shelf help` konuları listeler, `shelf help arama` konuyu açar.
"""

KONULAR = {}


def _konu(ad, baslik, ozet, metin):
    KONULAR[ad] = {"baslik": baslik, "ozet": ozet, "metin": metin.strip("\n")}


_konu("baslangic", "Sıfırdan kurulum", "İlk kez kullananlar için adım adım", """
1. ARŞİV DİZİNİNİ TANIT
   Belgelerinizin bulunduğu kök dizini bir kez ayarlayın:

     shelf config --archive ~/Documents/arsiv

   Alt klasör yapısı serbesttir; shelf ilk iki seviyeyi kategori olarak
   okur (ust_kategori/alt_kategori/belge.pdf).

2. İNDEKSİ KUR
   Bu adım PDF'lerin metnini çıkarıp aranabilir hale getirir:

     shelf index

   1180 belgelik 9 GB'lık bir arşivde ~85 saniye sürer. Sonraki
   çalıştırmalar yalnızca değişen dosyaları işler (saniyenin altında).

3. ARA
     shelf                      interaktif arayüz
     shelf kerberos             arayüzü bu sorguyla aç
     shelf -q kerberos          tek seferlik, terminale bas

4. (İSTEĞE BAĞLI) AI'I AÇ
   Ücretsiz bir sağlayıcı anahtarı ekleyin:

     shelf keys --set groq      https://console.groq.com/keys
     shelf keys --test          çalıştığını doğrula

   AI olmadan da arama, indeksleme ve kural tabanlı kategorilendirme
   tam olarak çalışır. AI yalnızca alaka sıralaması ve kuralın karar
   veremediği belgeler için devreye girer.
""")

_konu("arama", "Arama", "Ad araması, içerik araması, operatörler, limit", """
İKİ ARAMA KİPİ

  Ad araması (varsayılan)   Yalnızca dosya adlarına bakar. Çok hızlı.
  İçerik araması (-c)       Belge metninde arar. İndeks varsa yine hızlı
                            (1180 belgede ~0.15 sn).

    shelf -q kerberos              adlarda ara
    shelf -q kerberos -c           içerikte ara
    shelf -q "golden ticket" -c    çok kelimeli sorgu tırnak içinde

NASIL EŞLEŞİR

  Sorgudaki kelimelerin HEPSİNİ içeren belgeler önce aranır (AND).
  Hiç sonuç çıkmazsa otomatik olarak HERHANGİ BİRİNİ içerenlere
  geçilir (OR) ve çıktıda "gevşek eşleşme" yazar. Türkçe sorgularda
  bu sıkça devreye girer çünkü belgeler İngilizcedir.

  Türkçe karakterler normalleştirilir: "güvenlik" araması "guvenlik"
  yazan belgeleri de bulur.

SONUÇ SAYISI

    shelf -q pdf -c -n 20          ilk 20 sonuç
    shelf -q pdf -c -n hepsi       sınır yok
    shelf config --limit hepsi     kalıcı olarak sınırsız

KATEGORİYE DARALT

    shelf -q ldap -k 01_OFANSIF_GUVENLIK_(RED_TEAM)
    shelf rules                    kategori adlarını listeler

ÇIKTI BİÇİMİ

    shelf -q ldap --json           betiklerde işlemek için
    shelf -q ldap --json | jq -r '.[].path'

İNDEKS YOKSA
  shelf yine çalışır ama dosya sistemini tarar ("live" kipi) ve
  içerik araması çok yavaşlar. 'shelf index' önerilir.
""")

_konu("ai", "Yapay zeka", "Sağlayıcılar, anahtarlar, modeller, sıralama", """
AI NE YAPAR

  1. Alaka sıralaması (--ai): arama sonuçlarını okuyup 1-10 puanlar ve
     Türkçe gerekçe yazar. Sonuçlar puana göre yeniden sıralanır.
  2. Kategorilendirme yardımı: 'organize' sırasında kural puanı eşiğin
     altında kalan belgeler AI'a sorulur.
  3. Yeniden adlandırma (--rename): belgeye açıklayıcı bir ad üretir.

DÖRT SAĞLAYICI

  Groq         Ücretsiz katman, kredi kartı istemez, çok hızlı.
  OpenRouter   Adı ':free' ile biten modeller ücretsiz.
  Gemini       Ücretsiz katman, günlük/dakikalık istek sınırı sıkı.
  NVIDIA NIM   Kayıt sonrası ücretsiz kredi.

  Dördü de OpenAI uyumlu API sunduğu için tek istemciyle sürülür.

ANAHTAR YÖNETİMİ

    shelf keys                     durum tablosu + kayıt linkleri
    shelf keys --set groq          anahtarı gizli olarak sorar, kaydeder ve dener
    shelf keys --test              kayıtlı anahtarları gerçek istekle dener
    shelf keys --remove gemini     anahtarı siler

  Anahtarlar ~/.config/shelf/keys.env içinde 0600 izniyle durur.
  Arama sırası: ortam değişkeni > keys.env > proje .env dosyası.

MODEL SEÇİMİ

    shelf models                   anahtarı olan tüm sağlayıcıların modelleri
    shelf models -p openrouter --free   yalnızca ücretsizler
    shelf models -p groq -a        sohbet dışı modelleri de göster
    shelf config --model groq:openai/gpt-oss-20b

  Model referansı "saglayici:model" biçimindedir. Önek yazmazsanız
  varsayılan sağlayıcı kullanılır. ★ işareti önerilen modelleri,
  "ücretsiz" etiketi bedava olanları gösterir.

  Liste sohbete uygun olmayan modelleri (gömme, ses, görüntü, çeviri,
  robotik) otomatik eler; onlar sohbet uç noktasıyla çalışmaz.

AI SIRALAMASI

    shelf -q oscp -c --ai                 ilk 50 sonucu incele
    shelf -q oscp -c --ai --ai-limit 10   ilk 10
    shelf -q oscp -c --ai --ai-limit hepsi
    shelf config --ai-limit 50            kalıcı

  Not: metin katmanı olmayan (taranmış) PDF'ler puanlanamaz; AI'a
  gönderilecek içerik olmadığı için 0 puan alırlar.

KOTA
  Ücretsiz katmanlar sınırlıdır. Kota dolduğunda çıktıda açıkça
  yazar ve dosyalar kural puanına göre yerleştirilir. Başka bir
  sağlayıcıya geçmek için: shelf config --model <saglayici>:<model>
""")

_konu("duzenle", "Arşivi düzenleme", "organize: kategorilendirme ve adlandırma", """
NE YAPAR
  Dağınık bir dizindeki belgeleri okur, kategorilerine ayırır ve
  hedef arşivde uygun klasöre KOPYALAR (varsayılan davranış kopyalama,
  taşıma değil — kaynak olduğu gibi kalır).

ÖNCE KURU ÇALIŞTIRMA — HER ZAMAN

    shelf organize ~/Indirilenler -n

  Ne yapacağını gösterir, hiçbir dosyaya dokunmaz. Beğenirseniz -n'i
  kaldırın.

TEMEL KULLANIM

    shelf organize ~/Indirilenler                  kopyala
    shelf organize ~/Indirilenler -t ~/arsiv       hedefi belirt
    shelf organize ~/Indirilenler -r               alt klasörlere de in
    shelf organize ~/Indirilenler --move           kopyalamak yerine taşı

KARAR NASIL VERİLİR

  1. Belgenin ilk 10 sayfası / 8000 karakteri çıkarılır.
  2. 1459 anahtar kelime girdisi hem dosya adında hem metinde aranır.
     Ad eşleşmesi ağırlık x3, içerik eşleşmesi sıklığa göre x1/x2/x3.
  3. En yüksek puanlı kategori kazanır.
  4. Puan eşiğin (varsayılan 15) altındaysa karar AI'a devredilir.
     AI'a tüm metin değil, belgenin İÇİNDEKİLER'i gönderilir.
  5. AI da karar veremezse belge KATEGORISIZ'e düşer.

  1180 belgelik referans arşivde kural tek başına %94.6 isabet sağlar,
  yani AI'a yalnızca ~64 belge düşer.

EŞİK AYARI

    shelf organize ~/dizin --threshold 30    kural daha az karar versin
    shelf organize ~/dizin --no-ai           AI'a hiç sorma
    shelf organize ~/dizin --ai-only         kuralı yok say, hepsini AI'a sor

  --ai-only tavsiye edilmez: AI cevap veremediğinde geri dönülecek
  kural puanı olmadığı için belge doğrudan KATEGORISIZ'e düşer.

YENİDEN ADLANDIRMA

    shelf organize ~/dizin --rename

  Her belge için AI'dan açıklayıcı bir ad ister:
    VMware_Escape.pdf ->
    BULUT_SANALLASTIRMA_VMware_Workstation_UHCI_Controller_VM_Escape.pdf

  DİKKAT: --rename her belge için ayrı bir AI çağrısı demektir ve
  kategorilendirmenin kotasını tüketebilir. Büyük arşivlerde önce
  kategorilendirin, adlandırmayı ayrı bir koşuda yapın.

KURALLARI GÖRME VE DEĞİŞTİRME

    shelf rules                    kategori -> klasör eşlemesi
    shelf rules -k                 anahtar kelimeleri de göster
    shelf keywords                 kategorisiz belgelerden yeni kelime öner
    shelf organize ~/d --rules kendi.json    kendi kural dosyanız
""")

_konu("bakim", "Arşiv bakımı", "İndeks, kopyalar, anahtar kelime analizi", """
İNDEKS

    shelf index                    kur ya da güncelle (yalnızca değişenler)
    shelf index --rebuild          sıfırdan kur
    shelf index --info             durum: belge sayısı, boyut, tarih

  İndeks ~/.local/share/shelf/index.db içinde SQLite FTS5 tablosudur.
  Silmek zararsızdır, yeniden kurulabilir.

KOPYA DOSYALAR

    shelf duplicates               SHA-256 ile birebir kopyaları bul
    shelf duplicates --prune       kopyaları sil (onay ister)

  Önce boyuta göre grupladığı için 9 GB'lık arşivi ~0.15 sn'de tarar.
  --prune her grupta en iyi adlandırılmış dosyayı korur, kalanını
  siler; interaktif onay ister ve terminal yoksa çalışmayı reddeder.

ANAHTAR KELİME ANALİZİ

    shelf keywords                 kategorisiz belgelerde sık geçen
                                   kelimeleri bulur ve kural önerir
    shelf keywords --threshold 20  hangi belgelerin "kategorisiz"
                                   sayılacağını değiştirir

  Çıktıyı rules.json'a ekleyerek kural setini güçlendirebilirsiniz.
""")

_konu("kisayollar", "TUI kısayolları", "İnteraktif arayüzdeki tuşlar", """
  ↑ / ↓            Sonuçlar arasında gez (arama kutusundayken de çalışır)
  ⏎                Seçili belgeyi varsayılan uygulamada aç
  Tab / Shift+Tab  Paneller arasında geç
  Esc              Arama kutusuna dön / kategori filtresini temizle

  F1  ya da  ?     Bu yardım
  F2               İçerik araması aç/kapa
  F3               AI: sağlayıcı, anahtar, model, tarama sınırı
  F4               Arşivi düzenle (kategorilendirme, kuru çalıştırma)
  F5               Arşivi yeniden indeksle

  Ctrl+A           Sonuçları AI ile sırala
  Ctrl+O           Belgenin klasörünü dosya yöneticisinde aç
  Ctrl+Y           Belgenin tam yolunu panoya kopyala
  Ctrl+C           Çıkış

  Not: ctrl+q ve ctrl+t birçok terminal emülatöründe pencere/sekme
  kısayoludur ve uygulamaya ulaşmaz. Bu yüzden çıkış Ctrl+C'de,
  içerik araması F2'dedir. Terminaliniz izin veriyorsa eski tuşlar
  (ctrl+q, ctrl+t, ctrl+r) da çalışmaya devam eder.
""")

_konu("ayarlar", "Ayarlar", "~/.shelfrc ve tüm anahtarlar", """
    shelf config --show            mevcut ayarlar (* = varsayılandan farklı)

  archive_dir          Arşiv kök dizini
  index_path           İndeks veritabanı yolu
  extensions           İndekslenecek uzantılar (.pdf .md .txt .epub)
  index_max_chars      Belge başına indekslenecek azami karakter (60000)
  index_max_pages      Belge başına okunacak azami sayfa (40)
  limit                Arama sonuç sayısı (0 = sınırsız)
  ai_model             "saglayici:model" biçiminde etkin model
  ai_max_candidates    AI'ın inceleyeceği sonuç sayısı (0 = hepsi)
  organize_threshold   Kural puanı bu değerin altındaysa karar AI'a gider

  DEĞİŞTİRME

    shelf config --archive ~/arsiv
    shelf config --model groq:openai/gpt-oss-20b
    shelf config --limit hepsi
    shelf config --ai-limit 50
    shelf config --index-path /veri/shelf.db

  Ayar dosyası ~/.shelfrc, yalnızca varsayılandan farklı değerleri
  saklar. Silmek her şeyi varsayılana döndürür.

  API anahtarları burada DEĞİL, ~/.config/shelf/keys.env içinde
  0600 izniyle tutulur. Ayar dosyanızı paylaşabilirsiniz.
""")

_konu("sorun", "Sorun giderme", "Sık karşılaşılan hatalar", """
"Kaynak dizin bulunamadı" ama dizin var
  Tırnak İÇİNDE ters bölü kullanmayın. İkisinden biri:
    shelf organize "/yol/Siber güvenlik/arsiv"     (tırnak)
    shelf organize /yol/Siber\\ güvenlik/arsiv      (kaçış)

"Model bulunamadı"
  Sağlayıcı o modeli emekliye ayırmış olabilir:
    shelf models -p <saglayici>       canlı listeyi gör
    shelf config --model <yenisi>

"Kotası aşıldı"
  Ücretsiz katman doldu. Bekleyin ya da başka sağlayıcıya geçin:
    shelf keys --set groq
    shelf config --model groq:openai/gpt-oss-20b

Arama sonuç vermiyor
  İndeks kurulu mu:  shelf index --info
  İçerikte arıyor musunuz:  -c ekleyin
  Sonuç kesiliyorsa:  -n hepsi

Sadece 200 sonuç görünüyor
  Varsayılan limit 200'dür:  shelf config --limit hepsi

PDF'ten metin çıkmıyor
  Taranmış (görüntü) PDF'lerde metin katmanı yoktur. Bu belgeler
  yalnızca dosya adından kategorilendirilir ve AI ile puanlanamaz.
  Çözüm OCR'dir, shelf bunu yapmaz.

İnteraktif arayüz açılmıyor
  Terminal gerekir. Boru hattında/betikte -q kullanın:
    shelf -q sorgu
""")


_konu("indeks", "İndeks iç yapısı", "SQLite FTS5, tokenizer, sıralama", """
NEREDE
  ~/.local/share/shelf/index.db   (shelf config --index-path ile değişir)

  Silmek zararsızdır; 'shelf index' yeniden kurar. Arşivin kendisi asla
  değiştirilmez, indeks salt okunur bir türevdir.

ŞEMA
  files       path, relpath, name, category, subcategory, size, pages,
              mtime, sha (değişiklik tespiti için)
  files_fts   FTS5 sanal tablosu: name, relpath, content

  Tokenizer:  unicode61 remove_diacritics 2
  Bu ayar Türkçe için önemlidir: "güvenlik" ile "guvenlik", "İSTANBUL"
  ile "istanbul" aynı kabul edilir.

SIRALAMA
  bm25(files_fts, 12.0, 6.0, 1.0)

  Üç sayı üç kolonun ağırlığıdır: dosya adı 12, göreli yol 6, içerik 1.
  Yani sorgunun dosya adında geçmesi, içeride geçmesinden 12 kat
  değerlidir. Bu yüzden "kerberos" araması önce adında Kerberos geçen
  belgeleri getirir, sonra içinde geçenleri.

SORGU ÇEVİRİSİ
  Kullanıcı sorgusu doğrudan FTS5'e verilmez, güvenli bir ifadeye
  çevrilir. Her terim tırnağa alınıp yıldız eklenir:

    golden ticket        ->  "golden"* AND "ticket"*
    "golden ticket"      ->  "golden ticket"*        (tırnak korunur)
    CVE-2021-44228       ->  "CVE-2021-44228"*       (tire metin sayılır)

  Tırnağa alma, tire/iki nokta/yıldız gibi karakterlerin FTS5
  operatörü sanılmasını engeller. Yıldız önek eşleşmesi sağlar:
  "kerber"* araması Kerberos ve Kerberoasting'i bulur.

AND -> OR GERİ DÖNÜŞÜ
  Önce tüm terimleri içerenler aranır. Sonuç sıfırsa aynı sorgu OR ile
  tekrarlanır ve çıktıda "gevşek eşleşme" yazar. Türkçe sorgularda sık
  görülür çünkü belgeler İngilizcedir.

PARÇACIK (SNIPPET)
  snippet(files_fts, 2, ..., ' … ', 14)
  Eşleşen kelimenin çevresinden 14 kelimelik bağlam alınır ve eşleşen
  kısım vurgulanır. Yalnızca içerik kolonundan (2 numaralı) çıkarılır.

METİN ÇIKARMA SINIRLARI
  index_max_pages   40      belge başına okunacak sayfa
  index_max_chars   60000   belge başına saklanacak karakter

  Bu sınırlar bilinçlidir: 400 sayfalık bir kitabın tamamını
  indekslemek indeks boyutunu şişirir ve arama isabetini düşürür.
  İlk 40 sayfa genelde içindekiler + giriş içerir, konuyu belirlemeye
  yeter. Değiştirmek için ~/.shelfrc düzenlenir.

ARTIMLI GÜNCELLEME
  'shelf index' her dosyanın boyut ve değişiklik zamanına bakar;
  değişmeyenleri atlar. 1180 belgelik arşivde ilk kurulum ~85 sn,
  sonraki çalıştırmalar saniyenin altındadır.

İNDEKSSİZ ÇALIŞMA ("live" kipi)
  İndeks yoksa shelf dosya sistemini gezerek arar. Ad araması yine
  hızlıdır ama içerik araması her PDF'i tek tek açmak zorunda kalır
  ve dakikalar sürebilir. Çıktıda backend "live" olarak görünür.
""")

_konu("puanlama", "Kategori puanlaması", "Ağırlıklar, çarpanlar, eşik — matematiği", """
FORMÜL

  Her kategori için puan sıfırdan başlar. Kural dosyasındaki her
  anahtar kelime için:

    Dosya adında geçiyorsa   ->  puan += agirlik * 3
    İçerikte n kez geçiyorsa ->  puan += agirlik * siklik_bonusu(n)

  İkisi TOPLANIR, biri diğerinin yerine geçmez. Adında da içinde de
  geçen bir kelime iki kez katkı verir.

  siklik_bonusu(n):   n >= 10  ->  3
                      n >=  3  ->  2
                      aksi     ->  1

  En yüksek puanlı kategori kazanır. Eşitlikte kural dosyasındaki
  sıra belirleyicidir.

AĞIRLIK MANTIĞI
  Ağırlıklar ayırt ediciliğe göre elle verilmiştir:

    10   Sertifika/sınav kodları: oscp, ccna, sy0-701, cissp, sec560
         Başka hiçbir şeye benzemez, tek başına kesin karar verdirir.
     5-6 Çok özgül teknik terimler: kerberoasting, mimikatz, hashcat,
         process injection, maldev
     3-4 Alan terimleri: sql injection, forensics, wpa2, docker
     1-2 Genel kelimeler: security, hacking, network, cyber
         Her belgede geçer, tek başına bir şey söylemez.

  Bir sertifika kodu (10) dosya adında geçerse 10 x 3 = 30 puan
  yapar ve 15'lik eşiği tek başına geçer. Genel bir kelime (1)
  içerikte 2 kez geçerse 1 x 1 = 1 puan yapar, neredeyse etkisizdir.

AYIRICI NORMALLEŞTİRME
  Puanlamadan önce _ - . ( ) [ ] / , + karakterleri boşluğa çevrilir.
  Sebep: Python'un \b kelime sınırı alt çizgiyi harf sayar, bu yüzden
  "AD_PENTEST_Kerberoasting_Guide" içinde "kerberoasting" araması
  eşleşmezdi. Normalleştirme bunu çözer.

  Ayrıca çoğul toleransı vardır: kural setinde "forensic" varsa
  "forensics" de eşleşir (5 harften uzun, tek kelimelik terimlerde).

EŞİK
  organize_threshold varsayılan 15.

  Bu değer 1180 belgelik gerçek arşive karşı ölçülerek seçildi:
  15'te belgelerin %94.6'sına kural karar veriyor, %5.4'ü AI'a
  düşüyor. Eşiği yükseltmek AI'a daha çok iş verir (daha pahalı ama
  belirsiz vakalarda daha isabetli), düşürmek kurala daha çok güvenir.

    shelf organize ~/d --threshold 30
    shelf config --show     (organize_threshold satırı)

KURAL SETİ
  shelflib/rules.json — 35 kategori, 1459 kelime girdisi
  (1435 benzersiz; 24 kelime birden fazla kategoride farklı ağırlıkla
  geçer, örneğin "forensics" hem FORENSICS_MALWARE hem CERT_ECCOUNCIL
  altında bulunabilir).
  İki bölüm: DIR_STRUCTURE (kategori -> klasör yolu) ve
  KEYWORD_MAP (kategori -> {kelime: agirlik}).

    shelf rules            eşlemeyi göster
    shelf rules -k         kelimeleri de göster
    shelf organize ~/d --rules kendi.json
""")

_konu("dosyalar", "Dosya ve dizinler", "shelf'in diske yazdığı her şey", """
  ~/.shelfrc
      Yapılandırma. JSON. Yalnızca varsayılandan FARKLI değerleri
      saklar, bu yüzden genelde birkaç satırdır. Silmek her şeyi
      varsayılana döndürür. İçinde API anahtarı YOKTUR, paylaşılabilir.

  ~/.config/shelf/keys.env
      API anahtarları. Dosya izni 0600, dizin izni 0700.
      Biçim:  GROQ_API_KEY=gsk_...
      Atomik yazılır (önce .tmp, sonra rename), yarım dosya oluşmaz.
      ASLA paylaşmayın, depoya koymayın.

  ~/.local/share/shelf/index.db
      SQLite indeksi. Silmek zararsızdır.

  <proje>/shelflib/rules.json
      Kategori kuralları. Kendi kopyanızı --rules ile verebilirsiniz.

  ANAHTAR ARAMA SIRASI (ilki kazanır)
      1. Ortam değişkeni      GROQ_API_KEY, GOOGLE_API_KEY,
                              OPENROUTER_API_KEY, NVIDIA_API_KEY
      2. ~/.config/shelf/keys.env
      3. Eski .env dosyaları  (arşiv dizini, çalışma dizini, proje kökü)

      Üçüncü yol yalnızca geriye dönük uyumluluk içindir. Yeni
      kurulumlarda 'shelf keys --set' kullanın.

      Tek seferlik kullanım için:
        GROQ_API_KEY=gsk_... shelf -q oscp -c --ai

  ÇIKTI KODLARI
      0   başarılı
      1   hata (dizin yok, anahtar yok, geçersiz argüman, sonuç yok)

      Betiklerde:  shelf -q kerberos --json || echo "bulunamadı"
""")

_konu("bayraklar", "Tam bayrak referansı", "Her komut, her seçenek", """
ARAMA (alt komut yok)
  -q, --query SORGU     Tek seferlik arama; arayüz açmadan basar
  -c, --content         İçerikte ara (varsayılan: yalnızca dosya adı)
  -k, --category AD     Aramayı bir üst kategoriyle sınırla
  -n, --limit N         Azami sonuç ('hepsi' veya 0 = sınırsız)
  -d, --dir YOL         Bu arama için arşiv dizinini değiştir
      --ai              Sonuçları AI ile puanla ve yeniden sırala
      --ai-limit N      AI kaç sonucu incelesin ('hepsi' = tümü)
  -m, --model REF       Bu çalıştırma için model (saglayici:model)
      --json            JSON çıktı
  -V, --version         Sürüm

index
      --rebuild         İndeksi sıfırdan kur
      --info            Durum bilgisi (belge sayısı, boyut, tarih)

config
      --archive YOL     Arşiv kök dizini
      --index-path YOL  İndeks veritabanı yolu
      --model REF       Varsayılan AI modeli
      --limit N         Varsayılan sonuç limiti ('hepsi')
      --ai-limit N      Varsayılan AI inceleme sayısı ('hepsi')
      --show            Tüm ayarları göster

organize KAYNAK
  -t, --target YOL      Hedef arşiv (yoksa ayarlardaki archive_dir)
  -n, --dry-run         Kuru çalıştırma — hiçbir dosyaya dokunmaz
  -r, --recursive       Alt klasörleri de tara
      --move            Kopyalamak yerine taşı
      --rename          Adları AI ile yeniden üret
      --ai-only         Kural puanlamasını yok say, hepsini AI'a sor
      --no-ai           AI'a hiç sorma (yalnızca kural)
      --threshold N     Kural/AI devir eşiği
      --rules DOSYA     Alternatif kural dosyası
      --no-reindex      İşlem sonrası indeksi güncelleme
  -m, --model REF       Kullanılacak model

duplicates
      --prune           Kopyaları sil (onay ister)
  -d, --dir YOL         Taranacak dizin

keywords
      --threshold N     "Kategorisiz" sayılma eşiği
      --rules DOSYA     Kural dosyası

rules
  -k, --keywords        Her kategorinin anahtar kelimelerini de göster
      --rules DOSYA     Kural dosyası

keys
      --set SAGLAYICI     Anahtar ekle/güncelle (gizli giriş)
      --remove SAGLAYICI  Anahtarı sil
      --test              Kayıtlı anahtarları gerçek istekle dene

models
  -p, --provider AD     Yalnızca bu sağlayıcı
      --free            Yalnızca ücretsiz modeller
  -a, --all             Sohbet dışı modelleri de göster

help [KONU]             Konu listesi ya da konu metni
""")

_konu("guvenlik", "Güvenlik ve gizlilik", "Ne nereye gidiyor", """
AI'A NE GÖNDERİLİYOR
  Yalnızca AI özelliklerini kullandığınızda ve yalnızca şunlar:

    --ai ile arama      : dosya adı + belge özetinin ilk 2500 karakteri
    organize (kural yetmezse) : dosya adı + İÇİNDEKİLER (yoksa ilk
                          3000 karakter)
    --rename            : dosya adı + aynı özet + kategori kodu

  Belgenin tamamı hiçbir zaman gönderilmez. AI kapalıyken
  (--no-ai, ya da anahtar yoksa) hiçbir ağ isteği yapılmaz.

  Sağlayıcıların veri saklama politikaları kendilerine aittir.
  Hassas belgeler için --no-ai kullanın; arama, indeksleme ve kural
  tabanlı kategorilendirme tamamen yereldir.

ANAHTAR SAKLAMA
  ~/.config/shelf/keys.env, izin 0600 (yalnızca siz okuyabilirsiniz).
  Dizin izni 0700. Dosya atomik yazılır.
  Anahtarlar ekrana hiçbir zaman tam basılmaz, maskelenir: gsk_BS…zrBa
  'keys --set' girdiyi gizli okur, kabuk geçmişine düşmez.

  Anahtarı komut satırında ortam değişkeni olarak verirseniz kabuk
  geçmişinize yazılabilir; kalıcı kullanım için 'keys --set' tercih edin.

VERİ BÜTÜNLÜĞÜ
  organize varsayılan olarak KOPYALAR, taşımaz — kaynak korunur.
  --move açıkça istenmelidir.
  Hedefte aynı adda dosya varsa üzerine yazılmaz; içerik birebir
  aynıysa atlanır, farklıysa ad çakışması çözülür.

  duplicates --prune KALICI SİLME yapar:
    - yalnızca SHA-256'sı birebir aynı olan dosyaları gruplar
    - her gruptan birini korur (en kısa yol, sonra en kısa ad)
    - interaktif "evet" onayı ister
    - stdin bir terminal değilse çalışmayı reddeder (betikte kazara
      silme olmasın diye)

AĞ
  İstemci standart kütüphanenin urllib'idir; ek HTTP bağımlılığı yok.
  Zaman aşımı 90 saniye. Geçici hatalarda (429/500/502/503/504)
  2 ve 4 saniye bekleyerek en fazla 3 deneme yapılır.
""")

_konu("performans", "Performans", "Ölçülmüş rakamlar ve darboğazlar", """
  Aşağıdaki sayılar 1180 belgelik, 9.2 GB'lık gerçek bir arşivde
  ölçülmüştür (NVMe SSD, 8 çekirdek).

  İlk indeksleme            ~85 sn
  Artımlı indeksleme        < 1 sn (değişen yoksa)
  Ad araması                ~0.21 sn
  İçerik araması (indeks)   ~0.15 sn
  İçerik araması (indekssiz) dakikalar
  Kopya taraması            ~0.15 sn

  KOPYA TARAMASI NEDEN BU KADAR HIZLI
    9.2 GB'ın tamamını hash'lemek dakikalar sürerdi. Bunun yerine
    önce dosyalar BOYUTA göre gruplanır; tek başına kalan boyutlar
    kopya olamayacağı için hiç okunmaz. Yalnızca aynı boyutta birden
    fazla dosya varsa SHA-256 hesaplanır.

  ORGANIZE DARBOĞAZI
    AI değil, PDF metin çıkarma. 1180 belge için metin çıkarma
    25-40 dakika sürer; AI çağrıları (kuralın karar veremediği ~64
    belge) buna göre ihmal edilebilir.

    --rename bunu değiştirir: her belge için bir AI çağrısı demektir,
    yani 1180 çağrı. Ücretsiz katmanlarda kota bu noktada biter ve
    kategorilendirmenin çağrılarını da aç bırakır. Bu yüzden büyük
    arşivlerde kategorilendirme ile adlandırmayı AYRI koşularda yapın.

  AI HIZI (ölçülen)
    Groq openai/gpt-oss-120b    ~0.58 sn/istek
    Gemini 3.5-flash-lite       ~1.2 sn/istek
    Gemini 3.1-flash-lite       ~3.2 sn/istek

  İNDEKS BOYUTU
    index_max_chars 60000 ile 1180 belgelik arşiv ~40 MB'lık bir
    indeks üretir. Sınırı yükseltmek indeksi büyütür ve bm25
    sıralamasını genel kelimeler lehine bozabilir.
""")


GRUPLAR = [
    ("Başlarken", ["baslangic", "arama", "kisayollar"]),
    ("Günlük kullanım", ["ai", "duzenle", "bakim"]),
    ("Referans", ["bayraklar", "ayarlar", "dosyalar"]),
    ("Derinlemesine", ["indeks", "puanlama", "performans", "guvenlik"]),
    ("Yardım", ["sorun"]),
]


def konu_listesi():
    genislik = max(len(a) for a in KONULAR)
    satirlar = ["shelf — ayrıntılı yardım konuları", ""]
    for grup, adlar in GRUPLAR:
        satirlar.append(f"{grup}")
        for ad in adlar:
            veri = KONULAR.get(ad)
            if veri:
                satirlar.append(f"  {ad.ljust(genislik)}  {veri['ozet']}")
        satirlar.append("")
    # Gruplara girmemiş konu kalırsa yine de görünsün
    gruplu = {a for _, adlar in GRUPLAR for a in adlar}
    kalan = [a for a in KONULAR if a not in gruplu]
    if kalan:
        satirlar.append("Diğer")
        for ad in kalan:
            satirlar.append(f"  {ad.ljust(genislik)}  {KONULAR[ad]['ozet']}")
        satirlar.append("")
    satirlar += ["Kullanım:  shelf help <konu>",
                 "Örnek:     shelf help puanlama"]
    return "\n".join(satirlar)


def konu_metni(ad):
    veri = KONULAR.get(ad)
    if veri is None:
        return None
    cizgi = "─" * max(12, len(veri["baslik"]))
    return f"{veri['baslik']}\n{cizgi}\n\n{veri['metin']}"
