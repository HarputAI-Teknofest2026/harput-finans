import json
import os
import re
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


# =========================================================
# AYARLAR
# =========================================================

BANK_NAME = "Hayat Finans Katılım Bankası"

BASE_URL = "https://hayatfinans.com.tr"

LIST_URL = "https://hayatfinans.com.tr/krediler"

OUTPUT_FILE = "data/raw/hayat_finans_finansman_urunleri.json"

TIMEOUT = 30

EXPECTED_COUNT = 3


EXPECTED_PRODUCTS = {
    "/krediler/bana-bunu-al": {
        "urun_adi": "Bana Bunu Al",
        "required_keywords": [
            "50.000",
            "18 aya",
        ],
    },

    "/finansmanlar/bana-bunu-al-is-ortagim": {
        "urun_adi": "Bana Bunu Al İş Ortağım",
        "required_keywords": [
            "24 aya",
            "İhtiyaca Dayalı Finansman",
        ],
    },

    "/krediler/hayat-finans-egitim-finansmani-sistemi": {
        "urun_adi": "Eğitim Finansmanı Sistemi",
        "required_keywords": [
            "600.000",
            "Eğitim Finansmanı",
            "3 ay erteleme",
        ],
    },
}


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
}


# =========================================================
# BAŞKA ÜRÜNDEN GELEN İÇERİKLER
# =========================================================

CONTAMINATION_MARKERS = [
    "Avantajlı Katılma Hesabı",
    "eşit ve yüksek kâr paylaşım oranı",
    "birikimlerinizi değerlendirirken",
]


# =========================================================
# METİN NORMALİZASYONU
# =========================================================

def clean_text(value):
    value = str(value or "")

    value = value.replace("\u00a0", " ")
    value = value.replace("\u200b", "")
    value = value.replace("\ufeff", "")

    value = value.replace("\r\n", "\n")
    value = value.replace("\r", "\n")

    value = re.sub(
        r"[ \t]+",
        " ",
        value
    )

    value = re.sub(
        r" *\n *",
        "\n",
        value
    )

    value = re.sub(
        r"\n{3,}",
        "\n\n",
        value
    )

    return value.strip()


def one_line(value):
    return re.sub(
        r"\s+",
        " ",
        clean_text(value)
    ).strip()


def tr_lower(value):
    value = str(value or "")

    value = value.replace("İ", "i")
    value = value.replace("I", "ı")

    return value.casefold()


# =========================================================
# URL
# =========================================================

def normalize_url(url):
    absolute = urljoin(
        BASE_URL,
        url
    )

    parsed = urlparse(
        absolute
    )

    normalized = parsed._replace(
        query="",
        fragment=""
    )

    return urlunparse(
        normalized
    ).rstrip("/")


def get_path(url):
    parsed = urlparse(
        normalize_url(url)
    )

    return parsed.path.rstrip("/")


def is_official_domain(url):
    host = urlparse(
        url
    ).netloc.lower()

    return (
        host == "hayatfinans.com.tr"
        or host == "www.hayatfinans.com.tr"
        or host.endswith(".hayatfinans.com.tr")
    )


# =========================================================
# HTTP
# =========================================================

def create_session():
    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    return session


def get_page(session, url):
    response = session.get(
        url,
        timeout=TIMEOUT,
        allow_redirects=True
    )

    response.raise_for_status()

    return response


# =========================================================
# TABLOLARI KORU
# =========================================================

def preserve_tables(soup):
    for table in soup.find_all("table"):

        rows = []

        for row in table.find_all("tr"):

            cells = row.find_all(
                ["th", "td"]
            )

            values = [
                one_line(
                    cell.get_text(
                        " ",
                        strip=True
                    )
                )
                for cell in cells
            ]

            values = [
                value
                for value in values
                if value
            ]

            if values:
                rows.append(
                    " | ".join(values)
                )

        if rows:
            replacement = soup.new_tag(
                "div"
            )

            replacement.string = (
                "\n"
                + "\n".join(rows)
                + "\n"
            )

            table.replace_with(
                replacement
            )


# =========================================================
# HTML TEMİZLEME
# =========================================================

def prepare_soup(html):
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    for tag in soup.find_all(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "iframe",
            "canvas",
        ]
    ):
        tag.decompose()

    preserve_tables(
        soup
    )

    return soup


# =========================================================
# ÜRÜN KEŞFİ
# =========================================================

def discover_products(html):
    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    discovered = {}

    for anchor in soup.find_all(
        "a",
        href=True
    ):

        href = anchor.get(
            "href",
            ""
        )

        if not href:
            continue

        url = normalize_url(
            href
        )

        if not is_official_domain(
            url
        ):
            continue

        path = get_path(
            url
        )

        if path not in EXPECTED_PRODUCTS:
            continue

        discovered[path] = {
            "urun_adi": EXPECTED_PRODUCTS[
                path
            ][
                "urun_adi"
            ],

            "kaynak_url": url,
        }

    return discovered


# =========================================================
# ÜRÜN BAŞLANGIÇ BAŞLIKLARI
# =========================================================

def get_start_markers(product_name):

    if product_name == "Bana Bunu Al":
        return [
            "Bana Bunu Al"
        ]

    if product_name == "Bana Bunu Al İş Ortağım":
        return [
            "Bana Bunu Al İş Ortağım"
        ]

    if product_name == "Eğitim Finansmanı Sistemi":
        return [
            "Eğitim Finansmanı Sistemi",
            "Eğitim Finansmanı",
        ]

    return [
        product_name
    ]


# =========================================================
# CROSS-SELL / FOOTER DURDURMA
# =========================================================

def should_stop(line, collected):

    if not collected:
        return False

    normalized = tr_lower(
        one_line(line)
    )

    exact_stop_markers = {
        "yukarı",
        "hakkımızda",
        "hızlı erişim",
        "en çok ziyaret edilenler",
        "size nasıl yardımcı olabiliriz?",
    }

    if normalized in exact_stop_markers:
        return True

    substring_stop_markers = [
        "avantajlı katılma hesabı",
        "birikimlerinizi değerlendirirken",
        "eşit ve yüksek kâr paylaşım oranı",
    ]

    for marker in substring_stop_markers:

        if marker in normalized:
            return True

    return False


# =========================================================
# ÜRÜN METNİ
# =========================================================

def extract_product_text(
    html,
    product_name
):

    soup = prepare_soup(
        html
    )

    content = soup.find(
        "main"
    )

    if content is None:
        content = soup.find(
            attrs={
                "role": "main"
            }
        )

    if content is None:
        content = soup.body

    if content is None:
        content = soup

    raw_text = content.get_text(
        "\n",
        strip=True
    )

    lines = []

    for raw_line in raw_text.splitlines():

        line = one_line(
            raw_line
        )

        if line:
            lines.append(
                line
            )

    if not lines:
        return ""

    start_markers = get_start_markers(
        product_name
    )

    start_index = None

    # Tam eşleşmeye öncelik veriyoruz.
    for index, line in enumerate(
        lines
    ):

        line_normalized = tr_lower(
            line
        )

        for marker in start_markers:

            if (
                line_normalized
                == tr_lower(marker)
            ):
                start_index = index
                break

        if start_index is not None:
            break

    # Tam eşleşme bulunamazsa contains.
    if start_index is None:

        for index, line in enumerate(
            lines
        ):

            line_normalized = tr_lower(
                line
            )

            for marker in start_markers:

                if (
                    tr_lower(marker)
                    in line_normalized
                ):
                    start_index = index
                    break

            if start_index is not None:
                break

    if start_index is None:
        return ""

    collected = []

    for line in lines[
        start_index:
    ]:

        if should_stop(
            line,
            collected
        ):
            break

        collected.append(
            line
        )

    text = clean_text(
        "\n".join(
            collected
        )
    )

    return text


# =========================================================
# DUPLICATE KONTROL
# =========================================================

def find_duplicate_urls(records):

    seen = set()
    duplicates = []

    for record in records:

        key = normalize_url(
            record[
                "kaynak_url"
            ]
        ).lower()

        if key in seen:

            duplicates.append(
                record[
                    "kaynak_url"
                ]
            )

        seen.add(
            key
        )

    return duplicates


def find_duplicate_titles(records):

    seen = set()
    duplicates = []

    for record in records:

        key = tr_lower(
            record[
                "urun_adi"
            ]
        )

        if key in seen:

            duplicates.append(
                record[
                    "urun_adi"
                ]
            )

        seen.add(
            key
        )

    return duplicates


# =========================================================
# İÇERİK KONTROL
# =========================================================

def validate_product_content(record):

    errors = []

    path = get_path(
        record[
            "kaynak_url"
        ]
    )

    expected = EXPECTED_PRODUCTS.get(
        path
    )

    if expected is None:

        errors.append(
            (
                "Beklenmeyen ürün URL'si: "
                f"{record['kaynak_url']}"
            )
        )

        return errors

    text = record[
        "ham_metin"
    ]

    text_lower = tr_lower(
        text
    )

    # -----------------------------------------------------
    # Beklenen ifadeler
    # -----------------------------------------------------

    for keyword in expected[
        "required_keywords"
    ]:

        if (
            tr_lower(keyword)
            not in text_lower
        ):

            errors.append(
                (
                    f"{record['urun_adi']} -> "
                    f"beklenen ifade bulunamadı: "
                    f"{keyword}"
                )
            )

    # -----------------------------------------------------
    # Metin çok kısa mı?
    # -----------------------------------------------------

    if len(text) < 150:

        errors.append(
            (
                f"{record['urun_adi']} -> "
                "ham metin çok kısa."
            )
        )

    # -----------------------------------------------------
    # Başka ürün içeriği karışmış mı?
    # -----------------------------------------------------

    for marker in CONTAMINATION_MARKERS:

        if (
            tr_lower(marker)
            in text_lower
        ):

            errors.append(
                (
                    f"{record['urun_adi']} -> "
                    "başka ürün içeriği karışmış: "
                    f"{marker}"
                )
            )

    return errors


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 110
    )

    print(
        "HAYAT FİNANS - BİREYSEL FİNANSMAN SCRAPER V2"
    )

    print(
        "=" * 110
    )

    print(
        "Liste URL:",
        LIST_URL
    )

    print(
        "Beklenen ürün sayısı:",
        EXPECTED_COUNT
    )

    print()

    session = create_session()

    http_errors = []

    # =====================================================
    # 1. LİSTE SAYFASI
    # =====================================================

    print(
        "[1/3] Krediler liste sayfası indiriliyor..."
    )

    try:

        list_response = get_page(
            session,
            LIST_URL
        )

        print(
            "HTTP:",
            list_response.status_code
        )

    except Exception as error:

        print(
            "Liste sayfası alınamadı:"
        )

        print(
            error
        )

        raise

    # =====================================================
    # 2. DISCOVERY
    # =====================================================

    print()

    print(
        "[2/3] Finansman ürünleri keşfediliyor..."
    )

    discovered = discover_products(
        list_response.text
    )

    print(
        "Bulunan ürün sayısı:",
        len(discovered)
    )

    print()

    for path in EXPECTED_PRODUCTS:

        if path not in discovered:
            continue

        product = discovered[
            path
        ]

        print(
            "✓",
            product[
                "urun_adi"
            ]
        )

        print(
            "  ",
            product[
                "kaynak_url"
            ]
        )

    missing_paths = [
        path
        for path in EXPECTED_PRODUCTS
        if path not in discovered
    ]

    if missing_paths:

        print()

        print(
            "UYARI - Eksik beklenen ürünler:"
        )

        for path in missing_paths:

            print(
                "-",
                EXPECTED_PRODUCTS[
                    path
                ][
                    "urun_adi"
                ]
            )

    # =====================================================
    # 3. DETAYLAR
    # =====================================================

    print()

    print(
        "[3/3] Ürün detay sayfaları indiriliyor..."
    )

    records = []

    for path in EXPECTED_PRODUCTS:

        if path not in discovered:
            continue

        product_name = EXPECTED_PRODUCTS[
            path
        ][
            "urun_adi"
        ]

        url = discovered[
            path
        ][
            "kaynak_url"
        ]

        print()

        print(
            "-" * 110
        )

        print(
            "ÜRÜN:",
            product_name
        )

        print(
            "URL:",
            url
        )

        try:

            response = get_page(
                session,
                url
            )

            print(
                "HTTP:",
                response.status_code
            )

            text = extract_product_text(
                response.text,
                product_name
            )

            if not text:

                raise ValueError(
                    "Ürün içeriği çıkarılamadı."
                )

            record = {
                "banka": BANK_NAME,
                "kayit_turu": "finansman",
                "urun_adi": product_name,
                "kaynak_url": url,
                "ham_metin": text,
            }

            records.append(
                record
            )

            print(
                "Ham metin uzunluğu:",
                len(text)
            )

            print()

            print(
                "ÖNİZLEME:"
            )

            print(
                text[:1200]
            )

        except Exception as error:

            print(
                "HATA:",
                error
            )

            http_errors.append(
                {
                    "urun_adi": product_name,
                    "url": url,
                    "hata": str(error),
                }
            )

    # =====================================================
    # VALIDATION
    # =====================================================

    errors = []

    if len(
        discovered
    ) != EXPECTED_COUNT:

        errors.append(
            (
                "Discovery ürün sayısı hatalı. "
                f"Beklenen={EXPECTED_COUNT}, "
                f"Gerçek={len(discovered)}"
            )
        )

    if len(
        records
    ) != EXPECTED_COUNT:

        errors.append(
            (
                "Scrape edilen ürün sayısı hatalı. "
                f"Beklenen={EXPECTED_COUNT}, "
                f"Gerçek={len(records)}"
            )
        )

    if missing_paths:

        errors.append(
            "Beklenen bazı ürünler bulunamadı."
        )

    duplicate_urls = find_duplicate_urls(
        records
    )

    duplicate_titles = find_duplicate_titles(
        records
    )

    if duplicate_urls:

        errors.append(
            (
                "Duplicate URL: "
                f"{duplicate_urls}"
            )
        )

    if duplicate_titles:

        errors.append(
            (
                "Duplicate başlık: "
                f"{duplicate_titles}"
            )
        )

    for record in records:

        if not record[
            "urun_adi"
        ].strip():

            errors.append(
                "Boş ürün adı bulundu."
            )

        if not record[
            "kaynak_url"
        ].strip():

            errors.append(
                (
                    f"{record['urun_adi']} -> "
                    "URL boş."
                )
            )

        if not is_official_domain(
            record[
                "kaynak_url"
            ]
        ):

            errors.append(
                (
                    f"{record['urun_adi']} -> "
                    "resmi olmayan domain."
                )
            )

        if not record[
            "ham_metin"
        ].strip():

            errors.append(
                (
                    f"{record['urun_adi']} -> "
                    "ham metin boş."
                )
            )

        errors.extend(
            validate_product_content(
                record
            )
        )

    # =====================================================
    # OUTPUT
    # =====================================================

    output = {
        "banka": BANK_NAME,
        "kayit_turu": "finansman",
        "kaynak_liste_url": LIST_URL,
        "beklenen_kayit_sayisi": EXPECTED_COUNT,
        "toplam_kayit": len(records),
        "urunler": records,
        "http_hatalari": http_errors,
        "duplicate_url_sayisi": len(
            duplicate_urls
        ),
        "duplicate_baslik_sayisi": len(
            duplicate_titles
        ),
    }

    os.makedirs(
        os.path.dirname(
            OUTPUT_FILE
        ),
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
    # FINAL
    # =====================================================

    print()

    print(
        "=" * 110
    )

    print(
        "GENEL KONTROL"
    )

    print(
        "=" * 110
    )

    print(
        "Beklenen ürün:",
        EXPECTED_COUNT
    )

    print(
        "Discovery bulunan:",
        len(discovered)
    )

    print(
        "Başarılı scrape:",
        len(records)
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
        "Toplam hata:",
        len(errors)
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
                "FİNANSMAN RAW TEMİZ ✅"
            )
        )

    else:

        print(
            (
                "SONUÇ: HAYAT FİNANS "
                "FİNANSMAN RAW KONTROL GEREKİYOR ❌"
            )
        )

    print()

    print(
        "JSON:",
        OUTPUT_FILE
    )

    print(
        "=" * 110
    )


if __name__ == "__main__":
    main()