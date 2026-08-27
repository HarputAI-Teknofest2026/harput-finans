import json
import os
import time

from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


BASE_URL = "https://www.kuveytturk.com.tr"

CAMPAIGN_URL = (
    "https://www.kuveytturk.com.tr/"
    "kampanyalar/kendim-icin"
)

OUTPUT_FILE = (
    "data/raw/"
    "kuveyt_turk_kampanyalar.json"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}


# =========================================================
# ANA SİTEDE 404 DÖNEN AMA KUVEYT TÜRK'ÜN
# RESMİ SAĞLAM KART ALT DOMAINİNDE BULUNAN
# KAMPANYALAR
# =========================================================

FALLBACK_URLS = {

    (
        "https://www.kuveytturk.com.tr/"
        "kampanyalar/kendim-icin/"
        "kart-kampanyalari/"
        "konforda-vade-farksiz-9-aya-varan-taksit-firsati"
    ):
    (
        "https://saglamkart.kuveytturk.com.tr/"
        "kampanyalar/"
        "konforda-pesin-fiyatina-9-aya-varan-taksit-imkani-2898"
    )
}


# =========================================================
# URL TEMİZLEME
# =========================================================

def normalize_url(url):

    url = url.split("#")[0]
    url = url.split("?")[0]

    return url.rstrip("/")


# =========================================================
# KAMPANYA DETAY URL'Sİ Mİ?
# =========================================================

def is_campaign_detail_url(url):

    parsed = urlparse(
        url
    )

    parts = [
        part
        for part in parsed.path.strip("/").split("/")
        if part
    ]


    if len(parts) < 4:
        return False


    if parts[0] != "kampanyalar":
        return False


    if parts[1] != "kendim-icin":
        return False


    if "kampanya-arsivi" in parts:
        return False


    return True


# =========================================================
# PLAYWRIGHT İLE TÜM KAMPANYALARI YÜKLE
# =========================================================

def get_all_campaign_links():

    links = []

    click_count = 0


    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True
        )


        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 1200
            },

            user_agent=HEADERS[
                "User-Agent"
            ]
        )


        print(
            "Kampanya ana sayfası açılıyor..."
        )


        response = page.goto(
            CAMPAIGN_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )


        if response:

            print(
                "Ana sayfa HTTP:",
                response.status
            )


        page.wait_for_timeout(
            2000
        )


        # =================================================
        # DAHA FAZLA YÜKLE
        # =================================================

        while True:

            button = page.get_by_text(
                "Daha Fazla Yükle",
                exact=True
            )


            try:

                count = button.count()

            except Exception:

                count = 0


            if count == 0:

                break


            visible_button = None


            for index in range(
                count
            ):

                candidate = button.nth(
                    index
                )


                try:

                    if candidate.is_visible():

                        visible_button = candidate

                        break

                except Exception:

                    continue


            if visible_button is None:

                break


            before_links = page.locator(
                'a[href*="/kampanyalar/kendim-icin/"]'
            ).count()


            print(
                f"Daha Fazla Yükle tıklanıyor... "
                f"({click_count + 1})"
            )


            try:

                visible_button.scroll_into_view_if_needed()

                visible_button.click(
                    timeout=10000
                )

            except Exception as error:

                print(
                    "Load more tıklama sona erdi:",
                    error
                )

                break


            click_count += 1


            page.wait_for_timeout(
                1500
            )


            after_links = page.locator(
                'a[href*="/kampanyalar/kendim-icin/"]'
            ).count()


            print(
                "Link sayısı:",
                before_links,
                "->",
                after_links
            )


            if click_count >= 100:

                print(
                    "Güvenlik nedeniyle "
                    "100 tıklamada durduruldu."
                )

                break


            if after_links <= before_links:

                page.wait_for_timeout(
                    2000
                )


                final_count = page.locator(
                    'a[href*="/kampanyalar/kendim-icin/"]'
                ).count()


                if final_count <= before_links:

                    break


        # =================================================
        # HREF'LER
        # =================================================

        anchors = page.locator(
            "a[href]"
        )


        total_anchors = anchors.count()


        for index in range(
            total_anchors
        ):

            href = anchors.nth(
                index
            ).get_attribute(
                "href"
            )


            if not href:

                continue


            full_url = normalize_url(
                urljoin(
                    BASE_URL,
                    href
                )
            )


            if not is_campaign_detail_url(
                full_url
            ):

                continue


            if full_url not in links:

                links.append(
                    full_url
                )


        browser.close()


    return (
        links,
        click_count
    )


# =========================================================
# BAŞLIK TEMİZLEME
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
        " - Kuveyt Türk",
        " | Kampanyalar | Sağlam Kart Kuveyt Türk",
        " | Sağlam Kart Kuveyt Türk"
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
        "Kampanyalar",
        "Kendim İçin",
        "Ana Sayfa",
        "Sağlam Kart"
    }


    if title in invalid:

        return ""


    return title


# =========================================================
# BAŞLIK BUL
# =========================================================

def find_campaign_title(soup):

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
# GERÇEK İÇERİK BAŞLANGICI
# =========================================================

def find_content_start(
    strings,
    campaign_title
):

    normalized_title = (
        campaign_title
        .casefold()
        .strip()
    )


    indexes = []


    for index, value in enumerate(
        strings
    ):

        if (
            value.casefold().strip()
            == normalized_title
        ):

            indexes.append(
                index
            )


    if not indexes:

        return 0


    # -----------------------------------------------------
    # KUVEYT TÜRK ANA SİTE
    # -----------------------------------------------------

    for index in indexes:

        lookahead = strings[
            index + 1:
            index + 20
        ]


        joined = " ".join(
            lookahead
        ).casefold()


        if (
            "kampanya tarihleri"
            in joined
        ):

            return index


    # -----------------------------------------------------
    # SAĞLAM KART SAYFALARINDA BAŞLIKTAN SONRA
    # DOĞRUDAN KAMPANYA KOŞULLARI GELEBİLİR.
    # -----------------------------------------------------

    for index in indexes:

        lookahead = strings[
            index + 1:
            index + 6
        ]


        if not lookahead:

            continue


        joined = " ".join(
            lookahead
        )


        if len(
            joined
        ) >= 100:

            return index


    return indexes[
        -1
    ]


# =========================================================
# HAM METİN
# =========================================================

def extract_campaign_text(
    soup,
    campaign_title
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


    start_index = find_content_start(
        strings,
        campaign_title
    )


    campaign_strings = strings[
        start_index:
    ]


    stop_titles = {
        "Faydalı Linkler",
        "Duyurular",
        "İlginizi Çekebilir",
        "Bize Yazın",
        "Footer"
    }


    cleaned = []


    for value in campaign_strings:

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
# TEK URL'DEN SAYFAYI ÇEK
# =========================================================

def fetch_page(
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


    return response


# =========================================================
# TEK KAMPANYAYI ÇEK
# =========================================================

def scrape_campaign(
    session,
    url
):

    original_url = url

    source_url = url


    # -----------------------------------------------------
    # İLK ÖNCE ANA KUVEYT TÜRK URL'SİNİ DENE
    # -----------------------------------------------------

    response = fetch_page(
        session,
        source_url
    )


    # -----------------------------------------------------
    # 404 / HATALI İSE RESMİ FALLBACK VAR MI?
    # -----------------------------------------------------

    if response.status_code != 200:

        fallback_url = FALLBACK_URLS.get(
            original_url
        )


        if fallback_url:

            print(
                "Ana URL çalışmadı."
            )

            print(
                "Resmi fallback deneniyor:"
            )

            print(
                fallback_url
            )


            source_url = fallback_url


            response = fetch_page(
                session,
                source_url
            )


    # -----------------------------------------------------
    # FALLBACK DA ÇALIŞMADI
    # -----------------------------------------------------

    if response.status_code != 200:

        return None


    # -----------------------------------------------------
    # PARSE
    # -----------------------------------------------------

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )


    title = find_campaign_title(
        soup
    )


    if not title:

        print(
            "UYARI: Kampanya başlığı bulunamadı."
        )

        return None


    raw_text = extract_campaign_text(
        soup,
        title
    )


    if not raw_text:

        print(
            "UYARI: Kampanya metni bulunamadı."
        )

        return None


    return {

        "banka": (
            "Kuveyt Türk Katılım Bankası"
        ),

        "kayit_turu": "kampanya",

        "urun_adi": title,

        "kaynak_url": source_url,

        "ham_metin": raw_text
    }


# =========================================================
# DUPLICATE
# =========================================================

def remove_duplicates(
    campaigns
):

    unique_campaigns = []

    duplicate_campaigns = []

    seen = set()


    for campaign in campaigns:

        key = (
            campaign.get(
                "urun_adi",
                ""
            ).strip(),

            campaign.get(
                "ham_metin",
                ""
            ).strip()
        )


        if key in seen:

            duplicate_campaigns.append(
                campaign
            )

            continue


        seen.add(
            key
        )


        unique_campaigns.append(
            campaign
        )


    return (
        unique_campaigns,
        duplicate_campaigns
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 75
    )

    print(
        "KUVEYT TÜRK KAMPANYA SCRAPER"
    )

    print(
        "=" * 75
    )


    # =====================================================
    # 1. TÜM DETAY LİNKLERİNİ BUL
    # =====================================================

    (
        campaign_links,
        load_more_clicks
    ) = get_all_campaign_links()


    print()

    print(
        "Daha Fazla Yükle tıklama:",
        load_more_clicks
    )


    print(
        "Bulunan kampanya detay linki:",
        len(
            campaign_links
        )
    )


    print()


    for index, url in enumerate(
        campaign_links,
        start=1
    ):

        print(
            f"{index}. {url}"
        )


    # =====================================================
    # 2. DETAYLARI ÇEK
    # =====================================================

    session = requests.Session()


    campaigns = []

    failed_urls = []

    fallback_used = []


    for index, url in enumerate(
        campaign_links,
        start=1
    ):

        print()

        print(
            "-" * 75
        )


        print(
            f"[{index}/{len(campaign_links)}]"
        )


        print(
            "Çekiliyor:",
            url
        )


        try:

            campaign = scrape_campaign(
                session,
                url
            )


            if campaign:

                campaigns.append(
                    campaign
                )


                if (
                    campaign[
                        "kaynak_url"
                    ]
                    != url
                ):

                    fallback_used.append(
                        {
                            "original": url,
                            "fallback": (
                                campaign[
                                    "kaynak_url"
                                ]
                            )
                        }
                    )


                print(
                    "Kampanya:",
                    campaign[
                        "urun_adi"
                    ]
                )


                print(
                    "Ham metin uzunluğu:",
                    len(
                        campaign[
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
            0.25
        )


    # =====================================================
    # 3. DUPLICATE
    # =====================================================

    (
        campaigns,
        duplicate_campaigns
    ) = remove_duplicates(
        campaigns
    )


    # =====================================================
    # 4. JSON
    # =====================================================

    output = {

        "banka": (
            "Kuveyt Türk Katılım Bankası"
        ),

        "kayit_turu": "kampanya",

        "kampanya_sayisi": len(
            campaigns
        ),

        "kampanyalar": campaigns
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
        "=" * 75
    )

    print(
        "KUVEYT TÜRK KAMPANYA SCRAPER SONUCU"
    )

    print(
        "=" * 75
    )


    print(
        "Load more tıklama:",
        load_more_clicks
    )


    print(
        "Bulunan detay URL:",
        len(
            campaign_links
        )
    )


    print(
        "Çekilen benzersiz kampanya:",
        len(
            campaigns
        )
    )


    print(
        "Fallback kullanılan:",
        len(
            fallback_used
        )
    )


    print(
        "Duplicate:",
        len(
            duplicate_campaigns
        )
    )


    print(
        "Başarısız URL:",
        len(
            failed_urls
        )
    )


    if fallback_used:

        print()

        print(
            "RESMİ FALLBACK KULLANILANLAR:"
        )


        for item in fallback_used:

            print()

            print(
                "Eski URL:"
            )

            print(
                item[
                    "original"
                ]
            )


            print(
                "Çalışan URL:"
            )

            print(
                item[
                    "fallback"
                ]
            )


    if duplicate_campaigns:

        print()

        print(
            "DUPLICATE KAMPANYALAR:"
        )


        for campaign in duplicate_campaigns:

            print(
                "-",
                campaign.get(
                    "urun_adi",
                    ""
                )
            )


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


    print()

    print(
        "JSON:",
        OUTPUT_FILE
    )


    print(
        "=" * 75
    )


if __name__ == "__main__":
    main()