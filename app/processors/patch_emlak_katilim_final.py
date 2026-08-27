import json
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path


# ==================================================================================================
# EMLAK KATILIM - FINAL NORMALIZATION PATCH
# ==================================================================================================
#
# Amaç:
#   - Eski wrapper yapısını kaldırmak
#   - Canonical 18-key schema üretmek
#   - Türkiye Emlak Katılım Bankası A.Ş. adını standardize etmek
#   - TRY -> TL
#   - "12 taksit" -> "12"
#   - Açıklamalı finansman oranlarını sadece % değerlerine indirgemek
#   - Açıklamalı tutar/vade mappinglerini kosullar içinde korumak
#   - Örnek maliyet tablosu değerlerini ana finansman alanlarından çıkarmak
#   - Finansman kayıtlarındaki kampanya_avantaji leakage'ını temizlemek
#   - 23.08.2026 snapshot'ında aktif olmayan kampanyaları çıkarmak
#   - Exact 18-key schema ile data/processed/emlak_katilim_all.json üretmek
#
# ==================================================================================================


BANK_NAME = "Türkiye Emlak Katılım Bankası A.Ş."

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


INPUT_CANDIDATES = [
    PROCESSED_DIR / "emlak_katilim_all.json",
    PROCESSED_DIR / "emlak_katilim_final.json",
    PROCESSED_DIR / "emlak_katilim_all(1).json",
]


OUTPUT_FILE = (
    PROCESSED_DIR
    / "emlak_katilim_all.json"
)


BACKUP_FILE = (
    PROCESSED_DIR
    / "emlak_katilim_all_before_normalization.json"
)


# ==================================================================================================
# CATEGORY NORMALIZATION
# ==================================================================================================

CATEGORY_MAP = {
    "arsa": "Arsa Finansmanı",
    "isyeri": "İş Yeri Finansmanı",
    "yatirim": "Yatırım Finansmanı",
    "konut": "Konut Finansmanı",
    "ihtiyac": "İhtiyaç Finansmanı",
    "kentsel_donusum": "Kentsel Dönüşüm Finansmanı",
    "tasit": "Taşıt Finansmanı",
    "toki": "TOKİ İşlemleri",
    "kampanya": "Kart Kampanyaları",
}


CAMPAIGN_TYPE_MAP = {
    "indirim": "İndirim",
    "taksit": "Taksit",
    "parafpara": "ParafPara",
    "indirim+taksit": "İndirim + Taksit",
    "nakit_iade": "Nakit İade",
    "parafpara+taksit": "ParafPara + Taksit",
    "indirim+ayricalik": "İndirim + Ayrıcalık",
}


# ==================================================================================================
# TURKISH DATE HELPERS
# ==================================================================================================

MONTHS_TR = {
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


MONTH_NAMES = {
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


# ==================================================================================================
# GENERIC HELPERS
# ==================================================================================================

def normalize_space(value):
    if not isinstance(value, str):
        return ""

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def normalize_text(value):
    value = normalize_space(value)

    value = value.replace(
        "TRY",
        "TL",
    )

    # %1.69 -> %1,69
    value = re.sub(
        r"%\s*(\d+)\.(\d+)",
        r"%\1,\2",
        value,
    )

    # "% 3,99" -> "%3,99"
    value = re.sub(
        r"%\s+",
        "%",
        value,
    )

    return value


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


def find_input_file():
    for candidate in INPUT_CANDIDATES:

        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "\nEmlak Katılım input dosyası bulunamadı.\n\n"
        "Beklenen dosyalardan biri:\n"
        "  data/processed/emlak_katilim_all.json\n"
        "  data/processed/emlak_katilim_final.json\n"
        "  data/processed/emlak_katilim_all(1).json\n"
    )


# ==================================================================================================
# DATE PARSING
# ==================================================================================================

def parse_campaign_intervals(text):
    """
    Desteklenen örnekler:

    1-31 Ağustos 2026
    01-31 Ağustos 2026
    01 Ağustos – 31 Ağustos 2026
    18 Ağustos - 18 Eylül 2026
    10 Haziran 2026 saat 00.01 – 31 Ağustos 2026 saat 23.59
    31 Ağustos 2026 tarihine kadar
    31.12.2026 tarihine kadar

    Ayrıca "|" ile ayrılmış birden fazla kampanya penceresini işler.
    """

    if not isinstance(text, str):
        return []

    text = text.strip()

    if not text:
        return []

    normalized = (
        text
        .replace("–", "-")
        .replace("—", "-")
    )

    parts = [
        part.strip()
        for part in normalized.split("|")
        if part.strip()
    ]

    intervals = []

    for part in parts:

        # ------------------------------------------------------------------------------------------
        # 1-31 Ağustos 2026
        # 01-31 Ağustos 2026
        # ------------------------------------------------------------------------------------------

        same_month = re.search(
            r"^\s*"
            r"(\d{1,2})"
            r"\s*-\s*"
            r"(\d{1,2})"
            r"\s+"
            r"([A-Za-zÇĞİÖŞÜçğıöşü]+)"
            r"\s+"
            r"(\d{4})",
            part,
        )

        if same_month:

            start_day = int(
                same_month.group(1)
            )

            end_day = int(
                same_month.group(2)
            )

            month_name = (
                same_month
                .group(3)
                .casefold()
            )

            month = MONTHS_TR.get(
                month_name
            )

            year = int(
                same_month.group(4)
            )

            if month:

                try:
                    start = date(
                        year,
                        month,
                        start_day,
                    )

                    end = date(
                        year,
                        month,
                        end_day,
                    )

                    intervals.append(
                        (
                            start,
                            end,
                        )
                    )

                    continue

                except ValueError:
                    pass

        # ------------------------------------------------------------------------------------------
        # Textual tarihleri bul.
        #
        # 18 Ağustos - 18 Eylül 2026
        # 01 Ağustos - 31 Ağustos 2026
        # 10 Haziran 2026 ... 31 Ağustos 2026
        # ------------------------------------------------------------------------------------------

        textual_matches = list(
            re.finditer(
                r"(?<![.:])\b"
                r"(\d{1,2})"
                r"\s+"
                r"([A-Za-zÇĞİÖŞÜçğıöşü]+)"
                r"(?:\s+(\d{4}))?",
                part,
            )
        )

        parsed_dates = []

        for match in textual_matches:

            day = int(
                match.group(1)
            )

            month_name = (
                match
                .group(2)
                .casefold()
            )

            month = MONTHS_TR.get(
                month_name
            )

            if not month:
                continue

            year = (
                int(match.group(3))
                if match.group(3)
                else None
            )

            parsed_dates.append(
                [
                    day,
                    month,
                    year,
                ]
            )

        # İki tarih varsa range.
        if len(parsed_dates) >= 2:

            end_year = next(
                (
                    item[2]
                    for item in reversed(
                        parsed_dates
                    )
                    if item[2] is not None
                ),
                None,
            )

            if end_year is not None:

                for item in parsed_dates:

                    if item[2] is None:
                        item[2] = end_year

                try:

                    first = parsed_dates[0]
                    last = parsed_dates[-1]

                    start = date(
                        first[2],
                        first[1],
                        first[0],
                    )

                    end = date(
                        last[2],
                        last[1],
                        last[0],
                    )

                    intervals.append(
                        (
                            start,
                            end,
                        )
                    )

                    continue

                except ValueError:
                    pass

        # Tek textual tarih varsa "X tarihine kadar" olarak kabul edilir.
        if (
            len(parsed_dates) == 1
            and parsed_dates[0][2]
            is not None
        ):

            item = parsed_dates[0]

            try:

                end = date(
                    item[2],
                    item[1],
                    item[0],
                )

                intervals.append(
                    (
                        None,
                        end,
                    )
                )

                continue

            except ValueError:
                pass

        # ------------------------------------------------------------------------------------------
        # 31.12.2026
        # ------------------------------------------------------------------------------------------

        dotted = re.search(
            r"\b"
            r"(\d{1,2})"
            r"\."
            r"(\d{1,2})"
            r"\."
            r"(\d{4})"
            r"\b",
            part,
        )

        if dotted:

            try:

                end = date(
                    int(dotted.group(3)),
                    int(dotted.group(2)),
                    int(dotted.group(1)),
                )

                intervals.append(
                    (
                        None,
                        end,
                    )
                )

            except ValueError:
                pass

    return intervals


def campaign_is_active(
    duration_text,
):
    """
    Snapshot gününde aktif değilse False.

    Tarihi parse edemediğimiz veya duration boş olan kayıtları,
    veri kaybetmemek için tutarız.
    """

    intervals = parse_campaign_intervals(
        duration_text
    )

    if not intervals:
        return True

    for start, end in intervals:

        if start is None:

            if SNAPSHOT_DATE <= end:
                return True

        else:

            if (
                start
                <= SNAPSHOT_DATE
                <= end
            ):
                return True

    return False


def format_date_tr(value):
    return (
        f"{value.day} "
        f"{MONTH_NAMES[value.month]} "
        f"{value.year}"
    )


def normalize_campaign_duration(
    duration_text,
):
    if not duration_text:
        return ""

    intervals = parse_campaign_intervals(
        duration_text
    )

    if not intervals:

        return normalize_space(
            duration_text
        )

    normalized_parts = []

    for start, end in intervals:

        if start is None:

            normalized_parts.append(
                format_date_tr(
                    end
                )
            )

        else:

            normalized_parts.append(
                f"{format_date_tr(start)}"
                f" - "
                f"{format_date_tr(end)}"
            )

    return " | ".join(
        normalized_parts
    )


# ==================================================================================================
# PERCENTAGE NORMALIZATION
# ==================================================================================================

def normalize_percentage_token(
    token,
):
    match = re.search(
        r"%\s*"
        r"(\d+)"
        r"(?:[.,](\d+))?",
        token,
    )

    if not match:
        return None

    integer_part = match.group(1)

    decimal_part = match.group(2)

    if decimal_part:

        return (
            f"%{integer_part},"
            f"{decimal_part}"
        )

    return (
        f"%{integer_part}"
    )


def normalize_percentage_list(
    values,
    conditions,
):
    """
    Örnek:

    ["%50"]
        ->
    ["%50"]

    ["0-400.000 TL için %70"]
        ->
    ["%70"]

    Orijinal mapping cümlesi kosullar içine taşınır.
    """

    result = []

    if not isinstance(
        values,
        list,
    ):
        return result

    for value in values:

        if not isinstance(
            value,
            str,
        ):
            continue

        value = normalize_text(
            value
        )

        percentage_matches = list(
            re.finditer(
                r"%\s*"
                r"\d+"
                r"(?:[.,]\d+)?",
                value,
            )
        )

        pure_percentage = bool(
            re.fullmatch(
                r"%\s*"
                r"\d+"
                r"(?:[.,]\d+)?",
                value,
            )
        )

        # Açıklamalı mapping'i kaybetme.
        if (
            percentage_matches
            and not pure_percentage
        ):

            conditions.append(
                value
            )

        for match in percentage_matches:

            normalized = (
                normalize_percentage_token(
                    match.group(0)
                )
            )

            if normalized:

                result.append(
                    normalized
                )

    return unique_list(
        result
    )


# ==================================================================================================
# MONEY NORMALIZATION
# ==================================================================================================

def normalize_money_number(
    value,
):
    value = (
        value
        .strip()
        .replace(" ", "")
    )

    # 30.000,00 -> 30.000
    if value.endswith(
        ",00"
    ):

        value = value[:-3]

    return value


def normalize_amount_list(
    values,
    conditions,
):
    """
    Örnek:

    "Güçlendirme Kredisi: 320.000 TL üst limit"
        ->
    main field: "320.000 TL"
    kosullar: orijinal açıklama
    """

    result = []

    if not isinstance(
        values,
        list,
    ):
        return result

    for value in values:

        if not isinstance(
            value,
            str,
        ):
            continue

        value = normalize_text(
            value
        )

        matches = list(
            re.finditer(
                r"(?<!\d)"
                r"(\d[\d.]*?(?:,\d{1,2})?)"
                r"\s*"
                r"(TL|₺)"
                r"\b",
                value,
            )
        )

        pure_money = bool(
            re.fullmatch(
                r"\d[\d.]*?"
                r"(?:,\d{1,2})?"
                r"\s*"
                r"(?:TL|₺)",
                value,
            )
        )

        if (
            matches
            and not pure_money
        ):

            conditions.append(
                value
            )

        for match in matches:

            number = (
                normalize_money_number(
                    match.group(1)
                )
            )

            result.append(
                f"{number} TL"
            )

    return unique_list(
        result
    )


# ==================================================================================================
# VADE NORMALIZATION
# ==================================================================================================

def normalize_vade_list(
    values,
    conditions,
):
    """
    Örnek:

    "Memlekette Konut Finansmanı - TL: 120 ay"
        ->
    vade: "120 ay"
    mapping kosullar içinde kalır.

    "2.500.000 ve üzeri: 0 ay"
        ->
    0 ay ana vade listesine ALINMAZ.
    """

    result = []

    if not isinstance(
        values,
        list,
    ):
        return result

    for value in values:

        if not isinstance(
            value,
            str,
        ):
            continue

        value = normalize_text(
            value
        )

        matches = re.findall(
            r"\b"
            r"(\d+)"
            r"\s*"
            r"(ay|yıl|yil|gün|gun)"
            r"\b",
            value,
            flags=re.IGNORECASE,
        )

        pure_duration = bool(
            re.fullmatch(
                r"\d+"
                r"\s*"
                r"(?:ay|yıl|yil|gün|gun)",
                value,
                flags=re.IGNORECASE,
            )
        )

        if (
            matches
            and not pure_duration
        ):

            conditions.append(
                value
            )

        for number, unit in matches:

            number_int = int(
                number
            )

            # 0 ay karşılaştırılabilir gerçek vade değildir.
            if number_int == 0:
                continue

            unit = unit.casefold()

            if unit == "yil":
                unit = "yıl"

            if unit == "gun":
                unit = "gün"

            result.append(
                f"{number_int} {unit}"
            )

    return unique_list(
        result
    )


# ==================================================================================================
# INSTALLMENT NORMALIZATION
# ==================================================================================================

def normalize_installments(
    values,
):
    """
    "12 taksit" -> "12"
    "6 taksit"  -> "6"
    """

    result = []

    if not isinstance(
        values,
        list,
    ):
        return result

    for value in values:

        if not isinstance(
            value,
            str,
        ):
            continue

        value = normalize_text(
            value
        )

        if re.fullmatch(
            r"\d+",
            value,
        ):

            result.append(
                str(
                    int(value)
                )
            )

            continue

        matches = re.findall(
            r"\b"
            r"(\d+)"
            r"\s*"
            r"(?:taksit|taksite|taksitli)"
            r"\b",
            value,
            flags=re.IGNORECASE,
        )

        for number in matches:

            result.append(
                str(
                    int(number)
                )
            )

    return unique_list(
        result
    )


# ==================================================================================================
# SPECIAL SEMANTIC PATCHES
# ==================================================================================================

def patch_example_finance_values(
    record,
    conditions,
):
    """
    İhtiyaç Finansmanı sayfasındaki:

      30.000 TL
      12 ay
      %1,69
      tahsis ücreti
      taksit değerleri

    "Örnek İhtiyaç Finansmanı Tablosu"ndan geldiği için
    ürünün ana structured finance alanlarına yazılmamalıdır.
    """

    if (
        record.get(
            "kayit_turu"
        )
        != "finansman"
    ):
        return

    if (
        record.get(
            "urun_adi"
        )
        != "İhtiyaç Finansmanı"
    ):
        return

    fields = [
        "kar_payi_orani",
        "finansman_tutari",
        "vade",
        "taksit_sayisi",
        "masraf_bilgisi",
    ]

    for field in fields:

        values = record.get(
            field,
            [],
        )

        if not isinstance(
            values,
            list,
        ):
            continue

        for value in values:

            if not isinstance(
                value,
                str,
            ):
                continue

            conditions.append(
                "Örnek tablo verisi: "
                + normalize_text(
                    value
                )
            )

    record["kar_payi_orani"] = []
    record["finansman_tutari"] = []
    record["vade"] = []
    record["taksit_sayisi"] = []
    record["masraf_bilgisi"] = []


def clean_finance_campaign_leakage(
    record,
    conditions,
):
    """
    Finansman kayıtlarındaki:

      Kentsel Dönüşüm devlet desteği
      Çevreci Konut indirimi
      Çevreci Araç indirimi

    kampanya_avantaji alanına ait değildir.

    Bunları kosullar'a taşırız.
    """

    if (
        record.get(
            "kayit_turu"
        )
        != "finansman"
    ):
        return 0

    moved = 0

    advantages = record.get(
        "kampanya_avantaji",
        [],
    )

    if isinstance(
        advantages,
        list,
    ):

        for value in advantages:

            if not isinstance(
                value,
                str,
            ):
                continue

            value = normalize_text(
                value
            )

            if value:

                conditions.append(
                    value
                )

                moved += 1

    record["kampanya_avantaji"] = []
    record["kampanya_turu"] = ""
    record["kampanya_suresi"] = ""

    return moved


# ==================================================================================================
# RECORD PATCH
# ==================================================================================================

def patch_record(
    original_record,
):
    record = dict(
        original_record
    )

    conditions = unique_list(
        record.get(
            "kosullar",
            [],
        )
    )

    moved_finance_advantages = (
        clean_finance_campaign_leakage(
            record,
            conditions,
        )
    )

    patch_example_finance_values(
        record,
        conditions,
    )

    # ----------------------------------------------------------------------------------------------
    # BANK NAME
    # ----------------------------------------------------------------------------------------------

    record["banka"] = BANK_NAME

    # ----------------------------------------------------------------------------------------------
    # CATEGORY
    # ----------------------------------------------------------------------------------------------

    category = normalize_space(
        record.get(
            "urun_kategorisi",
            "",
        )
    )

    record[
        "urun_kategorisi"
    ] = CATEGORY_MAP.get(
        category,
        category,
    )

    # Emekli kaydı klasik kart kampanyası değil.
    if (
        record.get(
            "urun_adi"
        )
        == "Emekli Müşterilerimize Özel Ayrıcalıklar"
    ):

        record[
            "urun_kategorisi"
        ] = "Diğer Kampanya"

    # ----------------------------------------------------------------------------------------------
    # CAMPAIGN TYPE
    # ----------------------------------------------------------------------------------------------

    campaign_type = normalize_space(
        record.get(
            "kampanya_turu",
            "",
        )
    )

    record[
        "kampanya_turu"
    ] = CAMPAIGN_TYPE_MAP.get(
        campaign_type,
        campaign_type,
    )

    # ----------------------------------------------------------------------------------------------
    # STRUCTURED FINANCE FIELDS
    # ----------------------------------------------------------------------------------------------

    record[
        "kar_payi_orani"
    ] = normalize_percentage_list(
        record.get(
            "kar_payi_orani",
            [],
        ),
        conditions,
    )

    record[
        "finansman_orani"
    ] = normalize_percentage_list(
        record.get(
            "finansman_orani",
            [],
        ),
        conditions,
    )

    record[
        "finansman_tutari"
    ] = normalize_amount_list(
        record.get(
            "finansman_tutari",
            [],
        ),
        conditions,
    )

    record[
        "vade"
    ] = normalize_vade_list(
        record.get(
            "vade",
            [],
        ),
        conditions,
    )

    record[
        "taksit_sayisi"
    ] = normalize_installments(
        record.get(
            "taksit_sayisi",
            [],
        )
    )

    # ----------------------------------------------------------------------------------------------
    # OTHER LIST FIELDS
    # ----------------------------------------------------------------------------------------------

    record[
        "masraf_bilgisi"
    ] = unique_list(
        [
            normalize_text(
                item
            )
            for item in record.get(
                "masraf_bilgisi",
                [],
            )
            if isinstance(
                item,
                str,
            )
        ]
    )

    record[
        "kampanya_avantaji"
    ] = unique_list(
        [
            normalize_text(
                item
            )
            for item in record.get(
                "kampanya_avantaji",
                [],
            )
            if isinstance(
                item,
                str,
            )
        ]
    )

    record[
        "hedef_kitle"
    ] = unique_list(
        [
            normalize_text(
                item
            )
            for item in record.get(
                "hedef_kitle",
                [],
            )
            if isinstance(
                item,
                str,
            )
        ]
    )

    # ----------------------------------------------------------------------------------------------
    # CURRENCY
    # ----------------------------------------------------------------------------------------------

    currencies = []

    for currency in record.get(
        "para_birimi",
        [],
    ):

        if not isinstance(
            currency,
            str,
        ):
            continue

        currency = normalize_space(
            currency
        )

        if currency == "TRY":
            currency = "TL"

        if currency:
            currencies.append(
                currency
            )

    record[
        "para_birimi"
    ] = unique_list(
        currencies
    )

    # ----------------------------------------------------------------------------------------------
    # CONDITIONS
    # ----------------------------------------------------------------------------------------------

    record[
        "kosullar"
    ] = unique_list(
        [
            normalize_text(
                item
            )
            for item in conditions
            if isinstance(
                item,
                str,
            )
        ]
    )

    # ----------------------------------------------------------------------------------------------
    # CAMPAIGN DURATION
    # ----------------------------------------------------------------------------------------------

    if (
        record.get(
            "kayit_turu"
        )
        == "kampanya"
    ):

        record[
            "kampanya_suresi"
        ] = normalize_campaign_duration(
            record.get(
                "kampanya_suresi",
                "",
            )
        )

    # ----------------------------------------------------------------------------------------------
    # STRING FIELDS
    # ----------------------------------------------------------------------------------------------

    for field in STRING_FIELDS:

        value = record.get(
            field,
            "",
        )

        if value is None:
            value = ""

        if not isinstance(
            value,
            str,
        ):
            value = str(
                value
            )

        if field == "ham_metin":

            # Provenance: raw text değiştirilmez.
            value = value.strip()

        else:

            value = normalize_space(
                value
            )

        record[field] = value

    # ----------------------------------------------------------------------------------------------
    # LIST FIELD TYPES
    # ----------------------------------------------------------------------------------------------

    for field in LIST_FIELDS:

        if not isinstance(
            record.get(field),
            list,
        ):

            record[field] = []

    # ----------------------------------------------------------------------------------------------
    # EXACT 18-KEY OUTPUT ORDER
    # ----------------------------------------------------------------------------------------------

    canonical = {}

    for key in FINAL_KEYS:

        if key in LIST_FIELDS:

            canonical[key] = record.get(
                key,
                [],
            )

        else:

            canonical[key] = record.get(
                key,
                "",
            )

    return (
        canonical,
        moved_finance_advantages,
    )


# ==================================================================================================
# VALIDATION
# ==================================================================================================

def validate_records(
    records,
):
    errors = []

    urls = []

    for index, record in enumerate(
        records,
        start=1,
    ):

        name = record.get(
            "urun_adi",
            "",
        )

        prefix = (
            f"[{index:03d}] {name}"
        )

        # Exact schema/order
        if list(
            record.keys()
        ) != FINAL_KEYS:

            errors.append(
                f"{prefix} -> "
                "18-key schema/order yanlış"
            )

        # Bank name
        if record.get(
            "banka"
        ) != BANK_NAME:

            errors.append(
                f"{prefix} -> "
                "banka adı yanlış"
            )

        # Record type
        if record.get(
            "kayit_turu"
        ) not in {
            "finansman",
            "kampanya",
        }:

            errors.append(
                f"{prefix} -> "
                "kayit_turu yanlış"
            )

        # List fields
        for field in LIST_FIELDS:

            if not isinstance(
                record.get(field),
                list,
            ):

                errors.append(
                    f"{prefix} -> "
                    f"{field} list değil"
                )

        # String fields
        for field in STRING_FIELDS:

            if not isinstance(
                record.get(field),
                str,
            ):

                errors.append(
                    f"{prefix} -> "
                    f"{field} string değil"
                )

        # Currency standard
        if "TRY" in record.get(
            "para_birimi",
            [],
        ):

            errors.append(
                f"{prefix} -> "
                "TRY bulundu"
            )

        # Taksit must be numeric strings.
        for installment in record.get(
            "taksit_sayisi",
            [],
        ):

            if not re.fullmatch(
                r"\d+",
                installment,
            ):

                errors.append(
                    f"{prefix} -> "
                    f"geçersiz taksit: "
                    f"{installment}"
                )

        # Percent format
        for field in [
            "kar_payi_orani",
            "finansman_orani",
        ]:

            for percentage in record.get(
                field,
                [],
            ):

                if not re.fullmatch(
                    r"%\d+(?:,\d+)?",
                    percentage,
                ):

                    errors.append(
                        f"{prefix} -> "
                        f"{field} format hatası: "
                        f"{percentage}"
                    )

        # Finance records must not contain campaign fields.
        if (
            record.get(
                "kayit_turu"
            )
            == "finansman"
        ):

            if record.get(
                "kampanya_turu"
            ):

                errors.append(
                    f"{prefix} -> "
                    "finance kampanya_turu dolu"
                )

            if record.get(
                "kampanya_avantaji"
            ):

                errors.append(
                    f"{prefix} -> "
                    "finance kampanya_avantaji dolu"
                )

            if record.get(
                "kampanya_suresi"
            ):

                errors.append(
                    f"{prefix} -> "
                    "finance kampanya_suresi dolu"
                )

        url = record.get(
            "kaynak_url",
            "",
        )

        if url:
            urls.append(
                url
            )

    # Duplicate URLs
    duplicate_urls = [
        url
        for url, count in Counter(
            urls
        ).items()
        if count > 1
    ]

    for url in duplicate_urls:

        errors.append(
            f"Duplicate URL: {url}"
        )

    finance_count = sum(
        1
        for record in records
        if record.get(
            "kayit_turu"
        )
        == "finansman"
    )

    campaign_count = sum(
        1
        for record in records
        if record.get(
            "kayit_turu"
        )
        == "kampanya"
    )

    # İlk dosya:
    # 12 finance + 67 campaign = 79
    #
    # 23.08.2026 snapshot:
    # 4 aktif olmayan campaign çıkarılır.
    #
    # Final:
    # 12 finance + 63 campaign = 75
    if finance_count != 12:

        errors.append(
            f"Finansman sayısı 12 bekleniyordu, "
            f"{finance_count} bulundu."
        )

    if campaign_count != 63:

        errors.append(
            f"Kampanya sayısı 63 bekleniyordu, "
            f"{campaign_count} bulundu."
        )

    if len(records) != 75:

        errors.append(
            f"Toplam kayıt 75 bekleniyordu, "
            f"{len(records)} bulundu."
        )

    return errors


# ==================================================================================================
# AUDIT
# ==================================================================================================

def print_audit(
    input_count,
    records,
    skipped,
    moved_finance_advantages,
):
    finance = [
        record
        for record in records
        if record[
            "kayit_turu"
        ]
        == "finansman"
    ]

    campaigns = [
        record
        for record in records
        if record[
            "kayit_turu"
        ]
        == "kampanya"
    ]

    exact_schema = sum(
        1
        for record in records
        if list(
            record.keys()
        )
        == FINAL_KEYS
    )

    duplicate_urls = [
        url
        for url, count in Counter(
            record[
                "kaynak_url"
            ]
            for record in records
            if record[
                "kaynak_url"
            ]
        ).items()
        if count > 1
    ]

    try_count = sum(
        1
        for record in records
        if "TRY"
        in record.get(
            "para_birimi",
            [],
        )
    )

    bad_installments = []

    bad_percentages = []

    for record in records:

        for installment in record.get(
            "taksit_sayisi",
            [],
        ):

            if not installment.isdigit():

                bad_installments.append(
                    (
                        record[
                            "urun_adi"
                        ],
                        installment,
                    )
                )

        for field in [
            "kar_payi_orani",
            "finansman_orani",
        ]:

            for percentage in record.get(
                field,
                [],
            ):

                if not re.fullmatch(
                    r"%\d+(?:,\d+)?",
                    percentage,
                ):

                    bad_percentages.append(
                        (
                            record[
                                "urun_adi"
                            ],
                            field,
                            percentage,
                        )
                    )

    print()
    print("=" * 120)
    print("EMLAK KATILIM - FINAL PATCH AUDIT")
    print("=" * 120)

    print(
        f"Input kayıt          : "
        f"{input_count}"
    )

    print(
        f"Final kayıt          : "
        f"{len(records)}"
    )

    print(
        f"Finansman            : "
        f"{len(finance)}"
    )

    print(
        f"Kampanya             : "
        f"{len(campaigns)}"
    )

    print(
        f"Çıkarılan kampanya   : "
        f"{len(skipped)}"
    )

    print(
        f"Exact 18-key schema  : "
        f"{exact_schema}/{len(records)}"
    )

    print(
        f"Duplicate URL        : "
        f"{len(duplicate_urls)}"
    )

    print(
        f"TRY kalan kayıt      : "
        f"{try_count}"
    )

    print(
        f"Bozuk taksit         : "
        f"{len(bad_installments)}"
    )

    print(
        f"Bozuk yüzde          : "
        f"{len(bad_percentages)}"
    )

    print(
        f"Finance leakage move : "
        f"{moved_finance_advantages}"
    )

    print()
    print("SNAPSHOT DIŞI ÇIKARILAN KAMPANYALAR")
    print("-" * 120)

    if skipped:

        for name, duration in skipped:

            print(
                f"❌ {name}"
            )

            print(
                f"   Süre: {duration}"
            )

    else:

        print(
            "Çıkarılan kampanya yok."
        )

    print()
    print("KRİTİK FİNANSMAN KONTROLLERİ")
    print("-" * 120)

    important_products = [
        "İhtiyaç Finansmanı",
        "Kentsel Dönüşüm Finansmanı",
        "Konut Finansmanı",
        "Taşıt Finansmanı",
    ]

    by_name = {
        record[
            "urun_adi"
        ]: record
        for record in records
    }

    for product_name in important_products:

        record = by_name.get(
            product_name
        )

        if not record:
            continue

        print(
            f"✅ {product_name}"
        )

        print(
            f"   Kâr Payı : "
            f"{record['kar_payi_orani']}"
        )

        print(
            f"   Fin.Oranı: "
            f"{record['finansman_orani']}"
        )

        print(
            f"   Tutar    : "
            f"{record['finansman_tutari']}"
        )

        print(
            f"   Vade     : "
            f"{record['vade']}"
        )

        print(
            f"   Taksit   : "
            f"{record['taksit_sayisi']}"
        )

        print(
            f"   Currency : "
            f"{record['para_birimi']}"
        )

    print("=" * 120)


# ==================================================================================================
# MAIN
# ==================================================================================================

def main():

    print()
    print("=" * 120)
    print("EMLAK KATILIM - FINAL NORMALIZATION PATCH")
    print("=" * 120)

    input_file = find_input_file()

    print(
        f"Input : {input_file}"
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print(
        "Snapshot tarihi: "
        "23.08.2026"
    )

    print()

    with open(
        input_file,
        "r",
        encoding="utf-8",
    ) as file:

        raw_data = json.load(
            file
        )

    # ----------------------------------------------------------------------------------------------
    # OLD WRAPPER / NEW LIST SUPPORT
    # ----------------------------------------------------------------------------------------------

    if isinstance(
        raw_data,
        dict,
    ):

        records = raw_data.get(
            "kayitlar"
        )

        if not isinstance(
            records,
            list,
        ):

            raise ValueError(
                "Eski wrapper bulundu ancak "
                "'kayitlar' listesi yok."
            )

        print(
            "Eski wrapper formatı bulundu ✅"
        )

    elif isinstance(
        raw_data,
        list,
    ):

        records = raw_data

        print(
            "Root zaten list formatında."
        )

    else:

        raise ValueError(
            "JSON root dict veya list olmalı."
        )

    input_count = len(
        records
    )

    print(
        f"Input kayıt sayısı: "
        f"{input_count}"
    )

    print()

    # ----------------------------------------------------------------------------------------------
    # PATCH
    # ----------------------------------------------------------------------------------------------

    final_records = []

    skipped = []

    moved_finance_advantages = 0

    for index, original_record in enumerate(
        records,
        start=1,
    ):

        name = normalize_space(
            original_record.get(
                "urun_adi",
                "",
            )
        )

        record_type = original_record.get(
            "kayit_turu",
            "",
        )

        duration = original_record.get(
            "kampanya_suresi",
            "",
        )

        if (
            record_type
            == "kampanya"
            and not campaign_is_active(
                duration
            )
        ):

            print(
                f"[{index:02d}/{input_count}] "
                f"SKIP ❌ {name}"
            )

            skipped.append(
                (
                    name,
                    duration,
                )
            )

            continue

        patched, moved_count = (
            patch_record(
                original_record
            )
        )

        moved_finance_advantages += (
            moved_count
        )

        final_records.append(
            patched
        )

        print(
            f"[{index:02d}/{input_count}] "
            f"OK ✅ {name}"
        )

    # ----------------------------------------------------------------------------------------------
    # AUDIT
    # ----------------------------------------------------------------------------------------------

    print_audit(
        input_count,
        final_records,
        skipped,
        moved_finance_advantages,
    )

    # ----------------------------------------------------------------------------------------------
    # VALIDATE BEFORE WRITE
    # ----------------------------------------------------------------------------------------------

    errors = validate_records(
        final_records
    )

    if errors:

        print()
        print("=" * 120)
        print("VALIDATION ERRORS")
        print("=" * 120)

        for error in errors:

            print(
                f"❌ {error}"
            )

        print()
        print(
            "EMLAK KATILIM FINAL PATCH "
            "BAŞARISIZ ❌"
        )

        print(
            "Final dosya yazılmadı."
        )

        raise SystemExit(1)

    # ----------------------------------------------------------------------------------------------
    # BACKUP
    # ----------------------------------------------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if (
        input_file.resolve()
        == OUTPUT_FILE.resolve()
        and not BACKUP_FILE.exists()
    ):

        shutil.copy2(
            input_file,
            BACKUP_FILE,
        )

        print()
        print(
            f"Backup oluşturuldu: "
            f"{BACKUP_FILE}"
        )

    # ----------------------------------------------------------------------------------------------
    # WRITE
    # ----------------------------------------------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            final_records,
            file,
            ensure_ascii=False,
            indent=2,
        )

    # ----------------------------------------------------------------------------------------------
    # FINAL RE-READ CHECK
    # ----------------------------------------------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        saved_records = json.load(
            file
        )

    final_errors = validate_records(
        saved_records
    )

    if final_errors:

        print()
        print(
            "Dosya yazıldı fakat "
            "re-read validation başarısız ❌"
        )

        for error in final_errors:

            print(
                f"❌ {error}"
            )

        raise SystemExit(1)

    print()
    print("=" * 120)
    print(
        "EMLAK KATILIM FINAL PATCH BAŞARILI ✅"
    )
    print("=" * 120)

    print(
        f"JSON: {OUTPUT_FILE}"
    )

    print()

    print(
        "Wrapper kaldırıldı ✅"
    )

    print(
        "Banka adı standardize edildi ✅"
    )

    print(
        "TRY -> TL normalize edildi ✅"
    )

    print(
        "Taksit sayıları numeric string yapıldı ✅"
    )

    print(
        "Finansman oranları normalize edildi ✅"
    )

    print(
        "Tutar ve vade mappingleri normalize edildi ✅"
    )

    print(
        "Örnek maliyet tablosu ana alanlardan temizlendi ✅"
    )

    print(
        "Finance -> campaign leakage temizlendi ✅"
    )

    print(
        "Snapshot dışı kampanyalar çıkarıldı ✅"
    )

    print(
        "Exact 18-key schema korundu ✅"
    )

    print(
        "Duplicate URL kontrolü geçti ✅"
    )

    print("=" * 120)


if __name__ == "__main__":
    main()