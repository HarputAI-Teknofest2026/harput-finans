import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RAW_FILE = (
    ROOT
    / "data"
    / "raw"
    / "dunya_katilim_finansman_urunleri.json"
)

EXPECTED_COUNT = 6


PRODUCT_RULES = {
    "İhtiyaç Finansmanı": {
        "checks": {
            "125.000 TL sınırı": [
                "125.000",
            ],
            "250.000 TL sınırı": [
                "250.000",
            ],
            "500.000 TL sınırı": [
                "500.000",
            ],
            "36 ay vade": [
                "36 ay",
                "0 - 36",
                "0 – 36",
            ],
            "24 ay vade": [
                "24 ay",
                "0 - 24",
                "0 – 24",
            ],
            "12 ay vade": [
                "12 ay",
                "0 - 12",
                "0 – 12",
            ],
            "18 yaş şartı": [
                "18 yaşını doldurmuş",
            ],
            "Nakit verilmediği bilgisi": [
                "doğrudan nakit olarak alınmaz",
                "doğrudan nakit olarak verilmez",
            ],
            "Tahsis ücreti açıklaması": [
                "Tahsis ücreti müşteriden peşin olarak tahsil edilecektir",
            ],
        }
    },

    "Enerya İhtiyaç Finansmanı": {
        "checks": {
            "Maksimum 250.000 TL": [
                "250.000 TL",
            ],
            "36 ay vade": [
                "36 ay",
            ],
            "Aylık %3,99 kâr oranı": [
                "%3,99",
                "% 3,99",
            ],
            "18 yaş şartı": [
                "18 yaşını doldurmuş",
            ],
            "Proforma fatura": [
                "proforma fatura",
            ],
            "Ödeme satıcıya": [
                "ödeme müşteriye değil, satıcıya yapılmaktadır",
            ],
        }
    },

    "Enerya Karz-ı Hasen": {
        "checks": {
            "Vade farksız": [
                "vade farksız",
            ],
            "Minimum 500 TL": [
                "500 TL",
            ],
            "Maksimum 16.500 TL": [
                "16.500 TL",
            ],
            "Minimum 2 ay": [
                "2 ay",
            ],
            "Maksimum 6 ay": [
                "6 ay",
            ],
            "Antalya": [
                "Antalya",
            ],
            "Aydın": [
                "Aydın",
            ],
            "Denizli": [
                "Denizli",
            ],
            "Konya": [
                "Konya",
            ],
        }
    },

    "Araç Finansmanı": {
        "checks": {
            "0-400.000 TL bandı": [
                "0 TL – 400.000 TL",
                "0 TL - 400.000 TL",
            ],
            "%70 finansman": [
                "70%",
                "%70",
            ],
            "48 ay vade": [
                "48 ay",
                "70% 48",
            ],

            "400.001-800.000 TL bandı": [
                "400.001 TL – 800.000 TL",
                "400.001 TL - 800.000 TL",
            ],
            "%50 finansman": [
                "50%",
                "%50",
            ],
            "36 ay vade": [
                "36 ay",
                "50% 36",
            ],

            "800.001-1.200.000 TL bandı": [
                "800.001 TL – 1.200.000 TL",
                "800.001 TL - 1.200.000 TL",
            ],
            "%30 finansman": [
                "30%",
                "%30",
            ],
            "24 ay vade": [
                "24 ay",
                "30% 24",
            ],

            "1.200.001-2.000.000 TL bandı": [
                "1.200.001 TL- 2.000.000 TL",
                "1.200.001 TL – 2.000.000 TL",
                "1.200.001 TL - 2.000.000 TL",
            ],
            "%20 finansman": [
                "20%",
                "%20",
            ],
            "12 ay vade": [
                "12 ay",
                "20% 12",
            ],

            "2.000.000 ve üzeri": [
                "2.000.000 ve üzeri",
            ],
            "Gerçek %0 bandı": [
                "2.000.000 ve üzeri 0% 0",
            ],
            "12 yaş sınırı": [
                "12 yaşa kadar",
            ],
        }
    },

    "Çevre Dostu Araç Finansmanı": {
        "checks": {
            "Elektrikli araç": [
                "elektrikli",
            ],
            "Hibrit araç": [
                "hibrit",
            ],
            "18 yaş şartı": [
                "18 yaşını doldurmuş",
            ],
            "Proforma fatura": [
                "proforma fatura",
            ],
            "Nakit kullandırım yok": [
                "nakit olarak müşterinin hesabına geçmez",
                "nakit olarak başvuru sahibine verilmez",
            ],
            "Satıcı/bayiye ödeme": [
                "satıcıya veya bayiye doğrudan aktarılır",
            ],
        }
    },

    "Konut Finansmanı": {
        "checks": {
            "İlk ev %90": [
                "Değer x 90%",
            ],
            "İlk ev %80": [
                "Değer x 80%",
            ],
            "İlk ev %70": [
                "Değer x 70%",
            ],
            "5.000.000 TL sınırı": [
                "5.000.000",
            ],
            "7.000.000 TL sınırı": [
                "7.000.000",
            ],
            "10.000.000 TL sınırı": [
                "10.000.000",
            ],
            "20.000.000 TL sınırı": [
                "20.000.000",
            ],
            "İkinci ev %22.5": [
                "22.5%",
            ],
            "İkinci ev %17.5": [
                "17.5%",
            ],
            "İkinci ev %12.5": [
                "12.5%",
            ],
            "Erken ödeme %1": [
                "%1’i",
                "%1'i",
            ],
            "Erken ödeme %2": [
                "%2’si",
                "%2'si",
            ],
            "BSMV istisnası": [
                "BSMV uygulanmaz",
                "BSMV istisnası",
            ],
        }
    },
}


SEMANTIC_NOTES = {
    "İhtiyaç Finansmanı": [
        (
            "Tutar-vade ilişkisi korunmalı: "
            "0-125.000 TL → 36 ay, "
            "125.001-250.000 TL → 24 ay, "
            "250.001-500.000 TL → 12 ay."
        ),
        (
            "Widget'taki 1.000 TL / 50.000 TL / "
            "Vade 1-36 / %0 gerçek ürün verisi değildir."
        ),
    ],

    "Enerya İhtiyaç Finansmanı": [
        (
            "Ürün-spesifik açık veriler: "
            "maksimum 250.000 TL, 36 ay, aylık %3,99."
        ),
    ],

    "Enerya Karz-ı Hasen": [
        (
            "'Vade farksız' sayısal kâr oranına "
            "dönüştürülmemeli."
        ),
        (
            "Coğrafi kapsam Antalya, Aydın, Denizli "
            "ve Konya yeni abonelik işlemleridir."
        ),
    ],

    "Araç Finansmanı": [
        (
            "Tablodaki tutarlar aracın nihai fatura/kasko "
            "değeridir; finansman tutarı diye doğrudan yazılmamalı."
        ),
        (
            "2.000.000 TL üzerindeki gerçek %0 ile "
            "widget'taki sahte %0 karıştırılmamalı."
        ),
    ],

    "Çevre Dostu Araç Finansmanı": [
        (
            "Açık ürün-spesifik sayısal kâr oranı görünmüyor; "
            "widget %0 değeri alınmamalı."
        ),
    ],

    "Konut Finansmanı": [
        (
            "Finansman oranları konut değeri + enerji sınıfı + "
            "ilk/sonraki konut durumuna bağlıdır."
        ),
        (
            "%1 ve %2 kâr payı değil, "
            "erken ödeme tazminatı oranıdır."
        ),
        (
            "Widget'taki Vade 1-36 ve %0 ürünün ana "
            "vadesi/kâr oranı değildir."
        ),
    ],
}


WIDGET_MARKERS = [
    "Service unavailable",
    "Aylık Kâr Oranı",
    "% 0",
    "Finansman ihtiyacınız",
    "Kâr Oranını Kendim Belirleyeceğim",
]


def normalize_text(text):

    text = str(
        text or ""
    )

    replacements = {
        "İ": "i",
        "I": "ı",
        "’": "'",
        "‘": "'",
        "´": "'",
        "`": "'",
        "–": "-",
        "—": "-",
        "\xa0": " ",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    text = text.casefold()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def contains(
    text,
    term
):

    return (
        normalize_text(
            term
        )
        in normalize_text(
            text
        )
    )


def load_records():

    if not RAW_FILE.exists():

        print(
            f"RAW dosya bulunamadı: {RAW_FILE}"
        )

        sys.exit(
            1
        )

    try:

        with RAW_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

    except json.JSONDecodeError as error:

        print(
            "JSON parse hatası:",
            error
        )

        sys.exit(
            1
        )

    if not isinstance(
        data,
        dict
    ):

        print(
            "RAW root dict/object değil."
        )

        sys.exit(
            1
        )

    records = data.get(
        "urunler"
    )

    if not isinstance(
        records,
        list
    ):

        print(
            "'urunler' list değil."
        )

        sys.exit(
            1
        )

    return (
        data,
        records
    )


def find_match(
    text,
    candidates
):

    for candidate in candidates:

        if contains(
            text,
            candidate
        ):

            return candidate

    return None


def inspect_product(
    record,
    index,
    total
):

    title = record.get(
        "urun_adi",
        "?"
    )

    raw_text = str(
        record.get(
            "ham_metin",
            ""
        )
        or ""
    )

    config = PRODUCT_RULES.get(
        title
    )

    errors = []

    print()

    print(
        "=" * 110
    )

    print(
        f"[{index}/{total}] {title}"
    )

    print(
        "=" * 110
    )

    print(
        "Kategori:",
        record.get(
            "kategori_kaynak"
        )
    )

    print(
        "Karakter:",
        len(
            raw_text
        )
    )

    print(
        "URL:",
        record.get(
            "kaynak_url"
        )
    )

    print()

    print(
        "KRİTİK KAYNAK KONTROLLERİ"
    )

    print(
        "-" * 110
    )

    if config is None:

        errors.append(
            f"{title} -> inspector config yok"
        )

        print(
            "❌ Inspector config bulunamadı."
        )

        return errors

    for label, candidates in config[
        "checks"
    ].items():

        matched = find_match(
            raw_text,
            candidates
        )

        if matched:

            print(
                f"✅ {label}"
            )

        else:

            print(
                f"❌ {label}"
            )

            errors.append(
                (
                    f"{title} -> "
                    f"{label} bulunamadı"
                )
            )

    print()

    print(
        "SEMANTİK NOTLAR"
    )

    print(
        "-" * 110
    )

    for note in SEMANTIC_NOTES.get(
        title,
        []
    ):

        print(
            "•",
            note
        )

    print()

    if errors:

        print(
            f"ÜRÜN SONUCU: {len(errors)} HATA ❌"
        )

    else:

        print(
            "ÜRÜN SONUCU: SEMANTİK RAW TAM ✅"
        )

    return errors


def main():

    data, records = load_records()

    print()

    print(
        "#" * 110
    )

    print(
        "DÜNYA KATILIM - FİNANSMAN RAW INSPECTOR V2"
    )

    print(
        "#" * 110
    )

    print(
        "RAW:",
        RAW_FILE
    )

    print(
        "Banka:",
        data.get(
            "banka"
        )
    )

    print(
        "Ürün sayısı:",
        len(
            records
        )
    )

    all_errors = []

    if len(
        records
    ) != EXPECTED_COUNT:

        all_errors.append(
            (
                "Ürün sayısı yanlış: "
                f"beklenen={EXPECTED_COUNT}, "
                f"gerçek={len(records)}"
            )
        )

    actual_titles = {
        record.get(
            "urun_adi"
        )
        for record in records
        if isinstance(
            record,
            dict
        )
    }

    expected_titles = set(
        PRODUCT_RULES
    )

    missing = (
        expected_titles
        - actual_titles
    )

    unexpected = (
        actual_titles
        - expected_titles
    )

    if missing:

        all_errors.append(
            (
                "Eksik ürünler: "
                f"{sorted(missing)}"
            )
        )

    if unexpected:

        all_errors.append(
            (
                "Beklenmeyen ürünler: "
                f"{sorted(unexpected)}"
            )
        )

    for index, record in enumerate(
        records,
        start=1
    ):

        if not isinstance(
            record,
            dict
        ):

            all_errors.append(
                f"Kayıt {index} dict değil"
            )

            continue

        all_errors.extend(
            inspect_product(
                record,
                index,
                len(
                    records
                )
            )
        )

    warnings = []

    print()

    print(
        "=" * 110
    )

    print(
        "GLOBAL EXTRACTION SAFETY"
    )

    print(
        "=" * 110
    )

    for record in records:

        title = record.get(
            "urun_adi",
            "?"
        )

        raw_text = str(
            record.get(
                "ham_metin",
                ""
            )
            or ""
        )

        found = [
            marker
            for marker in WIDGET_MARKERS
            if contains(
                raw_text,
                marker
            )
        ]

        if found:

            warnings.append(
                (
                    f"{title}: "
                    f"{found}"
                )
            )

            print(
                f"⚠️ {title}: {found}"
            )

    print()

    print(
        "KESİN EXTRACTOR KURALI:"
    )

    print(
        (
            "Widget'taki Service unavailable / %0 / "
            "1.000 TL / 50.000 TL / Vade 1-36 "
            "değerleri gerçek ürün verisi olarak alınmayacak."
        )
    )

    print()

    print(
        "#" * 110
    )

    print(
        "RAW INSPECTOR SONUCU"
    )

    print(
        "#" * 110
    )

    print(
        "Beklenen ürün:",
        EXPECTED_COUNT
    )

    print(
        "Gerçek ürün:",
        len(
            records
        )
    )

    print(
        "Semantic error:",
        len(
            all_errors
        )
    )

    print(
        "Safety warning:",
        len(
            warnings
        )
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
                "SONUÇ: DÜNYA KATILIM "
                "FİNANSMAN RAW SEMANTİK "
                "INSPECTION BAŞARILI ✅"
            )
        )

        print(
            (
                "RAW artık extractor yazmak için "
                "yeterli durumda ✅"
            )
        )

    else:

        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "FİNANSMAN RAW SEMANTİK "
                "INSPECTION BAŞARISIZ ❌"
            )
        )

        sys.exit(
            1
        )


if __name__ == "__main__":
    main()