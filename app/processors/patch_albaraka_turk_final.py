import json
import re
import shutil
from collections import Counter
from copy import deepcopy
from datetime import date
from pathlib import Path


# ==================================================================================================
# ALBARAKA TÜRK - FINAL QUALITY PATCH
# ==================================================================================================


BANK_NAME = "Albaraka Türk Katılım Bankası A.Ş."
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


OUTPUT_FILE = (
    PROCESSED_DIR
    / "albaraka_turk_all.json"
)


BACKUP_FILE = (
    PROCESSED_DIR
    / "albaraka_turk_before_final_cleanup.json"
)


DIRECT_INPUT_CANDIDATES = [
    PROCESSED_DIR / "albaraka_turk_all.json",
    PROCESSED_DIR / "albaraka_turk_final_quality_v5.json",
    PROCESSED_DIR / "albaraka_turk_final_quality_v5 (1).json",
    PROCESSED_DIR / "albaraka_turk_final_quality_v5 (1)(1).json",
]


MIRROR_CAMPAIGN_NAMES = {
    "Togg Taşıt Finansmanı Kampanyası",
    "Umre Finansmanı Kampanyası",
}


ALLOWED_BLANK_CAMPAIGN_PERIOD = {
    "Ücretsiz Ortak ATM Kampanyası",
}


MONTHS_TR = {
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


MONTH_NUM = {
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


def find_input_file():

    for candidate in DIRECT_INPUT_CANDIDATES:

        if candidate.exists():
            return candidate

    matches = sorted(
        PROCESSED_DIR.glob(
            "albaraka_turk_final_quality_v5*.json"
        )
    )

    if matches:
        return matches[0]

    raise FileNotFoundError(
        "\nAlbaraka Türk input dosyası bulunamadı.\n\n"
        "Beklenen örnekler:\n"
        "  data/processed/albaraka_turk_all.json\n"
        "  data/processed/albaraka_turk_final_quality_v5.json\n"
    )


# ==================================================================================================
# DATE HELPERS
# ==================================================================================================


def format_date_tr(value):

    return (
        f"{value.day} "
        f"{MONTHS_TR[value.month]} "
        f"{value.year}"
    )


def parse_numeric_period(value):

    value = normalize_space(
        value
    )

    match = re.fullmatch(
        r"(\d{1,2})\."
        r"(\d{1,2})\."
        r"(\d{4})"
        r"\s*-\s*"
        r"(\d{1,2})\."
        r"(\d{1,2})\."
        r"(\d{4})",
        value,
    )

    if not match:
        return None

    try:

        start = date(
            int(match.group(3)),
            int(match.group(2)),
            int(match.group(1)),
        )

        end = date(
            int(match.group(6)),
            int(match.group(5)),
            int(match.group(4)),
        )

        return (
            start,
            end,
        )

    except ValueError:

        return None


def parse_turkish_period(value):

    value = normalize_space(
        value
    )

    month_pattern = (
        r"(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|"
        r"Haziran|Temmuz|Ağustos|Agustos|Eylül|Eylul|"
        r"Ekim|Kasım|Kasim|Aralık|Aralik)"
    )

    match = re.fullmatch(
        rf"(\d{{1,2}})\s+"
        rf"{month_pattern}\s+"
        rf"(\d{{4}})"
        rf"\s*-\s*"
        rf"(\d{{1,2}})\s+"
        rf"{month_pattern}\s+"
        rf"(\d{{4}})",
        value,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    start_month = MONTH_NUM.get(
        match.group(2).casefold()
    )

    end_month = MONTH_NUM.get(
        match.group(5).casefold()
    )

    if not start_month or not end_month:
        return None

    try:

        start = date(
            int(match.group(3)),
            start_month,
            int(match.group(1)),
        )

        end = date(
            int(match.group(6)),
            end_month,
            int(match.group(4)),
        )

        return (
            start,
            end,
        )

    except ValueError:

        return None


def parse_period(value):

    parsed = parse_numeric_period(
        value
    )

    if parsed:
        return parsed

    return parse_turkish_period(
        value
    )


def normalize_campaign_period(value):

    value = normalize_space(
        value
    )

    if not value:
        return ""

    parsed = parse_numeric_period(
        value
    )

    if not parsed:

        # Zaten Türkçe standarda geçmişse aynen bırak.
        return value

    start, end = parsed

    return (
        f"{format_date_tr(start)}"
        f" - "
        f"{format_date_tr(end)}"
    )


def campaign_is_active(value):

    if not value:
        return True

    parsed = parse_period(
        value
    )

    if not parsed:
        return True

    start, end = parsed

    return (
        start
        <= SNAPSHOT_DATE
        <= end
    )


# ==================================================================================================
# MIRROR / REDIRECT DETECTION
# ==================================================================================================


def campaign_structured_fields_empty(record):

    return (
        record.get(
            "kampanya_avantaji",
            [],
        )
        == []
        and record.get(
            "kampanya_suresi",
            "",
        )
        == ""
        and record.get(
            "hedef_kitle",
            [],
        )
        == []
        and record.get(
            "kosullar",
            [],
        )
        == []
    )


def is_togg_campaign_mirror(record):

    if (
        record.get(
            "kayit_turu"
        )
        != "kampanya"
    ):
        return False

    if (
        record.get(
            "urun_adi"
        )
        != "Togg Taşıt Finansmanı Kampanyası"
    ):
        return False

    if not campaign_structured_fields_empty(
        record
    ):
        return False

    ham = normalize_space(
        record.get(
            "ham_metin",
            "",
        )
    )

    return (
        "Togg Finansmanı"
        in ham
        and
        "Bireysel Finansmanlar"
        in ham
        and
        "Togg Araç Finansmanı Özellikleri"
        in ham
    )


def is_umre_campaign_mirror(record):

    if (
        record.get(
            "kayit_turu"
        )
        != "kampanya"
    ):
        return False

    if (
        record.get(
            "urun_adi"
        )
        != "Umre Finansmanı Kampanyası"
    ):
        return False

    if not campaign_structured_fields_empty(
        record
    ):
        return False

    ham = normalize_space(
        record.get(
            "ham_metin",
            "",
        )
    )

    return (
        "Şubesiz Umre Finansmanı"
        in ham
        and
        "Bireysel Finansmanlar"
        in ham
    )


def is_confirmed_mirror(record):

    return (
        is_togg_campaign_mirror(
            record
        )
        or
        is_umre_campaign_mirror(
            record
        )
    )


# ==================================================================================================
# CONDITIONS CLEANUP
# ==================================================================================================


def clean_conditions(record):

    name = record.get(
        "urun_adi",
        "",
    )

    values = record.get(
        "kosullar",
        [],
    )

    if not isinstance(
        values,
        list,
    ):

        return (
            values,
            [],
        )

    result = []

    log = []

    for raw_value in values:

        if not isinstance(
            raw_value,
            str,
        ):

            result.append(
                raw_value
            )

            continue

        normalized = normalize_space(
            raw_value
        )

        # ------------------------------------------------------------------------------------------
        # KONUT
        # ------------------------------------------------------------------------------------------

        if name == "Konut Finansmanı":

            prefix = (
                "Konut Finansmanı "
                "Anasayfa "
                "Bireysel Finansmanlar "
                "Konut Finansmanı "
                "Konut Finansmanı "
                "Hemen Başvur "
            )

            if normalized.startswith(
                prefix
            ):

                cleaned = (
                    normalized[
                        len(prefix):
                    ]
                    .strip()
                )

                if cleaned:

                    result.append(
                        cleaned
                    )

                    log.append(
                        {
                            "action": "prefix_clean",
                            "old": raw_value,
                            "new": cleaned,
                        }
                    )

                continue

            if normalized.startswith(
                "KONUT FİNANSMANI Finansman Türü "
            ):

                log.append(
                    {
                        "action": "remove",
                        "old": raw_value,
                    }
                )

                continue

            if normalized.startswith(
                "Web Sitesi Albaraka Mobil SMS Şube "
                "Konut (Ev) Finansmanı Hakkında "
                "Sıkça Sorulan Sorular "
            ):

                log.append(
                    {
                        "action": "remove",
                        "old": raw_value,
                    }
                )

                continue

        # ------------------------------------------------------------------------------------------
        # BAŞVURU KANALLARI PREFIX
        # ------------------------------------------------------------------------------------------

        application_prefix = (
            "Başvuru Kanalları "
            "Web Sitesi "
            "Albaraka Mobil "
            "SMS "
            "Şube "
        )

        if normalized.startswith(
            application_prefix
        ):

            cleaned = (
                normalized[
                    len(application_prefix):
                ]
                .strip()
            )

            if cleaned:

                result.append(
                    cleaned
                )

                log.append(
                    {
                        "action": "prefix_clean",
                        "old": raw_value,
                        "new": cleaned,
                    }
                )

            continue

        # ------------------------------------------------------------------------------------------
        # CTA PREFIX
        # ------------------------------------------------------------------------------------------

        branch_prefix = (
            "Size En Yakın Şube "
        )

        if normalized.startswith(
            branch_prefix
        ):

            cleaned = (
                normalized[
                    len(branch_prefix):
                ]
                .strip()
            )

            if cleaned:

                result.append(
                    cleaned
                )

                log.append(
                    {
                        "action": "prefix_clean",
                        "old": raw_value,
                        "new": cleaned,
                    }
                )

            continue

        # ------------------------------------------------------------------------------------------
        # FAQ HEADINGS
        # ------------------------------------------------------------------------------------------

        if (
            normalized.startswith(
                "Sıkça Sorulan Sorular "
            )
            and normalized.endswith(
                "?"
            )
        ):

            log.append(
                {
                    "action": "remove",
                    "old": raw_value,
                }
            )

            continue

        # ------------------------------------------------------------------------------------------
        # NO CHANGE
        # ------------------------------------------------------------------------------------------

        result.append(
            raw_value
        )

    return (
        result,
        log,
    )


# ==================================================================================================
# PATCH
# ==================================================================================================


def patch_records(records):

    final_records = []

    removed_mirrors = []

    condition_log = []

    normalized_dates = []

    for record in records:

        # ------------------------------------------------------------------------------------------
        # MIRROR DROP
        # ------------------------------------------------------------------------------------------

        if is_confirmed_mirror(
            record
        ):

            removed_mirrors.append(
                {
                    "urun_adi":
                        record.get(
                            "urun_adi",
                            "",
                        ),

                    "kaynak_url":
                        record.get(
                            "kaynak_url",
                            "",
                        ),
                }
            )

            continue

        patched = deepcopy(
            record
        )

        # ------------------------------------------------------------------------------------------
        # DATE NORMALIZATION
        # ------------------------------------------------------------------------------------------

        if (
            patched.get(
                "kayit_turu"
            )
            == "kampanya"
        ):

            old_period = patched.get(
                "kampanya_suresi",
                "",
            )

            new_period = (
                normalize_campaign_period(
                    old_period
                )
            )

            patched[
                "kampanya_suresi"
            ] = new_period

            if (
                old_period
                != new_period
            ):

                normalized_dates.append(
                    {
                        "urun_adi":
                            patched.get(
                                "urun_adi",
                                "",
                            ),

                        "old":
                            old_period,

                        "new":
                            new_period,
                    }
                )

        # ------------------------------------------------------------------------------------------
        # CONDITIONS
        # ------------------------------------------------------------------------------------------

        new_conditions, log = (
            clean_conditions(
                patched
            )
        )

        patched[
            "kosullar"
        ] = new_conditions

        if log:

            condition_log.append(
                {
                    "urun_adi":
                        patched.get(
                            "urun_adi",
                            "",
                        ),

                    "changes":
                        log,
                }
            )

        final_records.append(
            patched
        )

    return (
        final_records,
        removed_mirrors,
        normalized_dates,
        condition_log,
    )


# ==================================================================================================
# VALIDATION
# ==================================================================================================


def validate_records(
    original_records,
    final_records,
):

    errors = []

    # ----------------------------------------------------------------------------------------------
    # COUNTS
    # ----------------------------------------------------------------------------------------------

    if len(
        final_records
    ) != 63:

        errors.append(
            f"Toplam kayıt 63 bekleniyordu, "
            f"{len(final_records)} bulundu."
        )

    finance_count = sum(
        record.get(
            "kayit_turu"
        )
        == "finansman"

        for record
        in final_records
    )

    campaign_count = sum(
        record.get(
            "kayit_turu"
        )
        == "kampanya"

        for record
        in final_records
    )

    if finance_count != 17:

        errors.append(
            f"Finansman 17 bekleniyordu, "
            f"{finance_count} bulundu."
        )

    if campaign_count != 46:

        errors.append(
            f"Kampanya 46 bekleniyordu, "
            f"{campaign_count} bulundu."
        )

    # ----------------------------------------------------------------------------------------------
    # SCHEMA / TYPES / STRUCTURED FORMAT
    # ----------------------------------------------------------------------------------------------

    urls = []

    for index, record in enumerate(
        final_records,
        start=1,
    ):

        prefix = (
            f"[{index:03d}] "
            f"{record.get('urun_adi', '')}"
        )

        if list(
            record.keys()
        ) != FINAL_KEYS:

            errors.append(
                f"{prefix} -> "
                "Exact 18-key schema/order yanlış."
            )

        if (
            record.get(
                "banka"
            )
            != BANK_NAME
        ):

            errors.append(
                f"{prefix} -> "
                "Banka adı yanlış."
            )

        if (
            record.get(
                "kayit_turu"
            )
            not in {
                "finansman",
                "kampanya",
            }
        ):

            errors.append(
                f"{prefix} -> "
                "kayit_turu yanlış."
            )

        for field in LIST_FIELDS:

            if not isinstance(
                record.get(
                    field
                ),
                list,
            ):

                errors.append(
                    f"{prefix} -> "
                    f"{field} list değil."
                )

        for field in STRING_FIELDS:

            if not isinstance(
                record.get(
                    field
                ),
                str,
            ):

                errors.append(
                    f"{prefix} -> "
                    f"{field} string değil."
                )

        if (
            "TRY"
            in record.get(
                "para_birimi",
                [],
            )
        ):

            errors.append(
                f"{prefix} -> "
                "TRY bulundu."
            )

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
                    f"Bozuk taksit: "
                    f"{installment}"
                )

        for field in [
            "kar_payi_orani",
            "finansman_orani",
        ]:

            for value in record.get(
                field,
                [],
            ):

                if not re.fullmatch(
                    r"%\d+(?:,\d+)?",
                    value,
                ):

                    errors.append(
                        f"{prefix} -> "
                        f"Bozuk {field}: "
                        f"{value}"
                    )

        url = record.get(
            "kaynak_url",
            "",
        )

        if url:
            urls.append(
                url
            )

    # ----------------------------------------------------------------------------------------------
    # DUPLICATE URL
    # ----------------------------------------------------------------------------------------------

    for url, count in Counter(
        urls
    ).items():

        if count > 1:

            errors.append(
                f"Duplicate URL ({count}): "
                f"{url}"
            )

    # ----------------------------------------------------------------------------------------------
    # NO MIRROR CAMPAIGNS
    # ----------------------------------------------------------------------------------------------

    remaining_mirrors = [
        record.get(
            "urun_adi",
            ""
        )
        for record in final_records
        if (
            record.get(
                "kayit_turu"
            )
            == "kampanya"
            and record.get(
                "urun_adi"
            )
            in MIRROR_CAMPAIGN_NAMES
        )
    ]

    if remaining_mirrors:

        errors.append(
            "Mirror kampanyalar kaldı: "
            + ", ".join(
                remaining_mirrors
            )
        )

    # ----------------------------------------------------------------------------------------------
    # CAMPAIGN DATE CHECK
    # ----------------------------------------------------------------------------------------------

    for record in final_records:

        if (
            record.get(
                "kayit_turu"
            )
            != "kampanya"
        ):

            continue

        name = record.get(
            "urun_adi",
            "",
        )

        period = record.get(
            "kampanya_suresi",
            "",
        )

        if not period:

            if (
                name
                not in ALLOWED_BLANK_CAMPAIGN_PERIOD
            ):

                errors.append(
                    f"{name} -> "
                    "kampanya_suresi boş."
                )

            continue

        parsed = parse_period(
            period
        )

        if not parsed:

            errors.append(
                f"{name} -> "
                f"kampanya_suresi parse edilemedi: "
                f"{period}"
            )

            continue

        if not campaign_is_active(
            period
        ):

            errors.append(
                f"{name} -> "
                f"23.08.2026 tarihinde aktif değil: "
                f"{period}"
            )

    # ----------------------------------------------------------------------------------------------
    # ONLY ALLOWED FIELDS CHANGED
    #
    # Finalde kalan kayıtlar için sadece:
    #   - kampanya_suresi
    #   - kosullar
    #
    # değişebilir.
    # ----------------------------------------------------------------------------------------------

    original_by_url = {
        record.get(
            "kaynak_url"
        ): record

        for record
        in original_records
    }

    final_urls = {
        record.get(
            "kaynak_url"
        )

        for record
        in final_records
    }

    removed_original_records = [
        record
        for record in original_records
        if record.get(
            "kaynak_url"
        )
        not in final_urls
    ]

    for record in removed_original_records:

        if (
            record.get(
                "urun_adi"
            )
            not in MIRROR_CAMPAIGN_NAMES
        ):

            errors.append(
                "İzin verilmeyen kayıt silindi: "
                f"{record.get('urun_adi', '')}"
            )

    for record in final_records:

        url = record.get(
            "kaynak_url"
        )

        original = original_by_url.get(
            url
        )

        if original is None:

            errors.append(
                "Finalde yeni/unknown kayıt bulundu: "
                f"{record.get('urun_adi', '')}"
            )

            continue

        for key in FINAL_KEYS:

            if key in {
                "kampanya_suresi",
                "kosullar",
            }:

                continue

            if (
                original.get(key)
                != record.get(key)
            ):

                errors.append(
                    f"{record.get('urun_adi', '')} -> "
                    f"İzin verilmeyen alan değişti: "
                    f"{key}"
                )

    return errors


# ==================================================================================================
# AUDIT
# ==================================================================================================


def print_audit(
    records,
    removed_mirrors,
    normalized_dates,
    condition_log,
):

    finance = [
        record
        for record in records
        if record.get(
            "kayit_turu"
        )
        == "finansman"
    ]

    campaigns = [
        record
        for record in records
        if record.get(
            "kayit_turu"
        )
        == "kampanya"
    ]

    urls = [
        record.get(
            "kaynak_url"
        )
        for record in records
        if record.get(
            "kaynak_url"
        )
    ]

    duplicate_urls = [
        url
        for url, count in Counter(
            urls
        ).items()
        if count > 1
    ]

    bad_installments = [
        (
            record.get(
                "urun_adi"
            ),
            value,
        )
        for record in records
        for value in record.get(
            "taksit_sayisi",
            [],
        )
        if not re.fullmatch(
            r"\d+",
            value,
        )
    ]

    bad_percentages = [
        (
            record.get(
                "urun_adi"
            ),
            field,
            value,
        )
        for record in records
        for field in [
            "kar_payi_orani",
            "finansman_orani",
        ]
        for value in record.get(
            field,
            [],
        )
        if not re.fullmatch(
            r"%\d+(?:,\d+)?",
            value,
        )
    ]

    blank_periods = [
        record.get(
            "urun_adi"
        )
        for record in campaigns
        if not record.get(
            "kampanya_suresi"
        )
    ]

    print()
    print("=" * 120)
    print(
        "ALBARAKA TÜRK - FINAL QUALITY PATCH AUDIT"
    )
    print("=" * 120)

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
        f"Mirror çıkarıldı      : "
        f"{len(removed_mirrors)}"
    )

    print(
        f"Tarih normalize       : "
        f"{len(normalized_dates)}"
    )

    print(
        f"Koşul temizlenen kayıt: "
        f"{len(condition_log)}"
    )

    print(
        "Exact 18-key schema   : "
        f"{sum(list(r.keys()) == FINAL_KEYS for r in records)}"
        f"/{len(records)}"
    )

    print(
        f"Duplicate URL         : "
        f"{len(duplicate_urls)}"
    )

    print(
        "TRY kalan             : "
        f"{sum('TRY' in r.get('para_birimi', []) for r in records)}"
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
        f"Boş kampanya süresi   : "
        f"{len(blank_periods)}"
    )

    if blank_periods:

        for name in blank_periods:

            print(
                f"   ↳ {name}"
            )

    print()
    print(
        "ÇIKARILAN MIRROR KAYITLAR"
    )
    print("-" * 120)

    if removed_mirrors:

        for item in removed_mirrors:

            print(
                f"❌ {item['urun_adi']}"
            )

            print(
                f"   URL: "
                f"{item['kaynak_url']}"
            )

    else:

        print(
            "Mirror kayıt bulunmadı."
        )

    print()
    print(
        "KOŞUL CLEANUP"
    )
    print("-" * 120)

    if condition_log:

        for item in condition_log:

            print(
                f"✅ {item['urun_adi']} "
                f"({len(item['changes'])} değişiklik)"
            )

    else:

        print(
            "Ek koşul temizliği gerekmedi."
        )

    print("=" * 120)


# ==================================================================================================
# MAIN
# ==================================================================================================


def main():

    print()
    print("=" * 120)
    print(
        "ALBARAKA TÜRK - FINAL QUALITY PATCH"
    )
    print("=" * 120)

    input_file = find_input_file()

    print(
        f"Input : {input_file}"
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print(
        "Snapshot: 23.08.2026"
    )

    print()

    with open(
        input_file,
        "r",
        encoding="utf-8",
    ) as file:

        records = json.load(
            file
        )

    if not isinstance(
        records,
        list,
    ):

        raise ValueError(
            "Albaraka JSON root list olmalı."
        )

    original_records = deepcopy(
        records
    )

    print(
        f"Input kayıt: "
        f"{len(records)}"
    )

    (
        final_records,
        removed_mirrors,
        normalized_dates,
        condition_log,
    ) = patch_records(
        records
    )

    print_audit(
        final_records,
        removed_mirrors,
        normalized_dates,
        condition_log,
    )

    errors = validate_records(
        original_records,
        final_records,
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
            "ALBARAKA TÜRK FINAL PATCH BAŞARISIZ ❌"
        )

        print(
            "Final dosya yazılmadı."
        )

        raise SystemExit(1)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not BACKUP_FILE.exists():

        shutil.copy2(
            input_file,
            BACKUP_FILE,
        )

        print()
        print(
            f"Backup oluşturuldu: "
            f"{BACKUP_FILE}"
        )

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

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        saved_records = json.load(
            file
        )

    errors = validate_records(
        original_records,
        saved_records,
    )

    if errors:

        print()
        print(
            "Re-read validation başarısız ❌"
        )

        for error in errors:

            print(
                f"❌ {error}"
            )

        raise SystemExit(1)

    print()
    print("=" * 120)
    print(
        "ALBARAKA TÜRK FINAL PATCH BAŞARILI ✅"
    )
    print("=" * 120)

    print(
        f"JSON: {OUTPUT_FILE}"
    )

    print()

    print(
        "2 redirect/mirror kampanya temizlendi ✅"
    )

    print(
        "Kampanya tarihleri Türkçe standarda çekildi ✅"
    )

    print(
        "Kesin UI/navigation residue'ları kosullar alanından temizlendi ✅"
    )

    print(
        "ham_metin korunmuştur ✅"
    )

    print(
        "Structured finansman/kampanya alanları korunmuştur ✅"
    )

    print(
        "17 finansman + 46 kampanya = 63 kayıt ✅"
    )

    print(
        "Exact 18-key schema korundu ✅"
    )

    print(
        "Duplicate URL: 0 ✅"
    )

    print(
        "TRY: 0 ✅"
    )

    print("=" * 120)


if __name__ == "__main__":
    main()