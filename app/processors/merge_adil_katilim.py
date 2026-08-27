import json
import sys
from pathlib import Path


# =========================================================
# CONFIG
# =========================================================

ROOT = Path(__file__).resolve().parents[2]

FINANCE_FILE = (
    ROOT
    / "data"
    / "processed"
    / "adil_katilim_finansman_extracted.json"
)

OUTPUT_FILE = (
    ROOT
    / "data"
    / "processed"
    / "adil_katilim_all.json"
)

BANK_NAME = "Adil Katılım Bankası A.Ş."

EXPECTED_FINANCE_COUNT = 1
EXPECTED_CAMPAIGN_COUNT = 0
EXPECTED_TOTAL_COUNT = 1


SCHEMA_KEYS = [
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


# =========================================================
# LOAD
# =========================================================

def load_json(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            f"{path.name} root yapısı list değil."
        )

    return data


# =========================================================
# VALIDATE RECORD
# =========================================================

def validate_record(record, index):
    errors = []

    prefix = f"[{index}]"

    if not isinstance(record, dict):
        return [
            f"{prefix} kayıt dict değil."
        ]

    # Exact 18-key schema
    if list(record.keys()) != SCHEMA_KEYS:
        errors.append(
            f"{prefix} 18-key schema/order hatalı."
        )

    # Bank
    if record.get("banka") != BANK_NAME:
        errors.append(
            f"{prefix} banka alanı hatalı."
        )

    # Type
    if record.get("kayit_turu") != "finansman":
        errors.append(
            f"{prefix} kayit_turu finansman değil."
        )

    # List fields
    for field in LIST_FIELDS:
        if not isinstance(
            record.get(field),
            list,
        ):
            errors.append(
                f"{prefix} {field} list değil."
            )

    # Required scalar values
    for field in (
        "banka",
        "kayit_turu",
        "urun_adi",
        "urun_kategorisi",
        "kaynak_url",
        "ham_metin",
    ):
        value = record.get(field)

        if (
            not isinstance(value, str)
            or
            not value.strip()
        ):
            errors.append(
                f"{prefix} {field} boş."
            )

    # Product
    if (
        record.get("urun_adi")
        != "Bireysel Finansman"
    ):
        errors.append(
            (
                f"{prefix} beklenmeyen ürün: "
                f"{record.get('urun_adi')}"
            )
        )

    # Campaign fields must stay empty
    if record.get("kampanya_turu") != "":
        errors.append(
            f"{prefix} kampanya_turu boş değil."
        )

    if record.get("kampanya_avantaji") != []:
        errors.append(
            f"{prefix} kampanya_avantaji boş değil."
        )

    if record.get("kampanya_suresi") != "":
        errors.append(
            f"{prefix} kampanya_suresi boş değil."
        )

    # Source URL
    url = str(
        record.get(
            "kaynak_url",
            "",
        )
    ).strip()

    if not url.startswith(
        "https://www.adilkatilim.com.tr/"
    ):
        errors.append(
            (
                f"{prefix} kaynak_url "
                "Adil Katılım domaininde değil."
            )
        )

    # Semantic source markers
    raw_text = str(
        record.get(
            "ham_metin",
            "",
        )
    ).casefold()

    required_markers = [
        "bireysel finansman",
        "eğitim",
        "sağlık",
        "tatil",
        "ev eşyası",
        "faizsiz finansman",
    ]

    for marker in required_markers:
        if marker not in raw_text:
            errors.append(
                (
                    f"{prefix} ham_metin içinde "
                    f"beklenen ifade yok: {marker}"
                )
            )

    # Ticari kesinlikle olmamalı
    if "ticari finansman" in raw_text:
        errors.append(
            (
                f"{prefix} Ticari Finansman "
                "metni bulundu."
            )
        )

    return errors


# =========================================================
# DUPLICATE URL
# =========================================================

def find_duplicate_urls(records):
    seen = {}
    duplicates = []

    for index, record in enumerate(
        records,
        start=1,
    ):
        url = str(
            record.get(
                "kaynak_url",
                "",
            )
        ).strip()

        normalized = (
            url
            .rstrip("/")
            .casefold()
        )

        if not normalized:
            continue

        if normalized in seen:
            duplicates.append(
                {
                    "url": url,
                    "first": seen[normalized],
                    "second": index,
                }
            )
        else:
            seen[normalized] = index

    return duplicates


# =========================================================
# MAIN
# =========================================================

def main():
    print()

    print(
        "=" * 120
    )

    print(
        "ADİL KATILIM - FINAL MERGE"
    )

    print(
        "=" * 120
    )

    print(
        "Finance:",
        FINANCE_FILE,
    )

    print(
        "Campaign: 0 kayıt "
        "(public aktif kampanya bulunmadı)"
    )

    print(
        "Output:",
        OUTPUT_FILE,
    )

    print()

    # =====================================================
    # FILE CHECK
    # =====================================================

    if not FINANCE_FILE.exists():
        print(
            "Finance dosyası bulunamadı ❌"
        )

        sys.exit(1)

    # =====================================================
    # LOAD
    # =====================================================

    finance_records = load_json(
        FINANCE_FILE
    )

    campaign_records = []

    merged_records = (
        finance_records
        +
        campaign_records
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    errors = []

    if (
        len(finance_records)
        != EXPECTED_FINANCE_COUNT
    ):
        errors.append(
            (
                "Finance kayıt sayısı yanlış: "
                f"beklenen={EXPECTED_FINANCE_COUNT}, "
                f"actual={len(finance_records)}"
            )
        )

    if (
        len(campaign_records)
        != EXPECTED_CAMPAIGN_COUNT
    ):
        errors.append(
            (
                "Campaign kayıt sayısı yanlış: "
                f"beklenen={EXPECTED_CAMPAIGN_COUNT}, "
                f"actual={len(campaign_records)}"
            )
        )

    if (
        len(merged_records)
        != EXPECTED_TOTAL_COUNT
    ):
        errors.append(
            (
                "Final kayıt sayısı yanlış: "
                f"beklenen={EXPECTED_TOTAL_COUNT}, "
                f"actual={len(merged_records)}"
            )
        )

    for index, record in enumerate(
        merged_records,
        start=1,
    ):
        errors.extend(
            validate_record(
                record,
                index,
            )
        )

    duplicate_urls = find_duplicate_urls(
        merged_records
    )

    for duplicate in duplicate_urls:
        errors.append(
            (
                "Duplicate kaynak_url: "
                f"{duplicate['url']} "
                f"(index {duplicate['first']} "
                f"ve {duplicate['second']})"
            )
        )

    finance_count = sum(
        1
        for record in merged_records
        if record.get("kayit_turu")
        == "finansman"
    )

    campaign_count = sum(
        1
        for record in merged_records
        if record.get("kayit_turu")
        == "kampanya"
    )

    if (
        finance_count
        != EXPECTED_FINANCE_COUNT
    ):
        errors.append(
            (
                "Merged finance count yanlış: "
                f"{finance_count}"
            )
        )

    if (
        campaign_count
        != EXPECTED_CAMPAIGN_COUNT
    ):
        errors.append(
            (
                "Merged campaign count yanlış: "
                f"{campaign_count}"
            )
        )

    # =====================================================
    # REPORT
    # =====================================================

    print(
        "=" * 120
    )

    print(
        "MERGE VALIDATION"
    )

    print(
        "=" * 120
    )

    print(
        "Expected finance:",
        EXPECTED_FINANCE_COUNT,
    )

    print(
        "Actual finance:",
        finance_count,
    )

    print(
        "Expected campaign:",
        EXPECTED_CAMPAIGN_COUNT,
    )

    print(
        "Actual campaign:",
        campaign_count,
    )

    print(
        "Expected total:",
        EXPECTED_TOTAL_COUNT,
    )

    print(
        "Actual total:",
        len(
            merged_records
        ),
    )

    print(
        "Duplicate URL:",
        len(
            duplicate_urls
        ),
    )

    print(
        "Validation error:",
        len(
            errors
        ),
    )

    # =====================================================
    # ERRORS
    # =====================================================

    if errors:
        print()

        print(
            "HATALAR:"
        )

        for error in errors:
            print(
                "❌",
                error,
            )

        print()

        print(
            (
                "SONUÇ: ADİL KATILIM "
                "MERGE BAŞARISIZ ❌"
            )
        )

        sys.exit(1)

    # =====================================================
    # SAVE
    # =====================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            merged_records,
            file,
            ensure_ascii=False,
            indent=4,
        )

    # =====================================================
    # RELOAD CHECK
    # =====================================================

    saved_records = load_json(
        OUTPUT_FILE
    )

    if saved_records != merged_records:
        print()

        print(
            "Output reload validation başarısız ❌"
        )

        sys.exit(1)

    print()

    print(
        (
            "SONUÇ: ADİL KATILIM "
            "MERGE BAŞARILI ✅"
        )
    )

    print(
        (
            f"{finance_count} finansman "
            f"+ {campaign_count} kampanya "
            f"= {len(merged_records)} "
            "final kayıt ✅"
        )
    )

    print(
        "18-key schema doğrulandı ✅"
    )

    print(
        "Duplicate kaynak_url bulunmadı ✅"
    )

    print(
        "Output reload doğrulandı ✅"
    )

    print()

    print(
        "JSON:",
        OUTPUT_FILE,
    )

    print(
        "=" * 120
    )


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print(
            "\nKullanıcı tarafından durduruldu."
        )

        sys.exit(130)

    except Exception as error:
        print()

        print(
            "MERGE ERROR ❌"
        )

        print(
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )

        sys.exit(1)