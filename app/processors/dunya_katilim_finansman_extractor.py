import json
import re
import sys
from pathlib import Path


# =========================================================
# PATHS
# =========================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT
    / "data"
    / "raw"
    / "dunya_katilim_finansman_urunleri.json"
)

OUTPUT_FILE = (
    ROOT
    / "data"
    / "processed"
    / "dunya_katilim_finansman_extracted.json"
)


# =========================================================
# CONSTANTS
# =========================================================

BANK_NAME = "Dünya Katılım Bankası A.Ş."

EXPECTED_COUNT = 6


COMMON_SCHEMA = [
    "banka",
    "kayit_turu",
    "urun_adi",
    "urun_kategorisi",

    "kar_payi_orani",
    "finansman_orani",
    "finansman_tutari",
    "vade",
    "taksit_sayisi",

    "masraf_bilgisi",

    "kampanya_turu",
    "kampanya_avantaji",
    "kampanya_suresi",

    "hedef_kitle",
    "para_birimi",
    "kosullar",

    "kaynak_url",
    "ham_metin",
]


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_text(text):

    text = str(
        text or ""
    )

    replacements = {
        "\xa0": " ",
        "’": "'",
        "‘": "'",
        "´": "'",
        "`": "'",
        "–": "-",
        "—": "-",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    return text.strip()


def normalize_match(text):

    text = normalize_text(
        text
    )

    text = text.replace(
        "İ",
        "i"
    )

    text = text.replace(
        "I",
        "ı"
    )

    text = text.casefold()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def contains(
    text,
    term
):

    return (
        normalize_match(term)
        in normalize_match(text)
    )


def unique_list(values):

    result = []

    seen = set()

    for value in values:

        value = normalize_text(
            value
        )

        if not value:
            continue

        key = normalize_match(
            value
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            value
        )

    return result


# =========================================================
# RAW LOAD
# =========================================================

def load_raw():

    if not INPUT_FILE.exists():

        print(
            f"RAW dosya bulunamadı: {INPUT_FILE}"
        )

        sys.exit(
            1
        )

    try:

        with INPUT_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

    except json.JSONDecodeError as error:

        print(
            "JSON parse hatası:"
        )

        print(
            error
        )

        sys.exit(
            1
        )

    if not isinstance(
        data,
        dict
    ):

        print(
            "RAW root dict/object değil."
        )

        sys.exit(
            1
        )

    records = data.get(
        "urunler"
    )

    if not isinstance(
        records,
        list
    ):

        print(
            "'urunler' list değil."
        )

        sys.exit(
            1
        )

    return records


# =========================================================
# SOURCE ASSERT
# =========================================================

def require_terms(
    title,
    raw_text,
    terms
):

    missing = []

    for term in terms:

        if not contains(
            raw_text,
            term
        ):

            missing.append(
                term
            )

    if missing:

        raise ValueError(
            (
                f"{title}: Kaynakta beklenen kritik "
                f"ifadeler bulunamadı -> {missing}"
            )
        )


# =========================================================
# BASE RECORD
# =========================================================

def create_base_record(
    raw_record,
    category
):

    return {
        "banka": BANK_NAME,
        "kayit_turu": "finansman",
        "urun_adi": raw_record.get(
            "urun_adi",
            ""
        ),
        "urun_kategorisi": category,

        "kar_payi_orani": [],
        "finansman_orani": [],
        "finansman_tutari": [],
        "vade": [],
        "taksit_sayisi": [],

        "masraf_bilgisi": [],

        "kampanya_turu": "",
        "kampanya_avantaji": [],
        "kampanya_suresi": "",

        "hedef_kitle": [],
        "para_birimi": [],
        "kosullar": [],

        "kaynak_url": raw_record.get(
            "kaynak_url",
            ""
        ),
        "ham_metin": raw_record.get(
            "ham_metin",
            ""
        ),
    }


# =========================================================
# 1 - İHTİYAÇ FİNANSMANI
# =========================================================

def extract_ihtiyac(
    raw_record
):

    raw_text = raw_record[
        "ham_metin"
    ]

    require_terms(
        "İhtiyaç Finansmanı",
        raw_text,
        [
            "0 – 125.000",
            "125.001 – 250.000",
            "250.001 – 500.000",
            "36 ay",
            "24 ay",
            "12 ay",
            "18 yaşını doldurmuş",
        ],
    )

    record = create_base_record(
        raw_record,
        "İhtiyaç Finansmanı"
    )

    # Widget'taki 1.000 / 50.000 değerleri alınmıyor.
    record[
        "finansman_tutari"
    ] = [
        "0 - 125.000 TL",
        "125.001 - 250.000 TL",
        "250.001 - 500.000 TL",
    ]

    # Kaynak bunları sabit vade değil,
    # ilgili tutar bandı için azami süre olarak veriyor.
    record[
        "vade"
    ] = [
        "36 aya kadar",
        "24 aya kadar",
        "12 aya kadar",
    ]

    record[
        "masraf_bilgisi"
    ] = [
        (
            "Tahsis ücreti müşteriden peşin olarak "
            "tahsil edilir; ödenecek toplam tutar "
            "finansman tahsis ücretini içermez."
        ),
    ]

    record[
        "hedef_kitle"
    ] = [
        "Bireysel müşteriler",
        "İşletme sahipleri",
    ]

    record[
        "para_birimi"
    ] = [
        "TL",
    ]

    record[
        "kosullar"
    ] = [
        (
            "0 - 125.000 TL arası finansmanda "
            "geri ödeme süresi 0 - 36 ay arasında olabilir."
        ),
        (
            "125.001 - 250.000 TL arası finansmanda "
            "geri ödeme süresi 0 - 24 ay arasında olabilir."
        ),
        (
            "250.001 - 500.000 TL arası finansmanda "
            "geri ödeme süresi 0 - 12 ay arasında olabilir."
        ),
        "Başvuru sahibinin 18 yaşını doldurmuş olması gerekir.",
        "Başvuru sahibinin düzenli gelire sahip olması gerekir.",
        (
            "Kredi notu, ödeme alışkanlıkları ve finansal geçmiş "
            "bankanın tahsis kriterlerine göre değerlendirilir."
        ),
        (
            "Geçerli kimlik ve güncel adres bilgilerinin "
            "doğrulanması gerekir."
        ),
        (
            "Finansman kullanım amacının doğrulanması gerekir."
        ),
        (
            "Banka gerekli görürse teminat veya kefil "
            "talep edebilir."
        ),
        (
            "Finansman doğrudan nakit olarak verilmez; "
            "mal veya hizmet bedeli satıcıya ya da "
            "hizmet sağlayıcıya aktarılır."
        ),
    ]

    return record


# =========================================================
# 2 - ENERYA İHTİYAÇ
# =========================================================

def extract_enerya_ihtiyac(
    raw_record
):

    raw_text = raw_record[
        "ham_metin"
    ]

    require_terms(
        "Enerya İhtiyaç Finansmanı",
        raw_text,
        [
            "250.000 TL",
            "36 ay",
            "%3,99",
            "proforma fatura",
            "ödeme müşteriye değil, satıcıya",
        ],
    )

    record = create_base_record(
        raw_record,
        "İhtiyaç Finansmanı"
    )

    record[
        "kar_payi_orani"
    ] = [
        "%3,99",
    ]

    # Kaynakta "maksimum 250.000 TL" olarak geçiyor.
    record[
        "finansman_tutari"
    ] = [
        "250.000 TL'ye kadar",
    ]

    # Kaynakta 36 aya kadar / maksimum 36 ay.
    record[
        "vade"
    ] = [
        "36 aya kadar",
    ]

    record[
        "hedef_kitle"
    ] = [
        (
            "Enerya Enerji A.Ş. faaliyet alanındaki illerde "
            "doğalgaz dönüşümü kapsamında abonelik işlemleri "
            "başlatan Dünya Katılım müşterileri"
        ),
    ]

    record[
        "para_birimi"
    ] = [
        "TL",
    ]

    record[
        "kosullar"
    ] = [
        "Maksimum finansman tutarı 250.000 TL'dir.",
        "Maksimum vade 36 aydır.",
        "Aylık kâr oranı %3,99'dur.",
        "Başvuru sahibinin 18 yaşını doldurmuş olması gerekir.",
        (
            "Kimlik kartı, ehliyet veya pasaport "
            "ibraz edilmelidir."
        ),
        (
            "Finansmana konu olan proforma fatura "
            "ibraz edilmelidir."
        ),
        (
            "Finansman kapsamında alınan malın bedeli "
            "müşteriye değil satıcıya ödenir."
        ),
        (
            "Mobil Şube işlemlerinde nihai E-Fatura veya "
            "E-Arşiv Fatura XML (UBL) formatında "
            "sisteme yüklenmelidir."
        ),
    ]

    return record


# =========================================================
# 3 - ENERYA KARZ-I HASEN
# =========================================================

def extract_enerya_karz(
    raw_record
):

    raw_text = raw_record[
        "ham_metin"
    ]

    require_terms(
        "Enerya Karz-ı Hasen",
        raw_text,
        [
            "vade farksız",
            "500 TL",
            "16.500 TL",
            "2 ay",
            "6 ay",
            "Antalya",
            "Aydın",
            "Denizli",
            "Konya",
        ],
    )

    record = create_base_record(
        raw_record,
        "İhtiyaç Finansmanı"
    )

    # "Vade farksız" sayısal %0'a çevrilmiyor.
    record[
        "finansman_tutari"
    ] = [
        "500 TL - 16.500 TL",
    ]

    record[
        "vade"
    ] = [
        "2 ay - 6 ay",
    ]

    record[
        "masraf_bilgisi"
    ] = [
        (
            "Enerya abonelik ücreti finansman tutarının "
            "içinden alınarak Enerya hesabına aktarılır."
        ),
    ]

    record[
        "hedef_kitle"
    ] = [
        (
            "Antalya, Aydın, Denizli ve Konya illerinde "
            "yeni Enerya abonelik işlemi gerçekleştirecek müşteriler"
        ),
    ]

    record[
        "para_birimi"
    ] = [
        "TL",
    ]

    record[
        "kosullar"
    ] = [
        (
            "Antalya, Aydın, Denizli ve Konya illerindeki "
            "yeni abonelik işlemlerinde vade farksız "
            "finansman imkânı sağlanır."
        ),
        "Minimum finansman tutarı 500 TL'dir.",
        "Maksimum finansman tutarı 16.500 TL'dir.",
        "Minimum vade 2 aydır.",
        "Maksimum vade 6 aydır.",
        (
            "Enerya abonelik ücreti finansman tutarından "
            "alınarak Enerya hesabına aktarılır."
        ),
        (
            "Kalan tutar doğal gaz dönüşüm harcamaları "
            "için müşterinin kullanımına bırakılır."
        ),
    ]

    return record


# =========================================================
# 4 - ARAÇ FİNANSMANI
# =========================================================

def extract_arac(
    raw_record
):

    raw_text = raw_record[
        "ham_metin"
    ]

    require_terms(
        "Araç Finansmanı",
        raw_text,
        [
            "0 TL – 400.000 TL 70% 48",
            "400.001 TL – 800.000 TL 50% 36",
            "800.001 TL – 1.200.000 TL 30% 24",
            "1.200.001 TL- 2.000.000 TL 20% 12",
            "2.000.000 ve üzeri 0% 0",
            "12 yaşa kadar",
        ],
    )

    record = create_base_record(
        raw_record,
        "Araç Finansmanı"
    )

    # Bunlar ürünün gerçek LTV oranlarıdır.
    # Widget'taki %0 ile karıştırılmamalıdır.
    record[
        "finansman_orani"
    ] = [
        "%70",
        "%50",
        "%30",
        "%20",
        "%0",
    ]

    # Fatura/kasko değerleri finansman tutarı olmadığı için
    # finansman_tutari alanına yazılmıyor.
    record[
        "finansman_tutari"
    ] = []

    record[
        "vade"
    ] = [
        "48 ay",
        "36 ay",
        "24 ay",
        "12 ay",
    ]

    record[
        "hedef_kitle"
    ] = [
        (
            "Sıfır veya ikinci el araç satın alacak "
            "bireysel müşteriler"
        ),
    ]

    record[
        "para_birimi"
    ] = [
        "TL",
    ]

    record[
        "kosullar"
    ] = [
        (
            "Nihai fatura veya kasko değeri 0 - 400.000 TL "
            "olan araçlarda maksimum finansman oranı %70 "
            "ve azami vade 48 aydır."
        ),
        (
            "Nihai fatura veya kasko değeri "
            "400.001 - 800.000 TL olan araçlarda maksimum "
            "finansman oranı %50 ve azami vade 36 aydır."
        ),
        (
            "Nihai fatura veya kasko değeri "
            "800.001 - 1.200.000 TL olan araçlarda maksimum "
            "finansman oranı %30 ve azami vade 24 aydır."
        ),
        (
            "Nihai fatura veya kasko değeri "
            "1.200.001 - 2.000.000 TL olan araçlarda maksimum "
            "finansman oranı %20 ve azami vade 12 aydır."
        ),
        (
            "Nihai fatura veya kasko değeri 2.000.000 TL "
            "ve üzerindeki araçlarda maksimum finansman "
            "oranı %0 ve azami vade 0 aydır."
        ),
        (
            "İkinci el otomobillerde 12 yaşa kadar "
            "finansman sağlanmaktadır."
        ),
        (
            "0 km araç başvurularında proforma veya "
            "asıl fatura istenir."
        ),
        (
            "İkinci el araç başvurularında ruhsat "
            "fotokopisi istenir."
        ),
    ]

    return record


# =========================================================
# 5 - ÇEVRE DOSTU ARAÇ
# =========================================================

def extract_cevre_dostu_arac(
    raw_record
):

    raw_text = raw_record[
        "ham_metin"
    ]

    require_terms(
        "Çevre Dostu Araç Finansmanı",
        raw_text,
        [
            "elektrikli",
            "hibrit",
            "18 yaşını doldurmuş",
            "proforma fatura",
            "satıcıya veya bayiye doğrudan aktarılır",
        ],
    )

    record = create_base_record(
        raw_record,
        "Araç Finansmanı"
    )

    # Sayfada avantajlı oran deniyor fakat açık sayısal
    # ürün-spesifik oran yok.
    record[
        "kar_payi_orani"
    ] = []

    record[
        "finansman_orani"
    ] = []

    record[
        "finansman_tutari"
    ] = []

    record[
        "vade"
    ] = []

    record[
        "hedef_kitle"
    ] = [
        (
            "Elektrikli veya hibrit araç satın alacak müşteriler"
        ),
    ]

    record[
        "kosullar"
    ] = [
        (
            "Finansmandan yararlanmak için elektrikli "
            "veya hibrit araç satın alınması gerekir."
        ),
        "Başvuru sahibinin 18 yaşını doldurmuş olması gerekir.",
        "Başvuru sahibinin düzenli gelire sahip olması gerekir.",
        (
            "Kredi notu, ödeme alışkanlıkları ve finansal geçmiş "
            "bankanın tahsis kriterlerine göre değerlendirilir."
        ),
        (
            "Geçerli kimlik ve güncel adres bilgilerinin "
            "doğrulanması gerekir."
        ),
        (
            "Sıfır elektrikli veya hibrit araçlarda "
            "proforma fatura gereklidir."
        ),
        (
            "İkinci el elektrikli veya hibrit araçlarda "
            "eski ruhsat gereklidir."
        ),
        (
            "Banka gerekli görürse kefil, araç rehni veya "
            "gayrimenkul gibi ek güvence talep edebilir."
        ),
        (
            "Finansman nakit olarak müşteriye verilmez; "
            "satıcıya veya bayiye doğrudan aktarılır."
        ),
    ]

    return record


# =========================================================
# 6 - KONUT FİNANSMANI
# =========================================================

def extract_konut(
    raw_record
):

    raw_text = raw_record[
        "ham_metin"
    ]

    require_terms(
        "Konut Finansmanı",
        raw_text,
        [
            "Değer x 90%",
            "Değer x 80%",
            "Değer x 70%",
            "Değer x 22.5%",
            "Değer x 17.5%",
            "Değer x 12.5%",
            "%1’i",
            "%2’si",
            "BSMV uygulanmaz",
        ],
    )

    record = create_base_record(
        raw_record,
        "Konut Finansmanı"
    )

    record[
        "finansman_orani"
    ] = [
        "%90",
        "%80",
        "%70",
        "%60",
        "%50",
        "%40",
        "%30",
        "%20",
        "%22,5",
        "%17,5",
        "%15",
        "%12,5",
        "%10",
        "%7,5",
        "%5",
    ]

    # Konut değeri eşikleri finansman tutarı değildir.
    record[
        "finansman_tutari"
    ] = []

    # Widget'taki 1-36 gerçek ürün vadesi değildir.
    record[
        "vade"
    ] = []

    record[
        "masraf_bilgisi"
    ] = [
        (
            "Kalan vade 36 ayı aşmıyorsa erken ödenen "
            "anapara tutarı üzerinden %1 erken ödeme "
            "tazminatı uygulanabilir."
        ),
        (
            "Kalan vade 36 ayın üzerindeyse erken ödenen "
            "anapara tutarı üzerinden %2 erken ödeme "
            "tazminatı uygulanabilir."
        ),
        (
            "Finansmanın kullanıldığı tarihte üzerine kayıtlı "
            "konutu bulunmayan tüketicilerin ilk konut "
            "finansmanında BSMV uygulanmaz."
        ),
        (
            "6306 sayılı Kanun kapsamındaki hak sahiplerine "
            "kullandırılan dönüşüm finansmanlarında "
            "BSMV istisnası uygulanır."
        ),
    ]

    record[
        "hedef_kitle"
    ] = [
        "Ev sahibi olmak isteyen gerçek kişiler",
        "Serbest meslek sahipleri",
    ]

    record[
        "para_birimi"
    ] = [
        "TL",
    ]

    record[
        "kosullar"
    ] = [
        (
            "İlk evini alacaklarda konut değeri 5.000.000 TL "
            "ve altındaysa finansman oranı enerji sınıfı "
            "A-B için %90, C için %80, diğer için %70'tir."
        ),
        (
            "İlk evini alacaklarda konut değeri "
            "5.000.000 - 7.000.000 TL aralığındaysa "
            "A-B için %80, C için %70, diğer için %60'tır."
        ),
        (
            "İlk evini alacaklarda konut değeri "
            "7.000.000 - 10.000.000 TL aralığındaysa "
            "A-B için %70, C için %60, diğer için %50'dir."
        ),
        (
            "İlk evini alacaklarda konut değeri "
            "10.000.000 - 20.000.000 TL aralığındaysa "
            "A-B için %50, C için %40, diğer için %30'dur."
        ),
        (
            "İlk evini alacaklarda konut değeri "
            "20.000.000 TL üzerindeyse A-B için %40, "
            "C için %30, diğer için %20'dir."
        ),

        (
            "İkinci ve sonraki konut alımlarında konut değeri "
            "5.000.000 TL ve altındaysa A-B için %22,5, "
            "C için %20, diğer için %17,5'tir."
        ),
        (
            "İkinci ve sonraki konut alımlarında konut değeri "
            "5.000.000 - 7.000.000 TL aralığındaysa "
            "A-B için %20, C için %17,5, diğer için %15'tir."
        ),
        (
            "İkinci ve sonraki konut alımlarında konut değeri "
            "7.000.000 - 10.000.000 TL aralığındaysa "
            "A-B için %17,5, C için %15, diğer için %12,5'tir."
        ),
        (
            "İkinci ve sonraki konut alımlarında konut değeri "
            "10.000.000 - 20.000.000 TL aralığındaysa "
            "A-B için %12,5, C için %10, diğer için %7,5'tir."
        ),
        (
            "İkinci ve sonraki konut alımlarında konut değeri "
            "20.000.000 TL üzerindeyse A-B için %10, "
            "C için %7,5, diğer için %5'tir."
        ),

        "Başvuru sahibinin 18 yaşını tamamlamış olması gerekir.",
        (
            "Gerçek kişi başvurularında kimlik, gelir belgesi, "
            "maaş bordrosu veya net maaşı gösteren onaylı belge "
            "ve satın alınacak konutun tapu fotokopisi istenir."
        ),
        (
            "Konutun tapuda mesken niteliğinde olması, "
            "projesine aykırı değişiklik bulunmaması, "
            "iskân izinli olması ve hakkında yıkım kararı "
            "bulunmaması gerekir."
        ),
    ]

    return record


# =========================================================
# ROUTER
# =========================================================

def extract_record(
    raw_record
):

    title = raw_record.get(
        "urun_adi",
        ""
    )

    if title == "İhtiyaç Finansmanı":

        return extract_ihtiyac(
            raw_record
        )

    if title == "Enerya İhtiyaç Finansmanı":

        return extract_enerya_ihtiyac(
            raw_record
        )

    if title == "Enerya Karz-ı Hasen":

        return extract_enerya_karz(
            raw_record
        )

    if title == "Araç Finansmanı":

        return extract_arac(
            raw_record
        )

    if title == "Çevre Dostu Araç Finansmanı":

        return extract_cevre_dostu_arac(
            raw_record
        )

    if title == "Konut Finansmanı":

        return extract_konut(
            raw_record
        )

    raise ValueError(
        f"Bilinmeyen ürün: {title}"
    )


# =========================================================
# SCHEMA VALIDATION
# =========================================================

def validate_schema(
    records
):

    errors = []

    expected_keys = set(
        COMMON_SCHEMA
    )

    for index, record in enumerate(
        records,
        start=1
    ):

        actual_keys = set(
            record.keys()
        )

        missing = (
            expected_keys
            - actual_keys
        )

        extra = (
            actual_keys
            - expected_keys
        )

        title = record.get(
            "urun_adi",
            f"Kayıt {index}"
        )

        if missing:

            errors.append(
                (
                    f"{title}: eksik schema alanı -> "
                    f"{sorted(missing)}"
                )
            )

        if extra:

            errors.append(
                (
                    f"{title}: fazla schema alanı -> "
                    f"{sorted(extra)}"
                )
            )

        if record.get(
            "banka"
        ) != BANK_NAME:

            errors.append(
                f"{title}: banka adı yanlış"
            )

        if record.get(
            "kayit_turu"
        ) != "finansman":

            errors.append(
                f"{title}: kayit_turu finansman değil"
            )

        list_fields = [
            "kar_payi_orani",
            "finansman_orani",
            "finansman_tutari",
            "vade",
            "taksit_sayisi",
            "masraf_bilgisi",
            "kampanya_avantaji",
            "hedef_kitle",
            "para_birimi",
            "kosullar",
        ]

        for field in list_fields:

            if not isinstance(
                record.get(
                    field
                ),
                list
            ):

                errors.append(
                    (
                        f"{title}: {field} list değil"
                    )
                )

    return errors


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 118
    )

    print(
        "DÜNYA KATILIM - FİNANSMAN EXTRACTOR V2"
    )

    print(
        "=" * 118
    )

    print(
        "Input:",
        INPUT_FILE
    )

    print(
        "Output:",
        OUTPUT_FILE
    )

    raw_records = load_raw()

    if len(
        raw_records
    ) != EXPECTED_COUNT:

        print(
            (
                "HATA: Beklenen RAW ürün sayısı "
                f"{EXPECTED_COUNT}, gerçek {len(raw_records)}"
            )
        )

        sys.exit(
            1
        )

    extracted = []

    extraction_errors = []

    for index, raw_record in enumerate(
        raw_records,
        start=1
    ):

        title = raw_record.get(
            "urun_adi",
            "?"
        )

        print()

        print(
            "-" * 118
        )

        print(
            f"[{index}/{EXPECTED_COUNT}] {title}"
        )

        try:

            record = extract_record(
                raw_record
            )

            for field in [
                "kar_payi_orani",
                "finansman_orani",
                "finansman_tutari",
                "vade",
                "taksit_sayisi",
                "masraf_bilgisi",
                "kampanya_avantaji",
                "hedef_kitle",
                "para_birimi",
                "kosullar",
            ]:

                record[
                    field
                ] = unique_list(
                    record[
                        field
                    ]
                )

            extracted.append(
                record
            )

            print(
                "Kâr payı:",
                record[
                    "kar_payi_orani"
                ]
            )

            print(
                "Finansman oranı:",
                record[
                    "finansman_orani"
                ]
            )

            print(
                "Finansman tutarı:",
                record[
                    "finansman_tutari"
                ]
            )

            print(
                "Vade:",
                record[
                    "vade"
                ]
            )

            print(
                "Para birimi:",
                record[
                    "para_birimi"
                ]
            )

            print(
                "Koşul sayısı:",
                len(
                    record[
                        "kosullar"
                    ]
                )
            )

            print(
                "EXTRACT: ✅"
            )

        except Exception as error:

            extraction_errors.append(
                (
                    f"{title}: "
                    f"{type(error).__name__}: {error}"
                )
            )

            print(
                "EXTRACT: ❌"
            )

            print(
                error
            )

    schema_errors = validate_schema(
        extracted
    )

    errors = (
        extraction_errors
        + schema_errors
    )

    # =====================================================
    # SAVE
    # =====================================================

    if not errors:

        OUTPUT_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with OUTPUT_FILE.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                extracted,
                file,
                ensure_ascii=False,
                indent=4
            )

    # =====================================================
    # SUMMARY
    # =====================================================

    print()

    print(
        "=" * 118
    )

    print(
        "EXTRACTOR SONUCU"
    )

    print(
        "=" * 118
    )

    print(
        "Beklenen kayıt:",
        EXPECTED_COUNT
    )

    print(
        "Extract edilen:",
        len(
            extracted
        )
    )

    print(
        "Extraction error:",
        len(
            extraction_errors
        )
    )

    print(
        "Schema error:",
        len(
            schema_errors
        )
    )

    print(
        "Toplam error:",
        len(
            errors
        )
    )

    if errors:

        print()

        print(
            "HATALAR:"
        )

        for error in errors:

            print(
                "-",
                error
            )

    print()

    if not errors:

        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "FİNANSMAN EXTRACTION V2 BAŞARILI ✅"
            )
        )

        print(
            "JSON:",
            OUTPUT_FILE
        )

    else:

        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "FİNANSMAN EXTRACTION V2 BAŞARISIZ ❌"
            )
        )

        sys.exit(
            1
        )

    print(
        "=" * 118
    )


if __name__ == "__main__":
    main()