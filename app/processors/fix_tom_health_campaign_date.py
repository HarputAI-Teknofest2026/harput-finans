import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

FILE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "tom_katilim_all.json"
)

TARGET_NAME = (
    "Hadi Taksitli Sağlık Kredisi "
    "sağlık harcamalarında da yanında!"
)

CORRECT_DATE = "31 Aralık 2026"


def main():

    print("=" * 100)
    print("T.O.M. KATILIM - HEALTH CAMPAIGN DATE FIX")
    print("=" * 100)

    if not FILE_PATH.exists():
        raise FileNotFoundError(
            f"Dosya bulunamadı: {FILE_PATH}"
        )

    with open(
        FILE_PATH,
        "r",
        encoding="utf-8",
    ) as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError("JSON root list olmalı.")

    found = False

    for record in records:

        if record.get("urun_adi") == TARGET_NAME:

            print(f"Bulundu : {TARGET_NAME}")
            print(
                "Eski süre:",
                repr(record.get("kampanya_suresi", ""))
            )

            record["kampanya_suresi"] = CORRECT_DATE

            print(
                "Yeni süre:",
                repr(record["kampanya_suresi"])
            )

            found = True
            break

    if not found:
        raise ValueError(
            "Hedef kampanya bulunamadı."
        )

    with open(
        FILE_PATH,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            records,
            f,
            ensure_ascii=False,
            indent=2,
        )

    # Son kontrol
    with open(
        FILE_PATH,
        "r",
        encoding="utf-8",
    ) as f:
        check_records = json.load(f)

    target = next(
        (
            r for r in check_records
            if r.get("urun_adi") == TARGET_NAME
        ),
        None,
    )

    if target is None:
        raise ValueError(
            "Kaydetme sonrası hedef kayıt bulunamadı."
        )

    if target.get("kampanya_suresi") != CORRECT_DATE:
        raise ValueError(
            "Kampanya süresi doğru kaydedilemedi."
        )

    print()
    print("=" * 100)
    print("FIX BAŞARILI ✅")
    print("=" * 100)

    print(
        f"Kampanya süresi: "
        f"{target['kampanya_suresi']}"
    )

    print(
        f"Dosya: {FILE_PATH}"
    )

    print(
        f"Toplam kayıt: {len(check_records)}"
    )

    print("=" * 100)


if __name__ == "__main__":
    main()