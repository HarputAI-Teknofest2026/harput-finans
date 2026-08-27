import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FILE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "turkiye_finans_all.json"
)


EXTRA_LIMIT = "eXtra Limit"

MOBILE_CAMPAIGN = (
    "Mobilden Türkiye Finanslı Ol, "
    "Kâr Paysız 50.000 TL'ye Varan "
    "İhtiyaç Finansmanını Kaçırma!"
)


def main():

    with open(
        FILE_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError(
            "turkiye_finans_all.json root list olmalı."
        )

    found_extra = False
    found_mobile = False

    for record in records:

        name = record.get(
            "urun_adi",
            "",
        )

        # ============================================================
        # 1. eXtra Limit
        # ============================================================

        if name == EXTRA_LIMIT:

            record["taksit_sayisi"] = [
                "3",
                "6",
                "12",
                "36",
            ]

            found_extra = True

        # ============================================================
        # 2. %0 MOBİL MÜŞTERİ KAMPANYASI
        # ============================================================

        elif name == MOBILE_CAMPAIGN:

            record["kar_payi_orani"] = [
                "%0"
            ]

            record["finansman_tutari"] = [
                "50.000 TL"
            ]

            record["vade"] = [
                "3 ay"
            ]

            found_mobile = True

    if not found_extra:
        raise ValueError(
            "eXtra Limit kaydı bulunamadı."
        )

    if not found_mobile:
        raise ValueError(
            "Mobil %0 kampanya kaydı bulunamadı."
        )

    with open(
        FILE_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2,
        )

    # ================================================================
    # RE-READ
    # ================================================================

    with open(
        FILE_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        saved = json.load(file)

    extra = next(
        record
        for record in saved
        if record.get("urun_adi") == EXTRA_LIMIT
    )

    mobile = next(
        record
        for record in saved
        if record.get("urun_adi") == MOBILE_CAMPAIGN
    )

    if extra["taksit_sayisi"] != [
        "3",
        "6",
        "12",
        "36",
    ]:
        raise ValueError(
            "eXtra Limit taksit fix başarısız."
        )

    if mobile["kar_payi_orani"] != [
        "%0"
    ]:
        raise ValueError(
            "Mobil kampanya kâr payı fix başarısız."
        )

    if mobile["finansman_tutari"] != [
        "50.000 TL"
    ]:
        raise ValueError(
            "Mobil kampanya tutar fix başarısız."
        )

    if mobile["vade"] != [
        "3 ay"
    ]:
        raise ValueError(
            "Mobil kampanya vade fix başarısız."
        )

    print()
    print("=" * 100)
    print("TÜRKİYE FİNANS - SEMANTIC RESIDUAL FIX")
    print("=" * 100)

    print("✅ eXtra Limit")
    print(
        "   Taksit:",
        extra["taksit_sayisi"],
    )

    print()
    print("✅ Mobil %0 İhtiyaç Finansmanı Kampanyası")
    print(
        "   Kâr Payı:",
        mobile["kar_payi_orani"],
    )
    print(
        "   Tutar   :",
        mobile["finansman_tutari"],
    )
    print(
        "   Vade    :",
        mobile["vade"],
    )

    print()
    print(
        f"Toplam kayıt: {len(saved)}"
    )

    print(
        f"Dosya: {FILE_PATH}"
    )

    print("=" * 100)
    print("FIX BAŞARILI ✅")
    print("=" * 100)


if __name__ == "__main__":
    main()
