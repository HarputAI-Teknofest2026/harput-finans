import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# =========================================================
# CONFIG
# =========================================================

ROOT = Path(__file__).resolve().parents[2]

SOURCE_URL = (
    "https://www.adilkatilim.com.tr/"
    "katilim-bankaciligi/urun-ve-hizmetler"
)

OUTPUT_FILE = (
    ROOT
    / "data"
    / "raw"
    / "adil_katilim_finansmanlar.json"
)

BANK_NAME = "Adil Katılım Bankası A.Ş."

EXPECTED_PRODUCT_COUNT = 1

TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 "
        "Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}


# =========================================================
# TEXT HELPERS
# =========================================================

def clean_text(value):
    value = str(value or "")

    value = value.replace(
        "\xa0",
        " ",
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def normalize_text(value):
    value = clean_text(
        value
    )

    value = (
        value
        .replace("İ", "i")
        .replace("I", "ı")
        .casefold()
    )

    return value.strip()


# =========================================================
# PAGE DOWNLOAD
# =========================================================

def fetch_page():
    response = requests.get(
        SOURCE_URL,
        headers=HEADERS,
        timeout=TIMEOUT,
        allow_redirects=True,
    )

    print(
        "HTTP STATUS:",
        response.status_code,
    )

    if response.status_code != 200:
        raise RuntimeError(
            (
                "Ürün ve Hizmetler sayfası "
                f"HTTP {response.status_code} döndürdü."
            )
        )

    return response


# =========================================================
# FIND TITLE ELEMENT
# =========================================================

def find_product_title_element(soup):
    target = normalize_text(
        "Bireysel Finansman"
    )

    # Önce heading etiketlerinde ara.
    for tag_name in (
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    ):
        for element in soup.find_all(
            tag_name
        ):
            text = normalize_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            )

            if text == target:
                return element

    # Site heading yerine div/span/p kullanıyorsa fallback.
    for element in soup.find_all(
        [
            "div",
            "span",
            "p",
            "strong",
        ]
    ):
        text = normalize_text(
            element.get_text(
                " ",
                strip=True,
            )
        )

        if text == target:
            return element

    return None


# =========================================================
# DESCRIPTION EXTRACTION
# =========================================================

def find_description_from_siblings(
    title_element,
):
    """
    Başlığın ardından gelen ilk anlamlı açıklama
    paragrafını bulmaya çalışır.
    """

    for sibling in title_element.find_all_next(
        limit=20
    ):
        if sibling is title_element:
            continue

        name = (
            sibling.name
            or ""
        ).lower()

        text = clean_text(
            sibling.get_text(
                " ",
                strip=True,
            )
        )

        if not text:
            continue

        normalized = normalize_text(
            text
        )

        # Sonraki ürün başlığına geçtiysek dur.
        other_titles = {
            "özel cari hesap",
            "ticari finansman",
            "katılma hesapları",
            "kurumsal",
        }

        if (
            normalized
            in other_titles
        ):
            break

        # Paragraf ise en güçlü aday.
        if (
            name == "p"
            and
            len(text) >= 40
        ):
            return text

    return ""


def find_description_from_parent(
    title_element,
):
    """
    Eğer sibling yaklaşımı çalışmazsa,
    başlığın bulunduğu küçük card/container içinden
    açıklamayı çıkarmaya çalışır.
    """

    current = title_element

    for _ in range(6):
        current = current.parent

        if current is None:
            break

        text = clean_text(
            current.get_text(
                " ",
                strip=True,
            )
        )

        normalized = normalize_text(
            text
        )

        if not text:
            continue

        if (
            "bireysel finansman"
            not in normalized
        ):
            continue

        # Container çok büyüdüyse artık tüm sayfayı
        # almaya başlamış demektir.
        if len(text) > 1500:
            continue

        paragraphs = []

        for paragraph in current.find_all(
            "p"
        ):
            paragraph_text = clean_text(
                paragraph.get_text(
                    " ",
                    strip=True,
                )
            )

            if (
                paragraph_text
                and
                normalize_text(
                    paragraph_text
                )
                != normalize_text(
                    "Bireysel Finansman"
                )
            ):
                paragraphs.append(
                    paragraph_text
                )

        for paragraph_text in paragraphs:
            if len(
                paragraph_text
            ) >= 40:
                return paragraph_text

    return ""


def extract_bireysel_finansman(soup):
    """
    Sayfadaki görünen metinleri DOM sırasıyla alır.
    'Bireysel Finansman' başlığını bulur ve
    bir sonraki bölüm başlığına kadar olan açıklamayı çıkarır.
    """

    texts = []

    for value in soup.stripped_strings:
        text = clean_text(
            value
        )

        if text:
            texts.append(
                text
            )

    target = normalize_text(
        "Bireysel Finansman"
    )

    stop_titles = {
        normalize_text(
            "Özel Cari Hesap"
        ),
        normalize_text(
            "Ticari Finansman"
        ),
        normalize_text(
            "Katılma Hesapları"
        ),
        normalize_text(
            "Kurumsal"
        ),
        normalize_text(
            "Hakkımızda"
        ),
        normalize_text(
            "Katılım Bankacılığı"
        ),
    }

    matching_indexes = []

    for index, text in enumerate(
        texts
    ):
        if normalize_text(
            text
        ) == target:
            matching_indexes.append(
                index
            )

    if not matching_indexes:
        raise RuntimeError(
            (
                "'Bireysel Finansman' metni "
                "sayfada bulunamadı."
            )
        )

    # Birden fazla aynı metin varsa
    # gerçek ürün bölümünü semantik olarak seç.
    for title_index in matching_indexes:

        description_parts = []

        for text in texts[
            title_index + 1:
            title_index + 15
        ]:
            normalized = normalize_text(
                text
            )

            if normalized in stop_titles:
                break

            if normalized == target:
                continue

            description_parts.append(
                text
            )

        description = clean_text(
            " ".join(
                description_parts
            )
        )

        normalized_description = (
            normalize_text(
                description
            )
        )

        # Gerçek Bireysel Finansman açıklamasını
        # diğer menü/başlık tekrarlarından ayır.
        required_markers = (
            "bireysel müşterilerimize",
            "eğitim",
            "sağlık",
            "faizsiz finansman",
        )

        if not all(
            marker
            in normalized_description
            for marker in required_markers
        ):
            continue

        # Ticari ürün metni karıştıysa kabul etme.
        if (
            "işletmelerin mal ve hizmet"
            in normalized_description
        ):
            continue

        title = texts[
            title_index
        ]

        raw_text = clean_text(
            f"{title} {description}"
        )

        return {
            "banka": BANK_NAME,
            "urun_adi": "Bireysel Finansman",
            "urun_grubu": "Bireysel Finansman",
            "baslik": title,
            "aciklama": description,
            "kaynak_url": SOURCE_URL,
            "ham_metin": raw_text,
        }

    raise RuntimeError(
        (
            "'Bireysel Finansman' başlığı bulundu "
            "ama doğru ürün açıklaması "
            "semantik olarak eşleştirilemedi."
        )
    )


# =========================================================
# RAW VALIDATION
# =========================================================

def validate_records(records):
    errors = []

    if not isinstance(
        records,
        list,
    ):
        return [
            "Root JSON list değil."
        ]

    if (
        len(records)
        != EXPECTED_PRODUCT_COUNT
    ):
        errors.append(
            (
                "Ürün sayısı yanlış: "
                f"beklenen={EXPECTED_PRODUCT_COUNT}, "
                f"actual={len(records)}"
            )
        )

    required_fields = [
        "banka",
        "urun_adi",
        "urun_grubu",
        "baslik",
        "aciklama",
        "kaynak_url",
        "ham_metin",
    ]

    for index, record in enumerate(
        records,
        start=1,
    ):
        if not isinstance(
            record,
            dict,
        ):
            errors.append(
                f"[{index}] Kayıt dict değil."
            )

            continue

        for field in required_fields:
            value = record.get(
                field
            )

            if (
                not isinstance(
                    value,
                    str,
                )
                or
                not value.strip()
            ):
                errors.append(
                    (
                        f"[{index}] "
                        f"{field} boş."
                    )
                )

        if (
            record.get(
                "banka"
            )
            != BANK_NAME
        ):
            errors.append(
                (
                    f"[{index}] "
                    "banka alanı yanlış."
                )
            )

        if (
            record.get(
                "urun_adi"
            )
            != "Bireysel Finansman"
        ):
            errors.append(
                (
                    f"[{index}] "
                    "beklenmeyen ürün adı: "
                    f"{record.get('urun_adi')}"
                )
            )

        normalized_raw = normalize_text(
            record.get(
                "ham_metin",
                ""
            )
        )

        if (
            "ticari finansman"
            in normalized_raw
        ):
            errors.append(
                (
                    f"[{index}] "
                    "RAW içerisinde Ticari Finansman "
                    "metni bulundu."
                )
            )

    return errors


# =========================================================
# MAIN
# =========================================================

def main():
    print()

    print(
        "=" * 120
    )

    print(
        "ADİL KATILIM - FINANCE SCRAPER V1"
    )

    print(
        "=" * 120
    )

    print(
        "Kaynak:",
        SOURCE_URL,
    )

    print(
        "Output:",
        OUTPUT_FILE,
    )

    print()

    # =====================================================
    # DOWNLOAD
    # =====================================================

    response = fetch_page()

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    # Script/style temizliği.
    for element in soup(
        [
            "script",
            "style",
            "noscript",
        ]
    ):
        element.decompose()

    # =====================================================
    # EXTRACTION
    # =====================================================

    product = extract_bireysel_finansman(
        soup
    )

    records = [
        product
    ]

    print()

    print(
        "Ürün:",
        product[
            "urun_adi"
        ],
    )

    print()

    print(
        "Açıklama:"
    )

    print(
        product[
            "aciklama"
        ]
    )

    # =====================================================
    # VALIDATION
    # =====================================================

    errors = validate_records(
        records
    )

    print()

    print(
        "=" * 120
    )

    print(
        "RAW VALIDATION"
    )

    print(
        "=" * 120
    )

    print(
        "Beklenen ürün:",
        EXPECTED_PRODUCT_COUNT,
    )

    print(
        "Çekilen ürün:",
        len(
            records
        ),
    )

    print(
        "Validation error:",
        len(
            errors
        ),
    )

    if errors:
        print()

        for error in errors:
            print(
                "❌",
                error,
            )

        print()

        print(
            "SONUÇ: SCRAPER BAŞARISIZ ❌"
        )

        sys.exit(
            1
        )

    # =====================================================
    # SAVE
    # =====================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=4,
        )

    print()

    print(
        "SONUÇ: ADİL KATILIM "
        "FINANCE SCRAPER BAŞARILI ✅"
    )

    print(
        "Bireysel Finansman çekildi ✅"
    )

    print(
        "Ticari Finansman kapsam dışı bırakıldı ✅"
    )

    print()

    print(
        "JSON:",
        OUTPUT_FILE,
    )

    print(
        "=" * 120
    )


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print(
            "\nKullanıcı tarafından durduruldu."
        )

        sys.exit(
            130
        )

    except Exception as error:
        print()

        print(
            "SCRAPER ERROR ❌"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        sys.exit(
            1
        )