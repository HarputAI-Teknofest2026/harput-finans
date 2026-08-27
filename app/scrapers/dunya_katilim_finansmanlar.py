import json
import os
import re
import time
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


# =========================================================
# AYARLAR
# =========================================================

BANK_NAME = "Dünya Katılım Bankası A.Ş."

LIST_URL = "https://dunyakatilim.com.tr/kendim-icin/finansmanlar"

OUTPUT_FILE = "data/raw/dunya_katilim_finansman_urunleri.json"

EXPECTED_COUNT = 6

REQUEST_TIMEOUT = 30

REQUEST_DELAY = 0.8


# =========================================================
# RESMİ DISCOVERY SONUCU
# =========================================================

PRODUCTS = [
    {
        "urun_adi": "İhtiyaç Finansmanı",
        "kategori_kaynak": "İhtiyaç Finansmanları",
        "kaynak_url": (
            "https://dunyakatilim.com.tr/"
            "kendim-icin/finansmanlar/"
            "ihtiyac-finansmani"
        ),
    },
    {
        "urun_adi": "Enerya İhtiyaç Finansmanı",
        "kategori_kaynak": "İhtiyaç Finansmanları",
        "kaynak_url": (
            "https://dunyakatilim.com.tr/"
            "kendim-icin/finansmanlar/"
            "ihtiyac-finansmanlari/"
            "enerya-ihtiyac-finansmani"
        ),
    },
    {
        "urun_adi": "Enerya Karz-ı Hasen",
        "kategori_kaynak": "İhtiyaç Finansmanları",
        "kaynak_url": (
            "https://dunyakatilim.com.tr/"
            "kendim-icin/finansmanlar/"
            "ihtiyac-finansmanlari/"
            "enerya-karz-i-hasen"
        ),
    },
    {
        "urun_adi": "Araç Finansmanı",
        "kategori_kaynak": "Araç Finansmanları",
        "kaynak_url": (
            "https://dunyakatilim.com.tr/"
            "kendim-icin/finansmanlar/"
            "arac-finansmanlari/"
            "arac-finansmani"
        ),
    },
    {
        "urun_adi": "Çevre Dostu Araç Finansmanı",
        "kategori_kaynak": "Araç Finansmanları",
        "kaynak_url": (
            "https://dunyakatilim.com.tr/"
            "kendim-icin/finansmanlar/"
            "arac-finansmanlari/"
            "cevre-dostu-arac-finansmani"
        ),
    },
    {
        "urun_adi": "Konut Finansmanı",
        "kategori_kaynak": "Konut Finansmanları",
        "kaynak_url": (
            "https://dunyakatilim.com.tr/"
            "kendim-icin/finansmanlar/"
            "konut-finansmanlari/"
            "konut-finansmani"
        ),
    },
]


# =========================================================
# COOKIE / KVKK STOP MARKERLARI
# =========================================================

COOKIE_STOP_MARKERS = [
    "Tüm site ziyaretçilerimizi daha iyi tanımak",
    "Çerez Aydınlatma Metni",
    "ÇEREZ KULLANIMINA İLİŞKİN AYDINLATMA METNİ",
    "Çerez Ayarları",
    "Çerez Politikası",
]


# =========================================================
# SESSION
# =========================================================

def create_session():

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,"
                "image/webp,*/*;q=0.8"
            ),
            "Accept-Language": (
                "tr-TR,tr;q=0.9,"
                "en-US;q=0.8,en;q=0.7"
            ),
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    )

    return session


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def clean_line(line):

    line = str(
        line or ""
    )

    line = line.replace(
        "\xa0",
        " "
    )

    line = line.replace(
        "\u200b",
        ""
    )

    line = re.sub(
        r"[ \t]+",
        " ",
        line
    )

    return line.strip()


def normalize_text(text):

    lines = []

    previous = None

    for raw_line in str(
        text or ""
    ).splitlines():

        line = clean_line(
            raw_line
        )

        if not line:
            continue

        # Art arda aynı satır varsa tekilleştir.
        if line == previous:
            continue

        lines.append(
            line
        )

        previous = line

    return "\n".join(
        lines
    ).strip()


def normalize_match(text):

    text = str(
        text or ""
    )

    text = text.replace(
        "İ",
        "i"
    )

    text = text.replace(
        "I",
        "ı"
    )

    text = text.replace(
        "’",
        "'"
    )

    text = text.replace(
        "‘",
        "'"
    )

    text = text.replace(
        "´",
        "'"
    )

    text = text.replace(
        "`",
        "'"
    )

    text = text.casefold()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# HTML CLEANUP
# =========================================================

def remove_unwanted_nodes(container):

    unwanted_selectors = [
        "script",
        "style",
        "noscript",
        "svg",
        "canvas",
        "iframe",
        "header",
        "footer",
        "nav",
        "aside",
    ]

    for selector in unwanted_selectors:

        for node in container.select(
            selector
        ):

            node.decompose()


def find_best_content_container(
    soup,
    expected_title
):

    selectors = [
        "main",
        '[role="main"]',
        ".main-content",
        ".page-content",
        ".content",
    ]

    normalized_title = normalize_match(
        expected_title
    )

    for selector in selectors:

        candidates = soup.select(
            selector
        )

        for candidate in candidates:

            text = normalize_match(
                candidate.get_text(
                    "\n",
                    strip=True
                )
            )

            if (
                normalized_title
                and normalized_title in text
            ):

                return candidate

    # H1/H2 üzerinden uygun ana container ara.
    for heading in soup.find_all(
        [
            "h1",
            "h2",
        ]
    ):

        heading_text = normalize_match(
            heading.get_text(
                " ",
                strip=True
            )
        )

        if (
            normalized_title
            and normalized_title
            in heading_text
        ):

            parent = heading

            for _ in range(
                6
            ):

                if parent.parent is None:
                    break

                parent = parent.parent

                parent_text = normalize_text(
                    parent.get_text(
                        "\n",
                        strip=True
                    )
                )

                if len(
                    parent_text
                ) >= 500:

                    return parent

    return soup.body or soup


# =========================================================
# ÜRÜN BAŞINDAN ÖNCESİNİ KES
# =========================================================

def trim_before_product(
    text,
    product_title
):

    lines = text.splitlines()

    target = normalize_match(
        product_title
    )

    for index, line in enumerate(
        lines
    ):

        current = normalize_match(
            line
        )

        if (
            current == target
            or current.startswith(
                target
            )
        ):

            return "\n".join(
                lines[index:]
            ).strip()

    return text


# =========================================================
# COOKIE / KVKK SONRASINI KES
# =========================================================

def trim_cookie_and_privacy_noise(
    text
):

    lines = text.splitlines()

    result = []

    normalized_markers = [
        normalize_match(
            marker
        )
        for marker in COOKIE_STOP_MARKERS
    ]

    for line in lines:

        normalized_line = normalize_match(
            line
        )

        should_stop = False

        for marker in normalized_markers:

            if (
                marker
                and marker in normalized_line
            ):

                should_stop = True
                break

        if should_stop:
            break

        result.append(
            line
        )

    return "\n".join(
        result
    ).strip()


# =========================================================
# COOKIE KONTROL
# =========================================================

def contains_cookie_noise(
    text
):

    normalized_text = normalize_match(
        text
    )

    for marker in COOKIE_STOP_MARKERS:

        normalized_marker = normalize_match(
            marker
        )

        if (
            normalized_marker
            and normalized_marker
            in normalized_text
        ):

            return True

    return False


# =========================================================
# SAYFA SCRAPE
# =========================================================

def scrape_product(
    session,
    product
):

    url = product[
        "kaynak_url"
    ]

    expected_title = product[
        "urun_adi"
    ]

    response = session.get(
        url,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True
    )

    status_code = (
        response.status_code
    )

    response.raise_for_status()

    response.encoding = (
        response.apparent_encoding
        or response.encoding
        or "utf-8"
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    page_title = ""

    if soup.title:

        page_title = clean_line(
            soup.title.get_text(
                " ",
                strip=True
            )
        )

    container = (
        find_best_content_container(
            soup,
            expected_title
        )
    )

    # Container'ın bağımsız bir kopyasını oluştur.
    clean_soup = BeautifulSoup(
        str(
            container
        ),
        "html.parser"
    )

    remove_unwanted_nodes(
        clean_soup
    )

    raw_text = (
        clean_soup.get_text(
            "\n",
            strip=True
        )
    )

    raw_text = normalize_text(
        raw_text
    )

    # Ürün başlığından önceki site içeriğini at.
    raw_text = trim_before_product(
        raw_text,
        expected_title
    )

    # Cookie/KVKK metni başladığı anda kes.
    raw_text = (
        trim_cookie_and_privacy_noise(
            raw_text
        )
    )

    raw_text = normalize_text(
        raw_text
    )

    title_found = (
        normalize_match(
            expected_title
        )
        in normalize_match(
            raw_text
        )
    )

    cookie_noise_found = (
        contains_cookie_noise(
            raw_text
        )
    )

    return {
        "banka": BANK_NAME,
        "urun_adi": expected_title,
        "kategori_kaynak": product[
            "kategori_kaynak"
        ],
        "kaynak_url": url,
        "final_url": response.url,
        "http_status": status_code,
        "sayfa_basligi": page_title,
        "baslik_dogrulandi": title_found,
        "cookie_noise_var": cookie_noise_found,
        "ham_metin": raw_text,
    }


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

        key = normalize_match(
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
# RAW VALIDATION
# =========================================================

def validate_records(
    records
):

    errors = []

    warnings = []

    if len(
        records
    ) != EXPECTED_COUNT:

        errors.append(
            (
                "Kayıt sayısı yanlış. "
                f"Beklenen={EXPECTED_COUNT}, "
                f"Gerçek={len(records)}"
            )
        )

    expected_titles = {
        normalize_match(
            item[
                "urun_adi"
            ]
        )
        for item in PRODUCTS
    }

    actual_titles = {
        normalize_match(
            item.get(
                "urun_adi",
                ""
            )
        )
        for item in records
    }

    missing_titles = (
        expected_titles
        - actual_titles
    )

    if missing_titles:

        errors.append(
            (
                "Eksik ürün bulundu: "
                f"{sorted(missing_titles)}"
            )
        )

    for record in records:

        title = record.get(
            "urun_adi",
            "?"
        )

        if (
            record.get(
                "http_status"
            )
            != 200
        ):

            errors.append(
                (
                    f"{title} -> "
                    "HTTP 200 değil: "
                    f"{record.get('http_status')}"
                )
            )

        if not record.get(
            "kaynak_url"
        ):

            errors.append(
                (
                    f"{title} -> "
                    "kaynak_url boş."
                )
            )

        if not record.get(
            "ham_metin"
        ):

            errors.append(
                (
                    f"{title} -> "
                    "ham_metin boş."
                )
            )

        if len(
            record.get(
                "ham_metin",
                ""
            )
        ) < 200:

            warnings.append(
                (
                    f"{title} -> "
                    "ham_metin beklenenden kısa."
                )
            )

        if not record.get(
            "baslik_dogrulandi"
        ):

            errors.append(
                (
                    f"{title} -> "
                    "ürün başlığı içerikte "
                    "doğrulanamadı."
                )
            )

        if record.get(
            "cookie_noise_var"
        ):

            errors.append(
                (
                    f"{title} -> "
                    "cookie/KVKK metni "
                    "temizlenemedi."
                )
            )

        source_domain = urlparse(
            record.get(
                "final_url",
                ""
            )
        ).netloc.lower()

        if (
            source_domain
            and "dunyakatilim.com.tr"
            not in source_domain
        ):

            errors.append(
                (
                    f"{title} -> "
                    "resmi domain dışına "
                    "redirect oldu: "
                    f"{record.get('final_url')}"
                )
            )

    duplicate_urls = (
        find_duplicates(
            records,
            "kaynak_url"
        )
    )

    duplicate_titles = (
        find_duplicates(
            records,
            "urun_adi"
        )
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

    return (
        errors,
        warnings,
        duplicate_urls,
        duplicate_titles
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 118
    )

    print(
        "DÜNYA KATILIM - FİNANSMAN SCRAPER V2"
    )

    print(
        "=" * 118
    )

    print(
        "Liste:",
        LIST_URL
    )

    print(
        "Output:",
        OUTPUT_FILE
    )

    print(
        "Beklenen ürün:",
        EXPECTED_COUNT
    )

    print()

    session = create_session()

    records = []

    scrape_errors = []

    for index, product in enumerate(
        PRODUCTS,
        start=1
    ):

        print(
            "-" * 118
        )

        print(
            f"[{index}/{EXPECTED_COUNT}] "
            f"{product['urun_adi']}"
        )

        print(
            product[
                "kaynak_url"
            ]
        )

        try:

            record = scrape_product(
                session,
                product
            )

            records.append(
                record
            )

            print(
                "HTTP:",
                record[
                    "http_status"
                ]
            )

            print(
                "Başlık doğrulandı:",
                (
                    "EVET ✅"
                    if record[
                        "baslik_dogrulandi"
                    ]
                    else "HAYIR ❌"
                )
            )

            print(
                "Cookie/KVKK noise:",
                (
                    "YOK ✅"
                    if not record[
                        "cookie_noise_var"
                    ]
                    else "VAR ❌"
                )
            )

            print(
                "Ham metin karakter:",
                len(
                    record[
                        "ham_metin"
                    ]
                )
            )

            preview = (
                record[
                    "ham_metin"
                ][
                    :220
                ]
                .replace(
                    "\n",
                    " | "
                )
            )

            print(
                "Preview:",
                preview
            )

            ending = (
                record[
                    "ham_metin"
                ][
                    -220:
                ]
                .replace(
                    "\n",
                    " | "
                )
            )

            print(
                "Son kısım:",
                ending
            )

        except Exception as error:

            scrape_errors.append(
                (
                    f"{product['urun_adi']} -> "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

            print(
                "HATA ❌:",
                error
            )

        if (
            index
            < len(PRODUCTS)
        ):

            time.sleep(
                REQUEST_DELAY
            )

    (
        validation_errors,
        warnings,
        duplicate_urls,
        duplicate_titles
    ) = validate_records(
        records
    )

    errors = (
        scrape_errors
        + validation_errors
    )

    # =====================================================
    # OUTPUT
    # =====================================================

    os.makedirs(
        os.path.dirname(
            OUTPUT_FILE
        ),
        exist_ok=True
    )

    output = {
        "banka": BANK_NAME,
        "liste_url": LIST_URL,
        "scrape_zamani": (
            datetime.now().isoformat(
                timespec="seconds"
            )
        ),
        "beklenen_urun_sayisi": (
            EXPECTED_COUNT
        ),
        "toplam_urun_sayisi": (
            len(
                records
            )
        ),
        "http_hata_sayisi": (
            len(
                scrape_errors
            )
        ),
        "duplicate_url_sayisi": (
            len(
                duplicate_urls
            )
        ),
        "duplicate_baslik_sayisi": (
            len(
                duplicate_titles
            )
        ),
        "urunler": records,
    }

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
        "=" * 118
    )

    print(
        "SCRAPER SONUCU"
    )

    print(
        "=" * 118
    )

    print(
        "Beklenen ürün:",
        EXPECTED_COUNT
    )

    print(
        "Çekilen ürün:",
        len(
            records
        )
    )

    print(
        "HTTP/Scrape hata:",
        len(
            scrape_errors
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

    cookie_noise_count = sum(
        1
        for record in records
        if record.get(
            "cookie_noise_var"
        )
    )

    print(
        "Cookie/KVKK noise:",
        cookie_noise_count
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
                "FİNANSMAN RAW V2 TEMİZ ✅"
            )
        )

    else:

        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "FİNANSMAN RAW V2 "
                "KONTROL GEREKİYOR ❌"
            )
        )

    print()

    print(
        "JSON:",
        OUTPUT_FILE
    )

    print(
        "=" * 118
    )


if __name__ == "__main__":
    main()