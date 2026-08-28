# Harput Finans

> **TEKNOFEST 2026 Yapay Zeka Dil Ajanları Yarışması**  
> **Katılım Bankacılığı Finansal Metin Madenciliği**

**Harput Finans**, Türkiye'deki katılım bankalarının finansman ürünleri ve kampanyalarını resmî web kaynaklarından toplayan, ortak bir veri şemasına dönüştüren, yapılandırılmış finansal bilgi çıkarımı gerçekleştiren ve kullanıcıların doğal dildeki sorularına kaynak-temelli yanıtlar üreten bir finansal dil ajanıdır.

Proje; veri toplama, veri normalizasyonu, finansal bilgi çıkarımı, deterministik kayıt getirme, banka karşılaştırma, çok turlu konuşma, kaynak doğrulama ve web tabanlı yapay zekâ asistanını tek bir uçtan uca sistemde birleştirir.

---

## Proje Özeti

| Özellik | Değer |
|---|---:|
| Desteklenen katılım bankası | **10** |
| Toplam kayıt | **530** |
| Finansman ürünü | **116** |
| Kampanya | **414** |
| Bilgi çıkarımı alanı | **9** |
| AI Asistan modeli | **Qwen3.5 35B A3B Q8** |
| Bilgi çıkarımı modeli | **Qwen3-Coder-Next** |
| Agent orkestrasyonu | **LangGraph** |
| Yerel model çalışma altyapısı | **Ollama** |
| Backend | **FastAPI** |

---

## Öne Çıkan Değerlendirme Sonuçları

Harput Finans tek bir doğruluk metriğiyle değerlendirilmemiştir. Sistem farklı görev katmanlarında ayrı ayrı test edilmiştir.

| Değerlendirme Katmanı | Sonuç |
|---|---:|
| Niyet Sınıflandırma Doğruluğu | **%94.00 — 47/50** |
| Ham Alan/Filtre Çıkarımı | **%74.42 — 128/172** |
| Sayısal Finansal Grounding | **%100 — 92/92** |
| Retrieval Micro Precision | **%100** |
| Retrieval Micro Recall | **%100** |
| Retrieval Micro F1 | **%100** |
| Retrieval Exact Set Match | **%100 — 24/24** |
| Retrieved-record Source Integrity | **%100 — 130/130** |
| Çok Turlu Context Kontrolü — Post-fix | **%100 — 77/77** |
| Çok Turlu Senaryo Exact Success — Post-fix | **%100 — 10/10** |
| No-data Safety — Post-fix | **%100 — 108/108** |
| No-data Case Exact — Post-fix | **%100 — 12/12** |

> **Not:** Bu sonuçlar birbirinden farklı değerlendirme katmanlarına aittir.  
> Tek bir **“Harput Finans genel doğruluğu”** olarak birleştirilmemelidir.

---

# İçindekiler

- [Proje Hakkında](#proje-hakkında)
- [Problem](#problem)
- [Geliştirilen Çözüm](#geliştirilen-çözüm)
- [Temel Tasarım İlkeleri](#temel-tasarım-ilkeleri)
- [Sistem Mimarisi](#sistem-mimarisi)
- [Veri Seti](#veri-seti)
- [Desteklenen Katılım Bankaları](#desteklenen-katılım-bankaları)
- [Standart Veri Şeması](#standart-veri-şeması)
- [Bilgi Çıkarımı](#bilgi-çıkarımı)
- [AI Asistan](#ai-asistan)
- [Deterministik Finansal Araçlar](#deterministik-finansal-araçlar)
- [Çok Turlu Konuşma](#çok-turlu-konuşma)
- [Kaynak ve Finansal Değer Güvenliği](#kaynak-ve-finansal-değer-güvenliği)
- [Değerlendirme](#değerlendirme)
- [Web Arayüzü](#web-arayüzü)
- [API](#api)
- [Kullanılan Modeller](#kullanılan-modeller)
- [On-Premise Yaklaşımı](#on-premise-yaklaşımı)
- [Teknolojiler](#teknolojiler)
- [Proje Yapısı](#proje-yapısı)
- [Kurulum](#kurulum)
- [Uygulamayı Çalıştırma](#uygulamayı-çalıştırma)
- [Veri Güvenliği](#veri-güvenliği)
- [Lisans](#lisans)

---

# Proje Hakkında

Katılım bankaları finansman ürünleri ve kampanyalarını kendi resmî web sitelerinde yayımlamaktadır.

Ancak bankalar arasında;

- sayfa yapıları,
- kategori isimleri,
- kâr payı gösterimleri,
- finansman tutarı ifadeleri,
- vade formatları,
- kampanya açıklamaları,
- ücret ve masraf tanımları,
- kampanya avantajları,
- hedef müşteri tanımları

standart değildir.

Örneğin aynı finansal bilgi farklı kaynaklarda şu biçimlerde ifade edilebilir:

```text
%2,05 kâr payı oranı
% 2.05 kâr payı
2.05 % kâr oranı
avantajlı kâr payı fırsatı
```

Harput Finans bu heterojen yapıyı ortak bir veri katmanına dönüştürerek farklı katılım bankalarının finansman ürünleri ve kampanyalarının tek sistem üzerinden sorgulanmasını sağlar.

---

# Problem

Bir kullanıcı veya banka çalışanı farklı katılım bankalarının ürünlerini karşılaştırmak istediğinde her bankanın web sitesini ayrı ayrı incelemek zorundadır.

Bu süreç;

- konut finansmanı,
- taşıt finansmanı,
- ihtiyaç finansmanı,
- işyeri finansmanı,
- arsa finansmanı,
- alışveriş finansmanı,
- eğitim finansmanı,
- kart kampanyaları,
- indirim kampanyaları,
- taksit kampanyaları,
- puan ve ödül kampanyaları

gibi çok sayıda ürün olduğunda zaman alıcı ve hata yapmaya açık hâle gelmektedir.

Harput Finans'ın temel amacı bu süreci otomatikleştirerek kullanıcıya:

1. ortak bir veri katmanı,
2. doğal dilde sorgulama,
3. deterministik karşılaştırma,
4. kaynak-temelli cevap,
5. çok turlu konuşma

imkânı sunmaktır.

---

# Geliştirilen Çözüm

Harput Finans uçtan uca aşağıdaki akışı kullanır:

```text
Katılım Bankalarının
Resmî Web Siteleri
        │
        ▼
Veri Keşfi
ve Web Scraping
        │
        ▼
Ham Finansman /
Kampanya Metinleri
        │
        ▼
Alan Çıkarımı
ve Normalizasyon
        │
        ▼
Validasyon /
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
                       Niyet / Filtre Analizi
                               │
                               ▼
                       Deterministik Araçlar
                               │
                               ▼
                       Kaynak-Temelli Yanıt
```

---

# Temel Tasarım İlkeleri

## 1. LLM finansal değeri hesaplamaz

Harput Finans'ta yapay zekâ modeli doğrudan finansal karşılaştırma sonucunu hesaplayan güven kaynağı değildir.

Finansal kayıt getirme, filtreleme ve karşılaştırma işlemleri mümkün olduğunca deterministik Python araçları tarafından gerçekleştirilir.

> **LLM finansal değeri sayısal olarak karar vermek için değil, kullanıcının isteğini anlamak ve deterministik tool çıktısını doğal dile çevirmek için kullanılır.**

---

## 2. Bilgi çıkarımında model değer tahmin etmez

Harput Finans'ın dinamik bilgi çıkarımı yaklaşımının temel prensibi:

> **Model finansal değeri tahmin etmiyor; o değeri çıkaracak programı yazıyor.**

LLM, kaynak metni analiz ederek Python ve regex tabanlı bir extractor üretir.

Üretilen program çalıştırılarak kaynak metindeki finansal alanlar çıkarılır.

---

## 3. Kaynakta olmayan bilgi boş bırakılır

Bir finansal alan kaynak metinde açık biçimde bulunmuyorsa modelden tahmin edilmesi istenmez.

Örneğin kaynakta vade yoksa:

```json
{
  "vade": []
}
```

döndürülür.

---

## 4. Kaynak URL'leri model tarafından üretilmez

Kullanıcıya gösterilen resmî kaynaklar doğrudan veri setindeki `kaynak_url` alanlarından alınır.

Kaynak bağlantıları LLM tarafından yeniden oluşturulmaz.

---

# Sistem Mimarisi

Harput Finans üç ana kullanıcı modülüne sahiptir:

```text
                    HARPUT FİNANS
                         │
              ┌──────────┼──────────┐
              │          │          │
              ▼          ▼          ▼
         AI Asistan   Bilgi      Sistem &
                     Çıkarımı      Veri
              │          │          │
              ▼          ▼          ▼
           Sorgu       Serbest     Dataset
        Karşılaştırma   Metin      İstatistik
           Öneri        Analizi     Görüntüleme
```

AI Asistan tarafındaki ana akış:

```text
Kullanıcı Sorusu
        │
        ▼
Structured Intent Parser
        │
        ▼
Deterministik Guard / Routing
        │
        ▼
LangGraph
        │
        ▼
Deterministik Finansal Araçlar
        │
        ▼
Tool Evidence
        │
        ▼
Grounded Response Generator
        │
        ▼
Kaynak-Temelli Doğal Dil Yanıtı
```

---

# Veri Seti

Harput Finans master veri seti toplam **530 kayıt** içermektedir.

```text
10 katılım bankası

116 finansman ürünü
414 kampanya

Toplam: 530 kayıt
```

Ana veri dosyası:

```text
data/final_banks/katilim_finans_master.json
```

Master veri yapısı:

```json
{
  "metadata": {},
  "finansmanlar": [],
  "kampanyalar": []
}
```

---

# Desteklenen Katılım Bankaları

| Katılım Bankası | Finansman | Kampanya | Toplam |
|---|---:|---:|---:|
| Adil Katılım Bankası A.Ş. | 1 | 0 | 1 |
| Albaraka Türk Katılım Bankası A.Ş. | 17 | 46 | 63 |
| Dünya Katılım Bankası A.Ş. | 6 | 43 | 49 |
| Hayat Finans Katılım Bankası | 3 | 11 | 14 |
| Kuveyt Türk Katılım Bankası A.Ş. | 30 | 73 | 103 |
| T.O.M. Katılım Bankası A.Ş. | 3 | 50 | 53 |
| Türkiye Emlak Katılım Bankası A.Ş. | 12 | 63 | 75 |
| Türkiye Finans Katılım Bankası A.Ş. | 16 | 15 | 31 |
| Vakıf Katılım Bankası A.Ş. | 8 | 26 | 34 |
| Ziraat Katılım Bankası A.Ş. | 20 | 87 | 107 |
| **TOPLAM** | **116** | **414** | **530** |

---

# Standart Veri Şeması

Finansman ve kampanya kayıtları mümkün olduğunca ortak bir veri şeması üzerinden tutulmaktadır.

Temel alanlar:

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

## Finansman canonical alanları

Finansman kayıtlarında ayrıca:

```text
_canonical_category
_canonical_subtype
_semantic_tags
```

alanları bulunmaktadır.

`_canonical_category`, farklı bankaların farklı isimlerle sunduğu finansman ürünlerini ortak kategori altında toplar.

Örnek kategoriler:

```text
IHTIYAC_FINANSMANI
KONUT_FINANSMANI
TASIT_FINANSMANI
ISYERI_FINANSMANI
ARSA_FINANSMANI
ALISVERIS_FINANSMANI
EGITIM_FINANSMANI
ENERJI_FINANSMANI
KENTSEL_DONUSUM_FINANSMANI
YATIRIM_FINANSMANI
BES_TEMINATLI_FINANSMAN
TOKI
```

## Kampanya canonical alanları

Kampanya kayıtlarında:

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

Bu alanlar kampanyaların kategori, avantaj tipi, kullanıcı kapsamı, tarih durumu ve karşılaştırılabilir özelliklerinin deterministik şekilde işlenmesine yardımcı olur.

---

# Bilgi Çıkarımı

Harput Finans'ın **Bilgi Çıkarımı** modülü serbest finansal metin kabul eder.

Örnek:

```text
Yeni müşterilerimize özel %2,89 kâr payı oranıyla
250.000 TL'ye kadar 24 ay vadeli finansman...
```

Sistem dokuz temel alan çıkarmaya çalışır:

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

Örnek çıktı:

```json
{
  "kar_payi_orani": ["%2,89"],
  "finansman_orani": [],
  "finansman_tutari": ["250.000 TL'ye kadar"],
  "vade": ["24 ay"],
  "taksit_sayisi": [],
  "masraf_bilgisi": [],
  "hedef_kitle": ["Yeni müşteriler"],
  "para_birimi": ["TL"],
  "kosullar": []
}
```

---

# Dinamik Program-Sentezi Tabanlı Extraction

Bilgi çıkarımı mekanizması doğrudan LLM'den yapılandırılmış finansal değer istemek yerine **program sentezi** yaklaşımı kullanır.

Final extraction akışı:

```text
Ham Finansal Metin
        │
        ▼
Qwen3-Coder-Next
        │
        ▼
Python + Regex
Extractor Kodu
        │
        ▼
AST Güvenlik Kontrolü
        │
        ▼
İzole Subprocess
        │
        ▼
9 Alanlı Sabit JSON
```

Bu yaklaşım **single-pass** olarak çalışır.

Final pipeline'da:

```text
Retry yok
Repair yok
Semantic critic yok
```

Kaynakta bulunmayan alanlar:

```json
[]
```

olarak döndürülür.

---

# AST Güvenlik Kontrolü

LLM tarafından üretilen Python kodu doğrudan çalıştırılmaz.

Kod önce Python AST üzerinden kontrol edilir.

Tehlikeli veya gereksiz yapılara izin verilmez.

Örneğin:

```text
eval
exec
__import__
os
sys
dosya sistemi erişimi
ağ erişimi
sistem komutları
```

gibi işlemler sınırlandırılır.

AST kontrolünü geçen extractor ayrı subprocess içerisinde ve çalışma süresi sınırlandırılarak çalıştırılır.

---

# AI Asistan

Harput Finans AI Asistanı kullanıcının veri şemasını veya backend fonksiyonlarını bilmesini gerektirmez.

Örnek sorgular:

```text
Konut finansmanlarını göster.
```

```text
Kuveyt Türk konut finansmanlarını göster.
```

```text
Kuveyt Türk ile Ziraat Katılım
konut finansmanlarını karşılaştır.
```

```text
Dünya Katılım Hepsiburada kampanyalarını göster.
```

```text
peki vadeleri?
```

Desteklenen temel niyet sınıfları:

```text
PRODUCT_INFO
PRODUCT_COMPARE
PERSONAL_RECOMMENDATION
CAMPAIGN_INFO
CAMPAIGN_COMPARE
FOLLOW_UP
GENERAL_CHAT
```

---

# Structured Intent Parser

Kullanıcı sorgusu AI Asistan içinde yapılandırılmış bir forma dönüştürülür.

Parser aşağıdaki temel alanları üretir:

```text
intent
banks
all_banks
topic
product_category
requested_fields
comparison_criteria
```

Bu yapı deterministic backend'in hangi tool'u çağıracağını belirlemeye yardımcı olur.

Modelin görevi finansal sonucu hesaplamak değil, kullanıcının talebini yapılandırmaktır.

---

# Deterministik Finansal Araçlar

Harput Finans'ta finansal kayıtlar ve karşılaştırmalar aşağıdaki deterministik araçlar üzerinden işlenir:

```text
get_product_info
get_product_fields
compare_products
recommend_products

get_campaign_info
get_campaign_fields
compare_campaigns
```

Finansal oran, tutar, vade, taksit ve benzeri yapılandırılmış değerler doğrudan LLM tarafından karşılaştırılmaz.

Karşılaştırma işlemleri Python tarafında gerçekleştirilir.

---

# LangGraph

AI Asistan'ın yönlendirme ve conversation state akışı **LangGraph** ile yönetilmektedir.

Temel graph akışı:

```text
START
  │
  ▼
Intent Parsing
  │
  ├────────────► General Chat
  │
  └────────────► Deterministic Backend
                         │
                         ▼
                 Grounded Response
                         │
                         ▼
                        END
```

Conversation context gerektiğinde `FOLLOW_UP` intent'i kullanılır.

---

# Çok Turlu Konuşma

AI Asistan konuşma durumunu session bazlı olarak koruyabilir.

Örnek:

```text
Kullanıcı:
Konut finansmanlarını göster.

Asistan:
Hangi bankayı görmek istersiniz?

Kullanıcı:
Kuveyt Türk

Kullanıcı:
Peki vadeleri?
```

Son mesajda kullanıcının tekrar:

```text
Kuveyt Türk konut finansmanlarının vadeleri
```

yazması gerekmez.

Önceki konuşma scope'u session state üzerinden korunur.

Session'lar birbirinden izole tutulur.

---

# Kaynak ve Finansal Değer Güvenliği

Harput Finans'ın cevap üretim katmanı **grounded response** yaklaşımını kullanır.

Akış:

```text
Kullanıcı Sorusu
        │
        ▼
Deterministik Tool
        │
        ▼
Tool Result / Evidence
        │
        ▼
Qwen3.5
        │
        ▼
Doğal Dil Yanıtı
```

Finansal sayıların mümkün olduğunca tool evidence dışından oluşturulmaması hedeflenir.

Kaynak URL'leri LLM tarafından üretilmez.

---

# No-data Davranışı

Sistem veri bulunmayan durumlarda kayıt üretmeye çalışmaz.

Örneğin:

```text
XyzaqMarket kampanyalarını göster.
```

sorgusunda master veri setinde eşleşen kayıt bulunmuyorsa sistem:

```text
NOT_FOUND
```

durumunu döndürür.

Belirli bir bankada ürün bulunmayıp başka bankalarda bulunuyorsa:

```text
BANK_NOT_AVAILABLE
```

durumu kullanılabilir.

Bu ayrım kullanıcıya “ürün hiç yok” ile “bu bankada yok” durumlarının farklı şekilde sunulmasını sağlar.

---

# Değerlendirme

Harput Finans farklı sistem katmanlarında ayrı benchmarklarla değerlendirilmiştir.

## 1. Bilgi Çıkarımı Benchmarkı

50 kayıt kullanılmıştır:

```text
30 finansman
20 kampanya
10 banka
```

Her kayıt üç bağımsız run üzerinden değerlendirilmiştir.

Toplam:

```text
50 × 3 × 9 = 1.350 alan ölçümü
```

### Harput sonuçları

| Metrik | Sonuç |
|---|---:|
| Teknik Başarı | **%78.00 — 117/150** |
| Strict Accuracy — Tüm Alanlar | **%47.85** |
| Weighted Accuracy — Tüm Alanlar | **%54.00** |
| Strict Accuracy — Başarılı Kayıtlar | **%61.35** |
| Weighted Accuracy — Başarılı Kayıtlar | **%69.23** |
| Alan-değer Ortalama Pairwise Jaccard | **%65.33** |
| Presence Consistency | **%79.11** |
| 9 Alanın Üç Run'da Tamamen Aynı Olması | **%4.00** |

> Jaccard ve presence değerleri doğruluk değil, **tutarlılık** ölçümüdür.

---

## Direct-JSON Baseline Karşılaştırması

| Metrik | Harput | Qwen3.5 9B Direct JSON | Llama3.1 8B Direct JSON |
|---|---:|---:|---:|
| Teknik Başarı | **78.00** | 100.00 | 98.00 |
| Strict — Tüm Alanlar | **47.85** | 73.19 | 60.30 |
| Weighted — Tüm Alanlar | **54.00** | 81.78 | 68.93 |
| Strict — Başarılı Kayıtlar | **61.35** | 73.19 | 61.53 |
| Weighted — Başarılı Kayıtlar | **69.23** | 81.78 | 70.33 |

> **Önemli:** Baseline karşılaştırmasında yalnızca yöntem değil, kullanılan modeller de değişmektedir.  
> Bu nedenle performans farkı yalnızca extraction mimarisine atfedilemez.

---

## 2. Niyet Sınıflandırma

50 soruluk frozen test seti:

```text
47 doğru
3 yanlış
0 teknik hata
```

Sonuç:

```text
Intent Classification Accuracy = %94.00
```

---

## 3. Yapılandırılmış Alan / Filtre Çıkarımı

30 soruluk değerlendirme setinde:

```text
172 slot
128 doğru
```

Sonuç:

```text
Raw Slot Extraction Accuracy = %74.42
```

Tüm değerlendirilen filtre alanlarının aynı anda birebir doğru olmasını gerektiren daha katı metrik:

```text
Strict Exact Filter Match
10 / 30
%33.33
```

Bu metrik canonical isimlendirme farklılıklarına karşı da hassastır.

---

## 4. Sayısal Finansal Grounding

30 cevap üzerinde grounding değerlendirmesi yapılmıştır.

Sayısal finansal değer içeren 14 cevapta toplam:

```text
92 finansal sayı
```

tespit edilmiştir.

Bu değerlerin:

```text
92 / 92
```

adedi ilgili tool evidence tarafından desteklenmiştir.

```text
Numeric Financial Grounding = %100
```

> Bu değer yalnızca tespit edilen sayısal finansal ifadelerin grounding başarısını gösterir.  
> Bütün agent'ın genel doğruluğu anlamına gelmez.

---

## 5. Deterministik Retrieval

24 frozen sorgu üzerinde deterministic backend değerlendirilmiştir.

Final V3 sonucu:

```text
TP = 130
FP = 0
FN = 0
```

| Metrik | Sonuç |
|---|---:|
| Micro Precision | **%100** |
| Micro Recall | **%100** |
| Micro F1 | **%100** |
| Exact Retrieved Set Match | **24/24** |
| Retrieved-record Source Integrity | **130/130** |

Retrieval V1 evaluator implementasyon hataları nedeniyle geçersiz sayılmıştır.

Final V3, kaydedilmiş V2 prediction'larının düzeltilmiş evaluator semantiğiyle offline yeniden skorlanmasıdır.

---

## 6. Çok Turlu Konuşma

10 frozen senaryo üzerinde toplam 77 context kontrolü gerçekleştirilmiştir.

### Pre-fix

```text
Context Checks:
66 / 77 = %85.71

Scenario Exact:
8 / 10 = %80.00
```

Benchmark sırasında iki bank-switch context problemi tespit edilmiştir.

Production'a contextual bank follow-up guard eklenmiştir.

### Post-fix

Aynı frozen test seti yeniden kullanılmıştır.

```text
Context Checks:
77 / 77 = %100

Scenario Exact:
10 / 10 = %100
```

| Metrik | Pre-fix | Post-fix |
|---|---:|---:|
| Context Check Accuracy | 85.71% | **100.00%** |
| Scenario Exact Success | 80.00% | **100.00%** |

---

## 7. No-data Safety

12 frozen no-data vakasında toplam 108 safety check gerçekleştirilmiştir.

### Pre-fix

```text
107 / 108 = %99.07
11 / 12 exact case = %91.67
```

Bir `all-banks + zero-record` status contract problemi tespit edilmiştir.

### Post-fix

Aynı frozen set tekrar kullanılmıştır.

```text
108 / 108 = %100
12 / 12 = %100 exact case
```

Final post-fix değerlendirmesinde:

```text
Requested-target record leak = 0
Invalid source URL = 0
Unsupported numeric claim = 0
Answer URL leak = 0
```

| Metrik | Pre-fix | Post-fix |
|---|---:|---:|
| Safety Check Accuracy | 99.07% | **100.00%** |
| Case Exact Success | 91.67% | **100.00%** |

---

# Değerlendirme Metodolojisi Hakkında Notlar

Değerlendirme sonuçlarının doğru yorumlanması için aşağıdaki sınırlamalar dikkate alınmalıdır.

Intent, structured filter ve grounding test setleri **assistant-authored frozen evaluation setleri**dir.

Bunlar bağımsız insan anotasyonlu akademik benchmarklar olarak sunulmamaktadır.

Retrieval değerlendirmesinde ground truth master veri setinden deterministik olarak oluşturulmuştur.

Retrieval V3 sonucu, önceden kaydedilmiş prediction'lar üzerinde yapılan evaluator semantics correction sonrasında elde edilen offline rescore sonucudur.

Multi-turn ve no-data post-fix sonuçları, pre-fix değerlendirmelerinde kullanılan **aynı frozen test setleri** üzerinde gerçekleştirilmiştir.

Bu nedenle Harput Finans için tek bir:

```text
Overall Accuracy
```

değeri raporlanmamaktadır.

---

# Web Arayüzü

Harput Finans tek web uygulamasında üç temel modül sunar.

## AI Asistan

- Doğal dilde finansal soru sorma
- Finansman ürünü bulma
- Kampanya bulma
- Banka filtreleme
- Finansman karşılaştırma
- Kampanya karşılaştırma
- Follow-up sorguları
- Kaynak görüntüleme

## Bilgi Çıkarımı

- Serbest finansal metin girişi
- Dinamik extractor üretimi
- 9 alanlı yapılandırılmış sonuç
- JSON görünümü

## Sistem & Veri

- Toplam banka
- Toplam kayıt
- Finansman sayısı
- Kampanya sayısı
- Veri dağılımı
- Sistem durumu

---

# API

Backend **FastAPI** üzerinde çalışmaktadır.

Ana endpointler:

```text
GET  /health
POST /chat
POST /chat/reset
POST /extract
GET  /
```

## `GET /health`

Servisin çalışma durumunu kontrol eder.

## `POST /chat`

AI Asistan sorgusunu işler.

Örnek:

```json
{
  "message": "Kuveyt Türk konut finansmanlarını göster.",
  "session_id": "optional"
}
```

## `POST /chat/reset`

Belirtilen session'ın konuşma durumunu sıfırlar.

## `POST /extract`

Serbest finansal metni bilgi çıkarımı pipeline'ına gönderir.

## `GET /`

Web arayüzünü sunar.

---

# Kullanılan Modeller

Harput Finans'ta agent ve extraction görevleri birbirinden ayrılmıştır.

## AI Asistan

```text
qwen3.5:35b-a3b-q8_0
```

Görevleri:

```text
Niyet analizi
Structured parsing
Doğal dil cevap üretimi
```

Finansal retrieval ve karşılaştırma işlemleri model yerine deterministik backend tarafından gerçekleştirilir.

## Bilgi Çıkarımı

```text
qwen3-coder-next
```

Görevi:

```text
Kaynak finansal metinden
alan çıkarımı gerçekleştirecek
Python + regex extractor kodu üretmek
```

---

# On-Premise Yaklaşımı

Harput Finans yerel model çalıştırmayı desteklemektedir.

LLM çalışma katmanında:

```text
Ollama
```

kullanılmaktadır.

Varsayılan servis adresi:

```text
http://127.0.0.1:11434
```

Bu sayede uygun donanıma sahip kurumlarda sistem temel AI işlemlerini haricî bir LLM API'sine ihtiyaç duymadan çalıştırabilir.

Cloudflare Tunnel yalnızca yarışma/demo ortamında web uygulamasının dış erişime açılması için kullanılabilir.

---

# Teknolojiler

## Programlama

```text
Python
HTML
CSS
JavaScript
```

## Web Scraping

```text
Requests
BeautifulSoup
Playwright
Selenium
```

## Backend

```text
FastAPI
Uvicorn
Pydantic
```

## AI / Agent

```text
Ollama
Qwen3.5
Qwen3-Coder-Next
LangGraph
```

## Veri

```text
JSON
```

## Geliştirme

```text
Google Colab
Jupyter Notebook
Python Virtual Environment
```

## Demo

```text
Cloudflare Tunnel
```

---

# Proje Yapısı

```text
harput-finans/
│
├── app/
│   ├── discovery/
│   ├── dynamic_extractor/
│   ├── processors/
│   └── scrapers/
│
├── data/
│   ├── final_banks/
│   │   └── katilim_finans_master.json
│   └── test/
│
├── colab dosyaları/
│   ├── uygulama dosyaları/
│   │   └── Harput_Finans.ipynb
│   └── veri çekme dosyalarının devamı/
│
├── evaluation/
│   ├── figures/
│   └── results/
│
├── docs/
│
├── requirements.txt
├── LICENSE
├── .gitignore
└── README.md
```

> Ana uygulama notebooku repoda da `Harput_Finans.ipynb` olarak yeniden adlandırılmalıdır.

---

# Veri Toplama Katmanı

`app/scrapers` klasörü katılım bankalarının resmî web sitelerinden finansman ve kampanya verilerinin toplanması için kullanılan banka bazlı scraperları içerir.

Web altyapıları farklı olduğu için bankaya göre:

```text
Requests
BeautifulSoup
Playwright
Selenium
URL Discovery
HTML Parsing
```

gibi farklı yöntemler kullanılmıştır.

---

# Veri Hazırlama Katmanı

`app/processors` scraper çıktılarının final veri setine dönüşmeden önce işlendiği katmandır.

Genel akış:

```text
RAW
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

Processor scriptleri:

```text
extraction
normalization
validation
inspection
cleanup
bank-specific patch
merge
```

işlemlerini gerçekleştirir.

---

# Final Dataset

Banka bazlı final dosyaları:

```text
data/final_banks/
```

altında bulunmaktadır.

Ana master dataset:

```text
data/final_banks/katilim_finans_master.json
```

Raw GitHub bağlantısı:

```text
https://raw.githubusercontent.com/HarputAI-Teknofest2026/harput-finans/main/data/final_banks/katilim_finans_master.json
```

Banka bazlı final dataset klasörü:

```text
https://github.com/HarputAI-Teknofest2026/harput-finans/tree/main/data/final_banks
```

---

# Kurulum

Repository'yi klonlayın:

```bash
git clone https://github.com/HarputAI-Teknofest2026/harput-finans.git
```

Proje dizinine geçin:

```bash
cd harput-finans
```

Sanal ortam oluşturun:

```bash
python -m venv .venv
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

Bağımlılıkları yükleyin:

```bash
pip install -r requirements.txt
```

Playwright kullanılan scraperlar için:

```bash
playwright install
```

---

# Uygulamayı Çalıştırma

Harput Finans'ın ana uygulaması Google Colab / Jupyter Notebook tabanlı olarak geliştirilmiştir.

Ana notebook:

```text
colab dosyaları/uygulama dosyaları/Harput_Finans.ipynb
```

Notebook içerisinde:

```text
Master dataset yükleme
Ollama kontrolü
Agent modeli
Extraction modeli
Deterministik finansman araçları
Deterministik kampanya araçları
LangGraph
Session yönetimi
FastAPI
Web arayüzü
Cloudflare demo
```

bileşenleri bulunmaktadır.

---

# Ollama

Ollama servisinin çalıştığını doğrulamak için:

```bash
ollama list
```

Servis aktif değilse:

```bash
ollama serve
```

Varsayılan servis:

```text
http://127.0.0.1:11434
```

Agent modeli:

```text
qwen3.5:35b-a3b-q8_0
```

Bilgi çıkarımı modeli:

```text
qwen3-coder-next
```

---

# Veri Güvenliği

Harput Finans geliştirilirken aşağıdaki prensipler uygulanmıştır.

## Resmî kaynak kullanımı

Veriler katılım bankalarının halka açık resmî web kaynaklarından toplanmıştır.

## Kaynak URL koruması

Her kayıtta mümkün olduğunca orijinal banka URL'si korunmuştur.

## Kaynak dışı finansal değer üretimini sınırlandırma

Kaynak metinde bulunmayan finansal alanların tahmin edilmesi yerine boş bırakılması hedeflenmiştir.

## Yapılandırılmış veri katmanı

LLM cevabı tek bilgi kaynağı olarak kullanılmaz.

Finansal retrieval ve karşılaştırma yapılandırılmış master dataset ve deterministik araçlar üzerinden gerçekleştirilir.

## Validasyon

Scraping ve veri işleme aşamalarında:

```text
schema
duplicate URL
duplicate record
record count
bank identity
source URL
financial field format
```

kontrolleri uygulanmıştır.

---

# Harput Finans'ın Temel Farkı

Harput Finans yalnızca bir chatbot değildir.

Sistem:

```text
RESMÎ WEB KAYNAKLARI
        +
VERİ TOPLAMA
        +
VERİ TEMİZLEME
        +
NORMALİZASYON
        +
PROGRAM-SENTEZİ TABANLI
BİLGİ ÇIKARIMI
        +
CANONICAL SINIFLANDIRMA
        +
DETERMİNİSTİK RETRIEVAL
        +
DETERMİNİSTİK KARŞILAŞTIRMA
        +
LANGGRAPH AGENT
        +
ÇOK TURLU KONUŞMA
        +
KAYNAK-TEMELLİ YANIT
        +
FASTAPI
        +
WEB ARAYÜZÜ
```

bileşenlerinden oluşan uçtan uca bir finansal dil ajanıdır.

---

# Lisans

Bu proje **Apache License 2.0** kapsamında lisanslanmıştır.

Detaylar:

```text
LICENSE
```

dosyasında bulunmaktadır.

---

# Harput Finans

> **Katılım finansını daha erişilebilir, karşılaştırılabilir ve kaynak-temelli hâle getiriyoruz.**

---

## Yarışma Etiketleri

- Bilişim Vadisi 2026: `BilisimVadisi2026`
- Türkiye Açık Kaynak Platformu: [@tracikkaynak](https://github.com/tracikkaynak)
