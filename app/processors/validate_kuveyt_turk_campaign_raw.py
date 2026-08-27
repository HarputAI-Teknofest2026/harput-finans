import json
import statistics
from collections import Counter


INPUT_FILE = (
    "data/raw/"
    "kuveyt_turk_kampanyalar.json"
)


REQUIRED_FIELDS = [
    "banka",
    "kayit_turu",
    "urun_adi",
    "kaynak_url",
    "ham_metin"
]


def detect_source_category(url):

    if (
        "/musteri-ol-kampanyalari/"
        in url
    ):
        return "Müşteri Ol Kampanyaları"

    if (
        "/kart-kampanyalari/"
        in url
    ):
        return "Kart Kampanyaları"

    if (
        "/finansman-kampanyalari/"
        in url
    ):
        return "Finansman Kampanyaları"

    if (
        "/seyahat-kampanyalari/"
        in url
    ):
        return "Seyahat Kampanyaları"

    if (
        "saglamkart.kuveytturk.com.tr"
        in url
    ):
        return "Kart Kampanyaları / Sağlam Kart"

    return "Diğer"


def main():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        data = json.load(
            file
        )


    campaigns = data.get(
        "kampanyalar",
        []
    )


    print()

    print(
        "=" * 75
    )

    print(
        "KUVEYT TÜRK KAMPANYA RAW DATA KONTROLÜ"
    )

    print(
        "=" * 75
    )


    print()

    print(
        "Toplam kampanya:",
        len(campaigns)
    )


    text_lengths = []

    empty_records = []

    missing_fields = []

    short_records = []

    title_not_in_text = []

    duplicate_urls = []

    duplicate_contents = []

    suspicious_titles = []

    urls_seen = set()

    content_seen = set()

    categories = Counter()


    for index, campaign in enumerate(
        campaigns,
        start=1
    ):

        print()

        print(
            "-" * 75
        )


        title = str(
            campaign.get(
                "urun_adi",
                ""
            )
        ).strip()


        url = str(
            campaign.get(
                "kaynak_url",
                ""
            )
        ).strip()


        text = str(
            campaign.get(
                "ham_metin",
                ""
            )
        ).strip()


        # =================================================
        # ŞEMA
        # =================================================

        missing = [
            field
            for field in REQUIRED_FIELDS
            if field not in campaign
        ]


        if missing:

            missing_fields.append(
                (
                    index,
                    title,
                    missing
                )
            )


        # =================================================
        # BOŞ ALAN
        # =================================================

        if (
            not title
            or not url
            or not text
        ):

            empty_records.append(
                title or f"Kayıt {index}"
            )


        # =================================================
        # METİN UZUNLUĞU
        # =================================================

        text_length = len(
            text
        )


        text_lengths.append(
            text_length
        )


        if text_length < 500:

            short_records.append(
                (
                    title,
                    text_length
                )
            )


        # =================================================
        # BAŞLIK HAM METİNDE Mİ?
        # =================================================

        if (
            title
            and title.casefold()
            not in text.casefold()
        ):

            title_not_in_text.append(
                title
            )


        # =================================================
        # URL DUPLICATE
        # =================================================

        if url in urls_seen:

            duplicate_urls.append(
                url
            )

        else:

            urls_seen.add(
                url
            )


        # =================================================
        # AYNI BAŞLIK + AYNI METİN
        # =================================================

        content_key = (
            title.casefold(),
            text
        )


        if content_key in content_seen:

            duplicate_contents.append(
                title
            )

        else:

            content_seen.add(
                content_key
            )


        # =================================================
        # BAŞLIK KONTROLÜ
        # =================================================

        if title in {
            "Kuveyt Türk",
            "Kampanyalar",
            "Kendim İçin",
            "Ana Sayfa",
            "Sağlam Kart"
        }:

            suspicious_titles.append(
                title
            )


        # =================================================
        # KATEGORİ
        # =================================================

        category = detect_source_category(
            url
        )


        categories[
            category
        ] += 1


        # =================================================
        # TEK KAYIT RAPORU
        # =================================================

        print(
            f"[{index}/{len(campaigns)}]"
        )


        print(
            "Kampanya:",
            title
        )


        print(
            "Kategori:",
            category
        )


        print(
            "Metin uzunluğu:",
            text_length
        )


        print(
            "Başlık metinde:",
            (
                "EVET"
                if (
                    title
                    and title.casefold()
                    in text.casefold()
                )
                else "HAYIR"
            )
        )


        print(
            "Kaynak:",
            url
        )


    # =====================================================
    # GENEL İSTATİSTİK
    # =====================================================

    print()

    print(
        "=" * 75
    )

    print(
        "GENEL SONUÇ"
    )

    print(
        "=" * 75
    )


    if text_lengths:

        print(
            "En kısa metin:",
            min(
                text_lengths
            )
        )


        print(
            "En uzun metin:",
            max(
                text_lengths
            )
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
        "Eksik şema alanı olan:",
        len(
            missing_fields
        )
    )


    print(
        "Boş kayıt:",
        len(
            empty_records
        )
    )


    print(
        "500 karakterden kısa kayıt:",
        len(
            short_records
        )
    )


    print(
        "Başlığı ham metinde bulunmayan:",
        len(
            title_not_in_text
        )
    )


    print(
        "Duplicate URL:",
        len(
            duplicate_urls
        )
    )


    print(
        "Duplicate içerik:",
        len(
            duplicate_contents
        )
    )


    print(
        "Şüpheli başlık:",
        len(
            suspicious_titles
        )
    )


    # =====================================================
    # KATEGORİ DAĞILIMI
    # =====================================================

    print()

    print(
        "=" * 75
    )

    print(
        "KAYNAK KATEGORİ DAĞILIMI"
    )

    print(
        "=" * 75
    )


    for category, count in (
        categories.most_common()
    ):

        print(
            f"{category}: {count}"
        )


    # =====================================================
    # PROBLEMLİLER
    # =====================================================

    if missing_fields:

        print()

        print(
            "EKSİK ŞEMA ALANLARI:"
        )


        for (
            index,
            title,
            fields
        ) in missing_fields:

            print(
                f"- {index}. {title}: "
                f"{fields}"
            )


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


        for (
            title,
            length
        ) in short_records:

            print(
                f"- {title}: "
                f"{length}"
            )


    if title_not_in_text:

        print()

        print(
            "BAŞLIK METİNDE YOK:"
        )


        for title in (
            title_not_in_text
        ):

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


    if duplicate_contents:

        print()

        print(
            "DUPLICATE İÇERİK:"
        )


        for title in (
            duplicate_contents
        ):

            print(
                "-",
                title
            )


    if suspicious_titles:

        print()

        print(
            "ŞÜPHELİ BAŞLIKLAR:"
        )


        for title in (
            suspicious_titles
        ):

            print(
                "-",
                title
            )


    # =====================================================
    # FALLBACK
    # =====================================================

    fallback_records = [
        campaign
        for campaign in campaigns
        if (
            "saglamkart.kuveytturk.com.tr"
            in campaign.get(
                "kaynak_url",
                ""
            )
        )
    ]


    print()

    print(
        "Resmi fallback kaynaklı kayıt:",
        len(
            fallback_records
        )
    )


    for campaign in fallback_records:

        print(
            "-",
            campaign.get(
                "urun_adi",
                ""
            )
        )

        print(
            " ",
            campaign.get(
                "kaynak_url",
                ""
            )
        )


    # =====================================================
    # FINAL
    # =====================================================

    print()

    print(
        "=" * 75
    )


    if (
        len(campaigns) == 74

        and not missing_fields

        and not empty_records

        and not short_records

        and not title_not_in_text

        and not duplicate_urls

        and not duplicate_contents

        and not suspicious_titles

        and len(
            fallback_records
        ) == 1
    ):

        print(
            "SONUÇ: KAMPANYA RAW DATA SAĞLIKLI ✅"
        )


    else:

        print(
            "SONUÇ: KONTROL GEREKEN "
            "KAYITLAR VAR ⚠️"
        )


    print(
        "=" * 75
    )


if __name__ == "__main__":

    main()