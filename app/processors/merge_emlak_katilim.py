import json
import os


FINANCE_FILE = (
    "data/processed/"
    "emlak_katilim_finansman_extracted.json"
)

CAMPAIGN_FILE = (
    "data/processed/"
    "emlak_katilim_kampanya_extracted.json"
)

OUTPUT_FILE = (
    "data/processed/"
    "emlak_katilim_all.json"
)


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


# =========================================================
# JSON OKU
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

        return json.load(
            file
        )


# =========================================================
# KAYIT LİSTESİNİ BUL
#
# Finansman JSON'unun üst yapısı ile kampanya JSON'unun
# üst yapısı farklı olsa bile kayıtları bulabilsin.
# =========================================================

def get_records(data):

    # JSON direkt listeyse
    if isinstance(
        data,
        list
    ):
        return data


    if not isinstance(
        data,
        dict
    ):
        raise ValueError(
            "JSON yapısı geçersiz."
        )


    possible_keys = [
        "kayitlar",
        "urunler",
        "finansmanlar",
        "kampanyalar",
        "products",
        "records"
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
        "JSON içerisinde kayıt listesi bulunamadı."
    )


# =========================================================
# ŞEMA KONTROLÜ
# =========================================================

def validate_record(
    record,
    index,
    source_name
):

    if not isinstance(
        record,
        dict
    ):
        raise ValueError(
            f"{source_name} "
            f"{index}. kayıt dict değil."
        )


    missing_fields = []

    for field in REQUIRED_FIELDS:

        if field not in record:

            missing_fields.append(
                field
            )


    if missing_fields:

        raise ValueError(
            f"{source_name} "
            f"{index}. kayıtta eksik alanlar var: "
            f"{missing_fields}"
        )


# =========================================================
# KAYIT TÜRÜ KONTROLÜ
# =========================================================

def validate_record_type(
    record,
    expected_type,
    index
):

    record_type = record.get(
        "kayit_turu",
        ""
    )


    if record_type != expected_type:

        print(
            "UYARI:"
        )

        print(
            f"  Kayıt: {index}"
        )

        print(
            f"  Beklenen tür: {expected_type}"
        )

        print(
            f"  Gelen tür: {record_type}"
        )

        print(
            f"  Ürün: {record.get('urun_adi', '')}"
        )

        print()


# =========================================================
# DUPLICATE KONTROLÜ
# =========================================================

def find_duplicates(records):

    seen = set()

    duplicates = []


    for record in records:

        key = (
            record.get(
                "kayit_turu",
                ""
            ),
            record.get(
                "urun_adi",
                ""
            ),
            record.get(
                "kaynak_url",
                ""
            )
        )


        if key in seen:

            duplicates.append(
                record
            )

        else:

            seen.add(
                key
            )


    return duplicates


# =========================================================
# MAIN
# =========================================================

def main():

    # -----------------------------------------------------
    # DOSYALARI OKU
    # -----------------------------------------------------

    finance_data = load_json(
        FINANCE_FILE
    )

    campaign_data = load_json(
        CAMPAIGN_FILE
    )


    # -----------------------------------------------------
    # KAYITLARI ÇIKAR
    # -----------------------------------------------------

    finance_records = get_records(
        finance_data
    )

    campaign_records = get_records(
        campaign_data
    )


    print()

    print(
        "========================================="
    )

    print(
        "EMLAK KATILIM DATASET BİRLEŞTİRME"
    )

    print(
        "========================================="
    )

    print()

    print(
        f"Finansman kaydı: "
        f"{len(finance_records)}"
    )

    print(
        f"Kampanya kaydı: "
        f"{len(campaign_records)}"
    )

    print()


    # -----------------------------------------------------
    # ŞEMA KONTROLÜ
    # -----------------------------------------------------

    print(
        "Şema kontrol ediliyor..."
    )


    for index, record in enumerate(
        finance_records,
        start=1
    ):

        validate_record(
            record,
            index,
            "Finansman"
        )

        validate_record_type(
            record,
            "finansman",
            index
        )


    for index, record in enumerate(
        campaign_records,
        start=1
    ):

        validate_record(
            record,
            index,
            "Kampanya"
        )

        validate_record_type(
            record,
            "kampanya",
            index
        )


    print(
        "Şema kontrolü başarılı."
    )

    print()


    # -----------------------------------------------------
    # BİRLEŞTİR
    # -----------------------------------------------------

    all_records = (
        finance_records
        + campaign_records
    )


    # -----------------------------------------------------
    # DUPLICATE KONTROLÜ
    # -----------------------------------------------------

    duplicates = find_duplicates(
        all_records
    )


    print(
        f"Duplicate kayıt: "
        f"{len(duplicates)}"
    )


    if duplicates:

        print()

        print(
            "Duplicate bulunan kayıtlar:"
        )

        for duplicate in duplicates:

            print(
                "-",
                duplicate.get(
                    "urun_adi",
                    ""
                )
            )

            print(
                " ",
                duplicate.get(
                    "kaynak_url",
                    ""
                )
            )

        print()


    # -----------------------------------------------------
    # ÇIKTI
    # -----------------------------------------------------

    output_data = {

        "banka": (
            "Türkiye Emlak Katılım Bankası"
        ),

        "toplam_kayit": len(
            all_records
        ),

        "finansman_sayisi": len(
            finance_records
        ),

        "kampanya_sayisi": len(
            campaign_records
        ),

        "kayitlar": all_records
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
            output_data,
            file,
            ensure_ascii=False,
            indent=4
        )


    # -----------------------------------------------------
    # SONUÇ
    # -----------------------------------------------------

    print()

    print(
        "========================================="
    )

    print(
        f"Finansman: "
        f"{len(finance_records)}"
    )

    print(
        f"Kampanya: "
        f"{len(campaign_records)}"
    )

    print(
        f"Toplam: "
        f"{len(all_records)}"
    )

    print(
        f"Duplicate: "
        f"{len(duplicates)}"
    )

    print()

    print(
        f"JSON kaydedildi: "
        f"{OUTPUT_FILE}"
    )

    print(
        "========================================="
    )


if __name__ == "__main__":
    main()