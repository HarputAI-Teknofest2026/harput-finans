import json


INPUT_FILE = (
    "data/raw/"
    "kuveyt_turk_finansman_urunleri.json"
)


SELECTED_PRODUCTS = [
    "Araç Finansmanı",
    "Konut Finansmanı",
    "İlk Evim Konut Finansmanı",
    "Taksitlio Alışveriş Finansmanı",
    "İhtiyaç Kart",
    "Yeşil Konut Finansmanı",
    "Çatı GES Finansmanı"
]


def main():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(file)


    products = data.get(
        "urunler",
        []
    )


    product_map = {
        product.get(
            "urun_adi",
            ""
        ): product

        for product in products
    }


    print()
    print("=" * 90)
    print("KUVEYT TÜRK TEMSİLCİ RAW METİNLER")
    print("=" * 90)


    for product_name in SELECTED_PRODUCTS:

        print()
        print()
        print("#" * 90)
        print("# ÜRÜN:", product_name)
        print("#" * 90)


        product = product_map.get(
            product_name
        )


        if not product:

            print(
                "ÜRÜN BULUNAMADI"
            )

            continue


        print()
        print(
            "URL:",
            product.get(
                "kaynak_url",
                ""
            )
        )

        print()
        print(
            "HAM METİN:"
        )

        print("-" * 90)

        print(
            product.get(
                "ham_metin",
                ""
            )
        )

        print("-" * 90)


    print()
    print("=" * 90)
    print("BİTTİ")
    print("=" * 90)


if __name__ == "__main__":
    main()