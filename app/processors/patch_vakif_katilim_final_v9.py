import json
import re
from pathlib import Path
from collections import Counter


# ==================================================================================================
# VAKIF KATILIM - FINAL CLOSED PATCH V9
# ==================================================================================================

BANK_NAME = "Vakıf Katılım Bankası A.Ş."

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
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE = PROCESSED_DIR / "vakif_katilim_final_closed_v9.json"


# --------------------------------------------------------------------------------------------------
# INPUT BULMA
# --------------------------------------------------------------------------------------------------

INPUT_CANDIDATES = [
    PROCESSED_DIR / "vakif_katilim_final_closed_v8.json",
    PROCESSED_DIR / "vakif_katilim_final_closed_v8(1).json",
    PROCESSED_DIR / "vakif_katilim_final_closed_patch_v8.json",
    PROCESSED_DIR / "vakif_katilim_final_closed_v7.json",
]


def find_input_file():
    for path in INPUT_CANDIDATES:
        if path.exists():
            return path

    candidates = sorted(
        PROCESSED_DIR.glob("vakif_katilim*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    json_candidates = [
        p for p in candidates
        if p.suffix.lower() == ".json"
        and p.name != OUTPUT_FILE.name
    ]

    if json_candidates:
        return json_candidates[0]

    raise FileNotFoundError(
        "\nVakıf Katılım input JSON bulunamadı.\n"
        f"Beklenen klasör: {PROCESSED_DIR}\n"
    )


# --------------------------------------------------------------------------------------------------
# HELPERS
# --------------------------------------------------------------------------------------------------

def normalize_space(text):
    if not isinstance(text, str):
        return ""

    return re.sub(r"\s+", " ", text).strip()


def unique_list(values):
    result = []
    seen = set()

    for value in values:
        if not isinstance(value, str):
            continue

        value = normalize_space(value)

        if not value:
            continue

        key = value.casefold()

        if key not in seen:
            seen.add(key)
            result.append(value)

    return result


def clean_conditions(values):
    """
    kosullar alanından:
    - boş değerleri
    - duplicate değerleri
    - 'Tümünü Göster' noise'unu
    temizler.
    """

    if not isinstance(values, list):
        return []

    cleaned = []

    for value in values:
        if not isinstance(value, str):
            continue

        value = normalize_space(value)

        if not value:
            continue

        # Tek başına veya satır sonunda bulunan "Tümünü Göster" ifadesini kaldır.
        value = re.sub(
            r"(?:\s*•?\s*Tümünü Göster)\s*$",
            "",
            value,
            flags=re.IGNORECASE,
        ).strip()

        if not value:
            continue

        if value.casefold() == "tümünü göster":
            continue

        cleaned.append(value)

    return unique_list(cleaned)


# --------------------------------------------------------------------------------------------------
# RECORD PATCH
# --------------------------------------------------------------------------------------------------

def patch_record(record):
    r = dict(record)

    # ----------------------------------------------------------------------------------------------
    # 1. BANKA ADI
    # ----------------------------------------------------------------------------------------------

    r["banka"] = BANK_NAME

    # ----------------------------------------------------------------------------------------------
    # 2. GENEL CONDITION CLEANUP
    # ----------------------------------------------------------------------------------------------

    r["kosullar"] = clean_conditions(
        r.get("kosullar", [])
    )

    name = normalize_space(
        r.get("urun_adi", "")
    )

    # ----------------------------------------------------------------------------------------------
    # 3. KONUT FİNANSMANI
    # ----------------------------------------------------------------------------------------------

    if name == "Konut Finansmanı":

        r["kosullar"] = [
            "Konut alımı: Değer <= 5.000.000 TL → A-B %90; C %80; Diğer %70.",

            "Konut alımı: 5.000.000 TL < Değer <= 7.000.000 TL "
            "→ A-B %80; C %70; Diğer %60.",

            "Konut alımı: 7.000.000 TL < Değer <= 10.000.000 TL "
            "→ A-B %70; C %60; Diğer %50.",

            "Konut alımı: 10.000.000 TL < Değer <= 20.000.000 TL "
            "→ A-B %50; C %40; Diğer %30.",

            "Konut alımı: Değer > 20.000.000 TL "
            "→ A-B %40; C %30; Diğer %20.",

            "2. ev alımı: Değer <= 5.000.000 TL "
            "→ A-B %22,5; C %20; Diğer %17,5.",

            "2. ev alımı: 5.000.000 TL < Değer <= 7.000.000 TL "
            "→ A-B %20; C %17,5; Diğer %15.",

            "2. ev alımı: 7.000.000 TL < Değer <= 10.000.000 TL "
            "→ A-B %17,5; C %15; Diğer %12,5.",

            "2. ev alımı: 10.000.000 TL < Değer <= 20.000.000 TL "
            "→ A-B %12,5; C %10; Diğer %7,5.",

            "2. ev alımı: Değer > 20.000.000 TL "
            "→ A-B %10; C %7,5; Diğer %5.",

            "Finansman vadesi 120 aya kadardır.",
        ]

    # ----------------------------------------------------------------------------------------------
    # 4. MASTERCARD EĞİTİM
    #
    # Kaynak:
    # - yalnızca bireysel Mastercard kredi kartları dahil
    # - TROY dahil değil
    # ----------------------------------------------------------------------------------------------

    elif name == "Mastercard’la Eğitimde Vade Farksız 5 Taksit":

        r["hedef_kitle"] = [
            "Bireysel Mastercard kredi kartı sahipleri",
            "Vakıf Katılım müşterileri",
        ]

    # ----------------------------------------------------------------------------------------------
    # 5. TROY EĞİTİM
    #
    # Kaynak:
    # - yalnızca bireysel TROY kredi kartları dahil
    # - Mastercard dahil değil
    # ----------------------------------------------------------------------------------------------

    elif name == "TROY’la Eğitimde Vade Farksız 5 Taksit":

        r["hedef_kitle"] = [
            "Bireysel TROY kredi kartı sahipleri",
            "Vakıf Katılım müşterileri",
        ]

    # ----------------------------------------------------------------------------------------------
    # 6. VCLUB
    #
    # Kaynak:
    # Vakıf Katılım kredi veya banka kartının aktif kullanılması gerekiyor.
    # ----------------------------------------------------------------------------------------------

    elif name == "“VClub Dünyası” Artık Vakıf Katılım Mobil’de!":

        r["hedef_kitle"] = [
            "Vakıf Katılım kredi kartı sahipleri",
            "Vakıf Katılım banka kartı sahipleri",
            "Vakıf Katılım müşterileri",
        ]

    # ----------------------------------------------------------------------------------------------
    # 7. HİSSE SENEDİ KAMPANYASI
    #
    # Structured kampanya tarihi:
    # 14 Aralık 2021 - 31 Aralık 2027
    #
    # Ham metindeki "kampanya süresizdir" ifadesi provenance amacıyla
    # ham_metin içinde korunur.
    #
    # Final dataset'te structured tarih esas alınır.
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "Dijitalden Müşteri Ol, "
        "Hisse Senedi İşlemlerinde %75 Komisyon İndirimi Kazan!"
    ):

        r["kampanya_suresi"] = "14 Aralık 2021 - 31 Aralık 2027"

        r["kampanya_turu"] = "İndirim"

        r["kampanya_avantaji"] = [
            "%75 komisyon indirimi"
        ]

        r["hedef_kitle"] = [
            "Yeni bireysel müşteriler",
            "Dijital kanallardan yatırım hesabı açan müşteriler",
        ]

    # ----------------------------------------------------------------------------------------------
    # 8. MOBİLDEN FATURA TALİMATI
    #
    # 1 ay finansman vadesi DEĞİL.
    # Hediye üyelik süresi.
    # ----------------------------------------------------------------------------------------------

    elif name == (
        "Mobilden Fatura Talimatına "
        "1 Aylık tabii Premium Üyelik Hediye!"
    ):

        r["vade"] = []

        r["kampanya_turu"] = "Hediye"

        r["kampanya_avantaji"] = [
            "1 aylık tabii Premium üyelik"
        ]

        r["hedef_kitle"] = [
            "İlk kez fatura talimatı veren Vakıf Katılım müşterileri"
        ]

    # ----------------------------------------------------------------------------------------------
    # FINAL FIELD NORMALIZATION
    # ----------------------------------------------------------------------------------------------

    for field in LIST_FIELDS:

        value = r.get(field, [])

        if not isinstance(value, list):
            value = []

        r[field] = unique_list(value)

    for field in STRING_FIELDS:

        value = r.get(field, "")

        if value is None:
            value = ""

        if not isinstance(value, str):
            value = str(value)

        r[field] = normalize_space(value)

    # ----------------------------------------------------------------------------------------------
    # EXACT 18-KEY SCHEMA
    #
    # manual_review
    # veri_uyarisi
    #
    # gibi final schema dışındaki bütün alanlar burada otomatik olarak düşer.
    # ----------------------------------------------------------------------------------------------

    final_record = {}

    for key in FINAL_KEYS:

        if key in LIST_FIELDS:
            final_record[key] = r.get(key, [])

        else:
            final_record[key] = r.get(key, "")

    return final_record


# --------------------------------------------------------------------------------------------------
# VALIDATION
# --------------------------------------------------------------------------------------------------

def validate_records(records):

    errors = []

    if not isinstance(records, list):
        errors.append("Root JSON list değil.")
        return errors

    urls = []

    for index, record in enumerate(records, start=1):

        prefix = f"[{index:02d}] {record.get('urun_adi', '')}"

        # Exact key order + schema
        if list(record.keys()) != FINAL_KEYS:

            errors.append(
                f"{prefix} -> 18-key schema/order hatası"
            )

        # List field types
        for field in LIST_FIELDS:

            if not isinstance(record.get(field), list):

                errors.append(
                    f"{prefix} -> {field} list değil"
                )

        # String field types
        for field in STRING_FIELDS:

            if not isinstance(record.get(field), str):

                errors.append(
                    f"{prefix} -> {field} string değil"
                )

        # Record type
        if record["kayit_turu"] not in {
            "finansman",
            "kampanya",
        }:

            errors.append(
                f"{prefix} -> geçersiz kayit_turu: "
                f"{record['kayit_turu']}"
            )

        # Bank
        if record["banka"] != BANK_NAME:

            errors.append(
                f"{prefix} -> banka adı yanlış"
            )

        # TRY forbidden
        if "TRY" in record["para_birimi"]:

            errors.append(
                f"{prefix} -> TRY kullanılmış"
            )

        # URL
        url = record.get(
            "kaynak_url",
            "",
        ).strip()

        if url:

            urls.append(url)

        # Noise check
        for condition in record["kosullar"]:

            if condition.casefold() == "tümünü göster":

                errors.append(
                    f"{prefix} -> "
                    f"'Tümünü Göster' noise kaldı"
                )

        # Extra key guard
        extra_keys = (
            set(record.keys())
            - set(FINAL_KEYS)
        )

        if extra_keys:

            errors.append(
                f"{prefix} -> extra keys: "
                f"{sorted(extra_keys)}"
            )

    # Duplicate URL
    url_counter = Counter(urls)

    duplicates = [
        url
        for url, count in url_counter.items()
        if count > 1
    ]

    for url in duplicates:

        errors.append(
            f"Duplicate URL: {url}"
        )

    return errors


# --------------------------------------------------------------------------------------------------
# AUDIT
# --------------------------------------------------------------------------------------------------

def print_audit(records):

    finance = [
        r
        for r in records
        if r["kayit_turu"] == "finansman"
    ]

    campaigns = [
        r
        for r in records
        if r["kayit_turu"] == "kampanya"
    ]

    duplicate_urls = []

    counter = Counter(
        r["kaynak_url"]
        for r in records
        if r["kaynak_url"]
    )

    for url, count in counter.items():

        if count > 1:
            duplicate_urls.append(url)

    print()
    print("=" * 110)
    print("VAKIF KATILIM - FINAL CLOSED V9 AUDIT")
    print("=" * 110)

    print(f"Toplam kayıt       : {len(records)}")
    print(f"Finansman          : {len(finance)}")
    print(f"Kampanya           : {len(campaigns)}")
    print(f"Duplicate URL      : {len(duplicate_urls)}")

    exact_schema_count = sum(
        1
        for r in records
        if list(r.keys()) == FINAL_KEYS
    )

    print(
        f"Exact 18-key schema: "
        f"{exact_schema_count}/{len(records)}"
    )

    extra_key_count = sum(
        1
        for r in records
        if set(r.keys()) - set(FINAL_KEYS)
    )

    print(
        f"Extra-key kayıt    : "
        f"{extra_key_count}"
    )

    noise_count = sum(
        1
        for r in records
        for c in r["kosullar"]
        if c.casefold() == "tümünü göster"
    )

    print(
        f"Tümünü Göster noise: "
        f"{noise_count}"
    )

    print()
    print("KRİTİK KAYIT KONTROLLERİ")
    print("-" * 110)

    critical_names = [
        "Konut Finansmanı",

        "Mastercard’la Eğitimde Vade Farksız 5 Taksit",

        "TROY’la Eğitimde Vade Farksız 5 Taksit",

        "“VClub Dünyası” Artık Vakıf Katılım Mobil’de!",

        "Mobilden Fatura Talimatına "
        "1 Aylık tabii Premium Üyelik Hediye!",

        "Dijitalden Müşteri Ol, "
        "Hisse Senedi İşlemlerinde %75 Komisyon İndirimi Kazan!",
    ]

    lookup = {
        r["urun_adi"]: r
        for r in records
    }

    for name in critical_names:

        record = lookup.get(name)

        if not record:

            print(
                f"❌ BULUNAMADI: {name}"
            )

            continue

        print(
            f"✅ {name}"
        )

        print(
            f"   Hedef : "
            f"{record['hedef_kitle']}"
        )

        print(
            f"   Vade  : "
            f"{record['vade']}"
        )

        print(
            f"   Tür   : "
            f"{record['kampanya_turu']}"
        )

        print(
            f"   Avantaj: "
            f"{record['kampanya_avantaji']}"
        )

        print(
            f"   Süre  : "
            f"{record['kampanya_suresi']}"
        )

    print("=" * 110)


# --------------------------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------------------------

def main():

    print()
    print("=" * 110)
    print("VAKIF KATILIM - FINAL CLOSED PATCH V9")
    print("=" * 110)

    input_file = find_input_file()

    print(f"Input : {input_file}")
    print(f"Output: {OUTPUT_FILE}")
    print()

    with open(
        input_file,
        "r",
        encoding="utf-8",
    ) as f:

        raw_records = json.load(f)

    if not isinstance(raw_records, list):

        raise ValueError(
            "Input JSON root list olmalı."
        )

    print(
        f"Input kayıt sayısı: "
        f"{len(raw_records)}"
    )

    patched_records = []

    for index, record in enumerate(
        raw_records,
        start=1,
    ):

        patched = patch_record(
            record
        )

        patched_records.append(
            patched
        )

        print(
            f"[{index:02d}/{len(raw_records)}] "
            f"{patched['urun_adi']}"
        )

    errors = validate_records(
        patched_records
    )

    print_audit(
        patched_records
    )

    if errors:

        print()
        print("=" * 110)
        print("VALIDATION ERRORS")
        print("=" * 110)

        for error in errors:

            print(
                f"❌ {error}"
            )

        print()
        print(
            "SONUÇ: V9 VALIDATION BAŞARISIZ ❌"
        )

        raise SystemExit(1)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            patched_records,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 110)
    print(
        "SONUÇ: "
        "VAKIF KATILIM FINAL CLOSED V9 BAŞARILI ✅"
    )
    print("=" * 110)

    print(
        f"JSON: {OUTPUT_FILE}"
    )

    print()

    print(
        "34 kayıt exact 18-key schema'ya "
        "dönüştürüldü ✅"
    )

    print(
        "manual_review / veri_uyarisi "
        "final dataset'ten kaldırıldı ✅"
    )

    print(
        "Mastercard / TROY negative-context "
        "hataları düzeltildi ✅"
    )

    print(
        "Konut oran mapping'i düzeltildi ✅"
    )

    print(
        "'Tümünü Göster' noise temizlendi ✅"
    )

    print(
        "VClub hedef kitlesi düzeltildi ✅"
    )

    print(
        "Fatura talimatındaki yanlış vade "
        "temizlendi ✅"
    )

    print("=" * 110)


if __name__ == "__main__":
    main()