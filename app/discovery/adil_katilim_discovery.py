import json
import re
import sys
from collections import deque
from datetime import datetime
from pathlib import Path
from urllib.parse import (
    urljoin,
    urlparse,
    urlunparse,
)

import requests
from bs4 import BeautifulSoup


# =========================================================
# CONFIG
# =========================================================

ROOT = Path(__file__).resolve().parents[2]

OUTPUT_FILE = (
    ROOT
    / "data"
    / "raw"
    / "adil_katilim_discovery.json"
)

BASE_URL = "https://www.adilkatilim.com.tr/"

BANK_NAME = "Adil Katılım Bankası A.Ş."

DOMAIN = "www.adilkatilim.com.tr"

MAX_PAGES = 250
MAX_DEPTH = 5
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


SKIP_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".css",
    ".js",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp4",
    ".mp3",
    ".zip",
    ".rar",
}


FINANCE_KEYWORDS = {
    "finansman": 5,
    "bireysel finansman": 8,
    "ticari finansman": 8,
    "ihtiyaç finansmanı": 8,
    "ihtiyac finansmani": 8,
    "konut finansmanı": 8,
    "konut finansmani": 8,
    "araç finansmanı": 8,
    "arac finansmani": 8,
    "taşıt finansmanı": 8,
    "tasit finansmani": 8,
    "murabaha": 5,
    "murâbaha": 5,
    "kullandırım": 3,
    "kullandirim": 3,
}


CAMPAIGN_KEYWORDS = {
    "kampanya": 10,
    "kampanyalar": 10,
    "fırsat": 4,
    "firsat": 4,
    "indirim": 5,
    "cashback": 5,
    "nakit iade": 5,
    "hediye": 4,
    "promosyon": 5,
    "peşin fiyatına": 4,
    "pesin fiyatina": 4,
}


PRODUCT_KEYWORDS = {
    "ürün ve hizmetler": 8,
    "urun ve hizmetler": 8,
    "ürünler": 5,
    "urunler": 5,
    "hizmetler": 4,
    "katılım bankacılığı": 3,
    "katilim bankaciligi": 3,
}


# =========================================================
# TEXT
# =========================================================

def normalize_text(value):
    value = str(value or "")

    value = (
        value
        .replace("\xa0", " ")
        .replace("İ", "i")
        .replace("I", "ı")
        .casefold()
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


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


# =========================================================
# URL
# =========================================================

def canonicalize_url(url):
    try:
        parsed = urlparse(
            url
        )

    except Exception:
        return ""

    scheme = (
        parsed.scheme
        or "https"
    )

    netloc = (
        parsed.netloc
        or DOMAIN
    ).lower()

    if netloc == "adilkatilim.com.tr":
        netloc = DOMAIN

    if netloc != DOMAIN:
        return ""

    path = (
        parsed.path
        or "/"
    )

    path = re.sub(
        r"/+",
        "/",
        path,
    )

    if (
        path != "/"
        and path.endswith("/")
    ):
        path = path[:-1]

    return urlunparse(
        (
            scheme,
            netloc,
            path,
            "",
            "",
            "",
        )
    )


def is_internal_url(url):
    try:
        parsed = urlparse(
            url
        )

        host = parsed.netloc.lower()

        return host in {
            "",
            DOMAIN,
            "adilkatilim.com.tr",
        }

    except Exception:
        return False


def get_extension(url):
    path = urlparse(
        url
    ).path.lower()

    return Path(
        path
    ).suffix


def should_skip_url(url):
    extension = get_extension(
        url
    )

    if extension in SKIP_EXTENSIONS:
        return True

    lowered = url.lower()

    skip_fragments = (
        "mailto:",
        "tel:",
        "javascript:",
    )

    return any(
        lowered.startswith(
            fragment
        )
        for fragment
        in skip_fragments
    )


# =========================================================
# SCORING
# =========================================================

def calculate_score(
    url,
    title,
    text,
    keyword_map,
):
    normalized_url = normalize_text(
        url
    )

    normalized_title = normalize_text(
        title
    )

    normalized_text = normalize_text(
        text
    )

    score = 0
    matched = []

    for keyword, weight in keyword_map.items():
        keyword_normalized = normalize_text(
            keyword
        )

        matched_here = False

        if keyword_normalized in normalized_url:
            score += weight * 3
            matched_here = True

        if keyword_normalized in normalized_title:
            score += weight * 2
            matched_here = True

        if keyword_normalized in normalized_text:
            score += weight
            matched_here = True

        if matched_here:
            matched.append(
                keyword
            )

    return (
        score,
        sorted(
            set(
                matched
            )
        ),
    )


# =========================================================
# SITEMAP DISCOVERY
# =========================================================

def discover_sitemaps(
    session,
):
    sitemap_urls = set()

    robots_url = urljoin(
        BASE_URL,
        "/robots.txt",
    )

    try:
        response = session.get(
            robots_url,
            timeout=TIMEOUT,
        )

        if response.ok:
            for line in response.text.splitlines():
                line = line.strip()

                if line.lower().startswith(
                    "sitemap:"
                ):
                    sitemap = line.split(
                        ":",
                        1,
                    )[1].strip()

                    if sitemap:
                        sitemap_urls.add(
                            sitemap
                        )

    except requests.RequestException:
        pass

    sitemap_urls.add(
        urljoin(
            BASE_URL,
            "/sitemap.xml",
        )
    )

    return sorted(
        sitemap_urls
    )


def parse_sitemap(
    session,
    sitemap_url,
    visited_sitemaps=None,
):
    if visited_sitemaps is None:
        visited_sitemaps = set()

    if sitemap_url in visited_sitemaps:
        return set()

    visited_sitemaps.add(
        sitemap_url
    )

    discovered = set()

    try:
        response = session.get(
            sitemap_url,
            timeout=TIMEOUT,
        )

        if not response.ok:
            return discovered

        content_type = (
            response.headers
            .get(
                "Content-Type",
                "",
            )
            .lower()
        )

        if (
            "xml" not in content_type
            and
            "<loc>" not in response.text
        ):
            return discovered

        soup = BeautifulSoup(
            response.text,
            "xml",
        )

        locs = [
            clean_text(
                loc.get_text()
            )
            for loc in soup.find_all(
                "loc"
            )
        ]

        for loc in locs:
            if not loc:
                continue

            if loc.lower().endswith(
                ".xml"
            ):
                discovered.update(
                    parse_sitemap(
                        session,
                        loc,
                        visited_sitemaps,
                    )
                )

                continue

            if not is_internal_url(
                loc
            ):
                continue

            canonical = canonicalize_url(
                loc
            )

            if canonical:
                discovered.add(
                    canonical
                )

    except Exception:
        pass

    return discovered


# =========================================================
# PAGE PARSER
# =========================================================

def parse_page(
    session,
    url,
):
    response = session.get(
        url,
        timeout=TIMEOUT,
        allow_redirects=True,
    )

    final_url = canonicalize_url(
        response.url
    )

    content_type = (
        response.headers
        .get(
            "Content-Type",
            ""
        )
        .lower()
    )

    result = {
        "url": final_url or url,
        "status_code": response.status_code,
        "content_type": content_type,
        "title": "",
        "text": "",
        "links": [],
        "pdf_links": [],
    }

    if not response.ok:
        return result

    if (
        "text/html"
        not in content_type
    ):
        return result

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    for element in soup(
        [
            "script",
            "style",
            "noscript",
        ]
    ):
        element.decompose()

    if soup.title:
        result["title"] = clean_text(
            soup.title.get_text(
                " ",
                strip=True,
            )
        )

    body = soup.body or soup

    text = body.get_text(
        " ",
        strip=True,
    )

    result["text"] = clean_text(
        text
    )

    links = set()
    pdf_links = set()

    for anchor in soup.find_all(
        "a",
        href=True,
    ):
        href = clean_text(
            anchor.get(
                "href"
            )
        )

        if not href:
            continue

        if should_skip_url(
            href
        ):
            continue

        absolute_url = urljoin(
            response.url,
            href,
        )

        if not is_internal_url(
            absolute_url
        ):
            continue

        extension = get_extension(
            absolute_url
        )

        if extension == ".pdf":
            pdf_links.add(
                absolute_url
            )

            continue

        canonical = canonicalize_url(
            absolute_url
        )

        if canonical:
            links.add(
                canonical
            )

    result["links"] = sorted(
        links
    )

    result["pdf_links"] = sorted(
        pdf_links
    )

    return result


# =========================================================
# MAIN DISCOVERY
# =========================================================

def main():
    print()

    print(
        "=" * 120
    )

    print(
        "ADİL KATILIM - WEBSITE DISCOVERY V1"
    )

    print(
        "=" * 120
    )

    print(
        "Base URL:",
        BASE_URL,
    )

    print(
        "Output:",
        OUTPUT_FILE,
    )

    print()

    session = requests.Session()

    session.headers.update(
        HEADERS
    )

    # =====================================================
    # INITIAL URLS
    # =====================================================

    sitemap_urls = discover_sitemaps(
        session
    )

    sitemap_pages = set()

    for sitemap_url in sitemap_urls:
        pages = parse_sitemap(
            session,
            sitemap_url,
        )

        sitemap_pages.update(
            pages
        )

    print(
        "Sitemap endpoint:",
        len(
            sitemap_urls
        ),
    )

    print(
        "Sitemap page:",
        len(
            sitemap_pages
        ),
    )

    print()

    queue = deque()

    queue.append(
        (
            canonicalize_url(
                BASE_URL
            ),
            0,
        )
    )

    for url in sorted(
        sitemap_pages
    ):
        queue.append(
            (
                url,
                0,
            )
        )

    visited = set()

    pages = []

    pdf_links = set()

    errors = []

    finance_candidates = []
    campaign_candidates = []
    product_candidates = []

    # =====================================================
    # CRAWL
    # =====================================================

    while (
        queue
        and
        len(
            visited
        )
        < MAX_PAGES
    ):
        url, depth = queue.popleft()

        if not url:
            continue

        if url in visited:
            continue

        if depth > MAX_DEPTH:
            continue

        visited.add(
            url
        )

        try:
            page = parse_page(
                session,
                url,
            )

        except Exception as error:
            errors.append(
                {
                    "url": url,
                    "error": (
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                }
            )

            print(
                f"[ERROR] {url}"
            )

            continue

        print(
            (
                f"[{len(visited):03d}] "
                f"{page['status_code']} "
                f"depth={depth} "
                f"{url}"
            )
        )

        if (
            page["status_code"]
            != 200
        ):
            continue

        if (
            "text/html"
            not in page[
                "content_type"
            ]
        ):
            continue

        for pdf_url in page[
            "pdf_links"
        ]:
            pdf_links.add(
                pdf_url
            )

        text_preview = page[
            "text"
        ][:1000]

        finance_score, finance_words = (
            calculate_score(
                url=page["url"],
                title=page["title"],
                text=page["text"],
                keyword_map=FINANCE_KEYWORDS,
            )
        )

        campaign_score, campaign_words = (
            calculate_score(
                url=page["url"],
                title=page["title"],
                text=page["text"],
                keyword_map=CAMPAIGN_KEYWORDS,
            )
        )

        product_score, product_words = (
            calculate_score(
                url=page["url"],
                title=page["title"],
                text=page["text"],
                keyword_map=PRODUCT_KEYWORDS,
            )
        )

        page_record = {
            "url": page[
                "url"
            ],
            "title": page[
                "title"
            ],
            "depth": depth,
            "status_code": page[
                "status_code"
            ],
            "finance_score": finance_score,
            "campaign_score": campaign_score,
            "product_score": product_score,
            "text_preview": text_preview,
        }

        pages.append(
            page_record
        )

        # -------------------------------------------------
        # FINANCE CANDIDATE
        # -------------------------------------------------

        if finance_score > 0:
            finance_candidates.append(
                {
                    "url": page[
                        "url"
                    ],
                    "title": page[
                        "title"
                    ],
                    "score": finance_score,
                    "matched_keywords": (
                        finance_words
                    ),
                    "text_preview": (
                        text_preview
                    ),
                }
            )

        # -------------------------------------------------
        # CAMPAIGN CANDIDATE
        # -------------------------------------------------

        if campaign_score > 0:
            campaign_candidates.append(
                {
                    "url": page[
                        "url"
                    ],
                    "title": page[
                        "title"
                    ],
                    "score": campaign_score,
                    "matched_keywords": (
                        campaign_words
                    ),
                    "text_preview": (
                        text_preview
                    ),
                }
            )

        # -------------------------------------------------
        # PRODUCT CANDIDATE
        # -------------------------------------------------

        if product_score > 0:
            product_candidates.append(
                {
                    "url": page[
                        "url"
                    ],
                    "title": page[
                        "title"
                    ],
                    "score": product_score,
                    "matched_keywords": (
                        product_words
                    ),
                    "text_preview": (
                        text_preview
                    ),
                }
            )

        # -------------------------------------------------
        # NEXT LINKS
        # -------------------------------------------------

        if depth < MAX_DEPTH:
            for link in page[
                "links"
            ]:
                if link not in visited:
                    queue.append(
                        (
                            link,
                            depth + 1,
                        )
                    )

    # =====================================================
    # SORT
    # =====================================================

    finance_candidates.sort(
        key=lambda item: (
            -item["score"],
            item["url"],
        )
    )

    campaign_candidates.sort(
        key=lambda item: (
            -item["score"],
            item["url"],
        )
    )

    product_candidates.sort(
        key=lambda item: (
            -item["score"],
            item["url"],
        )
    )

    pages.sort(
        key=lambda item: (
            item["url"]
        )
    )

    # =====================================================
    # OUTPUT
    # =====================================================

    result = {
        "banka": BANK_NAME,
        "base_url": BASE_URL,
        "discovery_time": (
            datetime.now()
            .astimezone()
            .isoformat(
                timespec="seconds"
            )
        ),
        "summary": {
            "pages_crawled": len(
                pages
            ),
            "finance_candidate_count": len(
                finance_candidates
            ),
            "campaign_candidate_count": len(
                campaign_candidates
            ),
            "product_candidate_count": len(
                product_candidates
            ),
            "pdf_count": len(
                pdf_links
            ),
            "error_count": len(
                errors
            ),
        },
        "finance_candidates": (
            finance_candidates
        ),
        "campaign_candidates": (
            campaign_candidates
        ),
        "product_candidates": (
            product_candidates
        ),
        "pdf_links": sorted(
            pdf_links
        ),
        "all_pages": pages,
        "errors": errors,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=4,
        )

    # =====================================================
    # REPORT
    # =====================================================

    print()

    print(
        "=" * 120
    )

    print(
        "DISCOVERY SONUCU"
    )

    print(
        "=" * 120
    )

    print(
        "Crawled page:",
        len(
            pages
        ),
    )

    print(
        "Finance candidate:",
        len(
            finance_candidates
        ),
    )

    print(
        "Campaign candidate:",
        len(
            campaign_candidates
        ),
    )

    print(
        "Product candidate:",
        len(
            product_candidates
        ),
    )

    print(
        "PDF:",
        len(
            pdf_links
        ),
    )

    print(
        "Error:",
        len(
            errors
        ),
    )

    print()

    # =====================================================
    # TOP FINANCE
    # =====================================================

    print(
        "TOP FINANCE CANDIDATES"
    )

    print(
        "-" * 120
    )

    for index, item in enumerate(
        finance_candidates[:20],
        start=1,
    ):
        print(
            (
                f"[{index:02d}] "
                f"score={item['score']} "
                f"{item['title']}"
            )
        )

        print(
            "     ",
            item[
                "url"
            ],
        )

        print(
            "      keywords:",
            item[
                "matched_keywords"
            ],
        )

    print()

    # =====================================================
    # TOP CAMPAIGN
    # =====================================================

    print(
        "TOP CAMPAIGN CANDIDATES"
    )

    print(
        "-" * 120
    )

    if campaign_candidates:
        for index, item in enumerate(
            campaign_candidates[:20],
            start=1,
        ):
            print(
                (
                    f"[{index:02d}] "
                    f"score={item['score']} "
                    f"{item['title']}"
                )
            )

            print(
                "     ",
                item[
                    "url"
                ],
            )

            print(
                "      keywords:",
                item[
                    "matched_keywords"
                ],
            )

    else:
        print(
            "Campaign candidate bulunamadı."
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