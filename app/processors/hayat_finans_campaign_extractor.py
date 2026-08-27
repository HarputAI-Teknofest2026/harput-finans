import json
import os
import re
from copy import deepcopy


# =========================================================
# AYARLAR
# =========================================================

INPUT_FILE = "data/raw/hayat_finans_kampanyalar.json"

OUTPUT_FILE = "data/processed/hayat_finans_kampanya_extracted.json"

BANK_NAME = "Hayat Finans Katılım Bankası"

EXPECTED_COUNT = 11


# =========================================================
# STANDART ŞEMA
# =========================================================

EMPTY_SCHEMA = {
    "banka": "",
    "kayit_turu": "",
    "urun_adi": "",
    "urun_kategorisi": "",

    "kar_payi_orani": [],
    "finansman_orani": [],
    "finansman_tutari": [],
    "vade": [],
    "taksit_sayisi": [],

    "masraf_bilgisi": [],

    "kampanya_turu": "",
    "kampanya_avantaji": [],
    "kampanya_suresi": "",

    "hedef_kitle": [],
    "para_birimi": [],
    "kosullar": [],

    "kaynak_url": "",
    "ham_metin": ""
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


def normalize_for_match(value):
    """
    V2:
    Satır sonları / çoklu boşluklar eşleştirmeyi bozmasın.

    Örn:
        en fazla
        5 çocuğuna

    => en fazla 5 çocuğuna
    """

    value = tr_lower(value)

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def contains(text, value):
    return (
        normalize_for_match(value)
        in normalize_for_match(text)
    )


def unique_list(values):
    result = []
    seen = set()

    for value in values:

        if value is None:
            continue

        value = str(value).strip()

        if not value:
            continue

        key = normalize_for_match(
            value
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            value
        )

    return result


# =========================================================
# RAW
# =========================================================

def load_raw():

    if not os.path.exists(
        INPUT_FILE
    ):

        raise FileNotFoundError(
            f"RAW dosya bulunamadı: {INPUT_FILE}"
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
# TEMEL RECORD
# =========================================================

def create_base(record):

    result = deepcopy(
        EMPTY_SCHEMA
    )

    result["banka"] = BANK_NAME

    result["kayit_turu"] = "kampanya"

    result["urun_adi"] = record.get(
        "urun_adi",
        ""
    )

    result["kaynak_url"] = record.get(
        "kaynak_url",
        ""
    )

    result["ham_metin"] = record.get(
        "ham_metin",
        ""
    )

    result["kampanya_suresi"] = record.get(
        "tarih_kaynak_ifadesi",
        ""
    )

    return result


# =========================================================
# 1 - ARKADAŞINI DAVET ET
# =========================================================

def extract_invite_advantage(record):

    result = create_base(
        record
    )

    text = result[
        "ham_metin"
    ]

    result[
        "urun_kategorisi"
    ] = "Arkadaşını Getir"

    result[
        "kampanya_turu"
    ] = "Nakit Ödül"

    result[
        "kampanya_avantaji"
    ] = [
        (
            "Koşulları sağlayan her davet için "
            "2.000 TL nakit ödül"
        ),
        (
            "En fazla 5 kişi için toplam "
            "10.000 TL nakit ödül"
        ),
        (
            "Davet edilen müşterinin banka kartı "
            "harcamalarında %20 nakit ödül; "
            "günlük en fazla 100 TL ve toplam "
            "500 TL"
        ),
    ]

    result[
        "hedef_kitle"
    ] = [
        "Hayat Finans bireysel müşterileri"
    ]

    result[
        "para_birimi"
    ] = [
        "TL"
    ]

    conditions = []

    if contains(
        text,
        "minimum 50.000 TL"
    ):
        conditions.append(
            (
                "Avantajlı Katılma Hesabı minimum "
                "50.000 TL bakiye ile açılmalıdır."
            )
        )

    if contains(
        text,
        "30 günün dolması"
    ):
        conditions.append(
            (
                "Nakit ödül için hesap açılışından "
                "itibaren 30 günün dolması gerekir."
            )
        )

    if contains(
        text,
        "30 gün dolmadan"
    ):
        conditions.append(
            (
                "30 gün dolmadan kapatılan hesaplar "
                "ödül kazanamaz."
            )
        )

    if contains(
        text,
        "ilk Avantajlı Hesap"
    ):
        conditions.append(
            (
                "Davet eden müşteri yalnızca davet "
                "edilen kişinin ilk Avantajlı Hesap "
                "açılışından ödül kazanabilir."
            )
        )

    result[
        "kosullar"
    ] = unique_list(
        conditions
    )

    return result


# =========================================================
# 2 - FX DAR MAKAS
# =========================================================

def extract_fx_spread(record):

    result = create_base(
        record
    )

    text = result[
        "ham_metin"
    ]

    result[
        "urun_kategorisi"
    ] = "Yatırım"

    result[
        "kampanya_turu"
    ] = "Dar Makas Avantajı"

    result[
        "kampanya_avantaji"
    ] = [
        (
            "Hayat FX işlemlerinde 5.000 USD veya "
            "karşılığı işlem hacmine kadar "
            "%0,1 dar makas avantajı"
        )
    ]

    result[
        "hedef_kitle"
    ] = [
        (
            "17 Temmuz 2026 sonrası yeni Avantajlı "
            "Hesap açan bireysel müşteriler"
        )
    ]

    result[
        "para_birimi"
    ] = [
        "USD"
    ]

    conditions = []

    if contains(
        text,
        "08.30-17.30"
    ):
        conditions.append(
            (
                "Avantaj resmi iş günlerinde "
                "08.30-17.30 saatleri arasında geçerlidir."
            )
        )

    if contains(
        text,
        "Avantajlı Hesabının açık olması"
    ):
        conditions.append(
            (
                "Avantajdan yararlanmak için Avantajlı "
                "Hesabın açık olması gerekir."
            )
        )

    if contains(
        text,
        "sadece Hayat FX"
    ):
        conditions.append(
            (
                "Avantaj yalnızca Hayat FX "
                "işlemlerinde geçerlidir."
            )
        )

    if contains(
        text,
        "Kıymetli maden işlemleri"
    ):
        conditions.append(
            (
                "Kıymetli maden işlemleri kampanya "
                "kapsamında değildir."
            )
        )

    result[
        "kosullar"
    ] = unique_list(
        conditions
    )

    return result


# =========================================================
# 3 - BİZ KART ARKADAŞINI GETİR
# =========================================================

def extract_bizkart_invite(record):

    result = create_base(
        record
    )

    text = result[
        "ham_metin"
    ]

    result[
        "urun_kategorisi"
    ] = "Biz Kart"

    result[
        "kampanya_turu"
    ] = "Nakit Ödül"

    result[
        "kampanya_avantaji"
    ] = [
        (
            "Davet edilen kişinin ilk uygun Biz Kart "
            "başvurusu için davet eden müşteriye "
            "500 TL nakit ödül"
        ),
        (
            "Davet eden müşteri toplamda en fazla "
            "25.000 TL nakit ödül kazanabilir"
        ),
        (
            "Koşulları sağlayan Biz Kartlar için "
            "davet edilen müşteri de 500 TL "
            "nakit ödül kazanabilir"
        ),
    ]

    result[
        "hedef_kitle"
    ] = [
        "Hayat Finans bireysel müşterileri",
        (
            "Davet koduyla müşteri olan ve "
            "8-25 yaş aralığında çocuğu bulunan müşteriler"
        ),
    ]

    result[
        "para_birimi"
    ] = [
        "TL"
    ]

    conditions = []

    if contains(
        text,
        "8-25 yaş"
    ):
        conditions.append(
            (
                "Biz Kart için çocukların "
                "8-25 yaş aralığında olması gerekir."
            )
        )

    if contains(
        text,
        "1.000 TL ve üzeri"
    ):
        conditions.append(
            (
                "Biz Kartın bağlı olduğu cari hesaba "
                "7 gün içerisinde en az 1.000 TL net "
                "para transferi yapılmalıdır."
            )
        )

    # =====================================================
    # V2 DÜZELTME
    #
    # RAW:
    # "en fazla\n5 çocuğuna"
    #
    # normalize_for_match sayesinde artık yakalanıyor.
    # =====================================================

    if contains(
        text,
        "en fazla 5 çocuğuna"
    ):
        conditions.append(
            (
                "Davet edilen müşteri en fazla "
                "5 çocuğu için Biz Kart "
                "başvurusunda bulunabilir."
            )
        )

    if contains(
        text,
        "aktif olması gerekmektedir"
    ):
        conditions.append(
            (
                "Biz Kart kampanya süresi boyunca "
                "aktif olmalıdır."
            )
        )

    result[
        "kosullar"
    ] = unique_list(
        conditions
    )

    return result


# =========================================================
# 4 - DİJİTAL ÜYELİK
# =========================================================

def extract_digital_subscription(record):

    result = create_base(
        record
    )

    text = result[
        "ham_metin"
    ]

    result[
        "urun_kategorisi"
    ] = "Biz Kart"

    result[
        "kampanya_turu"
    ] = "Nakit İade"

    result[
        "kampanya_avantaji"
    ] = [
        (
            "Kampanya kapsamındaki dijital üyelik "
            "ödemelerinin %75'i oranında nakit ödül"
        ),
        (
            "Toplam maksimum 300 TL nakit ödül"
        ),
    ]

    result[
        "hedef_kitle"
    ] = [
        "Hayat Finans bireysel müşterileri",
        (
            "Hayat Finans Banka Kartı sahibi ve "
            "yakınına en az 1 Biz Kart tanımlamış müşteriler"
        ),
    ]

    result[
        "para_birimi"
    ] = [
        "TL"
    ]

    conditions = []

    if contains(
        text,
        "Spotify"
    ):
        conditions.append(
            (
                "Spotify, Netflix, ChatGPT OpenAI, "
                "HBO Max, YouTube Premium, tabii ve "
                "TOD ödemeleri kampanya kapsamındadır."
            )
        )

    if contains(
        text,
        "resmî web sitesi veya mobil uygulamaları"
    ):
        conditions.append(
            (
                "Ödemeler ilgili platformların resmi "
                "web sitesi veya mobil uygulaması "
                "üzerinden yapılmalıdır."
            )
        )

    if contains(
        text,
        "App Store"
    ):
        conditions.append(
            (
                "App Store, Google Play Store, "
                "App Gallery ve benzeri mağazalar "
                "üzerinden yapılan ödemeler kapsam dışıdır."
            )
        )

    result[
        "kosullar"
    ] = unique_list(
        conditions
    )

    return result


# =========================================================
# 5 - İŞLEM YAPTIKÇA KAZAN
# =========================================================

def extract_transaction_rewards(record):

    result = create_base(
        record
    )

    text = result[
        "ham_metin"
    ]

    # Kaynak liste görünümünde açık kategori
    # doğrulanamadı.
    result[
        "urun_kategorisi"
    ] = ""

    result[
        "kampanya_turu"
    ] = "Nakit Ödül"

    result[
        "kampanya_avantaji"
    ] = [
        (
            "EFT/FAST ile gelen para transferlerinde "
            "işlem tutarının %0,1'i kadar nakit ödül; "
            "işlem başına en fazla 10 TL"
        ),
        (
            "Talimatsız fatura ödemelerinde fatura "
            "başına en fazla 20 TL, talimatlı "
            "ödemelerde en fazla 30 TL nakit ödül"
        ),
        (
            "İlk otomatik fatura ödemesinde "
            "100 TL'ye varan nakit ödül"
        ),
        (
            "Döviz alış/satış işlemlerinde işlem "
            "tutarının %0,1'i kadar, aylık en fazla "
            "200 TL nakit ödül"
        ),
        (
            "Banka kartı harcamalarında %1 oranında, "
            "aylık en fazla 100 TL nakit ödül"
        ),
        (
            "Biz Kart başvurusu başına 20 TL, "
            "kampanya boyunca en fazla 100 TL ödül"
        ),
    ]

    result[
        "hedef_kitle"
    ] = [
        "Hayat Finans bireysel müşterileri"
    ]

    result[
        "para_birimi"
    ] = [
        "TL"
    ]

    conditions = []

    if contains(
        text,
        "aktif Hayat Pay cüzdanı"
    ):
        conditions.append(
            (
                "Ödül kazanımı için işlem öncesinde "
                "aktif Hayat Pay cüzdanı bulunmalıdır."
            )
        )

    if contains(
        text,
        "Sadece EFT/FAST"
    ):
        conditions.append(
            (
                "Para transferi ödülü yalnızca "
                "EFT/FAST ile gelen transferlerde geçerlidir."
            )
        )

    if contains(
        text,
        "en fazla 5 adet fatura"
    ):
        conditions.append(
            (
                "Bir ay içinde en fazla 5 fatura "
                "ödemesi ödül kazandırır."
            )
        )

    if contains(
        text,
        "Biz Kart ile yapılan işlemler dahil değildir"
    ):
        conditions.append(
            (
                "Banka kartı harcama ödülünde "
                "Biz Kart işlemleri kapsam dışıdır."
            )
        )

    result[
        "kosullar"
    ] = unique_list(
        conditions
    )

    return result


# =========================================================
# 6 - AVANTAJLI HESAP
# =========================================================

def extract_advantage_account(record):

    result = create_base(
        record
    )

    text = result[
        "ham_metin"
    ]

    result[
        "urun_kategorisi"
    ] = "Katılma Hesabı"

    result[
        "kar_payi_orani"
    ] = [
        "%99",
        "%95",
        "%90",
    ]

    result[
        "vade"
    ] = [
        "32 günden başlayan vadeler"
    ]

    result[
        "kampanya_turu"
    ] = "Kâr Paylaşım Avantajı"

    result[
        "kampanya_avantaji"
    ] = [
        (
            "Altın derecesinde %99 "
            "kâr paylaşım oranı"
        ),
        (
            "Gümüş derecesinde %95 "
            "kâr paylaşım oranı"
        ),
        (
            "Bronz derecesinde %90 "
            "kâr paylaşım oranı"
        ),
    ]

    result[
        "hedef_kitle"
    ] = [
        (
            "Katılım finans prensiplerine uygun "
            "birikim yapmak isteyen bireysel müşteriler"
        )
    ]

    result[
        "para_birimi"
    ] = [
        "TL"
    ]

    conditions = []

    if contains(
        text,
        "minimum tutar 50.000 TL"
    ):
        conditions.append(
            (
                "Hesap açılışı için minimum "
                "tutar 50.000 TL'dir."
            )
        )

    if contains(
        text,
        "maksimum tutar ise 2.000.000 TL"
    ):
        conditions.append(
            (
                "Hesap açılışı için maksimum "
                "tutar 2.000.000 TL'dir."
            )
        )

    if contains(
        text,
        "ilk açılışta Altın"
    ):
        conditions.append(
            (
                "Müşteriler ilk hesap açılışında "
                "Altın derecesi avantajıyla başlar."
            )
        )

    if contains(
        text,
        "12.05.2026"
    ):
        conditions.append(
            (
                "12.05.2026 itibarıyla Avantajlı Hesap "
                "derece yapısı güncellenmiştir."
            )
        )

    result[
        "kosullar"
    ] = unique_list(
        conditions
    )

    return result


# =========================================================
# 7 - GÜMÜŞ
# =========================================================

def extract_silver(record):

    result = create_base(
        record
    )

    text = result[
        "ham_metin"
    ]

    result[
        "urun_kategorisi"
    ] = "Yatırım"

    result[
        "kampanya_turu"
    ] = "Dar Makas Avantajı"

    result[
        "kampanya_avantaji"
    ] = [
        (
            "Hayat FX üzerinden gerçekleştirilen "
            "gümüş alım ve satım işlemlerinde "
            "dar makas avantajı"
        )
    ]

    result[
        "hedef_kitle"
    ] = [
        (
            "Kampanya döneminde Hayat FX üzerinden "
            "gümüş alım/satım işlemi yapan "
            "bireysel müşteriler"
        )
    ]

    conditions = []

    if contains(
        text,
        "risk seviyelerine göre belirlenen işlem limitleri"
    ):
        conditions.append(
            (
                "Müşteriler risk seviyelerine göre "
                "belirlenen işlem limitleri kapsamında "
                "kampanyadan yararlanabilir."
            )
        )

    if contains(
        text,
        "yalnızca gümüş alım ve satım"
    ):
        conditions.append(
            (
                "Kampanya yalnızca gümüş alım "
                "ve satım işlemlerini kapsar."
            )
        )

    result[
        "kosullar"
    ] = unique_list(
        conditions
    )

    return result


# =========================================================
# 8 - YEMEK
# =========================================================

def extract_food(record):

    result = create_base(
        record
    )

    text = result[
        "ham_metin"
    ]

    result[
        "urun_kategorisi"
    ] = "Biz Kart"

    result[
        "kampanya_turu"
    ] = "Nakit İade"

    result[
        "kampanya_avantaji"
    ] = [
        (
            "Biz Kart ile yemek harcamalarında "
            "%10'a kadar nakit iade"
        ),
        "Günlük en fazla 100 TL nakit iade",
        "Aylık en fazla 1.000 TL nakit iade",
    ]

    result[
        "hedef_kitle"
    ] = [
        (
            "Hayat Finans bireysel müşterileri "
            "arasındaki Biz Kart sahipleri"
        )
    ]

    result[
        "para_birimi"
    ] = [
        "TL"
    ]

    conditions = []

    if contains(
        text,
        "Biz Kart QR"
    ):
        conditions.append(
            (
                "Yalnızca Hayat Finans Biz Kart veya "
                "Biz Kart QR ile yapılan harcamalar "
                "kampanya kapsamındadır."
            )
        )

    if contains(
        text,
        "Lokanta/Restoran"
    ):
        conditions.append(
            (
                "Biz Kart ayarlarında Lokanta/Restoran "
                "ve Gıda sektörleri aktif olmalıdır."
            )
        )

    if contains(
        text,
        "sadece yurtiçinde"
    ):
        conditions.append(
            (
                "Kampanya yalnızca yurt içindeki "
                "işlemler için geçerlidir."
            )
        )

    result[
        "kosullar"
    ] = unique_list(
        conditions
    )

    return result


# =========================================================
# 9 - TROY
# =========================================================

def extract_troy(record):

    result = create_base(
        record
    )

    text = result[
        "ham_metin"
    ]

    result[
        "urun_kategorisi"
    ] = "Teknoloji"

    result[
        "finansman_tutari"
    ] = [
        "80.000 TL"
    ]

    result[
        "vade"
    ] = [
        "3 ay"
    ]

    result[
        "taksit_sayisi"
    ] = [
        "3"
    ]

    result[
        "kampanya_turu"
    ] = "Finansman Avantajı"

    result[
        "kampanya_avantaji"
    ] = [
        (
            "Troy mağazalarında 80.000 TL üst limite "
            "kadar 3 aya varan taksitli finansman fırsatı"
        )
    ]

    result[
        "hedef_kitle"
    ] = [
        "Hayat Finans müşterileri"
    ]

    result[
        "para_birimi"
    ] = [
        "TL"
    ]

    conditions = []

    if contains(
        text,
        "sadece fiziksel mağazalarda"
    ):
        conditions.append(
            (
                "Kampanya yalnızca fiziksel "
                "Troy mağazalarında geçerlidir."
            )
        )

    if contains(
        text,
        "Banka uygun görmediği kredi başvurularını"
    ):
        conditions.append(
            (
                "Finansman başvuruları banka "
                "değerlendirmesine tabidir."
            )
        )

    result[
        "kosullar"
    ] = unique_list(
        conditions
    )

    return result


# =========================================================
# 10 - XIAOMI
# =========================================================

def extract_xiaomi(record):

    result = create_base(
        record
    )

    text = result[
        "ham_metin"
    ]

    result[
        "urun_kategorisi"
    ] = "Teknoloji"

    result[
        "finansman_tutari"
    ] = [
        "40.000 TL"
    ]

    result[
        "vade"
    ] = [
        "3 ay"
    ]

    result[
        "taksit_sayisi"
    ] = [
        "3"
    ]

    result[
        "kampanya_turu"
    ] = "Finansman Avantajı"

    result[
        "kampanya_avantaji"
    ] = [
        (
            "Xiaomi mağazalarında 40.000 TL üst limite "
            "kadar 3 aya varan taksitli finansman fırsatı"
        )
    ]

    result[
        "hedef_kitle"
    ] = [
        "Hayat Finans müşterileri"
    ]

    result[
        "para_birimi"
    ] = [
        "TL"
    ]

    conditions = []

    if contains(
        text,
        "sadece fiziksel mağazalarda"
    ):
        conditions.append(
            (
                "Kampanya yalnızca fiziksel "
                "Xiaomi mağazalarında geçerlidir."
            )
        )

    if contains(
        text,
        "Banka uygun görmediği kredi başvurularını"
    ):
        conditions.append(
            (
                "Finansman başvuruları banka "
                "değerlendirmesine tabidir."
            )
        )

    result[
        "kosullar"
    ] = unique_list(
        conditions
    )

    return result


# =========================================================
# 11 - GASTROCLUB
# =========================================================

def extract_gastroclub(record):

    result = create_base(
        record
    )

    text = result[
        "ham_metin"
    ]

    result[
        "urun_kategorisi"
    ] = "Genel"

    result[
        "kampanya_turu"
    ] = "İndirim"

    result[
        "kampanya_avantaji"
    ] = [
        (
            "GastroClub kapsamında çeşitli sektörlerde "
            "%10 ile %50 arasında indirim"
        ),
        "GastroClub üyeliği ücretsizdir",
        (
            "200'e yakın restoranda "
            "%30'a varan indirim"
        ),
        (
            "Paket servis platformlarında "
            "%25'e varan indirim"
        ),
        (
            "Moda ve teknoloji markalarında "
            "%20'ye varan avantaj"
        ),
        (
            "Kuru temizleme hizmetinde "
            "%50 indirim"
        ),
    ]

    result[
        "hedef_kitle"
    ] = [
        "Bireysel Hayat Finans müşterileri"
    ]

    conditions = []

    if contains(
        text,
        "Kampanyalar > Ayrıcalıklar"
    ):
        conditions.append(
            (
                "GastroClub üyeliği ve indirim kodları "
                "Hayat Finans Mobil uygulamasındaki "
                "Kampanyalar > Ayrıcalıklar "
                "alanından kullanılır."
            )
        )

    if contains(
        text,
        "diğer davet kodlu kampanyalarla birleştirilemez"
    ):
        conditions.append(
            (
                "Kampanya diğer davet kodlu "
                "kampanyalarla birleştirilemez."
            )
        )

    result[
        "kosullar"
    ] = unique_list(
        conditions
    )

    return result


# =========================================================
# ROUTER
# =========================================================

def extract_record(record):

    title = record.get(
        "urun_adi",
        ""
    )

    normalized_title = normalize_for_match(
        title
    )

    routes = {
        normalize_for_match(
            "Arkadaşını Davet Et, Avantajlı Hesapla Kazanmaya Başla!"
        ): extract_invite_advantage,

        normalize_for_match(
            "Avantajlı Hesap Müşterilerine Özel FX Dar Makas Avantajı!"
        ): extract_fx_spread,

        normalize_for_match(
            "Biz Kart Arkadaşını Getir & Kazan"
        ): extract_bizkart_invite,

        normalize_for_match(
            "Biz Kart ile Dijital Üyeliklerde %75 Nakit İade Fırsatı!"
        ): extract_digital_subscription,

        normalize_for_match(
            "Hayat Finans'la İşlem Yaptıkça Kazan!"
        ): extract_transaction_rewards,

        normalize_for_match(
            "Birikimin Büyüsün, Avantajın Bitmesin!"
        ): extract_advantage_account,

        normalize_for_match(
            "Gümüş İşlemleri Hayat FX'te!"
        ): extract_silver,

        normalize_for_match(
            "Biz Kart ile Yemek Harcamalarına 1.000 TL’ye Varan Nakit İade!"
        ): extract_food,

        normalize_for_match(
            (
                "Bana Bunu Al İş Ortağım ile "
                "Troy Mağazalarında Finansman Fırsatı!"
            )
        ): extract_troy,

        normalize_for_match(
            "Xiaomi Ürünlerinde Finansman Avantajı"
        ): extract_xiaomi,

        normalize_for_match(
            "Harcadıkça Kazan, Cebin Hep Dolu Kalsın!"
        ): extract_gastroclub,
    }

    extractor = routes.get(
        normalized_title
    )

    if extractor is None:

        raise ValueError(
            f"Bilinmeyen kampanya: {title}"
        )

    return extractor(
        record
    )


# =========================================================
# ŞEMA VALIDATION
# =========================================================

def validate_schema(record):

    errors = []

    expected_keys = set(
        EMPTY_SCHEMA.keys()
    )

    actual_keys = set(
        record.keys()
    )

    missing = (
        expected_keys
        - actual_keys
    )

    extra = (
        actual_keys
        - expected_keys
    )

    if missing:

        errors.append(
            f"Eksik alanlar: {sorted(missing)}"
        )

    if extra:

        errors.append(
            f"Fazladan alanlar: {sorted(extra)}"
        )

    list_fields = [
        "kar_payi_orani",
        "finansman_orani",
        "finansman_tutari",
        "vade",
        "taksit_sayisi",
        "masraf_bilgisi",
        "kampanya_avantaji",
        "hedef_kitle",
        "para_birimi",
        "kosullar",
    ]

    string_fields = [
        "banka",
        "kayit_turu",
        "urun_adi",
        "urun_kategorisi",
        "kampanya_turu",
        "kampanya_suresi",
        "kaynak_url",
        "ham_metin",
    ]

    for field in list_fields:

        if not isinstance(
            record.get(field),
            list
        ):

            errors.append(
                f"{field} list değil."
            )

    for field in string_fields:

        if not isinstance(
            record.get(field),
            str
        ):

            errors.append(
                f"{field} string değil."
            )

    return errors


# =========================================================
# SEMANTİK VALIDATION
# =========================================================

def validate_semantics(record):

    errors = []

    warnings = []

    title = record[
        "urun_adi"
    ]

    if record[
        "banka"
    ] != BANK_NAME:

        errors.append(
            "Banka adı yanlış."
        )

    if record[
        "kayit_turu"
    ] != "kampanya":

        errors.append(
            "kayit_turu kampanya değil."
        )

    if not record[
        "kaynak_url"
    ]:

        errors.append(
            "kaynak_url boş."
        )

    if not record[
        "ham_metin"
    ]:

        errors.append(
            "ham_metin boş."
        )

    if not record[
        "kampanya_turu"
    ]:

        errors.append(
            "kampanya_turu boş."
        )

    if not record[
        "kampanya_avantaji"
    ]:

        errors.append(
            "kampanya_avantaji boş."
        )

    # =====================================================
    # BİZ KART ARKADAŞINI GETİR - V2
    # =====================================================

    if (
        normalize_for_match(title)
        == normalize_for_match(
            "Biz Kart Arkadaşını Getir & Kazan"
        )
    ):

        expected_condition = (
            "Davet edilen müşteri en fazla "
            "5 çocuğu için Biz Kart "
            "başvurusunda bulunabilir."
        )

        if expected_condition not in record[
            "kosullar"
        ]:

            errors.append(
                (
                    "Biz Kart Arkadaşını Getir -> "
                    "en fazla 5 çocuk koşulu "
                    "structured çıktıya aktarılmadı."
                )
            )

        if len(
            record[
                "kosullar"
            ]
        ) != 4:

            errors.append(
                (
                    "Biz Kart Arkadaşını Getir -> "
                    "beklenen koşul sayısı 4, "
                    f"gerçek={len(record['kosullar'])}"
                )
            )

    # =====================================================
    # İŞLEM YAPTIKÇA KAZAN
    # =====================================================

    if (
        normalize_for_match(title)
        == normalize_for_match(
            "Hayat Finans'la İşlem Yaptıkça Kazan!"
        )
    ):

        if record[
            "urun_kategorisi"
        ]:

            errors.append(
                (
                    "İşlem Yaptıkça Kazan için "
                    "urun_kategorisi kaynakta açık "
                    "doğrulanmadığı için boş olmalı."
                )
            )

    # =====================================================
    # AVANTAJLI HESAP
    # =====================================================

    if title == (
        "Birikimin Büyüsün, Avantajın Bitmesin!"
    ):

        expected_rates = [
            "%99",
            "%95",
            "%90",
        ]

        if (
            record[
                "kar_payi_orani"
            ]
            != expected_rates
        ):

            errors.append(
                (
                    "Avantajlı Hesap kâr paylaşım "
                    "oranları yanlış."
                )
            )

        warnings.append(
            (
                "Resmi kampanya listesi doğrudan "
                "/hesaplar/avantajli-hesap sayfasına "
                "yönlendiriyor; kaynak URL korunmuştur."
            )
        )

    # =====================================================
    # TROY
    # =====================================================

    if title == (
        "Bana Bunu Al İş Ortağım ile "
        "Troy Mağazalarında Finansman Fırsatı!"
    ):

        if record[
            "finansman_tutari"
        ] != [
            "80.000 TL"
        ]:

            errors.append(
                "Troy finansman üst limiti yanlış."
            )

        if record[
            "taksit_sayisi"
        ] != [
            "3"
        ]:

            errors.append(
                "Troy taksit sayısı yanlış."
            )

    # =====================================================
    # XIAOMI
    # =====================================================

    if title == (
        "Xiaomi Ürünlerinde Finansman Avantajı"
    ):

        if record[
            "finansman_tutari"
        ] != [
            "40.000 TL"
        ]:

            errors.append(
                "Xiaomi finansman üst limiti yanlış."
            )

        if record[
            "taksit_sayisi"
        ] != [
            "3"
        ]:

            errors.append(
                "Xiaomi taksit sayısı yanlış."
            )

    # =====================================================
    # GASTROCLUB
    # =====================================================

    if title == (
        "Harcadıkça Kazan, Cebin Hep Dolu Kalsın!"
    ):

        if record[
            "kampanya_suresi"
        ]:

            errors.append(
                (
                    "GastroClub kaynakta açık tarih "
                    "olmadığı için kampanya_suresi "
                    "boş olmalı."
                )
            )

        warnings.append(
            (
                "GastroClub kaynağında açık başlangıç/"
                "bitiş tarihi bulunmuyor; "
                "kampanya_suresi boş bırakıldı."
            )
        )

    return (
        errors,
        warnings
    )


# =========================================================
# DUPLICATE
# =========================================================

def find_duplicates(
    records,
    field
):

    seen = set()

    duplicates = []

    for record in records:

        value = record.get(
            field,
            ""
        )

        key = normalize_for_match(
            value
        )

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
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 118
    )

    print(
        "HAYAT FİNANS - KAMPANYA EXTRACTOR V2"
    )

    print(
        "=" * 118
    )

    print(
        "RAW:",
        INPUT_FILE
    )

    print(
        "OUTPUT:",
        OUTPUT_FILE
    )

    raw = load_raw()

    raw_records = raw.get(
        "kampanyalar",
        []
    )

    print()

    print(
        "RAW kayıt:",
        len(raw_records)
    )

    extracted_records = []

    errors = []

    warnings = []

    # =====================================================
    # EXTRACTION
    # =====================================================

    for index, raw_record in enumerate(
        raw_records,
        start=1
    ):

        title = raw_record.get(
            "urun_adi",
            ""
        )

        print()

        print(
            "-" * 118
        )

        print(
            f"[{index}/{len(raw_records)}] {title}"
        )

        try:

            extracted = extract_record(
                raw_record
            )

            schema_errors = validate_schema(
                extracted
            )

            (
                semantic_errors,
                semantic_warnings
            ) = validate_semantics(
                extracted
            )

            for error in schema_errors:

                errors.append(
                    f"{title} -> {error}"
                )

            for error in semantic_errors:

                errors.append(
                    f"{title} -> {error}"
                )

            for warning in semantic_warnings:

                warnings.append(
                    f"{title} -> {warning}"
                )

            extracted_records.append(
                extracted
            )

            print(
                "Kategori:",
                extracted[
                    "urun_kategorisi"
                ]
                or "-"
            )

            print(
                "Kampanya türü:",
                extracted[
                    "kampanya_turu"
                ]
            )

            print(
                "Kâr payı:",
                extracted[
                    "kar_payi_orani"
                ]
            )

            print(
                "Finansman tutarı:",
                extracted[
                    "finansman_tutari"
                ]
            )

            print(
                "Vade:",
                extracted[
                    "vade"
                ]
            )

            print(
                "Taksit:",
                extracted[
                    "taksit_sayisi"
                ]
            )

            print(
                "Avantaj sayısı:",
                len(
                    extracted[
                        "kampanya_avantaji"
                    ]
                )
            )

            print(
                "Kampanya süresi:",
                extracted[
                    "kampanya_suresi"
                ]
                or "-"
            )

            print(
                "Hedef kitle:",
                extracted[
                    "hedef_kitle"
                ]
            )

            print(
                "Para birimi:",
                extracted[
                    "para_birimi"
                ]
            )

            print(
                "Koşul sayısı:",
                len(
                    extracted[
                        "kosullar"
                    ]
                )
            )

        except Exception as error:

            errors.append(
                (
                    f"{title} -> "
                    f"Extractor exception: {error}"
                )
            )

            print(
                "HATA:",
                error
            )

    # =====================================================
    # TOPLU KONTROLLER
    # =====================================================

    if len(
        extracted_records
    ) != EXPECTED_COUNT:

        errors.append(
            (
                "Extract edilen kayıt sayısı yanlış. "
                f"Beklenen={EXPECTED_COUNT}, "
                f"Gerçek={len(extracted_records)}"
            )
        )

    duplicate_urls = find_duplicates(
        extracted_records,
        "kaynak_url"
    )

    duplicate_titles = find_duplicates(
        extracted_records,
        "urun_adi"
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

    # =====================================================
    # OUTPUT
    # =====================================================

    os.makedirs(
        os.path.dirname(
            OUTPUT_FILE
        ),
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            extracted_records,
            file,
            ensure_ascii=False,
            indent=4
        )

    # =====================================================
    # FINAL RAPOR
    # =====================================================

    print()

    print(
        "=" * 118
    )

    print(
        "EXTRACTOR SONUCU"
    )

    print(
        "=" * 118
    )

    print(
        "RAW kayıt:",
        len(raw_records)
    )

    print(
        "Extract edilen:",
        len(extracted_records)
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
                "KAMPANYA EXTRACTION V2 BAŞARILI ✅"
            )
        )

    else:

        print(
            (
                "SONUÇ: HAYAT FİNANS "
                "KAMPANYA EXTRACTION V2 "
                "KONTROL GEREKİYOR ❌"
            )
        )

    print()

    print(
        "JSON:",
        OUTPUT_FILE
    )

    print(
        "=" * 118
    )


if __name__ == "__main__":
    main()