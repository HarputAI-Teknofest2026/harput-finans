import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = ROOT / "data" / "processed"

CAMPAIGN_FILE = (
    PROCESSED_DIR
    / "dunya_katilim_kampanya_extracted.json"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "dunya_katilim_all.json"
)

BANK_NAME = "Dünya Katılım Bankası A.Ş."

EXPECTED_FINANCE_COUNT = 6
EXPECTED_CAMPAIGN_COUNT = 43
EXPECTED_TOTAL_COUNT = 49


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


SCALAR_FIELDS = set(SCHEMA_KEYS) - LIST_FIELDS


# =========================================================
# JSON LOAD
# =========================================================

def load_json(path):
    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except Exception as error:
        raise RuntimeError(
            f"{path.name} okunamadı: {error}"
        )

    if not isinstance(
        data,
        list,
    ):
        raise ValueError(
            f"{path.name} root yapısı list değil."
        )

    return data


# =========================================================
# FINANCE FILE DISCOVERY
# =========================================================

def find_finance_file():
    candidates = []

    for path in sorted(
        PROCESSED_DIR.glob(
            "dunya_katilim*.json"
        )
    ):
        if path == CAMPAIGN_FILE:
            continue

        if path == OUTPUT_FILE:
            continue

        try:
            data = load_json(
                path
            )

        except Exception:
            continue

        if len(data) != EXPECTED_FINANCE_COUNT:
            continue

        if not data:
            continue

        if not all(
            isinstance(record, dict)
            for record in data
        ):
            continue

        if not all(
            record.get(
                "banka"
            )
            == BANK_NAME
            for record in data
        ):
            continue

        if not all(
            record.get(
                "kayit_turu"
            )
            == "finansman"
            for record in data
        ):
            continue

        candidates.append(
            path
        )

    if len(candidates) == 1:
        return candidates[0]

    if not candidates:
        raise FileNotFoundError(
            (
                "Dünya Katılım final finance JSON "
                "otomatik bulunamadı.\n"
                f"Aranan klasör: {PROCESSED_DIR}\n"
                "Beklenen: 6 kayıt ve tüm kayıtlarda "
                'kayit_turu="finansman".'
            )
        )

    candidate_names = "\n".join(
        f"- {path}"
        for path in candidates
    )

    raise RuntimeError(
        (
            "Birden fazla finance JSON adayı bulundu:\n"
            f"{candidate_names}\n"
            "Merge güvenliği için işlem durduruldu."
        )
    )


# =========================================================
# RECORD VALIDATION
# =========================================================

def validate_record(
    record,
    index,
    expected_type,
    source_name,
):
    errors = []

    prefix = (
        f"{source_name}[{index}]"
    )

    if not isinstance(
        record,
        dict,
    ):
        return [
            (
                f"{prefix} -> "
                "kayıt dict değil."
            )
        ]

    # -----------------------------------------------------
    # EXACT 18-KEY SCHEMA
    # -----------------------------------------------------

    if list(
        record.keys()
    ) != SCHEMA_KEYS:
        errors.append(
            (
                f"{prefix} -> "
                "18-key schema/order uyuşmuyor."
            )
        )

    # -----------------------------------------------------
    # BANK
    # -----------------------------------------------------

    if (
        record.get(
            "banka"
        )
        != BANK_NAME
    ):
        errors.append(
            (
                f"{prefix} -> "
                "banka alanı yanlış: "
                f"{record.get('banka')}"
            )
        )

    # -----------------------------------------------------
    # RECORD TYPE
    # -----------------------------------------------------

    if (
        record.get(
            "kayit_turu"
        )
        != expected_type
    ):
        errors.append(
            (
                f"{prefix} -> "
                "kayit_turu yanlış: "
                f"{record.get('kayit_turu')} "
                f"(beklenen={expected_type})"
            )
        )

    # -----------------------------------------------------
    # LIST FIELDS
    # -----------------------------------------------------

    for field in LIST_FIELDS:
        if not isinstance(
            record.get(
                field
            ),
            list,
        ):
            errors.append(
                (
                    f"{prefix} -> "
                    f"{field} list değil."
                )
            )

    # -----------------------------------------------------
    # SCALAR FIELDS
    # -----------------------------------------------------

    for field in SCALAR_FIELDS:
        if not isinstance(
            record.get(
                field
            ),
            str,
        ):
            errors.append(
                (
                    f"{prefix} -> "
                    f"{field} string değil."
                )
            )

    # -----------------------------------------------------
    # REQUIRED PROVENANCE
    # -----------------------------------------------------

    for field in (
        "urun_adi",
        "urun_kategorisi",
        "kaynak_url",
        "ham_metin",
    ):
        value = record.get(
            field
        )

        if (
            not isinstance(
                value,
                str,
            )
            or
            not value.strip()
        ):
            errors.append(
                (
                    f"{prefix} -> "
                    f"{field} boş."
                )
            )

    # -----------------------------------------------------
    # URL
    # -----------------------------------------------------

    url = str(
        record.get(
            "kaynak_url",
            "",
        )
    )

    if (
        url
        and
        not url.startswith(
            "https://dunyakatilim.com.tr/"
        )
    ):
        errors.append(
            (
                f"{prefix} -> "
                "kaynak_url Dünya Katılım "
                f"domaininde değil: {url}"
            )
        )

    # -----------------------------------------------------
    # CURRENCY
    # -----------------------------------------------------

    currencies = record.get(
        "para_birimi",
        [],
    )

    if isinstance(
        currencies,
        list,
    ):
        for currency in currencies:
            if currency != "TL":
                errors.append(
                    (
                        f"{prefix} -> "
                        "desteklenmeyen "
                        f"para_birimi: {currency}"
                    )
                )

    # -----------------------------------------------------
    # CAMPAIGN FIELDS ON FINANCE
    # -----------------------------------------------------

    if expected_type == "finansman":
        if record.get(
            "kampanya_turu"
        ) != "":
            errors.append(
                (
                    f"{prefix} -> "
                    "finansman kaydında "
                    "kampanya_turu boş olmalı."
                )
            )

        if record.get(
            "kampanya_avantaji"
        ) != []:
            errors.append(
                (
                    f"{prefix} -> "
                    "finansman kaydında "
                    "kampanya_avantaji [] olmalı."
                )
            )

        if record.get(
            "kampanya_suresi"
        ) != "":
            errors.append(
                (
                    f"{prefix} -> "
                    "finansman kaydında "
                    "kampanya_suresi boş olmalı."
                )
            )

    # -----------------------------------------------------
    # CAMPAIGN TYPE
    # -----------------------------------------------------

    if expected_type == "kampanya":
        if not record.get(
            "kampanya_turu"
        ):
            errors.append(
                (
                    f"{prefix} -> "
                    "kampanya_turu boş."
                )
            )

    return errors


# =========================================================
# DATASET VALIDATION
# =========================================================

def validate_dataset(
    records,
    expected_count,
    expected_type,
    source_name,
):
    errors = []

    if len(
        records
    ) != expected_count:
        errors.append(
            (
                f"{source_name} kayıt sayısı yanlış: "
                f"beklenen={expected_count}, "
                f"actual={len(records)}"
            )
        )

    for index, record in enumerate(
        records,
        start=1,
    ):
        errors.extend(
            validate_record(
                record=record,
                index=index,
                expected_type=expected_type,
                source_name=source_name,
            )
        )

    return errors


# =========================================================
# DUPLICATE VALIDATION
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

        if not url:
            continue

        normalized = (
            url
            .rstrip("/")
            .casefold()
        )

        if normalized in seen:
            duplicates.append(
                {
                    "url": url,
                    "first_index": seen[
                        normalized
                    ],
                    "duplicate_index": index,
                }
            )

        else:
            seen[
                normalized
            ] = index

    return duplicates


# =========================================================
# PRODUCT NAME DUPLICATE VALIDATION
# =========================================================

def find_duplicate_names(records):
    seen = {}
    duplicates = []

    for index, record in enumerate(
        records,
        start=1,
    ):
        name = str(
            record.get(
                "urun_adi",
                "",
            )
        ).strip()

        if not name:
            continue

        normalized = (
            name
            .casefold()
        )

        if normalized in seen:
            duplicates.append(
                {
                    "name": name,
                    "first_index": seen[
                        normalized
                    ],
                    "duplicate_index": index,
                }
            )

        else:
            seen[
                normalized
            ] = index

    return duplicates


# =========================================================
# MAIN
# =========================================================

def main():
    print()

    print(
        "=" * 118
    )

    print(
        "DÜNYA KATILIM - FINANCE + CAMPAIGN MERGE"
    )

    print(
        "=" * 118
    )

    print(
        "Processed directory:",
        PROCESSED_DIR,
    )

    print()

    # =====================================================
    # CAMPAIGN FILE
    # =====================================================

    if not CAMPAIGN_FILE.exists():
        print(
            "Campaign JSON bulunamadı ❌"
        )

        print(
            CAMPAIGN_FILE
        )

        sys.exit(
            1
        )

    # =====================================================
    # FINANCE FILE DISCOVERY
    # =====================================================

    try:
        finance_file = find_finance_file()

    except Exception as error:
        print(
            "Finance JSON discovery başarısız ❌"
        )

        print(
            error
        )

        sys.exit(
            1
        )

    print(
        "Finance:",
        finance_file,
    )

    print(
        "Campaign:",
        CAMPAIGN_FILE,
    )

    print(
        "Output:",
        OUTPUT_FILE,
    )

    print()

    # =====================================================
    # LOAD
    # =====================================================

    try:
        finance_records = load_json(
            finance_file
        )

        campaign_records = load_json(
            CAMPAIGN_FILE
        )

    except Exception as error:
        print(
            "JSON yükleme başarısız ❌"
        )

        print(
            error
        )

        sys.exit(
            1
        )

    print(
        "Finance kayıt:",
        len(
            finance_records
        ),
    )

    print(
        "Campaign kayıt:",
        len(
            campaign_records
        ),
    )

    # =====================================================
    # VALIDATE INPUTS
    # =====================================================

    finance_errors = validate_dataset(
        records=finance_records,
        expected_count=EXPECTED_FINANCE_COUNT,
        expected_type="finansman",
        source_name="FINANCE",
    )

    campaign_errors = validate_dataset(
        records=campaign_records,
        expected_count=EXPECTED_CAMPAIGN_COUNT,
        expected_type="kampanya",
        source_name="CAMPAIGN",
    )

    # =====================================================
    # MERGE
    # =====================================================

    merged_records = (
        finance_records
        +
        campaign_records
    )

    merge_errors = []

    # -----------------------------------------------------
    # TOTAL COUNT
    # -----------------------------------------------------

    if (
        len(
            merged_records
        )
        != EXPECTED_TOTAL_COUNT
    ):
        merge_errors.append(
            (
                "Final kayıt sayısı yanlış: "
                f"beklenen={EXPECTED_TOTAL_COUNT}, "
                f"actual={len(merged_records)}"
            )
        )

    # -----------------------------------------------------
    # COUNT BY TYPE
    # -----------------------------------------------------

    finance_count = sum(
        1
        for record in merged_records
        if record.get(
            "kayit_turu"
        )
        == "finansman"
    )

    campaign_count = sum(
        1
        for record in merged_records
        if record.get(
            "kayit_turu"
        )
        == "kampanya"
    )

    if (
        finance_count
        != EXPECTED_FINANCE_COUNT
    ):
        merge_errors.append(
            (
                "Merged finance sayısı yanlış: "
                f"{finance_count}"
            )
        )

    if (
        campaign_count
        != EXPECTED_CAMPAIGN_COUNT
    ):
        merge_errors.append(
            (
                "Merged campaign sayısı yanlış: "
                f"{campaign_count}"
            )
        )

    # -----------------------------------------------------
    # DUPLICATE URL
    # -----------------------------------------------------

    duplicate_urls = find_duplicate_urls(
        merged_records
    )

    if duplicate_urls:
        for duplicate in duplicate_urls:
            merge_errors.append(
                (
                    "Duplicate kaynak_url: "
                    f"{duplicate['url']} "
                    f"(index "
                    f"{duplicate['first_index']} "
                    "ve "
                    f"{duplicate['duplicate_index']})"
                )
            )

    # -----------------------------------------------------
    # DUPLICATE PRODUCT NAME
    #
    # Bu hard-error değil.
    # Aynı isimde farklı URL'ler teorik olarak olabilir.
    # Sadece raporlanır.
    # -----------------------------------------------------

    duplicate_names = find_duplicate_names(
        merged_records
    )

    # -----------------------------------------------------
    # ALL BANK CHECK
    # -----------------------------------------------------

    wrong_bank_count = sum(
        1
        for record in merged_records
        if record.get(
            "banka"
        )
        != BANK_NAME
    )

    if wrong_bank_count:
        merge_errors.append(
            (
                "Yanlış banka alanına sahip "
                f"kayıt sayısı: {wrong_bank_count}"
            )
        )

    # -----------------------------------------------------
    # FINAL SCHEMA CHECK
    # -----------------------------------------------------

    wrong_schema_count = sum(
        1
        for record in merged_records
        if list(
            record.keys()
        )
        != SCHEMA_KEYS
    )

    if wrong_schema_count:
        merge_errors.append(
            (
                "Final merged dataset içinde "
                "schema uyumsuz kayıt sayısı: "
                f"{wrong_schema_count}"
            )
        )

    # =====================================================
    # REPORT
    # =====================================================

    total_errors = (
        len(
            finance_errors
        )
        +
        len(
            campaign_errors
        )
        +
        len(
            merge_errors
        )
    )

    print()

    print(
        "=" * 118
    )

    print(
        "MERGE VALIDATION"
    )

    print(
        "=" * 118
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
        "Duplicate ürün adı:",
        len(
            duplicate_names
        ),
    )

    print(
        "Finance validation error:",
        len(
            finance_errors
        ),
    )

    print(
        "Campaign validation error:",
        len(
            campaign_errors
        ),
    )

    print(
        "Merge validation error:",
        len(
            merge_errors
        ),
    )

    print(
        "Toplam error:",
        total_errors,
    )

    # =====================================================
    # ERRORS
    # =====================================================

    if finance_errors:
        print()

        print(
            "FINANCE HATALARI:"
        )

        for error in finance_errors:
            print(
                "-",
                error,
            )

    if campaign_errors:
        print()

        print(
            "CAMPAIGN HATALARI:"
        )

        for error in campaign_errors:
            print(
                "-",
                error,
            )

    if merge_errors:
        print()

        print(
            "MERGE HATALARI:"
        )

        for error in merge_errors:
            print(
                "-",
                error,
            )

    # =====================================================
    # DUPLICATE NAME INFO
    # =====================================================

    if duplicate_names:
        print()

        print(
            "DUPLICATE ÜRÜN ADI BİLGİSİ:"
        )

        for duplicate in duplicate_names:
            print(
                (
                    "- "
                    f"{duplicate['name']} "
                    f"(index "
                    f"{duplicate['first_index']} "
                    "ve "
                    f"{duplicate['duplicate_index']})"
                )
            )

    # =====================================================
    # SAVE ONLY IF CLEAN
    # =====================================================

    print()

    if total_errors == 0:
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

        print(
            (
                "SONUÇ: DÜNYA KATILIM "
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
            (
                "Finance + Campaign "
                "kayıpsız birleştirildi ✅"
            )
        )

        print(
            (
                "18-key schema "
                "doğrulandı ✅"
            )
        )

        print(
            (
                "Duplicate kaynak_url "
                "bulunmadı ✅"
            )
        )

        print()

        print(
            "JSON:",
            OUTPUT_FILE,
        )

    else:
        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "MERGE BAŞARISIZ ❌"
            )
        )

        print(
            (
                "Hatalar düzeltilmeden "
                "dunya_katilim_all.json "
                "yazılmadı."
            )
        )

    print(
        "=" * 118
    )

    if total_errors:
        sys.exit(
            1
        )


if __name__ == "__main__":
    main()