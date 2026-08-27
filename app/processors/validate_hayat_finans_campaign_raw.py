import json
import os
from urllib.parse import urlparse


# =========================================================
# AYARLAR
# =========================================================

INPUT_FILE = "data/raw/hayat_finans_kampanyalar.json"

EXPECTED_BANK = "Hayat Finans Katılım Bankası"

EXPECTED_RECORD_TYPE = "kampanya"

EXPECTED_COUNT = 11


EXPECTED_CAMPAIGNS = {
    "Arkadaşını Davet Et, Avantajlı Hesapla Kazanmaya Başla!": {
        "category": "Arkadaşını Getir",
        "start": "2026-08-17",
        "end": "2026-09-17",
        "status": "aktif_dogrulanmis",
        "required_terms": [
            "2.000 TL",
            "10.000 TL",
            "17 Ağustos",
            "17 Eylül 2026",
        ],
    },

    "Avantajlı Hesap Müşterilerine Özel FX Dar Makas Avantajı!": {
        "category": "Yatırım",
        "start": "2026-07-17",
        "end": "2026-09-17",
        "status": "aktif_dogrulanmis",
        "required_terms": [
            "5.000 USD",
            "%0,1",
            "17 Temmuz",
            "17 Eylül 2026",
        ],
    },

    "Biz Kart Arkadaşını Getir & Kazan": {
        "category": "Biz Kart",
        "start": "2026-06-16",
        "end": "2026-08-31",
        "status": "aktif_dogrulanmis",
        "required_terms": [
            "500 TL",
            "25.000 TL",
            "16 Haziran",
            "31 Ağustos 2026",
        ],
    },

    "Biz Kart ile Dijital Üyeliklerde %75 Nakit İade Fırsatı!": {
        "category": "Biz Kart",
        "start": "2026-06-16",
        "end": "2026-08-31",
        "status": "aktif_dogrulanmis",
        "required_terms": [
            "%75",
            "300 TL",
            "16 Haziran",
            "31 Ağustos 2026",
        ],
    },

    "Hayat Finans'la İşlem Yaptıkça Kazan!": {
        "category": "Genel",
        "start": "2026-07-02",
        "end": "2026-12-31",
        "status": "aktif_dogrulanmis",
        "required_terms": [
            "2 Temmuz",
            "31 Aralık 2026",
            "nakit ödül",
            "Hayat Pay",
        ],
    },

    "Birikimin Büyüsün, Avantajın Bitmesin!": {
        "category": "Katılma Hesabı",
        "start": "",
        "end": "2026-10-08",
        "status": "aktif_dogrulanmis",
        "required_terms": [
            "%99",
            "%95",
            "%90",
            "08.10.2026",
        ],
    },

    "Gümüş İşlemleri Hayat FX'te!": {
        "category": "Yatırım",
        "start": "2026-06-01",
        "end": "2026-08-31",
        "status": "aktif_dogrulanmis",
        "required_terms": [
            "1 Haziran 2026",
            "31 Ağustos 2026",
            "gümüş",
            "dar makas",
        ],
    },

    "Biz Kart ile Yemek Harcamalarına 1.000 TL’ye Varan Nakit İade!": {
        "category": "Biz Kart",
        "start": "2026-02-06",
        "end": "2026-08-31",
        "status": "aktif_dogrulanmis",
        "required_terms": [
            "%10",
            "1.000 TL",
            "100 TL",
            "31 Ağustos 2026",
        ],
    },

    "Bana Bunu Al İş Ortağım ile Troy Mağazalarında Finansman Fırsatı!": {
        "category": "Teknoloji",
        "start": "",
        "end": "2026-08-31",
        "status": "aktif_dogrulanmis",
        "required_terms": [
            "3 aya",
            "80.000TL",
            "31 Ağustos 2026",
            "fiziksel mağazalarda",
        ],
    },

    "Xiaomi Ürünlerinde Finansman Avantajı": {
        "category": "Teknoloji",
        "start": "",
        "end": "2026-08-31",
        "status": "aktif_dogrulanmis",
        "required_terms": [
            "3 aya",
            "40.000TL",
            "31 Ağustos 2026",
            "fiziksel mağazalarda",
        ],
    },

    "Harcadıkça Kazan, Cebin Hep Dolu Kalsın!": {
        "category": "Genel",
        "start": "",
        "end": "",
        "status": "aktif_listede",
        "required_terms": [
            "GastroClub",
            "%10",
            "%50",
            "bireysel Hayat Finans müşterileri",
        ],
    },
}


# =========================================================
# NORMALİZASYON
# =========================================================

def tr_lower(value):
    value = str(value or "")

    value = value.replace("İ", "i")
    value = value.replace("I", "ı")

    value = value.replace("’", "'")
    value = value.replace("‘", "'")
    value = value.replace("´", "'")
    value = value.replace("`", "'")

    value = value.replace("“", '"')
    value = value.replace("”", '"')

    return value.casefold()


def normalize_url(url):
    return str(url or "").strip().rstrip("/")


def is_official_domain(url):
    host = urlparse(
        normalize_url(url)
    ).netloc.lower()

    return (
        host == "hayatfinans.com.tr"
        or host == "www.hayatfinans.com.tr"
        or host.endswith(".hayatfinans.com.tr")
    )


# =========================================================
# JSON
# =========================================================

def load_json():

    if not os.path.exists(
        INPUT_FILE
    ):

        raise FileNotFoundError(
            f"Dosya bulunamadı: {INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(
            file
        )


# =========================================================
# DUPLICATE
# =========================================================

def find_duplicates(values):

    seen = set()

    duplicates = []

    for value in values:

        key = tr_lower(
            value
        ).strip()

        if key in seen:

            duplicates.append(
                value
            )

        else:

            seen.add(
                key
            )

    return duplicates


# =========================================================
# BAŞLIK EŞLEŞTİR
# =========================================================

def get_expected_title(actual_title):

    normalized_actual = tr_lower(
        actual_title
    )

    for expected_title in EXPECTED_CAMPAIGNS:

        if (
            tr_lower(expected_title)
            == normalized_actual
        ):

            return expected_title

    return None


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 115
    )

    print(
        "HAYAT FİNANS - KAMPANYA RAW VALIDATOR V1"
    )

    print(
        "=" * 115
    )

    print(
        "Dosya:",
        INPUT_FILE
    )

    data = load_json()

    errors = []

    warnings = []

    # =====================================================
    # 1. WRAPPER
    # =====================================================

    print()

    print(
        "[1/7] Wrapper kontrol ediliyor..."
    )

    bank = data.get(
        "banka",
        ""
    )

    record_type = data.get(
        "kayit_turu",
        ""
    )

    expected_count_from_json = data.get(
        "beklenen_kayit_sayisi"
    )

    total_count = data.get(
        "toplam_kayit"
    )

    campaigns = data.get(
        "kampanyalar",
        []
    )

    http_errors = data.get(
        "http_hatalari",
        []
    )

    duplicate_url_count = data.get(
        "duplicate_url_sayisi",
        None
    )

    duplicate_title_count = data.get(
        "duplicate_baslik_sayisi",
        None
    )

    if bank != EXPECTED_BANK:

        errors.append(
            (
                "Wrapper banka adı yanlış: "
                f"{bank}"
            )
        )

    if record_type != EXPECTED_RECORD_TYPE:

        errors.append(
            (
                "Wrapper kayıt türü yanlış: "
                f"{record_type}"
            )
        )

    if expected_count_from_json != EXPECTED_COUNT:

        errors.append(
            (
                "beklenen_kayit_sayisi yanlış. "
                f"Beklenen={EXPECTED_COUNT}, "
                f"Gerçek={expected_count_from_json}"
            )
        )

    if not isinstance(
        campaigns,
        list
    ):

        errors.append(
            "'kampanyalar' list değil."
        )

        campaigns = []

    if total_count != len(
        campaigns
    ):

        errors.append(
            (
                "toplam_kayit ile gerçek kayıt "
                "sayısı uyuşmuyor. "
                f"toplam_kayit={total_count}, "
                f"liste={len(campaigns)}"
            )
        )

    if len(
        campaigns
    ) != EXPECTED_COUNT:

        errors.append(
            (
                "Kampanya sayısı yanlış. "
                f"Beklenen={EXPECTED_COUNT}, "
                f"Gerçek={len(campaigns)}"
            )
        )

    print(
        "Banka:",
        bank
    )

    print(
        "Kayıt türü:",
        record_type
    )

    print(
        "Toplam kayıt:",
        len(campaigns)
    )

    # =====================================================
    # 2. HTTP
    # =====================================================

    print()

    print(
        "[2/7] HTTP hata kontrol ediliyor..."
    )

    if http_errors:

        errors.append(
            (
                "RAW içinde HTTP hatası var: "
                f"{len(http_errors)}"
            )
        )

    print(
        "HTTP hata:",
        len(http_errors)
    )

    # =====================================================
    # 3. ZORUNLU ALANLAR
    # =====================================================

    print()

    print(
        "[3/7] Zorunlu alanlar kontrol ediliyor..."
    )

    required_fields = [
        "banka",
        "kayit_turu",
        "urun_adi",
        "kampanya_kategorisi",
        "aktiflik_durumu",
        "kampanya_baslangic_tarihi",
        "kampanya_bitis_tarihi",
        "tarih_kaynak_ifadesi",
        "kaynak_url",
        "ham_metin",
    ]

    for index, campaign in enumerate(
        campaigns,
        start=1
    ):

        title = campaign.get(
            "urun_adi",
            f"Kayıt {index}"
        )

        for field in required_fields:

            if field not in campaign:

                errors.append(
                    (
                        f"{title} -> "
                        f"alan yok: {field}"
                    )
                )

        if (
            campaign.get(
                "banka"
            )
            != EXPECTED_BANK
        ):

            errors.append(
                (
                    f"{title} -> "
                    "banka adı yanlış."
                )
            )

        if (
            campaign.get(
                "kayit_turu"
            )
            != "kampanya"
        ):

            errors.append(
                (
                    f"{title} -> "
                    "kayit_turu kampanya değil."
                )
            )

        if not campaign.get(
            "urun_adi",
            ""
        ).strip():

            errors.append(
                "Boş kampanya başlığı bulundu."
            )

        if not campaign.get(
            "kampanya_kategorisi",
            ""
        ).strip():

            errors.append(
                (
                    f"{title} -> "
                    "kampanya_kategorisi boş."
                )
            )

        if not campaign.get(
            "aktiflik_durumu",
            ""
        ).strip():

            errors.append(
                (
                    f"{title} -> "
                    "aktiflik_durumu boş."
                )
            )

        if not campaign.get(
            "kaynak_url",
            ""
        ).strip():

            errors.append(
                (
                    f"{title} -> "
                    "kaynak_url boş."
                )
            )

        if not campaign.get(
            "ham_metin",
            ""
        ).strip():

            errors.append(
                (
                    f"{title} -> "
                    "ham_metin boş."
                )
            )

    print(
        "Zorunlu alan kontrolü tamamlandı."
    )

    # =====================================================
    # 4. URL / DUPLICATE
    # =====================================================

    print()

    print(
        "[4/7] URL ve duplicate kontrol ediliyor..."
    )

    urls = [
        normalize_url(
            campaign.get(
                "kaynak_url",
                ""
            )
        )
        for campaign in campaigns
    ]

    titles = [
        campaign.get(
            "urun_adi",
            ""
        )
        for campaign in campaigns
    ]

    duplicate_urls = find_duplicates(
        urls
    )

    duplicate_titles = find_duplicates(
        titles
    )

    if duplicate_urls:

        errors.append(
            (
                "Duplicate URL bulundu: "
                f"{duplicate_urls}"
            )
        )

    if duplicate_titles:

        errors.append(
            (
                "Duplicate başlık bulundu: "
                f"{duplicate_titles}"
            )
        )

    if (
        duplicate_url_count
        != len(duplicate_urls)
    ):

        errors.append(
            (
                "Wrapper duplicate_url_sayisi "
                "gerçek değerle uyuşmuyor."
            )
        )

    if (
        duplicate_title_count
        != len(duplicate_titles)
    ):

        errors.append(
            (
                "Wrapper duplicate_baslik_sayisi "
                "gerçek değerle uyuşmuyor."
            )
        )

    for campaign in campaigns:

        if not is_official_domain(
            campaign.get(
                "kaynak_url",
                ""
            )
        ):

            errors.append(
                (
                    f"{campaign.get('urun_adi')} -> "
                    "resmi olmayan domain."
                )
            )

    print(
        "Duplicate URL:",
        len(duplicate_urls)
    )

    print(
        "Duplicate başlık:",
        len(duplicate_titles)
    )

    # =====================================================
    # 5. BEKLENEN KAMPANYALAR
    # =====================================================

    print()

    print(
        "[5/7] Beklenen kampanyalar kontrol ediliyor..."
    )

    matched_campaigns = {}

    unexpected_titles = []

    for campaign in campaigns:

        actual_title = campaign.get(
            "urun_adi",
            ""
        )

        expected_title = get_expected_title(
            actual_title
        )

        if expected_title is None:

            unexpected_titles.append(
                actual_title
            )

            errors.append(
                (
                    "Beklenmeyen kampanya: "
                    f"{actual_title}"
                )
            )

            continue

        matched_campaigns[
            expected_title
        ] = campaign

    missing_titles = []

    for expected_title in EXPECTED_CAMPAIGNS:

        if expected_title not in matched_campaigns:

            missing_titles.append(
                expected_title
            )

            errors.append(
                (
                    "Beklenen kampanya eksik: "
                    f"{expected_title}"
                )
            )

    print(
        "Eksik kampanya:",
        len(missing_titles)
    )

    print(
        "Beklenmeyen kampanya:",
        len(unexpected_titles)
    )

    # =====================================================
    # 6. SEMANTİK KONTROL
    # =====================================================

    print()

    print(
        "[6/7] Kampanya içerikleri kontrol ediliyor..."
    )

    for title, config in (
        EXPECTED_CAMPAIGNS.items()
    ):

        if title not in matched_campaigns:
            continue

        campaign = matched_campaigns[
            title
        ]

        text = campaign.get(
            "ham_metin",
            ""
        )

        lower = tr_lower(
            text
        )

        print()

        print(
            "-",
            title
        )

        print(
            "  Kategori:",
            campaign.get(
                "kampanya_kategorisi"
            )
        )

        print(
            "  Başlangıç:",
            campaign.get(
                "kampanya_baslangic_tarihi"
            )
            or "-"
        )

        print(
            "  Bitiş:",
            campaign.get(
                "kampanya_bitis_tarihi"
            )
            or "-"
        )

        print(
            "  Durum:",
            campaign.get(
                "aktiflik_durumu"
            )
        )

        print(
            "  Metin uzunluğu:",
            len(text)
        )

        if len(text) < 100:

            errors.append(
                (
                    f"{title} -> "
                    "ham metin çok kısa."
                )
            )

        if (
            campaign.get(
                "kampanya_kategorisi"
            )
            != config[
                "category"
            ]
        ):

            errors.append(
                (
                    f"{title} -> "
                    "kategori yanlış. "
                    f"Beklenen={config['category']}, "
                    f"Gerçek="
                    f"{campaign.get('kampanya_kategorisi')}"
                )
            )

        if (
            campaign.get(
                "kampanya_baslangic_tarihi"
            )
            != config[
                "start"
            ]
        ):

            errors.append(
                (
                    f"{title} -> "
                    "başlangıç tarihi yanlış. "
                    f"Beklenen={config['start']}, "
                    f"Gerçek="
                    f"{campaign.get('kampanya_baslangic_tarihi')}"
                )
            )

        if (
            campaign.get(
                "kampanya_bitis_tarihi"
            )
            != config[
                "end"
            ]
        ):

            errors.append(
                (
                    f"{title} -> "
                    "bitiş tarihi yanlış. "
                    f"Beklenen={config['end']}, "
                    f"Gerçek="
                    f"{campaign.get('kampanya_bitis_tarihi')}"
                )
            )

        if (
            campaign.get(
                "aktiflik_durumu"
            )
            != config[
                "status"
            ]
        ):

            errors.append(
                (
                    f"{title} -> "
                    "aktiflik durumu yanlış. "
                    f"Beklenen={config['status']}, "
                    f"Gerçek="
                    f"{campaign.get('aktiflik_durumu')}"
                )
            )

        for term in config[
            "required_terms"
        ]:

            found = (
                tr_lower(term)
                in lower
            )

            print(
                " ",
                (
                    "✓"
                    if found
                    else "✗"
                ),
                term
            )

            if not found:

                errors.append(
                    (
                        f"{title} -> "
                        "beklenen ifade yok: "
                        f"{term}"
                    )
                )

    # =====================================================
    # 7. ÖZEL KONTROLLER
    # =====================================================

    print()

    print(
        "[7/7] Özel çapraz kontroller yapılıyor..."
    )

    # -----------------------------------------------------
    # GastroClub
    # -----------------------------------------------------

    gastro_title = (
        "Harcadıkça Kazan, Cebin Hep Dolu Kalsın!"
    )

    if gastro_title in matched_campaigns:

        gastro = matched_campaigns[
            gastro_title
        ]

        if gastro.get(
            "kampanya_baslangic_tarihi"
        ):

            errors.append(
                (
                    "GastroClub -> kaynakta açık "
                    "başlangıç tarihi yok; "
                    "başlangıç boş olmalı."
                )
            )

        if gastro.get(
            "kampanya_bitis_tarihi"
        ):

            errors.append(
                (
                    "GastroClub -> kaynakta açık "
                    "bitiş tarihi yok; "
                    "bitiş boş olmalı."
                )
            )

        if (
            gastro.get(
                "aktiflik_durumu"
            )
            != "aktif_listede"
        ):

            errors.append(
                (
                    "GastroClub -> tarih olmadığı için "
                    "aktif_listede olmalı."
                )
            )

    # -----------------------------------------------------
    # Hayat Finans'la İşlem Yaptıkça Kazan
    # -----------------------------------------------------

    işlem_title = (
        "Hayat Finans'la İşlem Yaptıkça Kazan!"
    )

    if işlem_title in matched_campaigns:

        işlem = matched_campaigns[
            işlem_title
        ]

        işlem_text = tr_lower(
            işlem.get(
                "ham_metin",
                ""
            )
        )

        if (
            "hayat pay"
            not in işlem_text
        ):

            errors.append(
                (
                    "Hayat Finans'la İşlem Yaptıkça Kazan "
                    "-> Hayat Pay bilgisi kayıp."
                )
            )

        if (
            işlem.get(
                "kampanya_baslangic_tarihi"
            )
            != "2026-07-02"
        ):

            errors.append(
                (
                    "İşlem Yaptıkça Kazan -> "
                    "2 Temmuz başlangıç kayıp."
                )
            )

        if (
            işlem.get(
                "kampanya_bitis_tarihi"
            )
            != "2026-12-31"
        ):

            errors.append(
                (
                    "İşlem Yaptıkça Kazan -> "
                    "31 Aralık bitiş kayıp."
                )
            )

    # -----------------------------------------------------
    # Avantajlı Hesap
    # -----------------------------------------------------

    avantaj_title = (
        "Birikimin Büyüsün, Avantajın Bitmesin!"
    )

    if avantaj_title in matched_campaigns:

        avantaj = matched_campaigns[
            avantaj_title
        ]

        avantaj_text = tr_lower(
            avantaj.get(
                "ham_metin",
                ""
            )
        )

        for rate in [
            "%99",
            "%95",
            "%90",
        ]:

            if (
                tr_lower(rate)
                not in avantaj_text
            ):

                errors.append(
                    (
                        f"Avantajlı Hesap -> "
                        f"{rate} oranı kayıp."
                    )
                )

    # -----------------------------------------------------
    # Troy / Xiaomi
    # -----------------------------------------------------

    troy_title = (
        "Bana Bunu Al İş Ortağım ile "
        "Troy Mağazalarında Finansman Fırsatı!"
    )

    if troy_title in matched_campaigns:

        troy_text = tr_lower(
            matched_campaigns[
                troy_title
            ].get(
                "ham_metin",
                ""
            )
        )

        if (
            "80.000tl"
            not in troy_text
        ):

            errors.append(
                "Troy -> 80.000 TL üst limit kayıp."
            )

    xiaomi_title = (
        "Xiaomi Ürünlerinde Finansman Avantajı"
    )

    if xiaomi_title in matched_campaigns:

        xiaomi_text = tr_lower(
            matched_campaigns[
                xiaomi_title
            ].get(
                "ham_metin",
                ""
            )
        )

        if (
            "40.000tl"
            not in xiaomi_text
        ):

            errors.append(
                "Xiaomi -> 40.000 TL üst limit kayıp."
            )

    print(
        "Özel çapraz kontroller tamamlandı."
    )

    # =====================================================
    # STATUS DAĞILIMI
    # =====================================================

    calculated_status_counts = {}

    for campaign in campaigns:

        status = campaign.get(
            "aktiflik_durumu",
            ""
        )

        calculated_status_counts[
            status
        ] = (
            calculated_status_counts.get(
                status,
                0
            )
            + 1
        )

    wrapper_status_counts = data.get(
        "durum_sayilari",
        {}
    )

    if (
        wrapper_status_counts
        != calculated_status_counts
    ):

        errors.append(
            (
                "durum_sayilari wrapper değeri "
                "gerçek kayıtlarla uyuşmuyor. "
                f"Wrapper={wrapper_status_counts}, "
                f"Gerçek={calculated_status_counts}"
            )
        )

    expected_status_counts = {
        "aktif_dogrulanmis": 10,
        "aktif_listede": 1,
    }

    if (
        calculated_status_counts
        != expected_status_counts
    ):

        errors.append(
            (
                "Durum dağılımı beklenenden farklı. "
                f"Beklenen={expected_status_counts}, "
                f"Gerçek={calculated_status_counts}"
            )
        )

    # =====================================================
    # FINAL
    # =====================================================

    print()

    print(
        "=" * 115
    )

    print(
        "VALIDATION SONUCU"
    )

    print(
        "=" * 115
    )

    print(
        "Beklenen kayıt:",
        EXPECTED_COUNT
    )

    print(
        "Gerçek kayıt:",
        len(campaigns)
    )

    print(
        "HTTP hata:",
        len(http_errors)
    )

    print(
        "Duplicate URL:",
        len(duplicate_urls)
    )

    print(
        "Duplicate başlık:",
        len(duplicate_titles)
    )

    print(
        "Eksik kampanya:",
        len(missing_titles)
    )

    print(
        "Beklenmeyen kampanya:",
        len(unexpected_titles)
    )

    print()

    print(
        "Durum dağılımı:",
        calculated_status_counts
    )

    print(
        "Warning:",
        len(warnings)
    )

    print(
        "Error:",
        len(errors)
    )

    if warnings:

        print()

        print(
            "UYARILAR:"
        )

        for warning in warnings:

            print(
                "-",
                warning
            )

    if errors:

        print()

        print(
            "HATALAR:"
        )

        for error in errors:

            print(
                "-",
                error
            )

    print()

    if not errors:

        print(
            (
                "SONUÇ: HAYAT FİNANS "
                "KAMPANYA RAW VALIDATION BAŞARILI ✅"
            )
        )

    else:

        print(
            (
                "SONUÇ: HAYAT FİNANS "
                "KAMPANYA RAW VALIDATION BAŞARISIZ ❌"
            )
        )

    print(
        "=" * 115
    )


if __name__ == "__main__":
    main()