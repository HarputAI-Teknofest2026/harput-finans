import json
import os
import re
from datetime import date, datetime
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


# =========================================================
# AYARLAR
# =========================================================

BANK_NAME = "Hayat Finans Katılım Bankası"

BASE_URL = "https://hayatfinans.com.tr"

LIST_URL = "https://hayatfinans.com.tr/kampanyalar"

OUTPUT_FILE = "data/raw/hayat_finans_kampanyalar.json"

TIMEOUT = 30

EXPECTED_COUNT = 11


EXPECTED_CAMPAIGNS = {
    "/kampanyalar/arkadasini-getir-avantajli-hesap-ac-nakit-odul-kazan": {
        "urun_adi": (
            "Arkadaşını Davet Et, Avantajlı Hesapla "
            "Kazanmaya Başla!"
        ),
        "kampanya_kategorisi": "Arkadaşını Getir",
        "required_terms": [
            "17 Ağustos",
            "17 Eylül 2026",
            "2.000 TL",
            "10.000 TL",
        ],
    },

    "/kampanyalar/avantajli-hesap-musterilerine-ozel-fx-dar-makas-avantaji": {
        "urun_adi": (
            "Avantajlı Hesap Müşterilerine Özel "
            "FX Dar Makas Avantajı!"
        ),
        "kampanya_kategorisi": "Yatırım",
        "required_terms": [
            "17 Temmuz",
            "17 Eylül 2026",
            "5.000 USD",
            "%0,1",
        ],
    },

    "/kampanyalar/biz-kart-ile-arkadasini-getir-kazan": {
        "urun_adi": "Biz Kart Arkadaşını Getir & Kazan",
        "kampanya_kategorisi": "Biz Kart",
        "required_terms": [
            "16 Haziran",
            "31 Ağustos 2026",
            "500 TL",
            "25.000 TL",
        ],
    },

    "/kampanyalar/biz-kart-dijital-uyelikler-kampanyasi": {
        "urun_adi": (
            "Biz Kart ile Dijital Üyeliklerde "
            "%75 Nakit İade Fırsatı!"
        ),
        "kampanya_kategorisi": "Biz Kart",
        "required_terms": [
            "16 Haziran",
            "31 Ağustos 2026",
            "%75",
            "300 TL",
        ],
    },

    "/kampanyalar/hayatfinansla-islem-yaptikca-kazan": {
        "urun_adi": "Hayat Finans'la İşlem Yaptıkça Kazan!",
        "kampanya_kategorisi": "Genel",
        "required_terms": [
            "2 Temmuz",
            "31 Aralık 2026",
            "nakit ödül",
            "Hayat Pay",
        ],
    },

    "/hesaplar/avantajli-hesap": {
        "urun_adi": "Birikimin Büyüsün, Avantajın Bitmesin!",
        "kampanya_kategorisi": "Katılma Hesabı",
        "required_terms": [
            "%99",
            "%95",
            "%90",
            "08.10.2026",
        ],
    },

    "/kampanyalar/hayatfx-ile-gumus-islemleri": {
        "urun_adi": "Gümüş İşlemleri Hayat FX'te!",
        "kampanya_kategorisi": "Yatırım",
        "required_terms": [
            "1 Haziran 2026",
            "31 Ağustos 2026",
            "gümüş",
            "dar makas",
        ],
    },

    "/kampanyalar/biz-kart-yemek-harcamasi-nakit-iade-kampanyasi": {
        "urun_adi": (
            "Biz Kart ile Yemek Harcamalarına "
            "1.000 TL’ye Varan Nakit İade!"
        ),
        "kampanya_kategorisi": "Biz Kart",
        "required_terms": [
            "6 Şubat",
            "31 Ağustos 2026",
            "%10",
            "1.000 TL",
        ],
    },

    "/kampanyalar/bana-bunu-al-is-ortagim-ile-troy-magaza-firsatlari": {
        "urun_adi": (
            "Bana Bunu Al İş Ortağım ile "
            "Troy Mağazalarında Finansman Fırsatı!"
        ),
        "kampanya_kategorisi": "Teknoloji",
        "required_terms": [
            "31 Ağustos 2026",
            "3 aya",
            "80.000TL",
        ],
    },

    "/kampanyalar/xiaomi-urunlerinde-finansman-avantaji": {
        "urun_adi": "Xiaomi Ürünlerinde Finansman Avantajı",
        "kampanya_kategorisi": "Teknoloji",
        "required_terms": [
            "31 Ağustos 2026",
            "3 aya",
            "40.000TL",
        ],
    },

    "/kampanyalar/hayat-finans-ile-gastroclub-ayricaliklari": {
        "urun_adi": "Harcadıkça Kazan, Cebin Hep Dolu Kalsın!",
        "kampanya_kategorisi": "Genel",
        "required_terms": [
            "GastroClub",
            "%10",
            "%50",
            "bireysel Hayat Finans müşterileri",
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
    "Accept-Language": (
        "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    ),
    "Connection": "keep-alive",
}


# =========================================================
# TÜRKÇE AY
# =========================================================

MONTHS = {
    "ocak": 1,
    "şubat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "eylül": 9,
    "ekim": 10,
    "kasım": 11,
    "aralık": 12,
}


# =========================================================
# NORMALİZASYON
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
    """
    Türkçe case normalizasyonu + tipografik
    apostrof/tırnak normalizasyonu.

    Hayat Finans'la
    Hayat Finans’la
    Hayat Finans‘la

    aynı kabul edilir.
    """

    value = str(value or "")

    value = value.replace("İ", "i")
    value = value.replace("I", "ı")

    # V2 - tipografik apostrofları standartlaştır
    value = value.replace("’", "'")
    value = value.replace("‘", "'")
    value = value.replace("´", "'")
    value = value.replace("`", "'")

    # Tipografik çift tırnakları da standartlaştır
    value = value.replace("“", '"')
    value = value.replace("”", '"')

    return value.casefold()


# =========================================================
# URL
# =========================================================

def normalize_url(url):
    absolute = urljoin(
        BASE_URL,
        str(url or "")
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
    return urlparse(
        normalize_url(url)
    ).path.rstrip("/")


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
# TABLO KORUMA
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

def prepare_soup(page_html):
    soup = BeautifulSoup(
        page_html,
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
# KAMPANYA DISCOVERY
# =========================================================

def discover_campaigns(page_html):
    soup = BeautifulSoup(
        page_html,
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

        if path not in EXPECTED_CAMPAIGNS:
            continue

        discovered[path] = {
            "kaynak_url": url,
            "link_metni": one_line(
                anchor.get_text(
                    " ",
                    strip=True
                )
            ),
        }

    return discovered


# =========================================================
# SAYFA METNİ
# =========================================================

def get_start_markers(title):
    markers = [
        title
    ]

    if title == (
        "Arkadaşını Davet Et, Avantajlı Hesapla "
        "Kazanmaya Başla!"
    ):
        markers.append(
            "Arkadaşını Davet Et"
        )

    elif title == (
        "Hayat Finans'la İşlem Yaptıkça Kazan!"
    ):
        # Gerçek sayfa başlığı tipografik apostrof kullanıyor.
        markers.extend(
            [
                "Hayat Finans’la İşlem Yaptıkça Kazan!",
                "İşlem Yaptıkça Kazan",
                "Masraf yok, kazanç var: Hayat’la Kazan",
            ]
        )

    elif title == (
        "Birikimin Büyüsün, Avantajın Bitmesin!"
    ):
        markers.append(
            "Hayat Finans Avantajlı Hesap"
        )

    elif title == (
        "Harcadıkça Kazan, Cebin Hep Dolu Kalsın!"
    ):
        markers.append(
            "Harcadıkça Kazan"
        )

    return markers


def should_stop_line(line):
    normalized = tr_lower(
        one_line(line)
    )

    exact_stops = {
        "yukarı",
        "size nasıl yardımcı olabiliriz?",
        "hakkımızda",
        "hızlı erişim",
        "en çok ziyaret edilenler",
    }

    if normalized in exact_stops:
        return True

    if normalized.startswith(
        "hemen avantajlı olmak için tıklayın!"
    ):
        return True

    return False


def extract_campaign_text(
    page_html,
    campaign_title
):
    soup = prepare_soup(
        page_html
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

    lines = [
        one_line(line)
        for line in raw_text.splitlines()
        if one_line(line)
    ]

    if not lines:
        return ""

    markers = get_start_markers(
        campaign_title
    )

    start_index = None

    # =====================================================
    # TAM EŞLEŞME
    # =====================================================

    for index, line in enumerate(lines):

        normalized_line = tr_lower(
            line
        )

        for marker in markers:

            if (
                normalized_line
                == tr_lower(marker)
            ):
                start_index = index
                break

        if start_index is not None:
            break

    # =====================================================
    # CONTAINS
    # =====================================================

    if start_index is None:

        for index, line in enumerate(lines):

            normalized_line = tr_lower(
                line
            )

            for marker in markers:

                if (
                    tr_lower(marker)
                    in normalized_line
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

        if (
            collected
            and should_stop_line(line)
        ):
            break

        collected.append(
            line
        )

    return clean_text(
        "\n".join(
            collected
        )
    )


# =========================================================
# TARİH
# =========================================================

def parse_turkish_month_date(
    day_value,
    month_value,
    year_value
):
    month_number = MONTHS.get(
        tr_lower(
            month_value
        )
    )

    if not month_number:
        return None

    try:

        return date(
            int(year_value),
            month_number,
            int(day_value)
        )

    except ValueError:
        return None


def extract_campaign_dates(text):

    normalized = one_line(
        text
    )

    # =====================================================
    # FORMAT 1
    # 1 Haziran 2026 – 31 Ağustos 2026
    # =====================================================

    match = re.search(
        (
            r"(\d{1,2})\s+"
            r"(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
            r"Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)"
            r"\s+(\d{4})"
            r"\s*[-–—]\s*"
            r"(\d{1,2})\s+"
            r"(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
            r"Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)"
            r"\s+(\d{4})"
        ),
        normalized,
        flags=re.IGNORECASE
    )

    if match:

        start = parse_turkish_month_date(
            match.group(1),
            match.group(2),
            match.group(3)
        )

        end = parse_turkish_month_date(
            match.group(4),
            match.group(5),
            match.group(6)
        )

        return (
            start.isoformat() if start else "",
            end.isoformat() if end else "",
            match.group(0)
        )

    # =====================================================
    # FORMAT 2
    # 17 Ağustos - 17 Eylül 2026
    # =====================================================

    match = re.search(
        (
            r"(\d{1,2})\s+"
            r"(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
            r"Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)"
            r"\s*[-–—]\s*"
            r"(\d{1,2})\s+"
            r"(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
            r"Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)"
            r"\s+(\d{4})"
        ),
        normalized,
        flags=re.IGNORECASE
    )

    if match:

        year = match.group(5)

        start = parse_turkish_month_date(
            match.group(1),
            match.group(2),
            year
        )

        end = parse_turkish_month_date(
            match.group(3),
            match.group(4),
            year
        )

        return (
            start.isoformat() if start else "",
            end.isoformat() if end else "",
            match.group(0)
        )

    # =====================================================
    # FORMAT 3
    # Kampanya 31 Ağustos 2026 tarihine kadar geçerlidir
    # =====================================================

    match = re.search(
        (
            r"Kampanya\s+"
            r"(\d{1,2})\s+"
            r"(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
            r"Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)"
            r"\s+(\d{4})"
            r"\s+tarihine\s+kadar\s+geçerlidir"
        ),
        normalized,
        flags=re.IGNORECASE
    )

    if match:

        end = parse_turkish_month_date(
            match.group(1),
            match.group(2),
            match.group(3)
        )

        return (
            "",
            end.isoformat() if end else "",
            match.group(0)
        )

    # =====================================================
    # FORMAT 4
    # kampanya bitiş tarihi 08.10.2026
    # =====================================================

    match = re.search(
        (
            r"kampanya\s+bitiş\s+tarihi"
            r".{0,20}?"
            r"(\d{1,2})[./](\d{1,2})[./](\d{4})"
        ),
        normalized,
        flags=re.IGNORECASE
    )

    if match:

        try:

            end = date(
                int(match.group(3)),
                int(match.group(2)),
                int(match.group(1))
            )

        except ValueError:
            end = None

        return (
            "",
            end.isoformat() if end else "",
            match.group(0)
        )

    return (
        "",
        "",
        ""
    )


# =========================================================
# AKTİFLİK
# =========================================================

def determine_status(
    start_iso,
    end_iso,
    found_on_active_list
):
    today = date.today()

    start = None
    end = None

    if start_iso:

        try:
            start = datetime.strptime(
                start_iso,
                "%Y-%m-%d"
            ).date()

        except ValueError:
            pass

    if end_iso:

        try:
            end = datetime.strptime(
                end_iso,
                "%Y-%m-%d"
            ).date()

        except ValueError:
            pass

    if start and end:

        if start <= today <= end:
            return "aktif_dogrulanmis"

        if today < start:
            return "gelecek"

        return "suresi_dolmus"

    if end:

        if today <= end:
            return "aktif_dogrulanmis"

        return "suresi_dolmus"

    if found_on_active_list:
        return "aktif_listede"

    return "manuel_kontrol"


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

        if field == "kaynak_url":

            key = normalize_url(
                value
            ).lower()

        else:

            key = tr_lower(
                value
            ).strip()

        if key in seen:

            duplicates.append(
                value
            )

        seen.add(
            key
        )

    return duplicates


# =========================================================
# RECORD VALIDATION
# =========================================================

def validate_record(record):

    errors = []

    title = record[
        "urun_adi"
    ]

    path = get_path(
        record[
            "kaynak_url"
        ]
    )

    expected = EXPECTED_CAMPAIGNS.get(
        path
    )

    if expected is None:

        errors.append(
            (
                "Beklenmeyen kampanya URL'si: "
                f"{record['kaynak_url']}"
            )
        )

        return errors

    text = record[
        "ham_metin"
    ]

    lower = tr_lower(
        text
    )

    if len(text) < 100:

        errors.append(
            "Ham metin çok kısa."
        )

    for term in expected[
        "required_terms"
    ]:

        if (
            tr_lower(term)
            not in lower
        ):

            errors.append(
                (
                    "Beklenen ifade bulunamadı: "
                    f"{term}"
                )
            )

    if (
        "avantajlı katılma hesabı ile "
        "birikimlerinizi değerlendirirken"
        in lower
        and path
        != "/hesaplar/avantajli-hesap"
    ):

        errors.append(
            (
                "Avantajlı Hesap cross-sell metni "
                "kampanya ham metnine karışmış."
            )
        )

    return errors


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 115
    )

    print(
        "HAYAT FİNANS - KAMPANYA SCRAPER V2"
    )

    print(
        "=" * 115
    )

    print(
        "Liste URL:",
        LIST_URL
    )

    print(
        "Beklenen aktif/güncel kayıt:",
        EXPECTED_COUNT
    )

    print(
        "Çalıştırma tarihi:",
        date.today().isoformat()
    )

    session = create_session()

    http_errors = []

    # =====================================================
    # LISTE
    # =====================================================

    print()

    print(
        "[1/3] Kampanya liste sayfası indiriliyor..."
    )

    list_response = get_page(
        session,
        LIST_URL
    )

    print(
        "HTTP:",
        list_response.status_code
    )

    # =====================================================
    # DISCOVERY
    # =====================================================

    print()

    print(
        "[2/3] Kampanyalar keşfediliyor..."
    )

    discovered = discover_campaigns(
        list_response.text
    )

    print(
        "Bulunan beklenen kayıt:",
        len(discovered)
    )

    missing_paths = []

    for path, config in (
        EXPECTED_CAMPAIGNS.items()
    ):

        if path in discovered:

            print(
                "✓",
                config[
                    "urun_adi"
                ]
            )

        else:

            missing_paths.append(
                path
            )

            print(
                "✗",
                config[
                    "urun_adi"
                ]
            )

    # =====================================================
    # DETAYLAR
    # =====================================================

    print()

    print(
        "[3/3] Kampanya detay sayfaları indiriliyor..."
    )

    records = []

    errors = []

    for index, (
        path,
        config
    ) in enumerate(
        EXPECTED_CAMPAIGNS.items(),
        start=1
    ):

        if path not in discovered:
            continue

        title = config[
            "urun_adi"
        ]

        category = config[
            "kampanya_kategorisi"
        ]

        url = discovered[
            path
        ][
            "kaynak_url"
        ]

        print()

        print(
            "-" * 115
        )

        print(
            f"[{index}/{EXPECTED_COUNT}]"
        )

        print(
            "KAMPANYA:",
            title
        )

        print(
            "Kategori:",
            category
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

            text = extract_campaign_text(
                response.text,
                title
            )

            if not text:

                raise ValueError(
                    "Kampanya içeriği çıkarılamadı."
                )

            (
                start_date,
                end_date,
                date_source
            ) = extract_campaign_dates(
                text
            )

            status = determine_status(
                start_date,
                end_date,
                True
            )

            record = {
                "banka": BANK_NAME,
                "kayit_turu": "kampanya",
                "urun_adi": title,
                "kampanya_kategorisi": category,
                "aktiflik_durumu": status,
                "kampanya_baslangic_tarihi": start_date,
                "kampanya_bitis_tarihi": end_date,
                "tarih_kaynak_ifadesi": date_source,
                "kaynak_url": url,
                "ham_metin": text,
            }

            records.append(
                record
            )

            record_errors = validate_record(
                record
            )

            for error in record_errors:

                errors.append(
                    f"{title} -> {error}"
                )

            print(
                "Metin uzunluğu:",
                len(text)
            )

            print(
                "Başlangıç:",
                start_date or "-"
            )

            print(
                "Bitiş:",
                end_date or "-"
            )

            print(
                "Durum:",
                status
            )

            print()

            print(
                "ÖNİZLEME:"
            )

            print(
                text[:900]
            )

        except Exception as error:

            print(
                "HATA:",
                error
            )

            http_errors.append(
                {
                    "urun_adi": title,
                    "kaynak_url": url,
                    "hata": str(error),
                }
            )

    # =====================================================
    # GENEL VALIDATION
    # =====================================================

    if len(
        discovered
    ) != EXPECTED_COUNT:

        errors.append(
            (
                "Discovery sayısı yanlış. "
                f"Beklenen={EXPECTED_COUNT}, "
                f"Bulunan={len(discovered)}"
            )
        )

    if missing_paths:

        errors.append(
            (
                "Beklenen bazı kampanyalar "
                "liste sayfasında bulunamadı."
            )
        )

    if len(
        records
    ) != EXPECTED_COUNT:

        errors.append(
            (
                "Scrape edilen kayıt sayısı yanlış. "
                f"Beklenen={EXPECTED_COUNT}, "
                f"Gerçek={len(records)}"
            )
        )

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

    for record in records:

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
                    "ham_metin boş."
                )
            )

    # =====================================================
    # DURUM
    # =====================================================

    status_counts = {}

    for record in records:

        status = record[
            "aktiflik_durumu"
        ]

        status_counts[
            status
        ] = (
            status_counts.get(
                status,
                0
            )
            + 1
        )

    # =====================================================
    # OUTPUT
    # =====================================================

    output = {
        "banka": BANK_NAME,
        "kayit_turu": "kampanya",
        "kaynak_liste_url": LIST_URL,
        "scrape_tarihi": date.today().isoformat(),
        "beklenen_kayit_sayisi": EXPECTED_COUNT,
        "toplam_kayit": len(records),
        "durum_sayilari": status_counts,
        "kampanyalar": records,
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
        "=" * 115
    )

    print(
        "GENEL KONTROL"
    )

    print(
        "=" * 115
    )

    print(
        "Beklenen kampanya:",
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

    print()

    print(
        "DURUM DAĞILIMI:"
    )

    for status, count in sorted(
        status_counts.items()
    ):

        print(
            f"- {status}: {count}"
        )

    print()

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
                "KAMPANYA RAW V2 TEMİZ ✅"
            )
        )

    else:

        print(
            (
                "SONUÇ: HAYAT FİNANS "
                "KAMPANYA RAW V2 "
                "KONTROL GEREKİYOR ❌"
            )
        )

    print()

    print(
        "JSON:",
        OUTPUT_FILE
    )

    print(
        "=" * 115
    )


if __name__ == "__main__":
    main()