import json
import os


# =========================================================
# DOSYALAR
# =========================================================

FINANCE_FILE = (
    "data/processed/"
    "turkiye_finans_finansman_extracted.json"
)

CAMPAIGN_FILE = (
    "data/processed/"
    "turkiye_finans_kampanya_extracted.json"
)

OUTPUT_FILE = (
    "data/processed/"
    "turkiye_finans_all.json"
)


BANK_NAME = "Türkiye Finans Katılım Bankası"


EXPECTED_FINANCE_COUNT = 16
EXPECTED_CAMPAIGN_COUNT = 15
EXPECTED_TOTAL_COUNT = 31


# =========================================================
# ORTAK ŞEMA
# =========================================================

REQUIRED_FIELDS = [
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
    "ham_metin"
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
    "kosullar"
]


STRING_FIELDS = [
    "banka",
    "kayit_turu",
    "urun_adi",
    "urun_kategorisi",
    "kampanya_turu",
    "kampanya_suresi",
    "kaynak_url",
    "ham_metin"
]


# =========================================================
# NORMALİZASYON
# =========================================================

def tr_lower(value):

    value = str(
        value or ""
    )

    value = value.replace(
        "İ",
        "i"
    )

    value = value.replace(
        "I",
        "ı"
    )

    value = value.casefold()

    value = value.replace(
        "\u0307",
        ""
    )

    return value


def normalize_text(value):

    return " ".join(
        str(
            value or ""
        ).split()
    )


def canonical_url(url):

    return (
        str(
            url or ""
        )
        .split("#", 1)[0]
        .split("?", 1)[0]
        .rstrip("/")
        .casefold()
    )


# =========================================================
# JSON OKU
# =========================================================

def load_json(path):

    if not os.path.exists(
        path
    ):

        raise FileNotFoundError(
            (
                "Dosya bulunamadı: "
                f"{path}"
            )
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(
            file
        )


# =========================================================
# RECORD LİSTESİ BUL
#
# Mevcut extractor formatımız "urunler".
# Yine de güvenli fallback bırakıyoruz.
# =========================================================

def get_records(data):

    possible_keys = [
        "urunler",
        "finansmanlar",
        "kampanyalar",
        "kayitlar"
    ]

    for key in possible_keys:

        value = data.get(
            key
        )

        if isinstance(
            value,
            list
        ):

            return value

    raise ValueError(
        (
            "JSON içinde kayıt listesi bulunamadı. "
            "Beklenen anahtarlardan biri: "
            + ", ".join(
                possible_keys
            )
        )
    )


# =========================================================
# ŞEMA KONTROLÜ
# =========================================================

def validate_record(
    record,
    expected_type
):

    missing_fields = [
        field

        for field
        in REQUIRED_FIELDS

        if field not in record
    ]

    if missing_fields:

        raise ValueError(
            (
                f"{record.get('urun_adi', 'Bilinmeyen')} "
                f"-> eksik alanlar: "
                f"{missing_fields}"
            )
        )

    extra_fields = [
        field

        for field
        in record.keys()

        if field not in REQUIRED_FIELDS
    ]

    if extra_fields:

        raise ValueError(
            (
                f"{record.get('urun_adi', 'Bilinmeyen')} "
                f"-> ortak şema dışında alan var: "
                f"{extra_fields}"
            )
        )

    for field in LIST_FIELDS:

        if not isinstance(
            record[field],
            list
        ):

            raise ValueError(
                (
                    f"{record['urun_adi']} "
                    f"-> {field} list değil."
                )
            )

    for field in STRING_FIELDS:

        if not isinstance(
            record[field],
            str
        ):

            raise ValueError(
                (
                    f"{record['urun_adi']} "
                    f"-> {field} string değil."
                )
            )

    if (
        record["banka"]
        != BANK_NAME
    ):

        raise ValueError(
            (
                f"{record['urun_adi']} "
                f"-> banka yanlış: "
                f"{record['banka']}"
            )
        )

    if (
        record["kayit_turu"]
        != expected_type
    ):

        raise ValueError(
            (
                f"{record['urun_adi']} "
                f"-> kayit_turu yanlış. "
                f"Beklenen: {expected_type}, "
                f"Gerçek: {record['kayit_turu']}"
            )
        )

    if not normalize_text(
        record["urun_adi"]
    ):

        raise ValueError(
            "urun_adi boş."
        )

    if not normalize_text(
        record["kaynak_url"]
    ):

        raise ValueError(
            (
                f"{record['urun_adi']} "
                "-> kaynak_url boş."
            )
        )

    if not normalize_text(
        record["ham_metin"]
    ):

        raise ValueError(
            (
                f"{record['urun_adi']} "
                "-> ham_metin boş."
            )
        )


# =========================================================
# TÜM KAYITLARI KONTROL ET
# =========================================================

def validate_records(
    records,
    expected_type
):

    for record in records:

        validate_record(
            record,
            expected_type
        )


# =========================================================
# DUPLICATE KONTROLÜ
# =========================================================

def find_duplicate_urls(records):

    duplicates = []

    seen = {}

    for record in records:

        key = canonical_url(
            record["kaynak_url"]
        )

        if key in seen:

            duplicates.append(
                {
                    "ilk_kayit": (
                        seen[key]
                    ),

                    "ikinci_kayit": (
                        record[
                            "urun_adi"
                        ]
                    ),

                    "url": (
                        record[
                            "kaynak_url"
                        ]
                    )
                }
            )

        else:

            seen[key] = (
                record[
                    "urun_adi"
                ]
            )

    return duplicates


def find_duplicate_titles(records):

    duplicates = []

    seen = {}

    for record in records:

        key = tr_lower(
            normalize_text(
                record[
                    "urun_adi"
                ]
            )
        )

        if key in seen:

            duplicates.append(
                {
                    "ilk_kayit": (
                        seen[key]
                    ),

                    "ikinci_kayit": (
                        record[
                            "urun_adi"
                        ]
                    )
                }
            )

        else:

            seen[key] = (
                record[
                    "urun_adi"
                ]
            )

    return duplicates


# =========================================================
# KAYIT TÜRÜ SAYILARI
# =========================================================

def count_record_types(records):

    result = {}

    for record in records:

        record_type = (
            record[
                "kayit_turu"
            ]
        )

        result[
            record_type
        ] = (
            result.get(
                record_type,
                0
            )
            + 1
        )

    return result


# =========================================================
# KATEGORİ SAYILARI
# =========================================================

def count_categories(records):

    result = {}

    for record in records:

        category = (
            record[
                "urun_kategorisi"
            ]
            or "Belirtilmemiş"
        )

        result[
            category
        ] = (
            result.get(
                category,
                0
            )
            + 1
        )

    return dict(
        sorted(
            result.items()
        )
    )


# =========================================================
# BOŞ ZORUNLU ALAN KONTROLÜ
#
# Liste alanlarının boş olması hata değildir.
# Kaynakta olmayan bilgi uydurulmamalıdır.
# =========================================================

def find_empty_core_fields(records):

    problems = []

    fields = [
        "banka",
        "kayit_turu",
        "urun_adi",
        "urun_kategorisi",
        "kaynak_url",
        "ham_metin"
    ]

    for record in records:

        for field in fields:

            if not normalize_text(
                record[
                    field
                ]
            ):

                problems.append(
                    {
                        "urun_adi": (
                            record.get(
                                "urun_adi",
                                ""
                            )
                        ),

                        "alan": (
                            field
                        )
                    }
                )

    return problems


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 100
    )

    print(
        "TÜRKİYE FİNANS MERGE"
    )

    print(
        "=" * 100
    )

    # =====================================================
    # DOSYALARI OKU
    # =====================================================

    finance_data = load_json(
        FINANCE_FILE
    )

    campaign_data = load_json(
        CAMPAIGN_FILE
    )

    finance_records = get_records(
        finance_data
    )

    campaign_records = get_records(
        campaign_data
    )

    print(
        "Finansman kayıt:",
        len(
            finance_records
        )
    )

    print(
        "Kampanya kayıt:",
        len(
            campaign_records
        )
    )

    # =====================================================
    # BANKA WRAPPER KONTROLÜ
    # =====================================================

    finance_bank = finance_data.get(
        "banka",
        BANK_NAME
    )

    campaign_bank = campaign_data.get(
        "banka",
        BANK_NAME
    )

    if (
        finance_bank
        != BANK_NAME
    ):

        raise ValueError(
            (
                "Finansman JSON banka adı yanlış: "
                f"{finance_bank}"
            )
        )

    if (
        campaign_bank
        != BANK_NAME
    ):

        raise ValueError(
            (
                "Kampanya JSON banka adı yanlış: "
                f"{campaign_bank}"
            )
        )

    # =====================================================
    # BEKLENEN SAYILAR
    # =====================================================

    if (
        len(
            finance_records
        )
        != EXPECTED_FINANCE_COUNT
    ):

        raise ValueError(
            (
                "Finansman kayıt sayısı beklenenden farklı. "
                f"Beklenen: {EXPECTED_FINANCE_COUNT}, "
                f"Gerçek: {len(finance_records)}"
            )
        )

    if (
        len(
            campaign_records
        )
        != EXPECTED_CAMPAIGN_COUNT
    ):

        raise ValueError(
            (
                "Kampanya kayıt sayısı beklenenden farklı. "
                f"Beklenen: {EXPECTED_CAMPAIGN_COUNT}, "
                f"Gerçek: {len(campaign_records)}"
            )
        )

    # =====================================================
    # ŞEMA
    # =====================================================

    print()

    print(
        "Finansman şema kontrolü..."
    )

    validate_records(
        finance_records,
        "finansman"
    )

    print(
        "Finansman şema: BAŞARILI ✅"
    )

    print()

    print(
        "Kampanya şema kontrolü..."
    )

    validate_records(
        campaign_records,
        "kampanya"
    )

    print(
        "Kampanya şema: BAŞARILI ✅"
    )

    # =====================================================
    # MERGE
    # =====================================================

    all_records = (
        finance_records
        + campaign_records
    )

    if (
        len(
            all_records
        )
        != EXPECTED_TOTAL_COUNT
    ):

        raise ValueError(
            (
                "Merge toplamı yanlış. "
                f"Beklenen: {EXPECTED_TOTAL_COUNT}, "
                f"Gerçek: {len(all_records)}"
            )
        )

    # =====================================================
    # DUPLICATE
    # =====================================================

    duplicate_urls = (
        find_duplicate_urls(
            all_records
        )
    )

    duplicate_titles = (
        find_duplicate_titles(
            all_records
        )
    )

    empty_core_fields = (
        find_empty_core_fields(
            all_records
        )
    )

    type_counts = count_record_types(
        all_records
    )

    category_counts = (
        count_categories(
            all_records
        )
    )

    # =====================================================
    # STRICT KONTROLLER
    # =====================================================

    finance_count = (
        type_counts.get(
            "finansman",
            0
        )
    )

    campaign_count = (
        type_counts.get(
            "kampanya",
            0
        )
    )

    if (
        finance_count
        != EXPECTED_FINANCE_COUNT
    ):

        raise ValueError(
            (
                "Merged finansman sayısı yanlış: "
                f"{finance_count}"
            )
        )

    if (
        campaign_count
        != EXPECTED_CAMPAIGN_COUNT
    ):

        raise ValueError(
            (
                "Merged kampanya sayısı yanlış: "
                f"{campaign_count}"
            )
        )

    if duplicate_urls:

        print()

        print(
            "DUPLICATE URL BULUNDU:"
        )

        for item in duplicate_urls:

            print(
                "-",
                item
            )

        raise ValueError(
            (
                "Duplicate URL bulundu. "
                "Merge kilitlenemez."
            )
        )

    if duplicate_titles:

        print()

        print(
            "DUPLICATE BAŞLIK BULUNDU:"
        )

        for item in duplicate_titles:

            print(
                "-",
                item
            )

        raise ValueError(
            (
                "Duplicate başlık bulundu. "
                "Merge kilitlenemez."
            )
        )

    if empty_core_fields:

        print()

        print(
            "BOŞ ZORUNLU ALAN BULUNDU:"
        )

        for item in empty_core_fields:

            print(
                "-",
                item
            )

        raise ValueError(
            (
                "Boş zorunlu alan bulundu. "
                "Merge kilitlenemez."
            )
        )

    # =====================================================
    # OUTPUT
    # =====================================================

    output = {
        "banka": (
            BANK_NAME
        ),

        "toplam_kayit": (
            len(
                all_records
            )
        ),

        "finansman_sayisi": (
            finance_count
        ),

        "kampanya_sayisi": (
            campaign_count
        ),

        "kayit_turu_sayilari": (
            type_counts
        ),

        "kategori_sayilari": (
            category_counts
        ),

        "urunler": (
            all_records
        )
    }

    os.makedirs(
        "data/processed",
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=4
        )

    # =====================================================
    # RAPOR
    # =====================================================

    print()

    print(
        "=" * 100
    )

    print(
        "MERGE SONUCU"
    )

    print(
        "=" * 100
    )

    print(
        "Finansman:",
        finance_count
    )

    print(
        "Kampanya:",
        campaign_count
    )

    print(
        "Toplam:",
        len(
            all_records
        )
    )

    print(
        "Duplicate URL:",
        len(
            duplicate_urls
        )
    )

    print(
        "Duplicate başlık:",
        len(
            duplicate_titles
        )
    )

    print(
        "Boş zorunlu alan:",
        len(
            empty_core_fields
        )
    )

    print()

    print(
        "KAYIT TÜRÜ DAĞILIMI:"
    )

    for (
        record_type,
        count
    ) in type_counts.items():

        print(
            (
                f"- "
                f"{record_type}: "
                f"{count}"
            )
        )

    print()

    print(
        "KATEGORİ DAĞILIMI:"
    )

    for (
        category,
        count
    ) in category_counts.items():

        print(
            (
                f"- "
                f"{category}: "
                f"{count}"
            )
        )

    print()

    print(
        "=" * 100
    )

    if (
        len(
            all_records
        )
        == EXPECTED_TOTAL_COUNT

        and finance_count
        == EXPECTED_FINANCE_COUNT

        and campaign_count
        == EXPECTED_CAMPAIGN_COUNT

        and len(
            duplicate_urls
        )
        == 0

        and len(
            duplicate_titles
        )
        == 0

        and len(
            empty_core_fields
        )
        == 0
    ):

        print(
            "SONUÇ: TÜRKİYE FİNANS MERGE BAŞARILI ✅"
        )

    else:

        print(
            "SONUÇ: MERGE KONTROL GEREKİYOR ⚠️"
        )

    print(
        "JSON:",
        OUTPUT_FILE
    )

    print(
        "=" * 100
    )


if __name__ == "__main__":

    main()