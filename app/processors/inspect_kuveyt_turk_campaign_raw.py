import json


INPUT_FILE = (
    "data/raw/"
    "kuveyt_turk_kampanyalar.json"
)


SELECTED_CAMPAIGNS = [

    # TL hediye
    "Yakınlarını Kuveyt Türk'e Davet Et Toplamda 5.000 TL'ye Varan Hediye Kazan!",

    # Mil
    "Yeni Kuveyt Türk Mobil Müşterilerine 10.000 Mil'e Varan Fırsat!",

    # Taksit
    "Yeni Sağlam Kart Troy'lulara Özel Vade Farksız 5 Aya Varan Taksit İmkanı!",

    # Kâr oranı
    "Yeni Müşterilere Özel İhtiyaç Kart'ta %1,99 Oran Fırsatı!",

    # İndirim
    "Bella Maison'da %25 İndirim Fırsatı!",

    # Karma indirim
    "Kuveyt Türk Kredi Kartlarına Toprak Turizm Yurt Dışı Turlarında %10, Umre Turlarında %7 İndirim",

    # Finansman kampanyası
    "Taksitlio’da Yeni Müşterilere Özel Kuveyt Türk Alışveriş Finansmanı Fırsatı!",

    # Büyük / karma kampanya
    "Evlenecek Olan veya Yeni Evli Çiftlere Kuveyt Türk’ten Müjde Evlilik Paketi!",

    # Fallback
    "Konfor‘da Vade Farksız 9 Aya Varan Taksit Fırsatı!",

    # Finansman + taksit
    "Diyanet Umre Finansmanı ile Vade Farksız 3 Taksit İmkanı!",

    # Hediye
    "Fatura Talimatlarınıza Toplam 500 TL Hediye!",

    # Seyahat
    "Kuveyt Türk ile Yurt Dışı Seyahatlerinde Ayrıcalıklar Sizinle!"
]


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


    campaign_map = {

        campaign.get(
            "urun_adi",
            ""
        ): campaign

        for campaign in campaigns
    }


    print()

    print(
        "=" * 100
    )

    print(
        "KUVEYT TÜRK TEMSİLCİ KAMPANYA RAW METİNLERİ"
    )

    print(
        "=" * 100
    )


    for campaign_name in SELECTED_CAMPAIGNS:

        print()

        print()

        print(
            "#" * 100
        )

        print(
            "# KAMPANYA:",
            campaign_name
        )

        print(
            "#" * 100
        )


        campaign = campaign_map.get(
            campaign_name
        )


        if not campaign:

            print()

            print(
                "KAMPANYA BULUNAMADI"
            )

            continue


        print()

        print(
            "URL:",
            campaign.get(
                "kaynak_url",
                ""
            )
        )


        print()

        print(
            "HAM METİN:"
        )


        print(
            "-" * 100
        )


        print(
            campaign.get(
                "ham_metin",
                ""
            )
        )


        print(
            "-" * 100
        )


    print()

    print(
        "=" * 100
    )

    print(
        "BİTTİ"
    )

    print(
        "=" * 100
    )


if __name__ == "__main__":

    main()