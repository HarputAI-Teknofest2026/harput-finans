import json
import sys
from pathlib import Path


# =========================================================
# CONFIG
# =========================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT
    / "data"
    / "raw"
    / "adil_katilim_finansmanlar.json"
)

OUTPUT_FILE = (
    ROOT
    / "data"
    / "processed"
    / "adil_katilim_finansman_extracted.json"
)

BANK_NAME = "Adil Katılım Bankası A.Ş."

EXPECTED_COUNT = 1


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

    if not isinstance(
        data,
        list,
    ):
        raise ValueError(
            "RAW JSON root yapısı list değil."
        )

    return data


# =========================================================
# EXTRACT
# =========================================================

def extract_record(raw):
    if (
        raw.get("urun_adi")
        != "Bireysel Finansman"
    ):
        raise ValueError(
            (
                "Beklenmeyen ürün: "
                f"{raw.get('urun_adi')}"
            )
        )

    return {
        "banka": BANK_NAME,

        "kayit_turu": "finansman",

        "urun_adi": "Bireysel Finansman",

        "urun_kategorisi": (
            "Bireysel Finansman"
        ),

        # Kaynak sayfada sayısal
        # kâr payı oranı verilmemiş.
        "kar_payi_orani": [],

        # Kaynak sayfada finansman
        # oranı belirtilmemiş.
        "finansman_orani": [],

        # Kaynak sayfada tutar
        # bilgisi belirtilmemiş.
        "finansman_tutari": [],

        # Kaynak sayfada vade
        # bilgisi belirtilmemiş.
        "vade": [],

        # Kaynak sayfada taksit
        # sayısı belirtilmemiş.
        "taksit_sayisi": [],

        # Kaynak sayfada açık bir
        # ücret/masraf bilgisi yok.
        "masraf_bilgisi": [],

        "kampanya_turu": "",

        "kampanya_avantaji": [],

        "kampanya_suresi": "",

        "hedef_kitle": [
            "Bireysel müşteriler"
        ],

        # Para birimi kaynak metinde
        # açıkça belirtilmediği için boş.
        "para_birimi": [],

        "kosullar": [
            (
                "Finansmana konu ürün veya "
                "hizmet katılım esaslarına "
                "uygun olmalıdır."
            ),
            (
                "Müşterinin talep ettiği ürün "
                "veya hizmet banka tarafından "
                "satın alınır ve üzerine kâr "
                "eklenerek vadeli olarak "
                "müşteriye satılır."
            ),
        ],

        "kaynak_url": raw[
            "kaynak_url"
        ],

        "ham_metin": raw[
            "ham_metin"
        ],
    }


# =========================================================
# VALIDATION
# =========================================================

def validate_record(
    record,
    index,
):
    errors = []

    prefix = f"[{index}]"

    # -----------------------------------------------------
    # SCHEMA
    # -----------------------------------------------------

    if list(
        record.keys()
    ) != SCHEMA_KEYS:
        errors.append(
            (
                f"{prefix} "
                "18-key schema/order hatalı."
            )
        )

    # -----------------------------------------------------
    # BANK
    # -----------------------------------------------------

    if (
        record.get("banka")
        != BANK_NAME
    ):
        errors.append(
            (
                f"{prefix} "
                "banka alanı hatalı."
            )
        )

    # -----------------------------------------------------
    # TYPE
    # -----------------------------------------------------

    if (
        record.get("kayit_turu")
        != "finansman"
    ):
        errors.append(
            (
                f"{prefix} "
                "kayit_turu finansman değil."
            )
        )

    # -----------------------------------------------------
    # PRODUCT
    # -----------------------------------------------------

    if (
        record.get("urun_adi")
        != "Bireysel Finansman"
    ):
        errors.append(
            (
                f"{prefix} "
                "ürün adı hatalı."
            )
        )

    # -----------------------------------------------------
    # LIST TYPES
    # -----------------------------------------------------

    for field in LIST_FIELDS:
        if not isinstance(
            record.get(field),
            list,
        ):
            errors.append(
                (
                    f"{prefix} "
                    f"{field} list değil."
                )
            )

    # -----------------------------------------------------
    # REQUIRED TEXT
    # -----------------------------------------------------

    for field in (
        "banka",
        "kayit_turu",
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
                    f"{prefix} "
                    f"{field} boş."
                )
            )

    # -----------------------------------------------------
    # SOURCE SEMANTIC CHECKS
    # -----------------------------------------------------

    raw_text = (
        record.get(
            "ham_metin",
            ""
        )
        .casefold()
    )

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
                    f"{prefix} "
                    "ham_metin içinde "
                    f"beklenen ifade yok: {marker}"
                )
            )

    # Ticari ürün kesinlikle karışmamalı.
    if (
        "ticari finansman"
        in raw_text
    ):
        errors.append(
            (
                f"{prefix} "
                "Ticari Finansman metni bulundu."
            )
        )

    # -----------------------------------------------------
    # NO INVENTED NUMERIC DATA
    # -----------------------------------------------------

    must_be_empty = [
        "kar_payi_orani",
        "finansman_orani",
        "finansman_tutari",
        "vade",
        "taksit_sayisi",
        "masraf_bilgisi",
        "para_birimi",
    ]

    for field in must_be_empty:
        if record.get(
            field
        ) != []:
            errors.append(
                (
                    f"{prefix} "
                    f"{field} kaynakta yokken "
                    "doldurulmuş."
                )
            )

    # -----------------------------------------------------
    # CAMPAIGN FIELDS
    # -----------------------------------------------------

    if (
        record.get(
            "kampanya_turu"
        )
        != ""
    ):
        errors.append(
            (
                f"{prefix} "
                "kampanya_turu boş değil."
            )
        )

    if (
        record.get(
            "kampanya_avantaji"
        )
        != []
    ):
        errors.append(
            (
                f"{prefix} "
                "kampanya_avantaji boş değil."
            )
        )

    if (
        record.get(
            "kampanya_suresi"
        )
        != ""
    ):
        errors.append(
            (
                f"{prefix} "
                "kampanya_suresi boş değil."
            )
        )

    return errors


# =========================================================
# MAIN
# =========================================================

def main():
    print()

    print(
        "=" * 120
    )

    print(
        "ADİL KATILIM - FINANCE EXTRACTOR V1"
    )

    print(
        "=" * 120
    )

    print(
        "Input:",
        INPUT_FILE,
    )

    print(
        "Output:",
        OUTPUT_FILE,
    )

    print()

    # =====================================================
    # LOAD
    # =====================================================

    if not INPUT_FILE.exists():
        print(
            "RAW dosya bulunamadı ❌"
        )

        sys.exit(1)

    raw_records = load_json(
        INPUT_FILE
    )

    print(
        "RAW kayıt:",
        len(
            raw_records
        ),
    )

    if (
        len(raw_records)
        != EXPECTED_COUNT
    ):
        print(
            (
                "Beklenen RAW kayıt sayısı "
                f"{EXPECTED_COUNT}, "
                f"gelen {len(raw_records)} ❌"
            )
        )

        sys.exit(1)

    # =====================================================
    # EXTRACTION
    # =====================================================

    extracted_records = []

    extraction_errors = []

    for index, raw in enumerate(
        raw_records,
        start=1,
    ):
        try:
            record = extract_record(
                raw
            )

            extracted_records.append(
                record
            )

            print(
                (
                    f"[{index}/{len(raw_records)}] "
                    f"{record['urun_adi']} ✅"
                )
            )

        except Exception as error:
            extraction_errors.append(
                (
                    f"[{index}] "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

    # =====================================================
    # VALIDATION
    # =====================================================

    validation_errors = []

    for index, record in enumerate(
        extracted_records,
        start=1,
    ):
        validation_errors.extend(
            validate_record(
                record,
                index,
            )
        )

    total_errors = (
        len(extraction_errors)
        +
        len(validation_errors)
    )

    print()

    print(
        "=" * 120
    )

    print(
        "EXTRACTION VALIDATION"
    )

    print(
        "=" * 120
    )

    print(
        "Beklenen:",
        EXPECTED_COUNT,
    )

    print(
        "RAW:",
        len(
            raw_records
        ),
    )

    print(
        "Extracted:",
        len(
            extracted_records
        ),
    )

    print(
        "Extraction error:",
        len(
            extraction_errors
        ),
    )

    print(
        "Schema/Semantic error:",
        len(
            validation_errors
        ),
    )

    print(
        "Toplam error:",
        total_errors,
    )

    if extraction_errors:
        print()

        print(
            "EXTRACTION ERRORS:"
        )

        for error in extraction_errors:
            print(
                "-",
                error,
            )

    if validation_errors:
        print()

        print(
            "VALIDATION ERRORS:"
        )

        for error in validation_errors:
            print(
                "-",
                error,
            )

    if total_errors:
        print()

        print(
            (
                "SONUÇ: ADİL KATILIM "
                "FINANCE EXTRACTION "
                "BAŞARISIZ ❌"
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
            extracted_records,
            file,
            ensure_ascii=False,
            indent=4,
        )

    print()

    print(
        (
            "SONUÇ: ADİL KATILIM "
            "FINANCE EXTRACTION "
            "BAŞARILI ✅"
        )
    )

    print(
        (
            "1 bireysel finansman "
            "18-key final schema'ya "
            "dönüştürüldü ✅"
        )
    )

    print(
        (
            "Kaynakta bulunmayan sayısal "
            "alanlar boş bırakıldı ✅"
        )
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
            "EXTRACTOR ERROR ❌"
        )

        print(
            (
                f"{type(error).__name__}: "
                f"{error}"
            )
        )

        sys.exit(1)