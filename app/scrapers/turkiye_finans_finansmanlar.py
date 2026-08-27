import json
import os
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


OUTPUT_FILE = (
    "data/raw/"
    "turkiye_finans_finansman_urunleri.json"
)


TURKIYE_FINANS_BASE = (
    "https://www.turkiyefinans.com.tr"
)

TURKIYE_FINANS_SITE_MAP = (
    "https://www.turkiyefinans.com.tr/"
    "tr-tr/Sayfalar/site-haritasi.aspx"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 "
        "Safari/537.36"
    )
}


MAIN_TARGET_NAMES = [
    "İhtiyaç Finansmanı",

    "eXtra Limit",

    "Dijital İhtiyaç Finansmanı",
    "Dijital İhtiyaç Kredisi",

    "Trendyol Alışveriş Finansmanı",

    "Taşıt Finansmanı",

    "Dijital Taşıt Finansmanı",

    "Motosiklet Finansmanı",
    "Motosiklet Kredisi",

    "Ticari Hat / Ticari Plaka Finansmanı",
    "Ticari Hat / Ticari Plaka Kredisi",

    "Taksitli Ticari Taşıt Finansmanı",
    "Taksitli Ticari Taşıt Kredisi",

    "Konut Finansmanı",

    "Arsa Finansmanı",

    "İş yeri Finansmanı",
    "İş Yeri Finansmanı"
]


HIZLI_FINANSMAN_PRODUCTS = [
    {
        "urun_adi": (
            "Hızlı Finansman - "
            "İhtiyaç Finansmanı"
        ),

        "url": (
            "https://www.hizlifinansman.com.tr/"
            "finansman-urunleri/Sayfalar/"
            "ihtiyac-finansmani.aspx"
        )
    },

    {
        "urun_adi": (
            "Hızlı Finansman - "
            "Eğitim Finansmanı"
        ),

        "url": (
            "https://www.hizlifinansman.com.tr/"
            "finansman-urunleri/Sayfalar/"
            "egitim-finansmani.aspx"
        )
    },

    {
        "urun_adi": (
            "Hızlı Finansman - "
            "Taşıt Finansmanı"
        ),

        "url": (
            "https://www.hizlifinansman.com.tr/"
            "finansman-urunleri/Sayfalar/"
            "tasit-finansmani.aspx"
        )
    },

    {
        "urun_adi": (
            "Hızlı Finansman - "
            "Motosiklet Finansmanı"
        ),

        "url": (
            "https://www.hizlifinansman.com.tr/"
            "finansman-urunleri/Sayfalar/"
            "motosiklet-finansmani.aspx"
        )
    }
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


# =========================================================
# URL
# =========================================================

def normalize_url(
    base_url,
    url
):

    if not url:

        return ""


    url = urljoin(
        base_url,
        url
    )


    url = url.split(
        "#"
    )[0]


    url = url.split(
        "?"
    )[0]


    return url.rstrip(
        "/"
    )


def canonical_url_key(url):

    return tr_lower(
        normalize_text(
            url
        ).rstrip("/")
    )


# =========================================================
# DOMAIN
# =========================================================

def get_host(url):

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


def is_turkiye_finans_url(url):

    return get_host(
        url
    ) in {
        "www.turkiyefinans.com.tr",
        "turkiyefinans.com.tr"
    }


def is_hizli_finansman_url(url):

    return get_host(
        url
    ) in {
        "www.hizlifinansman.com.tr",
        "hizlifinansman.com.tr"
    }


# =========================================================
# ANA SİTE TARGET
# =========================================================

def is_main_target_name(text):

    text_lower = tr_lower(
        normalize_text(
            text
        )
    )


    if (
        text_lower
        == tr_lower(
            "Hızlı Finansman"
        )
    ):

        return False


    for name in MAIN_TARGET_NAMES:

        if (
            tr_lower(
                name
            )
            in text_lower
        ):

            return True


    return False


# =========================================================
# ANA SİTE LİNKLERİ
# =========================================================

def get_main_finance_links():

    response = requests.get(
        TURKIYE_FINANS_SITE_MAP,
        headers=HEADERS,
        timeout=30
    )


    print(
        "Türkiye Finans site haritası HTTP:",
        response.status_code
    )


    response.raise_for_status()


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    candidates = []


    for anchor in soup.find_all(
        "a",
        href=True
    ):

        anchor_text = normalize_text(
            anchor.get_text(
                " ",
                strip=True
            )
        )


        if not anchor_text:

            continue


        if not is_main_target_name(
            anchor_text
        ):

            continue


        url = normalize_url(
            TURKIYE_FINANS_BASE,
            anchor.get(
                "href"
            )
        )


        if not url:

            continue


        if not is_turkiye_finans_url(
            url
        ):

            continue


        url_lower = tr_lower(
            url
        )


        if (
            "/tr-tr/bireysel/"
            not in url_lower
        ):

            continue


        if (
            "/kampanyalar/"
            in url_lower
        ):

            continue


        candidates.append(
            {
                "kaynak_kanal": (
                    "Türkiye Finans"
                ),

                "liste_basligi": (
                    anchor_text
                ),

                "url": url
            }
        )


    unique_items = []

    seen_urls = set()


    for item in candidates:

        key = canonical_url_key(
            item[
                "url"
            ]
        )


        if key in seen_urls:

            continue


        seen_urls.add(
            key
        )


        unique_items.append(
            item
        )


    return unique_items


# =========================================================
# KRİTİK ANA SİTE SAYFALARI
# =========================================================

def add_critical_main_pages(items):

    critical_pages = [
        {
            "kaynak_kanal": (
                "Türkiye Finans"
            ),

            "liste_basligi": (
                "Ticari Hat / "
                "Ticari Plaka Finansmanı"
            ),

            "url": (
                "https://www.turkiyefinans.com.tr/"
                "tr-tr/bireysel/tasit-finansmani/"
                "Sayfalar/"
                "taksitli-ticari-tasit-finansmani.aspx"
            )
        },

        {
            "kaynak_kanal": (
                "Türkiye Finans"
            ),

            "liste_basligi": (
                "Taksitli Ticari "
                "Taşıt Finansmanı"
            ),

            "url": (
                "https://www.turkiyefinans.com.tr/"
                "tr-tr/bireysel/tasit-finansmani/"
                "Sayfalar/"
                "ticari-hat-ticari-plaka-finansmani.aspx"
            )
        }
    ]


    seen = {
        canonical_url_key(
            item[
                "url"
            ]
        )

        for item
        in items
    }


    for item in critical_pages:

        key = canonical_url_key(
            item[
                "url"
            ]
        )


        if key in seen:

            continue


        seen.add(
            key
        )


        items.append(
            item
        )


    return items


# =========================================================
# HIZLI FİNANSMAN LİNKLERİ
# =========================================================

def get_hizli_finansman_links():

    results = []


    for product in HIZLI_FINANSMAN_PRODUCTS:

        results.append(
            {
                "kaynak_kanal": (
                    "Hızlı Finansman"
                ),

                "liste_basligi": (
                    product[
                        "urun_adi"
                    ]
                ),

                "url": (
                    product[
                        "url"
                    ]
                )
            }
        )


    return results


# =========================================================
# TITLE
# =========================================================

def clean_title(title):

    title = normalize_text(
        title
    )


    suffixes = [
        "| Türkiye Finans",
        "- Türkiye Finans",

        "| Türkiye Finans Katılım Bankası",
        "- Türkiye Finans Katılım Bankası",

        "| Hızlı Finansman",
        "- Hızlı Finansman",

        "| Türkiye Finans Hızlı Finansman",
        "- Türkiye Finans Hızlı Finansman"
    ]


    for suffix in suffixes:

        if title.endswith(
            suffix
        ):

            title = title[
                :-len(suffix)
            ].strip()


    return title


def find_page_title(soup):

    h1 = soup.find(
        "h1"
    )


    if h1:

        title = clean_title(
            h1.get_text(
                " ",
                strip=True
            )
        )


        if title:

            return title


    og_title = soup.find(
        "meta",
        attrs={
            "property": "og:title"
        }
    )


    if og_title:

        title = clean_title(
            og_title.get(
                "content",
                ""
            )
        )


        if title:

            return title


    if soup.title:

        title = clean_title(
            soup.title.get_text(
                " ",
                strip=True
            )
        )


        if title:

            return title


    return ""


# =========================================================
# STRINGS
# =========================================================

def get_container_strings(container):

    strings = []


    if container is None:

        return strings


    for value in container.stripped_strings:

        value = normalize_text(
            value
        )


        if not value:

            continue


        lower = tr_lower(
            value
        )


        if value in {
            "Sayfayı Yazdır",
            "Facebook'da Paylaş",
            "Twitter'da Paylaş",
            "Linkedin'de Paylaş",
            "BAŞA DÖN"
        }:

            continue


        if (
            "çerez"
            in lower
            and len(value) < 150
        ):

            continue


        strings.append(
            value
        )


    return strings


# =========================================================
# BAŞLIKTAN BAŞLAT
# =========================================================

def slice_from_title(
    strings,
    page_title,
    prefer_last=False
):

    title_lower = tr_lower(
        page_title
    )


    indexes = []


    for index, value in enumerate(
        strings
    ):

        if (
            tr_lower(
                value
            )
            == title_lower
        ):

            indexes.append(
                index
            )


    if not indexes:

        return strings


    # =====================================================
    # HIZLI FİNANSMAN
    #
    # Aynı ürün adı menülerde birkaç kez geçiyor.
    # Gerçek H1 çoğunlukla son eşleşmedir.
    # =====================================================

    if prefer_last:

        return strings[
            indexes[-1]:
        ]


    # =====================================================
    # TÜRKİYE FİNANS
    # =====================================================

    selected_index = None


    for index in indexes:

        lookahead = " ".join(
            strings[
                index + 1:
                index + 10
            ]
        )


        if len(
            lookahead
        ) >= 100:

            selected_index = index

            break


    if selected_index is None:

        selected_index = indexes[
            -1
        ]


    return strings[
        selected_index:
    ]


# =========================================================
# FOOTER KES
# =========================================================

def cut_footer(
    strings,
    is_hizli
):

    common_stops = {
        "Müşteri Memnuniyet Merkezi",
        "Yatırımcı İlişkileri",
        "Finans Portalı",
        "Şube ve ATM'ler",
        "Şube ve ATM’ler",
        "Gizlilik Politikamız",
        "Türkiye Finans Linkleri",
        "Türkiye Finans Blog",
        "Site Haritası",
        "İnsan Kaynakları"
    }


    hizli_stops = {
        "Toplama Resmi",
        "Ürün ve Hizmet Ücretleri",
        "Kişisel Verilerin Korunması",
        "Bilgi Toplumu Hizmetleri",
        "Sözleşmeler ve Bilgi Formları"
    }


    cleaned = []


    for value in strings:

        if (
            value in common_stops
            and len(cleaned) >= 10
        ):

            break


        if (
            is_hizli
            and value in hizli_stops
            and len(cleaned) >= 10
        ):

            break


        cleaned.append(
            value
        )


    return cleaned


# =========================================================
# MAIN TEXT
# =========================================================

def extract_main_text(
    soup,
    page_title,
    source_channel
):

    is_hizli = (
        source_channel
        == "Hızlı Finansman"
    )


    # =====================================================
    # HIZLI FİNANSMAN
    #
    # <main> alanı gerçek içeriğin yalnızca küçük
    # bölümünü içerdiği için BODY kullanıyoruz.
    # =====================================================

    if is_hizli:

        container = soup.body


        strings = get_container_strings(
            container
        )


        strings = slice_from_title(
            strings,
            page_title,
            prefer_last=True
        )


        strings = cut_footer(
            strings,
            is_hizli=True
        )


        return "\n".join(
            strings
        )


    # =====================================================
    # NORMAL TÜRKİYE FİNANS
    # =====================================================

    candidate_containers = []


    main = soup.find(
        "main"
    )


    if main is not None:

        candidate_containers.append(
            main
        )


    for selector_id in [
        "DeltaPlaceHolderMain",
        "ctl00_PlaceHolderMain",
        "contentBox",
        "content",
        "main-content",
        "page-content"
    ]:

        container = soup.find(
            id=selector_id
        )


        if (
            container is not None
            and container
            not in candidate_containers
        ):

            candidate_containers.append(
                container
            )


    if not candidate_containers:

        candidate_containers.append(
            soup.body
        )


    best_strings = []


    for container in candidate_containers:

        current_strings = (
            get_container_strings(
                container
            )
        )


        current_strings = (
            slice_from_title(
                current_strings,
                page_title,
                prefer_last=False
            )
        )


        current_strings = cut_footer(
            current_strings,
            is_hizli=False
        )


        current_length = len(
            "\n".join(
                current_strings
            )
        )


        best_length = len(
            "\n".join(
                best_strings
            )
        )


        if current_length > best_length:

            best_strings = (
                current_strings
            )


    return "\n".join(
        best_strings
    )


# =========================================================
# HIZLI FİNANSMAN İÇERİK SAĞLIK KONTROLÜ
# =========================================================

def validate_hizli_content(
    title,
    raw_text
):

    lower = tr_lower(
        raw_text
    )


    problems = []


    if len(
        raw_text
    ) < 1000:

        problems.append(
            (
                "ham metin 1000 karakterden "
                "kısa"
            )
        )


    if (
        tr_lower(
            title.replace(
                "Hızlı Finansman - ",
                ""
            )
        )
        not in lower
    ):

        problems.append(
            "ürün adı metinde yok"
        )


    if (
        "başvuru"
        not in lower
    ):

        problems.append(
            "başvuru bölümü bulunamadı"
        )


    if (
        "vade"
        not in lower
    ):

        problems.append(
            "vade bilgisi bulunamadı"
        )


    return problems


# =========================================================
# TEK ÜRÜN SCRAPE
# =========================================================

def scrape_product(
    session,
    item
):

    url = item[
        "url"
    ]


    response = session.get(
        url,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True
    )


    print(
        "HTTP STATUS:",
        response.status_code
    )


    print(
        "Final URL:",
        response.url
    )


    if response.status_code != 200:

        return None


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    page_title = find_page_title(
        soup
    )


    if not page_title:

        print(
            "UYARI: Sayfa başlığı bulunamadı."
        )

        return None


    raw_text = extract_main_text(
        soup,
        page_title,
        item[
            "kaynak_kanal"
        ]
    )


    if not raw_text:

        print(
            "UYARI: Ham metin bulunamadı."
        )

        return None


    # =====================================================
    # HIZLI FİNANSMAN ÖZEL VALIDATION
    # =====================================================

    if (
        item[
            "kaynak_kanal"
        ]
        == "Hızlı Finansman"
    ):

        problems = (
            validate_hizli_content(
                page_title,
                raw_text
            )
        )


        if problems:

            print(
                "UYARI: Hızlı Finansman "
                "içeriği eksik görünüyor:"
            )


            for problem in problems:

                print(
                    " -",
                    problem
                )


            print(
                "Ham metin uzunluğu:",
                len(
                    raw_text
                )
            )


            return None


    else:

        if len(
            raw_text
        ) < 500:

            print(
                "UYARI: Ham metin çok kısa:",
                len(
                    raw_text
                )
            )

            return None


    # =====================================================
    # PRODUCT TITLE
    # =====================================================

    if (
        item[
            "kaynak_kanal"
        ]
        == "Hızlı Finansman"
    ):

        product_title = (
            "Hızlı Finansman - "
            + page_title
        )

    else:

        product_title = (
            page_title
        )


    return {
        "banka": (
            "Türkiye Finans Katılım Bankası"
        ),

        "kayit_turu": (
            "finansman"
        ),

        "urun_adi": (
            product_title
        ),

        "kaynak_url": (
            response.url
        ),

        "ham_metin": (
            raw_text
        )
    }


# =========================================================
# DUPLICATE
# =========================================================

def remove_duplicates(products):

    unique_products = []

    duplicate_products = []


    seen_urls = set()

    seen_contents = set()


    for product in products:

        url_key = canonical_url_key(
            product.get(
                "kaynak_url",
                ""
            )
        )


        text_key = tr_lower(
            normalize_text(
                product.get(
                    "ham_metin",
                    ""
                )
            )
        )


        if (
            url_key
            in seen_urls
        ):

            duplicate_products.append(
                {
                    "sebep": (
                        "duplicate URL"
                    ),

                    "urun": (
                        product
                    )
                }
            )

            continue


        if (
            text_key
            in seen_contents
        ):

            duplicate_products.append(
                {
                    "sebep": (
                        "duplicate içerik"
                    ),

                    "urun": (
                        product
                    )
                }
            )

            continue


        seen_urls.add(
            url_key
        )


        seen_contents.add(
            text_key
        )


        unique_products.append(
            product
        )


    return (
        unique_products,
        duplicate_products
    )


# =========================================================
# KRİTİK ÜRÜN KONTROLÜ
# =========================================================

def critical_product_check(products):

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

        "eXtra Limit": [
            "extra limit"
        ],

        "Dijital İhtiyaç": [
            "dijital ihtiyaç"
        ],

        "Trendyol": [
            "trendyol"
        ],

        "Taşıt Finansmanı": [
            "taşıt finansmanı"
        ],

        "Dijital Taşıt": [
            "dijital taşıt"
        ],

        "Motosiklet": [
            "motosiklet"
        ],

        "Ticari Hat / Ticari Plaka": [
            "ticari hat",
            "ticari plaka"
        ],

        "Taksitli Ticari Taşıt": [
            "taksitli ticari"
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
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 80
    )

    print(
        "TÜRKİYE FİNANS FİNANSMAN SCRAPER V3"
    )

    print(
        "=" * 80
    )


    # =====================================================
    # ANA TÜRKİYE FİNANS
    # =====================================================

    main_links = (
        get_main_finance_links()
    )


    main_links = (
        add_critical_main_pages(
            main_links
        )
    )


    # =====================================================
    # HIZLI FİNANSMAN
    # =====================================================

    hizli_links = (
        get_hizli_finansman_links()
    )


    all_links = (
        main_links
        + hizli_links
    )


    # =====================================================
    # URL DUPLICATE
    # =====================================================

    final_links = []

    seen_link_urls = set()


    for item in all_links:

        key = canonical_url_key(
            item[
                "url"
            ]
        )


        if key in seen_link_urls:

            continue


        seen_link_urls.add(
            key
        )


        final_links.append(
            item
        )


    print()

    print(
        "Ana Türkiye Finans linki:",
        len(
            main_links
        )
    )


    print(
        "Hızlı Finansman linki:",
        len(
            hizli_links
        )
    )


    print(
        "Toplam aday link:",
        len(
            final_links
        )
    )


    print()


    for index, item in enumerate(
        final_links,
        start=1
    ):

        print(
            f"{index}. "
            f"[{item['kaynak_kanal']}] "
            f"{item['liste_basligi']}"
        )


        print(
            "   ",
            item[
                "url"
            ]
        )


    # =====================================================
    # SCRAPE
    # =====================================================

    session = requests.Session()


    products = []

    failed_urls = []


    for index, item in enumerate(
        final_links,
        start=1
    ):

        print()

        print(
            "-" * 80
        )


        print(
            f"[{index}/{len(final_links)}]"
        )


        print(
            "Kanal:",
            item[
                "kaynak_kanal"
            ]
        )


        print(
            "Liste başlığı:",
            item[
                "liste_basligi"
            ]
        )


        print(
            "Çekiliyor:",
            item[
                "url"
            ]
        )


        try:

            product = scrape_product(
                session,
                item
            )


            if product:

                products.append(
                    product
                )


                print(
                    "Ürün:",
                    product[
                        "urun_adi"
                    ]
                )


                print(
                    "Ham metin uzunluğu:",
                    len(
                        product[
                            "ham_metin"
                        ]
                    )
                )


                # =========================================
                # HIZLI İÇİN EK KONTROL
                # =========================================

                if (
                    item[
                        "kaynak_kanal"
                    ]
                    == "Hızlı Finansman"
                ):

                    lower = tr_lower(
                        product[
                            "ham_metin"
                        ]
                    )


                    print(
                        "  Başvuru var:",
                        (
                            "EVET"
                            if "başvuru" in lower
                            else "HAYIR"
                        )
                    )


                    print(
                        "  Vade var:",
                        (
                            "EVET"
                            if "vade" in lower
                            else "HAYIR"
                        )
                    )


                    print(
                        "  Kâr oranı var:",
                        (
                            "EVET"
                            if (
                                "kâr oran"
                                in lower

                                or "kâr payı"
                                in lower

                                or "kar oran"
                                in lower
                            )
                            else "HAYIR"
                        )
                    )


            else:

                failed_urls.append(
                    item[
                        "url"
                    ]
                )


        except Exception as error:

            failed_urls.append(
                item[
                    "url"
                ]
            )


            print(
                "HATA:",
                repr(
                    error
                )
            )


        time.sleep(
            0.3
        )


    # =====================================================
    # DUPLICATE
    # =====================================================

    (
        products,
        duplicate_products
    ) = remove_duplicates(
        products
    )


    # =====================================================
    # KRİTİK
    # =====================================================

    missing_critical = (
        critical_product_check(
            products
        )
    )


    # =====================================================
    # JSON
    # =====================================================

    output = {
        "banka": (
            "Türkiye Finans Katılım Bankası"
        ),

        "kayit_turu": (
            "finansman"
        ),

        "urun_sayisi": (
            len(
                products
            )
        ),

        "urunler": (
            products
        )
    }


    os.makedirs(
        "data/raw",
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
    # RAPOR
    # =====================================================

    print()

    print(
        "=" * 80
    )

    print(
        "TÜRKİYE FİNANS SCRAPER V3 SONUCU"
    )

    print(
        "=" * 80
    )


    print(
        "Ana site aday link:",
        len(
            main_links
        )
    )


    print(
        "Hızlı Finansman aday link:",
        len(
            hizli_links
        )
    )


    print(
        "Toplam aday link:",
        len(
            final_links
        )
    )


    print(
        "Çekilen benzersiz ürün:",
        len(
            products
        )
    )


    print(
        "Duplicate:",
        len(
            duplicate_products
        )
    )


    print(
        "Başarısız URL:",
        len(
            failed_urls
        )
    )


    print(
        "Eksik kritik ürün:",
        len(
            missing_critical
        )
    )


    # =====================================================
    # DUPLICATE
    # =====================================================

    if duplicate_products:

        print()

        print(
            "DUPLICATE KAYITLAR:"
        )


        for item in (
            duplicate_products
        ):

            print(
                "-",
                item[
                    "sebep"
                ],
                ":",
                item[
                    "urun"
                ].get(
                    "urun_adi",
                    ""
                )
            )


    # =====================================================
    # FAILED
    # =====================================================

    if failed_urls:

        print()

        print(
            "BAŞARISIZ URL'LER:"
        )


        for url in failed_urls:

            print(
                "-",
                url
            )


    # =====================================================
    # MISSING
    # =====================================================

    if missing_critical:

        print()

        print(
            "EKSİK KRİTİK ÜRÜNLER:"
        )


        for name in missing_critical:

            print(
                "-",
                name
            )


    # =====================================================
    # FINAL LIST
    # =====================================================

    print()

    print(
        "=" * 80
    )

    print(
        "FINAL ÜRÜN LİSTESİ"
    )

    print(
        "=" * 80
    )


    for index, product in enumerate(
        products,
        start=1
    ):

        print(
            f"{index}. "
            f"{product['urun_adi']}"
        )


        print(
            "   Metin:",
            len(
                product[
                    "ham_metin"
                ]
            )
        )


        print(
            "   URL:",
            product[
                "kaynak_url"
            ]
        )


    # =====================================================
    # FINAL
    # =====================================================

    print()

    print(
        "=" * 80
    )


    if (
        len(products) == 16

        and len(
            failed_urls
        ) == 0

        and len(
            missing_critical
        ) == 0

        and len(
            duplicate_products
        ) == 0
    ):

        print(
            "SONUÇ: RAW FİNANSMAN VERİSİ "
            "İLK KONTROLDEN GEÇTİ ✅"
        )

    else:

        print(
            "SONUÇ: RAW FİNANSMAN VERİSİNDE "
            "KONTROL GEREKİYOR ⚠️"
        )


    print(
        "JSON:",
        OUTPUT_FILE
    )


    print(
        "=" * 80
    )


if __name__ == "__main__":

    main()