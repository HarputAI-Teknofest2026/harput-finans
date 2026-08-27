import json
import os
import re
import time
import unicodedata

from urllib.parse import (
    urljoin,
    unquote,
    urlsplit,
    urlunsplit
)

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.emlakkatilim.com.tr"

CAMPAIGNS_URL = (
    "https://www.emlakkatilim.com.tr"
    "/tr/bireysel/kampanyalar"
)

OUTPUT_FILE = (
    "data/raw/"
    "emlak_katilim_kampanyalar.json"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}


# ---------------------------------------------------------
# TÜRKÇE SLUG OLUŞTUR
# ---------------------------------------------------------

def slugify_turkish(text):
    replacements = {
        "ç": "c",
        "Ç": "c",
        "ğ": "g",
        "Ğ": "g",
        "ı": "i",
        "İ": "i",
        "ö": "o",
        "Ö": "o",
        "ş": "s",
        "Ş": "s",
        "ü": "u",
        "Ü": "u"
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new
        )

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(
            character
        )
    )

    text = text.lower()

    text = text.replace(
        "’",
        ""
    )

    text = text.replace(
        "'",
        ""
    )

    text = re.sub(
        r"[^a-z0-9]+",
        "-",
        text
    )

    text = text.strip(
        "-"
    )

    return text


# ---------------------------------------------------------
# BOZUK KAMPANYA URL'SİNİ NORMALLEŞTİR
# ---------------------------------------------------------

def normalize_campaign_url(url):
    parts = urlsplit(
        url
    )

    path_parts = parts.path.split(
        "/"
    )

    if not path_parts:
        return url

    last_part = path_parts[-1]

    decoded_last_part = unquote(
        last_part
    ).strip()

    # Bazı kampanya linkleri slug yerine
    # doğrudan kampanya başlığı olarak geliyor.
    #
    # Örnek:
    #
    # Paraf ile Hepsiburada’da Peşin Fiyatına...
    #
    # Bunu:
    #
    # paraf-ile-hepsiburadada-pesin-fiyatina...
    #
    # biçimine dönüştürüyoruz.

    if " " in decoded_last_part:

        fixed_slug = slugify_turkish(
            decoded_last_part
        )

        path_parts[-1] = fixed_slug

        fixed_path = "/".join(
            path_parts
        )

        fixed_url = urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                fixed_path,
                parts.query,
                parts.fragment
            )
        )

        print()
        print(
            "URL düzeltildi:"
        )

        print(
            "Eski:",
            url
        )

        print(
            "Yeni:",
            fixed_url
        )

        print()

        return fixed_url

    return url


# ---------------------------------------------------------
# KAMPANYA LİNKLERİNİ BUL
# ---------------------------------------------------------

def get_campaign_links(session):
    response = session.get(
        CAMPAIGNS_URL,
        headers=HEADERS,
        timeout=30
    )

    print(
        "Kampanyalar ana sayfası:",
        response.status_code
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    campaign_links = []

    for a in soup.find_all(
        "a",
        href=True
    ):

        href = a.get(
            "href",
            ""
        ).strip()

        if (
            "/tr/bireysel/kampanyalar/kampanya/"
            not in href
        ):
            continue

        full_url = urljoin(
            BASE_URL,
            href
        )

        full_url = normalize_campaign_url(
            full_url
        )

        full_url = requests.utils.requote_uri(
            full_url
        )

        if full_url not in campaign_links:

            campaign_links.append(
                full_url
            )

    return campaign_links


# ---------------------------------------------------------
# BAŞLIK TEMİZLEME
# ---------------------------------------------------------

def clean_campaign_title(title):
    if not title:
        return None

    title = " ".join(
        title.split()
    ).strip()

    invalid_titles = {
        "Türkiye Emlak Katılım Bankası",
        "Emlak Katılım",
        "Kampanyalar",
        "Kampanya",
        "Bireysel",
        "Ana Sayfa",
        "Öne Çıkan Aramalar",
        "Yükleniyor..."
    }

    if title in invalid_titles:
        return None

    if len(title) < 5:
        return None

    suffixes = [
        " | Türkiye Emlak Katılım Bankası",
        " | Emlak Katılım",
        " - Türkiye Emlak Katılım Bankası",
        " - Emlak Katılım"
    ]

    for suffix in suffixes:

        if title.endswith(
            suffix
        ):

            title = title[
                :-len(suffix)
            ].strip()

    if title in invalid_titles:
        return None

    if not title:
        return None

    return title


# ---------------------------------------------------------
# KAMPANYA BAŞLIĞI
# ---------------------------------------------------------

def find_campaign_title(
    soup,
    url
):

    # -----------------------------------------------------
    # 1. OPEN GRAPH TITLE
    # -----------------------------------------------------

    meta_og = soup.find(
        "meta",
        attrs={
            "property": "og:title"
        }
    )

    if meta_og:

        title = clean_campaign_title(
            meta_og.get(
                "content",
                ""
            )
        )

        if title:
            return title


    # -----------------------------------------------------
    # 2. TWITTER TITLE
    # -----------------------------------------------------

    meta_twitter = soup.find(
        "meta",
        attrs={
            "name": "twitter:title"
        }
    )

    if meta_twitter:

        title = clean_campaign_title(
            meta_twitter.get(
                "content",
                ""
            )
        )

        if title:
            return title


    # -----------------------------------------------------
    # 3. H1 / H2 / H3
    # -----------------------------------------------------

    for tag_name in [
        "h1",
        "h2",
        "h3"
    ]:

        tags = soup.find_all(
            tag_name
        )

        for tag in tags:

            candidate = tag.get_text(
                " ",
                strip=True
            )

            title = clean_campaign_title(
                candidate
            )

            if title:
                return title


    # -----------------------------------------------------
    # 4. HTML TITLE
    # -----------------------------------------------------

    if soup.title:

        candidate = soup.title.get_text(
            " ",
            strip=True
        )

        title = clean_campaign_title(
            candidate
        )

        if title:
            return title


    # -----------------------------------------------------
    # 5. SON ÇARE URL SLUG
    # -----------------------------------------------------

    slug = (
        url
        .rstrip("/")
        .split("/")[-1]
    )

    slug = unquote(
        slug
    )

    slug = slug.replace(
        "-",
        " "
    )

    slug = " ".join(
        slug.split()
    ).strip()

    return slug


# ---------------------------------------------------------
# HAM KAMPANYA METNİ
# ---------------------------------------------------------

def extract_campaign_text(
    soup,
    campaign_title
):
    strings = []

    for text in soup.stripped_strings:

        value = text.strip()

        if not value:
            continue

        normalized_value = (
            value
            .lower()
        )

        if value in [
            "×",
            "Yükleniyor..."
        ]:
            continue

        if (
            "your browser does not support"
            in normalized_value
        ):
            continue

        if (
            "tarayıcınız audio elementini desteklemiyor"
            in normalized_value
        ):
            continue

        strings.append(
            value
        )

    if not strings:
        return ""


    # -----------------------------------------------------
    # BAŞLANGIÇ NOKTASINI BUL
    # -----------------------------------------------------

    start_index = None

    normalized_title = (
        campaign_title
        .strip()
        .casefold()
    )


    # -----------------------------------------------------
    # 1. TAM BAŞLIK EŞLEŞMESİ
    # -----------------------------------------------------

    for index, value in enumerate(
        strings
    ):

        normalized_value = (
            value
            .strip()
            .casefold()
        )

        if (
            normalized_value
            == normalized_title
        ):

            # Başlık birden fazla yerde geçebilir.
            # Son eşleşmeyi tercih ediyoruz.
            start_index = index


    # -----------------------------------------------------
    # 2. ESNEK BAŞLIK EŞLEŞMESİ
    # -----------------------------------------------------

    if start_index is None:

        for index, value in enumerate(
            strings
        ):

            normalized_value = (
                value
                .strip()
                .casefold()
            )

            if (
                len(normalized_value) > 10
                and (
                    normalized_title
                    in normalized_value
                    or normalized_value
                    in normalized_title
                )
            ):

                start_index = index


    # -----------------------------------------------------
    # BAŞLIK BULUNAMAZSA
    # -----------------------------------------------------

    if start_index is None:

        print(
            "UYARI: Kampanya başlığı içerikte bulunamadı."
        )

        return ""


    # -----------------------------------------------------
    # İÇERİĞİN SONUNU BUL
    # -----------------------------------------------------

    end_index = len(
        strings
    )

    stop_words = [
        "İletişim",
        "Bize Ulaşın"
    ]

    for index in range(
        start_index + 1,
        len(strings)
    ):

        if strings[index] in stop_words:

            end_index = index

            break


    campaign_strings = strings[
        start_index:end_index
    ]


    # -----------------------------------------------------
    # SON TEMİZLİK
    # -----------------------------------------------------

    clean_strings = []

    unwanted_values = {
        "ZIP",
        "X",
        "Ana sayfa",
        "İNTERNET ŞUBE",
        "BİREYSEL",
        "KURUMSAL",
        "MÜŞTERİ OL",
        "Öne Çıkan Aramalar"
    }

    for value in campaign_strings:

        if value in unwanted_values:
            continue

        clean_strings.append(
            value
        )


    return "\n".join(
        clean_strings
    )


# ---------------------------------------------------------
# TEK KAMPANYAYI ÇEK
# ---------------------------------------------------------

def scrape_campaign(
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


    campaign_title = find_campaign_title(
        soup,
        url
    )


    campaign_text = extract_campaign_text(
        soup,
        campaign_title
    )


    if not campaign_text:

        print(
            "UYARI: Kampanya metni bulunamadı."
        )

        return None


    return {
        "banka": (
            "Türkiye Emlak Katılım Bankası"
        ),

        "kayit_turu": "kampanya",

        "kampanya_adi": campaign_title,

        "kaynak_url": url,

        "ham_metin": campaign_text
    }


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    session = requests.Session()


    # -----------------------------------------------------
    # KAMPANYA LİNKLERİ
    # -----------------------------------------------------

    campaign_links = get_campaign_links(
        session
    )


    print()

    print(
        f"Toplam kampanya linki: "
        f"{len(campaign_links)}"
    )

    print()


    campaigns = []

    failed_campaigns = []


    # -----------------------------------------------------
    # TÜM KAMPANYALARI ÇEK
    # -----------------------------------------------------

    for index, url in enumerate(
        campaign_links,
        start=1
    ):

        print(
            "-----------------------------------------"
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

                print(
                    "Kampanya:",
                    campaign[
                        "kampanya_adi"
                    ]
                )


                # -------------------------------------------------
                # HEPSİBURADA KONTROLÜ
                # -------------------------------------------------

                if (
                    "hepsiburada"
                    in url.lower()
                ):

                    print()

                    print(
                        "HEPSİBURADA HAM METİN ÖNİZLEME:"
                    )

                    print(
                        campaign[
                            "ham_metin"
                        ][:1000]
                    )

                    print()


            else:

                failed_campaigns.append(
                    url
                )

                print(
                    "Kampanya alınamadı."
                )


        except Exception as error:

            failed_campaigns.append(
                url
            )

            print(
                "HATA:",
                error
            )


        # Siteye hızlı istek göndermeyelim.
        time.sleep(
            0.3
        )


    # -----------------------------------------------------
    # JSON ÇIKTISI
    # -----------------------------------------------------

    output_data = {
        "banka": (
            "Türkiye Emlak Katılım Bankası"
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
            output_data,
            file,
            ensure_ascii=False,
            indent=4
        )


    # -----------------------------------------------------
    # SONUÇ
    # -----------------------------------------------------

    print()

    print(
        "========================================="
    )

    print(
        f"Toplam bulunan link: "
        f"{len(campaign_links)}"
    )

    print(
        f"Başarıyla çekilen kampanya: "
        f"{len(campaigns)}"
    )

    print(
        f"Başarısız kampanya: "
        f"{len(failed_campaigns)}"
    )


    if failed_campaigns:

        print()

        print(
            "Başarısız URL'ler:"
        )

        for url in failed_campaigns:

            print(
                "-",
                url
            )


    print()

    print(
        f"JSON kaydedildi: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()