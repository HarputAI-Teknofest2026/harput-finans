import json
import os
import re


# =========================================================
# AYARLAR
# =========================================================

INPUT_FILE = "data/raw/hayat_finans_kampanyalar.json"

EXPECTED_COUNT = 11

BANK_NAME = "Hayat Finans Katılım Bankası"


# =========================================================
# BEKLENEN KAMPANYALAR VE KRİTİK BİLGİLER
# =========================================================

CAMPAIGN_CHECKS = {
    "Arkadaşını Davet Et, Avantajlı Hesapla Kazanmaya Başla!": {
        "facts": [
            ("Kampanya başlangıcı", "17 Ağustos"),
            ("Kampanya bitişi", "17 Eylül 2026"),
            ("Kişi başı ödül", "2.000 TL"),
            ("Toplam ödül üst limiti", "10.000 TL"),
            ("Minimum hesap bakiyesi", "50.000 TL"),
            ("Bekleme süresi", "30 gün"),
            ("Banka kartı ödül oranı", "%20"),
            ("Banka kartı toplam ödül", "500 TL"),
        ]
    },

    "Avantajlı Hesap Müşterilerine Özel FX Dar Makas Avantajı!": {
        "facts": [
            ("Kampanya başlangıcı", "17 Temmuz"),
            ("Kampanya bitişi", "17 Eylül 2026"),
            ("İşlem hacmi üst sınırı", "5.000 USD"),
            ("Dar makas oranı", "%0,1"),
            ("Platform", "Hayat FX"),
            ("Hedef hesap", "Avantajlı Hesap"),
        ]
    },

    "Biz Kart Arkadaşını Getir & Kazan": {
        "facts": [
            ("Kampanya başlangıcı", "16 Haziran"),
            ("Kampanya bitişi", "31 Ağustos 2026"),
            ("Ödül", "500 TL"),
            ("Toplam ödül üst limiti", "25.000 TL"),
            ("Yaş aralığı", "8-25"),
            ("Net transfer koşulu", "1.000 TL"),
            ("Maksimum çocuk", "5 çocuğuna"),
        ]
    },

    "Biz Kart ile Dijital Üyeliklerde %75 Nakit İade Fırsatı!": {
        "facts": [
            ("Kampanya başlangıcı", "16 Haziran"),
            ("Kampanya bitişi", "31 Ağustos 2026"),
            ("Nakit iade oranı", "%75"),
            ("Maksimum ödül", "300 TL"),
            ("Spotify", "Spotify"),
            ("Netflix", "Netflix"),
            ("YouTube Premium", "YouTube Premium"),
        ]
    },

    "Hayat Finans'la İşlem Yaptıkça Kazan!": {
        "facts": [
            ("Kampanya başlangıcı", "2 Temmuz"),
            ("Kampanya bitişi", "31 Aralık 2026"),
            ("Ödül cüzdanı", "Hayat Pay"),
            ("Para transferi", "Gelen Para Transferi"),
            ("Fatura", "Fatura Ödeme"),
            ("Döviz", "Döviz İşlemleri"),
            ("Banka kartı", "Banka Kartı Harcaması"),
            ("Biz Kart", "Biz Kart Başvurusu"),
            ("Kart harcama oranı", "%1"),
            ("Döviz/transfer oranı", "%0,1"),
        ]
    },

    "Birikimin Büyüsün, Avantajın Bitmesin!": {
        "facts": [
            ("Altın oranı", "%99"),
            ("Gümüş oranı", "%95"),
            ("Bronz oranı", "%90"),
            ("Minimum tutar", "50.000 TL"),
            ("Maksimum tutar", "2.000.000 TL"),
            ("Başlangıç vadesi", "32 günden"),
            ("Fiyatlama kampanya bitişi", "08.10.2026"),
        ]
    },

    "Gümüş İşlemleri Hayat FX'te!": {
        "facts": [
            ("Kampanya başlangıcı", "1 Haziran 2026"),
            ("Kampanya bitişi", "31 Ağustos 2026"),
            ("Ürün", "gümüş"),
            ("Avantaj", "dar makas"),
            ("Platform", "Hayat FX"),
            ("Hedef", "bireysel müşteriler"),
        ]
    },

    "Biz Kart ile Yemek Harcamalarına 1.000 TL’ye Varan Nakit İade!": {
        "facts": [
            ("Kampanya başlangıcı", "6 Şubat"),
            ("Kampanya bitişi", "31 Ağustos 2026"),
            ("Nakit iade oranı", "%10"),
            ("Günlük üst limit", "100 TL"),
            ("Aylık üst limit", "1.000 TL"),
            ("Kart", "Biz Kart"),
            ("Sektör", "Lokanta/Restoran"),
        ]
    },

    "Bana Bunu Al İş Ortağım ile Troy Mağazalarında Finansman Fırsatı!": {
        "facts": [
            ("Kampanya bitişi", "31 Ağustos 2026"),
            ("Taksit", "3 aya"),
            ("Üst limit", "80.000TL"),
            ("Kanal", "fiziksel mağazalarda"),
            ("Ürün", "Bana Bunu Al İş Ortağım"),
        ]
    },

    "Xiaomi Ürünlerinde Finansman Avantajı": {
        "facts": [
            ("Kampanya bitişi", "31 Ağustos 2026"),
            ("Taksit", "3 aya"),
            ("Üst limit", "40.000TL"),
            ("Kanal", "fiziksel mağazalarda"),
            ("Ürün", "Bana Bunu Al İş Ortağım"),
        ]
    },

    "Harcadıkça Kazan, Cebin Hep Dolu Kalsın!": {
        "facts": [
            ("Platform", "GastroClub"),
            ("Alt indirim oranı", "%10"),
            ("Üst indirim oranı", "%50"),
            ("İşletme sayısı", "1.200"),
            ("Üyelik", "ücretsiz"),
            ("Hedef kitle", "bireysel Hayat Finans müşterileri"),
        ]
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


def one_line(value):
    return re.sub(
        r"\s+",
        " ",
        str(value or "")
    ).strip()


def contains(text, value):
    return (
        tr_lower(value)
        in tr_lower(text)
    )


# =========================================================
# JSON
# =========================================================

def load_json():

    if not os.path.exists(INPUT_FILE):

        raise FileNotFoundError(
            f"RAW dosya bulunamadı: {INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# =========================================================
# RECORD BUL
# =========================================================

def find_record(records, expected_title):

    expected_normalized = tr_lower(
        expected_title
    )

    for record in records:

        if (
            tr_lower(
                record.get(
                    "urun_adi",
                    ""
                )
            )
            == expected_normalized
        ):

            return record

    return None


# =========================================================
# FOOTER / KİRLİLİK KONTROLÜ
# =========================================================

def inspect_contamination(text):

    suspicious = []

    markers = [
        "size nasıl yardımcı olabiliriz?",
        "en çok ziyaret edilenler",
        "gizlilik politikası",
        "çerez politikası",
        "kişisel verilerin korunması",
        "internet sitemizde çerez",
    ]

    lower = tr_lower(
        text
    )

    for marker in markers:

        if (
            tr_lower(marker)
            in lower
        ):

            suspicious.append(
                marker
            )

    return suspicious


# =========================================================
# TARİH KONTROLÜ
# =========================================================

def inspect_date_consistency(record):

    errors = []

    title = record.get(
        "urun_adi",
        ""
    )

    start = record.get(
        "kampanya_baslangic_tarihi",
        ""
    )

    end = record.get(
        "kampanya_bitis_tarihi",
        ""
    )

    source = record.get(
        "tarih_kaynak_ifadesi",
        ""
    )

    # GastroClub:
    # Kaynakta açık tarih yok.
    if title == (
        "Harcadıkça Kazan, Cebin Hep Dolu Kalsın!"
    ):

        if start:
            errors.append(
                "Kaynakta başlangıç tarihi yok ama RAW dolu."
            )

        if end:
            errors.append(
                "Kaynakta bitiş tarihi yok ama RAW dolu."
            )

        if source:
            errors.append(
                "Kaynakta kampanya tarihi yok ama tarih_kaynak_ifadesi dolu."
            )

        return errors

    # Troy / Xiaomi / Avantajlı Hesap:
    # yalnızca bitiş tarihi var.
    only_end_titles = {
        (
            "Bana Bunu Al İş Ortağım ile "
            "Troy Mağazalarında Finansman Fırsatı!"
        ),
        "Xiaomi Ürünlerinde Finansman Avantajı",
        "Birikimin Büyüsün, Avantajın Bitmesin!",
    }

    if title in only_end_titles:

        if start:
            errors.append(
                (
                    "Kaynakta açık başlangıç tarihi "
                    "yokken başlangıç tarihi üretilmiş."
                )
            )

        if not end:
            errors.append(
                "Kaynak bitiş tarihi kayıp."
            )

        return errors

    # Geri kalan tarihli kampanyalarda
    # başlangıç + bitiş bekliyoruz.
    if not start:
        errors.append(
            "Başlangıç tarihi kayıp."
        )

    if not end:
        errors.append(
            "Bitiş tarihi kayıp."
        )

    return errors


# =========================================================
# ÖZEL SEMANTİK KONTROLLER
# =========================================================

def inspect_special_semantics(record):

    errors = []

    warnings = []

    title = record.get(
        "urun_adi",
        ""
    )

    text = record.get(
        "ham_metin",
        ""
    )

    # -----------------------------------------------------
    # Arkadaşını Getir
    # -----------------------------------------------------

    if title == (
        "Arkadaşını Davet Et, Avantajlı Hesapla "
        "Kazanmaya Başla!"
    ):

        if not contains(
            text,
            "toplamda 5 kişi"
        ):

            errors.append(
                "5 kişi üst sınırı kayıp."
            )

        if not contains(
            text,
            "maksimum 10.000 TL"
        ):

            errors.append(
                "10.000 TL maksimum ödül bilgisi kayıp."
            )

        if not contains(
            text,
            "minimum 50.000 TL"
        ):

            errors.append(
                "50.000 TL minimum Avantajlı Hesap bilgisi kayıp."
            )

    # -----------------------------------------------------
    # FX DAR MAKAS
    # -----------------------------------------------------

    elif title == (
        "Avantajlı Hesap Müşterilerine Özel "
        "FX Dar Makas Avantajı!"
    ):

        if not (
            contains(text, "%0,1")
            or contains(text, "%0.1")
        ):

            errors.append(
                "%0,1 dar makas oranı kayıp."
            )

        if not contains(
            text,
            "5.000 USD"
        ):

            errors.append(
                "5.000 USD işlem hacmi kayıp."
            )

    # -----------------------------------------------------
    # BİZ KART ARKADAŞINI GETİR
    # -----------------------------------------------------

    elif title == (
        "Biz Kart Arkadaşını Getir & Kazan"
    ):

        if not contains(
            text,
            "maksimum 25.000 TL"
        ):

            errors.append(
                "25.000 TL ödül üst limiti kayıp."
            )

        if not contains(
            text,
            "8-25"
        ):

            errors.append(
                "8-25 yaş koşulu kayıp."
            )

    # -----------------------------------------------------
    # DİJİTAL ÜYELİK
    # -----------------------------------------------------

    elif title == (
        "Biz Kart ile Dijital Üyeliklerde "
        "%75 Nakit İade Fırsatı!"
    ):

        if not contains(
            text,
            "%75"
        ):

            errors.append(
                "%75 nakit iade kayıp."
            )

        if not contains(
            text,
            "300 TL"
        ):

            errors.append(
                "300 TL üst limit kayıp."
            )

    # -----------------------------------------------------
    # İŞLEM YAPTIKÇA KAZAN
    # -----------------------------------------------------

    elif title == (
        "Hayat Finans'la İşlem Yaptıkça Kazan!"
    ):

        required_operations = [
            "Gelen Para Transferi",
            "Fatura Ödeme",
            "Döviz İşlemleri",
            "Banka Kartı Harcaması",
            "Biz Kart Başvurusu",
        ]

        for operation in required_operations:

            if not contains(
                text,
                operation
            ):

                errors.append(
                    (
                        "Kazandıran işlem kayıp: "
                        f"{operation}"
                    )
                )

        if not contains(
            text,
            "Hayat Pay"
        ):

            errors.append(
                "Hayat Pay ödül cüzdanı bilgisi kayıp."
            )

    # -----------------------------------------------------
    # AVANTAJLI HESAP
    # -----------------------------------------------------

    elif title == (
        "Birikimin Büyüsün, Avantajın Bitmesin!"
    ):

        for rate in [
            "%99",
            "%95",
            "%90",
        ]:

            if not contains(
                text,
                rate
            ):

                errors.append(
                    f"{rate} kâr paylaşım oranı kayıp."
                )

        if not contains(
            text,
            "Fiyatlama kampanya bitiş tarihi 08.10.2026"
        ):

            errors.append(
                "08.10.2026 fiyatlama kampanya bitişi kayıp."
            )

        # Bu URL kampanya URL'si değil ama
        # resmi kampanya listesi bu ürün sayfasına yönlendiriyor.
        if "/hesaplar/" in record.get(
            "kaynak_url",
            ""
        ):

            warnings.append(
                (
                    "Resmi kampanya kartı /hesaplar/ "
                    "ürün sayfasına yönlendiriyor. "
                    "Kaynak korunmuş; hata değil."
                )
            )

    # -----------------------------------------------------
    # GÜMÜŞ
    # -----------------------------------------------------

    elif title == (
        "Gümüş İşlemleri Hayat FX'te!"
    ):

        if not contains(
            text,
            "gümüş alım"
        ):

            errors.append(
                "Gümüş alım işlemi bilgisi kayıp."
            )

        if not contains(
            text,
            "gümüş alım ve satım"
        ):

            errors.append(
                "Gümüş alış/satış kapsamı kayıp."
            )

    # -----------------------------------------------------
    # YEMEK
    # -----------------------------------------------------

    elif title == (
        "Biz Kart ile Yemek Harcamalarına "
        "1.000 TL’ye Varan Nakit İade!"
    ):

        if not contains(
            text,
            "%10"
        ):

            errors.append(
                "%10 nakit iade oranı kayıp."
            )

        if not contains(
            text,
            "günlük en fazla 100 TL"
        ):

            errors.append(
                "100 TL günlük üst limit kayıp."
            )

        if not contains(
            text,
            "aylık en fazla 1.000 TL"
        ):

            errors.append(
                "1.000 TL aylık üst limit kayıp."
            )

    # -----------------------------------------------------
    # TROY
    # -----------------------------------------------------

    elif title == (
        "Bana Bunu Al İş Ortağım ile "
        "Troy Mağazalarında Finansman Fırsatı!"
    ):

        if not contains(
            text,
            "3 aya varan"
        ):

            errors.append(
                "3 aya varan taksit bilgisi kayıp."
            )

        if not contains(
            text,
            "80.000TL"
        ):

            errors.append(
                "80.000 TL kampanya üst limiti kayıp."
            )

        if not contains(
            text,
            "sadece fiziksel mağazalarda"
        ):

            errors.append(
                "Fiziksel mağaza koşulu kayıp."
            )

    # -----------------------------------------------------
    # XIAOMI
    # -----------------------------------------------------

    elif title == (
        "Xiaomi Ürünlerinde Finansman Avantajı"
    ):

        if not contains(
            text,
            "3 aya varan"
        ):

            errors.append(
                "3 aya varan taksit bilgisi kayıp."
            )

        if not contains(
            text,
            "40.000TL"
        ):

            errors.append(
                "40.000 TL kampanya üst limiti kayıp."
            )

        if not contains(
            text,
            "sadece fiziksel mağazalarda"
        ):

            errors.append(
                "Fiziksel mağaza koşulu kayıp."
            )

    # -----------------------------------------------------
    # GASTROCLUB
    # -----------------------------------------------------

    elif title == (
        "Harcadıkça Kazan, Cebin Hep Dolu Kalsın!"
    ):

        if not contains(
            text,
            "%10 ila %50"
        ):

            errors.append(
                "%10-%50 indirim aralığı kayıp."
            )

        if not contains(
            text,
            "1.200"
        ):

            errors.append(
                "1.200+ işletme bilgisi kayıp."
            )

        if not contains(
            text,
            "ücretsiz"
        ):

            errors.append(
                "Ücretsiz üyelik bilgisi kayıp."
            )

        warnings.append(
            (
                "Kaynakta açık kampanya başlangıç/bitiş "
                "tarihi yok. Tarihler boş bırakılmış; doğru."
            )
        )

    return errors, warnings


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 118
    )

    print(
        "HAYAT FİNANS - KAMPANYA RAW INSPECTOR V1"
    )

    print(
        "=" * 118
    )

    print(
        "RAW:",
        INPUT_FILE
    )

    data = load_json()

    records = data.get(
        "kampanyalar",
        []
    )

    errors = []

    warnings = []

    print()

    print(
        "Toplam RAW kayıt:",
        len(records)
    )

    # =====================================================
    # SAYI
    # =====================================================

    if len(records) != EXPECTED_COUNT:

        errors.append(
            (
                "Kayıt sayısı yanlış. "
                f"Beklenen={EXPECTED_COUNT}, "
                f"Gerçek={len(records)}"
            )
        )

    # =====================================================
    # KAMPANYA BAZLI INSPECTION
    # =====================================================

    for index, (
        title,
        config
    ) in enumerate(
        CAMPAIGN_CHECKS.items(),
        start=1
    ):

        print()

        print(
            "-" * 118
        )

        print(
            f"[{index}/{EXPECTED_COUNT}] {title}"
        )

        record = find_record(
            records,
            title
        )

        if record is None:

            print(
                "KAYIT BULUNAMADI ❌"
            )

            errors.append(
                f"Kampanya bulunamadı: {title}"
            )

            continue

        text = record.get(
            "ham_metin",
            ""
        )

        print(
            "Kategori:",
            record.get(
                "kampanya_kategorisi",
                ""
            )
        )

        print(
            "Başlangıç:",
            record.get(
                "kampanya_baslangic_tarihi",
                ""
            )
            or "-"
        )

        print(
            "Bitiş:",
            record.get(
                "kampanya_bitis_tarihi",
                ""
            )
            or "-"
        )

        print(
            "Durum:",
            record.get(
                "aktiflik_durumu",
                ""
            )
        )

        print(
            "Metin uzunluğu:",
            len(text)
        )

        print()

        print(
            "KRİTİK BİLGİLER:"
        )

        missing_facts = []

        for label, value in config[
            "facts"
        ]:

            found = contains(
                text,
                value
            )

            print(
                (
                    "  ✓"
                    if found
                    else "  ✗"
                ),
                f"{label}:",
                value
            )

            if not found:

                missing_facts.append(
                    (
                        label,
                        value
                    )
                )

                errors.append(
                    (
                        f"{title} -> "
                        f"kritik bilgi kayıp: "
                        f"{label} = {value}"
                    )
                )

        # =================================================
        # TARİH TUTARLILIĞI
        # =================================================

        date_errors = inspect_date_consistency(
            record
        )

        for error in date_errors:

            errors.append(
                f"{title} -> {error}"
            )

        # =================================================
        # SEMANTİK
        # =================================================

        (
            semantic_errors,
            semantic_warnings
        ) = inspect_special_semantics(
            record
        )

        for error in semantic_errors:

            errors.append(
                f"{title} -> {error}"
            )

        for warning in semantic_warnings:

            warnings.append(
                f"{title} -> {warning}"
            )

        # =================================================
        # FOOTER / KİRLİLİK
        # =================================================

        contamination = inspect_contamination(
            text
        )

        if contamination:

            errors.append(
                (
                    f"{title} -> "
                    "muhtemel footer/site contamination: "
                    f"{contamination}"
                )
            )

        print()

        if (
            not missing_facts
            and not date_errors
            and not semantic_errors
            and not contamination
        ):

            print(
                "INSPECT: TEMİZ ✅"
            )

        else:

            print(
                "INSPECT: KONTROL GEREKİYOR ❌"
            )

    # =====================================================
    # DUPLICATE TITLE / URL
    # =====================================================

    urls = [
        one_line(
            record.get(
                "kaynak_url",
                ""
            )
        )
        for record in records
    ]

    titles = [
        tr_lower(
            record.get(
                "urun_adi",
                ""
            )
        )
        for record in records
    ]

    if len(set(urls)) != len(urls):

        errors.append(
            "Duplicate URL bulundu."
        )

    if len(set(titles)) != len(titles):

        errors.append(
            "Duplicate başlık bulundu."
        )

    # =====================================================
    # SONUÇ
    # =====================================================

    print()

    print(
        "=" * 118
    )

    print(
        "INSPECTOR SONUCU"
    )

    print(
        "=" * 118
    )

    print(
        "Beklenen kayıt:",
        EXPECTED_COUNT
    )

    print(
        "Gerçek kayıt:",
        len(records)
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
                "KAMPANYA RAW INSPECTION BAŞARILI ✅"
            )
        )

    else:

        print(
            (
                "SONUÇ: HAYAT FİNANS "
                "KAMPANYA RAW INSPECTION "
                "KONTROL GEREKİYOR ❌"
            )
        )

    print(
        "=" * 118
    )


if __name__ == "__main__":
    main()