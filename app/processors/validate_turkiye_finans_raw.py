import json
import re
from urllib.parse import urlparse


INPUT_FILE = (
    "data/raw/"
    "turkiye_finans_finansman_urunleri.json"
)


EXPECTED_BANK = (
    "Türkiye Finans Katılım Bankası"
)

EXPECTED_RECORD_TYPE = (
    "finansman"
)

EXPECTED_PRODUCT_COUNT = 16


REQUIRED_FIELDS = [
    "banka",
    "kayit_turu",
    "urun_adi",
    "kaynak_url",
    "ham_metin"
]


# =========================================================
# TÜRKÇE NORMALİZASYON
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

    return re.sub(
        r"\s+",
        " ",
        str(value or "")
    ).strip()


def canonical_url(url):

    return (
        normalize_text(
            url
        )
        .rstrip("/")
        .casefold()
    )


# =========================================================
# DOMAIN
# =========================================================

def get_domain(url):

    try:

        return (
            urlparse(
                url
            )
            .netloc
            .casefold()
        )

    except Exception:

        return ""


def valid_domain(url):

    domain = get_domain(
        url
    )

    return domain in {
        "www.turkiyefinans.com.tr",
        "turkiyefinans.com.tr",
        "www.hizlifinansman.com.tr",
        "hizlifinansman.com.tr"
    }


# =========================================================
# BAŞLIK METİN İÇİNDE Mİ?
# =========================================================

def title_in_text(
    title,
    text
):

    title_normalized = tr_lower(
        title
    )

    text_normalized = tr_lower(
        text
    )


    # Hızlı Finansman ürünlerinde dataset başlığına
    # "Hızlı Finansman - " prefix'i eklenmiş durumda.
    if title_normalized.startswith(
        tr_lower(
            "Hızlı Finansman - "
        )
    ):

        title_normalized = (
            title_normalized[
                len(
                    tr_lower(
                        "Hızlı Finansman - "
                    )
                ):
            ]
        )


    # Türkiye Finans title'larında:
    #
    # İhtiyaç Finansmanı (İhtiyaç Kredisi)*
    #
    # gibi parantez açıklamaları bulunabiliyor.
    simple_title = re.sub(
        r"\s*\([^)]*\)\s*\*?\s*$",
        "",
        title_normalized
    ).strip()


    if (
        title_normalized
        in text_normalized
    ):

        return True


    if (
        simple_title
        and simple_title
        in text_normalized
    ):

        return True


    return False


# =========================================================
# KRİTİK ÜRÜNLER
# =========================================================

def critical_product_check(
    products
):

    titles = [
        tr_lower(
            product[
                "urun_adi"
            ]
        )

        for product
        in products
    ]


    required_groups = {
        "İhtiyaç Finansmanı": [
            "ihtiyaç finansmanı"
        ],

        "Taşıt Finansmanı": [
            "taşıt finansmanı"
        ],

        "Konut Finansmanı": [
            "konut finansmanı"
        ],

        "Arsa Finansmanı": [
            "arsa finansmanı"
        ],

        "İş Yeri Finansmanı": [
            "iş yeri finansmanı"
        ],

        "eXtra Limit": [
            "extra limit"
        ],

        "Dijital İhtiyaç Finansmanı": [
            "dijital ihtiyaç finansmanı"
        ],

        "Trendyol Alışveriş Finansmanı": [
            "trendyol alışveriş finansmanı"
        ],

        "Dijital Taşıt Finansmanı": [
            "dijital taşıt finansmanı"
        ],

        "Motosiklet Finansmanı": [
            "motosiklet finansmanı"
        ],

        "Ticari Hat / Ticari Plaka": [
            "ticari hat",
            "ticari plaka"
        ],

        "Taksitli Ticari Taşıt": [
            "taksitli ticari taşıt"
        ],

        "Hızlı Finansman - İhtiyaç": [
            "hızlı finansman",
            "ihtiyaç finansmanı"
        ],

        "Hızlı Finansman - Eğitim": [
            "hızlı finansman",
            "eğitim finansmanı"
        ],

        "Hızlı Finansman - Taşıt": [
            "hızlı finansman",
            "taşıt finansmanı"
        ],

        "Hızlı Finansman - Motosiklet": [
            "hızlı finansman",
            "motosiklet finansmanı"
        ]
    }


    missing = []


    for group_name, keywords in (
        required_groups.items()
    ):

        normalized_keywords = [
            tr_lower(
                keyword
            )

            for keyword
            in keywords
        ]


        found = False


        for title in titles:

            if all(
                keyword
                in title

                for keyword
                in normalized_keywords
            ):

                found = True

                break


        if not found:

            missing.append(
                group_name
            )


    return missing


# =========================================================
# HIZLI FİNANSMAN İÇERİK SAĞLIĞI
# =========================================================

def validate_hizli_product(
    product
):

    problems = []


    title = product[
        "urun_adi"
    ]

    text = product[
        "ham_metin"
    ]


    lower = tr_lower(
        text
    )


    if len(
        text
    ) < 1000:

        problems.append(
            "1000 karakterden kısa"
        )


    if (
        "başvuru"
        not in lower
    ):

        problems.append(
            "başvuru bilgisi yok"
        )


    if (
        "vade"
        not in lower
    ):

        problems.append(
            "vade bilgisi yok"
        )


    kar_present = (
        "kâr oran"
        in lower

        or "kar oran"
        in lower

        or "kâr pay"
        in lower

        or "kar pay"
        in lower
    )


    if not kar_present:

        problems.append(
            "kâr oranı bilgisi yok"
        )


    return problems


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 80
    )

    print(
        "TÜRKİYE FİNANS RAW VALIDATOR"
    )

    print(
        "=" * 80
    )


    # =====================================================
    # JSON OKU
    # =====================================================

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(
            file
        )


    products = data.get(
        "urunler",
        []
    )


    declared_count = data.get(
        "urun_sayisi"
    )


    print()

    print(
        "JSON urun_sayisi:",
        declared_count
    )


    print(
        "Gerçek ürün sayısı:",
        len(
            products
        )
    )


    # =====================================================
    # SAYAÇLAR
    # =====================================================

    missing_schema = []

    wrong_bank = []

    wrong_type = []

    empty_title = []

    empty_url = []

    empty_text = []

    short_text = []

    title_not_in_text = []

    invalid_domains = []

    hizli_problems = []

    duplicate_urls = []

    duplicate_contents = []

    duplicate_titles = []


    seen_urls = set()

    seen_contents = set()

    seen_titles = set()


    # =====================================================
    # TEK TEK KONTROL
    # =====================================================

    for index, product in enumerate(
        products,
        start=1
    ):

        title = normalize_text(
            product.get(
                "urun_adi",
                ""
            )
        )


        url = normalize_text(
            product.get(
                "kaynak_url",
                ""
            )
        )


        text = str(
            product.get(
                "ham_metin",
                ""
            )
        ).strip()


        print()

        print(
            "-" * 80
        )


        print(
            f"[{index}/{len(products)}]"
        )


        print(
            "Ürün:",
            title
        )


        print(
            "Metin uzunluğu:",
            len(
                text
            )
        )


        print(
            "Domain:",
            get_domain(
                url
            )
        )


        # =================================================
        # ŞEMA
        # =================================================

        missing = [
            field

            for field
            in REQUIRED_FIELDS

            if field not in product
        ]


        if missing:

            missing_schema.append(
                {
                    "urun": title,
                    "alanlar": missing
                }
            )


        # =================================================
        # BANKA
        # =================================================

        if (
            product.get(
                "banka"
            )
            != EXPECTED_BANK
        ):

            wrong_bank.append(
                title
            )


        # =================================================
        # TÜR
        # =================================================

        if (
            product.get(
                "kayit_turu"
            )
            != EXPECTED_RECORD_TYPE
        ):

            wrong_type.append(
                title
            )


        # =================================================
        # BOŞ
        # =================================================

        if not title:

            empty_title.append(
                index
            )


        if not url:

            empty_url.append(
                title
            )


        if not text:

            empty_text.append(
                title
            )


        # =================================================
        # METİN UZUNLUĞU
        # =================================================

        if (
            text
            and len(
                text
            ) < 500
        ):

            short_text.append(
                (
                    title,
                    len(
                        text
                    )
                )
            )


        # =================================================
        # BAŞLIK METİNDE
        # =================================================

        title_found = (
            title_in_text(
                title,
                text
            )
            if title and text
            else False
        )


        print(
            "Başlık metinde:",
            (
                "EVET"
                if title_found
                else "HAYIR"
            )
        )


        if (
            title
            and text
            and not title_found
        ):

            title_not_in_text.append(
                title
            )


        # =================================================
        # DOMAIN
        # =================================================

        domain_ok = valid_domain(
            url
        )


        print(
            "Domain geçerli:",
            (
                "EVET"
                if domain_ok
                else "HAYIR"
            )
        )


        if not domain_ok:

            invalid_domains.append(
                (
                    title,
                    url
                )
            )


        # =================================================
        # URL DUPLICATE
        # =================================================

        url_key = canonical_url(
            url
        )


        if url_key:

            if (
                url_key
                in seen_urls
            ):

                duplicate_urls.append(
                    (
                        title,
                        url
                    )
                )

            else:

                seen_urls.add(
                    url_key
                )


        # =================================================
        # TITLE DUPLICATE
        # =================================================

        title_key = tr_lower(
            title
        )


        if title_key:

            if (
                title_key
                in seen_titles
            ):

                duplicate_titles.append(
                    title
                )

            else:

                seen_titles.add(
                    title_key
                )


        # =================================================
        # CONTENT DUPLICATE
        # =================================================

        content_key = tr_lower(
            normalize_text(
                text
            )
        )


        if content_key:

            if (
                content_key
                in seen_contents
            ):

                duplicate_contents.append(
                    title
                )

            else:

                seen_contents.add(
                    content_key
                )


        # =================================================
        # HIZLI FİNANSMAN
        # =================================================

        if (
            "hizlifinansman.com.tr"
            in get_domain(
                url
            )
        ):

            problems = (
                validate_hizli_product(
                    product
                )
            )


            print(
                "Hızlı içerik:",
                (
                    "SAĞLIKLI"
                    if not problems
                    else "SORUNLU"
                )
            )


            if problems:

                hizli_problems.append(
                    {
                        "urun": title,
                        "sorunlar": problems
                    }
                )


    # =====================================================
    # KRİTİK ÜRÜNLER
    # =====================================================

    missing_critical = (
        critical_product_check(
            products
        )
    )


    # =====================================================
    # MIN / MAX / ORTALAMA
    # =====================================================

    lengths = [
        len(
            str(
                product.get(
                    "ham_metin",
                    ""
                )
            )
        )

        for product
        in products
    ]


    min_length = (
        min(
            lengths
        )
        if lengths
        else 0
    )


    max_length = (
        max(
            lengths
        )
        if lengths
        else 0
    )


    avg_length = (
        sum(
            lengths
        )
        / len(
            lengths
        )
        if lengths
        else 0
    )


    # =====================================================
    # RAPOR
    # =====================================================

    print()

    print(
        "=" * 80
    )

    print(
        "RAW VALIDATION ÖZETİ"
    )

    print(
        "=" * 80
    )


    print(
        "Beklenen ürün:",
        EXPECTED_PRODUCT_COUNT
    )


    print(
        "JSON urun_sayisi:",
        declared_count
    )


    print(
        "Gerçek ürün:",
        len(
            products
        )
    )


    print(
        "Minimum metin:",
        min_length
    )


    print(
        "Maksimum metin:",
        max_length
    )


    print(
        "Ortalama metin:",
        round(
            avg_length,
            2
        )
    )


    print()

    print(
        "Eksik şema:",
        len(
            missing_schema
        )
    )


    print(
        "Yanlış banka:",
        len(
            wrong_bank
        )
    )


    print(
        "Yanlış kayıt türü:",
        len(
            wrong_type
        )
    )


    print(
        "Boş başlık:",
        len(
            empty_title
        )
    )


    print(
        "Boş URL:",
        len(
            empty_url
        )
    )


    print(
        "Boş ham metin:",
        len(
            empty_text
        )
    )


    print(
        "500 karakterden kısa:",
        len(
            short_text
        )
    )


    print(
        "Başlığı metinde olmayan:",
        len(
            title_not_in_text
        )
    )


    print(
        "Geçersiz domain:",
        len(
            invalid_domains
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
        "Duplicate içerik:",
        len(
            duplicate_contents
        )
    )


    print(
        "Hızlı Finansman sorunu:",
        len(
            hizli_problems
        )
    )


    print(
        "Eksik kritik ürün:",
        len(
            missing_critical
        )
    )


    # =====================================================
    # SORUN DETAYLARI
    # =====================================================

    if missing_schema:

        print()

        print(
            "EKSİK ŞEMA:"
        )


        for item in missing_schema:

            print(
                "-",
                item
            )


    if short_text:

        print()

        print(
            "KISA METİNLER:"
        )


        for item in short_text:

            print(
                "-",
                item
            )


    if title_not_in_text:

        print()

        print(
            "BAŞLIK METİNDE YOK:"
        )


        for item in title_not_in_text:

            print(
                "-",
                item
            )


    if invalid_domains:

        print()

        print(
            "GEÇERSİZ DOMAIN:"
        )


        for item in invalid_domains:

            print(
                "-",
                item
            )


    if duplicate_urls:

        print()

        print(
            "DUPLICATE URL:"
        )


        for item in duplicate_urls:

            print(
                "-",
                item
            )


    if duplicate_titles:

        print()

        print(
            "DUPLICATE BAŞLIK:"
        )


        for item in duplicate_titles:

            print(
                "-",
                item
            )


    if duplicate_contents:

        print()

        print(
            "DUPLICATE İÇERİK:"
        )


        for item in duplicate_contents:

            print(
                "-",
                item
            )


    if hizli_problems:

        print()

        print(
            "HIZLI FİNANSMAN SORUNLARI:"
        )


        for item in hizli_problems:

            print(
                "-",
                item[
                    "urun"
                ]
            )


            for problem in (
                item[
                    "sorunlar"
                ]
            ):

                print(
                    "   ",
                    problem
                )


    if missing_critical:

        print()

        print(
            "EKSİK KRİTİK ÜRÜNLER:"
        )


        for item in missing_critical:

            print(
                "-",
                item
            )


    # =====================================================
    # FINAL HEALTH
    # =====================================================

    healthy = all(
        [
            declared_count
            == EXPECTED_PRODUCT_COUNT,

            len(products)
            == EXPECTED_PRODUCT_COUNT,

            len(missing_schema)
            == 0,

            len(wrong_bank)
            == 0,

            len(wrong_type)
            == 0,

            len(empty_title)
            == 0,

            len(empty_url)
            == 0,

            len(empty_text)
            == 0,

            len(short_text)
            == 0,

            len(title_not_in_text)
            == 0,

            len(invalid_domains)
            == 0,

            len(duplicate_urls)
            == 0,

            len(duplicate_titles)
            == 0,

            len(duplicate_contents)
            == 0,

            len(hizli_problems)
            == 0,

            len(missing_critical)
            == 0
        ]
    )


    print()

    print(
        "=" * 80
    )


    if healthy:

        print(
            "SONUÇ: TÜRKİYE FİNANS RAW "
            "FİNANSMAN VERİSİ SAĞLIKLI ✅"
        )

    else:

        print(
            "SONUÇ: TÜRKİYE FİNANS RAW "
            "FİNANSMAN VERİSİNDE "
            "SORUN VAR ⚠️"
        )


    print(
        "=" * 80
    )


if __name__ == "__main__":

    main()