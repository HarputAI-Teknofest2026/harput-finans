import json
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path


# ==================================================================================================
# TÜRKİYE FİNANS - FINAL NORMALIZATION PATCH
# ==================================================================================================


BANK_NAME = "Türkiye Finans Katılım Bankası A.Ş."
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

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)


INPUT_CANDIDATES = [
    PROCESSED_DIR / "turkiye_finans_all.json",
    PROCESSED_DIR / "turkiye_finans_final.json",
    PROCESSED_DIR / "turkiye_finans_all(1).json",
]


OUTPUT_FILE = (
    PROCESSED_DIR
    / "turkiye_finans_all.json"
)


BACKUP_FILE = (
    PROCESSED_DIR
    / "turkiye_finans_all_before_normalization.json"
)


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
# BASIC HELPERS
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


def find_input_file():
    for candidate in INPUT_CANDIDATES:

        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "\nTürkiye Finans input dosyası bulunamadı.\n\n"
        "Beklenenlerden biri:\n"
        "  data/processed/turkiye_finans_all.json\n"
        "  data/processed/turkiye_finans_final.json\n"
        "  data/processed/turkiye_finans_all(1).json\n"
    )


# ==================================================================================================
# PERCENT NORMALIZATION
# ==================================================================================================


def normalize_percentage_token(value):
    value = value.strip()

    match = re.fullmatch(
        r"%\s*(\d+)(?:[.,](\d+))?",
        value,
    )

    if not match:
        return None

    integer_part = str(
        int(match.group(1))
    )

    decimal_part = match.group(2)

    if decimal_part is None:
        return f"%{integer_part}"

    # %22,50 -> %22,5
    # %10,00 -> %10
    decimal_part = (
        decimal_part
        .rstrip("0")
    )

    if not decimal_part:
        return f"%{integer_part}"

    return (
        f"%{integer_part},"
        f"{decimal_part}"
    )


def normalize_percent_text(value):
    value = normalize_space(value)

    # 70% -> %70
    # 2,95% -> %2,95
    value = re.sub(
        r"(?<!%)\b"
        r"(\d+(?:[.,]\d+)?)"
        r"\s*%",
        lambda match:
            "%"
            + match.group(1).replace(
                ".",
                ",",
            ),
        value,
    )

    # %4.20 -> %4,20
    value = re.sub(
        r"%\s*(\d+)\.(\d+)",
        r"%\1,\2",
        value,
    )

    value = re.sub(
        r"%\s+",
        "%",
        value,
    )

    return value


def normalize_percentage_list(
    values,
    conditions,
    remove_example_tables=False,
):
    result = []

    if not isinstance(values, list):
        return result

    for value in values:

        if not isinstance(value, str):
            continue

        value = normalize_percent_text(
            value
        )

        lower = value.casefold()

        # Açıkça örnek ödeme / maliyet tablosu.
        # Main structured rate alanına alınmaz.
        if (
            remove_example_tables
            and "örnek" in lower
        ):

            conditions.append(
                "Örnek maliyet tablosu: "
                + value
            )

            continue

        matches = re.findall(
            r"%\d+(?:[.,]\d+)?",
            value,
        )

        # Mapping kaybolmasın.
        if (
            matches
            and not re.fullmatch(
                r"%\d+(?:[.,]\d+)?",
                value,
            )
        ):

            conditions.append(
                value
            )

        for match in matches:

            normalized = (
                normalize_percentage_token(
                    match
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


def normalize_money_number(value):
    value = (
        value
        .strip()
        .replace(" ", "")
    )

    if value.endswith(",00"):
        value = value[:-3]

    return value


def normalize_money_text(value):
    value = normalize_space(value)

    # 120 bin TL -> 120.000 TL
    def replace_thousand(match):
        number = int(
            match.group(1)
        )

        number = (
            f"{number * 1000:,}"
            .replace(
                ",",
                ".",
            )
        )

        return (
            f"{number} TL"
        )

    value = re.sub(
        r"\b(\d+)\s*bin\s*TL\b",
        replace_thousand,
        value,
        flags=re.IGNORECASE,
    )

    value = value.replace(
        "TRY",
        "TL",
    )

    return value


def normalize_amount_list(
    values,
    conditions,
):
    result = []

    if not isinstance(values, list):
        return result

    for value in values:

        if not isinstance(value, str):
            continue

        value = normalize_money_text(
            value
        )

        matches = list(
            re.finditer(
                r"(?<!\d)"
                r"(\d[\d.]*(?:,\d{1,2})?)"
                r"\s*(?:TL|₺)"
                r"\b",
                value,
            )
        )

        pure_money = bool(
            re.fullmatch(
                r"\d[\d.]*(?:,\d{1,2})?"
                r"\s*(?:TL|₺)",
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

            number = normalize_money_number(
                match.group(1)
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
    result = []

    if not isinstance(values, list):
        return result

    for value in values:

        if not isinstance(value, str):
            continue

        value = normalize_space(
            value
        )

        if not value:
            continue

        matches = re.findall(
            r"(?<!\d)"
            r"(\d+)"
            r"\s*"
            r"(aya|ay|yıla|yıl|yila|yil|güne|gün|gune|gun)"
            r"\b",
            value,
            flags=re.IGNORECASE,
        )

        pure_duration = bool(
            re.fullmatch(
                r"\d+\s*"
                r"(?:aya|ay|yıla|yıl|yila|yil|güne|gün|gune|gun)",
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

            number = int(number)

            if number <= 0:
                continue

            unit = unit.casefold()

            if unit in {
                "aya",
                "ay",
            }:
                unit = "ay"

            elif unit in {
                "yıla",
                "yıl",
                "yila",
                "yil",
            }:
                unit = "yıl"

            else:
                unit = "gün"

            result.append(
                f"{number} {unit}"
            )

    return unique_list(
        result
    )


# ==================================================================================================
# TAKSİT NORMALIZATION
# ==================================================================================================


def normalize_installments(
    values,
    conditions,
):
    result = []

    if not isinstance(values, list):
        return result

    for value in values:

        if not isinstance(value, str):
            continue

        value = normalize_space(
            value
        )

        if not value:
            continue

        if re.fullmatch(
            r"\d+",
            value,
        ):

            result.append(
                str(int(value))
            )

            continue

        # Structured açıklama kaybolmasın.
        conditions.append(
            value
        )

        # 3-12 taksit
        ranges = re.findall(
            r"(\d+)"
            r"\s*[-–]\s*"
            r"(\d+)"
            r"\s*taksit",
            value,
            flags=re.IGNORECASE,
        )

        for start, end in ranges:

            start = int(start)
            end = int(end)

            if (
                0 < start <= end
                and end - start <= 20
            ):

                for number in range(
                    start,
                    end + 1,
                ):

                    result.append(
                        str(number)
                    )

        # "12 taksit"
        singles = re.findall(
            r"(?<!\d)"
            r"(\d+)"
            r"\s*taksit(?:e|li)?"
            r"\b",
            value,
            flags=re.IGNORECASE,
        )

        for number in singles:

            result.append(
                str(int(number))
            )

        # "36 aya kadar taksitlendir"
        until = re.findall(
            r"(?<!\d)"
            r"(\d+)"
            r"\s*aya?\s+kadar"
            r"[^,.]{0,30}"
            r"taksit",
            value,
            flags=re.IGNORECASE,
        )

        for number in until:

            result.append(
                str(int(number))
            )

        # "12 aya varan taksit"
        up_to = re.findall(
            r"(?<!\d)"
            r"(\d+)"
            r"\s*aya?\s+varan"
            r"[^,.]{0,30}"
            r"taksit",
            value,
            flags=re.IGNORECASE,
        )

        for number in up_to:

            result.append(
                str(int(number))
            )

    return unique_list(
        result
    )


# ==================================================================================================
# MASRAF NORMALIZATION
# ==================================================================================================


def normalize_fee_list(values):
    result = []

    if not isinstance(values, list):
        return result

    for value in values:

        if not isinstance(value, str):
            continue

        value = normalize_percent_text(
            value
        )

        value = value.replace(
            "TRY",
            "TL",
        )

        value = normalize_space(
            value
        )

        if not value:
            continue

        # Tahsis ücreti tablo satırlarını sadeleştir.
        match = re.search(
            r"Tahsis Ücreti:\s*"
            r"(%\d+(?:[.,]\d+)?)",
            value,
            flags=re.IGNORECASE,
        )

        if match:

            percentage = (
                normalize_percentage_token(
                    match.group(1)
                )
            )

            if percentage:

                result.append(
                    f"Tahsis ücreti: {percentage}"
                )

            continue

        result.append(
            value
        )

    return unique_list(
        result
    )


# ==================================================================================================
# CAMPAIGN DATE NORMALIZATION
# ==================================================================================================


def format_date_tr(value):
    return (
        f"{value.day} "
        f"{MONTH_NAMES[value.month]} "
        f"{value.year}"
    )


def parse_campaign_period(value):
    value = normalize_space(
        value
    )

    if not value:
        return None

    # 2026-08-01 - 2026-08-31
    match = re.fullmatch(
        r"(\d{4})-(\d{2})-(\d{2})"
        r"\s*-\s*"
        r"(\d{4})-(\d{2})-(\d{2})",
        value,
    )

    if match:

        try:

            start = date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )

            end = date(
                int(match.group(4)),
                int(match.group(5)),
                int(match.group(6)),
            )

            return (
                start,
                end,
            )

        except ValueError:
            return None

    # 2026-12-31 tarihine kadar
    match = re.fullmatch(
        r"(\d{4})-(\d{2})-(\d{2})"
        r"\s+tarihine kadar",
        value,
        flags=re.IGNORECASE,
    )

    if match:

        try:

            end = date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )

            return (
                None,
                end,
            )

        except ValueError:
            return None

    return None


def normalize_campaign_period(value):
    parsed = parse_campaign_period(
        value
    )

    if not parsed:
        return normalize_space(
            value
        )

    start, end = parsed

    if start is None:

        return format_date_tr(
            end
        )

    return (
        f"{format_date_tr(start)}"
        f" - "
        f"{format_date_tr(end)}"
    )


def campaign_is_active(value):
    parsed = parse_campaign_period(
        value
    )

    # Boş veya parse edilemeyen süreyi
    # veri kaybı olmasın diye otomatik silmeyiz.
    if not parsed:
        return True

    start, end = parsed

    if start is None:

        return (
            SNAPSHOT_DATE
            <= end
        )

    return (
        start
        <= SNAPSHOT_DATE
        <= end
    )


# ==================================================================================================
# CONDITIONS
# ==================================================================================================


UI_NOISE = {
    "başvuru merkezi",
    "hesaplama araçları",
    "müşteri memnuniyet merkezi",
    "yatırımcı ilişkileri",
    "finans portalı",
    "satılık gayrimenkuller",
    "türkiye finans linkleri",
    "türkiye finans blog",
    "sıkça ziyaret edilen sayfalar",
    "sıkça sorulan sorular",
    "müşteri ol",
    "son gezdiklerim",
}


def clean_conditions(
    values,
    product_name,
):
    result = []

    for value in values:

        if not isinstance(value, str):
            continue

        value = normalize_percent_text(
            value
        )

        value = value.replace(
            "TRY",
            "TL",
        )

        value = normalize_space(
            value
        )

        if not value:
            continue

        lower = value.casefold()

        if lower in UI_NOISE:
            continue

        if (
            lower
            == product_name.casefold()
        ):
            continue

        result.append(
            value
        )

    return unique_list(
        result
    )


# ==================================================================================================
# RECORD PATCH
# ==================================================================================================


def patch_record(original_record):
    record = dict(
        original_record
    )

    name = normalize_space(
        record.get(
            "urun_adi",
            "",
        )
    )

    conditions = unique_list(
        record.get(
            "kosullar",
            [],
        )
    )

    record[
        "banka"
    ] = BANK_NAME

    # ----------------------------------------------------------------------------------------------
    # FINANCE -> CAMPAIGN LEAKAGE
    # ----------------------------------------------------------------------------------------------

    if (
        record.get(
            "kayit_turu"
        )
        == "finansman"
    ):

        for value in record.get(
            "kampanya_avantaji",
            [],
        ):

            if not isinstance(
                value,
                str,
            ):
                continue

            value = normalize_space(
                value
            )

            if value:

                conditions.append(
                    value
                )

        record[
            "kampanya_turu"
        ] = ""

        record[
            "kampanya_avantaji"
        ] = []

        record[
            "kampanya_suresi"
        ] = ""

    else:

        record[
            "kampanya_turu"
        ] = normalize_space(
            record.get(
                "kampanya_turu",
                "",
            )
        )

        record[
            "kampanya_avantaji"
        ] = unique_list(
            [
                normalize_percent_text(
                    value
                )
                for value in record.get(
                    "kampanya_avantaji",
                    [],
                )
                if isinstance(
                    value,
                    str,
                )
            ]
        )

        record[
            "kampanya_suresi"
        ] = normalize_campaign_period(
            record.get(
                "kampanya_suresi",
                "",
            )
        )

    # ----------------------------------------------------------------------------------------------
    # KAR PAYI
    # ----------------------------------------------------------------------------------------------

    record[
        "kar_payi_orani"
    ] = normalize_percentage_list(
        record.get(
            "kar_payi_orani",
            [],
        ),
        conditions,
        remove_example_tables=True,
    )

    # ----------------------------------------------------------------------------------------------
    # FINANSMAN ORANI
    # ----------------------------------------------------------------------------------------------

    record[
        "finansman_orani"
    ] = normalize_percentage_list(
        record.get(
            "finansman_orani",
            [],
        ),
        conditions,
        remove_example_tables=False,
    )

    # ----------------------------------------------------------------------------------------------
    # FINANSMAN TUTARI
    # ----------------------------------------------------------------------------------------------

    record[
        "finansman_tutari"
    ] = normalize_amount_list(
        record.get(
            "finansman_tutari",
            [],
        ),
        conditions,
    )

    # ----------------------------------------------------------------------------------------------
    # VADE
    # ----------------------------------------------------------------------------------------------

    record[
        "vade"
    ] = normalize_vade_list(
        record.get(
            "vade",
            [],
        ),
        conditions,
    )

    # ----------------------------------------------------------------------------------------------
    # TAKSİT
    # ----------------------------------------------------------------------------------------------

    record[
        "taksit_sayisi"
    ] = normalize_installments(
        record.get(
            "taksit_sayisi",
            [],
        ),
        conditions,
    )

    # ----------------------------------------------------------------------------------------------
    # MASRAF
    # ----------------------------------------------------------------------------------------------

    record[
        "masraf_bilgisi"
    ] = normalize_fee_list(
        record.get(
            "masraf_bilgisi",
            [],
        )
    )

    # ----------------------------------------------------------------------------------------------
    # TARGET
    # ----------------------------------------------------------------------------------------------

    record[
        "hedef_kitle"
    ] = unique_list(
        [
            normalize_space(
                value
            )
            for value in record.get(
                "hedef_kitle",
                [],
            )
            if isinstance(
                value,
                str,
            )
            and "?" not in value
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

        if currency.casefold() in {
            "döviz",
            "doviz",
        }:

            conditions.append(
                "Para birimi kaynakta genel olarak döviz olarak belirtilmiştir."
            )

            continue

        if currency:
            currencies.append(
                currency
            )

    # Structured monetary values varsa TL'yi garanti et.
    monetary_fields = (
        record.get(
            "finansman_tutari",
            [],
        )
        + record.get(
            "kampanya_avantaji",
            [],
        )
    )

    if any(
        re.search(
            r"\bTL\b",
            value,
        )
        for value in monetary_fields
        if isinstance(
            value,
            str,
        )
    ):

        currencies.append(
            "TL"
        )

    record[
        "para_birimi"
    ] = unique_list(
        currencies
    )

    # ----------------------------------------------------------------------------------------------
    # TARGETED SEMANTIC FIXES
    # ----------------------------------------------------------------------------------------------

    # Hızlı Finansman İhtiyaç ve Eğitim kayıtlarındaki
    # %0 oranları açıkça "Örnek Maliyet Tablosu" olduğundan
    # normalize_percentage_list zaten kaldırdı.

    if (
        name
        == "Hızlı Finansman - İhtiyaç Finansmanı"
    ):

        record[
            "kar_payi_orani"
        ] = []

        record[
            "vade"
        ] = [
            "36 ay"
        ]

    elif (
        name
        == "Hızlı Finansman - Eğitim Finansmanı"
    ):

        record[
            "kar_payi_orani"
        ] = []

        # Kaynakta ürün anlatımında 12 aya varan
        # kullanım avantajı açıkça belirtiliyor.
        record[
            "vade"
        ] = [
            "12 ay"
        ]

    # Taşıt finansmanı structured oran / vade mappingi
    if (
        name
        == "Taşıt Finansmanı (Taşıt Kredisi)*"
    ):

        record[
            "finansman_orani"
        ] = [
            "%70",
            "%50",
            "%30",
            "%20",
            "%0",
        ]

        record[
            "vade"
        ] = [
            "48 ay",
            "36 ay",
            "24 ay",
            "12 ay",
        ]

    # Konut ana vadesi
    if (
        name
        == "Konut Finansmanı (Konut Kredisi)*"
    ):

        record[
            "vade"
        ] = [
            "120 ay"
        ]

    # Arsa özel 84 aya çıkabilen yapı.
    if (
        name
        == "Arsa Finansmanı (Arsa Kredisi)*"
    ):

        record[
            "vade"
        ] = [
            "60 ay",
            "84 ay",
        ]

    # İş yeri
    if (
        name
        == "İş yeri Finansmanı (İş yeri Kredisi)*"
    ):

        record[
            "vade"
        ] = [
            "84 ay"
        ]

    # ----------------------------------------------------------------------------------------------
    # CONDITIONS
    # ----------------------------------------------------------------------------------------------

    record[
        "kosullar"
    ] = clean_conditions(
        conditions,
        name,
    )

    # ----------------------------------------------------------------------------------------------
    # TYPES
    # ----------------------------------------------------------------------------------------------

    for field in LIST_FIELDS:

        if not isinstance(
            record.get(field),
            list,
        ):

            record[field] = []

        record[field] = unique_list(
            record[field]
        )

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
            value = str(value)

        if field == "ham_metin":

            record[field] = (
                value.strip()
            )

        else:

            record[field] = (
                normalize_space(
                    value
                )
            )

    return {
        key: record[key]
        for key in FINAL_KEYS
    }


# ==================================================================================================
# VALIDATION
# ==================================================================================================


def validate_records(records):
    errors = []

    if len(records) != 31:

        errors.append(
            f"Toplam kayıt 31 bekleniyordu, "
            f"{len(records)} bulundu."
        )

    finance_count = sum(
        1
        for record in records
        if record[
            "kayit_turu"
        ] == "finansman"
    )

    campaign_count = sum(
        1
        for record in records
        if record[
            "kayit_turu"
        ] == "kampanya"
    )

    if finance_count != 16:

        errors.append(
            f"Finansman 16 bekleniyordu, "
            f"{finance_count} bulundu."
        )

    if campaign_count != 15:

        errors.append(
            f"Kampanya 15 bekleniyordu, "
            f"{campaign_count} bulundu."
        )

    urls = []

    for index, record in enumerate(
        records,
        start=1,
    ):

        prefix = (
            f"[{index:02d}] "
            f"{record['urun_adi']}"
        )

        if list(
            record.keys()
        ) != FINAL_KEYS:

            errors.append(
                f"{prefix} -> "
                "18-key schema/order yanlış"
            )

        if (
            record[
                "banka"
            ]
            != BANK_NAME
        ):

            errors.append(
                f"{prefix} -> "
                "banka adı yanlış"
            )

        if (
            record[
                "kayit_turu"
            ]
            not in {
                "finansman",
                "kampanya",
            }
        ):

            errors.append(
                f"{prefix} -> "
                "kayit_turu yanlış"
            )

        for field in LIST_FIELDS:

            if not isinstance(
                record[field],
                list,
            ):

                errors.append(
                    f"{prefix} -> "
                    f"{field} list değil"
                )

        for field in STRING_FIELDS:

            if not isinstance(
                record[field],
                str,
            ):

                errors.append(
                    f"{prefix} -> "
                    f"{field} string değil"
                )

        if (
            "TRY"
            in record[
                "para_birimi"
            ]
        ):

            errors.append(
                f"{prefix} -> TRY bulundu"
            )

        for value in record[
            "taksit_sayisi"
        ]:

            if not re.fullmatch(
                r"\d+",
                value,
            ):

                errors.append(
                    f"{prefix} -> "
                    f"bozuk taksit: {value}"
                )

        for field in [
            "kar_payi_orani",
            "finansman_orani",
        ]:

            for value in record[
                field
            ]:

                if not re.fullmatch(
                    r"%\d+(?:,\d+)?",
                    value,
                ):

                    errors.append(
                        f"{prefix} -> "
                        f"bozuk {field}: {value}"
                    )

        if (
            record[
                "kayit_turu"
            ]
            == "finansman"
        ):

            if (
                record[
                    "kampanya_turu"
                ]
                or record[
                    "kampanya_avantaji"
                ]
                or record[
                    "kampanya_suresi"
                ]
            ):

                errors.append(
                    f"{prefix} -> "
                    "finance campaign leakage"
                )

        else:

            # Parse edilebilir kampanya tarihi varsa
            # snapshot tarihinde aktif olmalı.
            original_period = (
                record[
                    "kampanya_suresi"
                ]
            )

            # Türkçe normalize edilmiş tarihlerin
            # active kontrolü burada tekrar yapılmaz.
            # Filtering main aşamada eski kaynak formatı üzerinden yapılır.

        if record[
            "kaynak_url"
        ]:

            urls.append(
                record[
                    "kaynak_url"
                ]
            )

    for url, count in Counter(
        urls
    ).items():

        if count > 1:

            errors.append(
                f"Duplicate URL ({count}): {url}"
            )

    return errors


# ==================================================================================================
# AUDIT
# ==================================================================================================


def print_audit(
    input_count,
    records,
    skipped,
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

    bad_installments = [
        (
            record["urun_adi"],
            value,
        )
        for record in records
        for value in record[
            "taksit_sayisi"
        ]
        if not value.isdigit()
    ]

    bad_percentages = [
        (
            record["urun_adi"],
            field,
            value,
        )
        for record in records
        for field in [
            "kar_payi_orani",
            "finansman_orani",
        ]
        for value in record[field]
        if not re.fullmatch(
            r"%\d+(?:,\d+)?",
            value,
        )
    ]

    finance_leakage = [
        record[
            "urun_adi"
        ]
        for record in finance
        if (
            record[
                "kampanya_turu"
            ]
            or record[
                "kampanya_avantaji"
            ]
            or record[
                "kampanya_suresi"
            ]
        )
    ]

    blank_campaign_dates = [
        record[
            "urun_adi"
        ]
        for record in campaigns
        if not record[
            "kampanya_suresi"
        ]
    ]

    print()
    print("=" * 120)
    print(
        "TÜRKİYE FİNANS - FINAL PATCH AUDIT"
    )
    print("=" * 120)

    print(
        f"Input kayıt           : "
        f"{input_count}"
    )

    print(
        f"Final kayıt           : "
        f"{len(records)}"
    )

    print(
        f"Finansman             : "
        f"{len(finance)}"
    )

    print(
        f"Kampanya              : "
        f"{len(campaigns)}"
    )

    print(
        f"Çıkarılan kampanya    : "
        f"{len(skipped)}"
    )

    print(
        f"Exact 18-key schema   : "
        f"{exact_schema}/{len(records)}"
    )

    print(
        f"Duplicate URL         : "
        f"{len(duplicate_urls)}"
    )

    print(
        "TRY kalan             : "
        f"{sum('TRY' in r['para_birimi'] for r in records)}"
    )

    print(
        f"Bozuk taksit          : "
        f"{len(bad_installments)}"
    )

    print(
        f"Bozuk yüzde           : "
        f"{len(bad_percentages)}"
    )

    print(
        f"Finance leakage       : "
        f"{len(finance_leakage)}"
    )

    print(
        f"Boş kampanya süresi   : "
        f"{len(blank_campaign_dates)}"
    )

    print()

    print(
        "SNAPSHOT DIŞI ÇIKARILAN KAMPANYALAR"
    )

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

    print(
        "KRİTİK KAYIT KONTROLLERİ"
    )

    print("-" * 120)

    important_names = [
        "İhtiyaç Finansmanı (İhtiyaç Kredisi)*",
        "Taşıt Finansmanı (Taşıt Kredisi)*",
        "Konut Finansmanı (Konut Kredisi)*",
        "eXtra Limit",
        "Trendyol Alışveriş Finansmanı",
        "Hızlı Finansman - İhtiyaç Finansmanı",
        "Hızlı Finansman - Eğitim Finansmanı",
        "Mobilden Türkiye Finanslı Ol, Kâr Paysız 50.000 TL'ye Varan İhtiyaç Finansmanını Kaçırma!",
    ]

    by_name = {
        record[
            "urun_adi"
        ]: record
        for record in records
    }

    for name in important_names:

        record = by_name.get(
            name
        )

        if not record:
            continue

        print(
            f"✅ {name}"
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
    print(
        "TÜRKİYE FİNANS - FINAL NORMALIZATION PATCH"
    )
    print("=" * 120)

    input_path = find_input_file()

    print(
        f"Input : {input_path}"
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print(
        "Snapshot tarihi: 23.08.2026"
    )

    print()

    with open(
        input_path,
        "r",
        encoding="utf-8",
    ) as file:

        raw_data = json.load(
            file
        )

    # ----------------------------------------------------------------------------------------------
    # OLD WRAPPER / LIST SUPPORT
    # ----------------------------------------------------------------------------------------------

    if isinstance(
        raw_data,
        dict,
    ):

        records = raw_data.get(
            "urunler"
        )

        if not isinstance(
            records,
            list,
        ):

            # Fallback
            records = raw_data.get(
                "kayitlar"
            )

        if not isinstance(
            records,
            list,
        ):

            raise ValueError(
                "Eski wrapper bulundu ancak "
                "'urunler' veya 'kayitlar' listesi yok."
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

    final_records = []

    skipped = []

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

        if (
            original_record.get(
                "kayit_turu"
            )
            == "kampanya"
            and not campaign_is_active(
                original_record.get(
                    "kampanya_suresi",
                    "",
                )
            )
        ):

            print(
                f"[{index:02d}/{input_count}] "
                f"SKIP ❌ {name}"
            )

            skipped.append(
                (
                    name,
                    original_record.get(
                        "kampanya_suresi",
                        "",
                    ),
                )
            )

            continue

        patched = patch_record(
            original_record
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
    )

    # ----------------------------------------------------------------------------------------------
    # VALIDATION
    # ----------------------------------------------------------------------------------------------

    errors = validate_records(
        final_records
    )

    if errors:

        print()
        print("=" * 120)
        print(
            "VALIDATION ERRORS"
        )
        print("=" * 120)

        for error in errors:

            print(
                f"❌ {error}"
            )

        print()
        print(
            "TÜRKİYE FİNANS FINAL PATCH BAŞARISIZ ❌"
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
        input_path.resolve()
        == OUTPUT_FILE.resolve()
        and not BACKUP_FILE.exists()
    ):

        shutil.copy2(
            input_path,
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
    # RE-READ VALIDATION
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
            "Re-read validation başarısız ❌"
        )

        for error in final_errors:

            print(
                f"❌ {error}"
            )

        raise SystemExit(1)

    print()
    print("=" * 120)
    print(
        "TÜRKİYE FİNANS FINAL PATCH BAŞARILI ✅"
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
        "Kâr payı oranları sadece yüzde değerlerine indirildi ✅"
    )

    print(
        "Örnek maliyet tablosu oranları ana alandan çıkarıldı ✅"
    )

    print(
        "Finansman oranları normalize edildi ✅"
    )

    print(
        "Finansman tutarı ve vade alanları normalize edildi ✅"
    )

    print(
        "Taksit sayıları numeric string yapıldı ✅"
    )

    print(
        "Finance -> campaign leakage temizlendi ✅"
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