import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path
from collections import Counter


# ==================================================================================================
# T.O.M. KATILIM - FINAL PATCH
# ==================================================================================================
#
# Input :
#   data/processed/tom_katilim_final.json
#
# Output:
#   data/processed/tom_katilim_all.json
#
# Snapshot tarihi:
#   23 Ağustos 2026
#
# Bu script:
#   - exact 18-key final schema'yı korur
#   - banka adını normalize eder
#   - kampanya tarihlerini normalize eder
#   - bilinen semantic extraction hatalarını düzeltir
#   - aktif olmayan / henüz başlamamış net kampanyaları finalden çıkarır
#   - duplicate URL ve schema validation yapar
#
# ==================================================================================================


BANK_NAME = "T.O.M. Katılım Bankası A.Ş."

SNAPSHOT_DATE = date(2026, 8, 23)


FINAL_KEYS = [
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


LIST_FIELDS = {
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
}


STRING_FIELDS = set(FINAL_KEYS) - LIST_FIELDS


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

INPUT_FILE = PROCESSED_DIR / "tom_katilim_final.json"

OUTPUT_FILE = PROCESSED_DIR / "tom_katilim_all.json"


# ==================================================================================================
# AY İSİMLERİ
# ==================================================================================================

MONTH_TO_INT = {
    "ocak": 1,
    "şubat": 2,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "agustos": 8,
    "eylül": 9,
    "eylul": 9,
    "ekim": 10,
    "kasım": 11,
    "kasim": 11,
    "aralık": 12,
    "aralik": 12,
}


INT_TO_MONTH = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık",
}


MONTH_PATTERN = (
    r"Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|Haziran|"
    r"Temmuz|Ağustos|Agustos|Eylül|Eylul|Ekim|Kasım|Kasim|"
    r"Aralık|Aralik"
)


# ==================================================================================================
# AKTİF FINALDEN ÇIKARILACAK NET KAYITLAR
# ==================================================================================================
#
# 1) Samsung S26:
#    raw kaynak: 01.04.26 - 31.04.26
#    - 31 Nisan geçersiz tarih
#    - Ağustos 2026 snapshot'ında aktif değil
#
# 2) Eczanelerde Hadi Sağlık Kredisi %0:
#    raw kaynak: 1-30 Nisan
#    Ağustos snapshot'ında aktif değil.
#
# 3) Konfor:
#    raw kaynak: 03 Ekim - 31 Aralık 2026
#    23 Ağustos snapshot'ında henüz başlamamış.
#
# ==================================================================================================

DROP_CAMPAIGNS = {
    "TOM Bank Hadi'den Samsung S26 Fırsatı!",
    "Eczanelerde Hadi Sağlık Kredisi ile %0 Vade Farkı ile 6 taksit!",
    "Hadi Mağazadan Alışveriş Kredisi ile Konfor Mağazalarına Özel 15 Taksit!",
}


# ==================================================================================================
# HELPERS
# ==================================================================================================

def normalize_space(value):
    if not isinstance(value, str):
        return ""

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def unique_list(values):
    if not isinstance(values, list):
        return []

    result = []
    seen = set()

    for value in values:
        if not isinstance(value, str):
            continue

        value = normalize_space(value)

        if not value:
            continue

        key = value.casefold()

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


def add_unique(values, value):
    if not isinstance(values, list):
        values = []

    value = normalize_space(value)

    if not value:
        return unique_list(values)

    lowered = {
        normalize_space(x).casefold()
        for x in values
        if isinstance(x, str)
    }

    if value.casefold() not in lowered:
        values.append(value)

    return unique_list(values)


def month_number(name):
    return MONTH_TO_INT.get(
        name.casefold()
    )


def make_date(day, month, year):
    try:
        year = int(year)

        if year < 100:
            year += 2000

        return date(
            int(year),
            int(month),
            int(day),
        )

    except (ValueError, TypeError):
        return None


def format_date(dt):
    return (
        f"{dt.day:02d} "
        f"{INT_TO_MONTH[dt.month]} "
        f"{dt.year}"
    )


def format_period(start_date, end_date):
    if start_date and end_date:
        return (
            f"{format_date(start_date)}"
            f" - "
            f"{format_date(end_date)}"
        )

    if end_date:
        return format_date(end_date)

    return ""


# ==================================================================================================
# KAMPANYA TARİHİ NORMALIZATION
# ==================================================================================================

def extract_existing_year(existing):
    if not isinstance(existing, str):
        return None

    match = re.fullmatch(
        r"(\d{4})-(\d{2})-(\d{2})",
        existing.strip(),
    )

    if not match:
        return None

    return int(match.group(1))


def normalize_existing_iso_date(existing):
    if not isinstance(existing, str):
        return ""

    match = re.fullmatch(
        r"(\d{4})-(\d{2})-(\d{2})",
        existing.strip(),
    )

    if not match:
        return existing.strip()

    dt = make_date(
        match.group(3),
        match.group(2),
        match.group(1),
    )

    if not dt:
        return ""

    return format_date(dt)


def extract_campaign_period(ham_metin, current_value):
    """
    Kaynaktaki kampanya tarihini mümkün olduğunca:

        20 Ağustos 2026 - 31 Ağustos 2026

    şeklinde döndürür.

    Başlangıç tarihi kaynakta yoksa yalnızca bitiş tarihi korunur.
    """

    text = normalize_space(
        ham_metin or ""
    )

    existing_year = extract_existing_year(
        current_value
    )

    # ----------------------------------------------------------------------------------------------
    # 1. DD.MM.YYYY - DD.MM.YYYY
    #    DD/MM/YYYY - DD/MM/YYYY
    #    DD.MM.YY   - DD.MM.YY
    # ----------------------------------------------------------------------------------------------

    match = re.search(
        r"(?<!\d)"
        r"(\d{1,2})[./](\d{1,2})[./](\d{2,4})"
        r"\s*[-–]\s*"
        r"(\d{1,2})[./](\d{1,2})[./](\d{2,4})"
        r"(?!\d)",
        text,
    )

    if match:
        start = make_date(
            match.group(1),
            match.group(2),
            match.group(3),
        )

        end = make_date(
            match.group(4),
            match.group(5),
            match.group(6),
        )

        if start and end:
            return format_period(
                start,
                end,
            )

    # ----------------------------------------------------------------------------------------------
    # 2. 1 Temmuz 2026 - 31 Aralık 2026
    # ----------------------------------------------------------------------------------------------

    match = re.search(
        rf"(\d{{1,2}})\s+({MONTH_PATTERN})\s+(20\d{{2}})"
        rf"\s*[-–]\s*"
        rf"(\d{{1,2}})\s+({MONTH_PATTERN})\s+(20\d{{2}})",
        text,
        re.IGNORECASE,
    )

    if match:
        start = make_date(
            match.group(1),
            month_number(match.group(2)),
            match.group(3),
        )

        end = make_date(
            match.group(4),
            month_number(match.group(5)),
            match.group(6),
        )

        if start and end:
            return format_period(
                start,
                end,
            )

    # ----------------------------------------------------------------------------------------------
    # 3. 01 Temmuz - 31 Aralık 2026
    # ----------------------------------------------------------------------------------------------

    match = re.search(
        rf"(\d{{1,2}})\s+({MONTH_PATTERN})"
        rf"\s*[-–]\s*"
        rf"(\d{{1,2}})\s+({MONTH_PATTERN})\s+(20\d{{2}})",
        text,
        re.IGNORECASE,
    )

    if match:
        year = int(
            match.group(5)
        )

        start = make_date(
            match.group(1),
            month_number(match.group(2)),
            year,
        )

        end = make_date(
            match.group(3),
            month_number(match.group(4)),
            year,
        )

        if start and end:
            return format_period(
                start,
                end,
            )

    # ----------------------------------------------------------------------------------------------
    # 4. 08-31 Ağustos 2026
    # ----------------------------------------------------------------------------------------------

    match = re.search(
        rf"(?<!\d)"
        rf"(\d{{1,2}})\s*[-–]\s*(\d{{1,2}})"
        rf"\s+({MONTH_PATTERN})\s+(20\d{{2}})",
        text,
        re.IGNORECASE,
    )

    if match:
        month = month_number(
            match.group(3)
        )

        year = int(
            match.group(4)
        )

        start = make_date(
            match.group(1),
            month,
            year,
        )

        end = make_date(
            match.group(2),
            month,
            year,
        )

        if start and end:
            return format_period(
                start,
                end,
            )

    # ----------------------------------------------------------------------------------------------
    # 5. 19 Ağustos - 19 Eylül
    #    Yıl mevcut structured end date'ten alınır.
    # ----------------------------------------------------------------------------------------------

    if existing_year:

        match = re.search(
            rf"(\d{{1,2}})\s+({MONTH_PATTERN})"
            rf"\s*[-–]\s*"
            rf"(\d{{1,2}})\s+({MONTH_PATTERN})",
            text,
            re.IGNORECASE,
        )

        if match:
            start = make_date(
                match.group(1),
                month_number(match.group(2)),
                existing_year,
            )

            end = make_date(
                match.group(3),
                month_number(match.group(4)),
                existing_year,
            )

            if start and end:
                return format_period(
                    start,
                    end,
                )

    # ----------------------------------------------------------------------------------------------
    # 6. 31.12.2026'ya kadar
    # ----------------------------------------------------------------------------------------------

    match = re.search(
        r"(?<!\d)"
        r"(\d{1,2})[./](\d{1,2})[./](20\d{2})"
        r"\s*[\'’]?(?:ya|ye|a|e)?\s+kadar",
        text,
        re.IGNORECASE,
    )

    if match:
        end = make_date(
            match.group(1),
            match.group(2),
            match.group(3),
        )

        if end:
            return format_date(end)

    # ----------------------------------------------------------------------------------------------
    # 7. 31 Aralık 2026 tarihine kadar
    # ----------------------------------------------------------------------------------------------

    match = re.search(
        rf"(\d{{1,2}})\s+({MONTH_PATTERN})\s+(20\d{{2}})"
        rf"\s+tarihine\s+kadar",
        text,
        re.IGNORECASE,
    )

    if match:
        end = make_date(
            match.group(1),
            month_number(match.group(2)),
            match.group(3),
        )

        if end:
            return format_date(end)

    # ----------------------------------------------------------------------------------------------
    # 8. Structured ISO bitiş tarihi varsa Türkçe formata çevir
    # ----------------------------------------------------------------------------------------------

    normalized_existing = normalize_existing_iso_date(
        current_value
    )

    return normalized_existing


# ==================================================================================================
# CONDITION CLEANUP
# ==================================================================================================

def clean_conditions(values):
    if not isinstance(values, list):
        return []

    result = []

    exact_noise = {
        "hemen indir",
        "tıklayın",
        "tiklayin",
    }

    for value in values:
        value = normalize_space(value)

        if not value:
            continue

        if value.casefold() in exact_noise:
            continue

        result.append(value)

    return unique_list(result)


# ==================================================================================================
# AVANTAJ CLEANUP
# ==================================================================================================

def clean_advantages(record):
    """
    urun_adi ile birebir aynı olan advantage satırı,
    başka gerçek semantic avantaj varsa kaldırılır.
    """

    title = normalize_space(
        record.get(
            "urun_adi",
            "",
        )
    )

    advantages = unique_list(
        record.get(
            "kampanya_avantaji",
            [],
        )
    )

    if len(advantages) <= 1:
        return advantages

    cleaned = [
        item
        for item in advantages
        if item.casefold()
        != title.casefold()
    ]

    if cleaned:
        return cleaned

    return advantages


# ==================================================================================================
# FURNITURE HESAPLI CAMPAIGN PATCH
# ==================================================================================================

HESAPLI_CAMPAIGNS = {
    "TOM Bank Hadi'den Alfemo Kampanyası!",
    "TOM Bank Hadi'den Kelebek Kampanyası!",
    "TOM Bank Hadi'den Doğtaş Kampanyası!",
    "TOM Bank Hadi'den Enza Home Kampanyası!",
    "TOM Bank Hadi'den Divanev Kampanyası!",
    "TOM Bank Hadi'den Puffy Kampanyası!",
    "TOM Bank Hadi'den Yataş Bedding Kampanyası!",
}


def patch_hesapli_campaign(record):
    record["vade"] = [
        "12 ay"
    ]

    record["kampanya_avantaji"] = [
        "12 ay vadeli kredilerde vade farkı iadesi"
    ]

    record["hedef_kitle"] = unique_list(
        [
            *record.get(
                "hedef_kitle",
                [],
            ),
            "Kazananlar Kulübü Mini Paket üyeleri",
        ]
    )

    return record


# ==================================================================================================
# MAIN RECORD PATCH
# ==================================================================================================

def patch_record(record):
    r = deepcopy(record)

    name = normalize_space(
        r.get(
            "urun_adi",
            "",
        )
    )

    r["banka"] = BANK_NAME

    r["kosullar"] = clean_conditions(
        r.get(
            "kosullar",
            [],
        )
    )

    # ----------------------------------------------------------------------------------------------
    # FINANCE: TAKSİTLİ KREDİ
    #
    # Eski extractor açıklama cümlesini masraf sanmış.
    # Kaynakta bunun bir ücret/masraf olduğu söylenmiyor.
    # ----------------------------------------------------------------------------------------------

    if name == "Taksitli Kredi":

        r["masraf_bilgisi"] = []

    # ----------------------------------------------------------------------------------------------
    # CAMPAIGN DATE NORMALIZATION
    # ----------------------------------------------------------------------------------------------

    if r.get(
        "kayit_turu"
    ) == "kampanya":

        r["kampanya_suresi"] = (
            extract_campaign_period(
                r.get(
                    "ham_metin",
                    "",
                ),
                r.get(
                    "kampanya_suresi",
                    "",
                ),
            )
        )

        r["kampanya_avantaji"] = (
            clean_advantages(r)
        )

    # ----------------------------------------------------------------------------------------------
    # TOM1500
    # ----------------------------------------------------------------------------------------------

    if name == (
        "Toplam 1500 TL hoş geldin hediyesi! "
        "TOM1500 koduyla müşterimiz ol, 1500 TL senin olsun!"
    ):

        r["kampanya_suresi"] = (
            "20 Ağustos 2026 - 31 Ağustos 2026"
        )

        r["kampanya_avantaji"] = [
            "Toplam en fazla 1.500 TL Hediye Bakiye"
        ]

    # ----------------------------------------------------------------------------------------------
    # KLİMA / SÜPÜRGE / TV
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "Hadi Alışveriş Kredisi ile Klima, Süpürge ve "
        "Televizyonlarda Vade Farksız 12 Taksit!"
    ):

        r["kampanya_suresi"] = (
            "08 Ağustos 2026 - 31 Ağustos 2026"
        )

        r["taksit_sayisi"] = [
            "3",
            "6",
            "9",
            "12",
        ]

        r["kampanya_avantaji"] = [
            "Vade farksız 3, 6, 9 veya 12 taksit"
        ]

    # ----------------------------------------------------------------------------------------------
    # RESTODERM
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "Hadi Black Kredi Kartı ile Restoderm'de %30 İndirim!"
    ):

        r["kampanya_suresi"] = (
            "04 Ağustos 2026 - 30 Ağustos 2026"
        )

        r["kampanya_avantaji"] = [
            "%30 indirim"
        ]

    # ----------------------------------------------------------------------------------------------
    # A101 SÜT
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "A101'lerde süt ürünleri harcamalarında %50 Hediye Bakiye kazan!"
    ):

        r["kampanya_suresi"] = (
            "06 Ağustos 2026 - 31 Ağustos 2026"
        )

        r["kampanya_avantaji"] = [
            "%50 Hediye Bakiye",
            "Hadi Kredi Kartı ile günlük en fazla 25 TL, aylık en fazla 100 TL",
            "Hadi Black Kredi Kartı ile günlük en fazla 100 TL, aylık en fazla 250 TL",
            "Çok Kazananlar Kulübü üyesi Hadi Black müşterilerine günlük en fazla 200 TL, aylık en fazla 500 TL",
        ]

    # ----------------------------------------------------------------------------------------------
    # MTV / VERGİ
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "Hadi Black Kredi Kartı ile MTV Ödemelerinde "
        "Vade Farksız 3 taksit fırsatını kaçırma!"
    ):

        r["kampanya_suresi"] = (
            "01 Temmuz 2026 - 31 Ağustos 2026"
        )

        r["taksit_sayisi"] = [
            "3"
        ]

        r["kampanya_avantaji"] = [
            "Vade farksız 3 taksit"
        ]

    # ----------------------------------------------------------------------------------------------
    # Eczane - kredi kartı sonradan taksit
    #
    # 2 ve 3 -> %0
    # 4,5,6  -> %1,99
    #
    # %0 / %1,99 "finansman oranı" değildir.
    # ----------------------------------------------------------------------------------------------

    elif name == "TOM Bank Hadi'den Eczane Kampanyası!!":

        r["finansman_orani"] = []

        r["taksit_sayisi"] = [
            "2",
            "3",
            "4",
            "5",
            "6",
        ]

        r["kampanya_avantaji"] = [
            "2 ve 3 taksitte %0 vade farkı",
            "4, 5 ve 6 taksitte %1,99 vade farkı",
        ]

        r["hedef_kitle"] = [
            "Hadi Kredi Kartı sahipleri",
            "Hadi Black Kredi Kartı sahipleri",
        ]

    # ----------------------------------------------------------------------------------------------
    # Sigorta
    # ----------------------------------------------------------------------------------------------

    elif name == "TOM Bank Hadi'den Sigorta Kampanyası!!":

        r["finansman_orani"] = []

        r["taksit_sayisi"] = [
            "2",
            "3",
            "4",
            "5",
            "6",
        ]

        r["kampanya_avantaji"] = [
            "2 ve 3 taksitte %0 vade farkı",
            "4, 5 ve 6 taksitte %1,99 vade farkı",
        ]

        r["hedef_kitle"] = [
            "Hadi Kredi Kartı sahipleri",
            "Hadi Black Kredi Kartı sahipleri",
        ]

    # ----------------------------------------------------------------------------------------------
    # HESAPLI MOBİLYA KAMPANYALARI
    # ----------------------------------------------------------------------------------------------

    elif name in HESAPLI_CAMPAIGNS:

        r = patch_hesapli_campaign(
            r
        )

    # ----------------------------------------------------------------------------------------------
    # PETROL OFİSİ
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "Petrol Ofisi harcamalarında "
        "Hadi Taksitli Alışveriş Kredisi yanında!"
    ):

        r["taksit_sayisi"] = [
            "3"
        ]

        r["kampanya_avantaji"] = [
            "Petrol Ofisi harcamalarında 3 taksit"
        ]

    # ----------------------------------------------------------------------------------------------
    # HADI TAKSİTLİ SAĞLIK KREDİSİ GENEL
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "Hadi Taksitli Sağlık Kredisi "
        "sağlık harcamalarında da yanında!"
    ):

        r["finansman_orani"] = []

        r["taksit_sayisi"] = [
            "3",
            "6",
            "9",
            "12",
        ]

        r["kampanya_avantaji"] = [
            "Eczane harcamalarında %4,99 vade farkıyla 3 taksit",
            "Diğer sağlık harcamalarında %4,99 vade farkıyla 3, 6, 9 veya 12 taksit",
        ]

    # ----------------------------------------------------------------------------------------------
    # MONDİ
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "Hadi Taksitli Alışveriş Kredisi ile "
        "Mondi Mağazalarında 36 Aya Varan Taksit!"
    ):

        r["kampanya_suresi"] = (
            "31 Aralık 2026"
        )

        r["taksit_sayisi"] = [
            "36"
        ]

        r["kampanya_avantaji"] = [
            "36 aya varan taksit"
        ]

    # ----------------------------------------------------------------------------------------------
    # İSTİKBAL
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "Hadi Taksitli Alışveriş Kredisi ile "
        "İstikbal Mağazalarında 36 Aya Varan Taksit!"
    ):

        r["kampanya_suresi"] = (
            "31 Aralık 2026"
        )

        r["taksit_sayisi"] = [
            "36"
        ]

        r["kampanya_avantaji"] = [
            "36 aya varan taksit"
        ]

    # ----------------------------------------------------------------------------------------------
    # BELLONA
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "Hadi Taksitli Alışveriş Kredisi ile "
        "Bellona Mağazalarında 36 Aya Varan Taksit!"
    ):

        r["kampanya_suresi"] = (
            "31 Aralık 2026"
        )

        r["taksit_sayisi"] = [
            "36"
        ]

        r["kampanya_avantaji"] = [
            "36 aya varan taksit"
        ]

    # ----------------------------------------------------------------------------------------------
    # ALPI
    #
    # Kaynak başlığı 15 taksit,
    # gövde "vade farksız 12 aya varan taksit" diyor.
    #
    # Burada uydurma karar vermiyoruz.
    # Her iki source-backed değer kosullar'da zaten korunuyor.
    # Main field'da title'ın açık avantajını esas alıyoruz.
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "Hadi Mağazadan Alışveriş Kredisi ile "
        "Alpi Diş Hastanelerinde 15 Taksit!"
    ):

        r["kampanya_suresi"] = (
            "31 Aralık 2026"
        )

        r["taksit_sayisi"] = [
            "15"
        ]

        r["kampanya_avantaji"] = [
            "15 taksit"
        ]

    # ----------------------------------------------------------------------------------------------
    # SAMSUNG BEYAZ EŞYA
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "Hadi Mağazadan Alışveriş Kredisi ile "
        "Samsung Beyaz Eşya Alışverişlerine 12 Taksit!"
    ):

        r["kampanya_suresi"] = (
            "31 Aralık 2026"
        )

        r["taksit_sayisi"] = [
            "9",
            "12",
        ]

        r["kampanya_avantaji"] = [
            "Samsung beyaz eşya alışverişlerinde 9 veya 12 taksit"
        ]

        r["hedef_kitle"] = [
            "Hadi Taksitli Kredi limiti yeterli olan müşteriler"
        ]

    # ----------------------------------------------------------------------------------------------
    # KREDİ KARTI SONRADAN TAKSİTLENDİRME
    # ----------------------------------------------------------------------------------------------

    elif name == "Hadi Kredi Kartı ile sonradan taksitlendir!":

        r["vade"] = [
            "12 aya kadar"
        ]

        r["kampanya_avantaji"] = [
            "Eğitim, sağlık ve sigorta harcamalarını 12 aya kadar sonradan taksitlendirme"
        ]

        r["hedef_kitle"] = [
            "Hadi Kredi Kartı sahipleri"
        ]

        r["para_birimi"] = [
            "TL"
        ]

    # ----------------------------------------------------------------------------------------------
    # MEMORIAL
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "Hadi Taksitli Sağlık Kredisi ile Memorial "
        "harcamaların %0,99 vade farkına 3 taksit!"
    ):

        r["finansman_orani"] = []

        r["vade"] = [
            "12 aya varan"
        ]

        r["taksit_sayisi"] = [
            "3",
            "6",
            "9",
            "12",
        ]

        r["kampanya_avantaji"] = [
            "3 taksitte %0,99 vade farkı",
            "6, 9 veya 12 taksitte %1,99 vade farkı",
        ]

        r["kampanya_suresi"] = (
            "31 Aralık 2026"
        )

        r["hedef_kitle"] = [
            "Hadi Taksitli Kredi limiti yeterli olan müşteriler"
        ]

    # ----------------------------------------------------------------------------------------------
    # FINAL NORMALIZATION
    # ----------------------------------------------------------------------------------------------

    for field in LIST_FIELDS:

        value = r.get(
            field,
            [],
        )

        if not isinstance(
            value,
            list,
        ):
            value = []

        r[field] = unique_list(
            value
        )

    for field in STRING_FIELDS:

        value = r.get(
            field,
            "",
        )

        if value is None:
            value = ""

        if not isinstance(
            value,
            str,
        ):
            value = str(value)

        r[field] = normalize_space(
            value
        )

    # Exact 18-key final
    return {
        key: (
            r.get(key, [])
            if key in LIST_FIELDS
            else r.get(key, "")
        )
        for key in FINAL_KEYS
    }


# ==================================================================================================
# VALIDATION
# ==================================================================================================

def validate_records(records):
    errors = []

    urls = []

    for index, record in enumerate(
        records,
        start=1,
    ):

        prefix = (
            f"[{index:02d}] "
            f"{record.get('urun_adi', '')}"
        )

        # Exact schema/order
        if list(
            record.keys()
        ) != FINAL_KEYS:

            errors.append(
                f"{prefix} -> schema/order hatası"
            )

        # List types
        for field in LIST_FIELDS:

            if not isinstance(
                record.get(field),
                list,
            ):
                errors.append(
                    f"{prefix} -> "
                    f"{field} list değil"
                )

        # String types
        for field in STRING_FIELDS:

            if not isinstance(
                record.get(field),
                str,
            ):
                errors.append(
                    f"{prefix} -> "
                    f"{field} string değil"
                )

        # Bank name
        if record.get(
            "banka"
        ) != BANK_NAME:

            errors.append(
                f"{prefix} -> banka adı yanlış"
            )

        # Record type
        if record.get(
            "kayit_turu"
        ) not in {
            "finansman",
            "kampanya",
        }:

            errors.append(
                f"{prefix} -> kayit_turu yanlış"
            )

        # TRY forbidden
        if "TRY" in record.get(
            "para_birimi",
            [],
        ):

            errors.append(
                f"{prefix} -> TRY kullanılmış"
            )

        url = record.get(
            "kaynak_url",
            "",
        ).strip()

        if url:
            urls.append(url)

    # Duplicate URL
    counts = Counter(
        urls
    )

    for url, count in counts.items():

        if count > 1:

            errors.append(
                f"Duplicate URL: {url}"
            )

    # ----------------------------------------------------------------------------------------------
    # CRITICAL SEMANTIC ASSERTIONS
    # ----------------------------------------------------------------------------------------------

    by_name = {
        r["urun_adi"]: r
        for r in records
    }

    # Taksitli kredi masraf
    r = by_name.get(
        "Taksitli Kredi"
    )

    if r and r["masraf_bilgisi"]:

        errors.append(
            "Taksitli Kredi -> "
            "masraf_bilgisi boş olmalı"
        )

    # Eczane
    r = by_name.get(
        "TOM Bank Hadi'den Eczane Kampanyası!!"
    )

    if r:

        if r["taksit_sayisi"] != [
            "2",
            "3",
            "4",
            "5",
            "6",
        ]:
            errors.append(
                "Eczane -> taksit extraction yanlış"
            )

        if r["finansman_orani"]:
            errors.append(
                "Eczane -> vade farkı finansman_orani'nda kaldı"
            )

    # Sigorta
    r = by_name.get(
        "TOM Bank Hadi'den Sigorta Kampanyası!!"
    )

    if r:

        if r["taksit_sayisi"] != [
            "2",
            "3",
            "4",
            "5",
            "6",
        ]:
            errors.append(
                "Sigorta -> taksit extraction yanlış"
            )

        if r["finansman_orani"]:
            errors.append(
                "Sigorta -> vade farkı finansman_orani'nda kaldı"
            )

    # Memorial
    r = by_name.get(
        "Hadi Taksitli Sağlık Kredisi ile Memorial "
        "harcamaların %0,99 vade farkına 3 taksit!"
    )

    if r:

        if r["taksit_sayisi"] != [
            "3",
            "6",
            "9",
            "12",
        ]:
            errors.append(
                "Memorial -> 6 taksit eksik"
            )

        if r["finansman_orani"]:
            errors.append(
                "Memorial -> vade farkı finansman_orani'nda kaldı"
            )

    # Dropped campaigns guard
    for name in DROP_CAMPAIGNS:

        if name in by_name:

            errors.append(
                f"Final active dataset'te olmaması gereken kayıt kaldı: {name}"
            )

    return errors


# ==================================================================================================
# AUDIT
# ==================================================================================================

def print_audit(
    input_count,
    records,
    dropped,
):
    finance = [
        r
        for r in records
        if r["kayit_turu"] == "finansman"
    ]

    campaigns = [
        r
        for r in records
        if r["kayit_turu"] == "kampanya"
    ]

    duplicate_urls = [
        url
        for url, count in Counter(
            r["kaynak_url"]
            for r in records
            if r["kaynak_url"]
        ).items()
        if count > 1
    ]

    exact_schema = sum(
        1
        for r in records
        if list(r.keys()) == FINAL_KEYS
    )

    blank_campaign_advantage = sum(
        1
        for r in campaigns
        if not r["kampanya_avantaji"]
    )

    blank_campaign_period = sum(
        1
        for r in campaigns
        if not r["kampanya_suresi"]
    )

    wrong_campaign_finance_ratio = sum(
        1
        for r in campaigns
        if r["finansman_orani"]
    )

    print()
    print("=" * 115)
    print("T.O.M. KATILIM - FINAL PATCH AUDIT")
    print("=" * 115)

    print(
        f"Input kayıt         : {input_count}"
    )

    print(
        f"Final kayıt         : {len(records)}"
    )

    print(
        f"Finansman           : {len(finance)}"
    )

    print(
        f"Kampanya            : {len(campaigns)}"
    )

    print(
        f"Çıkarılan kayıt     : {len(dropped)}"
    )

    print(
        f"Exact 18-key schema : "
        f"{exact_schema}/{len(records)}"
    )

    print(
        f"Duplicate URL       : "
        f"{len(duplicate_urls)}"
    )

    print(
        f"Avantajı boş kamp.  : "
        f"{blank_campaign_advantage}"
    )

    print(
        f"Süresi boş kamp.    : "
        f"{blank_campaign_period}"
    )

    print(
        f"Campaign fin.oranı  : "
        f"{wrong_campaign_finance_ratio}"
    )

    print()
    print("ÇIKARILAN KAYITLAR")
    print("-" * 115)

    if not dropped:
        print("Yok")
    else:
        for name in dropped:
            print(
                f"❌ {name}"
            )

    print()
    print("KRİTİK KONTROLLER")
    print("-" * 115)

    by_name = {
        r["urun_adi"]: r
        for r in records
    }

    critical = [
        "Taksitli Kredi",
        "TOM Bank Hadi'den Eczane Kampanyası!!",
        "TOM Bank Hadi'den Sigorta Kampanyası!!",
        "Hadi Taksitli Sağlık Kredisi sağlık harcamalarında da yanında!",
        "Hadi Kredi Kartı ile sonradan taksitlendir!",
        "Hadi Taksitli Sağlık Kredisi ile Memorial harcamaların %0,99 vade farkına 3 taksit!",
        "Hadi Mağazadan Alışveriş Kredisi ile Samsung Beyaz Eşya Alışverişlerine 12 Taksit!",
    ]

    for name in critical:

        r = by_name.get(
            name
        )

        if not r:
            print(
                f"⚠️ Bulunamadı: {name}"
            )
            continue

        print(
            f"✅ {name}"
        )

        print(
            f"   Süre      : "
            f"{r['kampanya_suresi']}"
        )

        print(
            f"   Taksit    : "
            f"{r['taksit_sayisi']}"
        )

        print(
            f"   Vade      : "
            f"{r['vade']}"
        )

        print(
            f"   Fin.Oranı : "
            f"{r['finansman_orani']}"
        )

        print(
            f"   Avantaj   : "
            f"{r['kampanya_avantaji']}"
        )

    print("=" * 115)


# ==================================================================================================
# MAIN
# ==================================================================================================

def main():
    print()
    print("=" * 115)
    print("T.O.M. KATILIM - FINAL PATCH")
    print("=" * 115)

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            "\nInput bulunamadı:\n"
            f"{INPUT_FILE}\n"
            "\n"
            "tom_katilim_final.json dosyasını "
            "data/processed klasörüne koy."
        )

    print(
        f"Input : {INPUT_FILE}"
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print(
        f"Snapshot tarihi: "
        f"{SNAPSHOT_DATE.strftime('%d.%m.%Y')}"
    )

    print()

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        raw_records = json.load(
            f
        )

    if not isinstance(
        raw_records,
        list,
    ):

        raise ValueError(
            "JSON root list olmalı."
        )

    patched_records = []

    dropped = []

    for index, record in enumerate(
        raw_records,
        start=1,
    ):

        name = normalize_space(
            record.get(
                "urun_adi",
                "",
            )
        )

        # ------------------------------------------------------------------------------------------
        # Active snapshot filter
        # ------------------------------------------------------------------------------------------

        if (
            record.get("kayit_turu")
            == "kampanya"
            and name in DROP_CAMPAIGNS
        ):

            dropped.append(
                name
            )

            print(
                f"[{index:02d}/{len(raw_records)}] "
                f"SKIP ❌ {name}"
            )

            continue

        patched = patch_record(
            record
        )

        patched_records.append(
            patched
        )

        print(
            f"[{index:02d}/{len(raw_records)}] "
            f"OK ✅ {patched['urun_adi']}"
        )

    errors = validate_records(
        patched_records
    )

    print_audit(
        input_count=len(raw_records),
        records=patched_records,
        dropped=dropped,
    )

    if errors:

        print()
        print("=" * 115)
        print("VALIDATION ERRORS")
        print("=" * 115)

        for error in errors:
            print(
                f"❌ {error}"
            )

        print()
        print(
            "SONUÇ: T.O.M. FINAL PATCH BAŞARISIZ ❌"
        )

        raise SystemExit(1)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            patched_records,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 115)
    print("T.O.M. KATILIM FINAL PATCH BAŞARILI ✅")
    print("=" * 115)

    print(
        f"JSON: {OUTPUT_FILE}"
    )

    print()
    print(
        "Banka adı standardize edildi ✅"
    )

    print(
        "Taksitli Kredi masraf false-positive temizlendi ✅"
    )

    print(
        "Kampanya tarihleri normalize edildi ✅"
    )

    print(
        "Eczane/Sigorta 4 taksit düzeltildi ✅"
    )

    print(
        "Memorial 6 taksit düzeltildi ✅"
    )

    print(
        "Vade farkları finansman_orani alanından çıkarıldı ✅"
    )

    print(
        "Eksik kampanya avantajları tamamlandı ✅"
    )

    print(
        "Aktif snapshot dışı net kampanyalar çıkarıldı ✅"
    )

    print(
        "Exact 18-key schema korundu ✅"
    )

    print("=" * 115)


if __name__ == "__main__":
    main()