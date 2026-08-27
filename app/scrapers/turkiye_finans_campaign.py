import json
import os
import re
import time
from collections import deque
from datetime import date
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


# =========================================================
# AYARLAR
# =========================================================

BASE_URL = "https://www.turkiyefinans.com.tr"

CAMPAIGN_HOME = (
    "https://www.turkiyefinans.com.tr/"
    "tr-tr/kampanyalar/Sayfalar/default.aspx"
)

ENDED_CAMPAIGNS_URL = (
    "https://www.turkiyefinans.com.tr/"
    "tr-tr/kampanyalar/Sayfalar/Biten-Kampanyalar.aspx"
)

OUTPUT_FILE = (
    "data/raw/"
    "turkiye_finans_kampanyalar.json"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 "
        "Safari/537.36"
    ),
    "Accept-Language": (
        "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    )
}


REQUEST_TIMEOUT = 30
REQUEST_DELAY = 0.15
MAX_GRAPH_PAGES = 300


# =========================================================
# BİREYSEL KAMPANYA KATEGORİLERİ
# =========================================================

CATEGORY_URLS = {
    "Dijital Bankacılık Kampanyaları": (
        "https://www.turkiyefinans.com.tr/"
        "tr-tr/kampanyalar/Sayfalar/"
        "dijital-bankacilik-kampanyalari.aspx"
    ),

    "Kredi Kartı Kampanyaları": (
        "https://www.turkiyefinans.com.tr/"
        "tr-tr/kampanyalar/Sayfalar/"
        "kart-kampanyalari.aspx"
    ),

    "Maaş Ödemesi Kampanyaları": (
        "https://www.turkiyefinans.com.tr/"
        "tr-tr/kampanyalar/Sayfalar/"
        "odeme-kampanyalari.aspx"
    ),

    "Yatırım Kampanyaları": (
        "https://www.turkiyefinans.com.tr/"
        "tr-tr/kampanyalar/Sayfalar/"
        "yatirim-kampanyalari.aspx"
    ),

    "Birikim/Fon Kampanyaları": (
        "https://www.turkiyefinans.com.tr/"
        "tr-tr/kampanyalar/Sayfalar/"
        "birikim-fon-kampanyalari.aspx"
    ),

    "Sigorta Kampanyaları": (
        "https://www.turkiyefinans.com.tr/"
        "tr-tr/kampanyalar/Sayfalar/"
        "sigorta-kampanyalari.aspx"
    ),

    "Finansman Kampanyaları": (
        "https://www.turkiyefinans.com.tr/"
        "tr-tr/kampanyalar/Sayfalar/"
        "finansman-kampanyalari.aspx"
    ),

    "Diğer Kampanyalar": (
        "https://www.turkiyefinans.com.tr/"
        "tr-tr/kampanyalar/Sayfalar/"
        "diger-kampanyalar.aspx"
    )
}


# =========================================================
# KATEGORİDE GÖRÜNMEYEN AMA RESMÎ OLARAK
# DOĞRULANAN BİREYSEL KAMPANYA SAYFALARI
# =========================================================

EXTRA_CAMPAIGNS = {
    (
        "https://www.turkiyefinans.com.tr/"
        "tr-tr/kampanyalar/Sayfalar/"
        "maas-musterilerine-ozel-avantajlar.aspx"
    ): {
        "kategori": "Maaş Ödemesi Kampanyaları",
        "tarih_yoksa_aktif": True
    },

    (
        "https://www.turkiyefinans.com.tr/"
        "tr-tr/kampanyalar/Sayfalar/"
        "bereket-sigorta-kampanyasi.aspx"
    ): {
        "kategori": "Diğer Kampanyalar",
        "tarih_yoksa_aktif": True
    },

    (
        "https://www.turkiyefinans.com.tr/"
        "tr-tr/kampanyalar/Sayfalar/"
        "avantajli-bankacilik.aspx"
    ): {
        "kategori": "Diğer Kampanyalar",
        "tarih_yoksa_aktif": True
    }
}


# =========================================================
# LISTING SAYFALARI
# =========================================================

LISTING_PATHS = {
    "/tr-tr/kampanyalar/sayfalar/default.aspx",

    "/tr-tr/kampanyalar/sayfalar/"
    "dijital-bankacilik-kampanyalari.aspx",

    "/tr-tr/kampanyalar/sayfalar/"
    "kart-kampanyalari.aspx",

    "/tr-tr/kampanyalar/sayfalar/"
    "kredi-karti-kampanyalari.aspx",

    "/tr-tr/kampanyalar/sayfalar/"
    "odeme-kampanyalari.aspx",

    "/tr-tr/kampanyalar/sayfalar/"
    "maas-odemesi-kampanyalari.aspx",

    "/tr-tr/kampanyalar/sayfalar/"
    "yatirim-kampanyalari.aspx",

    "/tr-tr/kampanyalar/sayfalar/"
    "birikim-fon-kampanyalari.aspx",

    "/tr-tr/kampanyalar/sayfalar/"
    "sigorta-kampanyalari.aspx",

    "/tr-tr/kampanyalar/sayfalar/"
    "finansman-kampanyalari.aspx",

    "/tr-tr/kampanyalar/sayfalar/"
    "diger-kampanyalar.aspx",

    "/tr-tr/kampanyalar/sayfalar/"
    "ticari-kampanyalar.aspx",

    "/tr-tr/kampanyalar/sayfalar/"
    "biten-kampanyalar.aspx"
}


LISTING_TITLES = {
    "kampanyalar",
    "dijital bankacılık kampanyaları",
    "kredi kartı kampanyaları",
    "maaş ödemesi kampanyaları",
    "yatırım kampanyaları",
    "birikim/fon kampanyaları",
    "birikim / fon kampanyaları",
    "sigorta kampanyaları",
    "finansman kampanyaları",
    "diğer kampanyalar",
    "ticari kampanyalar",
    "biten kampanyalar"
}


# =========================================================
# TÜRKÇE AYLAR
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
    "aralık": 12
}


# =========================================================
# NORMALİZASYON
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


def remove_invisible(value):

    value = str(
        value or ""
    )

    for char in [
        "\u200b",
        "\u200c",
        "\u200d",
        "\u2060",
        "\ufeff",
        "\u00ad"
    ]:

        value = value.replace(
            char,
            ""
        )

    return value


def normalize_text(value):

    return re.sub(
        r"\s+",
        " ",
        remove_invisible(
            value
        )
    ).strip()


def unique_strings(items):

    result = []

    seen = set()

    for item in items:

        item = normalize_text(
            item
        )

        if not item:

            continue

        key = tr_lower(
            item
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        result.append(
            item
        )

    return result


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
        "#",
        1
    )[0]

    url = url.split(
        "?",
        1
    )[0]

    return url.rstrip(
        "/"
    )


def canonical_url(url):

    return normalize_url(
        BASE_URL,
        url
    ).casefold()


def get_path(url):

    try:

        return (
            urlparse(
                url
            )
            .path
            .casefold()
            .rstrip("/")
        )

    except Exception:

        return ""


# =========================================================
# URL KONTROLLERİ
# =========================================================

def valid_domain(url):

    try:

        host = (
            urlparse(
                url
            )
            .netloc
            .casefold()
        )

    except Exception:

        return False

    return host in {
        "turkiyefinans.com.tr",
        "www.turkiyefinans.com.tr"
    }


def is_campaign_namespace_url(url):

    if not valid_domain(
        url
    ):

        return False

    return (
        "/tr-tr/kampanyalar/"
        in get_path(
            url
        )
    )


def is_listing_url(url):

    return (
        get_path(
            url
        )
        in LISTING_PATHS
    )


def is_ended_listing(url):

    return (
        get_path(
            url
        )
        == (
            "/tr-tr/kampanyalar/"
            "sayfalar/"
            "biten-kampanyalar.aspx"
        )
    )


def is_detail_candidate_url(url):

    if not is_campaign_namespace_url(
        url
    ):

        return False

    path = get_path(
        url
    )

    if not path.endswith(
        ".aspx"
    ):

        return False

    if is_listing_url(
        url
    ):

        return False

    return True


# =========================================================
# HTTP
# =========================================================

def get_response(
    session,
    url
):

    return session.get(
        url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True
    )


# =========================================================
# TITLE
# =========================================================

def clean_title(value):

    value = normalize_text(
        value
    )

    suffixes = [
        "| Kampanyalar | Türkiye Finans",
        "- Kampanyalar | Türkiye Finans",
        "| Türkiye Finans Katılım Bankası",
        "- Türkiye Finans Katılım Bankası",
        "| Türkiye Finans",
        "- Türkiye Finans"
    ]

    for suffix in suffixes:

        if value.endswith(
            suffix
        ):

            value = value[
                :-len(
                    suffix
                )
            ].strip()

    return value


def get_page_title(soup):

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
# İÇERİK
# =========================================================

def container_strings(container):

    result = []

    for value in container.stripped_strings:

        value = normalize_text(
            value
        )

        if not value:

            continue

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
            in tr_lower(
                value
            )

            and len(
                value
            ) < 180
        ):

            continue

        result.append(
            value
        )

    return result


def slice_real_content(
    strings,
    page_title
):

    if not strings:

        return []

    content_indexes = [
        index

        for index, value
        in enumerate(
            strings
        )

        if (
            tr_lower(
                value
            )
            == "sayfa içeriği"
        )
    ]

    if content_indexes:

        strings = strings[
            content_indexes[-1] + 1:
        ]

    else:

        title_indexes = [
            index

            for index, value
            in enumerate(
                strings
            )

            if (
                tr_lower(
                    value
                )
                == tr_lower(
                    page_title
                )
            )
        ]

        if title_indexes:

            strings = strings[
                title_indexes[-1]:
            ]

    stop_values = {
        "Müşteri Memnuniyet Merkezi",
        "Yatırımcı İlişkileri",
        "Finans Portalı",
        "Satılık Gayrimenkuller",
        "Türkiye Finans Linkleri",
        "Türkiye Finans Blog",
        "Site Haritası",
        "İnsan Kaynakları"
    }

    result = []

    for value in strings:

        if (
            value in stop_values

            and len(
                result
            ) >= 8
        ):

            break

        result.append(
            value
        )

    return result


def extract_main_text(
    soup,
    title
):

    candidates = []

    for selector_id in [
        "DeltaPlaceHolderMain",
        "ctl00_PlaceHolderMain",
        "contentBox",
        "content",
        "main-content",
        "page-content"
    ]:

        element = soup.find(
            id=selector_id
        )

        if (
            element is not None
            and element not in candidates
        ):

            candidates.append(
                element
            )

    main = soup.find(
        "main"
    )

    if (
        main is not None
        and main not in candidates
    ):

        candidates.append(
            main
        )

    if (
        soup.body is not None
        and soup.body not in candidates
    ):

        candidates.append(
            soup.body
        )

    best = ""

    for container in candidates:

        strings = container_strings(
            container
        )

        strings = slice_real_content(
            strings,
            title
        )

        text = "\n".join(
            strings
        ).strip()

        if len(
            text
        ) > len(
            best
        ):

            best = text

    return best


# =========================================================
# LINK EXTRACTION
# =========================================================

def extract_campaign_links(
    soup,
    page_url
):

    result = []

    seen = set()

    for anchor in soup.find_all(
        "a",
        href=True
    ):

        url = normalize_url(
            page_url,
            anchor.get(
                "href"
            )
        )

        if not is_campaign_namespace_url(
            url
        ):

            continue

        key = canonical_url(
            url
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        result.append(
            url
        )

    return result


# =========================================================
# CANDIDATE
# =========================================================

def ensure_candidate(
    candidates,
    url
):

    url = normalize_url(
        BASE_URL,
        url
    )

    key = canonical_url(
        url
    )

    if key not in candidates:

        candidates[
            key
        ] = {
            "url": url,
            "categories": set(),
            "sources": set(),
            "active_listing": False,
            "verified_extra": False,
            "force_active_without_date": False
        }

    return candidates[
        key
    ]


# =========================================================
# KATEGORİ DISCOVERY
# =========================================================

def discover_category_campaigns(
    session
):

    candidates = {}

    stats = {}

    print()

    print(
        "=" * 100
    )

    print(
        "1) KATEGORİ DISCOVERY"
    )

    print(
        "=" * 100
    )

    for (
        category,
        url
    ) in CATEGORY_URLS.items():

        print()

        print(
            "-",
            category
        )

        try:

            response = get_response(
                session,
                url
            )

            print(
                "  HTTP:",
                response.status_code
            )

            if (
                response.status_code
                != 200
            ):

                stats[
                    category
                ] = 0

                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            found = set()

            for detail_url in extract_campaign_links(
                soup,
                response.url
            ):

                if not is_detail_candidate_url(
                    detail_url
                ):

                    continue

                key = canonical_url(
                    detail_url
                )

                found.add(
                    key
                )

                candidate = ensure_candidate(
                    candidates,
                    detail_url
                )

                candidate[
                    "categories"
                ].add(
                    category
                )

                candidate[
                    "sources"
                ].add(
                    "kategori"
                )

                candidate[
                    "active_listing"
                ] = True

            stats[
                category
            ] = len(
                found
            )

            print(
                "  Gerçek detay:",
                len(
                    found
                )
            )

        except Exception as error:

            stats[
                category
            ] = 0

            print(
                "  HATA:",
                repr(
                    error
                )
            )

        time.sleep(
            REQUEST_DELAY
        )

    return (
        candidates,
        stats
    )


# =========================================================
# EXTRA SEEDS
# =========================================================

def add_extra_campaigns(
    candidates
):

    print()

    print(
        "=" * 100
    )

    print(
        "2) DOĞRULANMIŞ EXTRA BİREYSEL SAYFALAR"
    )

    print(
        "=" * 100
    )

    for (
        url,
        metadata
    ) in EXTRA_CAMPAIGNS.items():

        candidate = ensure_candidate(
            candidates,
            url
        )

        candidate[
            "categories"
        ].add(
            metadata[
                "kategori"
            ]
        )

        candidate[
            "sources"
        ].add(
            "dogrulanmis_extra"
        )

        candidate[
            "verified_extra"
        ] = True

        candidate[
            "force_active_without_date"
        ] = metadata.get(
            "tarih_yoksa_aktif",
            False
        )

        print(
            "-",
            url
        )


# =========================================================
# GRAPH DISCOVERY
# =========================================================

def discover_graph(
    session,
    candidates
):

    print()

    print(
        "=" * 100
    )

    print(
        "3) KAMPANYA LINK GRAPH"
    )

    print(
        "=" * 100
    )

    seeds = [
        CAMPAIGN_HOME
    ]

    seeds.extend(
        CATEGORY_URLS.values()
    )

    seeds.extend(
        EXTRA_CAMPAIGNS.keys()
    )

    seeds.extend(
        item[
            "url"
        ]

        for item
        in candidates.values()
    )

    queue = deque()

    queued = set()

    for url in seeds:

        url = normalize_url(
            BASE_URL,
            url
        )

        key = canonical_url(
            url
        )

        if key in queued:

            continue

        queued.add(
            key
        )

        queue.append(
            url
        )

    visited = set()

    new_count = 0

    while (
        queue

        and len(
            visited
        )
        < MAX_GRAPH_PAGES
    ):

        url = queue.popleft()

        key = canonical_url(
            url
        )

        if key in visited:

            continue

        visited.add(
            key
        )

        try:

            response = get_response(
                session,
                url
            )

            if (
                response.status_code
                != 200
            ):

                continue

            final_url = normalize_url(
                BASE_URL,
                response.url
            )

            if not is_campaign_namespace_url(
                final_url
            ):

                continue

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            for found_url in extract_campaign_links(
                soup,
                final_url
            ):

                found_key = canonical_url(
                    found_url
                )

                if is_ended_listing(
                    found_url
                ):

                    continue

                if is_listing_url(
                    found_url
                ):

                    if (
                        found_key
                        not in queued
                    ):

                        queued.add(
                            found_key
                        )

                        queue.append(
                            found_url
                        )

                    continue

                if not is_detail_candidate_url(
                    found_url
                ):

                    continue

                if (
                    found_key
                    not in candidates
                ):

                    new_count += 1

                candidate = ensure_candidate(
                    candidates,
                    found_url
                )

                candidate[
                    "sources"
                ].add(
                    "kampanya_link_agi"
                )

                if (
                    found_key
                    not in queued
                ):

                    queued.add(
                        found_key
                    )

                    queue.append(
                        found_url
                    )

        except Exception:

            pass

        time.sleep(
            REQUEST_DELAY
        )

    print(
        "Graph ziyaret:",
        len(
            visited
        )
    )

    print(
        "Graph yeni aday:",
        new_count
    )

    print(
        "Graph sonrası toplam:",
        len(
            candidates
        )
    )


# =========================================================
# BİTEN KAMPANYALAR ARŞİVİ
# =========================================================

def discover_archive(
    session
):

    ended = set()

    print()

    print(
        "=" * 100
    )

    print(
        "4) BİTEN KAMPANYALAR ARŞİVİ"
    )

    print(
        "=" * 100
    )

    try:

        response = get_response(
            session,
            ENDED_CAMPAIGNS_URL
        )

        print(
            "HTTP:",
            response.status_code
        )

        if (
            response.status_code
            == 200
        ):

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            for url in extract_campaign_links(
                soup,
                response.url
            ):

                if is_detail_candidate_url(
                    url
                ):

                    ended.add(
                        canonical_url(
                            url
                        )
                    )

    except Exception as error:

        print(
            "HATA:",
            repr(
                error
            )
        )

    print(
        "Arşiv detay URL:",
        len(
            ended
        )
    )

    return ended


# =========================================================
# TARİH PARSER
# =========================================================

def safe_date(
    year,
    month,
    day
):

    try:

        return date(
            int(
                year
            ),
            int(
                month
            ),
            int(
                day
            )
        )

    except Exception:

        return None


def extract_numeric_dates(text):

    result = []

    pattern = re.compile(
        r"(?<!\d)"
        r"(\d{1,2})"
        r"\s*[./-]\s*"
        r"(\d{1,2})"
        r"\s*[./-]\s*"
        r"(\d{4})"
        r"(?!\d)"
    )

    for match in pattern.finditer(
        text
    ):

        parsed = safe_date(
            match.group(3),
            match.group(2),
            match.group(1)
        )

        if parsed:

            result.append(
                parsed
            )

    return result


def extract_turkish_dates(text):

    result = []

    lower = tr_lower(
        text
    )

    month_pattern = (
        "|".join(
            MONTHS.keys()
        )
    )

    full_date_pattern = re.compile(
        rf"(?<!\d)"
        rf"(\d{{1,2}})"
        rf"\s+"
        rf"({month_pattern})"
        rf"\s+"
        rf"(\d{{4}})"
        rf"(?!\d)",
        flags=re.IGNORECASE
    )

    for match in full_date_pattern.finditer(
        lower
    ):

        parsed = safe_date(
            match.group(3),
            MONTHS[
                tr_lower(
                    match.group(2)
                )
            ],
            match.group(1)
        )

        if parsed:

            result.append(
                parsed
            )

    range_pattern = re.compile(
        rf"(?<!\d)"
        rf"(\d{{1,2}})"
        rf"\s+"
        rf"({month_pattern})"
        rf"\s*[-–—]\s*"
        rf"(\d{{1,2}})"
        rf"\s+"
        rf"({month_pattern})"
        rf"\s+"
        rf"(\d{{4}})",
        flags=re.IGNORECASE
    )

    for match in range_pattern.finditer(
        lower
    ):

        year = int(
            match.group(5)
        )

        first = safe_date(
            year,
            MONTHS[
                tr_lower(
                    match.group(2)
                )
            ],
            match.group(1)
        )

        second = safe_date(
            year,
            MONTHS[
                tr_lower(
                    match.group(4)
                )
            ],
            match.group(3)
        )

        if first:

            result.append(
                first
            )

        if second:

            result.append(
                second
            )

    return result


def extract_dates(text):

    result = []

    result.extend(
        extract_numeric_dates(
            text
        )
    )

    result.extend(
        extract_turkish_dates(
            text
        )
    )

    return sorted(
        set(
            result
        )
    )


def get_validity_lines(raw_text):

    result = []

    phrases = [
        "geçerlidir",
        "geçerli olacaktır",
        "tarihleri arasında",
        "tarih aralığında",
        "tarihine kadar",
        "tarihlerine kadar",
        "kampanya dönemi"
    ]

    for raw_line in raw_text.splitlines():

        line = normalize_text(
            raw_line
        )

        if not line:

            continue

        lower = tr_lower(
            line
        )

        if not any(
            phrase
            in lower

            for phrase
            in phrases
        ):

            continue

        if not extract_dates(
            line
        ):

            continue

        result.append(
            line
        )

    return unique_strings(
        result
    )


def extract_campaign_dates(raw_text):

    validity_lines = get_validity_lines(
        raw_text
    )

    dates = []

    for line in validity_lines:

        dates.extend(
            extract_dates(
                line
            )
        )

    dates = sorted(
        set(
            dates
        )
    )

    if not dates:

        return (
            None,
            None,
            validity_lines
        )

    if len(
        dates
    ) == 1:

        return (
            None,
            dates[0],
            validity_lines
        )

    return (
        dates[0],
        dates[-1],
        validity_lines
    )


# =========================================================
# GERÇEK KAMPANYA SİNYALİ - V4
# =========================================================

def has_campaign_signal(
    title,
    raw_text
):

    combined = tr_lower(
        (
            title
            + "\n"
            + raw_text
        )
    )

    strong_signals = [
        "kampanya koşulları",
        "kampanya detayları",
        "kampanya detayları:",
        "kampanyadan kimler",
        "kampanyadan nasıl",
        "kampanya hangi tarihler",
        "kampanya hangi tarih",
        "kampanya kapsamında",
        "kampanya dönemi",
        "kampanyaya katıl",
        "kampanyası kapsamında",
        "masrafsızlık kampanyası"
    ]

    return any(
        signal
        in combined

        for signal
        in strong_signals
    )


# =========================================================
# TİCARİ / KOBİ FİLTRESİ - V4
#
# ÖNEMLİ:
#
# Artık ham metinde yalnızca "ticari kredi kartı"
# geçmesi kampanyayı ticari yapmaz.
#
# Örneğin Sevdiklerinize Fırsat Verin kampanyası
# hem bireysel hem şahıs firması müşterilerini kapsıyor.
#
# Gerçek ticari kampanyalar başlık veya hedef kitle
# bağlamıyla tespit edilir.
# =========================================================

def is_commercial_campaign(
    title,
    raw_text
):

    title_lower = tr_lower(
        title
    )

    # =====================================================
    # BAŞLIKTA AÇIK TİCARİ / KOBİ SİNYALİ
    # =====================================================

    title_signals = [
        "mastercard business",
        "business kart",
        "masterkobi",
        "kobi",
        "kobİ",
        "tüzel",
        "ticari müşteri",
        "ticari kart"
    ]

    if any(
        tr_lower(
            signal
        )
        in title_lower

        for signal
        in title_signals
    ):

        return True

    # =====================================================
    # METİNDE AÇIK HEDEF KİTLE İFADESİ
    #
    # "ticari kredi kartına yüklenir" gibi sadece
    # ödeme yöntemini anlatan ifadeleri dikkate almıyoruz.
    # =====================================================

    lines = [
        normalize_text(
            line
        )

        for line
        in raw_text.splitlines()

        if normalize_text(
            line
        )
    ]

    audience_patterns = [
        re.compile(
            (
                r"(?:kampanya|fırsat)"
                r".{0,120}"
                r"(?:"
                r"ticari müşter"
                r"|kobi müşter"
                r"|tüzel müşter"
                r")"
            ),
            flags=re.IGNORECASE
        ),

        re.compile(
            (
                r"(?:"
                r"ticari müşteriler"
                r"|ticari müşterilerimiz"
                r"|kobi müşterileri"
                r"|kobi müşterilerimiz"
                r"|tüzel müşteriler"
                r")"
                r".{0,150}"
                r"(?:"
                r"yararlanabilir"
                r"|geçerlidir"
                r"|faydalanabilir"
                r"|özeldir"
                r")"
            ),
            flags=re.IGNORECASE
        ),

        re.compile(
            (
                r"(?:"
                r"yalnızca"
                r"|sadece"
                r")"
                r".{0,80}"
                r"(?:"
                r"ticari"
                r"|kobi"
                r"|tüzel"
                r")"
                r".{0,80}"
                r"(?:"
                r"müşteri"
                r"|firma"
                r"|şirket"
                r")"
            ),
            flags=re.IGNORECASE
        )
    ]

    for line in lines:

        lower = tr_lower(
            line
        )

        # -------------------------------------------------
        # Bireysel müşterilerin açıkça dahil edildiği
        # cümleleri ticari kampanya kanıtı saymıyoruz.
        # -------------------------------------------------

        if (
            "bireysel"
            in lower

            and (
                "geçerlidir"
                in lower

                or "yararlanabilir"
                in lower

                or "müşteri"
                in lower
            )
        ):

            continue

        for pattern in audience_patterns:

            if pattern.search(
                line
            ):

                return True

    return False


# =========================================================
# STATUS
# =========================================================

def classify_status(
    candidate,
    archive_urls,
    start_date,
    end_date
):

    today = date.today()

    url_key = canonical_url(
        candidate[
            "url"
        ]
    )

    # =====================================================
    # BİTEN KAMPANYA ARŞİVİ
    # =====================================================

    if (
        url_key
        in archive_urls
    ):

        return "biten_arsivinde"

    # =====================================================
    # GELECEK
    # =====================================================

    if (
        start_date is not None

        and start_date > today
    ):

        return "gelecek"

    # =====================================================
    # BİTMİŞ
    # =====================================================

    if (
        end_date is not None

        and end_date < today
    ):

        return "suresi_dolmus"

    # =====================================================
    # TARİHİNE GÖRE AKTİF
    # =====================================================

    if (
        end_date is not None

        and end_date >= today
    ):

        return "aktif"

    # =====================================================
    # RESMÎ AKTİF KATEGORİDE AMA TARİH YOK
    # =====================================================

    if candidate.get(
        "active_listing"
    ):

        return "aktif_listede"

    # =====================================================
    # ELLE DOĞRULANMIŞ EXTRA
    # =====================================================

    if (
        candidate.get(
            "verified_extra"
        )

        and candidate.get(
            "force_active_without_date"
        )
    ):

        return "aktif_dogrulanmis"

    return "belirsiz"


# =========================================================
# DETAY SCRAPE - V4
# =========================================================

def scrape_detail(
    session,
    candidate,
    archive_urls
):

    response = get_response(
        session,
        candidate[
            "url"
        ]
    )

    if (
        response.status_code
        != 200
    ):

        return {
            "type": "http_error",
            "url": candidate[
                "url"
            ],
            "sebep": (
                f"HTTP "
                f"{response.status_code}"
            )
        }

    final_url = normalize_url(
        BASE_URL,
        response.url
    )

    if not is_detail_candidate_url(
        final_url
    ):

        return {
            "type": "gecersiz",
            "url": candidate[
                "url"
            ],
            "sebep": (
                "final URL kampanya "
                "detay sayfası değil"
            )
        }

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    title = get_page_title(
        soup
    )

    if not title:

        return {
            "type": "gecersiz",
            "url": final_url,
            "sebep": "başlık yok"
        }

    if (
        tr_lower(
            title
        )
        in LISTING_TITLES
    ):

        return {
            "type": "gecersiz",
            "url": final_url,
            "sebep": (
                "kategori/listing sayfası"
            )
        }

    raw_text = extract_main_text(
        soup,
        title
    )

    if len(
        raw_text
    ) < 300:

        return {
            "type": "gecersiz",
            "url": final_url,
            "sebep": (
                f"ham metin kısa: "
                f"{len(raw_text)}"
            )
        }

    # =====================================================
    # V4:
    #
    # Resmî aktif kategori sayfasından doğrudan bulunan
    # detay URL'sini ekstra "kampanya koşulları" başlığı
    # olmadığı için çöpe atmıyoruz.
    #
    # Emekli promosyonu ve Masrafsız Bankacılık burada
    # kurtarılıyor.
    #
    # Graph ile rastgele bulunan sayfalar ise hâlâ güçlü
    # kampanya sinyali vermek zorunda.
    # =====================================================

    campaign_signal = (
        has_campaign_signal(
            title,
            raw_text
        )
    )

    trusted_source = (
        candidate.get(
            "active_listing"
        )

        or candidate.get(
            "verified_extra"
        )
    )

    if (
        not campaign_signal

        and not trusted_source
    ):

        return {
            "type": "gecersiz",
            "url": final_url,
            "baslik": title,
            "sebep": (
                "gerçek kampanya sinyali yok "
                "ve aktif kategori/verified "
                "kaynağından gelmiyor"
            )
        }

    # =====================================================
    # TİCARİ/KOBİ
    # =====================================================

    if is_commercial_campaign(
        title,
        raw_text
    ):

        return {
            "type": "ticari",
            "url": final_url,
            "baslik": title,
            "sebep": (
                "KOBİ/ticari hedef kitle"
            )
        }

    # =====================================================
    # TARİHLER
    # =====================================================

    (
        start_date,
        end_date,
        validity_lines
    ) = extract_campaign_dates(
        raw_text
    )

    candidate_for_status = dict(
        candidate
    )

    candidate_for_status[
        "url"
    ] = final_url

    status = classify_status(
        candidate_for_status,
        archive_urls,
        start_date,
        end_date
    )

    categories = sorted(
        candidate.get(
            "categories",
            set()
        )
    )

    sources = sorted(
        candidate.get(
            "sources",
            set()
        )
    )

    return {
        "type": "record",

        "record": {
            "banka": (
                "Türkiye Finans Katılım Bankası"
            ),

            "kayit_turu": (
                "kampanya"
            ),

            "urun_adi": (
                title
            ),

            "kampanya_kategorisi": (
                categories[0]
                if categories
                else ""
            ),

            "kampanya_kategorileri": (
                categories
            ),

            "aktiflik_durumu": (
                status
            ),

            "kampanya_baslangic_tarihi": (
                start_date.isoformat()
                if start_date
                else ""
            ),

            "kampanya_bitis_tarihi": (
                end_date.isoformat()
                if end_date
                else ""
            ),

            "tarih_kaynak_satirlari": (
                validity_lines
            ),

            "kesif_kaynaklari": (
                sources
            ),

            "aktif_kategori_listesinde": (
                bool(
                    candidate.get(
                        "active_listing"
                    )
                )
            ),

            "kaynak_url": (
                final_url
            ),

            "ham_metin": (
                raw_text
            )
        }
    }


# =========================================================
# DUPLICATE
# =========================================================

def remove_duplicates(records):

    result = []

    duplicate = []

    seen_urls = set()

    seen_contents = set()

    for record in records:

        url_key = canonical_url(
            record[
                "kaynak_url"
            ]
        )

        content_key = tr_lower(
            normalize_text(
                record[
                    "ham_metin"
                ]
            )
        )

        if (
            url_key
            in seen_urls
        ):

            duplicate.append(
                {
                    "sebep": (
                        "duplicate URL"
                    ),
                    "urun_adi": (
                        record[
                            "urun_adi"
                        ]
                    ),
                    "kaynak_url": (
                        record[
                            "kaynak_url"
                        ]
                    )
                }
            )

            continue

        if (
            content_key
            in seen_contents
        ):

            duplicate.append(
                {
                    "sebep": (
                        "duplicate içerik"
                    ),
                    "urun_adi": (
                        record[
                            "urun_adi"
                        ]
                    ),
                    "kaynak_url": (
                        record[
                            "kaynak_url"
                        ]
                    )
                }
            )

            continue

        seen_urls.add(
            url_key
        )

        seen_contents.add(
            content_key
        )

        result.append(
            record
        )

    return (
        result,
        duplicate
    )


# =========================================================
# CATEGORY COUNTS
# =========================================================

def category_counts(records):

    result = {}

    for record in records:

        category = (
            record.get(
                "kampanya_kategorisi"
            )
            or "Kategorisiz"
        )

        result[
            category
        ] = (
            result.get(
                category,
                0
            )
            + 1
        )

    return result


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 100
    )

    print(
        "TÜRKİYE FİNANS KAMPANYA SCRAPER V4"
    )

    print(
        "=" * 100
    )

    print(
        "Tarama tarihi:",
        date.today().isoformat()
    )

    session = requests.Session()

    # =====================================================
    # KATEGORİ
    # =====================================================

    (
        candidates,
        category_stats
    ) = discover_category_campaigns(
        session
    )

    category_direct_count = len(
        candidates
    )

    # =====================================================
    # EXTRA
    # =====================================================

    add_extra_campaigns(
        candidates
    )

    extra_count = len(
        candidates
    )

    # =====================================================
    # GRAPH
    # =====================================================

    discover_graph(
        session,
        candidates
    )

    graph_count = len(
        candidates
    )

    # =====================================================
    # ARCHIVE
    # =====================================================

    archive_urls = discover_archive(
        session
    )

    # =====================================================
    # DISCOVERY SUMMARY
    # =====================================================

    print()

    print(
        "=" * 100
    )

    print(
        "DISCOVERY ÖZETİ"
    )

    print(
        "=" * 100
    )

    print(
        "Kategori direct aday:",
        category_direct_count
    )

    print(
        "Extra sonrası aday:",
        extra_count
    )

    print(
        "Graph sonrası aday:",
        graph_count
    )

    print(
        "Biten arşiv URL:",
        len(
            archive_urls
        )
    )

    print()

    print(
        "KATEGORİ DIRECT SAYILARI:"
    )

    for (
        category,
        count
    ) in category_stats.items():

        print(
            f"- {category}: {count}"
        )

    # =====================================================
    # DETAYLAR
    # =====================================================

    records = []

    commercial_excluded = []

    invalid_candidates = []

    http_errors = []

    candidates_sorted = sorted(
        candidates.values(),
        key=lambda item: (
            canonical_url(
                item[
                    "url"
                ]
            )
        )
    )

    print()

    print(
        "=" * 100
    )

    print(
        "DETAY SAYFALARI"
    )

    print(
        "=" * 100
    )

    for (
        index,
        candidate
    ) in enumerate(
        candidates_sorted,
        start=1
    ):

        print()

        print(
            "-" * 100
        )

        print(
            (
                f"[{index}/"
                f"{len(candidates_sorted)}]"
            )
        )

        print(
            "URL:",
            candidate[
                "url"
            ]
        )

        try:

            result = scrape_detail(
                session,
                candidate,
                archive_urls
            )

            result_type = result[
                "type"
            ]

            if (
                result_type
                == "record"
            ):

                record = result[
                    "record"
                ]

                records.append(
                    record
                )

                print(
                    "Kampanya:",
                    record[
                        "urun_adi"
                    ]
                )

                print(
                    "Durum:",
                    record[
                        "aktiflik_durumu"
                    ]
                )

                print(
                    "Başlangıç:",
                    (
                        record[
                            "kampanya_baslangic_tarihi"
                        ]
                        or "-"
                    )
                )

                print(
                    "Bitiş:",
                    (
                        record[
                            "kampanya_bitis_tarihi"
                        ]
                        or "-"
                    )
                )

                print(
                    "Kategori:",
                    (
                        record[
                            "kampanya_kategorisi"
                        ]
                        or "-"
                    )
                )

                print(
                    "Ham metin:",
                    len(
                        record[
                            "ham_metin"
                        ]
                    )
                )

            elif (
                result_type
                == "ticari"
            ):

                commercial_excluded.append(
                    result
                )

                print(
                    (
                        "ELENDİ "
                        "[TİCARİ/KOBİ]:"
                    ),
                    result.get(
                        "baslik",
                        ""
                    )
                )

            elif (
                result_type
                == "http_error"
            ):

                http_errors.append(
                    result
                )

                print(
                    "HTTP HATASI:",
                    result[
                        "sebep"
                    ]
                )

            else:

                invalid_candidates.append(
                    result
                )

                print(
                    "GEÇERSİZ/ORPHAN ADAY:",
                    result[
                        "sebep"
                    ]
                )

        except Exception as error:

            http_errors.append(
                {
                    "url": (
                        candidate[
                            "url"
                        ]
                    ),
                    "sebep": repr(
                        error
                    )
                }
            )

            print(
                "HATA:",
                repr(
                    error
                )
            )

        time.sleep(
            REQUEST_DELAY
        )

    # =====================================================
    # DUPLICATE
    # =====================================================

    (
        records,
        duplicate_records
    ) = remove_duplicates(
        records
    )

    # =====================================================
    # STATUS
    # =====================================================

    active_records = []

    expired_records = []

    future_records = []

    archive_records = []

    uncertain_records = []

    for record in records:

        status = record[
            "aktiflik_durumu"
        ]

        if status in {
            "aktif",
            "aktif_listede",
            "aktif_dogrulanmis"
        }:

            active_records.append(
                record
            )

        elif (
            status
            == "suresi_dolmus"
        ):

            expired_records.append(
                record
            )

        elif (
            status
            == "gelecek"
        ):

            future_records.append(
                record
            )

        elif (
            status
            == "biten_arsivinde"
        ):

            archive_records.append(
                record
            )

        else:

            uncertain_records.append(
                record
            )

    active_records = sorted(
        active_records,
        key=lambda item: (
            tr_lower(
                item[
                    "urun_adi"
                ]
            )
        )
    )

    expired_records = sorted(
        expired_records,
        key=lambda item: (
            tr_lower(
                item[
                    "urun_adi"
                ]
            )
        )
    )

    # =====================================================
    # OUTPUT
    #
    # "kampanyalar" SADECE AKTİF BİREYSEL
    # =====================================================

    output = {
        "banka": (
            "Türkiye Finans Katılım Bankası"
        ),

        "kayit_turu": (
            "kampanya"
        ),

        "tarama_tarihi": (
            date.today().isoformat()
        ),

        "discovery": {
            "kategori_direct_aday": (
                category_direct_count
            ),

            "extra_sonrasi_aday": (
                extra_count
            ),

            "graph_sonrasi_aday": (
                graph_count
            ),

            "biten_arsiv_url_sayisi": (
                len(
                    archive_urls
                )
            ),

            "ticari_kobi_elenen": (
                len(
                    commercial_excluded
                )
            ),

            "gecersiz_orphan_aday": (
                len(
                    invalid_candidates
                )
            )
        },

        "aktif_kampanya_sayisi": (
            len(
                active_records
            )
        ),

        "kategori_sayilari": (
            category_counts(
                active_records
            )
        ),

        "kampanyalar": (
            active_records
        ),

        "elenen_ticari_kobi": (
            commercial_excluded
        ),

        "elenen_suresi_dolmus": [
            {
                "urun_adi": (
                    record[
                        "urun_adi"
                    ]
                ),

                "kampanya_baslangic_tarihi": (
                    record[
                        "kampanya_baslangic_tarihi"
                    ]
                ),

                "kampanya_bitis_tarihi": (
                    record[
                        "kampanya_bitis_tarihi"
                    ]
                ),

                "kaynak_url": (
                    record[
                        "kaynak_url"
                    ]
                )
            }

            for record
            in expired_records
        ],

        "elenen_biten_arsivinde": [
            {
                "urun_adi": (
                    record[
                        "urun_adi"
                    ]
                ),

                "kaynak_url": (
                    record[
                        "kaynak_url"
                    ]
                )
            }

            for record
            in archive_records
        ],

        "gelecek_kampanyalar": [
            {
                "urun_adi": (
                    record[
                        "urun_adi"
                    ]
                ),

                "kampanya_baslangic_tarihi": (
                    record[
                        "kampanya_baslangic_tarihi"
                    ]
                ),

                "kaynak_url": (
                    record[
                        "kaynak_url"
                    ]
                )
            }

            for record
            in future_records
        ],

        "manuel_kontrol_gerektirenler": [
            {
                "urun_adi": (
                    record[
                        "urun_adi"
                    ]
                ),

                "kaynak_url": (
                    record[
                        "kaynak_url"
                    ]
                )
            }

            for record
            in uncertain_records
        ],

        "gecersiz_orphan_adaylar": (
            invalid_candidates
        ),

        "http_hatalari": (
            http_errors
        ),

        "duplicate_kayitlar": (
            duplicate_records
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
    # FINAL RAPOR
    # =====================================================

    print()

    print(
        "=" * 100
    )

    print(
        "TÜRKİYE FİNANS KAMPANYA V4 SONUCU"
    )

    print(
        "=" * 100
    )

    print(
        "Kategori direct aday:",
        category_direct_count
    )

    print(
        "Extra sonrası aday:",
        extra_count
    )

    print(
        "Graph sonrası toplam aday:",
        graph_count
    )

    print(
        "Geçerli kampanya sayfası:",
        len(
            records
        )
    )

    print(
        "Aktif BİREYSEL kampanya:",
        len(
            active_records
        )
    )

    print(
        "Ticari/KOBİ elenen:",
        len(
            commercial_excluded
        )
    )

    print(
        "Geçersiz/orphan aday:",
        len(
            invalid_candidates
        )
    )

    print(
        "Süresi dolmuş:",
        len(
            expired_records
        )
    )

    print(
        "Biten arşivinde:",
        len(
            archive_records
        )
    )

    print(
        "Gelecek:",
        len(
            future_records
        )
    )

    print(
        "Manuel kontrol:",
        len(
            uncertain_records
        )
    )

    print(
        "HTTP hata:",
        len(
            http_errors
        )
    )

    print(
        "Duplicate:",
        len(
            duplicate_records
        )
    )

    # =====================================================
    # AKTİF
    # =====================================================

    print()

    print(
        "=" * 100
    )

    print(
        "AKTİF BİREYSEL KAMPANYALAR"
    )

    print(
        "=" * 100
    )

    for (
        index,
        record
    ) in enumerate(
        active_records,
        start=1
    ):

        print()

        print(
            (
                f"{index}. "
                f"{record['urun_adi']}"
            )
        )

        print(
            "   Kategori:",
            (
                record[
                    "kampanya_kategorisi"
                ]
                or "-"
            )
        )

        print(
            "   Durum:",
            record[
                "aktiflik_durumu"
            ]
        )

        print(
            "   Başlangıç:",
            (
                record[
                    "kampanya_baslangic_tarihi"
                ]
                or "-"
            )
        )

        print(
            "   Bitiş:",
            (
                record[
                    "kampanya_bitis_tarihi"
                ]
                or "-"
            )
        )

        print(
            "   URL:",
            record[
                "kaynak_url"
            ]
        )

    # =====================================================
    # SÜRESİ DOLMUŞ
    # =====================================================

    if expired_records:

        print()

        print(
            "=" * 100
        )

        print(
            "SÜRESİ DOLMUŞ OLDUĞU İÇİN ELENENLER"
        )

        print(
            "=" * 100
        )

        for record in expired_records:

            print()

            print(
                "-",
                record[
                    "urun_adi"
                ]
            )

            print(
                "  Başlangıç:",
                (
                    record[
                        "kampanya_baslangic_tarihi"
                    ]
                    or "-"
                )
            )

            print(
                "  Bitiş:",
                (
                    record[
                        "kampanya_bitis_tarihi"
                    ]
                    or "-"
                )
            )

            print(
                "  URL:",
                record[
                    "kaynak_url"
                ]
            )

    # =====================================================
    # TİCARİ
    # =====================================================

    if commercial_excluded:

        print()

        print(
            "=" * 100
        )

        print(
            "TİCARİ/KOBİ OLDUĞU İÇİN ELENENLER"
        )

        print(
            "=" * 100
        )

        for item in commercial_excluded:

            print(
                (
                    "- "
                    f"{item.get('baslik', '')}"
                )
            )

            print(
                " ",
                item[
                    "url"
                ]
            )

    # =====================================================
    # ORPHAN
    # =====================================================

    if invalid_candidates:

        print()

        print(
            "=" * 100
        )

        print(
            "GEÇERSİZ / ORPHAN ADAYLAR"
        )

        print(
            "=" * 100
        )

        for item in invalid_candidates:

            print(
                "-",
                item[
                    "url"
                ]
            )

            print(
                " ",
                item[
                    "sebep"
                ]
            )

    # =====================================================
    # MANUEL
    # =====================================================

    if uncertain_records:

        print()

        print(
            "=" * 100
        )

        print(
            "MANUEL KONTROL"
        )

        print(
            "=" * 100
        )

        for record in uncertain_records:

            print(
                "-",
                record[
                    "urun_adi"
                ]
            )

            print(
                " ",
                record[
                    "kaynak_url"
                ]
            )

    # =====================================================
    # FINAL
    # =====================================================

    print()

    print(
        "=" * 100
    )

    if (
        len(
            active_records
        ) > 0

        and len(
            http_errors
        ) == 0

        and len(
            duplicate_records
        ) == 0

        and len(
            uncertain_records
        ) == 0
    ):

        print(
            "SONUÇ: TÜRKİYE FİNANS "
            "BİREYSEL KAMPANYA RAW "
            "İLK KONTROLDEN GEÇTİ ✅"
        )

    else:

        print(
            "SONUÇ: RAW KONTROL "
            "GEREKİYOR ⚠️"
        )

    print(
        "JSON:",
        OUTPUT_FILE
    )

    print(
        "=" * 100
    )


if __name__ == "__main__":

    main()