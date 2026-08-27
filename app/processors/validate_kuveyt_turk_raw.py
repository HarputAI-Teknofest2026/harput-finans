import json
import statistics


INPUT_FILE = (
    "data/raw/"
    "kuveyt_turk_finansman_urunleri.json"
)


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


    print()
    print("=" * 70)
    print("KUVEYT TÜRK RAW DATA KONTROLÜ")
    print("=" * 70)

    print()
    print(
        "Toplam ürün:",
        len(products)
    )


    text_lengths = []

    empty_records = []

    short_records = []

    title_not_in_text = []

    urls = set()

    duplicate_urls = []


    for index, product in enumerate(
        products,
        start=1
    ):

        title = product.get(
            "urun_adi",
            ""
        ).strip()

        url = product.get(
            "kaynak_url",
            ""
        ).strip()

        text = product.get(
            "ham_metin",
            ""
        ).strip()


        text_length = len(text)

        text_lengths.append(
            text_length
        )


        # ---------------------------------------------
        # BOŞ ALAN KONTROLÜ
        # ---------------------------------------------

        if (
            not title
            or not url
            or not text
        ):
            empty_records.append(
                title or f"Kayıt {index}"
            )


        # ---------------------------------------------
        # AŞIRI KISA METİN KONTROLÜ
        # ---------------------------------------------

        if text_length < 300:

            short_records.append(
                (
                    title,
                    text_length
                )
            )


        # ---------------------------------------------
        # BAŞLIK METİN İÇİNDE Mİ?
        # ---------------------------------------------

        if (
            title
            and title.casefold()
            not in text.casefold()
        ):

            title_not_in_text.append(
                title
            )


        # ---------------------------------------------
        # DUPLICATE URL
        # ---------------------------------------------

        if url in urls:

            duplicate_urls.append(
                url
            )

        else:

            urls.add(
                url
            )


        # ---------------------------------------------
        # TEK TEK RAPOR
        # ---------------------------------------------

        print()
        print("-" * 70)

        print(
            f"[{index}/{len(products)}]"
        )

        print(
            "Ürün:",
            title
        )

        print(
            "Metin uzunluğu:",
            text_length
        )

        print(
            "Başlık metinde:",
            (
                "EVET"
                if title.casefold()
                in text.casefold()
                else "HAYIR"
            )
        )


    # =================================================
    # GENEL İSTATİSTİK
    # =================================================

    print()
    print("=" * 70)
    print("GENEL SONUÇ")
    print("=" * 70)


    if text_lengths:

        print(
            "En kısa metin:",
            min(text_lengths)
        )

        print(
            "En uzun metin:",
            max(text_lengths)
        )

        print(
            "Ortalama metin uzunluğu:",
            round(
                statistics.mean(
                    text_lengths
                ),
                2
            )
        )


    print()

    print(
        "Boş kayıt:",
        len(empty_records)
    )

    print(
        "300 karakterden kısa kayıt:",
        len(short_records)
    )

    print(
        "Başlığı ham metinde bulunmayan:",
        len(title_not_in_text)
    )

    print(
        "Duplicate URL:",
        len(duplicate_urls)
    )


    # =================================================
    # PROBLEMLİLER
    # =================================================

    if empty_records:

        print()
        print(
            "BOŞ KAYITLAR:"
        )

        for item in empty_records:

            print(
                "-",
                item
            )


    if short_records:

        print()
        print(
            "KISA METİNLER:"
        )

        for title, length in short_records:

            print(
                f"- {title}: {length}"
            )


    if title_not_in_text:

        print()
        print(
            "BAŞLIK METİNDE YOK:"
        )

        for title in title_not_in_text:

            print(
                "-",
                title
            )


    if duplicate_urls:

        print()
        print(
            "DUPLICATE URL:"
        )

        for url in duplicate_urls:

            print(
                "-",
                url
            )


    print()
    print("=" * 70)

    if (
        len(products) == 30
        and not empty_records
        and not short_records
        and not title_not_in_text
        and not duplicate_urls
    ):

        print(
            "SONUÇ: RAW DATA SAĞLIKLI ✅"
        )

    else:

        print(
            "SONUÇ: KONTROL GEREKEN KAYITLAR VAR ⚠️"
        )

    print("=" * 70)


if __name__ == "__main__":
    main()