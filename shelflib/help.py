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
  2. 1459 anahtar kelime hem dosya adında hem metinde aranır.
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


def konu_listesi():
    genislik = max(len(a) for a in KONULAR)
    satirlar = ["Ayrıntılı yardım konuları:", ""]
    for ad, veri in KONULAR.items():
        satirlar.append(f"  {ad.ljust(genislik)}  {veri['ozet']}")
    satirlar += ["", "Kullanım:  shelf help <konu>", "Örnek:     shelf help arama"]
    return "\n".join(satirlar)


def konu_metni(ad):
    veri = KONULAR.get(ad)
    if veri is None:
        return None
    cizgi = "─" * max(12, len(veri["baslik"]))
    return f"{veri['baslik']}\n{cizgi}\n\n{veri['metin']}"
