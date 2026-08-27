import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


# =========================================================
# PATH
# =========================================================

ROOT = Path(__file__).resolve().parents[2]

RAW_FILE = (
    ROOT
    / "data"
    / "raw"
    / "dunya_katilim_finansman_urunleri.json"
)


# =========================================================
# AYARLAR
# =========================================================

EXPECTED_BANK = "Dünya Katılım Bankası A.Ş."

EXPECTED_COUNT = 6

EXPECTED_PRODUCTS = {
    "İhtiyaç Finansmanı": {
        "kategori_kaynak": "İhtiyaç Finansmanları",
        "required_terms": [
            "125.000",
            "36 ay",
            "250.000",
            "24 ay",
            "500.000",
            "12 ay",
            "Başvuru Şartları",
        ],
    },

    "Enerya İhtiyaç Finansmanı": {
        "kategori_kaynak": "İhtiyaç Finansmanları",
        "required_terms": [
            "250.000 TL",
            "36 ay",
            "%3,99",
            "proforma fatura",
        ],
    },

    "Enerya Karz-ı Hasen": {
        "kategori_kaynak": "İhtiyaç Finansmanları",
        "required_terms": [
            "vade farksız",
            "500 TL",
            "16.500 TL",
            "2 ay",
            "6 ay",
        ],
    },

    "Araç Finansmanı": {
        "kategori_kaynak": "Araç Finansmanları",
        "required_terms": [
            "400.000 TL",
            "70%",
            "48 ay",
            "800.000 TL",
            "50%",
            "36 ay",
            "1.200.000 TL",
            "30%",
            "24 ay",
            "2.000.000 TL",
            "20%",
            "12 ay",
            "12 yaş",
        ],
    },

    "Çevre Dostu Araç Finansmanı": {
        "kategori_kaynak": "Araç Finansmanları",
        "required_terms": [
            "elektrikli",
            "hibrit",
            "18 yaş",
            "proforma fatura",
            "nakit olarak",
        ],
    },

    "Konut Finansmanı": {
        "kategori_kaynak": "Konut Finansmanları",
        "required_terms": [
            "5.000.000",
            "90%",
            "80%",
            "70%",
            "20.000.000",
            "22.5%",
            "17.5%",
            "12.5%",
            "Başvuru Şartları",
        ],
    },
}


# =========================================================
# COOKIE / KVKK NOISE
# =========================================================

FORBIDDEN_TERMS = [
    "Tüm site ziyaretçilerimizi daha iyi tanımak",
    "Çerez Aydınlatma Metni",
    "ÇEREZ KULLANIMINA İLİŞKİN AYDINLATMA METNİ",
    "Çerez Politikası",
    "Zorunlu Çerezler",
    "Performans ve Analitik Çerezleri",
    "Kişiselleştirilmiş Reklam Çerezleri",
    "Kişisel veri sahipleri Kanunun",
    "Tercihlerimi Kaydet",
]


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_text(value):

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

    value = value.replace(
        "’",
        "'"
    )

    value = value.replace(
        "‘",
        "'"
    )

    value = value.replace(
        "–",
        "-"
    )

    value = value.replace(
        "—",
        "-"
    )

    value = value.replace(
        "\xa0",
        " "
    )

    value = value.casefold()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def contains(
    text,
    term
):

    return (
        normalize_text(term)
        in normalize_text(text)
    )


# =========================================================
# JSON LOAD
# =========================================================

def load_json():

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

            return json.load(
                file
            )

    except json.JSONDecodeError as error:

        print(
            "JSON parse hatası:"
        )

        print(
            error
        )

        sys.exit(
            1
        )


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
# VALIDATION
# =========================================================

def validate():

    data = load_json()

    errors = []

    warnings = []

    print()

    print(
        "=" * 118
    )

    print(
        "DÜNYA KATILIM - FİNANSMAN RAW VALIDATOR V1"
    )

    print(
        "=" * 118
    )

    print(
        "RAW:",
        RAW_FILE
    )

    # =====================================================
    # ROOT
    # =====================================================

    if not isinstance(
        data,
        dict
    ):

        errors.append(
            (
                "ROOT JSON object/dict olmalı. "
                f"Gerçek tip: {type(data).__name__}"
            )
        )

        records = []

    else:

        records = data.get(
            "urunler",
            []
        )

    # =====================================================
    # TOP LEVEL
    # =====================================================

    if isinstance(
        data,
        dict
    ):

        if (
            data.get(
                "banka"
            )
            != EXPECTED_BANK
        ):

            errors.append(
                (
                    "Top-level banka adı yanlış. "
                    f"Gerçek={data.get('banka')}"
                )
            )

        if (
            data.get(
                "beklenen_urun_sayisi"
            )
            != EXPECTED_COUNT
        ):

            errors.append(
                (
                    "beklenen_urun_sayisi yanlış. "
                    f"Beklenen={EXPECTED_COUNT}, "
                    f"Gerçek={data.get('beklenen_urun_sayisi')}"
                )
            )

        if (
            data.get(
                "toplam_urun_sayisi"
            )
            != EXPECTED_COUNT
        ):

            errors.append(
                (
                    "toplam_urun_sayisi yanlış. "
                    f"Beklenen={EXPECTED_COUNT}, "
                    f"Gerçek={data.get('toplam_urun_sayisi')}"
                )
            )

        if (
            data.get(
                "http_hata_sayisi"
            )
            != 0
        ):

            errors.append(
                (
                    "Top-level HTTP hata sayısı 0 değil: "
                    f"{data.get('http_hata_sayisi')}"
                )
            )

        if (
            data.get(
                "duplicate_url_sayisi"
            )
            != 0
        ):

            errors.append(
                (
                    "Top-level duplicate URL sayısı 0 değil: "
                    f"{data.get('duplicate_url_sayisi')}"
                )
            )

        if (
            data.get(
                "duplicate_baslik_sayisi"
            )
            != 0
        ):

            errors.append(
                (
                    "Top-level duplicate başlık sayısı 0 değil: "
                    f"{data.get('duplicate_baslik_sayisi')}"
                )
            )

    # =====================================================
    # URUNLER
    # =====================================================

    if not isinstance(
        records,
        list
    ):

        errors.append(
            (
                "'urunler' LIST olmalı. "
                f"Gerçek tip: {type(records).__name__}"
            )
        )

        records = []

    if len(
        records
    ) != EXPECTED_COUNT:

        errors.append(
            (
                "Gerçek ürün sayısı yanlış. "
                f"Beklenen={EXPECTED_COUNT}, "
                f"Gerçek={len(records)}"
            )
        )

    # =====================================================
    # EXPECTED TITLE CHECK
    # =====================================================

    actual_titles = {
        record.get(
            "urun_adi",
            ""
        )
        for record in records
        if isinstance(
            record,
            dict
        )
    }

    expected_titles = set(
        EXPECTED_PRODUCTS.keys()
    )

    missing_products = (
        expected_titles
        - actual_titles
    )

    unexpected_products = (
        actual_titles
        - expected_titles
    )

    if missing_products:

        errors.append(
            (
                "Eksik ürünler: "
                f"{sorted(missing_products)}"
            )
        )

    if unexpected_products:

        errors.append(
            (
                "Beklenmeyen ürünler: "
                f"{sorted(unexpected_products)}"
            )
        )

    # =====================================================
    # RECORD CHECK
    # =====================================================

    print()

    print(
        "-" * 118
    )

    print(
        "ÜRÜN KONTROLLERİ"
    )

    print(
        "-" * 118
    )

    required_fields = [
        "banka",
        "urun_adi",
        "kategori_kaynak",
        "kaynak_url",
        "final_url",
        "http_status",
        "sayfa_basligi",
        "baslik_dogrulandi",
        "cookie_noise_var",
        "ham_metin",
    ]

    for index, record in enumerate(
        records,
        start=1
    ):

        if not isinstance(
            record,
            dict
        ):

            errors.append(
                (
                    f"Kayıt {index} dict değil."
                )
            )

            continue

        title = record.get(
            "urun_adi",
            f"Kayıt {index}"
        )

        product_errors = []

        product_warnings = []

        # ---------------------------------------------
        # FIELD
        # ---------------------------------------------

        for field in required_fields:

            if field not in record:

                product_errors.append(
                    (
                        f"eksik alan: {field}"
                    )
                )

        # ---------------------------------------------
        # BANK
        # ---------------------------------------------

        if (
            record.get(
                "banka"
            )
            != EXPECTED_BANK
        ):

            product_errors.append(
                (
                    "banka adı yanlış: "
                    f"{record.get('banka')}"
                )
            )

        # ---------------------------------------------
        # EXPECTED PRODUCT
        # ---------------------------------------------

        product_config = (
            EXPECTED_PRODUCTS.get(
                title
            )
        )

        if product_config is None:

            product_errors.append(
                "beklenmeyen ürün"
            )

        else:

            expected_category = (
                product_config[
                    "kategori_kaynak"
                ]
            )

            if (
                record.get(
                    "kategori_kaynak"
                )
                != expected_category
            ):

                product_errors.append(
                    (
                        "kategori yanlış. "
                        f"Beklenen={expected_category}, "
                        f"Gerçek={record.get('kategori_kaynak')}"
                    )
                )

        # ---------------------------------------------
        # HTTP
        # ---------------------------------------------

        if (
            record.get(
                "http_status"
            )
            != 200
        ):

            product_errors.append(
                (
                    "HTTP 200 değil: "
                    f"{record.get('http_status')}"
                )
            )

        # ---------------------------------------------
        # TITLE
        # ---------------------------------------------

        if (
            record.get(
                "baslik_dogrulandi"
            )
            is not True
        ):

            product_errors.append(
                "başlık doğrulanmamış"
            )

        # ---------------------------------------------
        # COOKIE
        # ---------------------------------------------

        if (
            record.get(
                "cookie_noise_var"
            )
            is not False
        ):

            product_errors.append(
                "cookie_noise_var False değil"
            )

        # ---------------------------------------------
        # URL
        # ---------------------------------------------

        source_url = str(
            record.get(
                "kaynak_url",
                ""
            )
        ).strip()

        final_url = str(
            record.get(
                "final_url",
                ""
            )
        ).strip()

        if not source_url:

            product_errors.append(
                "kaynak_url boş"
            )

        if not final_url:

            product_errors.append(
                "final_url boş"
            )

        source_domain = urlparse(
            source_url
        ).netloc.lower()

        final_domain = urlparse(
            final_url
        ).netloc.lower()

        if (
            source_domain
            and source_domain
            != "dunyakatilim.com.tr"
        ):

            product_errors.append(
                (
                    "kaynak resmi domain değil: "
                    f"{source_domain}"
                )
            )

        if (
            final_domain
            and final_domain
            != "dunyakatilim.com.tr"
        ):

            product_errors.append(
                (
                    "final URL resmi domain değil: "
                    f"{final_domain}"
                )
            )

        # ---------------------------------------------
        # RAW TEXT
        # ---------------------------------------------

        raw_text = str(
            record.get(
                "ham_metin",
                ""
            )
        ).strip()

        if not raw_text:

            product_errors.append(
                "ham_metin boş"
            )

        elif len(
            raw_text
        ) < 500:

            product_warnings.append(
                (
                    "ham_metin kısa: "
                    f"{len(raw_text)} karakter"
                )
            )

        if (
            title
            and not contains(
                raw_text,
                title
            )
        ):

            product_errors.append(
                (
                    "urun_adi ham_metin içinde yok"
                )
            )

        # ---------------------------------------------
        # FORBIDDEN COOKIE TEXT
        # ---------------------------------------------

        found_forbidden = []

        for forbidden in FORBIDDEN_TERMS:

            if contains(
                raw_text,
                forbidden
            ):

                found_forbidden.append(
                    forbidden
                )

        if found_forbidden:

            product_errors.append(
                (
                    "cookie/KVKK contamination: "
                    f"{found_forbidden}"
                )
            )

        # ---------------------------------------------
        # CRITICAL TERMS
        # ---------------------------------------------

        missing_terms = []

        if product_config:

            for term in product_config[
                "required_terms"
            ]:

                if not contains(
                    raw_text,
                    term
                ):

                    missing_terms.append(
                        term
                    )

        if missing_terms:

            product_errors.append(
                (
                    "kritik kaynak terimleri eksik: "
                    f"{missing_terms}"
                )
            )

        # ---------------------------------------------
        # PLACEHOLDER WARNING
        # ---------------------------------------------

        placeholder_markers = [
            "Service unavailable",
            "Aylık Kâr Oranı",
            "% 0",
        ]

        found_placeholders = [
            marker
            for marker in placeholder_markers
            if contains(
                raw_text,
                marker
            )
        ]

        if found_placeholders:

            product_warnings.append(
                (
                    "Hesaplama widget placeholder'ları "
                    "RAW içinde mevcut; extractor bunları "
                    "gerçek ürün verisi olarak ALMAMALI: "
                    f"{found_placeholders}"
                )
            )

        # ---------------------------------------------
        # REPORT
        # ---------------------------------------------

        errors.extend(
            [
                f"{title} -> {message}"
                for message
                in product_errors
            ]
        )

        warnings.extend(
            [
                f"{title} -> {message}"
                for message
                in product_warnings
            ]
        )

        print()

        print(
            f"[{index}/{len(records)}] {title}"
        )

        print(
            "HTTP:",
            record.get(
                "http_status"
            )
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
            "Kritik veri:",
            (
                "TAM ✅"
                if not missing_terms
                else "EKSİK ❌"
            )
        )

        print(
            "Cookie/KVKK:",
            (
                "YOK ✅"
                if not found_forbidden
                else "VAR ❌"
            )
        )

        if product_warnings:

            print(
                "Warning:",
                len(
                    product_warnings
                )
            )

        else:

            print(
                "Warning: 0"
            )

        if product_errors:

            print(
                "Error:",
                len(
                    product_errors
                )
            )

        else:

            print(
                "Error: 0"
            )

    # =====================================================
    # DUPLICATE
    # =====================================================

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

    # =====================================================
    # FINAL
    # =====================================================

    print()

    print(
        "=" * 118
    )

    print(
        "RAW VALIDATION SONUCU"
    )

    print(
        "=" * 118
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
        "Eksik ürün:",
        len(
            missing_products
        )
    )

    print(
        "Beklenmeyen ürün:",
        len(
            unexpected_products
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
        "Warning:",
        len(
            warnings
        )
    )

    print(
        "Error:",
        len(
            errors
        )
    )

    if warnings:

        print()

        print(
            "UYARILAR:"
        )

        for warning in warnings:

            print(
                "-",
                warning
            )

    if errors:

        print()

        print(
            "HATALAR:"
        )

        for error in errors:

            print(
                "-",
                error
            )

    print()

    if not errors:

        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "FİNANSMAN RAW VALIDATION "
                "BAŞARILI ✅"
            )
        )

    else:

        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "FİNANSMAN RAW VALIDATION "
                "BAŞARISIZ ❌"
            )
        )

    print(
        "=" * 118
    )

    if errors:

        sys.exit(
            1
        )


if __name__ == "__main__":
    validate()