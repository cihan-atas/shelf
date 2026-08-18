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

<!-- KATALOG:BASLANGIC -->

## Arşivi küçültme

`tools/kucult.py`, PDF'leri Ghostscript ile yeniden kodlar. Orijinalleri **asla
değiştirmez** — ayrı bir dizin ağacına yazar, sayfa sayısını doğrular ve dosya
gerçekten küçülmediyse orijinali olduğu gibi kopyalar.

```bash
python3 tools/kucult.py ~/arsiv/hacking ~/arsiv/kucuk            # yalnızca ölç
python3 tools/kucult.py ~/arsiv/hacking ~/arsiv/kucuk --uygula -j 8
```

### Ölçüm sonuçları

9.2 GB'lık referans arşivden alınan örneklemde `-dPDFSETTINGS=/ebook`:

| Örneklem | Önce | Sonra | Kazanç |
| --- | ---: | ---: | ---: |
| 24 dosya, < 50 MB | 90 MB | 65 MB | %28 |
| 5 dosya, > 40 MB | 440 MB | 203 MB | %54 |

Ortalama yanıltıcı — dağılım çok geniş:

| Dosya | Değişim |
| --- | ---: |
| `Mobile_Forensic_Investigations` | **%81 küçüldü** |
| `WEB_API_Pentesting_Practical_Guide` | %75 küçüldü |
| `MalDev_Academy_Malware_Forensics` | %52 küçüldü |
| `CEHv13_Module06_System_Hacking` | değişmedi |
| `AG_SIZMA_Network_Security_Hackers_Guide` | %80 **büyüdü** |
| `CERT_DIGER_Hacking_Exposed_Windows` | %109 **büyüdü** |

Belirleyici olan, PDF'in içindeki görsellerin zaten sıkıştırılmış olup olmadığı.
Tarama tabanlı veya PNG ekran görüntüsü dolu kitaplar çok küçülür; iyi üretilmiş
metin PDF'leri hiç küçülmez, hatta Ghostscript'in yeniden kodlaması onları
büyütür. Bu yüzden araç her dosyayı tek tek ölçüp kararı dosya bazında verir.

Metin katmanı korunur — dönüşüm sonrası sayfa metni birebir aynı kalır, dolayısıyla
`shelf` indeksi ve araması etkilenmez. Kayıp, görsellerde olur: PNG ekran
görüntüleri JPEG'e çevrildiği için terminal çıktısı içeren görsellerde okunabilirlik
düşebilir. Arşivin tamamı için beklenen sonuç yaklaşık **9.2 GB → 4-4.5 GB**.

Kayıpsız alternatif olarak `qpdf --recompress-flate --compression-level=9
--object-streams=generate` denenebilir; ölçümde %9 civarı kazanç verdi, görsellere
dokunmaz.

## Arşiv kataloğu

Bu araç için referans arşiv **1180 belge** ve **9.2 GB** büyüklüğünde, 5 ana kategoriye ayrılmış. Belgelerin kendisi bu depoda **yer almaz** (telif); aşağıdaki liste yalnızca `shelf` ile üretilen dizin yapısını gösterir.

| Kategori | Belge | Boyut |
| --- | ---: | ---: |
| OFANSIF GUVENLIK (RED TEAM) | 521 | 3.1 GB |
| DEFANSIF GUVENLIK (BLUE TEAM) | 109 | 676.6 MB |
| TEMEL BILGILER VE ALTYAPI | 255 | 1.4 GB |
| SERTIFIKASYON VE KARIYER | 217 | 3.4 GB |
| OZEL KONULAR VE RAPORLAR | 78 | 746.8 MB |
| **Toplam** | **1180** | **9.2 GB** |

<details>
<summary><b>OFANSIF GUVENLIK (RED TEAM)</b> — 521 belge</summary>

```
OFANSIF GUVENLIK (RED TEAM)
├── Genel Pentest ve Metodoloji/
│   ├── CEHv13 Module06 System Hacking  (65.5 MB)
│   ├── CEHv13 Module13 WebServer Hacking  (21.2 MB)
│   ├── CEHv13 Module14 Web App Hacking  (65.9 MB)
│   ├── CEHv13 Module 01 Intro Ethical Hacking  (24.4 MB)
│   ├── HHS Digital Forensics Lesson8 License  (320 KB)
│   ├── PENTEST GENEL Algorithm Design Reference  (5.0 MB)
│   ├── PENTEST GENEL ArcGIS ArcPy Geospatial Analysis Python  (2.8 MB)
│   ├── PENTEST GENEL Cable Modem Hacking  (21.6 MB)
│   ├── PENTEST GENEL CleanCode Fundamentals Guide  (10.6 MB)
│   ├── PENTEST GENEL Cloud Breaching Techniques  (5.9 MB)
│   ├── PENTEST GENEL Cyberspace Operations Primer 2023  (3.2 MB)
│   ├── PENTEST GENEL DarkPsychology Manipulation Defense  (1.3 MB)
│   ├── PENTEST GENEL Ethical Hacking Beginner Guide  (792 KB)
│   ├── PENTEST GENEL Ethical Hacking Penetration Testing Guide  (22.4 MB)
│   ├── PENTEST GENEL Evasion Basics  (13.2 MB)
│   ├── PENTEST GENEL Gemini Workspace Prompting Guide  (3.6 MB)
│   ├── PENTEST GENEL Gmail Hacking Techniques  (5.3 MB)
│   ├── PENTEST GENEL Hacking Penetration Testing Basics  (3.7 MB)
│   ├── PENTEST GENEL Hacking Techniques Guide  (478 KB)
│   ├── PENTEST GENEL Hardware Trojan Insertion Defense Analysis  (5.5 MB)
│   ├── PENTEST GENEL LOTL Mitigation Guide  (2.3 MB)
│   ├── PENTEST GENEL LeBon Crowd Psychology  (3.6 MB)
│   ├── PENTEST GENEL ModernSoftwareTestingTechniques  (6.5 MB)
│   ├── PENTEST GENEL Offensive VBA Techniques  (7.6 MB)
│   └── PENTEST GENEL Python Hacking Beginners Guide  (724 KB)
├── Ag Sizma Testleri/
│   ├── AG SIZMA 100 Ethical Hacking Projects  (86 KB)
│   ├── AG SIZMA AV Bypass Techniques  (1.0 MB)
│   ├── AG SIZMA Active Directory Exploitation Cheatsheet  (362 KB)
│   ├── AG SIZMA Advanced ActiveDirectory Attacks Defense  (12.9 MB)
│   ├── AG SIZMA Advanced Windows Log Analysis QA  (232 KB)
│   ├── AG SIZMA Backtrack5 Penetration Testing Tutorial  (1.0 MB)
│   ├── AG SIZMA Blockchain Validator Resource Exhaustion Attack  (5.0 MB)
│   ├── AG SIZMA CRTO Exam Notes CobaltStrike AD Lab  (5.7 MB)
│   ├── AG SIZMA Cloud Computing Security Tests  (4.2 MB)
│   ├── AG SIZMA Command Injection Vulnerability Analysis  (2.7 MB)
│   ├── AG SIZMA Computer Forensics Investigations  (24.0 MB)
│   ├── AG SIZMA Computer Hacking Prevention Basics  (271 KB)
│   ├── AG SIZMA Computer Security Handbook  (1.8 MB)
│   ├── AG SIZMA Cybersecurity Course Notes  (1.6 MB)
│   ├── AG SIZMA DDoS Attack Mitigation Guide  (296 KB)
│   ├── AG SIZMA DNS Amplification Attacks CAMP  (1.6 MB)
│   ├── AG SIZMA Data Recovery Tool Review  (22.9 MB)
│   ├── AG SIZMA DoS DDoS Attacks Analysis  (2.0 MB)
│   ├── AG SIZMA Ethical Hacking Introduction  (9.3 MB)
│   ├── AG SIZMA Ethical Hacking Security Certification  (13.4 MB)
│   ├── AG SIZMA FalseDataInjection Attacks  (1.9 MB)
│   ├── AG SIZMA Firewall Evasion Techniques  (3.3 MB)
│   ├── AG SIZMA Firewall Testing Solutions  (1.2 MB)
│   ├── AG SIZMA Footprinting Recon Techniques  (2.5 MB)
│   ├── AG SIZMA GuerrillaWarfare Analysis Taber  (2.0 MB)
│   ├── AG SIZMA Hacker Handbook Ethical Hacking Techniques  (2.5 MB)
│   ├── AG SIZMA Heckler Malicious Interrupt Attack on Confidential VMs  (837 KB)
│   ├── AG SIZMA InfoSec Economic Perspective  (103 KB)
│   ├── AG SIZMA InformationSecurityLectureNotes  (1.3 MB)
│   ├── AG SIZMA IoT SSL TLS Binary Analysis SAMBA  (365 KB)
│   ├── AG SIZMA Java Deserialization Gadget Detection  (474 KB)
│   ├── AG SIZMA LateralMovement C2 PenetrationTesting  (7.3 MB)
│   ├── AG SIZMA Lateral Movement Techniques  (7.2 MB)
│   ├── AG SIZMA Linux Windows Basic Commands Lesson2  (361 KB)
│   ├── AG SIZMA ML IDS Ensemble Study  (1.2 MB)
│   ├── AG SIZMA Network Application Fuzzing Fault Injection  (773 KB)
│   ├── AG SIZMA Network Attack Exploitation Analysis  (25.1 MB)
│   ├── AG SIZMA Network Defense Against Hackers  (4.9 MB)
│   ├── AG SIZMA Network Hacks Python3 Defense  (3.2 MB)
│   ├── AG SIZMA Network Port Scanning Nmap Masscan  (83 KB)
│   ├── AG SIZMA Network Scanning Techniques  (2.7 MB)
│   ├── AG SIZMA Network Security Guide  (6.3 MB)
│   ├── AG SIZMA Network Security Hackers Guide  (2.6 MB)
│   ├── AG SIZMA Network Sniffing Attacks  (3.1 MB)
│   ├── AG SIZMA Networking Fundamentals for Hackers  (163 KB)
│   ├── AG SIZMA Password Cracking Tutorial  (51 KB)
│   ├── AG SIZMA Penetration Testing Cheat Sheet  (218 KB)
│   ├── AG SIZMA PhishingDetection TrainingEffectiveness  (736 KB)
│   ├── AG SIZMA Powershell RedTeam Techniques  (3.4 MB)
│   ├── AG SIZMA Rankin Deception WWI WWII  (6.5 MB)
│   ├── AG SIZMA SSH Security Guide  (4.3 MB)
│   ├── AG SIZMA Session Hijacking Attacks  (4.8 MB)
│   ├── AG SIZMA Session Hijacking Test CEHv13 Module11  (13.1 MB)
│   ├── AG SIZMA Sniffing Techniques CEHv13 Module8  (18.0 MB)
│   ├── AG SIZMA Suspicious Traffic Analysis  (669 KB)
│   ├── AG SIZMA TCP Spoofing Attack Analysis  (825 KB)
│   ├── AG SIZMA Testing Hacking Secrets Guide  (493 KB)
│   ├── AG SIZMA Tests CEHv13 Module04 Enumeration  (20.1 MB)
│   ├── AG SIZMA WebSecurityPrivacy Lesson10  (727 KB)
│   ├── AG SIZMA WebServer Hacking Tests  (3.1 MB)
│   ├── AG SIZMA WindowsXP Hacking Vulnerabilities  (10.1 MB)
│   ├── AG SIZMA Windows Event Log Analysis  (4.6 MB)
│   ├── AG SIZMA Windows Linux Privilege Escalation Automation  (4.8 MB)
│   ├── AG SIZMA Windows Security Reference  (4.8 MB)
│   ├── AG SIZMA Wireless Penetration Testing Lab Guide  (36.0 MB)
│   ├── AG SIZMA Wireshark Network Analysis Guide  (1.4 MB)
│   ├── Air-Gap Covert Channel Attack RAMBO  (15.9 MB)
│   ├── Android Kernel Defense Analysis USENIX2024  (2.4 MB)
│   ├── Android WiFi SocialMedia Hacking Recovery Course  (54 KB)
│   ├── Azure Hybrid Attack Path Detection Graph Theory  (925 KB)
│   ├── Azure Security Defense In Depth Guide  (23.8 MB)
│   ├── Azure Sentinel KQL Queries Top 300  (1.2 MB)
│   ├── Bash Scripting Guide for Professionals  (1.7 MB)
│   ├── Bash Scripting Professional Guide  (1.7 MB)
│   ├── Binarly PKFail SecureBoot SupplyChain Vulnerability Report 2024  (6.1 MB)
│   ├── CEH Exam Cheat Sheet Cryptography Attacks  (608 KB)
│   ├── CEH v11 Exam Questions and Answers  (1.7 MB)
│   ├── CEHv13 Module12 IDS Firewall Honeypot Evasion  (29.2 MB)
│   ├── CompTIA CySA Plus Threat Intelligence Notes  (1.1 MB)
│   ├── CompTIA SecurityPlus Malware Attacks CheatSheet  (796 KB)
│   ├── Cybersecurity History Attacks Guide  (1.2 MB)
│   ├── Cybersecurity Introduction DrPande UOU  (5.0 MB)
│   ├── Cybersecurity Overview and Subdomains  (698 KB)
│   ├── Cybersecurity Terms Glossary A-Z  (22.1 MB)
│   ├── Ethical Hacking Introduction Kanav Jindal  (142 KB)
│   ├── Ethical Hacking Tutorial  (2.7 MB)
│   ├── Ettercap Filters Tutorial  (368 KB)
│   ├── GSMA MoTIF v1.0 Mobile Threat Intelligence Principles  (963 KB)
│   ├── Go Programming for Hackers and Pentesters  (22.6 MB)
│   ├── HCIA-H12-211-Huawei-Networking-Practice-Exam  (210 KB)
│   ├── HCIA H12-211 AAA Authentication Practice Exam  (146 KB)
│   ├── HHS Attack Analysis Lesson7  (318 KB)
│   ├── HHS TOC Glossary and License Information  (244 KB)
│   ├── Hate Crime Operational Guidance 2014  (1.4 MB)
│   ├── HomeRouter DefaultSettings SecurityAnalysis  (1.1 MB)
│   ├── HookChain EDR Bypass Technique  (2.0 MB)
│   ├── HookChain EDR Bypass Technique  (14.4 MB)
│   ├── Huawei H12-211 AAA Authentication Practice Questions  (213 KB)
│   ├── Hypervisor Fuzzing HyperPill USENIX2024  (595 KB)
│   ├── Intrusion Detection Planning Guide  (199 KB)
│   ├── Kerberos Delegation Vulnerabilities and Mitigation  (3.9 MB)
│   ├── Lampson Computer Security Real World  (151 KB)
│   ├── Low-Level Software Security Compiler Vulnerabilities  (866 KB)
│   ├── MITRE ATT&CK Detection Rules Part2  (2.7 MB)
│   ├── Malware Development Tricks Evasion Persistence Techniques  (70.4 MB)
│   ├── Mantis LLM Defense Against Cyberattacks  (1.5 MB)
│   ├── NIST SP800-63B-4 Digital Identity Guidelines  (1.0 MB)
│   ├── Network Forensics Privacy Security Bijalwan AG SIZMA Tests  (8.9 MB)
│   ├── Network Security Interview Questions and Role Overview  (272 KB)
│   ├── Nmap Cheat Sheet AG SIZMA Tests  (286 KB)
│   ├── Nmap Cheatsheet AG SIZMA Tests  (563 KB)
│   ├── OSCP ActiveDirectory PenetrationTesting Notes  (1.9 MB)
│   ├── OSCP Active Directory Notes  (1.5 MB)
│   ├── OT Asset Discovery Myth vs Reality  (1.1 MB)
│   ├── OrganizedCrime Terrorism Nexus Analysis  (2.9 MB)
│   ├── Pentest Best Practices Checklist  (116 KB)
│   ├── PortForwarding Tunneling Cheatsheet  (5.2 MB)
│   ├── Python Hacking Beginner Guide  (3.2 MB)
│   ├── RSA Small Private Exponent Attack Analysis  (405 KB)
│   ├── Ransomware Cybercrime Analysis AG SIZMA  (3.5 MB)
│   ├── Ransomware Protection Containment Strategies  (4.2 MB)
│   ├── Ransomware in Education 2024 Sophos Report  (688 KB)
│   ├── SOC Analyst Interview Prep Guide  (5.8 MB)
│   ├── SOC Analyst Interview Questions Answers  (124 KB)
│   ├── Secure Microarchitecture Dissertation Thoma 2024  (10.6 MB)
│   ├── Securing WiFi6 Connection Establishment Against Attacks  (1.1 MB)
│   ├── SecurityPlus Exam Prep Questions  (1.4 MB)
│   ├── Signal Protocol MitM Detection Defense  (1.1 MB)
│   ├── Social-Engineering-Attack-Simulation-SET-Testing  (90 KB)
│   ├── SyncM Microservices DDoS Attack Analysis  (1.3 MB)
│   ├── Top 100 Cybersecurity Interview Questions  (863 KB)
│   ├── VoIP Security Testing with SIPVicious and VoIPER  (73 KB)
│   ├── WPA3 SAE Bypass SocialEngineering Attack  (1.3 MB)
│   ├── WebRTC DTLS ClientHello Race Condition Vulnerability  (156 KB)
│   ├── Windows API Red Team 101 Guide  (992 KB)
│   ├── Windows Downgrade Attacks Vulnerabilities  (2.0 MB)
│   └── Wireshark Security Analysis Guide  (12.7 MB)
├── Web Uygulama ve API Guvenligi/
│   ├── Alibaba Cloud ACA Cloud1 Cert Exam Practice Questions  (232 KB)
│   ├── CEHv13 Module15 SQLInjection PenetrationTesting  (25.3 MB)
│   ├── Mobile-App-Pentest-CheatSheet  (107 KB)
│   ├── OSCP Web App Pentest CheatSheet  (473 KB)
│   ├── Okta IAM Administration Guide  (24.9 MB)
│   ├── WEB API PENTEST 100 Beginner Advanced Project Ideas  (110 KB)
│   ├── WEB API PENTEST 2FA Bypass Techniques  (301 KB)
│   ├── WEB API PENTEST 2FA Bypass Techniques  (104 KB)
│   ├── WEB API PENTEST AEM Misconfiguration Cheatsheet  (141 KB)
│   ├── WEB API PENTEST Acunetix Vulnerability Report 2019  (4.1 MB)
│   ├── WEB API PENTEST Android Mobile App Penetration Testing  (7.1 MB)
│   ├── WEB API PENTEST AppSec Interview Questions  (264 KB)
│   ├── WEB API PENTEST Bitrix CMS Vulnerabilities Exploitation  (3.6 MB)
│   ├── WEB API PENTEST Blind SQL Injection XP CMDSHELL Exploitation  (35 KB)
│   ├── WEB API PENTEST Bugcrowd VRT Guide v1.8  (240 KB)
│   ├── WEB API PENTEST BurpSuite BruteForce Attack  (1.2 MB)
│   ├── WEB API PENTEST BurpSuite CheatSheet  (38 KB)
│   ├── WEB API PENTEST BurpSuite Dashboard Guide  (385 KB)
│   ├── WEB API PENTEST BurpSuite Installation Configuration  (3.6 MB)
│   ├── WEB API PENTEST BurpSuite TipsTricks Northsec2023  (706 KB)
│   ├── WEB API PENTEST BurpSuite User Guide  (2.0 MB)
│   ├── WEB API PENTEST Burp Intruder Attack Types  (104 KB)
│   ├── WEB API PENTEST CSRF Vulnerability Analysis  (203 KB)
│   ├── WEB API PENTEST CVE-2024-21893 Ivanti SSRF RCE Exploit  (397 KB)
│   ├── WEB API PENTEST Email OSINT Wildcard Finder Tool  (1.5 MB)
│   ├── WEB API PENTEST File Upload Exploitation Cheatsheet  (214 KB)
│   ├── WEB API PENTEST HackSynth LLM Penetration Testing Agent  (1012 KB)
│   ├── WEB API PENTEST Hacking Next Generation Reference  (8.6 MB)
│   ├── WEB API PENTEST Insecure Direct Object Reference IDOR Exploitation  (78 KB)
│   ├── WEB API PENTEST IoT Vulnerabilities and Exploitation  (1.8 MB)
│   ├── WEB API PENTEST JWT Security Checklist  (142 KB)
│   ├── WEB API PENTEST JavaScript Exploits Techniques  (1.3 MB)
│   ├── WEB API PENTEST Jira Vulnerabilities Exploitation Guide  (93 KB)
│   ├── WEB API PENTEST JonMon Windows Telemetry Analysis  (2.5 MB)
│   ├── WEB API PENTEST Log File Attack Detection  (2.8 MB)
│   ├── WEB API PENTEST MOCGuard Java Vulnerability Analysis  (330 KB)
│   ├── WEB API PENTEST Nmap Commands Reference  (53 KB)
│   ├── WEB API PENTEST Nmap Network Security Assessment  (5.3 MB)
│   ├── WEB API PENTEST Nmap Security Assessment  (6.6 MB)
│   ├── WEB API PENTEST OAuth2 Security Analysis  (14.1 MB)
│   ├── WEB API PENTEST OAuth Application Exploitation MidnightBlizzard  (1.7 MB)
│   ├── WEB API PENTEST OWASP Authentication Session Clickjacking Cheatsheet  (1.1 MB)
│   ├── WEB API PENTEST OllyDbg 2.01 Tutorial  (5.4 MB)
│   ├── WEB API PENTEST PHP Security XSS Defenses  (4.2 MB)
│   ├── WEB API PENTEST PSBP Vulnerability Guide Oct2024  (755 KB)
│   ├── WEB API PENTEST Parasoft DTP Default Creds RCE Exploit  (610 KB)
│   ├── WEB API PENTEST PrAu Privacy Risks Analysis  (2.0 MB)
│   ├── WEB API PENTEST Python Standard Library Reference  (1.8 MB)
│   ├── WEB API PENTEST REST API Testing Notes  (1.3 MB)
│   ├── WEB API PENTEST RFI LFI Exploitation Prevention  (1.4 MB)
│   ├── WEB API PENTEST SBOM Integrity Vulnerabilities  (1.9 MB)
│   ├── WEB API PENTEST SQLInjection CheatSheet  (11.6 MB)
│   ├── WEB API PENTEST SQLInjection Cheatsheet  (599 KB)
│   ├── WEB API PENTEST SQLInjection DNS Exfiltration  (436 KB)
│   ├── WEB API PENTEST SQL Injection Vulnerabilities  (3.0 MB)
│   ├── WEB API PENTEST SQL Injection Vulnerability Analysis  (2.4 MB)
│   ├── WEB API PENTEST SQLi Out-of-Band Techniques  (81 KB)
│   ├── WEB API PENTEST SQLmap CheatSheet and Techniques  (447 KB)
│   ├── WEB API PENTEST SSRF Vulnerability Analysis  (213 KB)
│   ├── WEB API PENTEST SecureCoding SQLInjection XSS  (579 KB)
│   ├── WEB API PENTEST Secure WebApp Development Guide  (103 KB)
│   ├── WEB API PENTEST Spring Security Vulnerabilities  (11.2 MB)
│   ├── WEB API PENTEST VS Code Extension Security Analysis  (686 KB)
│   ├── WEB API PENTEST Vulnerable WebApp Setup Guide  (1.1 MB)
│   ├── WEB API PENTEST WAF Bypass Techniques  (1.1 MB)
│   ├── WEB API PENTEST Web Hacking 101 Yaworski  (2.9 MB)
│   ├── WEB API PENTEST Web Hacking 101 Yaworski  (9.4 MB)
│   ├── WEB API PENTEST Wireless Security Vulnerabilities CEH V12 Questions  (1.8 MB)
│   ├── WEB API PENTEST XPath Cheat Sheet  (608 KB)
│   ├── WEB API PENTEST XSS Attacks Defense  (7.3 MB)
│   ├── WEB API PENTEST XSS CheatSheet 2019  (1.6 MB)
│   ├── WEB API PENTEST XSS CheatSheet 2020  (1.1 MB)
│   ├── WEB API PENTEST XSS Evasion WAF Bypass  (8.7 MB)
│   ├── WEB API PENTEST XSS Exploitation Prevention  (1.3 MB)
│   ├── WEB API PENTEST XSS Exploitation Techniques  (747 KB)
│   ├── WEB API PENTEST eBPF Security Threat Model  (1.5 MB)
│   ├── WEB API Password Reset Pentest Checklist  (97 KB)
│   ├── WEB API Penetration Testing CTF Handbook  (45.9 MB)
│   ├── WEB API Penetration Testing Checklist  (1001 KB)
│   ├── WEB API Penetration Testing Guide  (23.4 MB)
│   ├── WEB API Penetration Testing Techniques  (3.0 MB)
│   ├── WEB API Penetration Testing Workbook SEC522  (19.7 MB)
│   ├── WEB API Pentest Bounty Tips Twitter  (226 KB)
│   ├── WEB API Pentest Bug Bounty Tips and Tricks  (259 KB)
│   ├── WEB API Pentest Bug Bounty Tools List  (292 KB)
│   ├── WEB API Pentest Business Logic Errors Cheatsheet  (207 KB)
│   ├── WEB API Pentest ChatGPT Payloads XSS XXE InsecureDeserialization  (2.4 MB)
│   ├── WEB API Pentest CheatSheet Commands Techniques  (152 KB)
│   ├── WEB API Pentest Fundamentals and Exploitation  (4.6 MB)
│   ├── WEB API Pentest Fuzzing Bug Bounty Techniques  (198 KB)
│   ├── WEB API Pentest HackerOne Vulnerability Report Analysis  (671 KB)
│   ├── WEB API Pentest Hacker Methodologies Tools Techniques  (592 KB)
│   ├── WEB API Pentest Hacker Playbook Extract  (26.1 MB)
│   ├── WEB API Pentest InformationGathering ConfigMgmt  (13.3 MB)
│   ├── WEB API Pentest InformationGathering Recon Techniques  (13.1 MB)
│   ├── WEB API Pentest Injection Vulnerability Assessment  (1.5 MB)
│   ├── WEB API Pentest OSWE Notes Compilation  (10.0 MB)
│   ├── WEB API Pentest OWASP AppSec Guide  (2.8 MB)
│   ├── WEB API Pentest Planning Preparation Guide  (257 KB)
│   ├── WEB API Pentest SQLi XSS CSRF RCE Mitigation  (104 KB)
│   ├── WEB API Pentest Secure Architecture Checklist  (1.2 MB)
│   ├── WEB API Pentest SecurityPlus Labs  (38.8 MB)
│   ├── WEB API Pentest Security Notes  (692 KB)
│   ├── WEB API Pentest Seven Deadliest Attacks  (3.0 MB)
│   ├── WEB API Pentest Top 100 Vulnerabilities Guide  (657 KB)
│   ├── WEB API Pentest Vulnerability Analysis  (2.0 MB)
│   ├── WEB API Pentest Vulnerability Assessment Guide  (96 KB)
│   ├── WEB API Pentest WSTG v4.2 Guide  (9.7 MB)
│   ├── WEB API Pentest WebAppHackerHandbook 2ndEd  (13.5 MB)
│   ├── WEB API Pentest WebApp Hacker Handbook Reference  (11.0 MB)
│   ├── WEB API Pentest WebApp Sec Exploitation Mitigation Guide  (14.2 MB)
│   ├── WEB API Pentest Web Application Hacking  (3.4 MB)
│   ├── WEB API Pentest Yaworski Bug Hunting Guide  (6.1 MB)
│   ├── WEB API Pentester Quiz Questions Answers  (7.7 MB)
│   ├── WEB API Pentesting Checklist and Methodology  (581 KB)
│   ├── WEB API Pentesting Handbook  (23.6 MB)
│   ├── WEB API Pentesting Modern Techniques  (15.2 MB)
│   ├── WEB API Pentesting Practical Guide  (48.6 MB)
│   └── WEB API Pentesting TryHackMe Room Guide  (173 KB)
├── Active Directory Guvenligi/
│   ├── AD Compromise Detection Mitigation Guide  (2.0 MB)
│   ├── AD Exploitation CheatSheet Commands  (841 KB)
│   ├── AD PENTEST Active Directory Overview and Architecture  (1.2 MB)
│   ├── AD PENTEST BloodHound Enumeration Guide  (2.3 MB)
│   ├── AD PENTEST Compiler Interpreter Analysis  (34.4 MB)
│   ├── AD PENTEST Cybersecurity Practical Engineering Approach  (11.5 MB)
│   ├── AD PENTEST GOAD Attack Techniques Guide  (9.7 MB)
│   ├── AD PENTEST Initial Foothold Privilege Escalation  (80 KB)
│   ├── AD PENTEST Kerberoasting Attack Techniques  (285 KB)
│   ├── AD PENTEST Kerberos Authentication Process  (603 KB)
│   ├── AD PENTEST Kerberos Delegation Attacks Detection Defense  (5.9 MB)
│   ├── AD PENTEST Kerbrute Guide  (991 KB)
│   ├── AD PENTEST KillChain BestPractices  (2.6 MB)
│   ├── AD PENTEST LLMNR Poisoning Prevention Guide  (2.0 MB)
│   ├── AD PENTEST Lab1 Infinity Domain Enumeration  (174 KB)
│   ├── AD PENTEST LabManual Attack Defense  (3.1 MB)
│   ├── AD PENTEST Libra Secure Balanced Execution Paper  (493 KB)
│   ├── AD PENTEST MSSQL Attack Techniques  (3.2 MB)
│   ├── AD PENTEST Mimikatz Overview Defenses Detection  (2.6 MB)
│   ├── AD PENTEST NTLM Abuse Methods  (5.5 MB)
│   ├── AD PENTEST NetSync vs DCSync TexasCyberSummit2023  (31.6 MB)
│   ├── AD PENTEST Network Scanning and Shell Techniques  (141 KB)
│   ├── AD PENTEST NoFilter WFP Privilege Escalation  (1.8 MB)
│   ├── AD PENTEST OSEP ACBank Meterpreter Csharp Payload Evasion  (157 KB)
│   ├── AD PENTEST OpenNetAdmin Vulnerability Analysis  (416 KB)
│   ├── AD PENTEST PassTheHash Attack Techniques  (4.0 MB)
│   ├── AD PENTEST PowerShell Automation Scripting  (16.3 MB)
│   ├── AD PENTEST PowerShell Penetration Testing  (12.5 MB)
│   ├── AD PENTEST PowerView 3.0 Enumeration Techniques  (104 KB)
│   ├── AD PENTEST Privilege Escalation 40 Methods  (84.9 MB)
│   ├── AD PENTEST Quick Security Improvements  (2.8 MB)
│   ├── AD PENTEST RDP DFIR Logon Analysis  (76 KB)
│   ├── AD PENTEST RedTeam Interview Questions  (6.7 MB)
│   ├── AD PENTEST RedTeam Tools Techniques  (19.0 MB)
│   ├── AD PENTEST Report Multiple Domain Compromise Techniques  (694 KB)
│   ├── AD PENTEST SEC560 Domain Domination Azure Annihilation Report  (7.9 MB)
│   ├── AD PENTEST SOC Concepts Incident Response  (1.1 MB)
│   ├── AD PENTEST Vulnerable Domain Setup Guide  (2.8 MB)
│   ├── AD PENTEST Windows Security Internals PowerShell EA  (6.1 MB)
│   ├── AD PENTEST Windows Security Monitoring Scenarios  (6.3 MB)
│   ├── AD Pentest Active Directory Attack Techniques  (8.8 MB)
│   ├── AD Pentest Active Directory Overview and Structure  (1.2 MB)
│   ├── AD Pentest KaliLinux Attacks  (3.7 MB)
│   ├── AD Pentest Offensive ActiveDirectory 101  (7.0 MB)
│   ├── AD Pentest Offensive Attributes Exploitation  (1018 KB)
│   ├── AD Pentesting RedTeam Operations Course  (9.3 MB)
│   ├── AD Pentesting Techniques and Exploits  (258 KB)
│   ├── AD Security Checklist PENTEST  (208 KB)
│   ├── AD Security Handbook Penetration Testing  (4.3 MB)
│   └── AD Win Infra Pentesting Guide  (35.6 MB)
├── Kablosuz Ag Guvenligi/
│   ├── Complete WiFi Hacking Handbook  (3.2 MB)
│   ├── WIRELESS PENTEST 802.11 WLAN Fundamentals  (178 KB)
│   ├── WIRELESS PENTEST 802.1X Authentication Configuration  (66 KB)
│   ├── WIRELESS PENTEST Android Network SSID Hacking Techniques  (13.0 MB)
│   ├── WIRELESS PENTEST BackTrack WiFi Attacks Guide  (14.5 MB)
│   ├── WIRELESS PENTEST Bluetooth Hacking Prevention  (153 KB)
│   ├── WIRELESS PENTEST Criminal Investigations Intelligence Tradecraft  (11.6 MB)
│   ├── WIRELESS PENTEST HHS Password Security Lesson  (212 KB)
│   ├── WIRELESS PENTEST IOS ZoneBasedFirewall Configuration  (52 KB)
│   ├── WIRELESS PENTEST Network Fundamentals  (200 KB)
│   ├── WIRELESS PENTEST Physical Penetration Testing  (2.6 MB)
│   ├── WIRELESS PENTEST SSID Discovery Tools  (2.5 MB)
│   ├── WIRELESS PENTEST Sniffing Basics Airodump-ng  (102 KB)
│   ├── WIRELESS PENTEST WAP Bluetooth 3G Programming Analysis  (7.5 MB)
│   ├── WIRELESS PENTEST WiFi Security WEP WPA Attacks  (2.9 MB)
│   ├── WIRELESS PENTEST Wireshark 802.11 Filters Reference  (138 KB)
│   ├── Wireless Network Penetration Testing CEHv13 Module16  (24.3 MB)
│   └── Wireless Pentest System Failure Safeguards  (1.4 MB)
├── Mobil ve IoT Guvenligi/
│   ├── CEHv13 Module18 IoT OT Penetration Testing  (44.0 MB)
│   ├── Cellebrite Physical Analyzer 7.67 Release Notes  (632 KB)
│   ├── IoT System Design Analysis PacketTracer Exercise  (104 KB)
│   ├── MOBILE IOT OECD Security Challenges Report 2016  (675 KB)
│   ├── MOBILE IOT PENTEST 5GHOUL Vulnerability Report  (10.6 MB)
│   ├── MOBILE IOT PENTEST 5G TLS Vulnerabilities Analysis  (2.2 MB)
│   ├── MOBILE IOT PENTEST AI Threat Intelligence Handbook  (3.5 MB)
│   ├── MOBILE IOT PENTEST Android Architecture Fundamentals  (485 KB)
│   ├── MOBILE IOT PENTEST BugBounty ChatGPT Techniques  (1.1 MB)
│   ├── MOBILE IOT PENTEST ChatGPT BugBounty Techniques  (1.1 MB)
│   ├── MOBILE IOT PENTEST Cloud Edge Networking Security Analysis  (14.2 MB)
│   ├── MOBILE IOT PENTEST CrypTody Cryptographic Misuse Analysis  (1.5 MB)
│   ├── MOBILE IOT PENTEST Database Forensics Handbook  (13.2 MB)
│   ├── MOBILE IOT PENTEST DeepLearning XIoT MalwareAnalysis  (1.4 MB)
│   ├── MOBILE IOT PENTEST DeepWeb Anonymity Guide  (4.8 MB)
│   ├── MOBILE IOT PENTEST FCM Push Notification Privacy Leakage  (888 KB)
│   ├── MOBILE IOT PENTEST Facebook Account Hacking Techniques  (579 KB)
│   ├── MOBILE IOT PENTEST GNSS Spoofing Jamming Detection ML DL  (512 KB)
│   ├── MOBILE IOT PENTEST GNU Linux Keylogger Implementation  (276 KB)
│   ├── MOBILE IOT PENTEST InfoStealer Malware Automotive Head Units  (62.9 MB)
│   ├── MOBILE IOT PENTEST IoT Fundamentals Guide  (457 KB)
│   ├── MOBILE IOT PENTEST IoT Fundamentals Guide  (324 KB)
│   ├── MOBILE IOT PENTEST IoT Fundamentals and Applications  (3.2 MB)
│   ├── MOBILE IOT PENTEST IoT Future Challenges Security  (226 KB)
│   ├── MOBILE IOT PENTEST IoT Security Challenges and Applications  (660 KB)
│   ├── MOBILE IOT PENTEST IoT Security Review  (710 KB)
│   ├── MOBILE IOT PENTEST ML DL Blockchain Cybersecurity Defense  (10.3 MB)
│   ├── MOBILE IOT PENTEST OSINT Intelligence Analysis  (628 KB)
│   ├── MOBILE IOT PENTEST OWASP IoT Security Testing Guide  (753 KB)
│   ├── MOBILE IOT PENTEST OxygenForensicDetective v15.4 ReleaseNotes  (756 KB)
│   ├── MOBILE IOT PENTEST Pixel8 GPU Exploit Analysis  (2.8 MB)
│   ├── MOBILE IOT PENTEST RogueBaseStation Detection CellGuard  (9.0 MB)
│   ├── MOBILE IOT PENTEST SCADA ICS Security Guide  (2.2 MB)
│   ├── MOBILE IOT PENTEST Splunk Cheat Sheet  (604 KB)
│   ├── MOBILE IOT PENTEST Web Browser Forensics Analysis  (3.4 MB)
│   ├── MOBILE IOT PENTEST macOS Vulnerability Analysis and Exploitation  (17.7 MB)
│   ├── MOBILE IOT Pentest EconomicPerspective IoT  (1.5 MB)
│   ├── MOBILE IOT Pentest FTK Suite Mobile Data Forensics  (379 KB)
│   ├── MOBILE IOT Pentest IoT Introduction  (2.6 MB)
│   ├── MOBILE IOT Pentest IoT Societal Challenges Whitepaper  (2.2 MB)
│   ├── MOBILE IOT Pentest IoT Survey Analysis  (538 KB)
│   ├── MOBILE IOT Pentest MySQL Data Management  (9.7 MB)
│   ├── MOBILE IOT Pentesting Mobile OS Hacking  (4.5 MB)
│   ├── MOBILE IOT Pentesting Primer Deloitte  (1.1 MB)
│   ├── Mobile Forensic Investigations Fundamentals Advanced  (95.4 MB)
│   ├── Mobile Platform Hacking CEHv13 Module17  (28.2 MB)
│   └── OWASP MASTG v1.7.0 Mobile App Pentesting Guide  (26.5 MB)
├── Exploit Gelistirme ve Tersine Muhendislik/
│   ├── AI Cybersecurity Use Cases Handbook  (14.8 MB)
│   ├── BYOVD 0day Exploit Analysis BlackHat BHASIA  (2.0 MB)
│   ├── BreachSeek Automated Penetration Testing EXPLOIT RE  (840 KB)
│   ├── ERIAKOS Mobile Ad Scam Campaign Analysis  (4.8 MB)
│   ├── EXPLOIT RE 2023 Top Exploited Vulnerabilities  (907 KB)
│   ├── EXPLOIT RE Android Malware Handbook 2023  (49.8 MB)
│   ├── EXPLOIT RE Android TA Rollback Prevention Study  (883 KB)
│   ├── EXPLOIT RE BufferOverflow Exploit Guide  (4.9 MB)
│   ├── EXPLOIT RE Bug Hunters Diary Software Security  (5.2 MB)
│   ├── EXPLOIT RE Effective Exploit Search Techniques  (3.1 MB)
│   ├── EXPLOIT RE Grammar Mining Fuzzing Technique  (157 KB)
│   ├── EXPLOIT RE Hacking Art of Exploitation  (1.7 MB)
│   ├── EXPLOIT RE Hacking The Art of Exploitation 2nd Edition  (4.0 MB)
│   ├── EXPLOIT RE Hoglund McGraw ExploitingSoftware HowToBreakCode  (7.6 MB)
│   ├── EXPLOIT RE Hypervisor Vulnerabilities Reverse Engineering  (1.3 MB)
│   ├── EXPLOIT RE JS Engine Fuzzing Techniques 2024  (328 KB)
│   ├── EXPLOIT RE JS Engine Race Condition Exploit Butterfly  (11.0 MB)
│   ├── EXPLOIT RE Kali Linux Penetration Testing  (9.0 MB)
│   ├── EXPLOIT RE KernelSnitch SideChannel Attack  (1.8 MB)
│   ├── EXPLOIT RE LLM Hacking InterCode CTF Benchmark  (978 KB)
│   ├── EXPLOIT RE Legacy Kernel Exploits and Mitigations  (919 KB)
│   ├── EXPLOIT RE MAS08 macOS iOS Malware Analysis  (7.2 MB)
│   ├── EXPLOIT RE Mastering Metasploit 4th Edition  (35.8 MB)
│   ├── EXPLOIT RE Metasploit Penetration Testers Guide  (6.9 MB)
│   ├── EXPLOIT RE Metasploit Penetration Testers Guide  (6.9 MB)
│   ├── EXPLOIT RE NEUZZ Fuzzing Rebuttal Analysis  (418 KB)
│   ├── EXPLOIT RE Practical Malware Analysis  (9.3 MB)
│   ├── EXPLOIT RE Practical Reverse Engineering x86 x64 ARM  (5.2 MB)
│   ├── EXPLOIT RE Practical Reverse Engineering x86 x64 ARM Kernel  (4.6 MB)
│   ├── EXPLOIT RE Project6 BufferOverflow ExploitDev  (92 KB)
│   ├── EXPLOIT RE ProphetFuzz Automated Vulnerability Fuzzing  (1.1 MB)
│   ├── EXPLOIT RE Pwn2Own 2024 Lorex Camera RCE Exploit  (8.1 MB)
│   ├── EXPLOIT RE Ransomware Threat Actor Timeline  (755 KB)
│   ├── EXPLOIT RE Reverse Engineering Secrets  (8.4 MB)
│   ├── EXPLOIT RE Reversing Secrets Reverse Engineering  (8.5 MB)
│   ├── EXPLOIT RE SLUB Internals Exploit Development  (853 KB)
│   ├── EXPLOIT RE VMware Escape Techniques and CVE Analysis  (2.1 MB)
│   ├── EXPLOIT RE WDDR Windows Debugging Reversing Training  (8.1 MB)
│   ├── EXPLOIT RE WiFi RCE Over The Air Attacks  (5.1 MB)
│   ├── EXPLOIT RE Windows Security Internals Deep Dive  (6.3 MB)
│   ├── EXPLOIT RE Zerologon Vulnerability Exploitation Guide  (6.0 MB)
│   ├── Effective Penetration Testing Programme Guide  (1.8 MB)
│   ├── GrayHat Ethical Hacking Exploit Handbook  (12.5 MB)
│   ├── Hard Real-Time Computing Systems 4th Edition  (18.1 MB)
│   ├── Healthcare Cybersecurity Hygiene Exploit Analysis  (295 KB)
│   ├── HyLLFuzz LLM Assisted Hybrid Fuzzing EXPLOIT RE  (2.3 MB)
│   ├── Invivo Fuzzing Library Exploit Analysis  (546 KB)
│   ├── Linux Debugging Disassembly Reversing Guide  (3.0 MB)
│   ├── MSSQL Penetration Testing Metasploit Exploit  (1.9 MB)
│   ├── OSED Notes x86 Architecture Study Guide  (20.0 MB)
│   ├── RedHat Linux Security Optimization EXPLOIT RE  (5.1 MB)
│   ├── Reverse Engineering for Beginners Guide  (9.5 MB)
│   ├── US Government Counterinsurgency Guide 2009  (2.4 MB)
│   ├── WebAssembly SSP Vulnerabilities and Mitigation  (591 KB)
│   └── Win32k rs REcon2023 LightningTalk Analysis  (3.4 MB)
├── Sosyal Muhendislik ve OSINT/
│   ├── DoD OSINT Strategy 2024-2028  (3.4 MB)
│   ├── Microsoft Digital Defense Report 2024 SOCENG OSINT  (20.8 MB)
│   ├── SOCENG OSINT BugBountyAutomation Python  (1.1 MB)
│   ├── SOCENG OSINT CEHv13 Module09 SocialEngineering  (15.2 MB)
│   ├── SOCENG OSINT ChatGPT Shodan Prompts  (1.4 MB)
│   ├── SOCENG OSINT CobaltStrike Healthcare Threat Analysis  (3.6 MB)
│   ├── SOCENG OSINT Computer Forensics Guide  (48.7 MB)
│   ├── SOCENG OSINT Cplusplus Decompilation IDA HexRays Recon2011  (794 KB)
│   ├── SOCENG OSINT CyberWAR Weekly Report 2021-03-01  (27.1 MB)
│   ├── SOCENG OSINT DNS Enumeration DNSenum Fierce  (61 KB)
│   ├── SOCENG OSINT DUSS Misdirection Attack Analysis  (801 KB)
│   ├── SOCENG OSINT Dissecting The Forbidden Network  (14.9 MB)
│   ├── SOCENG OSINT FTC Cybersecurity Basics SmallBusiness  (3.0 MB)
│   ├── SOCENG OSINT Footprinting Recon Lab Manual  (1.5 MB)
│   ├── SOCENG OSINT Footprinting Reconnaissance CEHv13 Module02  (26.1 MB)
│   ├── SOCENG OSINT Free Phishing Detection Tools  (488 KB)
│   ├── SOCENG OSINT GenerativeAI Pentesting Risks Benefits  (821 KB)
│   ├── SOCENG OSINT HHS Email Security Lesson9  (531 KB)
│   ├── SOCENG OSINT HackerHighschool Lesson1 BeingAHacker  (229 KB)
│   ├── SOCENG OSINT Hacking SocialProblem Alleyne  (162 KB)
│   ├── SOCENG OSINT Hyperlink Hijacking Phantom Domains  (2.5 MB)
│   ├── SOCENG OSINT Kali Linux Reconnaissance Tools  (44 KB)
│   ├── SOCENG OSINT Linux User Privacy Guide  (4.2 MB)
│   ├── SOCENG OSINT MFA Comparison PhishingResistance  (4.3 MB)
│   ├── SOCENG OSINT MaliciousWebsiteDetection ML Approach  (861 KB)
│   ├── SOCENG OSINT Mitnick ArtOfDeception  (5.2 MB)
│   ├── SOCENG OSINT Mitnick ArtOfIntrusion  (3.1 MB)
│   ├── SOCENG OSINT Mitnick ArtOfIntrusion  (3.1 MB)
│   ├── SOCENG OSINT MuddyWater BugSleep Backdoor Analysis  (1.3 MB)
│   ├── SOCENG OSINT Passive Subdomain Recon  (2.1 MB)
│   ├── SOCENG OSINT Passkey Security Enterprise Adoption  (1.6 MB)
│   ├── SOCENG OSINT RedTeam BlueTeam OperatorHandbook  (3.1 MB)
│   ├── SOCENG OSINT Remote Code Execution Incident Report 20231121  (1.1 MB)
│   ├── SOCENG OSINT SocialEngineering HumanHacking Techniques  (6.1 MB)
│   ├── SOCENG OSINT SocialEngineering PsychologicalWarfare  (464 KB)
│   ├── SOCENG OSINT SocialEngineering Techniques Guide  (2.4 MB)
│   ├── SOCENG OSINT Teams Webhook Phishing Attack  (5.9 MB)
│   ├── SOCENG OSINT TikTok Attack Surface Analysis  (37 KB)
│   └── SOCENG OSINT TryHackMe Labs Links  (408 KB)
└── Araclar ve Notlar/
    ├── ARACLAR 20 Python Libraries Hattingh 2016  (4.1 MB)
    ├── ARACLAR AWS Penetration Testing Kali Linux  (36.1 MB)
    ├── ARACLAR Brain Theory Neural Networks Handbook  (33.6 MB)
    ├── ARACLAR BugBounty Wordlist Training  (2.5 MB)
    ├── ARACLAR CCD Forensics CheatSheet  (846 KB)
    ├── ARACLAR CEHv12 312-50v12 Ethical Hacking Exam Questions  (187 KB)
    ├── ARACLAR Compiler Book Thain 2023  (1.3 MB)
    ├── ARACLAR Cyberlaw Cheat Sheet Patents TradeSecrets  (128 KB)
    ├── ARACLAR Game Engine Gems 2 Graphics Rendering Techniques  (11.6 MB)
    ├── ARACLAR Hacking For Dummies 5th Edition  (8.6 MB)
    ├── ARACLAR Hydra Brute Force Guide  (3.6 MB)
    ├── ARACLAR Linux Commands CheatSheet  (24.9 MB)
    ├── ARACLAR MySQL Penetration Testing Guide  (3.3 MB)
    ├── ARACLAR Nessus Snort Ethereal OpenSourceSecurity  (7.1 MB)
    ├── ARACLAR Network Forensics Tracking Hackers  (19.8 MB)
    ├── ARACLAR Network Sniffing Project Wireshark Tcpdump  (88 KB)
    ├── ARACLAR Nmap Packet Trace Analysis  (2.2 MB)
    ├── ARACLAR Nmap Packet Trace Analysis  (2.7 MB)
    ├── ARACLAR OMLog Online Log Anomaly Detection Meta-learning  (5.9 MB)
    ├── ARACLAR PTCS2001 Proof Theory Proceedings  (2.5 MB)
    ├── ARACLAR Port Forwarding Tunneling Cheatsheet  (3.8 MB)
    ├── ARACLAR PowerShell Windows Cloud Compliance Cheatsheet  (1.3 MB)
    ├── ARACLAR Python Data Structures Cheat Sheet  (314 KB)
    ├── ARACLAR Reverse Shell Cheat Sheet  (67 KB)
    ├── ARACLAR Rogue AP Detection Guide  (64 KB)
    ├── ARACLAR SQL Server Analysis Services Succinctly  (2.9 MB)
    ├── ARACLAR Structured Analytic Techniques 2nd Edition  (10.6 MB)
    ├── ARACLAR Termux Ethical Hacking Guide  (314 KB)
    ├── ARACLAR Unix Commands CheatSheet  (365 KB)
    ├── ARACLAR Vi Editor Cheat Sheet  (600 KB)
    └── ARACLAR Wireshark Cheat Sheet Filters v1  (368 KB)
```

</details>

<details>
<summary><b>DEFANSIF GUVENLIK (BLUE TEAM)</b> — 109 belge</summary>

```
DEFANSIF GUVENLIK (BLUE TEAM)
├── SOC ve Olay Mudahelesi/
│   ├── SOC IR Automated Malware Response Playbook  (167 KB)
│   ├── SOC IR CTI CMM v1.0  (2.4 MB)
│   ├── SOC IR ChatGPT Incident Response  (1.1 MB)
│   ├── SOC IR CybersecurityAnalyst Interview Tips  (107 KB)
│   ├── SOC IR Cybersecurity Resume Essentials  (65 KB)
│   ├── SOC IR EDR Config vs Ransomware Testing  (1006 KB)
│   ├── SOC IR LLM Log Analysis Template Detection  (327 KB)
│   ├── SOC IR Linux Systemd Timers Analysis  (652 KB)
│   ├── SOC IR Log4j Incident Investigation Report  (2.7 MB)
│   ├── SOC IR Maltego Playbook Guide  (4.6 MB)
│   ├── SOC IR Manager Handbook 14 Steps V1.0  (3.6 MB)
│   ├── SOC IR NIDS Implementation Guide  (81 KB)
│   ├── SOC IR PurpleTeam Wazuh Win2016 Lab01  (3.7 MB)
│   ├── SOC IR Senior Cybersecurity Analyst Interview Prep  (149 KB)
│   ├── SOC IR Splunk Threat Hunting Techniques  (6.7 MB)
│   ├── SOC IR Threat Hunting Practical Guide  (5.8 MB)
│   └── SOC Organizational Structure Roles Responsibilities  (212 KB)
├── Adli Bilisim ve Malware Analizi/
│   ├── CEHv13 Module07 Malware Threats  (48.0 MB)
│   ├── Cybercrime Digital Forensics Investigation Guide  (6.9 MB)
│   ├── Cybersecurity Best Practices Guide  (374 KB)
│   ├── Cybersecurity Introduction for Care Providers  (732 KB)
│   ├── Digital Forensics Basics Guide  (3.6 MB)
│   ├── Digital Forensics First Responder Guidelines  (3.1 MB)
│   ├── Digital Forensics Interview Questions Answers  (162 KB)
│   ├── Digital Forensics Open Source Tools  (4.4 MB)
│   ├── FCC Small Business Cybersecurity Planning Guide  (562 KB)
│   ├── FORENSICS MALWARE Babuk Ransomware Analysis Report  (1.4 MB)
│   ├── FORENSICS MALWARE CrimeScience DigitalForensics HolisticView  (11.3 MB)
│   ├── FORENSICS MALWARE CyberPhysicalSecurity CriticalInfrastructure  (7.3 MB)
│   ├── FORENSICS MALWARE Cybersecurity Incident Disclosures 2011-2023  (5.4 MB)
│   ├── FORENSICS MALWARE DLP Interview Questions  (166 KB)
│   ├── FORENSICS MALWARE Digital Forensics Textbook  (32.8 MB)
│   ├── FORENSICS MALWARE EUREKHA Key Hacker Identification Method  (5.9 MB)
│   ├── FORENSICS MALWARE EssentialCybersecuritySolutions  (674 KB)
│   ├── FORENSICS MALWARE GAI Memory Analysis  (4.4 MB)
│   ├── FORENSICS MALWARE Go Reversing Analysis Bhack2021  (3.6 MB)
│   ├── FORENSICS MALWARE Iceland EXE Analysis Report  (2.9 MB)
│   ├── FORENSICS MALWARE L1 Analyst Training Log SSH Bruteforce  (137 KB)
│   ├── FORENSICS MALWARE Ludwig Little Black Book Computer Viruses  (1.4 MB)
│   ├── FORENSICS MALWARE Maldoc Analysis Example1  (1.3 MB)
│   ├── FORENSICS MALWARE Metasploit Penetration Testing Cookbook  (3.6 MB)
│   ├── FORENSICS MALWARE OSCAR SupplyChainPoisoningDetection  (986 KB)
│   ├── FORENSICS MALWARE PIXHELL AirGap CovertChannel Attack  (31.5 MB)
│   ├── FORENSICS MALWARE Stuxnet Techniques Analysis  (3.1 MB)
│   ├── FORENSICS MALWARE Top 14 Free Commercial Tools  (531 KB)
│   ├── FORENSICS MALWARE WMI Abuse Threat Actor Techniques  (1.4 MB)
│   ├── FORENSICS MALWARE YARA Rule Feature Extraction  (716 KB)
│   ├── FORENSICS MALWARE eNVMe SSD Attack Vectors  (6.3 MB)
│   ├── FORENSICS Malware Analysis Beginner Guide  (7.6 MB)
│   ├── FORENSICS Malware Analysis Techniques  (16.8 MB)
│   ├── FORENSICS Malware Analysis eBook  (31.2 MB)
│   ├── FORENSICS Malware FP FN TP TN Analysis  (12.8 MB)
│   ├── FORENSICS Malware File Recovery Tools  (78 KB)
│   ├── FORENSICS Malware Incident Handling Process  (284 KB)
│   ├── FORENSICS Malware Threat Hunting Playbook  (2.7 MB)
│   ├── FORENSICS Malware Types Detection Techniques  (3.0 MB)
│   ├── FORENSICS Malware Viruses Revealed  (4.9 MB)
│   ├── FORENSICS Malware Windows Troubleshooting  (4.1 MB)
│   ├── FORENSICS Mobile Malware Attacks Defense  (6.7 MB)
│   ├── FORENSICS Uttarakhand Open University Digital Forensics Textbook  (2.3 MB)
│   ├── HHS Malware Lesson6 License Info  (208 KB)
│   ├── Intel471 2024 Cyber Threat Report Forensics Malware  (4.8 MB)
│   ├── MalDev Academy Malware Forensics  (146.7 MB)
│   ├── Malware Analysis Project Cuckoo VirusTotal  (87 KB)
│   ├── NISTIR 7621r1 Small Business Cybersecurity Fundamentals  (1.0 MB)
│   ├── PLC Malware Web Based Attack Analysis  (13.9 MB)
│   ├── Practical Memory Forensics Jumpstart  (21.8 MB)
│   └── Ransomware Forensic Playbook  (1.1 MB)
├── Tehdit Avciligi ve Istihbarat/
│   ├── NIST SP800-53A r5 Security Privacy Controls Assessment  (6.3 MB)
│   ├── NIST SP 800-50r1 Cybersecurity Privacy Learning Program  (2.1 MB)
│   ├── Ransomware TTPs Kaspersky Threat Hunting Report  (4.6 MB)
│   ├── THREAT HUNTING Asian APT TTPs Kaspersky Report  (12.5 MB)
│   ├── THREAT HUNTING DIY Malware Analysis Platform  (3.6 MB)
│   ├── THREAT HUNTING Ethical Hacking Tactics Techniques  (5.8 MB)
│   ├── THREAT HUNTING ICS OpenSource INSM Monitoring  (1.8 MB)
│   ├── THREAT HUNTING Incident Response Interview Prep  (188 KB)
│   ├── THREAT HUNTING MITRE ATT CK Framework Alignment  (7.5 MB)
│   ├── THREAT HUNTING Maltego Incident Response Handbook  (4.1 MB)
│   ├── THREAT HUNTING Practical Threat Detection Engineering  (8.2 MB)
│   ├── THREAT HUNTING RansomHub Ransomware Advisory  (861 KB)
│   ├── THREAT HUNTING RiskBasedVulnerabilityMgmt  (444 KB)
│   ├── THREAT HUNTING SOC Essentials  (1.3 MB)
│   ├── THREAT HUNTING Security Maturity Business Enablement  (312 KB)
│   ├── THREAT HUNTING WorldClass Cybersecurity Center Strategies  (15.7 MB)
│   ├── THREAT HUNTING XFF Backdoor Analysis  (779 KB)
│   ├── Threat Hunting Incident Response Plan  (1.3 MB)
│   └── Threat Hunting Malware Analysis Techniques  (1.8 MB)
└── Guvenlik Sikilastirma ve Mimariler/
    ├── HARDENING MIMARI 24 Deadly Sins Software Security  (2.8 MB)
    ├── HARDENING MIMARI API Security Checklist Best Practices  (2.4 MB)
    ├── HARDENING MIMARI Access Control Types and Strategies  (173 KB)
    ├── HARDENING MIMARI CDPAS Assessment Standards 2024  (1.9 MB)
    ├── HARDENING MIMARI CompTIA SecurityPlus StudyNotes  (1.1 MB)
    ├── HARDENING MIMARI Compiler Optimization SideChannel Attacks  (1.1 MB)
    ├── HARDENING MIMARI CrossPartyDelegatedResources SecurityRisks  (7.1 MB)
    ├── HARDENING MIMARI CyberEssentials Compliance Guide  (7.9 MB)
    ├── HARDENING MIMARI DarkWeb Research Practices  (6.3 MB)
    ├── HARDENING MIMARI Data Breach Prevention Tips  (3.2 MB)
    ├── HARDENING MIMARI DevOps Automated Governance Architecture  (1.0 MB)
    ├── HARDENING MIMARI Digital Footprint Erasing Techniques  (774 KB)
    ├── HARDENING MIMARI IT Governance Data Security ISO27001 27002  (1.4 MB)
    ├── HARDENING MIMARI Infosec Best Practices  (4.3 MB)
    ├── HARDENING MIMARI PCI DSS v4.0.1 Requirements Testing  (4.3 MB)
    ├── HARDENING MIMARI Security Handbook Reference  (17.6 MB)
    ├── HARDENING MIMARI Server Security Checklist  (223 KB)
    ├── HARDENING MIMARI SmartAxe CrossChain Vulnerability Detection  (814 KB)
    ├── HARDENING MIMARI Surveillance Studies Handbook  (4.7 MB)
    ├── LLM Vulnerability Scanner Comparative Analysis  (4.2 MB)
    ├── Old Dominion University Information Security Program  (343 KB)
    └── SecurityPlus Q&A Hardening Architecture  (14.3 MB)
```

</details>

<details>
<summary><b>TEMEL BILGILER VE ALTYAPI</b> — 255 belge</summary>

```
TEMEL BILGILER VE ALTYAPI
├── Ag Temelleri ve Protokoller/
│   ├── AG Account Security Checklist  (622 KB)
│   ├── AG Common Ports Reference  (19 KB)
│   ├── AG Common Ports and Protocols CheatSheet  (732 KB)
│   ├── AG Communications Infrastructure Hardening Guide  (794 KB)
│   ├── AG EIGRP Protocol Configuration Guide  (67 KB)
│   ├── AG EmailHeaderAnalysis Techniques  (1.2 MB)
│   ├── AG Fundamentals 70 Vital Linux Commands  (151 KB)
│   ├── AG Fundamentals Basic Networking Tutorial  (266 KB)
│   ├── AG Fundamentals Bug Hunter Methodology V4  (87 KB)
│   ├── AG Fundamentals Common Ports  (94 KB)
│   ├── AG Fundamentals Computer Network Security Guide  (2.5 MB)
│   ├── AG Fundamentals Fault Tolerant IP MPLS Networks  (2.5 MB)
│   ├── AG Fundamentals Firewalls InternetSecurity  (3.1 MB)
│   ├── AG Fundamentals HCNA CBSN Security Q&A  (152 KB)
│   ├── AG Fundamentals Hacking Security Audit Guide  (9.6 MB)
│   ├── AG Fundamentals HighPerformanceBrowserNetworking  (16.4 MB)
│   ├── AG Fundamentals IPSec GRE OSPF Tunnel Config  (41 KB)
│   ├── AG Fundamentals IP Addressing Subnetting Workbook v2  (190 KB)
│   ├── AG Fundamentals IP Network Segmentation Quiz  (218 KB)
│   ├── AG Fundamentals IPv4 IPv6 Notes  (3.1 MB)
│   ├── AG Fundamentals IPv6 Protocol Guide  (53 KB)
│   ├── AG Fundamentals ISC2 CC Practice Questions  (329 KB)
│   ├── AG Fundamentals Internet Network Security  (2.3 MB)
│   ├── AG Fundamentals Junos Genius Practice Test  (131 KB)
│   ├── AG Fundamentals Network Enumeration Techniques  (3.6 MB)
│   ├── AG Fundamentals Networking  (34.1 MB)
│   ├── AG Fundamentals OSI Model  (100 KB)
│   ├── AG Fundamentals OSPF Routing Protocols Guide  (9.3 MB)
│   ├── AG Fundamentals RIP Routing Protocol Configuration  (46 KB)
│   ├── AG Fundamentals Shodan Complete Guide  (4.3 MB)
│   ├── AG Fundamentals TCPIP Guide  (28.2 MB)
│   ├── AG Fundamentals Tcpdump CheatSheet  (335 KB)
│   ├── AG Fundamentals UltraBroadband QoS  (10.0 MB)
│   ├── AG Fundamentals VLAN Tagging  (209 KB)
│   ├── AG Fundamentals Virtual Chassis Configuration  (204 KB)
│   ├── AG Fundamentals Website Fingerprinting Attack Oscar  (2.5 MB)
│   ├── AG Fundamentals Wireshark Display Filters  (38 KB)
│   ├── AG Fundamentals Wireshark Filters and Capture  (169 KB)
│   ├── AG Fundamentals Wireshark Traffic Analysis  (27.4 MB)
│   ├── AG Interior Routing Protocols IOS Configuration  (123 KB)
│   ├── AG InternetHistory LeinerEtAl 1997  (326 KB)
│   ├── AG OSPF Routing Exercises  (148 KB)
│   ├── AG PPP Configuration Troubleshooting Guide  (62 KB)
│   ├── AG TEMELLERI 200 125 Cisco Networking Fundamentals Exam Prep  (8.7 MB)
│   ├── AG TEMELLERI Hacking Attacks Reference Guide  (8.1 MB)
│   ├── AG TEMELLERI Juniper Networking Training Materials  (226 KB)
│   ├── AG TEMELLERI MPLS Configuration and Troubleshooting  (69 KB)
│   ├── AG TEMELLERI OSPF Protocol Overview  (93 KB)
│   ├── AG TEMELLERI OSPF Routing Protocol Guide  (358 KB)
│   ├── AG TEMELLERI Tcpdump Command Line Options  (37 KB)
│   ├── AG Telecom Network Technologies Bibliography  (14.6 MB)
│   ├── BGP Fundamentals and Troubleshooting  (69 KB)
│   ├── CCIE R S v5 Workbook Advanced Labs BGP Diagram  (184 KB)
│   ├── CCNA 200 301 Exam Cram Study Guide  (25.8 MB)
│   ├── CCNA 200 301 Exam Description Fundamentals  (226 KB)
│   ├── CCNA Command Cheat Sheet  (37 KB)
│   ├── CCNA Interview Questions Answers  (1.5 MB)
│   ├── CCNA Labs VLAN Routing Security  (7.2 MB)
│   ├── CCNAv7 Networking Fundamentals Guide  (32.9 MB)
│   ├── CCNAv7 Networking Security Automation Companion  (78.1 MB)
│   ├── CCNP Enterprise 300-410 ENARSI Study Guide  (193 KB)
│   ├── CEH V12 Exam Set 3 Network Security Questions  (1.9 MB)
│   ├── CISSP Certification Guide CheatSheet  (833 KB)
│   ├── CISSP Guide 10th Security Governance and Risk Management  (27.4 MB)
│   ├── Cisco Networking Handbook Routing Switching Security  (24.3 MB)
│   ├── Cisco Networking Handbook Routing Switching Security  (35.3 MB)
│   ├── Cisco Switch Command Reference AG TEMELLERI  (2.9 MB)
│   ├── Cisco Switch Configuration Commands  (125 KB)
│   ├── Cisco Switch Configuration Commands  (1.1 MB)
│   ├── CompTIA A Plus Cheat Sheet 220-1101 220-1102  (1.1 MB)
│   ├── CompTIA NetworkPlus N10-007 Exam Guide 2018  (8.4 MB)
│   ├── CompTIA NetworkPlus N10-008 CheatSheet  (581 KB)
│   ├── Computer Network Security Guide  (12.0 MB)
│   ├── Computing Systems Intro Bits Gates to CCpp Patt Patel  (10.8 MB)
│   ├── Cybersecurity Event Logging Best Practices  (1001 KB)
│   ├── HCNA Exam Dumps Access Control OSPF IPv6  (290 KB)
│   ├── HCNP-R&S-IERN H12-221 Practice Exam  (203 KB)
│   ├── HHS Services Connections License Agreement  (301 KB)
│   ├── IEEE 802.1D-2004 MAC Bridges Standard  (2.5 MB)
│   ├── IOS IPv4 Access Lists Configuration Guide  (43 KB)
│   ├── IPv4 Multicast IGMP PIM Configuration Guide  (45 KB)
│   ├── IPv4 Subnet CheatSheet CIDR Reference  (2.2 MB)
│   ├── IS-IS Routing Protocol Labs  (1.0 MB)
│   ├── JWD Hospital Network Upgrade Design Part1  (1.7 MB)
│   ├── Java2 Network Security IBM Redbook  (5.6 MB)
│   ├── Macchanger Anonsurf Commands Guide  (58 KB)
│   ├── MediaWiki Markup Reference Guide  (42 KB)
│   ├── MikroTik RouterOS Training Course Materials  (1.2 MB)
│   ├── Mobile Wireless Network Security Privacy  (3.3 MB)
│   ├── Network Address Translation NAT Configuration  (54 KB)
│   ├── Network Architecture Fundamentals  (512 KB)
│   ├── Network Fundamentals for Hackers  (34.6 MB)
│   ├── Networking Terminology Dictionary  (8.1 MB)
│   ├── Nmap Network Scanning Notes  (4.1 MB)
│   ├── OSI Model Cheat Sheet Networking Fundamentals  (942 KB)
│   ├── OSI Model Layers Acronyms CheatSheet  (453 KB)
│   ├── OSI Model Reference Chart Networking Fundamentals  (78 KB)
│   ├── OSPF IS-IS Link State Routing Principles Technologies  (14.9 MB)
│   ├── OSPF Interview Questions and Theory  (377 KB)
│   ├── OSPF RFC Demystified Guide  (2.8 MB)
│   ├── Post-Quantum DNSSEC Fragmentation QBF Technique  (567 KB)
│   ├── QoS Routing Wireless Sensor Networks  (3.8 MB)
│   ├── Quantum-Safe Signatureless DNSSEC SL-DNSSEC  (530 KB)
│   ├── RPKI Fort RCE Vulnerability Poster  (426 KB)
│   ├── SQL CheatSheet Basic Syntax Reference  (561 KB)
│   ├── SS7 Vulnerabilities and Exploitation Techniques  (7.3 MB)
│   ├── Scapy Packet Construction Guide  (35 KB)
│   ├── Small Office ISP Network Configuration  (196 KB)
│   ├── Subnetting Exercises and Solutions  (2.5 MB)
│   ├── US Intelligence Fundamentals 4th Edition  (3.3 MB)
│   ├── VPN Port Shadow Attack Exploit  (3.4 MB)
│   ├── WLAN Routing Protocol Comparison OPNET Simulation  (2.6 MB)
│   ├── Windows Command Line Cheat Sheet  (864 KB)
│   └── Wireless Network Security Resources  (5.7 MB)
├── Isletim Sistemleri (Linux Windows)/
│   ├── 101 Essential Linux Commands Guide  (764 KB)
│   ├── ASLR Effectiveness Analysis Operating Systems  (1.4 MB)
│   ├── ActiveDirectory Enumeration PowerShell HaboobTeam  (991 KB)
│   ├── ActiveDirectory Enumeration Powershell  (993 KB)
│   ├── Active Directory Hacking Techniques  (33.0 MB)
│   ├── Advanced Penetration Testing Medical Research Security  (6.3 MB)
│   ├── Bash Cookbook 1st Edition  (3.2 MB)
│   ├── Bash Cookbook Solutions Examples  (6.0 MB)
│   ├── Bash Level3 Control Structures CheatSheet  (124 KB)
│   ├── Bash Shell Tutorial Guide  (1.6 MB)
│   ├── Batch File Programming Techniques and Security Risks  (3.8 MB)
│   ├── Beginner Guide Ethical Hacking Computer Systems  (615 KB)
│   ├── BlackHatBash Scripting for Hackers Pentesters EarlyAccess  (6.2 MB)
│   ├── Bypassing AppLocker UAC via CMSTP Exploit  (1.8 MB)
│   ├── CISA FY23 RVA MITRE ATT&CK Analysis  (511 KB)
│   ├── C CPP Linux Memory Diagnostics  (8.1 MB)
│   ├── Checking PC COM Ports Windows Guide  (129 KB)
│   ├── Computer Security Internet Tools Jewels  (5.5 MB)
│   ├── Computer Security Internet Tools Jewels 2nd Edition  (161 KB)
│   ├── Cybersecurity Investigation Logging Strategies  (3.8 MB)
│   ├── DVWA Vulnerable Web Server Setup Guide  (726 KB)
│   ├── Dark Web Exploration Guide  (1.6 MB)
│   ├── Docker Container Pentesting Guide  (4.9 MB)
│   ├── EDR vs ZeroTrust Endpoint Security  (4.5 MB)
│   ├── Embedded C Programming Pico Microcontroller Guide  (867 KB)
│   ├── FFUF Web Enumeration Tool Guide  (3.6 MB)
│   ├── GenAI-Ethical-Hacking-Linux-Privilege-Escalation  (14.6 MB)
│   ├── HHS Ports Protocols Lesson3  (487 KB)
│   ├── HHS System Identification Lesson5  (237 KB)
│   ├── HTTP Enumeration Dirb Dirbuster Guide  (67 KB)
│   ├── Initial-Access-and-Privilege-Escalation-MS01-Scenario  (1.4 MB)
│   ├── Jenkins Penetration Testing Guide  (2.7 MB)
│   ├── Kali Linux Basic Security Testing  (13.8 MB)
│   ├── Kali Linux Security Testing Guide 2nd Edition  (16.3 MB)
│   ├── LinuxCommandLine Reference Guide  (2.0 MB)
│   ├── LinuxFromScratch Guide  (1.3 MB)
│   ├── LinuxFundamentals Training Guide  (6.7 MB)
│   ├── Linux April2024 Hacking Basics Python Kernel  (47.6 MB)
│   ├── Linux Bash Shell Scripting Recipes  (17.3 MB)
│   ├── Linux Command Line Cheatsheet  (1.1 MB)
│   ├── Linux Command Line Complete Introduction  (3.5 MB)
│   ├── Linux Complete Command Reference  (10.1 MB)
│   ├── Linux Essential Commands Handbook  (13.9 MB)
│   ├── Linux File Permissions Cheat Sheet  (342 KB)
│   ├── Linux Hands On Guide  (1.5 MB)
│   ├── Linux Kernel Programming Guide  (12.8 MB)
│   ├── Linux OSINT Beginner Course  (7.1 MB)
│   ├── Linux Persistence Techniques  (6.9 MB)
│   ├── Linux Privilege Escalation Cheatsheet  (2.6 MB)
│   ├── Linux Privilege Escalation Guide  (131 KB)
│   ├── Linux Privilege Escalation Techniques  (1.3 MB)
│   ├── Linux Professional Notes Guide  (844 KB)
│   ├── Linux Professional Notes Guide  (857 KB)
│   ├── Linux Shell Scripting Bible 3rd Edition  (17.0 MB)
│   ├── Linux Shell Scripting Cookbook  (3.1 MB)
│   ├── Linux Shell Scripting Examples  (55 KB)
│   ├── Linux Shell Scripting Tutorial  (170 KB)
│   ├── Linux Technical Interview Questions 200Plus  (239 KB)
│   ├── Linux Tips Tricks Guide  (1.2 MB)
│   ├── MCSA Windows Server 2012 R2 Study Guide  (31.3 MB)
│   ├── MSFvenom Payload Generator CheatSheet  (2.6 MB)
│   ├── MSI File Vulnerabilities Analysis  (3.8 MB)
│   ├── MSSQL Exploitation and Privilege Escalation  (495 KB)
│   ├── OSCP 2024 Complete Guide  (1.9 MB)
│   ├── Penetration Tester Coding Building Better Tools  (9.9 MB)
│   ├── Pentesters Promiscuous Notebook Pentesting Notes  (7.0 MB)
│   ├── PowerShell Notes for Professionals  (1.7 MB)
│   ├── PowerShell Professional Notes  (1.7 MB)
│   ├── Powershell CheatSheet Commands Guide  (1009 KB)
│   ├── Python Data Analysis McKinney  (8.3 MB)
│   ├── Python Programming Examples  (1.9 MB)
│   ├── Python for Kids Programming Introduction  (13.8 MB)
│   ├── SSH Commands Cheat Sheet  (1.5 MB)
│   ├── SSH Penetration Testing Guide  (2.7 MB)
│   ├── System Hacking Metasploit Exploits and Payloads  (7.0 MB)
│   ├── Tmux Installation and CheatSheet  (493 KB)
│   ├── TwingoSystems WebsiteHacking Presentation 2003  (511 KB)
│   ├── Unix Shell Scripting Bash Bourne Korn Guide  (4.3 MB)
│   ├── WiFi Hacking Kali Linux VirtualBox Guide  (599 KB)
│   ├── Windows10 Segment Heap Internals  (1.8 MB)
│   ├── Windows11 STIG Compliance PowerShell Guide  (393 KB)
│   ├── Windows Linux Privilege Escalation Training  (2.5 MB)
│   ├── Windows PowerShell Cookbook 3rd Edition  (15.4 MB)
│   ├── Windows Privilege Escalation Techniques  (2.7 MB)
│   ├── Windows Privilege Escalation Techniques  (347 KB)
│   └── Windows Privilege Escalation Techniques  (309 KB)
├── Programlama ve Scripting/
│   ├── 50 Useful Python Scripts  (426 KB)
│   ├── Cross-Site Scripting Vulnerabilities  (17.8 MB)
│   ├── HandsOn Concurrency with Rust  (3.5 MB)
│   ├── Python Networking Programming Guide  (27.9 MB)
│   ├── Python Pro Practices Programming Guide  (4.1 MB)
│   ├── Python Requests Essentials Programming Guide  (1.2 MB)
│   ├── Rust Standard Library Cookbook Recipes  (4.0 MB)
│   └── WASM Programming Techniques  (2.5 MB)
├── Kriptografi/
│   ├── API Hacking RESTful APIs Guide  (81 KB)
│   ├── Block Ciphers Cryptanalysis Feistel Ciphers STEA  (241 KB)
│   ├── Bluetooth Security Fundamentals  (1.5 MB)
│   ├── CEHv13 Module20 Cryptography  (53.7 MB)
│   ├── Crypto101 Introduction to Cryptography  (14.9 MB)
│   ├── Cryptography Embedded Systems Security  (17.6 MB)
│   ├── Cryptography Fundamentals Symmetric Asymmetric  (5.1 MB)
│   ├── Cryptography Symmetric Asymmetric PostQuantum Algorithms  (11.4 MB)
│   ├── EV Code Signing Cybercrime Market Analysis  (1.5 MB)
│   ├── Elliptic Curve Cryptography EndToEnd Systems  (187 KB)
│   ├── Hybrid TLSv1.3 PostQuantum Cryptography  (4.2 MB)
│   ├── IPsec Protocols Encryption Algorithms and Configuration  (58 KB)
│   ├── Information Security Principles Practice  (7.6 MB)
│   ├── Introduction to Cryptography Bierbrauer  (3.3 MB)
│   ├── KRIPTOGRAFI CloudStorage Security Vulnerabilities  (771 KB)
│   ├── KRIPTOGRAFI Exploiting Corporate VPN Clients for Remote Access  (40.4 MB)
│   ├── KRIPTOGRAFI The Code Book Singh  (1.8 MB)
│   ├── Konheim Computer Security Cryptography  (14.1 MB)
│   ├── NIST SP800-12 Intro Computer Security  (2.8 MB)
│   ├── Python Cryptography Hacking Techniques  (1.0 MB)
│   ├── QUIC VReverso Efficiency Improvements  (641 KB)
│   ├── SSL Certificate Understanding  (1.9 MB)
│   ├── SSLyze OpenSSL SSL TLS Security Analysis  (37 KB)
│   ├── Securing Cryptographic Libraries Against Attacks  (176 KB)
│   ├── TLS RPK Identity Misbinding Vulnerability  (1.1 MB)
│   ├── Tor DarkNet Anonymity NSA Spying  (682 KB)
│   └── WebAssembly vs LinuxContainers Kubernetes Security Efficiency  (1.5 MB)
└── Bulut ve Sanallastirma/
    ├── AWS Certified Developer Associate Exam Prep  (48 KB)
    ├── AWS Pentesting Guide  (295 KB)
    ├── CleanCode Principles Patterns Handbook  (30.3 MB)
    ├── Cloud Computing Security CEHv13 Module19  (57.6 MB)
    ├── Cloud Pentesting Cheatsheet Azure O365  (193 KB)
    ├── Cloud Provider Vulnerability Exploitation  (6.3 MB)
    ├── Cloud Recon Techniques and Tools  (1.5 MB)
    ├── Cloud Secret Management in SDLC  (967 KB)
    ├── Cloud Security Bug Bounty Recon Cheatsheet  (575 KB)
    ├── Cloud Security Engineer Roadmap 2024  (4.3 MB)
    ├── Cloud Unauthorized OAuth2 Vulnerabilities  (5.5 MB)
    ├── Cloud eBPF Verifier Fuzzing Lessons  (943 KB)
    ├── Container Runtime Security Performance Cost Analysis  (1.8 MB)
    ├── EncryptedDNS Implementation Guide CISA  (1.4 MB)
    ├── Kubernetes Cloud Orchestration IR Guide  (223 KB)
    ├── Kubernetes Security Observability Guide  (11.5 MB)
    ├── Metasploit 5.0 Penetration Testing Beginner Guide  (17.7 MB)
    ├── OCI Foundations IZ0 1085 Study Guide  (189 KB)
    ├── Predator-OS v3 Linux Penetration Testing Guide  (17.8 MB)
    └── SQL NoSQL Interview Questions  (10.9 MB)
```

</details>

<details>
<summary><b>SERTIFIKASYON VE KARIYER</b> — 217 belge</summary>

```
SERTIFIKASYON VE KARIYER
├── Offensive Security (OSCP-OSEP-OSWE)/
│   ├── CERT OFFSEC API Vulnerability Analysis Report  (17.7 MB)
│   ├── CERT OFFSEC Android Messenger 1Click Exploit Defense  (4.1 MB)
│   ├── CERT OFFSEC BlackHatPython 2ndEd  (13.7 MB)
│   ├── CERT OFFSEC EXP301 OSED Windows Exploit Dev  (8.6 MB)
│   ├── CERT OFFSEC Evading EDR Definitive Guide  (13.4 MB)
│   ├── CERT OFFSEC Exploit Development Lifecycle BSidesCbr24  (83.0 MB)
│   ├── CERT OFFSEC HackTheBox OSCP Roadmap  (88 KB)
│   ├── CERT OFFSEC Hacking APIs EarlyAccess  (39.4 MB)
│   ├── CERT OFFSEC Hardware Pentesting Guide  (8.0 MB)
│   ├── CERT OFFSEC Lab2 SQL Server Vulnerability Assessment  (184 KB)
│   ├── CERT OFFSEC Linux Kernel PageSpray Exploitation  (369 KB)
│   ├── CERT OFFSEC MegaCorpOne PenetrationTestReport 2013  (3.8 MB)
│   ├── CERT OFFSEC Modern Web Application Exploitation Techniques  (45.3 MB)
│   ├── CERT OFFSEC Novel Email Spoofing Attacks  (13.2 MB)
│   ├── CERT OFFSEC OSCP CheatSheet  (1.7 MB)
│   ├── CERT OFFSEC OSCP Enumeration Checklist  (5.2 MB)
│   ├── CERT OFFSEC OSCP Enumeration and Scanning Techniques  (487 KB)
│   ├── CERT OFFSEC OSCP Exam Prep Guide  (901 KB)
│   ├── CERT OFFSEC OSCP Penetration Test Report 2021  (8.1 MB)
│   ├── CERT OFFSEC OSCP Penetration Test Report 2022  (2.3 MB)
│   ├── CERT OFFSEC OSCP Resources Links  (67 KB)
│   ├── CERT OFFSEC OSCP Roadmap HackTheBox VulnShields  (1.2 MB)
│   ├── CERT OFFSEC OSEP Lab3 Network Scan Results  (209 KB)
│   ├── CERT OFFSEC OSEP Lab4 Network Scan Report  (382 KB)
│   ├── CERT OFFSEC OSEP Lab6 Network Scan Report  (621 KB)
│   ├── CERT OFFSEC OSEP Penetration Test Exam Report  (4.2 MB)
│   ├── CERT OFFSEC Python Training 2024  (30.1 MB)
│   ├── CERT OFFSEC Python Web Penetration Testing Cookbook  (1.8 MB)
│   ├── CERT OFFSEC VAPT Interview QnA Level1  (1.6 MB)
│   ├── CERT OFFSEC VAPT Interview Questions Answers Level1  (1.6 MB)
│   ├── CERT OFFSEC WarCon22 InitialAccess Evasion Tactics  (5.9 MB)
│   ├── CERT OFFSEC Windows Privilege Escalation Potatoes Techniques  (1.6 MB)
│   ├── CERT OFFSEC Wireless Attacks WiFu v3.0  (81.0 MB)
│   ├── CERT OFFSEC Wireless Attacks WiFu v3.0  (81.0 MB)
│   └── CERT OFFSEC Wireless Hacking 101 Guide  (4.2 MB)
├── EC-Council (CEH-CHFI-CPENT)/
│   ├── CERT ECCOUNCIL API Security White Hackers  (35.4 MB)
│   ├── CERT ECCOUNCIL CEH 312-50 Practice Questions  (2.1 MB)
│   ├── CERT ECCOUNCIL CEH Exam Summary Guide 2021  (7.4 MB)
│   ├── CERT ECCOUNCIL CEH V12 Exam Questions DNSSEC Non-Repudiation  (1.6 MB)
│   ├── CERT ECCOUNCIL CEH V12 Exam Questions USB Tools Encryption  (1.5 MB)
│   ├── CERT ECCOUNCIL CEH v12 500 QnA IDS Evasion  (4.8 MB)
│   ├── CERT ECCOUNCIL CEHv13 Version Change Document  (3.4 MB)
│   ├── CERT ECCOUNCIL CompTIA SecurityPlus 701 Last Minute Guide  (913 KB)
│   ├── CERT ECCOUNCIL Computer Forensics Investigating Data Image Files  (15.2 MB)
│   ├── CERT ECCOUNCIL CyberChef Zero to Hero Guide  (6.9 MB)
│   ├── CERT ECCOUNCIL Cybersecurity Strategies BestPractices  (11.5 MB)
│   ├── CERT ECCOUNCIL GrayHatHacking EthicalHackerHandbook  (12.6 MB)
│   ├── CERT ECCOUNCIL HackingTheHacker Grimes 2017  (1.3 MB)
│   ├── CERT ECCOUNCIL Hacking Exposed Malware Rootkits  (10.4 MB)
│   ├── CERT ECCOUNCIL KaliLinuxCookbook PenetrationTesting  (10.7 MB)
│   ├── CERT ECCOUNCIL Network Automation Python3  (4.2 MB)
│   ├── CERT ECCOUNCIL Ninja Hacking Penetration Testing Techniques  (9.9 MB)
│   ├── CERT ECCOUNCIL Virtual Pentesting Labs  (17.2 MB)
│   ├── CERT ECCOUNCIL Wireless Network Security Testing BackTrack  (4.3 MB)
│   └── CPENT Appendix  (442.8 MB)
├── CompTIA (Security+-CySA+-Network+)/
│   ├── CERT COMPTIA Linux Command Line Beginners Guide  (330 KB)
│   ├── CERT COMPTIA SY0-601 Study Guide  (33.6 MB)
│   ├── CERT COMPTIA SY0701 SecurityPlus PracticeExams  (3.1 MB)
│   ├── CERT COMPTIA SY0701 SecurityPlus PracticeExams v15  (3.1 MB)
│   ├── CERT COMPTIA SY0701 SecurityPlus Practice Questions Answers  (1.8 MB)
│   ├── CERT COMPTIA SY0701 SecurityPlus StudyGuide  (2.1 MB)
│   ├── CERT COMPTIA SY0 601 Practice Questions  (6.2 MB)
│   ├── CERT COMPTIA SY0 701 Practice Exam V9.02  (2.9 MB)
│   ├── CERT COMPTIA SY0 701 SecurityPlus Exam Dumps 2024  (2.6 MB)
│   ├── CERT COMPTIA SY0 701 Security Plus Practice Questions May2024  (4.2 MB)
│   ├── CERT COMPTIA SY0 701 Security Plus Study Guide  (6.8 MB)
│   ├── CERT COMPTIA SecurityPlus CheatSheet SY0-601  (569 KB)
│   ├── CERT COMPTIA SecurityPlus SY0-701 StudyGuide  (7.4 MB)
│   ├── CERT COMPTIA SecurityPlus SY0701 PracticeTests  (5.9 MB)
│   ├── CERT COMPTIA SecurityPlus SY0701 StudyGuide  (1.6 MB)
│   ├── CERT COMPTIA SecurityPlus SY0 601 Notes  (1.5 MB)
│   └── SY0-601 CompTIA Security Study Guide  (10.2 MB)
├── Cisco (CCNA-CCNP)/
│   ├── CERT CISCO 200-301 CCNA Practice Exam Questions  (1.4 MB)
│   ├── CERT CISCO 200-301 CCNA Practice Exam v2  (3.5 MB)
│   ├── CERT CISCO Advanced EIGRP IPv4 Configuration Lab  (707 KB)
│   ├── CERT CISCO CCDEv3 Practice Labs  (9.8 MB)
│   ├── CERT CISCO CCIE Data Center Lab Workbook v3  (37.4 MB)
│   ├── CERT CISCO CCIE Enterprise Infrastructure Foundation 2023  (106.8 MB)
│   ├── CERT CISCO CCNA2 Study Guide Module1 2  (80 KB)
│   ├── CERT CISCO CCNA 200 301 Exam Guide  (6.5 MB)
│   ├── CERT CISCO CCNA 200 301 Exam Review Guide  (39.7 MB)
│   ├── CERT CISCO CCNA 200 301 Lammle StudyGuide Vol2  (48.8 MB)
│   ├── CERT CISCO CCNA 200 301 Official Cert Guide  (157.1 MB)
│   ├── CERT CISCO CCNA 200 301 Official Cert Guide  (167.3 MB)
│   ├── CERT CISCO CCNA 200 301 Study Guide Lammle  (53.5 MB)
│   ├── CERT CISCO CCNA 200 301 Vol1 Official Cert Guide  (19.2 MB)
│   ├── CERT CISCO CCNA 200 301 Vol2 Labs Guide  (10.0 MB)
│   ├── CERT CISCO CCNA Advanced Routing Switching  (5.2 MB)
│   ├── CERT CISCO CCNA Certification Overview  (6.6 MB)
│   ├── CERT CISCO CCNA Exploration Companion Guide  (9.0 MB)
│   ├── CERT CISCO CCNA IOS Command Guide  (7.2 MB)
│   ├── CERT CISCO CCNA OSPF Summarization Lab  (75 KB)
│   ├── CERT CISCO CCNA Q&A Study Guide  (3.8 MB)
│   ├── CERT CISCO CCNA Routing Protocols Concepts  (10.3 MB)
│   ├── CERT CISCO CCNA Routing Switching Essentials  (14.3 MB)
│   ├── CERT CISCO CCNA Routing Switching Workbook  (5.2 MB)
│   ├── CERT CISCO CCNP CCIE Security Core 350-701 Cert Guide 2nd Edition  (14.3 MB)
│   ├── CERT CISCO CCNP Dynamic Static NAT Lab  (299 KB)
│   ├── CERT CISCO CCNP EIGRP Routing Lab 3.2.1  (269 KB)
│   ├── CERT CISCO CCNP Enterprise Overview  (72 KB)
│   ├── CERT CISCO CCNP Security Firewall 642-618 Cert Guide  (27.1 MB)
│   ├── CERT CISCO Cisco Cloud Infrastructure Architecture 2023  (66.9 MB)
│   ├── CERT CISCO Cisco Networking 200-301 Lammle Vol1  (15.3 MB)
│   ├── CERT CISCO CompTIA ServerPlus Certification Guide 2024  (6.5 MB)
│   ├── CERT CISCO DHCP NAT Configuration Lab  (277 KB)
│   ├── CERT CISCO Deploying QoS Cisco NextGen Networks  (12.7 MB)
│   ├── CERT CISCO EIGRP MD5 Authentication Lab  (105 KB)
│   ├── CERT CISCO EndToEndNetworkSecurity DefenseInDepth  (12.4 MB)
│   ├── CERT CISCO FirstHopRedundancy HSRP VRRP GLBP Protocols  (67 KB)
│   ├── CERT CISCO Hacker Challenge Incident Response Scenarios  (19.3 MB)
│   ├── CERT CISCO IOS Versioning Lifecycle Guide  (68 KB)
│   ├── CERT CISCO IS IS Protocol Analysis  (87 KB)
│   ├── CERT CISCO IT Essentials v6 Companion Guide  (41.8 MB)
│   ├── CERT CISCO IT Essentials v7 Companion Guide  (112.2 MB)
│   ├── CERT CISCO InfoSec Fundamentals Bibliography  (5.8 MB)
│   ├── CERT CISCO InterVLAN Routing Lab Guide  (127 KB)
│   ├── CERT CISCO KaliLinux PenetrationTesting  (6.5 MB)
│   ├── CERT CISCO NAT PAT Configuration CCNP Lab  (180 KB)
│   ├── CERT CISCO NetScaler Load Balancing Configuration  (2.3 MB)
│   ├── CERT CISCO NetworkSecurityBible 2005  (12.5 MB)
│   ├── CERT CISCO Penetration Testing Guide  (8.9 MB)
│   ├── CERT CISCO Penetration Testing Network Defense  (12.7 MB)
│   ├── CERT CISCO Practical Networking Skills  (1.9 MB)
│   ├── CERT CISCO Python Offensive Penetration Testing Guide  (8.9 MB)
│   ├── CERT CISCO SCOR350 701 Security Core Exam Guide  (10.7 MB)
│   ├── CERT CISCO Spanning Tree Protocol Analysis  (81 KB)
│   ├── CERT CISCO VLAN Configuration Troubleshooting  (58 KB)
│   ├── CERT CISCO VoIP Basics Configuration Guide  (76 KB)
│   ├── CERT CISCO Weissman CompTIA SecurityPlus Bio  (83.3 MB)
│   ├── CERT CISCO Windows Forensics Analysis  (4.3 MB)
│   ├── CERT CISCO Wireless Mesh Network Security  (10.4 MB)
│   └── CERT CISCO Wireless Network Hacking For Dummies  (11.0 MB)
├── SANS ve GIAC/
│   ├── CERT SANS Accidental Guerrilla Book  (2.7 MB)
│   ├── CERT SANS DLL Hijacking Overview  (249 KB)
│   ├── CERT SANS Google Dorking Techniques Guide  (222 KB)
│   ├── CERT SANS GrayHatHacking 5thEd ExploitDevTechniques  (45.7 MB)
│   ├── CERT SANS PowerShell CheatSheet  (109 KB)
│   ├── CERT SANS SEC511 Continuous Monitoring Security Operations 2023  (76.1 MB)
│   ├── CERT SANS SEC522 Book1 Security Training Material  (23.3 MB)
│   ├── CERT SANS SEC522 Book2 Training Material  (22.4 MB)
│   ├── CERT SANS SEC522 Book3 Security Training Notes  (26.6 MB)
│   ├── CERT SANS SEC522 Book4 Security Training Materials  (22.7 MB)
│   ├── CERT SANS SEC522 Book5 Training Material  (23.9 MB)
│   ├── CERT SANS SEC522 Book6 InformationSecurityTraining  (18.2 MB)
│   ├── CERT SANS SEC560 Enterprise Penetration Testing Book1 2022  (7.5 MB)
│   ├── CERT SANS SEC560 Enterprise Penetration Testing Book2 2022  (7.1 MB)
│   ├── CERT SANS SEC560 Penetration Testing Book3 2022  (7.6 MB)
│   ├── CERT SANS SEC560 Penetration Testing Workbook Sections 1-3 2022  (19.4 MB)
│   ├── CERT SANS SQLInjection Attacks Defense Guide  (6.4 MB)
│   ├── CERT SANS Web Security Testing Guide Splaine 2002  (2.6 MB)
│   ├── CERT SANS Windows Process Analysis Guide  (1.5 MB)
│   ├── CERT SANS Zero Day Exploit Countdown to Darkness  (3.7 MB)
│   └── CERT SANS iOS Mobile Forensics Investigators Guide  (20.0 MB)
├── Diger Sertifikasyonlar (CISSP-AWS-Oracle)/
│   ├── CERT DIGER 2024 Threat Exposure Mgmt Report  (11.6 MB)
│   ├── CERT DIGER Active Directory Attack Techniques  (2.3 MB)
│   ├── CERT DIGER Active Directory Beginners Guide  (1.8 MB)
│   ├── CERT DIGER AntiHackerToolkit 4thEd  (27.1 MB)
│   ├── CERT DIGER Attacking Active Directory with Linux  (2.9 MB)
│   ├── CERT DIGER Automating DevOps with GitLab CI CD  (27.2 MB)
│   ├── CERT DIGER Botnet Threats and Mitigation  (7.0 MB)
│   ├── CERT DIGER Botnets WebApps Hacking  (7.0 MB)
│   ├── CERT DIGER BugBounty HowTo Guide  (1.4 MB)
│   ├── CERT DIGER CISSP Study Guide 3rd Edition  (14.2 MB)
│   ├── CERT DIGER CISSP Study Guide 8th Edition  (9.5 MB)
│   ├── CERT DIGER CISSP Technology Workbook v1  (7.3 MB)
│   ├── CERT DIGER CompTIA CySA Study Guide CS0-003  (24.7 MB)
│   ├── CERT DIGER Computer Virus Malware Attacks Guide  (2.6 MB)
│   ├── CERT DIGER Copyright Notice HackingForDummies  (9.3 MB)
│   ├── CERT DIGER CounterSEVeillance SEV-SNP SideChannel Attack  (331 KB)
│   ├── CERT DIGER Cybersecurity Interview Prep Guide  (3.5 MB)
│   ├── CERT DIGER Database Attack Techniques and Defense  (552 KB)
│   ├── CERT DIGER Endgame Adversary Hunting Handbook  (5.2 MB)
│   ├── CERT DIGER GrayHatHacking EthicalHackerHandbook 3rdEd  (12.2 MB)
│   ├── CERT DIGER Hacking Exposed Linux Security Guide  (10.5 MB)
│   ├── CERT DIGER Hacking Exposed Network Security  (8.0 MB)
│   ├── CERT DIGER Hacking Exposed Windows Security  (9.1 MB)
│   ├── CERT DIGER Hacking Exposed Windows Security  (6.0 MB)
│   ├── CERT DIGER Hydra Tool Guide  (2.4 MB)
│   ├── CERT DIGER IT Manager InfoSec Essentials  (2.3 MB)
│   ├── CERT DIGER InfoSec Handbook Resource List  (42.9 MB)
│   ├── CERT DIGER Iris Scanner Biometric Security QnA  (7.7 MB)
│   ├── CERT DIGER KaliLinux CTF Blueprints  (3.5 MB)
│   ├── CERT DIGER Kali Linux CTF Blueprints  (3.5 MB)
│   ├── CERT DIGER LinkedIn Optimization Guide  (78 KB)
│   ├── CERT DIGER Malware Analyst Cookbook  (8.9 MB)
│   ├── CERT DIGER MySQL Admin Security BestPractices  (18.1 MB)
│   ├── CERT DIGER Network Hack Proofing Guide  (8.8 MB)
│   ├── CERT DIGER NextGen SOC QRadar Guide  (10.1 MB)
│   ├── CERT DIGER OCI Architect Associate Exam Dump V12.95  (305 KB)
│   ├── CERT DIGER OSINT RealWorldValue  (53.1 MB)
│   ├── CERT DIGER Oracle Autonomous Database 1z0-931 Exam Prep  (192 KB)
│   ├── CERT DIGER Oracle Autonomous Database Cloud 2019 Specialist Exam Questions  (211 KB)
│   ├── CERT DIGER Oracle Autonomous Database Exam 1Z0-931 Answers  (206 KB)
│   ├── CERT DIGER Oracle Autonomous Database Exam Questions  (232 KB)
│   ├── CERT DIGER Oracle Cloud Infrastructure Security Quiz  (66 KB)
│   ├── CERT DIGER Practical Hacking Techniques Countermeasures  (144.0 MB)
│   ├── CERT DIGER Quantum Algorithms LFSR Cryptanalysis  (2.5 MB)
│   ├── CERT DIGER RedTeaming GitHub Repos List  (298 KB)
│   ├── CERT DIGER Serious Cryptography Fundamentals  (18.7 MB)
│   ├── CERT DIGER Shellcoders Handbook Exploiting Security Holes  (8.7 MB)
│   ├── CERT DIGER Snort3 IDS IPS Guide  (12.3 MB)
│   ├── CERT DIGER Snort IDS IPS Lab Manual  (139 KB)
│   ├── CERT DIGER Syngress Publishing Solutions  (11.7 MB)
│   └── CERT DIGER Web Application Hacking Exposed  (7.6 MB)
└── Mulakat ve Kariyer/
    ├── MULAKAT 70 Tough Interview Qs As Neha Malhotra  (473 KB)
    ├── MULAKAT Cracking the Coding Interview  (3.2 MB)
    ├── MULAKAT Cybercrime Research Methodologies Ethics Approaches  (6.1 MB)
    ├── MULAKAT Cybersecurity Education Magazine Issue18  (32.6 MB)
    ├── MULAKAT Drone Technology AEC Guide  (32.4 MB)
    ├── MULAKAT FM2-22.3 Human Intelligence Collector Operations  (4.6 MB)
    ├── MULAKAT HHS Internet Legalities Ethics License  (290 KB)
    ├── MULAKAT Influence Science Practice 5th Edition  (22.2 MB)
    ├── MULAKAT Interview Questions Guide  (3.8 MB)
    ├── MULAKAT MATLAB Demystified McMahon  (4.6 MB)
    ├── MULAKAT Penetration Testing Report Writing Approaches  (7.8 MB)
    ├── MULAKAT Python Interview Questions Answers  (212 KB)
    └── MULAKAT Security Plus 701 Study Plan  (132 KB)
```

</details>

<details>
<summary><b>OZEL KONULAR VE RAPORLAR</b> — 78 belge</summary>

```
OZEL KONULAR VE RAPORLAR
├── Bug Bounty/
│   ├── BUG BOUNTY Awesome Hacker Search Engines  (1.1 MB)
│   ├── Bug Bounty Beginner Roadmap  (188 KB)
│   └── HTB Certified Bug Bounty Hunter Jayant Kumawat Cert 57096A90A7  (278 KB)
├── Yapay Zeka ve Siber Guvenlik/
│   ├── AI ChatGPT Automated SPA Cryptosystem Analysis  (2.3 MB)
│   ├── AI Cybersecurity Prompt Dataset CySecBench  (8.0 MB)
│   ├── AI Cybersecurity Transformation GenAI Report 2024  (4.5 MB)
│   ├── AI ML Cloud Computing Debugging Python  (7.5 MB)
│   ├── AI ML Security Principles  (10.1 MB)
│   ├── AI Model Weight Security RAND Report  (1.2 MB)
│   ├── AI Risk Management in Financial Services  (9.1 MB)
│   ├── AI Security Benchmarking OpenAI o1 Models  (131 KB)
│   ├── AI Security ChatGPT Prompts Guide  (1.6 MB)
│   ├── AI Security ConfusedPilot RAG Vulnerabilities  (1.0 MB)
│   ├── AI Security Deepfake Threats  (2.3 MB)
│   ├── AI Security Deepfakes LawEnforcement Europol Report  (2.1 MB)
│   ├── AI Security Encrypted Traffic Classification MH-Net  (498 KB)
│   ├── AI Security GAN Cookbook  (8.8 MB)
│   ├── AI Security GPT Trustworthiness Assessment  (38.3 MB)
│   ├── AI Security IC OSINT Strategy 2024-2026  (1.0 MB)
│   ├── AI Security LLM Backdoor Defense W2SDefense  (5.8 MB)
│   ├── AI Security LLM Crypto Protocol Vulnerability Detection  (463 KB)
│   ├── AI Security LLM Fingerprinting HideAndSeek  (530 KB)
│   ├── AI Security LLM Generated Hardware Trojans  (1.0 MB)
│   ├── AI Security LLM SOAR Implementation  (2.1 MB)
│   ├── AI Security Nova LLM Assembly Code Analysis  (7.2 MB)
│   ├── AI Security RAG Hijacking Attacks  (661 KB)
│   ├── AI Security RAG Jailbreaking Worm Attacks  (4.2 MB)
│   ├── AI Security RAGent Access Control Policy Generation  (1.1 MB)
│   ├── AI Security RedTeaming LLMs  (2.0 MB)
│   ├── AI Security ScamChatbot Analysis  (748 KB)
│   └── AI Strategic Competition Risks Opportunities  (6.8 MB)
├── Raporlar Sunumlar ve Makaleler/
│   ├── CIA Espionage Techniques Dulles Report  (4.7 MB)
│   ├── Ethical Malware Development Guide  (27.7 MB)
│   ├── Ethical Malware Development Guide  (51.5 MB)
│   ├── GenerativeAI Openness EUAI Act Assessment  (2.0 MB)
│   ├── Google Hacking Penetration Testers Guide  (32.2 MB)
│   ├── Mastering React Web App Development  (3.5 MB)
│   ├── OSINT History Analysis Report  (764 KB)
│   ├── US Semiconductor Exports Russia Ukraine Senate Report 2024  (1.2 MB)
│   └── Windows Persistence Techniques  (9.8 MB)
└── Kategorisiz ve Genel/
    ├── AYBU Wireless Network Setup Guide  (1.4 MB)
    ├── Access Control Fundamentals  (43.9 MB)
    ├── Asset Security Best Practices  (13.7 MB)
    ├── CEHv12 2022 Exam Dumps  (4.8 MB)
    ├── CEHv13 Module03 Network Scanning  (24.0 MB)
    ├── CEHv13 Module05 Vulnerability Analysis  (14.4 MB)
    ├── CEHv13 Module10 DoS Attacks  (13.6 MB)
    ├── CENG Department Course Schedule 2024-2025 Fall  (759 KB)
    ├── Cloud Hacking Techniques  (17.7 MB)
    ├── Cross-Site Request Forgery Vulnerability  (8.2 MB)
    ├── Cybersecurity Bounty Hunting Tips  (18.3 MB)
    ├── Cybersecurity Business Industry Risks  (3.7 MB)
    ├── Cybersecurity Network Integration Guide  (8.8 MB)
    ├── Cybersecurity Risk Metric Scenarios  (3.8 MB)
    ├── Data Structures Guide  (4.9 MB)
    ├── HackLearners Brochure  (26.2 MB)
    ├── Hacking System Vulnerabilities  (25.3 MB)
    ├── Hide01 IR Cybersecurity Encoding Filtering Techniques  (17.6 MB)
    ├── KATEGORISIZ Fundamentals  (49.2 MB)
    ├── KATEGORISIZ QoS Models and Markings Guide  (85 KB)
    ├── MS01-v3 WsoO2 Security Document  (1.6 MB)
    ├── Maltego POI Investigation CheatSheet  (2.1 MB)
    ├── Markdown Formatting Guide  (43 KB)
    ├── Multi-Factor Authentication Guide  (978 KB)
    ├── NetworkSecurity Notes  (21.3 MB)
    ├── Network Fundamentals  (33.3 MB)
    ├── OSEE Vulnerabilities Guide  (41.2 MB)
    ├── Prepaway 102q Exam Dump  (6.5 MB)
    ├── Project Stage 0 Git Repo Setup Guide  (82 KB)
    ├── Propaganda Persuasion 7th Edition  (1.3 MB)
    ├── Secure Network Design Best Practices  (11.1 MB)
    ├── Securing Communications Collaboration Solutions  (3.0 MB)
    ├── Security Assessment Report  (19.7 MB)
    ├── TheCubeMethod Powerlifting Program  (4.0 MB)
    ├── Turkey AI AutonomousDriving ChipDesign TrainingProgram Extension  (414 KB)
    ├── Vulnerability Assessment Methods Tools  (8.6 MB)
    ├── WAF Bypass Techniques  (1.1 MB)
    └── WAN Remote Access Security Best Practices  (24.1 MB)
```

</details>

<!-- KATALOG:BITIS -->

## Lisans

MIT — bkz. [LICENSE](LICENSE).
