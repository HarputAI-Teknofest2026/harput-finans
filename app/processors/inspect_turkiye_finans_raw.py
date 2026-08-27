import json
import re


INPUT_FILE = (
    "data/raw/"
    "turkiye_finans_finansman_urunleri.json"
)


SELECTED_PRODUCTS = [
    "İhtiyaç Finansmanı (İhtiyaç Kredisi)*",

    "Taşıt Finansmanı (Taşıt Kredisi)*",

    "Konut Finansmanı (Konut Kredisi)*",

    "eXtra Limit",

    "Dijital İhtiyaç Finansmanı (Dijital İhtiyaç Kredisi)*",

    "Trendyol Alışveriş Finansmanı",

    "Ticari Hat / Ticari Plaka Finansmanı (Ticari Hat / Ticari Plaka Kredisi)*",

    "Hızlı Finansman - İhtiyaç Finansmanı",

    "Hızlı Finansman - Eğitim Finansmanı",

    "Hızlı Finansman - Taşıt Finansmanı",

    "Hızlı Finansman - Motosiklet Finansmanı"
]


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


def normalize_text(value):

    return re.sub(
        r"\s+",
        " ",
        str(value or "")
    ).strip()


def main():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(
            file
        )


    products = data.get(
        "urunler",
        []
    )


    by_name = {
        tr_lower(
            product.get(
                "urun_adi",
                ""
            )
        ): product

        for product
        in products
    }


    print()

    print(
        "=" * 100
    )

    print(
        "TÜRKİYE FİNANS RAW TEMSİLİ ÜRÜN İNCELEMESİ"
    )

    print(
        "=" * 100
    )


    print(
        "Toplam RAW ürün:",
        len(
            products
        )
    )


    print(
        "İncelenecek ürün:",
        len(
            SELECTED_PRODUCTS
        )
    )


    found_count = 0


    for index, product_name in enumerate(
        SELECTED_PRODUCTS,
        start=1
    ):

        product = by_name.get(
            tr_lower(
                product_name
            )
        )


        print()

        print()

        print(
            "#" * 100
        )

        print(
            f"[{index}/{len(SELECTED_PRODUCTS)}]"
        )

        print(
            product_name
        )

        print(
            "#" * 100
        )


        if not product:

            print(
                "BULUNAMADI"
            )

            continue


        found_count += 1


        print()

        print(
            "BANKA:"
        )

        print(
            product.get(
                "banka",
                ""
            )
        )


        print()

        print(
            "KAYIT TÜRÜ:"
        )

        print(
            product.get(
                "kayit_turu",
                ""
            )
        )


        print()

        print(
            "ÜRÜN ADI:"
        )

        print(
            product.get(
                "urun_adi",
                ""
            )
        )


        print()

        print(
            "KAYNAK URL:"
        )

        print(
            product.get(
                "kaynak_url",
                ""
            )
        )


        raw_text = str(
            product.get(
                "ham_metin",
                ""
            )
        ).strip()


        print()

        print(
            "HAM METİN UZUNLUĞU:"
        )

        print(
            len(
                raw_text
            )
        )


        print()

        print(
            "-" * 100
        )

        print(
            "HAM METİN"
        )

        print(
            "-" * 100
        )

        print()

        print(
            raw_text
        )

        print()

        print(
            "-" * 100
        )

        print(
            "HAM METİN SONU"
        )

        print(
            "-" * 100
        )


    print()

    print()

    print(
        "=" * 100
    )

    print(
        "İNCELEME ÖZETİ"
    )

    print(
        "=" * 100
    )


    print(
        "İstenen ürün:",
        len(
            SELECTED_PRODUCTS
        )
    )


    print(
        "Bulunan ürün:",
        found_count
    )


    print(
        "Bulunamayan ürün:",
        (
            len(
                SELECTED_PRODUCTS
            )
            - found_count
        )
    )


    print(
        "=" * 100
    )


if __name__ == "__main__":

    main()