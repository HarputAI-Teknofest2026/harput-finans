import json
import os


# =========================================================
# AYARLAR
# =========================================================

FINANCE_FILE = (
    "data/processed/"
    "hayat_finans_finansman_extracted.json"
)

CAMPAIGN_FILE = (
    "data/processed/"
    "hayat_finans_kampanya_extracted.json"
)

OUTPUT_FILE = (
    "data/processed/"
    "hayat_finans_all.json"
)

BANK_NAME = "Hayat Finans Katılım Bankası"

EXPECTED_FINANCE_COUNT = 3

EXPECTED_CAMPAIGN_COUNT = 11

EXPECTED_TOTAL_COUNT = (
    EXPECTED_FINANCE_COUNT
    + EXPECTED_CAMPAIGN_COUNT
)


# =========================================================
# STANDART ŞEMA
# =========================================================

EXPECTED_FIELDS = [
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


LIST_FIELDS = [
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


STRING_FIELDS = [
    "banka",
    "kayit_turu",
    "urun_adi",
    "urun_kategorisi",
    "kampanya_turu",
    "kampanya_suresi",
    "kaynak_url",
    "ham_metin",
]


# =========================================================
# NORMALİZASYON
# =========================================================

def normalize_text(value):
    value = str(value or "")

    value = value.replace("İ", "i")
    value = value.replace("I", "ı")

    value = value.replace("’", "'")
    value = value.replace("‘", "'")
    value = value.replace("´", "'")
    value = value.replace("`", "'")

    return " ".join(
        value.casefold().split()
    )


def normalize_url(value):
    return str(
        value or ""
    ).strip().rstrip("/").lower()


# =========================================================
# JSON OKUMA
# =========================================================

def load_json(path):

    if not os.path.exists(path):

        raise FileNotFoundError(
            f"Dosya bulunamadı: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)

    if not isinstance(
        data,
        list
    ):

        raise ValueError(
            (
                f"{path} içeriği LIST olmalı. "
                f"Gerçek tip: {type(data).__name__}"
            )
        )

    return data


# =========================================================
# DUPLICATE
# =========================================================

def find_duplicates(
    records,
    field
):

    seen = set()

    duplicates = []

    for record in records:

        value = record.get(
            field,
            ""
        )

        if field == "kaynak_url":

            key = normalize_url(
                value
            )

        else:

            key = normalize_text(
                value
            )

        if not key:
            continue

        if key in seen:

            duplicates.append(
                value
            )

        else:

            seen.add(
                key
            )

    return duplicates


# =========================================================
# ŞEMA KONTROLÜ
# =========================================================

def validate_schema(
    record,
    index
):

    errors = []

    title = record.get(
        "urun_adi",
        f"Kayıt {index}"
    )

    expected_set = set(
        EXPECTED_FIELDS
    )

    actual_set = set(
        record.keys()
    )

    missing_fields = (
        expected_set
        - actual_set
    )

    extra_fields = (
        actual_set
        - expected_set
    )

    if missing_fields:

        errors.append(
            (
                f"{title} -> "
                "eksik alanlar: "
                f"{sorted(missing_fields)}"
            )
        )

    if extra_fields:

        errors.append(
            (
                f"{title} -> "
                "fazladan alanlar: "
                f"{sorted(extra_fields)}"
            )
        )

    for field in LIST_FIELDS:

        if field not in record:
            continue

        if not isinstance(
            record[field],
            list
        ):

            errors.append(
                (
                    f"{title} -> "
                    f"{field} LIST değil."
                )
            )

    for field in STRING_FIELDS:

        if field not in record:
            continue

        if not isinstance(
            record[field],
            str
        ):

            errors.append(
                (
                    f"{title} -> "
                    f"{field} STRING değil."
                )
            )

    return errors


# =========================================================
# TEMEL KAYIT KONTROLÜ
# =========================================================

def validate_record(
    record,
    expected_type,
    index
):

    errors = []

    title = record.get(
        "urun_adi",
        f"Kayıt {index}"
    )

    errors.extend(
        validate_schema(
            record,
            index
        )
    )

    if (
        record.get(
            "banka"
        )
        != BANK_NAME
    ):

        errors.append(
            (
                f"{title} -> "
                "banka adı yanlış. "
                f"Gerçek={record.get('banka')}"
            )
        )

    if (
        record.get(
            "kayit_turu"
        )
        != expected_type
    ):

        errors.append(
            (
                f"{title} -> "
                "kayit_turu yanlış. "
                f"Beklenen={expected_type}, "
                f"Gerçek={record.get('kayit_turu')}"
            )
        )

    if not str(
        record.get(
            "urun_adi",
            ""
        )
    ).strip():

        errors.append(
            f"Kayıt {index} -> urun_adi boş."
        )

    if not str(
        record.get(
            "kaynak_url",
            ""
        )
    ).strip():

        errors.append(
            (
                f"{title} -> "
                "kaynak_url boş."
            )
        )

    if not str(
        record.get(
            "ham_metin",
            ""
        )
    ).strip():

        errors.append(
            (
                f"{title} -> "
                "ham_metin boş."
            )
        )

    return errors


# =========================================================
# FİNANSMAN KONTROLÜ
# =========================================================

def validate_finance_records(
    records
):

    errors = []

    if (
        len(records)
        != EXPECTED_FINANCE_COUNT
    ):

        errors.append(
            (
                "Finansman kayıt sayısı yanlış. "
                f"Beklenen={EXPECTED_FINANCE_COUNT}, "
                f"Gerçek={len(records)}"
            )
        )

    for index, record in enumerate(
        records,
        start=1
    ):

        errors.extend(
            validate_record(
                record=record,
                expected_type="finansman",
                index=index
            )
        )

    return errors


# =========================================================
# KAMPANYA KONTROLÜ
# =========================================================

def validate_campaign_records(
    records
):

    errors = []

    if (
        len(records)
        != EXPECTED_CAMPAIGN_COUNT
    ):

        errors.append(
            (
                "Kampanya kayıt sayısı yanlış. "
                f"Beklenen={EXPECTED_CAMPAIGN_COUNT}, "
                f"Gerçek={len(records)}"
            )
        )

    for index, record in enumerate(
        records,
        start=1
    ):

        errors.extend(
            validate_record(
                record=record,
                expected_type="kampanya",
                index=index
            )
        )

    return errors


# =========================================================
# MERGE SONRASI KONTROL
# =========================================================

def validate_merged(
    records
):

    errors = []

    if (
        len(records)
        != EXPECTED_TOTAL_COUNT
    ):

        errors.append(
            (
                "Merge toplam kayıt sayısı yanlış. "
                f"Beklenen={EXPECTED_TOTAL_COUNT}, "
                f"Gerçek={len(records)}"
            )
        )

    finance_count = sum(
        1
        for record in records
        if (
            record.get(
                "kayit_turu"
            )
            == "finansman"
        )
    )

    campaign_count = sum(
        1
        for record in records
        if (
            record.get(
                "kayit_turu"
            )
            == "kampanya"
        )
    )

    if (
        finance_count
        != EXPECTED_FINANCE_COUNT
    ):

        errors.append(
            (
                "Merge finansman dağılımı yanlış. "
                f"Beklenen={EXPECTED_FINANCE_COUNT}, "
                f"Gerçek={finance_count}"
            )
        )

    if (
        campaign_count
        != EXPECTED_CAMPAIGN_COUNT
    ):

        errors.append(
            (
                "Merge kampanya dağılımı yanlış. "
                f"Beklenen={EXPECTED_CAMPAIGN_COUNT}, "
                f"Gerçek={campaign_count}"
            )
        )

    duplicate_urls = find_duplicates(
        records,
        "kaynak_url"
    )

    duplicate_titles = find_duplicates(
        records,
        "urun_adi"
    )

    if duplicate_urls:

        errors.append(
            (
                "Duplicate URL bulundu: "
                f"{duplicate_urls}"
            )
        )

    if duplicate_titles:

        errors.append(
            (
                "Duplicate başlık bulundu: "
                f"{duplicate_titles}"
            )
        )

    return (
        errors,
        duplicate_urls,
        duplicate_titles,
        finance_count,
        campaign_count
    )


# =========================================================
# ANA PROGRAM
# =========================================================

def main():

    print()

    print(
        "=" * 118
    )

    print(
        "HAYAT FİNANS - FINANSMAN + KAMPANYA MERGE V1"
    )

    print(
        "=" * 118
    )

    print(
        "Finansman:",
        FINANCE_FILE
    )

    print(
        "Kampanya:",
        CAMPAIGN_FILE
    )

    print(
        "Output:",
        OUTPUT_FILE
    )

    # =====================================================
    # DOSYALARI OKU
    # =====================================================

    finance_records = load_json(
        FINANCE_FILE
    )

    campaign_records = load_json(
        CAMPAIGN_FILE
    )

    print()

    print(
        "[1/4] Dosyalar okundu."
    )

    print(
        "Finansman kayıt:",
        len(finance_records)
    )

    print(
        "Kampanya kayıt:",
        len(campaign_records)
    )

    # =====================================================
    # FİNANSMAN VALIDATION
    # =====================================================

    print()

    print(
        "[2/4] Finansman kayıtları kontrol ediliyor..."
    )

    finance_errors = (
        validate_finance_records(
            finance_records
        )
    )

    if finance_errors:

        print(
            "Finansman kontrol: BAŞARISIZ ❌"
        )

    else:

        print(
            "Finansman kontrol: TEMİZ ✅"
        )

    # =====================================================
    # KAMPANYA VALIDATION
    # =====================================================

    print()

    print(
        "[3/4] Kampanya kayıtları kontrol ediliyor..."
    )

    campaign_errors = (
        validate_campaign_records(
            campaign_records
        )
    )

    if campaign_errors:

        print(
            "Kampanya kontrol: BAŞARISIZ ❌"
        )

    else:

        print(
            "Kampanya kontrol: TEMİZ ✅"
        )

    # =====================================================
    # MERGE
    # =====================================================

    print()

    print(
        "[4/4] Kayıtlar birleştiriliyor..."
    )

    merged_records = (
        finance_records
        + campaign_records
    )

    (
        merge_errors,
        duplicate_urls,
        duplicate_titles,
        finance_count,
        campaign_count
    ) = validate_merged(
        merged_records
    )

    all_errors = (
        finance_errors
        + campaign_errors
        + merge_errors
    )

    # =====================================================
    # OUTPUT YAZ
    # =====================================================

    if not all_errors:

        os.makedirs(
            os.path.dirname(
                OUTPUT_FILE
            ),
            exist_ok=True
        )

        with open(
            OUTPUT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                merged_records,
                file,
                ensure_ascii=False,
                indent=4
            )

    # =====================================================
    # KAYITLARI RAPORLA
    # =====================================================

    print()

    print(
        "-" * 118
    )

    print(
        "FİNANSMAN KAYITLARI"
    )

    print(
        "-" * 118
    )

    for index, record in enumerate(
        finance_records,
        start=1
    ):

        print(
            f"{index}.",
            record.get(
                "urun_adi",
                ""
            )
        )

    print()

    print(
        "-" * 118
    )

    print(
        "KAMPANYA KAYITLARI"
    )

    print(
        "-" * 118
    )

    for index, record in enumerate(
        campaign_records,
        start=1
    ):

        print(
            f"{index}.",
            record.get(
                "urun_adi",
                ""
            )
        )

    # =====================================================
    # FINAL
    # =====================================================

    print()

    print(
        "=" * 118
    )

    print(
        "MERGE SONUCU"
    )

    print(
        "=" * 118
    )

    print(
        "Beklenen finansman:",
        EXPECTED_FINANCE_COUNT
    )

    print(
        "Gerçek finansman:",
        finance_count
    )

    print(
        "Beklenen kampanya:",
        EXPECTED_CAMPAIGN_COUNT
    )

    print(
        "Gerçek kampanya:",
        campaign_count
    )

    print(
        "Beklenen toplam:",
        EXPECTED_TOTAL_COUNT
    )

    print(
        "Gerçek toplam:",
        len(merged_records)
    )

    print(
        "Duplicate URL:",
        len(duplicate_urls)
    )

    print(
        "Duplicate başlık:",
        len(duplicate_titles)
    )

    print(
        "Error:",
        len(all_errors)
    )

    if all_errors:

        print()

        print(
            "HATALAR:"
        )

        for error in all_errors:

            print(
                "-",
                error
            )

    print()

    if not all_errors:

        print(
            (
                "SONUÇ: HAYAT FİNANS "
                "MERGE BAŞARILI ✅"
            )
        )

        print()

        print(
            "JSON:",
            OUTPUT_FILE
        )

    else:

        print(
            (
                "SONUÇ: HAYAT FİNANS "
                "MERGE BAŞARISIZ ❌"
            )
        )

        print()

        print(
            "Hata bulunduğu için final JSON yazılmadı."
        )

    print(
        "=" * 118
    )


if __name__ == "__main__":
    main()