import json
import os
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.emlakkatilim.com.tr"

FINANSMANLAR_URL = (
    "https://www.emlakkatilim.com.tr/tr/bireysel/finansmanlar"
)

OUTPUT_FILE = (
    "data/raw/emlak_katilim_finansman_urunleri.json"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}


def get_financing_links():
    response = requests.get(
        FINANSMANLAR_URL,
        headers=HEADERS,
        timeout=30
    )

    print("Finansman ana sayfası:", response.status_code)

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "lxml"
    )

    product_links = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()

        full_url = urljoin(
            BASE_URL,
            href
        )

        parsed = urlparse(full_url)

        path = parsed.path.rstrip("/")

        # Sadece Emlak Katılım
        if parsed.netloc not in {
            "www.emlakkatilim.com.tr",
            "emlakkatilim.com.tr"
        }:
            continue

        # Sadece bireysel finansman detay sayfaları
        if not path.startswith(
            "/tr/bireysel/finansmanlar/"
        ):
            continue

        clean_url = (
            f"{parsed.scheme}://"
            f"{parsed.netloc}"
            f"{path}"
        )

        product_links.add(clean_url)

    return sorted(product_links)


def clean_lines(lines):
    unwanted_lines = {
        "×",
        "Your browser does not support the audio element."
    }

    cleaned_lines = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line in unwanted_lines:
            continue

        cleaned_lines.append(line)

    return cleaned_lines


def find_product_title(soup, url):

    # 1. Öncelikle <title> etiketini kullan
    if soup.title:

        title_text = soup.title.get_text(
            " ",
            strip=True
        )

        if "|" in title_text:
            title_text = title_text.split("|")[0].strip()

        if title_text:
            return title_text

    # 2. Sonra h1 dene
    h1 = soup.find("h1")

    if h1:
        title = h1.get_text(
            " ",
            strip=True
        )

        if title and title != "Öne Çıkan Aramalar":
            return title

    # 3. Son çare olarak URL slug
    slug = url.rstrip("/").split("/")[-1]

    return (
        slug
        .replace("-", " ")
        .title()
    )


def extract_product_text(soup, product_name):
    all_lines = [
        text.strip()
        for text in soup.stripped_strings
        if text.strip()
    ]

    all_lines = clean_lines(
        all_lines
    )

    # Aynı ürün başlığı menüde veya içerikte birden fazla kez olabilir.
    indexes = [
        index
        for index, line in enumerate(all_lines)
        if line == product_name
    ]

    if not indexes:
        return None

    # Son geçen başlığı gerçek içerik başlangıcı kabul ediyoruz
    start_index = indexes[-1]

    end_index = len(all_lines)

    # Footer başlangıcı
    for i in range(
        start_index + 1,
        len(all_lines)
    ):
        if all_lines[i] == "İletişim":
            end_index = i
            break

    product_lines = all_lines[
        start_index:end_index
    ]

    product_lines = clean_lines(
        product_lines
    )

    return "\n".join(product_lines)


def scrape_product(url):
    print(f"Çekiliyor: {url}")

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    print(
        "HTTP STATUS:",
        response.status_code
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "lxml"
    )

    product_name = find_product_title(
        soup,
        url
    )

    if not product_name:
        print(
            "UYARI: Ürün başlığı bulunamadı."
        )
        return None

    product_text = extract_product_text(
        soup,
        product_name
    )

    if not product_text:
        print(
            "UYARI: Ürün metni bulunamadı."
        )
        return None

    return {
        "banka": "Türkiye Emlak Katılım Bankası",
        "kayit_turu": "urun",
        "kategori": "bireysel_finansman",
        "urun_adi": product_name,
        "kaynak_url": url,
        "ham_metin": product_text
    }


def main():
    links = get_financing_links()

    print(
        f"\nToplam ürün linki: {len(links)}"
    )

    products = []

    for index, url in enumerate(
        links,
        start=1
    ):
        print(
            f"\n[{index}/{len(links)}]"
        )

        try:
            product = scrape_product(
                url
            )

            if product:
                products.append(
                    product
                )

                print(
                    "Ürün:",
                    product["urun_adi"]
                )

        except Exception as error:
            print(
                "HATA:",
                error
            )

        # Siteye arka arkaya istek göndermeyelim
        time.sleep(1)

    data = {
        "banka": "Türkiye Emlak Katılım Bankası",
        "kategori": "bireysel_finansman",
        "urun_sayisi": len(products),
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
            data,
            file,
            ensure_ascii=False,
            indent=4
        )

    print("\n-----------------------------")
    print(
        f"Toplam çekilen ürün: {len(products)}"
    )
    print(
        f"JSON kaydedildi: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()