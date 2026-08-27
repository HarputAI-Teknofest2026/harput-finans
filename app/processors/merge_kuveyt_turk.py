import json
import os


FINANCE_FILE = (
    "data/processed/"
    "kuveyt_turk_finansman_extracted.json"
)

CAMPAIGN_FILE = (
    "data/processed/"
    "kuveyt_turk_kampanya_extracted.json"
)

OUTPUT_FILE = (
    "data/processed/"
    "kuveyt_turk_all.json"
)


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
# JSON OKU
# =========================================================

def load_json(path):

    if not os.path.exists(
        path
    ):

        raise FileNotFoundError(
            f"Dosya bulunamadı: {path}"
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
# ŞEMA KONTROLÜ
# =========================================================

def validate_record(
    record,
    index,
    expected_type
):

    missing = [
        field

        for field
        in REQUIRED_FIELDS

        if field not in record
    ]


    if missing:

        raise ValueError(
            (
                f"{expected_type} "
                f"{index}. kayıtta "
                f"eksik alanlar var: "
                f"{missing}"
            )
        )


    # =====================================================
    # KAYIT TÜRÜ
    # =====================================================

    if (
        record[
            "kayit_turu"
        ]
        != expected_type
    ):

        raise ValueError(
            (
                f"{index}. kayıt türü hatalı. "
                f"Beklenen: {expected_type}, "
                f"Gelen: "
                f"{record['kayit_turu']}"
            )
        )


    # =====================================================
    # BANKA
    # =====================================================

    if (
        record[
            "banka"
        ]
        != "Kuveyt Türk Katılım Bankası"
    ):

        raise ValueError(
            (
                f"{index}. kayıtta banka "
                f"adı hatalı: "
                f"{record['banka']}"
            )
        )


    # =====================================================
    # LIST ALANLAR
    # =====================================================

    for field in LIST_FIELDS:

        if not isinstance(
            record[
                field
            ],
            list
        ):

            raise ValueError(
                (
                    f"{expected_type} "
                    f"{index}. kayıt -> "
                    f"{field} list değil."
                )
            )


    # =====================================================
    # STRING ALANLAR
    # =====================================================

    for field in STRING_FIELDS:

        if not isinstance(
            record[
                field
            ],
            str
        ):

            raise ValueError(
                (
                    f"{expected_type} "
                    f"{index}. kayıt -> "
                    f"{field} string değil."
                )
            )


    # =====================================================
    # TEMEL ZORUNLU DEĞERLER
    # =====================================================

    if not record[
        "urun_adi"
    ].strip():

        raise ValueError(
            (
                f"{expected_type} "
                f"{index}. kayıtta "
                f"ürün adı boş."
            )
        )


    if not record[
        "kaynak_url"
    ].strip():

        raise ValueError(
            (
                f"{expected_type} "
                f"{index}. kayıtta "
                f"kaynak URL boş."
            )
        )


    if not record[
        "ham_metin"
    ].strip():

        raise ValueError(
            (
                f"{expected_type} "
                f"{index}. kayıtta "
                f"ham metin boş."
            )
        )


# =========================================================
# TÜM KAYITLARI KONTROL ET
# =========================================================

def validate_records(
    records,
    expected_type
):

    for index, record in enumerate(
        records,
        start=1
    ):

        validate_record(
            record,
            index,
            expected_type
        )


# =========================================================
# DUPLICATE KONTROLÜ
# =========================================================

def find_duplicates(records):

    duplicate_urls = []

    duplicate_records = []

    seen_urls = set()

    seen_records = set()


    for record in records:

        url = record[
            "kaynak_url"
        ].strip()


        if url in seen_urls:

            duplicate_urls.append(
                url
            )

        else:

            seen_urls.add(
                url
            )


        record_key = (
            record[
                "banka"
            ].strip(),

            record[
                "kayit_turu"
            ].strip(),

            record[
                "urun_adi"
            ].strip(),

            record[
                "kaynak_url"
            ].strip()
        )


        if record_key in seen_records:

            duplicate_records.append(
                (
                    record[
                        "urun_adi"
                    ],
                    record[
                        "kaynak_url"
                    ]
                )
            )

        else:

            seen_records.add(
                record_key
            )


    return (
        duplicate_urls,
        duplicate_records
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 75
    )

    print(
        "KUVEYT TÜRK DATASET BİRLEŞTİRME"
    )

    print(
        "=" * 75
    )


    # =====================================================
    # JSON DOSYALARINI OKU
    # =====================================================

    finance_data = load_json(
        FINANCE_FILE
    )


    campaign_data = load_json(
        CAMPAIGN_FILE
    )


    # =====================================================
    # KAYITLARI AL
    # =====================================================

    finance_records = (
        finance_data.get(
            "urunler",
            []
        )
    )


    campaign_records = (
        campaign_data.get(
            "kampanyalar",
            []
        )
    )


    print()

    print(
        "Finansman kaydı:",
        len(
            finance_records
        )
    )


    print(
        "Kampanya kaydı:",
        len(
            campaign_records
        )
    )


    # =====================================================
    # BEKLENEN SAYILAR
    # =====================================================

    if len(
        finance_records
    ) != 30:

        raise ValueError(
            (
                "Finansman kayıt sayısı "
                f"30 değil: "
                f"{len(finance_records)}"
            )
        )


    if len(
        campaign_records
    ) != 74:

        raise ValueError(
            (
                "Kampanya kayıt sayısı "
                f"74 değil: "
                f"{len(campaign_records)}"
            )
        )


    # =====================================================
    # ŞEMA KONTROLÜ
    # =====================================================

    validate_records(
        finance_records,
        "finansman"
    )


    validate_records(
        campaign_records,
        "kampanya"
    )


    print(
        "Şema kontrolü başarılı."
    )


    # =====================================================
    # BİRLEŞTİR
    # =====================================================

    all_records = (
        finance_records
        + campaign_records
    )


    # =====================================================
    # DUPLICATE
    # =====================================================

    (
        duplicate_urls,
        duplicate_records
    ) = find_duplicates(
        all_records
    )


    if duplicate_urls:

        print()

        print(
            "UYARI - DUPLICATE URL:"
        )


        for url in duplicate_urls:

            print(
                "-",
                url
            )


    if duplicate_records:

        print()

        print(
            "UYARI - DUPLICATE KAYIT:"
        )


        for (
            title,
            url
        ) in duplicate_records:

            print(
                "-",
                title
            )

            print(
                " ",
                url
            )


    # =====================================================
    # TÜR SAYILARI
    # =====================================================

    finance_count = sum(
        1

        for record
        in all_records

        if (
            record[
                "kayit_turu"
            ]
            == "finansman"
        )
    )


    campaign_count = sum(
        1

        for record
        in all_records

        if (
            record[
                "kayit_turu"
            ]
            == "kampanya"
        )
    )


    # =====================================================
    # SON ŞEMA KONTROLÜ
    # =====================================================

    for index, record in enumerate(
        all_records,
        start=1
    ):

        missing = [
            field

            for field
            in REQUIRED_FIELDS

            if field
            not in record
        ]


        if missing:

            raise ValueError(
                (
                    f"Birleşik dataset "
                    f"{index}. kayıt "
                    f"eksik alanlar: "
                    f"{missing}"
                )
            )


    # =====================================================
    # OUTPUT
    # =====================================================

    output = {

        "banka": (
            "Kuveyt Türk Katılım Bankası"
        ),

        "toplam_kayit": len(
            all_records
        ),

        "finansman_sayisi": (
            finance_count
        ),

        "kampanya_sayisi": (
            campaign_count
        ),

        "kayitlar": (
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
    # FINAL RAPOR
    # =====================================================

    print()

    print(
        "=" * 75
    )

    print(
        "BİRLEŞTİRME TAMAMLANDI"
    )

    print(
        "=" * 75
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
        "Duplicate kayıt:",
        len(
            duplicate_records
        )
    )


    print(
        "Şema kontrolü: BAŞARILI"
    )


    print(
        "JSON:",
        OUTPUT_FILE
    )


    print(
        "=" * 75
    )


if __name__ == "__main__":

    main()