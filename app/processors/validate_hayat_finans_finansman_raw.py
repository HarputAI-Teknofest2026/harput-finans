import json
import os
from urllib.parse import urlparse


# =========================================================
# AYARLAR
# =========================================================

INPUT_FILE = "data/raw/hayat_finans_finansman_urunleri.json"

EXPECTED_BANK = "Hayat Finans Katılım Bankası"

EXPECTED_RECORD_TYPE = "finansman"

EXPECTED_COUNT = 3

EXPECTED_PRODUCTS = {
    "Bana Bunu Al": {
        "url_path": "/krediler/bana-bunu-al",
        "required_terms": [
            "50.000",
            "18 aya",
            "500 TL",
            "İhtiyaca Dayalı Finansman",
        ],
    },

    "Bana Bunu Al İş Ortağım": {
        "url_path": "/finansmanlar/bana-bunu-al-is-ortagim",
        "required_terms": [
            "24 aya",
            "İhtiyaca Dayalı Finansman",
            "avantajlı kâr oranları",
        ],
    },

    "Eğitim Finansmanı Sistemi": {
        "url_path": "/krediler/hayat-finans-egitim-finansmani-sistemi",
        "required_terms": [
            "600.000",
            "3 ay erteleme",
            "masraf",
            "vade farkı",
        ],
    },
}


FORBIDDEN_CONTAMINATION = {
    "Eğitim Finansmanı Sistemi": [
        "Avantajlı Katılma Hesabı",
        "eşit ve yüksek kâr paylaşım oranı",
        "birikimlerinizi değerlendirirken",
    ],
}


# =========================================================
# NORMALİZASYON
# =========================================================

def tr_lower(value):
    value = str(value or "")

    value = value.replace("İ", "i")
    value = value.replace("I", "ı")

    return value.casefold()


def normalize_url(url):
    return str(url or "").strip().rstrip("/")


def get_url_path(url):
    parsed = urlparse(
        normalize_url(url)
    )

    return parsed.path.rstrip("/")


def is_official_domain(url):
    host = urlparse(
        normalize_url(url)
    ).netloc.lower()

    return (
        host == "hayatfinans.com.tr"
        or host == "www.hayatfinans.com.tr"
        or host.endswith(".hayatfinans.com.tr")
    )


# =========================================================
# JSON OKU
# =========================================================

def load_json():
    if not os.path.exists(
        INPUT_FILE
    ):
        raise FileNotFoundError(
            f"Dosya bulunamadı: {INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(
            file
        )


# =========================================================
# DUPLICATE
# =========================================================

def find_duplicates(values):
    seen = set()
    duplicates = []

    for value in values:
        key = tr_lower(
            value
        ).strip()

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
# MAIN
# =========================================================

def main():

    print()
    print(
        "=" * 110
    )

    print(
        "HAYAT FİNANS - FİNANSMAN RAW VALIDATOR V1"
    )

    print(
        "=" * 110
    )

    print(
        "Dosya:",
        INPUT_FILE
    )

    data = load_json()

    errors = []
    warnings = []

    # =====================================================
    # WRAPPER KONTROLÜ
    # =====================================================

    print()
    print(
        "[1/6] JSON wrapper kontrol ediliyor..."
    )

    bank = data.get(
        "banka",
        ""
    )

    record_type = data.get(
        "kayit_turu",
        ""
    )

    total_count = data.get(
        "toplam_kayit",
        None
    )

    products = data.get(
        "urunler",
        []
    )

    http_errors = data.get(
        "http_hatalari",
        []
    )

    if bank != EXPECTED_BANK:
        errors.append(
            (
                "Wrapper banka adı hatalı: "
                f"{bank}"
            )
        )

    if record_type != EXPECTED_RECORD_TYPE:
        errors.append(
            (
                "Wrapper kayıt türü hatalı: "
                f"{record_type}"
            )
        )

    if not isinstance(
        products,
        list
    ):
        errors.append(
            "'urunler' list değil."
        )

        products = []

    if total_count != len(
        products
    ):
        errors.append(
            (
                "toplam_kayit ile gerçek liste "
                "uzunluğu uyuşmuyor. "
                f"toplam_kayit={total_count}, "
                f"gerçek={len(products)}"
            )
        )

    if len(
        products
    ) != EXPECTED_COUNT:
        errors.append(
            (
                "Ürün sayısı hatalı. "
                f"Beklenen={EXPECTED_COUNT}, "
                f"Gerçek={len(products)}"
            )
        )

    print(
        "Wrapper banka:",
        bank
    )

    print(
        "Wrapper kayıt türü:",
        record_type
    )

    print(
        "Toplam kayıt:",
        len(products)
    )

    # =====================================================
    # HTTP HATA
    # =====================================================

    print()
    print(
        "[2/6] HTTP hata kontrol ediliyor..."
    )

    if http_errors:
        errors.append(
            (
                "RAW içinde HTTP hataları var: "
                f"{len(http_errors)}"
            )
        )

    print(
        "HTTP hata:",
        len(http_errors)
    )

    # =====================================================
    # ZORUNLU ALANLAR
    # =====================================================

    print()
    print(
        "[3/6] Zorunlu alanlar kontrol ediliyor..."
    )

    required_fields = [
        "banka",
        "kayit_turu",
        "urun_adi",
        "kaynak_url",
        "ham_metin",
    ]

    for index, product in enumerate(
        products,
        start=1
    ):

        title = product.get(
            "urun_adi",
            f"Kayıt {index}"
        )

        for field in required_fields:

            if field not in product:
                errors.append(
                    (
                        f"{title} -> "
                        f"alan yok: {field}"
                    )
                )

                continue

            value = product.get(
                field
            )

            if (
                value is None
                or str(value).strip() == ""
            ):
                errors.append(
                    (
                        f"{title} -> "
                        f"alan boş: {field}"
                    )
                )

        if product.get(
            "banka"
        ) != EXPECTED_BANK:
            errors.append(
                (
                    f"{title} -> "
                    "banka adı yanlış."
                )
            )

        if product.get(
            "kayit_turu"
        ) != EXPECTED_RECORD_TYPE:
            errors.append(
                (
                    f"{title} -> "
                    "kayit_turu finansman değil."
                )
            )

    print(
        "Zorunlu alan kontrolü tamamlandı."
    )

    # =====================================================
    # URL / DUPLICATE
    # =====================================================

    print()
    print(
        "[4/6] URL ve duplicate kontrol ediliyor..."
    )

    urls = [
        normalize_url(
            product.get(
                "kaynak_url",
                ""
            )
        )
        for product in products
    ]

    titles = [
        product.get(
            "urun_adi",
            ""
        )
        for product in products
    ]

    duplicate_urls = find_duplicates(
        urls
    )

    duplicate_titles = find_duplicates(
        titles
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
                "Duplicate ürün adı bulundu: "
                f"{duplicate_titles}"
            )
        )

    for product in products:

        url = product.get(
            "kaynak_url",
            ""
        )

        title = product.get(
            "urun_adi",
            ""
        )

        if not is_official_domain(
            url
        ):
            errors.append(
                (
                    f"{title} -> "
                    f"resmi olmayan domain: {url}"
                )
            )

    print(
        "Duplicate URL:",
        len(duplicate_urls)
    )

    print(
        "Duplicate başlık:",
        len(duplicate_titles)
    )

    # =====================================================
    # BEKLENEN ÜRÜNLER
    # =====================================================

    print()
    print(
        "[5/6] Beklenen ürünler kontrol ediliyor..."
    )

    products_by_title = {
        product.get(
            "urun_adi",
            ""
        ): product

        for product in products
    }

    missing_products = []

    unexpected_products = []

    for expected_title in EXPECTED_PRODUCTS:

        if expected_title not in products_by_title:

            missing_products.append(
                expected_title
            )

            errors.append(
                (
                    "Beklenen ürün eksik: "
                    f"{expected_title}"
                )
            )

    for title in products_by_title:

        if title not in EXPECTED_PRODUCTS:

            unexpected_products.append(
                title
            )

            errors.append(
                (
                    "Beklenmeyen ürün var: "
                    f"{title}"
                )
            )

    for title, config in (
        EXPECTED_PRODUCTS.items()
    ):

        if title not in products_by_title:
            continue

        product = products_by_title[
            title
        ]

        actual_path = get_url_path(
            product[
                "kaynak_url"
            ]
        )

        if (
            actual_path
            != config[
                "url_path"
            ]
        ):
            errors.append(
                (
                    f"{title} -> "
                    "URL path yanlış. "
                    f"Beklenen={config['url_path']}, "
                    f"Gerçek={actual_path}"
                )
            )

    print(
        "Eksik ürün:",
        len(missing_products)
    )

    print(
        "Beklenmeyen ürün:",
        len(unexpected_products)
    )

    # =====================================================
    # SEMANTİK RAW KONTROLÜ
    # =====================================================

    print()
    print(
        "[6/6] Ham metin semantik kontrol ediliyor..."
    )

    for title, config in (
        EXPECTED_PRODUCTS.items()
    ):

        if title not in products_by_title:
            continue

        product = products_by_title[
            title
        ]

        text = product.get(
            "ham_metin",
            ""
        )

        text_lower = tr_lower(
            text
        )

        print()
        print(
            "-",
            title
        )

        print(
            "  Metin uzunluğu:",
            len(text)
        )

        if len(text) < 150:
            errors.append(
                (
                    f"{title} -> "
                    "ham metin çok kısa."
                )
            )

        for required_term in config[
            "required_terms"
        ]:

            found = (
                tr_lower(
                    required_term
                )
                in text_lower
            )

            print(
                (
                    "  "
                    + (
                        "✓"
                        if found
                        else "✗"
                    )
                    + " "
                    + required_term
                )
            )

            if not found:
                errors.append(
                    (
                        f"{title} -> "
                        "beklenen ifade yok: "
                        f"{required_term}"
                    )
                )

        forbidden_list = (
            FORBIDDEN_CONTAMINATION.get(
                title,
                []
            )
        )

        for forbidden in forbidden_list:

            if (
                tr_lower(
                    forbidden
                )
                in text_lower
            ):
                errors.append(
                    (
                        f"{title} -> "
                        "başka ürün içeriği karışmış: "
                        f"{forbidden}"
                    )
                )

        # CTA yalnız başına problem değil.
        if (
            title
            == "Eğitim Finansmanı Sistemi"
            and "hemen avantajlı olmak için tıklayın"
            in text_lower
        ):
            warnings.append(
                (
                    "Eğitim Finansmanı Sistemi -> "
                    "'Hemen Avantajlı Olmak için Tıklayın!' "
                    "CTA metni mevcut. "
                    "Semantik contamination olarak değerlendirilmedi."
                )
            )

    # =====================================================
    # ÖZEL ÇAPRAZ KONTROLLER
    # =====================================================

    if (
        "Bana Bunu Al"
        in products_by_title
    ):

        text = tr_lower(
            products_by_title[
                "Bana Bunu Al"
            ][
                "ham_metin"
            ]
        )

        if (
            "50.000"
            not in text
        ):
            errors.append(
                (
                    "Bana Bunu Al -> "
                    "50.000 TL üst limit kayıp."
                )
            )

        if (
            "18 aya"
            not in text
        ):
            errors.append(
                (
                    "Bana Bunu Al -> "
                    "18 ay vade bilgisi kayıp."
                )
            )

    if (
        "Bana Bunu Al İş Ortağım"
        in products_by_title
    ):

        text = tr_lower(
            products_by_title[
                "Bana Bunu Al İş Ortağım"
            ][
                "ham_metin"
            ]
        )

        if (
            "24 aya"
            not in text
        ):
            errors.append(
                (
                    "Bana Bunu Al İş Ortağım -> "
                    "24 ay vade bilgisi kayıp."
                )
            )

    if (
        "Eğitim Finansmanı Sistemi"
        in products_by_title
    ):

        text = tr_lower(
            products_by_title[
                "Eğitim Finansmanı Sistemi"
            ][
                "ham_metin"
            ]
        )

        if (
            "600.000"
            not in text
        ):
            errors.append(
                (
                    "Eğitim Finansmanı Sistemi -> "
                    "600.000 TL üst limit kayıp."
                )
            )

        if (
            "3 ay erteleme"
            not in text
        ):
            errors.append(
                (
                    "Eğitim Finansmanı Sistemi -> "
                    "3 ay erteleme bilgisi kayıp."
                )
            )

    # =====================================================
    # FINAL
    # =====================================================

    print()
    print(
        "=" * 110
    )

    print(
        "VALIDATION SONUCU"
    )

    print(
        "=" * 110
    )

    print(
        "Beklenen kayıt:",
        EXPECTED_COUNT
    )

    print(
        "Gerçek kayıt:",
        len(products)
    )

    print(
        "HTTP hata:",
        len(http_errors)
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
        "Eksik ürün:",
        len(missing_products)
    )

    print(
        "Beklenmeyen ürün:",
        len(unexpected_products)
    )

    print(
        "Warning:",
        len(warnings)
    )

    print(
        "Error:",
        len(errors)
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
                "SONUÇ: HAYAT FİNANS "
                "FİNANSMAN RAW VALIDATION BAŞARILI ✅"
            )
        )

    else:

        print(
            (
                "SONUÇ: HAYAT FİNANS "
                "FİNANSMAN RAW VALIDATION BAŞARISIZ ❌"
            )
        )

    print(
        "=" * 110
    )


if __name__ == "__main__":
    main()