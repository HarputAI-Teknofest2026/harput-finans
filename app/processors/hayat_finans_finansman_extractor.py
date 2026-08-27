import json
import os
import re
from copy import deepcopy


# =========================================================
# AYARLAR
# =========================================================

INPUT_FILE = "data/raw/hayat_finans_finansman_urunleri.json"

OUTPUT_FILE = "data/processed/hayat_finans_finansman_extracted.json"

BANK_NAME = "Hayat Finans Katılım Bankası"

EXPECTED_COUNT = 3


# =========================================================
# ORTAK ŞEMA
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

    return value.casefold()


def clean_text(value):
    value = str(value or "")

    value = value.replace("\u00a0", " ")
    value = value.replace("\u200b", "")
    value = value.replace("\ufeff", "")

    value = value.replace("\r\n", "\n")
    value = value.replace("\r", "\n")

    value = re.sub(
        r"[ \t]+",
        " ",
        value
    )

    value = re.sub(
        r"\n{3,}",
        "\n\n",
        value
    )

    return value.strip()


def one_line(value):
    return re.sub(
        r"\s+",
        " ",
        clean_text(value)
    ).strip()


def unique_list(values):
    result = []
    seen = set()

    for value in values:

        if value is None:
            continue

        if isinstance(value, str):
            value = value.strip()

        if value == "":
            continue

        key = tr_lower(
            str(value)
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


# =========================================================
# BİRBİRİNİ KAPSAYAN KOŞULLARI TEMİZLE
# =========================================================

def remove_contained_duplicates(values):
    """
    Örnek:

    A:
    "Müşteriye limit tahsisi ... Banka finansman
    başvurularını serbestçe değerlendirme..."

    B:
    "Banka finansman başvurularını serbestçe
    değerlendirme..."

    B zaten A'nın içindeyse yalnızca A tutulur.
    """

    values = unique_list(
        [
            one_line(value)
            for value in values
            if one_line(value)
        ]
    )

    result = []

    for index, value in enumerate(values):

        value_lower = tr_lower(
            value
        )

        contained = False

        for other_index, other in enumerate(values):

            if index == other_index:
                continue

            other_lower = tr_lower(
                other
            )

            if (
                len(other_lower) > len(value_lower)
                and value_lower in other_lower
            ):
                contained = True
                break

        if not contained:
            result.append(
                value
            )

    return result


# =========================================================
# PARA NORMALİZASYONU
# =========================================================

def normalize_tl(value):
    value = one_line(
        value
    )

    match = re.search(
        r"(\d{1,3}(?:\.\d{3})+|\d+)\s*(?:TL|₺)",
        value,
        flags=re.IGNORECASE
    )

    if not match:
        return value

    amount = match.group(1)

    return f"{amount} TL"


# =========================================================
# ORAN NORMALİZASYONU
# =========================================================

def normalize_percent(value):
    value = str(
        value or ""
    ).strip()

    match = re.search(
        r"%?\s*(\d+(?:[.,]\d+)?)\s*%?",
        value
    )

    if not match:
        return value

    number = match.group(1)

    number = number.replace(
        ".",
        ","
    )

    return f"%{number}"


# =========================================================
# RAW JSON
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
# SATIR YARDIMCILARI
# =========================================================

def get_lines(text):

    return [
        one_line(line)
        for line in clean_text(
            text
        ).splitlines()
        if one_line(line)
    ]


# =========================================================
# BANA BUNU AL
# =========================================================

def extract_bana_bunu_al(record):

    result = deepcopy(
        EMPTY_SCHEMA
    )

    text = clean_text(
        record.get(
            "ham_metin",
            ""
        )
    )

    lower = tr_lower(
        text
    )

    result["banka"] = BANK_NAME

    result[
        "kayit_turu"
    ] = "finansman"

    result[
        "urun_adi"
    ] = "Bana Bunu Al"

    result[
        "urun_kategorisi"
    ] = "İhtiyaç Finansmanı"

    result[
        "kaynak_url"
    ] = record.get(
        "kaynak_url",
        ""
    )

    result[
        "ham_metin"
    ] = text

    # =====================================================
    # KÂR PAYI
    # =====================================================
    #
    # Maliyet Tablosu:
    #
    # Vade | Oran | Tahsis Ücreti |
    # Aylık Toplam | Yıllık Toplam Maliyet
    #
    # 6  | %4.25 | %0 | %5.53 | %90.66
    # 12 | %4.25 | %0 | %5.53 | %90.66
    # 18 | %4.25 | %0 | %5.53 | %90.77
    #
    # Yalnızca "Oran" kolonu alınır.
    # =====================================================

    table_rates = re.findall(
        (
            r"(?:^|\n)"
            r"\s*(?:6|12|18)"
            r"\s*\|\s*"
            r"(%\s*\d+(?:[.,]\d+)?)"
            r"\s*\|"
        ),
        text,
        flags=re.IGNORECASE
    )

    result[
        "kar_payi_orani"
    ] = unique_list(
        [
            normalize_percent(
                rate
            )
            for rate in table_rates
        ]
    )

    # =====================================================
    # FİNANSMAN TUTARI
    # =====================================================
    #
    # Gerçek ürün üst limiti = 50.000 TL
    #
    # 500 TL minimum harcama
    # 10.000 TL örnek tablo
    # 20.000 / 125.000 / 250.000 TL eşikler
    #
    # Bunlar finansman üst limiti değildir.
    # =====================================================

    max_limit_match = re.search(
        (
            r"maksimum\s+"
            r"(?:kredi\s*)?"
            r"\(?(?:finansman)?\)?\s*"
            r"limiti"
            r".{0,40}?"
            r"(\d{1,3}(?:\.\d{3})+\s*TL)"
        ),
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if max_limit_match:

        result[
            "finansman_tutari"
        ] = [
            normalize_tl(
                max_limit_match.group(1)
            )
        ]

    elif "50.000 tl" in lower:

        result[
            "finansman_tutari"
        ] = [
            "50.000 TL"
        ]

    # =====================================================
    # VADE
    # =====================================================

    if (
        "18 aya kadar"
        in lower
        or "18 aya varan"
        in lower
        or "maksimum vadesi 18 aydır"
        in lower
    ):

        result[
            "vade"
        ] = [
            "18 ay"
        ]

    # =====================================================
    # TAKSİT SAYISI - V2
    # =====================================================
    #
    # Kaynak ürün tablosunda:
    #
    # Bilgisayar | 12
    # Tablet | 6
    # Mobilya | 18
    # Havayolu / Konaklama | 18
    # Beyaz Eşya | 18
    # Elektronik | 18
    # Eğitim | 18
    # Sağlık | 18
    # Giyim | 18
    # ...
    #
    # Ayrıca:
    #
    # 20.000 TL’ye kadar cep telefonu -> 12
    # 20.000 TL üzeri cep telefonu -> 3
    #
    # Dolayısıyla kaynakta bulunan unique taksit
    # değerleri:
    #
    # 3, 6, 12, 18
    # =====================================================

    installment_values = []

    # ---------------------------------------------
    # Ürün | Taksit tablosundaki değerler
    # ---------------------------------------------

    table_installments = re.findall(
        r"(?:^|\n)[^|\n]+\|\s*(\d{1,2})\s*(?:\n|$)",
        text,
        flags=re.IGNORECASE
    )

    for value in table_installments:

        try:

            number = int(
                value
            )

        except ValueError:

            continue

        # Gerçekçi taksit değerleri
        if 1 <= number <= 60:

            installment_values.append(
                str(number)
            )

    # ---------------------------------------------
    # Cep telefonu özel sınırları
    # ---------------------------------------------

    phone_rules = [
        (
            r"20\.000\s*TL[’']?ye kadar "
            r"cep telefonu alımları\s+12",
            "12"
        ),

        (
            r"20\.000\s*TL üzeri "
            r"cep telefonu alımları\s+3",
            "3"
        ),
    ]

    for pattern, value in phone_rules:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ):

            installment_values.append(
                value
            )

    # ---------------------------------------------
    # Bilgisayar / tablet fallback
    # ---------------------------------------------

    explicit_rules = [
        (
            r"bilgisayar alımları\s+12",
            "12"
        ),

        (
            r"tablet alımları\s+6",
            "6"
        ),
    ]

    for pattern, value in explicit_rules:

        if re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        ):

            installment_values.append(
                value
            )

    # Numerik sıralama
    result[
        "taksit_sayisi"
    ] = [
        str(value)
        for value in sorted(
            {
                int(item)
                for item in installment_values
            }
        )
    ]

    # =====================================================
    # MASRAF
    # =====================================================

    if re.search(
        r"\|\s*%0\s*\|",
        text
    ):

        result[
            "masraf_bilgisi"
        ].append(
            "Tahsis Ücreti: %0"
        )

    # =====================================================
    # HEDEF KİTLE
    # =====================================================

    if (
        "bireysel ihtiyaçlarınızı"
        in lower
    ):

        result[
            "hedef_kitle"
        ].append(
            "Bireysel müşteriler"
        )

    # =====================================================
    # PARA BİRİMİ
    # =====================================================

    if (
        " tl"
        in lower
        or "tl’"
        in lower
        or "tl'"
        in lower
    ):

        result[
            "para_birimi"
        ].append(
            "TL"
        )

    # =====================================================
    # KOŞULLAR
    # =====================================================

    conditions = []

    condition_patterns = [
        (
            r"Harcama yapabileceğiniz minimum tutar "
            r"500 TL[^\n]*"
        ),

        (
            r"Limit geçerlilik süresi boyunca "
            r"limitinizi parçalı olarak ya da tek seferde "
            r"kullanabilirsiniz[^\n]*"
        ),

        (
            r"Limit geçerlilik süreniz dolmadan önce "
            r"limitiniz yeniden değerlendirilir[^\n]*"
        ),

        (
            r"Müşteriye limit tahsisi yapılmış olsa dahi,"
            r"[^\n]*"
        ),

        (
            r"Banka finansman başvurularını serbestçe "
            r"değerlendirme[^\n]*"
        ),
    ]

    for pattern in condition_patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        conditions.extend(
            matches
        )

    # =====================================================
    # KATEGORİ BAZLI TAKSİT KURALI
    # =====================================================

    category_rule = re.search(
        (
            r"20\.000 TL[’']ye kadar cep telefonu alımları "
            r"12,"
            r".{0,300}?"
            r"tablet alımları 6 taksit ile "
            r"sınırlandırılmıştır\."
        ),
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if category_rule:

        conditions.append(
            one_line(
                category_rule.group(0)
            )
        )

    # =====================================================
    # MEVZUAT VADE EŞİKLERİ
    # =====================================================
    #
    # Bunları finansman_tutari veya ana vade olarak
    # kullanmıyoruz.
    #
    # Kaynak koşulu olarak saklıyoruz.
    # =====================================================

    regulatory_rule = re.search(
        (
            r"Finansman tutarının 125\.000 TL[’']ye kadar "
            r"olması durumunda en fazla 36 ay,"
            r".{0,250}?"
            r"250\.000 TL[’']den fazla olması durumunda "
            r"en fazla 12 ay olarak belirlenmiştir\."
        ),
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if regulatory_rule:

        conditions.append(
            one_line(
                regulatory_rule.group(0)
            )
        )

    # =====================================================
    # V2:
    # Birbirini kapsayan tekrar koşulları kaldır.
    # =====================================================

    result[
        "kosullar"
    ] = remove_contained_duplicates(
        conditions
    )

    return result


# =========================================================
# BANA BUNU AL İŞ ORTAĞIM
# =========================================================

def extract_is_ortagim(record):

    result = deepcopy(
        EMPTY_SCHEMA
    )

    text = clean_text(
        record.get(
            "ham_metin",
            ""
        )
    )

    lower = tr_lower(
        text
    )

    result[
        "banka"
    ] = BANK_NAME

    result[
        "kayit_turu"
    ] = "finansman"

    result[
        "urun_adi"
    ] = "Bana Bunu Al İş Ortağım"

    result[
        "urun_kategorisi"
    ] = "İhtiyaç Finansmanı"

    result[
        "kaynak_url"
    ] = record.get(
        "kaynak_url",
        ""
    )

    result[
        "ham_metin"
    ] = text

    # =====================================================
    # KÂR PAYI
    # =====================================================
    #
    # Sayfa yalnızca:
    #
    # "avantajlı kâr oranları"
    #
    # diyor.
    #
    # Sayısal oran yok.
    # =====================================================

    result[
        "kar_payi_orani"
    ] = []

    # =====================================================
    # FİNANSMAN TUTARI
    # =====================================================

    result[
        "finansman_tutari"
    ] = []

    # =====================================================
    # VADE
    # =====================================================

    if (
        "24 aya varan"
        in lower
        or "24 aya kadar"
        in lower
    ):

        result[
            "vade"
        ] = [
            "24 ay"
        ]

    # =====================================================
    # TAKSİT
    # =====================================================

    result[
        "taksit_sayisi"
    ] = []

    # =====================================================
    # MASRAF
    # =====================================================

    result[
        "masraf_bilgisi"
    ] = []

    # =====================================================
    # HEDEF KİTLE
    # =====================================================

    if (
        "bankamız müşterisi olunmasına gerek bulunmamaktadır"
        in lower
    ):

        result[
            "hedef_kitle"
        ].append(
            "Banka müşterisi olma zorunluluğu bulunmayan başvuru sahipleri"
        )

    # =====================================================
    # KOŞULLAR
    # =====================================================

    conditions = []

    candidate_phrases = [
        (
            "İhtiyacınız olan ürün/hizmete ilişkin "
            "ihtiyaç finansmanı başvurusunu sadece "
            "kimlik belgeniz ile gerçekleştirebilir"
        ),

        (
            "İhtiyaç Kredi* başvurunuzu Hayat Finans "
            "Bana Bunu Al İş Ortağım bayimiz olan "
            "satış noktalarımızdan yapabilirsiniz"
        ),

        (
            "Bana Bunu Al İş Ortağım platformundan "
            "kredi başvurusu yapmak için Bankamız "
            "müşterisi olunmasına gerek bulunmamaktadır"
        ),

        (
            "Banka uygun görmediği kredi başvurularını "
            "serbestçe değerlendirme"
        ),
    ]

    lines = get_lines(
        text
    )

    for candidate in candidate_phrases:

        candidate_lower = tr_lower(
            candidate
        )

        for line in lines:

            if (
                candidate_lower
                in tr_lower(line)
            ):

                conditions.append(
                    line
                )

                break

    # Sözel oran bilgisi koşul olarak tutulabilir.
    for line in lines:

        lower_line = tr_lower(
            line
        )

        if (
            "avantajlı kâr oranları"
            in lower_line
            and "24 aya"
            in lower_line
        ):

            conditions.append(
                line
            )

            break

    result[
        "kosullar"
    ] = remove_contained_duplicates(
        conditions
    )

    return result


# =========================================================
# EĞİTİM FİNANSMANI
# =========================================================

def extract_education(record):

    result = deepcopy(
        EMPTY_SCHEMA
    )

    text = clean_text(
        record.get(
            "ham_metin",
            ""
        )
    )

    lower = tr_lower(
        text
    )

    result[
        "banka"
    ] = BANK_NAME

    result[
        "kayit_turu"
    ] = "finansman"

    result[
        "urun_adi"
    ] = "Eğitim Finansmanı Sistemi"

    result[
        "urun_kategorisi"
    ] = "Eğitim Finansmanı"

    result[
        "kaynak_url"
    ] = record.get(
        "kaynak_url",
        ""
    )

    result[
        "ham_metin"
    ] = text

    # =====================================================
    # KÂR PAYI
    # =====================================================
    #
    # "Vade farksız" -> %0 kâr payı olarak
    # yorumlanmaz.
    # =====================================================

    result[
        "kar_payi_orani"
    ] = []

    # =====================================================
    # FİNANSMAN TUTARI
    # =====================================================

    amount_match = re.search(
        (
            r"Eğitim finansmanı üst limiti "
            r"(\d{1,3}(?:\.\d{3})+\s*TL)"
        ),
        text,
        flags=re.IGNORECASE
    )

    if amount_match:

        result[
            "finansman_tutari"
        ] = [
            normalize_tl(
                amount_match.group(1)
            )
        ]

    elif (
        "600.000tl"
        in lower
        or "600.000 tl"
        in lower
    ):

        result[
            "finansman_tutari"
        ] = [
            "600.000 TL"
        ]

    # =====================================================
    # VADE
    # =====================================================
    #
    # 3 ay ERTELEME, vade değildir.
    # =====================================================

    result[
        "vade"
    ] = []

    result[
        "taksit_sayisi"
    ] = []

    # =====================================================
    # MASRAF
    # =====================================================

    if (
        "sigorta, kredi kartı, masraf ya da vade farkı alınmamaktadır"
        in lower
    ):

        result[
            "masraf_bilgisi"
        ].append(
            "Sigorta, kredi kartı, masraf veya vade farkı alınmamaktadır."
        )

    # =====================================================
    # HEDEF KİTLE
    # =====================================================

    result[
        "hedef_kitle"
    ].append(
        "Eğitim finansmanı başvurusu yapan bireysel müşteriler"
    )

    # =====================================================
    # PARA BİRİMİ
    # =====================================================

    if (
        "600.000tl"
        in lower
        or "600.000 tl"
        in lower
    ):

        result[
            "para_birimi"
        ].append(
            "TL"
        )

    # =====================================================
    # KOŞULLAR
    # =====================================================

    conditions = []

    lines = get_lines(
        text
    )

    condition_keywords = [
        "3 ay erteleme",
        "gelir belgesi",
        "yalnızca kimlik belgenizle",
        "masraf ya da vade farkı alınmamaktadır",
        "kampanya aşağıda belirtilen kurumlarda geçerlidir",
        "kampanyayı dilediği zaman durdurma",
    ]

    for line in lines:

        lower_line = tr_lower(
            line
        )

        if any(
            tr_lower(keyword)
            in lower_line
            for keyword in condition_keywords
        ):

            if (
                "hemen avantajlı olmak için tıklayın"
                in lower_line
            ):

                continue

            conditions.append(
                line
            )

    result[
        "kosullar"
    ] = remove_contained_duplicates(
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
    ).strip()

    if title == "Bana Bunu Al":

        return extract_bana_bunu_al(
            record
        )

    if title == "Bana Bunu Al İş Ortağım":

        return extract_is_ortagim(
            record
        )

    if title == "Eğitim Finansmanı Sistemi":

        return extract_education(
            record
        )

    raise ValueError(
        f"Bilinmeyen finansman ürünü: {title}"
    )


# =========================================================
# ŞEMA KONTROLÜ
# =========================================================

def validate_schema(record):

    errors = []

    expected_keys = list(
        EMPTY_SCHEMA.keys()
    )

    actual_keys = list(
        record.keys()
    )

    missing = [
        key
        for key in expected_keys
        if key not in record
    ]

    extra = [
        key
        for key in actual_keys
        if key not in EMPTY_SCHEMA
    ]

    if missing:

        errors.append(
            f"Eksik alanlar: {missing}"
        )

    if extra:

        errors.append(
            f"Fazladan alanlar: {extra}"
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

    # =====================================================
    # ORTAK
    # =====================================================

    if (
        record["banka"]
        != BANK_NAME
    ):

        errors.append(
            "Banka adı yanlış."
        )

    if (
        record["kayit_turu"]
        != "finansman"
    ):

        errors.append(
            "kayit_turu finansman değil."
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

    # =====================================================
    # BANA BUNU AL
    # =====================================================

    if title == "Bana Bunu Al":

        if (
            record[
                "urun_kategorisi"
            ]
            != "İhtiyaç Finansmanı"
        ):

            errors.append(
                "Ürün kategorisi yanlış."
            )

        if (
            record[
                "kar_payi_orani"
            ]
            != [
                "%4,25"
            ]
        ):

            errors.append(
                (
                    "Kâr payı oranı yanlış. "
                    f"Gerçek={record['kar_payi_orani']}"
                )
            )

        if (
            record[
                "finansman_tutari"
            ]
            != [
                "50.000 TL"
            ]
        ):

            errors.append(
                (
                    "Finansman tutarı yanlış. "
                    f"Gerçek={record['finansman_tutari']}"
                )
            )

        if (
            record[
                "vade"
            ]
            != [
                "18 ay"
            ]
        ):

            errors.append(
                (
                    "Vade yanlış. "
                    f"Gerçek={record['vade']}"
                )
            )

        # V2: Taksite 18 de dahil olmalı.
        expected_installments = [
            "3",
            "6",
            "12",
            "18"
        ]

        if (
            record[
                "taksit_sayisi"
            ]
            != expected_installments
        ):

            errors.append(
                (
                    "Taksit sayıları yanlış. "
                    f"Beklenen={expected_installments}, "
                    f"Gerçek={record['taksit_sayisi']}"
                )
            )

        forbidden_amounts = {
            "500 TL",
            "10.000 TL",
            "20.000 TL",
            "125.000 TL",
            "250.000 TL",
        }

        polluted_amounts = [
            value
            for value
            in record[
                "finansman_tutari"
            ]
            if value
            in forbidden_amounts
        ]

        if polluted_amounts:

            errors.append(
                (
                    "Finansman tutarına alakasız "
                    f"rakam girmiş: {polluted_amounts}"
                )
            )

        forbidden_rates = {
            "%0",
            "%5,53",
            "%90,66",
            "%90,77",
        }

        polluted_rates = [
            value
            for value
            in record[
                "kar_payi_orani"
            ]
            if value
            in forbidden_rates
        ]

        if polluted_rates:

            errors.append(
                (
                    "Kâr payına maliyet/tahsis oranı "
                    f"karışmış: {polluted_rates}"
                )
            )

        # Koşullarda birbirini kapsayan tekrar var mı?
        conditions = record[
            "kosullar"
        ]

        for index, condition in enumerate(
            conditions
        ):

            for other_index, other in enumerate(
                conditions
            ):

                if index == other_index:
                    continue

                condition_lower = tr_lower(
                    condition
                )

                other_lower = tr_lower(
                    other
                )

                if (
                    len(other_lower)
                    > len(condition_lower)
                    and condition_lower
                    in other_lower
                ):

                    errors.append(
                        (
                            "Koşullarda birbirini kapsayan "
                            f"tekrar bulundu: {condition}"
                        )
                    )

    # =====================================================
    # İŞ ORTAĞIM
    # =====================================================

    elif title == "Bana Bunu Al İş Ortağım":

        if record[
            "kar_payi_orani"
        ]:

            errors.append(
                (
                    "İş Ortağım sayfasında sayısal "
                    "kâr oranı yok; [] olmalı."
                )
            )

        if record[
            "finansman_tutari"
        ]:

            errors.append(
                (
                    "İş Ortağım sayfasında sayısal "
                    "finansman tutarı yok."
                )
            )

        if (
            record[
                "vade"
            ]
            != [
                "24 ay"
            ]
        ):

            errors.append(
                (
                    "İş Ortağım vadesi yanlış. "
                    f"Gerçek={record['vade']}"
                )
            )

        warnings.append(
            (
                "Sayfada 'avantajlı kâr oranları' "
                "ifadesi var fakat sayısal oran yok; "
                "[] bırakıldı."
            )
        )

    # =====================================================
    # EĞİTİM
    # =====================================================

    elif title == "Eğitim Finansmanı Sistemi":

        if (
            record[
                "finansman_tutari"
            ]
            != [
                "600.000 TL"
            ]
        ):

            errors.append(
                (
                    "Eğitim finansmanı limiti yanlış. "
                    f"Gerçek={record['finansman_tutari']}"
                )
            )

        if record[
            "vade"
        ]:

            errors.append(
                (
                    "3 ay erteleme vade değildir; "
                    "vade [] olmalı."
                )
            )

        if record[
            "kar_payi_orani"
        ]:

            errors.append(
                (
                    "'Vade farksız' ifadesinden "
                    "sayısal kâr payı üretilmemeli."
                )
            )

        for condition in record[
            "kosullar"
        ]:

            if (
                "hemen avantajlı olmak için tıklayın"
                in tr_lower(condition)
            ):

                errors.append(
                    "CTA koşullara karışmış."
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

        value = tr_lower(
            record.get(
                field,
                ""
            )
        ).strip()

        if value in seen:

            duplicates.append(
                record.get(
                    field,
                    ""
                )
            )

        seen.add(
            value
        )

    return duplicates


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "=" * 110
    )

    print(
        "HAYAT FİNANS - FİNANSMAN EXTRACTOR V2"
    )

    print(
        "=" * 110
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
        "urunler",
        []
    )

    print()

    print(
        "RAW kayıt:",
        len(raw_records)
    )

    extracted_records = []

    all_errors = []

    all_warnings = []

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
            "-" * 110
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
                warnings
            ) = validate_semantics(
                extracted
            )

            for error in schema_errors:

                all_errors.append(
                    f"{title} -> {error}"
                )

            for error in semantic_errors:

                all_errors.append(
                    f"{title} -> {error}"
                )

            for warning in warnings:

                all_warnings.append(
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
                "Masraf:",
                extracted[
                    "masraf_bilgisi"
                ]
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

            all_errors.append(
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

    if (
        len(extracted_records)
        != EXPECTED_COUNT
    ):

        all_errors.append(
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

        all_errors.append(
            (
                "Duplicate URL bulundu: "
                f"{duplicate_urls}"
            )
        )

    if duplicate_titles:

        all_errors.append(
            (
                "Duplicate ürün adı bulundu: "
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
        "=" * 110
    )

    print(
        "EXTRACTOR SONUCU"
    )

    print(
        "=" * 110
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
        len(all_warnings)
    )

    print(
        "Error:",
        len(all_errors)
    )

    if all_warnings:

        print()

        print(
            "UYARILAR:"
        )

        for warning in all_warnings:

            print(
                "-",
                warning
            )

    if all_errors:

        print()

        print(
            "HATALAR:"
        )

        for error in all_errors:

            print(
                "-",
                error
            )

    print()

    if not all_errors:

        print(
            (
                "SONUÇ: HAYAT FİNANS "
                "FİNANSMAN EXTRACTION V2 BAŞARILI ✅"
            )
        )

    else:

        print(
            (
                "SONUÇ: HAYAT FİNANS "
                "FİNANSMAN EXTRACTION V2 "
                "KONTROL GEREKİYOR ❌"
            )
        )

    print()

    print(
        "JSON:",
        OUTPUT_FILE
    )

    print(
        "=" * 110
    )


if __name__ == "__main__":
    main()