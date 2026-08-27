import json
import os
import time

from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.kuveytturk.com.tr"

FINANCE_URL = (
    "https://www.kuveytturk.com.tr/"
    "kendim-icin/finansmanlar"
)

OUTPUT_FILE = (
    "data/raw/"
    "kuveyt_turk_finansman_urunleri.json"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}


BROKEN_ALIAS_URLS = {
    (
        "https://www.kuveytturk.com.tr/"
        "kendim-icin/finansmanlar/"
        "surdurulebilir-finansmanlar/"
        "elektrikli-arac-sarj-unitesi-finansmani"
    ),

    (
        "https://www.kuveytturk.com.tr/"
        "kendim-icin/finansmanlar/"
        "surdurulebilir-finansmanlar/"
        "bisiklet-finansmani"
    )
}


# =========================================================
# URL
# =========================================================

def normalize_url(url):
    url = url.split("#")[0]
    url = url.split("?")[0]

    return url.rstrip("/")


def is_finance_detail_url(url):
    parsed = urlparse(url)

    parts = [
        part
        for part in parsed.path.strip("/").split("/")
        if part
    ]

    if len(parts) < 4:
        return False

    if parts[0] != "kendim-icin":
        return False

    if parts[1] != "finansmanlar":
        return False

    return True


# =========================================================
# LİNKLER
# =========================================================

def get_finance_links(session):

    response = session.get(
        FINANCE_URL,
        headers=HEADERS,
        timeout=30
    )

    print(
        "Finansman ana sayfası:",
        response.status_code
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    links = []

    ignored_aliases = []


    for a in soup.find_all(
        "a",
        href=True
    ):

        href = a.get(
            "href",
            ""
        ).strip()

        if not href:
            continue


        url = normalize_url(
            urljoin(
                BASE_URL,
                href
            )
        )


        if not is_finance_detail_url(
            url
        ):
            continue


        if url in BROKEN_ALIAS_URLS:

            if url not in ignored_aliases:

                ignored_aliases.append(
                    url
                )

            continue


        if url not in links:

            links.append(
                url
            )


    return (
        links,
        ignored_aliases
    )


# =========================================================
# BAŞLIK
# =========================================================

def clean_title(title):

    if not title:
        return ""


    title = " ".join(
        title.split()
    ).strip()


    suffixes = [
        " | Kuveyt Türk Katılım Bankası",
        " | Kuveyt Türk",
        " - Kuveyt Türk Katılım Bankası",
        " - Kuveyt Türk"
    ]


    for suffix in suffixes:

        if title.endswith(
            suffix
        ):

            title = title[
                :-len(suffix)
            ].strip()


    invalid = {
        "Kuveyt Türk",
        "Kuveyt Türk Katılım Bankası",
        "Finansmanlar",
        "Kendim İçin",
        "Ana Sayfa"
    }


    if title in invalid:
        return ""


    return title


def find_product_title(soup):

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


    og = soup.find(
        "meta",
        attrs={
            "property": "og:title"
        }
    )


    if og:

        title = clean_title(
            og.get(
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
# GERÇEK ÜRÜN İÇERİĞİNİN BAŞLANGICI
# =========================================================

def find_real_content_start(
    strings,
    product_title
):

    normalized_title = (
        product_title
        .casefold()
        .strip()
    )


    title_indexes = []


    for index, value in enumerate(
        strings
    ):

        if (
            value.casefold().strip()
            == normalized_title
        ):

            title_indexes.append(
                index
            )


    if not title_indexes:
        return 0


    # -----------------------------------------------------
    # Gerçek ürün başlığının hemen ardından genellikle
    # uzun bir açıklama/cümle geliyor.
    #
    # Menüde geçen ürün adlarının ardından ise başka
    # ürün isimleri geliyor.
    # -----------------------------------------------------

    for index in title_indexes:

        next_values = strings[
            index + 1:
            index + 4
        ]


        if not next_values:
            continue


        # En güçlü sinyal:
        # başlıktan hemen sonraki satır açıklama cümlesi
        if len(next_values[0]) >= 60:

            return index


        # Bazı sayfalarda kısa CTA satırı olabilir.
        if len(next_values) >= 2:

            first = next_values[0].casefold()

            if (
                first in {
                    "hemen başvur",
                    "başvur",
                    "detaylı bilgi"
                }
                and len(next_values[1]) >= 60
            ):

                return index


    # -----------------------------------------------------
    # Hiç güçlü eşleşme çıkmazsa:
    #
    # İlk occurrence header olabilir.
    # Son occurrence hesaplama başlığı olabilir.
    #
    # Ortalara yakın olan ikinci/üçüncü occurrence
    # çoğunlukla gerçek içeriktir.
    # -----------------------------------------------------

    if len(title_indexes) >= 3:

        return title_indexes[
            -2
        ]


    if len(title_indexes) >= 2:

        return title_indexes[
            1
        ]


    return title_indexes[
        0
    ]


# =========================================================
# ANA METİN
# =========================================================

def extract_main_text(
    soup,
    product_title
):

    container = soup.find(
        "main"
    )


    if container is None:

        container = soup.body


    if container is None:
        return ""


    strings = []


    for value in container.stripped_strings:

        value = " ".join(
            value.split()
        ).strip()


        if not value:
            continue


        lower = value.casefold()


        if value in {
            "×",
            "Yükleniyor..."
        }:
            continue


        if (
            "your browser does not support"
            in lower
        ):
            continue


        strings.append(
            value
        )


    if not strings:
        return ""


    start_index = find_real_content_start(
        strings,
        product_title
    )


    product_strings = strings[
        start_index:
    ]


    stop_titles = {
        "Faydalı Linkler",
        "Duyurular",
        "İlginizi Çekebilir",
        "Bize Yazın"
    }


    cleaned = []


    for value in product_strings:

        if (
            value in stop_titles
            and len(cleaned) > 3
        ):

            break


        cleaned.append(
            value
        )


    return "\n".join(
        cleaned
    )


# =========================================================
# TEK ÜRÜN
# =========================================================

def scrape_finance_product(
    session,
    url
):

    response = session.get(
        url,
        headers=HEADERS,
        timeout=30
    )


    print(
        "HTTP STATUS:",
        response.status_code
    )


    if response.status_code != 200:

        return None


    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    title = find_product_title(
        soup
    )


    if not title:

        print(
            "UYARI: Başlık bulunamadı."
        )

        return None


    text = extract_main_text(
        soup,
        title
    )


    if not text:

        print(
            "UYARI: Metin bulunamadı."
        )

        return None


    return {

        "banka": (
            "Kuveyt Türk Katılım Bankası"
        ),

        "kayit_turu": "finansman",

        "urun_adi": title,

        "kaynak_url": url,

        "ham_metin": text
    }


# =========================================================
# DUPLICATE
# =========================================================

def remove_duplicates(products):

    unique_products = []

    duplicates = []

    seen = set()


    for product in products:

        key = (
            product.get(
                "urun_adi",
                ""
            ).strip(),

            product.get(
                "ham_metin",
                ""
            ).strip()
        )


        if key in seen:

            duplicates.append(
                product
            )

            continue


        seen.add(
            key
        )

        unique_products.append(
            product
        )


    return (
        unique_products,
        duplicates
    )


# =========================================================
# MAIN
# =========================================================

def main():

    session = requests.Session()


    (
        links,
        ignored_aliases
    ) = get_finance_links(
        session
    )


    print()

    print(
        "Geçerli finansman linki:",
        len(links)
    )

    print(
        "Atlanan bozuk alias URL:",
        len(ignored_aliases)
    )


    print()


    for index, url in enumerate(
        links,
        start=1
    ):

        print(
            f"{index}. {url}"
        )


    print()


    products = []

    failed_urls = []


    for index, url in enumerate(
        links,
        start=1
    ):

        print(
            "-----------------------------------------"
        )

        print(
            f"[{index}/{len(links)}]"
        )

        print(
            "Çekiliyor:",
            url
        )


        try:

            product = scrape_finance_product(
                session,
                url
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


            else:

                failed_urls.append(
                    url
                )


        except Exception as error:

            failed_urls.append(
                url
            )

            print(
                "HATA:",
                error
            )


        time.sleep(
            0.3
        )


    (
        products,
        duplicates
    ) = remove_duplicates(
        products
    )


    # =====================================================
    # JSON
    # =====================================================

    output = {

        "banka": (
            "Kuveyt Türk Katılım Bankası"
        ),

        "kayit_turu": "finansman",

        "urun_sayisi": len(
            products
        ),

        "urunler": products
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
    # SONUÇ
    # =====================================================

    print()

    print(
        "=" * 70
    )

    print(
        "KUVEYT TÜRK FİNANSMAN SCRAPER SONUCU"
    )

    print(
        "=" * 70
    )


    print(
        "Geçerli link:",
        len(links)
    )

    print(
        "Atlanan bozuk alias:",
        len(ignored_aliases)
    )

    print(
        "Benzersiz ürün:",
        len(products)
    )

    print(
        "Duplicate:",
        len(duplicates)
    )

    print(
        "Başarısız gerçek URL:",
        len(failed_urls)
    )


    if duplicates:

        print()

        print(
            "Duplicate ürünler:"
        )

        for product in duplicates:

            print(
                "-",
                product[
                    "urun_adi"
                ],
                product[
                    "kaynak_url"
                ]
            )


    if failed_urls:

        print()

        print(
            "Başarısız URL'ler:"
        )

        for url in failed_urls:

            print(
                "-",
                url
            )


    print()

    print(
        "JSON:",
        OUTPUT_FILE
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()