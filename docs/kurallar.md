# Kategori kuralları

`shelf`'in dökümanları hangi klasöre koyacağına karar veren kural seti
`shelflib/rules.json` içindedir. Kendi arşivinize uyarlamak için bu dosyayı
düzenleyin veya `--rules kendi.json` ile başka bir dosya verin.

## Dosya yapısı

```json
{
  "DIR_STRUCTURE": {
    "AD_PENTEST": "01_OFANSIF_GUVENLIK_(RED_TEAM)/04_Active_Directory_Guvenligi",
    "KRIPTOGRAFI": "03_TEMEL_BILGILER_VE_ALTYAPI/04_Kriptografi",
    "KATEGORISIZ": "05_OZEL_KONULAR_VE_RAPORLAR/99_Kategorisiz_ve_Genel"
  },
  "KEYWORD_MAP": {
    "AD_PENTEST": {
      "kerberoasting": 5,
      "active directory": 5,
      "kerberos": 4,
      "ldap": 3
    }
  }
}
```

**DIR_STRUCTURE** kategori kodunu arşiv içindeki göreli klasör yoluna eşler.
`KATEGORISIZ` zorunludur: hiçbir kurala uymayan dökümanlar oraya gider.

**KEYWORD_MAP** her kategori için anahtar kelimeleri ve ağırlıklarını tutar.
Ağırlık, terimin o kategori için ne kadar belirleyici olduğunu anlatır:

| Ağırlık | Anlamı | Örnek |
|---|---|---|
| 5 | Neredeyse tek başına kategoriyi belirler | `kerberoasting`, `sql injection` |
| 4 | Güçlü işaret | `kerberos`, `owasp` |
| 3 | Destekleyici | `ldap`, `enumeration` |
| 1–2 | Zayıf, yalnız başına yetmez | `security`, `network` |

## Puanlama nasıl işler

Her döküman için dosya adı ve (varsa) çıkarılmış metin taranır. Bir anahtar
kelime bulunduğunda kategorisinin puanı artar:

- **Dosya adında geçerse** ağırlık **3 ile çarpılır.** Adlandırma zaten dökümanın
  konusunu özetler, dolayısıyla oradaki eşleşme içerikteki tek bir geçişten çok
  daha güçlü bir işarettir.
- **İçerikte geçerse** ağırlık, terimin metinde kaç kez geçtiğine göre kademeli
  bir çarpanla artar:

  | Geçiş sayısı | Çarpan |
  |---|---|
  | 1–2 | ×1 |
  | 3–9 | ×2 |
  | 10+ | ×3 |

  Kademeli olmasının nedeni: bir terimin bir kez geçmesi çoğu zaman rastlantıdır,
  onlarca kez geçmesi dökümanın konusunu belli eder. Doğrusal saymak ise yaygın
  kelimeleri aşırı ödüllendirirdi.

En yüksek puanı alan kategori seçilir. Puan `organize_threshold` (varsayılan 15)
altında kalırsa karar AI'a devredilir; AI da sonuç veremezse döküman
`KATEGORISIZ` olur.

Bir dökümanın nasıl puanlandığını görmek için `shelf organize <dizin> -n` kuru
çalıştırmasında her satırın başındaki `[kural]` / `[AI]` / `[?]` etiketine bakın.

## Eşiği seçmek

Eşik yükseldikçe kuralın verdiği kararlar azalır ama isabeti artar; düşürdükçe
daha çok dosya kuralla yerleşir, hata payı büyür. 1180 dökümanlık bir arşivde
ölçülen değerler:

| Eşik | Kuralın karar verdiği | Mevcut yerleşimle uyum |
|---|---|---|
| 10 | %88.5 | %77.3 |
| **15** | **%76.4** | **%78.6** |
| 20 | %66.2 | %79.1 |
| 25 | %51.8 | %82.5 |

Varsayılan 15, kapsam ile isabet arasındaki makul orta noktadır. AI kullanmıyorsanız
(`--no-ai`) eşiği düşürmek mantıklıdır, çünkü eşiğin altındaki her şey doğrudan
`KATEGORISIZ`'e gider.

```bash
shelf config --show                          # mevcut eşiği gör
shelf organize ~/yeni --threshold 10 -n      # tek seferlik dene
```

## Kelime sınırları

Eşleşmeler kelime sınırında yapılır: `ldap` kuralı `ldapsearch` kelimesiyle
eşleşmez. Dosya adlarındaki `_`, `-`, `.`, parantez gibi ayraçlar tarama öncesi
boşluğa çevrilir, böylece `AD_PENTEST_Kerberoasting_Guide.pdf` içindeki
`kerberoasting` bulunabilir.

Bunun bir yan etkisi: **çoğul biçimler ayrı terimlerdir.** `forensic` kuralı
`Forensics` yazan bir dosyayla eşleşmez. Çok geçen çoğul biçimleri kural setine
ayrıca eklemek gerekir — `shelf keywords` bu eksikleri yakalamanın en kolay yoludur.

## Kendi kural setinizi yazmak

1. Arşivinizin klasör yapısını `DIR_STRUCTURE`'a yazın. Kodlar kısa ve büyük harf
   olsun; AI'a kategori sorulurken bu kodlar kullanılır.
2. Her kategori için 5–15 anahtar kelime yeterlidir. Az sayıda güçlü terim, çok
   sayıda zayıf terimden iyi sonuç verir.
3. `shelf organize <örnek_dizin> -n --no-ai` ile kuru çalıştırıp dağılıma bakın.
4. `shelf keywords --content` ile kategorisiz kalanlardan eksik terimleri toplayın.
5. Kategoriler arası çakışma varsa (aynı terim iki kategoride) ağırlıkları
   ayrıştırın; puanlama toplamsal olduğu için küçük farklar sonucu belirler.

`shelf rules -k` mevcut setin tamamını kategori kategori, ağırlıklarıyla listeler.
