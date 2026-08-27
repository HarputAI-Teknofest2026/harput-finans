# Harput Finans

**Harput Finans**, katılım bankalarının finansman ürünleri ve kampanyalarını resmî kaynaklardan toplayan, doğal dil işleme ve yapay zekâ yöntemleriyle yapılandırılmış veriye dönüştüren, bankalar arası karşılaştırma yapabilen ve kullanıcıya web tabanlı bir **AI Asistan** üzerinden sunan karar destek platformudur.

Proje, **TEKNOFEST 2026 Yapay Zeka Dil Ajanları Yarışması – 2. Senaryo** kapsamında geliştirilmiştir.

---

## İçindekiler

* [Proje Hakkında](#proje-hakkında)
* [Problem](#problem)
* [Geliştirilen Çözüm](#geliştirilen-çözüm)
* [Temel Özellikler](#temel-özellikler)
* [Sistem Akışı](#sistem-akışı)
* [Veri Seti](#veri-seti)
* [Desteklenen Katılım Bankaları](#desteklenen-katılım-bankaları)
* [Standart Veri Şeması](#standart-veri-şeması)
* [Proje Klasör Yapısı](#proje-klasör-yapısı)
* [app/discovery](#appdiscovery)
* [app/scrapers](#appscrapers)
* [app/processors](#appprocessors)
* [app/dynamic_extractor](#appdynamic_extractor)
* [data/final_banks](#datafinal_banks)
* [Colab Dosyaları](#colab-dosyaları)
* [AI Asistan](#ai-asistan)
* [Bilgi Çıkarımı](#bilgi-çıkarımı)
* [Web Arayüzü](#web-arayüzü)
* [API Yapısı](#api-yapısı)
* [Kullanılan Yapay Zeka Modelleri](#kullanılan-yapay-zeka-modelleri)
* [On-Premise Yaklaşımı](#on-premise-yaklaşımı)
* [Teknolojiler](#teknolojiler)
* [Kurulum](#kurulum)
* [Lisans](#lisans)

---

# Proje Hakkında

Katılım bankaları finansman ürünleri ve kampanyalarını kendi resmî web sitelerinde yayınlamaktadır.

Ancak bankalar arasında;

* sayfa yapıları,
* kullanılan finansal ifadeler,
* kategori isimleri,
* kampanya açıklamaları,
* vade gösterimleri,
* kâr payı ifadeleri,
* ücret ve masraf tanımları,
* kampanya avantajları

standart değildir.

Örneğin aynı finansal bilgi farklı kaynaklarda;

```text
%2,05 kâr payı oranı
% 2.05 kâr payı
2.05 % kâr oranı
avantajlı kâr payı fırsatı
```

gibi farklı biçimlerde ifade edilebilir.

Harput Finans bu dağınık verileri ortak bir yapıya dönüştürerek farklı katılım bankalarının ürünlerinin aynı sistem üzerinden incelenebilmesini sağlar.

---

# Problem

Bir banka çalışanının veya kullanıcının farklı katılım bankalarının finansman seçeneklerini karşılaştırmak istemesi durumunda her bankanın web sitesini ayrı ayrı incelemesi gerekmektedir.

Bu durum özellikle;

* konut finansmanı,
* taşıt finansmanı,
* ihtiyaç finansmanı,
* işyeri finansmanı,
* arsa finansmanı,
* alışveriş finansmanı,
* eğitim finansmanı,
* kart kampanyaları,
* indirim kampanyaları,
* alışveriş puanı kampanyaları

gibi çok sayıda ürün ve kampanya bulunduğunda manuel olarak yönetilmesi zor bir sürece dönüşmektedir.

Harput Finans'ın temel amacı bu süreci otomatikleştirmektir.

---

# Geliştirilen Çözüm

Harput Finans uçtan uca aşağıdaki işlemleri gerçekleştirir:

```text
Katılım Bankalarının
Resmî Web Siteleri
        │
        ▼
Veri Keşfi ve
Web Scraping
        │
        ▼
Ham Finansman /
Kampanya Metinleri
        │
        ▼
Bilgi Çıkarımı
        │
        ▼
Normalizasyon
        │
        ▼
Validasyon ve
Kalite Kontrol
        │
        ▼
Banka Bazlı
Final Veri Setleri
        │
        ▼
Master Dataset
        │
        ├─────────────► Sistem & Veri
        │
        ├─────────────► Bilgi Çıkarımı
        │
        └─────────────► AI Asistan
                               │
                               ▼
                        Kullanıcı Sorusu
                               │
                               ▼
                      Filtreleme / Arama /
                        Karşılaştırma
                               │
                               ▼
                        Kaynaklı Yanıt
```

---

# Temel Özellikler

## 1. Çoklu Banka Veri Toplama

Katılım bankalarının resmî web sitelerindeki finansman ve kampanya sayfaları banka yapısına uygun scraperlar kullanılarak toplanır.

---

## 2. Finansal Bilgi Çıkarımı

Doğal dilde bulunan finansman metinlerinden karar vermede kullanılabilecek alanlar çıkarılır.

Örneğin:

```text
Yeni müşterilerimize özel %2,89 kâr payı oranıyla
250.000 TL'ye kadar 24 ay vadeli finansman...
```

gibi bir metin içerisinden;

```text
Kâr Payı Oranı → %2,89
Finansman Tutarı → 250.000 TL'ye kadar
Vade → 24 ay
Hedef Kitle → Yeni müşteriler
Para Birimi → TL
```

gibi yapılandırılmış alanlar oluşturulabilir.

---

## 3. Veri Normalizasyonu

Farklı bankalardan gelen veriler ortak veri şemasına dönüştürülür.

Böylece farklı kaynaklardaki aynı anlama sahip bilgiler karşılaştırılabilir hale gelir.

---

## 4. Finansman Kategorilerinin Canonical Hale Getirilmesi

Finansman ürünleri ortak kategoriler altında sınıflandırılır.

Master veri setinde kullanılan canonical finansman kategorileri arasında:

* `IHTIYAC_FINANSMANI`
* `KONUT_FINANSMANI`
* `TASIT_FINANSMANI`
* `ISYERI_FINANSMANI`
* `ARSA_FINANSMANI`
* `ALISVERIS_FINANSMANI`
* `EGITIM_FINANSMANI`
* `BES_TEMINATLI_FINANSMAN`
* `YATIRIM_FINANSMANI`
* `KENTSEL_DONUSUM_FINANSMANI`
* `TOKI`
* `ENERJI_FINANSMANI`

bulunmaktadır.

---

## 5. Bankalar Arası Karşılaştırma

Sistem farklı bankalardaki benzer finansman ürünlerini ortak kriterler üzerinden karşılaştırabilir.

Örneğin:

* kâr payı oranı,
* finansman oranı,
* finansman tutarı,
* vade,
* taksit sayısı,
* masraf bilgileri,
* kampanya avantajları,
* hedef müşteri,
* ürün koşulları

karşılaştırma sırasında kullanılabilir.

---

## 6. AI Asistan

Kullanıcı sistemdeki veri şemasını bilmek zorunda değildir.

Doğal dilde;

```text
Konut finansmanı seçeneklerini göster.
```

veya;

```text
Kuveyt Türk konut finansmanlarını göster.
```

veya;

```text
500.000 TL araç finansmanı için
24 ay vadede hangi seçenekler var?
```

gibi sorular sorabilir.

AI Asistan kullanıcının isteğini yorumlar ve ilgili yapılandırılmış veri üzerinden sonuç üretir.

---

## 7. Multi-Turn Konuşma

AI Asistan konuşma durumunu koruyabilmektedir.

Örneğin:

```text
Kullanıcı:
Konut finansmanı seçeneklerini göster.

Kullanıcı:
Sadece Kuveyt Türk olanları göster.
```

İkinci mesajda tekrar "konut finansmanı" ifadesinin yazılması gerekmez.

Sistem önceki konuşmanın kapsamını kullanarak isteği yorumlar.

---

## 8. Kaynaklı Yanıt

Finansal bilgi sunulurken kayıtların resmî kaynak URL'leri korunmaktadır.

Bu yaklaşım ile kullanıcının sunulan bilginin asıl banka sayfasına ulaşabilmesi hedeflenmektedir.

---

## 9. Eksik Veri Güvenliği

Kaynak metinde bulunmayan bilgiler tahmin edilerek oluşturulmaz.

Eksik alanlar boş bırakılır.

Bu yaklaşım özellikle finansal verilerde yapay zekâ kaynaklı yanlış bilgi üretme riskini azaltmayı amaçlamaktadır.

---

# Sistem Akışı

Harput Finans üç ana kullanıcı modülü üzerine kuruludur.

```text
                 HARPUT FİNANS
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
      AI Asistan    Bilgi       Sistem &
                   Çıkarımı       Veri
          │            │            │
          ▼            ▼            ▼
      Soru-Cevap    Serbest      Dataset
      Karşılaştırma  Metin        İstatistik
      Öneri          Analizi      Görüntüleme
```

---

# Veri Seti

Harput Finans master veri seti toplam:

**10 katılım bankasını**

kapsamaktadır.

Toplam veri:

```text
530 kayıt
```

Bunun:

```text
116'sı finansman ürünü
414'ü kampanya
```

kaydından oluşmaktadır.

Master dataset:

```text
data/final_banks/katilim_finans_master.json
```

dosyasında bulunmaktadır.

---

# Desteklenen Katılım Bankaları

| Katılım Bankası                     | Finansman | Kampanya |  Toplam |
| ----------------------------------- | --------: | -------: | ------: |
| Adil Katılım Bankası A.Ş.           |         1 |        0 |       1 |
| Albaraka Türk Katılım Bankası A.Ş.  |        17 |       46 |      63 |
| Dünya Katılım Bankası A.Ş.          |         6 |       43 |      49 |
| Hayat Finans Katılım Bankası        |         3 |       11 |      14 |
| Kuveyt Türk Katılım Bankası A.Ş.    |        30 |       73 |     103 |
| T.O.M. Katılım Bankası A.Ş.         |         3 |       50 |      53 |
| Türkiye Emlak Katılım Bankası A.Ş.  |        12 |       63 |      75 |
| Türkiye Finans Katılım Bankası A.Ş. |        16 |       15 |      31 |
| Vakıf Katılım Bankası A.Ş.          |         8 |       26 |      34 |
| Ziraat Katılım Bankası A.Ş.         |        20 |       87 |     107 |
| **TOPLAM**                          |   **116** |  **414** | **530** |

---

# Standart Veri Şeması

Finansman ve kampanya kayıtları mümkün olduğunca ortak alanlar üzerinden tutulmaktadır.

Temel veri alanları:

```text
banka
kayit_turu
urun_adi
urun_kategorisi

kar_payi_orani
finansman_orani
finansman_tutari
vade
taksit_sayisi
masraf_bilgisi

kampanya_turu
kampanya_avantaji
kampanya_suresi

hedef_kitle
para_birimi
kosullar

kaynak_url
ham_metin
```

## Alanların Açıklamaları

### `banka`

Kaydın ait olduğu katılım bankasını belirtir.

---

### `kayit_turu`

Kaydın;

```text
finansman
```

veya;

```text
kampanya
```

olduğunu belirtir.

---

### `urun_adi`

Finansman ürünü veya kampanyanın adı.

---

### `urun_kategorisi`

Ürünün banka tarafından sunulduğu kategori.

---

### `kar_payi_orani`

Metinde açıkça belirtilen kâr payı oranlarını içerir.

---

### `finansman_orani`

Finansman oranı açıkça belirtiliyorsa ilgili değerleri içerir.

---

### `finansman_tutari`

Finansman için belirtilen tutar veya limitleri içerir.

---

### `vade`

Finansmana ilişkin vade seçeneklerini içerir.

---

### `taksit_sayisi`

Özellikle kart ve kampanya metinlerinde bulunan taksit sayılarını içerir.

---

### `masraf_bilgisi`

Tahsis ücreti, dosya masrafı ve benzeri maliyet bilgilerini içerir.

---

### `kampanya_turu`

Kaydın kampanya türünü belirtir.

---

### `kampanya_avantaji`

Kullanıcıya sağlanan;

* indirim,
* ödül,
* puan,
* ücretsiz hizmet,
* masraf avantajı

gibi faydaları içerir.

---

### `kampanya_suresi`

Kampanyanın geçerli olduğu tarih aralığını ifade eder.

---

### `hedef_kitle`

Kampanyanın veya finansmanın hedeflediği kullanıcı grubunu içerir.

Örneğin:

```text
Yeni müşteriler
Bireysel müşteriler
Maaş müşterileri
Belirli kart sahipleri
```

---

### `para_birimi`

Finansal değerlerde kullanılan para birimlerini içerir.

---

### `kosullar`

Üründen veya kampanyadan faydalanmak için gereken şartları içerir.

---

### `kaynak_url`

Bilginin alındığı resmî banka sayfasıdır.

---

### `ham_metin`

Bilgi çıkarımı yapılmadan önce elde edilen kaynak metni içerir.

Bu alan veri doğrulama ve geriye dönük kontrol için korunmaktadır.

---

# Finansman Canonical Alanları

Finansman kayıtlarında temel alanlara ek olarak:

```text
_canonical_category
_canonical_subtype
_semantic_tags
```

alanları bulunmaktadır.

### `_canonical_category`

Bankaların birbirinden farklı kategori isimlerini ortak finansman kategorilerine dönüştürür.

### `_canonical_subtype`

Ana kategorinin daha spesifik alt türünü belirtir.

### `_semantic_tags`

Finansman ürününün anlamsal özelliklerini belirten etiketleri içerir.

Bu alanlar AI Asistan'ın banka terminolojisinden bağımsız biçimde ürün bulabilmesine yardımcı olur.

---

# Kampanya Canonical Alanları

Kampanya kayıtlarında ayrıca:

```text
_campaign_categories
_campaign_benefit_types
_campaign_semantic_tags
_campaign_scope

_campaign_start_date
_campaign_end_date
_campaign_date_parse_status
_campaign_date_semantics
_campaign_temporal_status
_campaign_date_source

_campaign_comparison_metrics
```

alanları kullanılmaktadır.

Bu alanlar kampanyaların;

* kategorisinin belirlenmesi,
* avantaj tipinin anlaşılması,
* tarih durumunun yorumlanması,
* aktiflik süresinin belirlenmesi,
* karşılaştırılabilir metriklerin oluşturulması

amacıyla kullanılmaktadır.

---

# Proje Klasör Yapısı

```text
harput-finans/
│
├── app/
│   │
│   ├── discovery/
│   │   └── adil_katilim_discovery.py
│   │
│   ├── dynamic_extractor/
│   │   └── dynamic_regex_extractor.py
│   │
│   ├── processors/
│   │   ├── *_extractor.py
│   │   ├── merge_*.py
│   │   ├── patch_*.py
│   │   ├── validate_*.py
│   │   ├── inspect_*.py
│   │   └── cleanup_*.py
│   │
│   └── scrapers/
│       ├── adil_katilim_finance_scraper.py
│       ├── dunya_katilim_*.py
│       ├── emlak_katilim_*.py
│       ├── hayat_finans_*.py
│       ├── kuveyt_turk_*.py
│       └── turkiye_finans_*.py
│
├── data/
│   ├── final_banks/
│   └── test/
│
├── colab dosyaları/
│   ├── uygulama dosyaları/
│   └── veri çekme dosyalarının devamı/
│
├── requirements.txt
├── LICENSE
├── .gitignore
└── README.md
```

---

# `app/discovery`

Bu klasör doğrudan veri çekmeden önce banka web sitesindeki ilgili sayfaların **keşfedilmesi** için kullanılan kodları içerir.

Şu anda:

```text
app/discovery/adil_katilim_discovery.py
```

bulunmaktadır.

Bu script Adil Katılım'ın web sitesi içerisinde ürün, finansman ve kampanya olabilecek sayfaları taramak amacıyla geliştirilmiştir.

Discovery mekanizması;

* aynı domain içerisinde gezinme,
* URL normalizasyonu,
* finansman anahtar kelimelerinin kontrolü,
* ürün/kampanya olabilecek sayfaların belirlenmesi,
* gereksiz dosya uzantılarının filtrelenmesi,
* maksimum tarama derinliğinin sınırlandırılması

gibi işlemler gerçekleştirir.

Discovery ile scraper birbirinden ayrılmıştır.

```text
Discovery
    ↓
İlgili sayfaları bulur

Scraper
    ↓
Bulunan sayfalardan içeriği çıkarır
```

---

# `app/scrapers`

Bu klasör, katılım bankalarının **resmî web sitelerinden veri toplamak** için oluşturulan banka bazlı scraperları içerir.

Kullanılan temel yöntemler:

* `requests`
* `BeautifulSoup`
* `Playwright`
* URL discovery
* HTML parsing
* sayfa içeriği temizleme

Bankanın web yapısına göre farklı scraping stratejileri kullanılmaktadır.

---

## Adil Katılım

```text
app/scrapers/adil_katilim_finance_scraper.py
```

Adil Katılım'ın finansman ürün sayfasından bireysel finansman bilgisini toplar.

---

## Dünya Katılım

```text
dunya_katilim_campaign_discovery.py
dunya_katilim_campaign.py
dunya_katilim_finansmanlar.py
```

Kampanya tarafında önce kampanya sayfalarının keşfi gerçekleştirilir.

Daha sonra kampanya detay sayfaları işlenir.

Finansman ürünleri ayrı scraper üzerinden toplanır.

---

## Emlak Katılım

```text
emlak_katilim_campaign.py
emlak_katilim_finansmanlar.py
```

Finansman ve kampanya verileri ayrı veri toplama akışlarından geçirilir.

---

## Hayat Finans

```text
hayat_finans_campaign.py
hayat_finans_finansmanlar.py
```

Hayat Finans'ın kampanya ve bireysel finansman sayfalarını işler.

Scraperlarda beklenen kayıtların ve resmî URL'lerin kontrolüne yönelik ek kontroller bulunmaktadır.

---

## Kuveyt Türk

```text
kuveyt_turk_campaign.py
kuveyt_turk_finansmanlar.py
```

Kuveyt Türk'ün finansman ve kampanya kaynaklarını toplar.

Kampanya tarafında dinamik içeriklerin yüklenmesi gerektiği durumlarda Playwright kullanılmaktadır.

Bazı resmî kampanya sayfalarında alternatif resmî kaynaklar için fallback mekanizması da bulunmaktadır.

---

## Türkiye Finans

```text
turkiye_finans_campaign.py
turkiye_finans_finansmanlar.py
```

Türkiye Finans'ın finansman ürünleri ve kampanyalarını toplar.

Kategori sayfaları, resmî ürün bağlantıları ve kampanya kaynakları ayrı ayrı işlenmektedir.

---

# `app/processors`

`processors` klasörü projenin en önemli veri hazırlama katmanlarından biridir.

Scraperlardan gelen veri doğrudan AI Asistan'a verilmez.

Önce processor katmanından geçirilir.

Genel akış:

```text
RAW DATA
   │
   ▼
EXTRACT
   │
   ▼
NORMALIZE
   │
   ▼
VALIDATE
   │
   ▼
PATCH / CLEANUP
   │
   ▼
MERGE
   │
   ▼
FINAL BANK DATA
```

Processor klasöründeki dosyalar görevlerine göre birkaç gruba ayrılır.

---

## Extractor Dosyaları

Örneğin:

```text
adil_katilim_finance_extractor.py

dunya_katilim_campaign_extractor.py
dunya_katilim_finansman_extractor.py

hayat_finans_campaign_extractor.py
hayat_finans_finansman_extractor.py

kuveyt_turk_campaign_extractor.py
kuveyt_turk_finansman_extractor.py

turkiye_finans_campaign_extractor.py
turkiye_finans_finansman_extractor.py

campaign_extractor.py
product_extractor.py
```

Bu dosyalar ham metinler içerisinden yapılandırılmış finansal alanları çıkarır.

Örneğin:

```text
kar_payi_orani
finansman_tutari
vade
taksit_sayisi
masraf_bilgisi
kampanya_avantaji
hedef_kitle
kosullar
```

---

## Normalizer

```text
product_normalizer.py
```

Farklı formatlarda bulunan ürün bilgilerini daha standart bir yapıya dönüştürür.

Normalizasyonun amacı banka kaynaklarını değiştirmek değil, karşılaştırılabilir hale getirmektir.

---

## Validator Dosyaları

Örneğin:

```text
validate_dunya_katilim_campaign_raw.py
validate_dunya_katilim_finansman_raw.py

validate_hayat_finans_campaign_raw.py
validate_hayat_finans_finansman_raw.py

validate_kuveyt_turk_campaign_raw.py
validate_kuveyt_turk_raw.py

validate_turkiye_finans_raw.py
```

Validatorların amacı veri toplama sonucunda;

* beklenen kayıt sayısı,
* banka adı,
* kayıt tipi,
* URL yapısı,
* duplicate URL,
* beklenen ürünler,
* tarih tutarlılığı,
* temel şema

gibi kontrolleri gerçekleştirmektir.

Bu sayede hatalı veya eksik scraping çıktısının doğrudan final veri setine ulaşması engellenir.

---

## Inspect Dosyaları

Örneğin:

```text
inspect_dunya_katilim_campaign_raw.py
inspect_dunya_katilim_finansman_raw.py

inspect_hayat_finans_campaign_raw.py
inspect_hayat_finans_finansman_raw.py

inspect_kuveyt_turk_campaign_raw.py
inspect_kuveyt_turk_raw.py

inspect_turkiye_finans_raw.py
```

Inspect scriptleri ham verilerin daha detaylı kalite kontrolü için kullanılmıştır.

Özellikle;

* beklenmeyen içerikler,
* geçmiş kampanya tarihleri,
* yanlış sayfadan gelen metinler,
* ürün içeriğine başka ürünlerin karışması,
* şüpheli değerler

gibi sorunların tespit edilmesine yardımcı olur.

---

## Patch / Cleanup Dosyaları

Örneğin:

```text
patch_albaraka_turk_final.py
patch_emlak_katilim_final.py
patch_kuveyt_turk_final.py
patch_tom_katilim_final.py
patch_turkiye_finans_final.py
patch_vakif_katilim_final_v9.py
patch_ziraat_katilim_final.py

cleanup_ziraat_katilim_final.py
```

Bu scriptler bankaya özgü son kalite düzeltmelerini gerçekleştirir.

Bunlar özellikle;

* yanlış formatlanmış yüzdeler,
* para tutarları,
* kampanya tarihleri,
* vade değerleri,
* tekrar eden bilgiler,
* web arayüzünden gelen gereksiz metinler,
* kampanya/finansman alanlarına yanlış taşınmış içerikler

gibi sorunları final aşamada temizlemek amacıyla kullanılır.

---

## Merge Dosyaları

Örneğin:

```text
merge_adil_katilim.py
merge_dunya_katilim.py
merge_emlak_katilim.py
merge_hayat_finans.py
merge_kuveyt_turk.py
merge_turkiye_finans.py
```

Finansman ve kampanya verileri ayrı süreçlerden geldikten sonra banka bazında bir araya getirilir.

Örneğin:

```text
Dünya Katılım

6 finansman
+
43 kampanya
=
49 kayıt
```

şeklinde final banka veri seti oluşturulur.

Merge aşamasında tekrar;

* şema,
* duplicate URL,
* duplicate başlık,
* finansman/kampanya sayıları

kontrol edilebilir.

---

# `app/dynamic_extractor`

Bu klasörde:

```text
dynamic_regex_extractor.py
```

bulunmaktadır.

Bu bileşen klasik sabit regex yaklaşımından farklı bir bilgi çıkarımı mekanizması sunar.

Amaç, daha önce görülmemiş bir finansman metni geldiğinde yapay zekâ modelinin o metni analiz ederek **regex tabanlı bir Python extractor üretmesini** sağlamaktır.

---

## Çalışma Mantığı

```text
Yeni Finansman Metni
        │
        ▼
Yerel Kod Üreten LLM
        │
        ▼
Regex Tabanlı
Python Extractor
        │
        ▼
AST Güvenlik Kontrolü
        │
        ▼
İzole Çalıştırma
        │
        ▼
Semantik Validasyon
        │
        ▼
Yapılandırılmış Sonuç
```

Dinamik extractor dokuz temel alan üretir:

```text
kar_payi_orani
finansman_orani
finansman_tutari
vade
taksit_sayisi
masraf_bilgisi
hedef_kitle
para_birimi
kosullar
```

Bütün alanların liste biçiminde dönmesi beklenmektedir.

---

## Hallucination Kontrolü

Extractor için temel prensip:

> Kaynakta bulunmayan bilgiyi üretme.

Çıkarılan değerlerin mümkün olduğunca doğrudan kaynak metindeki regex eşleşmelerinden gelmesi beklenir.

Örneğin kaynakta vade bulunmuyorsa:

```markdown
```json
"vade": []
```

döndürülür.

---

## Güvenli Kod Üretimi

LLM tarafından üretilen Python kodu doğrudan çalıştırılmaz.

Önce Python AST üzerinden güvenlik kontrolünden geçirilir.

Sistem;

* dosya açma,
* `eval`,
* `exec`,
* `__import__`,
* sistem komutları,
* `os`,
* `sys`,
* `subprocess`,
* ağ erişimi,
* tehlikeli Python yapılarını

üretilen extractor kodunda sınırlar.

Yalnızca ihtiyaç duyulan regex ve temel Python işlemlerine izin verilir.

---

## İzole Çalıştırma

Güvenlik kontrolünden geçen kod ayrı bir çalışma sürecinde ve zaman sınırı ile çalıştırılır.

Bu yaklaşım dinamik kod üretiminin uygulamanın ana sürecini kontrolsüz biçimde etkilemesini engellemeyi amaçlamaktadır.

---

## Retry / Repair Mekanizması

Üretilen extractor validator kontrollerinden geçmezse sistem modelden kodu düzeltmesini isteyebilir.

Bu işlem belirli sayıda tekrar denenir.

Böylece:

```text
Generate
   ↓
Validate
   ↓
Hata?
 ↙    ↘
Evet   Hayır
 │       │
Repair   Sonuç
 │
 └────► Validate
```

akışı oluşturulur.

---

# `data/final_banks`

Bu klasör Harput Finans'ın **kullanıma hazır final veri setlerini** içerir.

```text
data/final_banks/
│
├── adil_katilim_all.json
├── albaraka_turk_all.json
├── dunya_katilim_all.json
├── emlak_katilim_all.json
├── hayat_finans_all.json
├── kuveyt_turk_all.json
├── tom_katilim_all.json
├── turkiye_finans_all.json
├── vakif_katilim_all.json
├── ziraat_katilim_all.json
│
└── katilim_finans_master.json
```

---

## Banka Bazlı Dosyalar

`*_all.json` dosyaları ilgili bankanın final aşamasından geçmiş;

* finansman,
* kampanya

kayıtlarını içerir.

---

## Master Dataset

```text
katilim_finans_master.json
```

tüm banka verilerini tek bir kaynakta birleştirir.

Temel yapı:

```json
{
    "metadata": {},
    "finansmanlar": [],
    "kampanyalar": []
}
```

### `metadata`

Dataset hakkında genel bilgileri içerir.

Örneğin:

* dataset adı,
* schema version,
* banka sayısı,
* finansman sayısı,
* kampanya sayısı,
* toplam kayıt,
* canonical kategori bilgileri.

### `finansmanlar`

Tüm bankaların normalize edilmiş finansman ürünlerini içerir.

### `kampanyalar`

Tüm bankaların normalize edilmiş kampanyalarını içerir.

Web uygulamasının sorgu ve karşılaştırma katmanında temel veri kaynağı bu master yapıdır.

---

# Colab Dosyaları

Bazı bileşenler Google Colab üzerinde geliştirilmiştir.

Bu nedenle ilgili notebooklar proje içerisinde ayrıca paylaşılmaktadır.

---

# `colab dosyaları/uygulama dosyaları`

Bu klasör Harput Finans'ın son kullanıcı uygulamasını içeren notebooku barındırır.

Ana notebook:

```text
Harput_Finanas.ipynb
```

Bu notebook içerisinde sistemin;

* veri yükleme,
* finansman sorgulama,
* kampanya sorgulama,
* kullanıcı intent analizi,
* multi-turn konuşma durumu,
* finansman karşılaştırma,
* kampanya karşılaştırma,
* kişisel kriterlere göre ürün değerlendirme,
* kaynak güvenliği,
* AI cevap üretimi,
* LangGraph iş akışı,
* FastAPI backend,
* bilgi çıkarımı API'si,
* web arayüzü,
* Uvicorn sunucusu,
* Cloudflare üzerinden demo yayını

gibi uygulama katmanları bulunmaktadır.

---

# Veri Çekme Notebookları

```text
colab dosyaları/
└── veri çekme dosyalarının devamı/
```

içerisinde Python scriptleri dışında Colab üzerinde geliştirilen scraping süreçleri bulunmaktadır.

Mevcut notebooklar:

```text
albarakatürkgüncel.ipynb
tom_katılım_güncel.ipynb
vakıfkatılımscraping_....ipynb
ziraatkatılım.ipynb
```

Bu notebooklar sırasıyla;

* Albaraka Türk,
* T.O.M. Katılım,
* Vakıf Katılım,
* Ziraat Katılım

veri toplama ve veri hazırlama süreçlerinin ilgili bölümlerini içerir.

Bankaların web altyapıları birbirinden farklı olduğu için veri toplama işlemlerinde tek bir scraper yapısı yerine bankaya uygun yöntemler tercih edilmiştir.

Bu notebooklarda kullanılan yöntemler arasında projeye göre;

* Requests,
* BeautifulSoup,
* Playwright,
* Selenium,
* URL discovery,
* HTML parsing

gibi yaklaşımlar bulunmaktadır.

---

# AI Asistan

Harput Finans AI Asistan kullanıcının doğal dilde yazdığı soruyu doğrudan veri tabanı sorgusuna çevirmek yerine önce kullanıcının amacını analiz eder.

Desteklenen temel intent yapıları arasında:

```text
PRODUCT_INFO
PRODUCT_COMPARE
PERSONAL_RECOMMENDATION
CAMPAIGN_INFO
CAMPAIGN_COMPARE
FOLLOW_UP
GENERAL_CHAT
```

bulunmaktadır.

---

## PRODUCT_INFO

Belirli finansman ürünlerini sorgulamak için kullanılır.

Örnek:

```text
Kuveyt Türk konut finansmanları neler?
```

---

## PRODUCT_COMPARE

Finansman ürünlerini karşılaştırmak için kullanılır.

Örnek:

```text
Kuveyt Türk ve Albaraka Türk
konut finansmanlarını karşılaştır.
```

---

## PERSONAL_RECOMMENDATION

Kullanıcının finansman ihtiyacına göre uygun seçenekleri değerlendirmek için kullanılır.

Örnek:

```text
500.000 TL araç finansmanı istiyorum.
24 ay vade düşünüyorum.
```

---

## CAMPAIGN_INFO

Kampanya sorguları için kullanılır.

Örnek:

```text
Aktif alışveriş kampanyaları neler?
```

---

## CAMPAIGN_COMPARE

Farklı kampanyaların belirli metrikler üzerinden karşılaştırılmasını sağlar.

---

## FOLLOW_UP

Önceki mesajın devamı niteliğindeki sorgular için kullanılır.

Örnek:

```text
Konut finansmanlarını göster.
```

ardından:

```text
Sadece Kuveyt Türk olanları göster.
```

---

# Grounded Response Yaklaşımı

AI modeli doğrudan kendi bilgisine dayanarak finansal cevap oluşturmak yerine sistem tarafından elde edilen **deterministic tool result** üzerinden cevap üretmek üzere tasarlanmıştır.

Amaç;

```text
Kullanıcı Sorusu
       │
       ▼
Intent
       │
       ▼
Deterministik Veri İşleme
       │
       ▼
TOOL_RESULT
       │
       ▼
LLM
       │
       ▼
Doğal Dil Yanıtı
```

akışını kullanmaktır.

Bu yöntem finansal rakamların yapay zekâ tarafından uydurulma riskini azaltmayı amaçlamaktadır.

---

# Kaynak Güvenliği

Sistem cevap üretiminde kaynak URL'lerini ayrı olarak işlemektedir.

Kaynak URL'lerinin model tarafından yeniden oluşturulması yerine gerçek dataset kaynaklarının korunması amaçlanmıştır.

Bu sayede sistem tarafından hayalî kaynak URL oluşturma riskinin azaltılması hedeflenmiştir.

---

# Bilgi Çıkarımı

Web arayüzündeki **Bilgi Çıkarımı** modülü serbest metin kabul eder.

Kullanıcı örneğin:

```text
Yeni müşterilerimize özel %2,89 kâr payı oranıyla
250.000 TL'ye kadar 24 ay vadeli finansman...
```

metnini sisteme verebilir.

Sistem yapılandırılmış olarak şu dokuz alan üzerinde bilgi çıkarmaya çalışır:

```text
kar_payi_orani
finansman_orani
finansman_tutari
vade
taksit_sayisi
masraf_bilgisi
hedef_kitle
para_birimi
kosullar
```

Sonuç web arayüzünde kullanıcıya gösterilir.

---

# Web Arayüzü

Harput Finans tek web uygulaması içerisinde üç temel fonksiyon sunar.

## AI Asistan

* Doğal dilde soru sorma
* Finansman ürünlerini bulma
* Kampanyaları inceleme
* Banka filtreleme
* Takip soruları
* Ürün karşılaştırma
* Kampanya karşılaştırma
* Kriter bazlı değerlendirme
* Kaynak görüntüleme

---

## Bilgi Çıkarımı

* Serbest metin girişi
* Finansal bilgi çıkarımı
* Yapılandırılmış sonuç
* JSON görünümü
* Kullanıcı dostu sonuç gösterimi

---

## Sistem & Veri

* Toplam banka sayısı
* Toplam kayıt
* Finansman sayısı
* Kampanya sayısı
* Banka bazlı veri dağılımı
* Dataset ve sistem durumunun görüntülenmesi

gibi bilgilerin takip edilmesini sağlar.

---

# API Yapısı

Web uygulaması **FastAPI** üzerinde çalışmaktadır.

Ana endpointler:

```text
GET  /health
POST /chat
POST /chat/reset
POST /extract
GET  /
```

---

## `GET /health`

Sistemin çalışıp çalışmadığını kontrol eder.

---

## `POST /chat`

AI Asistan sorgularını işler.

Örnek istek:

```json
{
    "message": "Konut finansmanı seçeneklerini göster.",
    "session_id": "optional"
}
```

Session ID verilmediğinde sistem yeni bir oturum oluşturabilir.

---

## `POST /chat/reset`

Kullanıcının mevcut konuşma durumunu sıfırlamak için kullanılır.

---

## `POST /extract`

Bilgi çıkarımı modülünün backend endpointidir.

Kullanıcı tarafından verilen finansal metni bilgi çıkarım pipeline'ına gönderir.

---

## `GET /`

Harput Finans web arayüzünü sunar.

---

# LangGraph

AI Asistan'ın konuşma ve yönlendirme süreçlerinin yönetiminde **LangGraph** kullanılmaktadır.

LangGraph akışı;

* intent analizi,
* ürün bilgi sorgusu,
* ürün karşılaştırma,
* kampanya sorgusu,
* kampanya karşılaştırma,
* kişisel öneri,
* follow-up işlemleri

gibi farklı kullanıcı taleplerinin uygun işlem hattına yönlendirilmesine yardımcı olur.

---

# Session Yönetimi

Chatbot birden fazla kullanıcı mesajından oluşan konuşmaları desteklemek üzere session mantığı kullanmaktadır.

Her kullanıcı oturumu ayrı konuşma durumu ile takip edilir.

Bu sayede:

```text
1. Konut finansmanı seçeneklerini göster.
2. Kuveyt Türk olsun.
3. Bunlardan hangisinin vadesi daha uzun?
```

gibi ardışık konuşmalar gerçekleştirilebilir.

---

# Kullanılan Yapay Zeka Modelleri

Uygulamanın mevcut notebook yapısında iki farklı yapay zekâ görevi ayrılmıştır.

## AI Asistan Modeli

```text
qwen3.5:35b-a3b-q8_0
```

Kullanıcının intent'inin yorumlanması ve yapılandırılmış sonuçların doğal dil yanıtına dönüştürülmesi gibi agent görevlerinde kullanılmaktadır.

---

## Bilgi Çıkarımı Modeli

```text
qwen3-coder-next
```

Dinamik bilgi çıkarımı için regex tabanlı Python extractor üretiminde kullanılmaktadır.

Bu iki görev ayrı modeller üzerinden yürütülerek;

```text
Agent / Reasoning
```

ve;

```text
Extraction / Code Generation
```

sorumlulukları ayrılmıştır.

---

# Model Yaşam Döngüsü

Uygulamada büyük modellerin aynı anda gereksiz yere bellekte tutulmasını engellemek için model yaşam döngüsü kontrolleri bulunmaktadır.

Bilgi çıkarımı sırasında extractor modeli;

```text
qwen3-coder-next
```

kullanılır.

Chatbot işlemlerinde ise agent modeli;

```text
qwen3.5:35b-a3b-q8_0
```

kullanılır.

Sistem model yükleme/boşaltma işlemleriyle kaynak kullanımını kontrol etmeyi hedeflemektedir.

---

# On-Premise Yaklaşımı

Harput Finans mimarisi yerel model çalıştırmayı desteklemektedir.

LLM çalıştırma katmanında:

```text
Ollama
```

kullanılmaktadır.

Varsayılan yerel adres:

```text
http://127.0.0.1:11434
```

şeklindedir.

Bu yaklaşım sistemin uygun donanım bulunduğunda kurum içerisinde çalıştırılabilmesine imkân sağlar.

Cloudflare kullanımı uygulamanın yarışma/demo ortamında web arayüzünü dışarı açabilmek için kullanılan sunum katmanıdır; temel AI çalışma mantığının Ollama üzerinden yerel çalışması mümkündür.

---

# Teknolojiler

Projede kullanılan başlıca teknolojiler:

### Programlama

```text
Python
HTML
CSS
JavaScript
```

### Web Scraping

```text
Requests
BeautifulSoup
Playwright
Selenium
```

### Backend

```text
FastAPI
Uvicorn
Pydantic
```

### AI / Agent

```text
Ollama
Qwen
LangGraph
```

### Veri

```text
JSON
```

### Geliştirme Ortamı

```text
Google Colab
Jupyter Notebook
Python Virtual Environment
```

### Demo / Yayın

```text
Cloudflare Tunnel
```

---

# Kurulum

Repository'yi klonlayın:

```bash
git clone https://github.com/HarpuAI-Teknofest2026/harput-finans.git
```

Proje dizinine geçin:

```bash
cd harput-finans
```

Sanal ortam oluşturulması önerilir:

```bash
python -m venv .venv
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Python bağımlılıklarını yükleyin:

```bash
pip install -r requirements.txt
```

Playwright tabanlı scraperlar için gerekli browser bileşenlerini kurun:

```bash
playwright install
```

---

# Uygulamayı Çalıştırma

Harput Finans'ın ana uygulaması Google Colab / Jupyter Notebook ortamında çalışacak şekilde hazırlanmıştır.


Ana uygulama notebooku:

```text
colab dosyaları/uygulama dosyaları/Harput_Finanas.ipynb
```

Bu notebook içerisinde;

- Master veri setinin yüklenmesi
- Yapay zeka modellerinin hazırlanması
- AI Asistan'ın başlatılması
- Bilgi Çıkarımı bileşeninin çalıştırılması
- FastAPI backend'in oluşturulması
- Web arayüzünün başlatılması

işlemleri gerçekleştirilmektedir.

---

## 1. Ollama'nın Hazırlanması

Harput Finans'ın yapay zeka bileşenleri Ollama üzerinden yerel olarak çalıştırılmaktadır.

Ollama servisinin çalışıp çalışmadığını kontrol etmek için:

```bash
ollama list
```

Servis aktif değilse:

```bash
ollama serve
```

komutu ile başlatılabilir.

Uygulamada kullanılan varsayılan Ollama adresi:

```text
http://127.0.0.1:11434
```

şeklindedir.


---


# Final Dataset

Sadece son kullanım için hazırlanmış banka verileri:

```text
data/final_banks/
```

dizininde yer almaktadır.

Sistemin tüm bankaları birlikte kullandığı ana veri dosyası:

```text
data/final_banks/katilim_finans_master.json
```

dosyasıdır.

---

## Veri Setini İndir

Harput Finans kapsamında oluşturulan 10 katılım bankasına ait birleşik final veri seti herkese açık olarak aşağıdaki bağlantıdan indirilebilir:

**Master Veri Seti:**  
https://raw.githubusercontent.com/HarpuAI-Teknofest2026/harput-finans/main/data/final_banks/katilim_finans_master.json

Banka bazlı final veri dosyalarının tamamı:

https://github.com/HarpuAI-Teknofest2026/harput-finans/tree/main/data/final_banks

Veri seti toplam **530 kayıt** içermektedir:

- 116 finansman ürünü
- 414 kampanya
- 10 katılım bankası

# Test Verileri

```text
data/test/
```

dizini geliştirme sırasında bilgi çıkarımı gibi bileşenlerin kontrol edilmesinde kullanılan test girdilerini barındırır.

---

# Veri Güvenliği ve Doğruluk Yaklaşımı

Harput Finans geliştirilirken özellikle şu prensiplere dikkat edilmiştir:

### 1. Resmî Kaynak

Veriler katılım bankalarının resmî web kaynaklarından toplanır.

### 2. Kaynak URL Koruma

Her kayıt mümkün olduğunca kaynak URL ile birlikte tutulur.

### 3. Hallucination Önleme

Kaynakta bulunmayan finansal değerlerin üretilmemesi hedeflenir.

### 4. Yapılandırılmış Veri

LLM çıktısı doğrudan tek güven kaynağı olarak kullanılmak yerine yapılandırılmış ve doğrulanmış veri katmanı kullanılır.

### 5. Validasyon

Scraping ve extraction sonrasında banka özelinde doğrulama scriptleri kullanılır.

### 6. Duplicate Kontrolü

Aynı URL veya ürünün tekrar final veri setine eklenmesini engellemeye yönelik kontroller uygulanır.

---

# Projenin Temel Farkı

Harput Finans yalnızca bir chatbot değildir.

Sistem uçtan uca:

```text
VERİ TOPLAMA
    +
VERİ TEMİZLEME
    +
NLP BİLGİ ÇIKARIMI
    +
VERİ NORMALİZASYONU
    +
VALIDASYON
    +
CANONICAL SINIFLANDIRMA
    +
AI AGENT
    +
MULTI-TURN CHAT
    +
ÜRÜN KARŞILAŞTIRMA
    +
KAMPANYA KARŞILAŞTIRMA
    +
WEB ARAYÜZÜ
```

bileşenlerinden oluşmaktadır.

---

# Lisans

Bu proje **Apache License 2.0** kapsamında lisanslanmıştır.

Detaylı lisans metni repository içerisindeki:

```text
LICENSE
```

dosyasında bulunmaktadır.

---

## Harput Finans

**Katılım finansını daha anlaşılır hale getiriyoruz.**
