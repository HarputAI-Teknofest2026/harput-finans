import json
import os
import re


INPUT_FILE = "data/raw/emlak_katilim_finansman_urunleri.json"

OUTPUT_FILE = "data/processed/emlak_katilim_finansman_urunleri.json"


def extract_kar_payi_orani(text):
    patterns = [
        r"(?i)k[âa]r\s*oran[ıi]\s*[:\-]?\s*%?\s*(\d+[.,]\d+)",
        r"(?i)k[âa]r\s*pay[ıi]\s*oran[ıi]\s*[:\-]?\s*%?\s*(\d+[.,]\d+)",
        r"(?i)(\d+[.,]\d+)\s*%\s*k[âa]r",
        r"(?i)%\s*(\d+[.,]\d+)\s*k[âa]r",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            value = match.group(1)
            return f"%{value}"

    return "Belirtilmemiş"


def extract_vade(text):
    patterns = [
        r"(?i)azami\s+vade\s*[:\-]?\s*(\d+)\s*ay",
        r"(?i)finansman\s+vadesi\s+azami\s+(\d+)\s*ay",
        r"(?i)(\d+)\s*aya\s+kadar\s+vade",
        r"(?i)(\d+)\s*ay[a-zçğıöşü]*\s+kadar",
        r"(?i)azami\s+(\d+)\s*ay",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return f"{match.group(1)} ay"

    return "Belirtilmemiş"


def extract_masraf_durumu(text):
    # Tahsis ücreti tablo formatı
    pattern = (
        r"(?i)Finansman\s+Tahsis\s+Ücreti"
        r".{0,120}?"
        r"([\d.,]+)\s*₺"
    )

    match = re.search(
        pattern,
        text,
        re.DOTALL
    )

    if match:
        return (
            "Finansman tahsis ücreti: "
            f"{match.group(1)} TL"
        )

    # Masraf yok ifadeleri
    no_fee_patterns = [
        r"(?i)masraf\s+al[ıi]nm[ıi]yor",
        r"(?i)masrafs[ıi]z",
        r"(?i)ücret\s+al[ıi]nmamaktad[ıi]r",
        r"(?i)ücret\s+uygulanmayacakt[ıi]r",
    ]

    for pattern in no_fee_patterns:
        if re.search(pattern, text):
            return "Masraf alınmıyor"

    return "Belirtilmemiş"


def extract_kampanya_avantaji(text):
    patterns = [
        r"(?i)%\s*(\d+(?:[.,]\d+)?)\s*indirim",
        r"(?i)(\d+(?:[.,]\d+)?)\s*%\s*indirim",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return f"%{match.group(1)} indirim"

    return "Belirtilmemiş"


def extract_kampanya_suresi(text):
    patterns = [
        r"(?i)(\d{1,2}[./]\d{1,2}[./]\d{4})\s+tarihine\s+kadar",
        r"(?i)(\d{1,2}[./]\d{1,2}[./]\d{4})\s+kadar",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return f"{match.group(1)} tarihine kadar"

    return "Belirtilmemiş"


def normalize_product(raw_product):
    text = raw_product.get(
        "ham_metin",
        ""
    )

    return {
        "banka": raw_product.get(
            "banka",
            "Belirtilmemiş"
        ),

        "urun_turu": raw_product.get(
            "urun_adi",
            "Belirtilmemiş"
        ),

        "kar_payi_orani": extract_kar_payi_orani(
            text
        ),

        "vade": extract_vade(
            text
        ),

        "kampanya_avantaji": extract_kampanya_avantaji(
            text
        ),

        "masraf_durumu": extract_masraf_durumu(
            text
        ),

        "kampanya_suresi": extract_kampanya_suresi(
            text
        ),

        "kaynak_url": raw_product.get(
            "kaynak_url",
            ""
        ),

        "ham_metin": text
    }


def main():
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        raw_data = json.load(file)

    normalized_products = []

    for raw_product in raw_data["urunler"]:
        normalized = normalize_product(
            raw_product
        )

        normalized_products.append(
            normalized
        )

    output_data = {
        "banka": raw_data.get(
            "banka",
            "Türkiye Emlak Katılım Bankası"
        ),

        "urun_sayisi": len(
            normalized_products
        ),

        "urunler": normalized_products
    }

    os.makedirs(
        "data/processed",
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

    print(
        f"Toplam ürün: {len(normalized_products)}"
    )

    print()

    for product in normalized_products:
        print(
            f"{product['urun_turu']} | "
            f"Kâr Payı: {product['kar_payi_orani']} | "
            f"Vade: {product['vade']} | "
            f"Masraf: {product['masraf_durumu']}"
        )

    print()

    print(
        f"JSON kaydedildi: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()