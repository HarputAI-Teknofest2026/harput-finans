import json
import os
import re


# =========================================================
# DOSYALAR
# =========================================================

INPUT_FILE = "data/raw/turkiye_finans_kampanyalar.json"

OUTPUT_FILE = (
    "data/processed/"
    "turkiye_finans_kampanya_extracted.json"
)

BANK_NAME = "Türkiye Finans Katılım Bankası"


# =========================================================
# ORTAK ŞEMA
# =========================================================

REQUIRED_FIELDS = [
    "banka",
    "kayit_turu",
    "urun_adi",
    "urun_kategorisi",

    "kar_payi_orani",
    "finansman_orani",
    "finansman_tutari",
    "vade",
    "taksit_sayisi",

    "masraf_bilgisi",

    "kampanya_turu",
    "kampanya_avantaji",
    "kampanya_suresi",

    "hedef_kitle",
    "para_birimi",
    "kosullar",

    "kaynak_url",
    "ham_metin"
]


LIST_FIELDS = [
    "kar_payi_orani",
    "finansman_orani",
    "finansman_tutari",
    "vade",
    "taksit_sayisi",
    "masraf_bilgisi",
    "kampanya_avantaji",
    "hedef_kitle",
    "para_birimi",
    "kosullar"
]


# =========================================================
# KATEGORİ HARİTASI
# =========================================================

CATEGORY_MAP = {
    "finansman kampanyaları": "Finansman Kampanyası",
    "kredi kartı kampanyaları": "Kredi Kartı Kampanyası",
    "dijital bankacılık kampanyaları": "Dijital Bankacılık Kampanyası",
    "maaş ödemesi kampanyaları": "Maaş / Promosyon Kampanyası",
    "yatırım kampanyaları": "Yatırım Kampanyası",
    "birikim/fon kampanyaları": "Birikim / Hesap Kampanyası",
    "sigorta kampanyaları": "Sigorta / BES Kampanyası",
    "diğer kampanyalar": "Diğer Kampanya"
}


# =========================================================
# NORMALİZASYON
# =========================================================

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


def remove_invisible(value):

    value = str(
        value or ""
    )

    for char in [
        "\u200b",
        "\u200c",
        "\u200d",
        "\u2060",
        "\ufeff",
        "\u00ad"
    ]:

        value = value.replace(
            char,
            ""
        )

    return value


def normalize_spaces(value):

    return re.sub(
        r"\s+",
        " ",
        remove_invisible(
            value
        )
    ).strip()


def unique(items):

    result = []

    seen = set()

    for item in items:

        item = normalize_spaces(
            item
        )

        if not item:

            continue

        key = tr_lower(
            item
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        result.append(
            item
        )

    return result


def contains_any(
    text,
    keywords
):

    lower = tr_lower(
        text
    )

    return any(
        tr_lower(
            keyword
        )
        in lower

        for keyword
        in keywords
    )


# =========================================================
# YÜZDE NORMALİZASYONU
# =========================================================

def normalize_percent(value):

    value = normalize_spaces(
        value
    )

    match = re.fullmatch(
        r"%\s*(\d+(?:[.,]\d+)?)",
        value
    )

    if match:

        return (
            "%"
            + match.group(1).replace(
                ".",
                ","
            )
        )

    match = re.fullmatch(
        r"(\d+(?:[.,]\d+)?)\s*%",
        value
    )

    if match:

        return (
            "%"
            + match.group(1).replace(
                ".",
                ","
            )
        )

    return value


# =========================================================
# SATIRLAR
# =========================================================

FOOTER_LINES = {
    "Başvuru Merkezi",
    "Hesaplama Araçları",
    "Müşteri Memnuniyet Merkezi",
    "Yatırımcı İlişkileri",
    "Finans Portalı",
    "Satılık Gayrimenkuller",
    "Türkiye Finans Linkleri",
    "Türkiye Finans Blog",
    "Son Gezdiklerim"
}


def get_lines(text):

    result = []

    for raw_line in str(
        text or ""
    ).splitlines():

        line = normalize_spaces(
            raw_line
        )

        if not line:

            continue

        if line in FOOTER_LINES:

            continue

        result.append(
            line
        )

    return result


def sentence_units(text):

    result = []

    for line in get_lines(
        text
    ):

        parts = re.split(
            (
                r"(?<=[!?])\s+"
                r"|"
                r"(?<=[A-Za-zÇĞİÖŞÜçğıöşü])"
                r"\.\s+"
            ),
            line
        )

        for part in parts:

            part = normalize_spaces(
                part
            )

            if part:

                result.append(
                    part
                )

    return result


# =========================================================
# BAŞLIK / SORU MU?
# =========================================================

def is_heading_like(text):

    text = normalize_spaces(
        text
    )

    lower = tr_lower(
        text
    )

    if not text:

        return True

    if text.endswith(
        "?"
    ):

        return True

    if (
        text.endswith(":")
        and len(text) < 200
    ):

        return True

    heading_phrases = [
        "kampanya nedir",
        "kampanyası nedir",
        "avantajları nelerdir",
        "kimler yararlanabilir",
        "hangi tarihler arasında",
        "nasıl yararlan",
        "nasıl katıl",
        "nasıl başvur",
        "kampanya koşulları"
    ]

    if (
        len(text) < 200
        and any(
            phrase in lower

            for phrase
            in heading_phrases
        )
    ):

        return True

    # Kısa, rakamsız, fiilsiz menü/başlık
    if (
        len(text) < 80
        and not re.search(
            r"\d|%|₺",
            text
        )
        and not any(
            verb in lower

            for verb in [
                "yararlan",
                "kazan",
                "öde",
                "kullan",
                "sunul",
                "uygulan",
                "alın",
                "veril"
            ]
        )
        and not text.endswith(
            "."
        )
    ):

        return True

    return False


# =========================================================
# KATEGORİ
# =========================================================

def detect_product_category(
    raw_category
):

    key = tr_lower(
        normalize_spaces(
            raw_category
        )
    )

    return CATEGORY_MAP.get(
        key,
        "Diğer Kampanya"
    )


# =========================================================
# KAMPANYA TÜRÜ
# =========================================================

def detect_campaign_type(
    raw_category,
    title
):

    category = tr_lower(
        raw_category
    )

    title_lower = tr_lower(
        title
    )

    if (
        "emekli"
        in title_lower
    ):

        return "Emekli Promosyonu"

    if (
        title_lower.startswith(
            "bes "
        )
        or title_lower.startswith(
            "bes ile"
        )
    ):

        return "BES Kampanyası"

    if (
        "bereket sigorta"
        in title_lower
        and "çalışan"
        in title_lower
    ):

        return "Çalışan Avantaj Paketi"

    if (
        "avantajlı bankacılıkla"
        in title_lower
    ):

        return "Bankacılık Avantaj Paketi"

    if (
        "kazancı bol hoş geldin"
        in title_lower
    ):

        return "Hoş Geldin / Bonus Paketi"

    if (
        "masrafsız bankacılık"
        in title_lower
    ):

        return "Bankacılık Avantajı"

    if (
        "katılım hesab"
        in title_lower
        or "günlük hesap"
        in title_lower
    ):

        return "Hesap / Getiri Kampanyası"

    if (
        "yatırım"
        in category
        or "yatırım hesab"
        in title_lower
    ):

        return "Yatırım Kampanyası"

    if (
        "maaş müşterilerine"
        in title_lower
    ):

        return (
            "Maaş Müşterisi "
            "Avantaj Kampanyası"
        )

    if (
        "finansman"
        in category
        or "finansman"
        in title_lower
    ):

        return "Finansman Kampanyası"

    if any(
        phrase
        in title_lower

        for phrase
        in [
            "bonus",
            "ödül",
            "fırsat"
        ]
    ):

        return "Bonus / Ödül Kampanyası"

    if (
        "maaş"
        in category
    ):

        return "Maaş / Promosyon Kampanyası"

    if (
        "sigorta"
        in category
    ):

        return "Sigorta Kampanyası"

    if (
        "dijital"
        in category
    ):

        return "Dijital Bankacılık Kampanyası"

    return "Diğer Kampanya"


# =========================================================
# DOĞRUDAN FİNANSMAN KAMPANYASI
# =========================================================

def is_direct_finance_campaign(
    raw_category,
    title
):

    return (
        "finansman"
        in tr_lower(
            raw_category
        )
        or
        "finansman"
        in tr_lower(
            title
        )
    )


# =========================================================
# HESAP / GETİRİ
# =========================================================

def is_account_campaign(
    raw_category,
    title
):

    category = tr_lower(
        raw_category
    )

    title_lower = tr_lower(
        title
    )

    return (
        "birikim/fon"
        in category
        or "katılım hesab"
        in title_lower
        or "günlük hesap"
        in title_lower
    )


# =========================================================
# PARA BİRİMİ
# =========================================================

def extract_currency(text):

    result = []

    if re.search(
        r"\bTL\b|₺|Türk\s+Lirası",
        text,
        flags=re.IGNORECASE
    ):

        result.append(
            "TRY"
        )

    if re.search(
        r"\bUSD\b|ABD\s+Doları",
        text,
        flags=re.IGNORECASE
    ):

        result.append(
            "USD"
        )

    if re.search(
        r"\bEUR\b|\bEuro\b|\bAvro\b",
        text,
        flags=re.IGNORECASE
    ):

        result.append(
            "EUR"
        )

    return result


# =========================================================
# KAMPANYA SÜRESİ
# =========================================================

def extract_campaign_period(
    raw_record
):

    start = normalize_spaces(
        raw_record.get(
            "kampanya_baslangic_tarihi",
            ""
        )
    )

    end = normalize_spaces(
        raw_record.get(
            "kampanya_bitis_tarihi",
            ""
        )
    )

    if start and end:

        return (
            f"{start} - {end}"
        )

    if end:

        return (
            f"{end} tarihine kadar"
        )

    if start:

        return (
            f"{start} tarihinden itibaren"
        )

    validity_lines = raw_record.get(
        "tarih_kaynak_satirlari",
        []
    )

    if validity_lines:

        return normalize_spaces(
            validity_lines[0]
        )

    return ""


# =========================================================
# MALİYET TABLOLARI
# =========================================================

def extract_rate_tables(text):

    lines = get_lines(
        text
    )

    rates = []

    fees = []

    current_table = ""

    for index, line in enumerate(
        lines
    ):

        lower = tr_lower(
            line
        )

        if (
            "maliyet tablosu"
            in lower
        ):

            current_table = line

            continue

        if lower != "vade":

            continue

        header_window = [
            tr_lower(
                item
            )

            for item
            in lines[
                index + 1:
                index + 6
            ]
        ]

        has_rate_header = any(
            (
                "kâr payı oranı"
                in item
                or "kar oranı"
                in item
                or "kâr oranı"
                in item
                or "kar payı oranı"
                in item
            )

            for item
            in header_window
        )

        if not has_rate_header:

            continue

        cursor = index + 1

        while (
            cursor < len(lines)

            and (
                "oran"
                in tr_lower(
                    lines[cursor]
                )
                or "tahsis"
                in tr_lower(
                    lines[cursor]
                )
                or "maliyet"
                in tr_lower(
                    lines[cursor]
                )
            )
        ):

            cursor += 1

        while (
            cursor + 4
            < len(lines)
        ):

            vade_line = lines[
                cursor
            ]

            if not re.fullmatch(
                r"\d{1,3}",
                vade_line
            ):

                break

            rate = lines[
                cursor + 1
            ]

            fee = lines[
                cursor + 2
            ]

            monthly = lines[
                cursor + 3
            ]

            yearly = lines[
                cursor + 4
            ]

            percent_pattern = (
                r"%?\s*"
                r"\d+(?:[.,]\d+)?"
                r"\s*%"
            )

            if not all(
                re.fullmatch(
                    percent_pattern,
                    value
                )

                for value
                in [
                    rate,
                    fee,
                    monthly,
                    yearly
                ]
            ):

                break

            table_name = (
                current_table
                or "Maliyet Tablosu"
            )

            rates.append(
                (
                    f"{table_name} | "
                    f"{vade_line} ay: "
                    f"{normalize_percent(rate)}"
                )
            )

            fees.append(
                (
                    f"{table_name} | "
                    f"Tahsis Ücreti: "
                    f"{normalize_percent(fee)}"
                )
            )

            cursor += 5

    return (
        unique(rates),
        unique(fees)
    )


# =========================================================
# AÇIK KÂR PAYI
# =========================================================

def extract_explicit_profit_rates(
    text
):

    results = []

    for unit in sentence_units(
        text
    ):

        if is_heading_like(
            unit
        ):

            continue

        lower = tr_lower(
            unit
        )

        if not (
            "kâr pay"
            in lower
            or "kar pay"
            in lower
        ):

            continue

        if not re.search(
            (
                r"%\s*"
                r"\d+(?:[.,]\d+)?"
                r"|"
                r"\d+(?:[.,]\d+)?\s*%"
            ),
            unit
        ):

            continue

        results.append(
            unit
        )

    return unique(
        results
    )


# =========================================================
# HESAP KÂR PAYLAŞIM ORANI
# =========================================================

def extract_account_profit_sharing(
    text
):

    results = []

    for unit in sentence_units(
        text
    ):

        lower = tr_lower(
            unit
        )

        if not (
            "kâr paylaşım oran"
            in lower
            or "kar paylaşım oran"
            in lower
        ):

            continue

        if not re.search(
            r"\b\d{1,3}\s*/\s*\d{1,3}\b",
            unit
        ):

            continue

        results.append(
            unit
        )

    return unique(
        results
    )


def extract_profit_rates(
    text,
    direct_finance,
    account_campaign
):

    result = []

    if direct_finance:

        (
            table_rates,
            _
        ) = extract_rate_tables(
            text
        )

        result.extend(
            table_rates
        )

        result.extend(
            extract_explicit_profit_rates(
                text
            )
        )

    elif account_campaign:

        result.extend(
            extract_account_profit_sharing(
                text
            )
        )

    return unique(
        result
    )[:40]


# =========================================================
# FİNANSMAN ORANI
# =========================================================

def extract_finance_ratio(
    text,
    direct_finance
):

    if not direct_finance:

        return []

    results = []

    for unit in sentence_units(
        text
    ):

        if is_heading_like(
            unit
        ):

            continue

        if "%" not in unit:

            continue

        if contains_any(
            unit,
            [
                "kâr pay",
                "kar pay",
                "maliyet",
                "tahsis",
                "bonus",
                "indirim"
            ]
        ):

            continue

        if contains_any(
            unit,
            [
                "finansman oranı",
                "oranında finansman",
                "finansman desteği oranı"
            ]
        ):

            results.append(
                unit
            )

    return unique(
        results
    )[:15]


# =========================================================
# PARA VAR MI?
# =========================================================

def has_money(text):

    return bool(
        re.search(
            (
                r"\b"
                r"\d[\d.,]*"
                r"\s*"
                r"(?:bin\s+)?"
                r"TL\b"
            ),
            text,
            flags=re.IGNORECASE
        )
    )


# =========================================================
# FİNANSMAN TUTARI - V3
# =========================================================

def extract_finance_amount(
    text,
    direct_finance
):

    if not direct_finance:

        return []

    results = []

    for unit in sentence_units(
        text
    ):

        if is_heading_like(
            unit
        ):

            continue

        lower = tr_lower(
            unit
        )

        if not has_money(
            unit
        ):

            continue

        if (
            "finansman"
            not in lower
        ):

            continue

        # -------------------------------------------------
        # MALİYET TABLOSU BAŞLIKLARI
        # -------------------------------------------------

        if contains_any(
            unit,
            [
                "maliyet tablosu",
                "ürün hizmet ücretleri",
                "urun hizmet ucretleri",
                "kar payı oranları ürün",
                "kâr payı oranları ürün",
                "kar payı oranları urun"
            ]
        ):

            continue

        # -------------------------------------------------
        # GENEL VADE REGÜLASYON EŞİKLERİ
        # finansman_tutari değildir
        # -------------------------------------------------

        if (
            (
                "finansman tutarının"
                in lower
                or "finansman tutarı;"
                in lower
            )
            and contains_any(
                unit,
                [
                    "maksimum vade",
                    "vade 36",
                    "vade 24",
                    "vade 12",
                    "ayı aşamaz"
                ]
            )
        ):

            continue

        if contains_any(
            unit,
            [
                "örnek ödeme tablosu",
                "örnek hesaplama",
                "baz alınarak oluşturulan",
                "aylık toplam maliyet",
                "yıllık toplam maliyet"
            ]
        ):

            continue

        # -------------------------------------------------
        # GERÇEK TUTAR İFADESİ
        # -------------------------------------------------

        has_amount_relation = contains_any(
            unit,
            [
                "kadar",
                "varan",
                "arasında",
                "finansman başvurusu",
                "finansmanından yararlan"
            ]
        )

        if not has_amount_relation:

            continue

        results.append(
            unit
        )

    return unique(
        results
    )[:12]


# =========================================================
# VADE - V3
# =========================================================

def extract_term(
    text,
    title,
    direct_finance
):

    results = []

    time_pattern = re.compile(
        (
            r"\b"
            r"\d{1,3}"
            r"(?:\s*[-–—]\s*\d{1,3})?"
            r"\s*"
            r"(?:"
            r"ay"
            r"|aya"
            r"|ayı"
            r"|aylık"
            r"|aydır"
            r"|gün"
            r"|gündür"
            r"|günlük"
            r")"
            r"\b"
        ),
        flags=re.IGNORECASE
    )

    special_50k_campaign = (
        direct_finance
        and "50.000"
        in title
    )

    for unit in sentence_units(
        text
    ):

        lower = tr_lower(
            unit
        )

        if (
            "vade"
            not in lower
        ):

            continue

        if contains_any(
            unit,
            [
                "erken ödeme",
                "kalan vade",
                "tazminat"
            ]
        ):

            continue

        if not time_pattern.search(
            unit
        ):

            continue

        # 50 bin TL kampanyasına ait olmayan
        # genel 125/250 bin TL regülasyon satırlarını at.
        if (
            special_50k_campaign
            and (
                "125.000"
                in unit
                or "250.000"
                in unit
            )
        ):

            continue

        results.append(
            unit
        )

    return unique(
        results
    )[:20]


# =========================================================
# TAKSİT
# =========================================================

def extract_installments(text):

    results = []

    pattern = re.compile(
        (
            r"\b"
            r"\d{1,3}"
            r"\s*"
            r"taksit"
            r"(?:e|le|li)?"
            r"\b"
        ),
        flags=re.IGNORECASE
    )

    for unit in sentence_units(
        text
    ):

        if is_heading_like(
            unit
        ):

            continue

        lower = tr_lower(
            unit
        )

        if (
            "taksit"
            not in lower
        ):

            continue

        if contains_any(
            unit,
            [
                "taksit tutarı",
                "ilk taksitte tahsil",
                "aylık maksimum taksit"
            ]
        ):

            continue

        if not pattern.search(
            unit
        ):

            continue

        results.append(
            unit
        )

    return unique(
        results
    )[:15]


# =========================================================
# MASRAF
# =========================================================

def extract_expenses(
    text,
    table_fees
):

    results = []

    keywords = [
        "tahsis ücreti",
        "dosya masrafsız",
        "masrafsız finansman",
        "masrafsız bankacılık",
        "ücretsiz eft",
        "ücretsiz havale",
        "ücretsiz fast",
        "komisyon ödemeden",
        "sıfır komisyon",
        "komisyon oranı"
    ]

    for unit in sentence_units(
        text
    ):

        if is_heading_like(
            unit
        ):

            continue

        lower = tr_lower(
            unit
        )

        if not any(
            tr_lower(keyword)
            in lower

            for keyword
            in keywords
        ):

            continue

        if (
            len(unit) < 55
            and not re.search(
                r"\d|%|ücretsiz|ödemeden",
                lower
            )
        ):

            continue

        results.append(
            unit
        )

    results.extend(
        table_fees
    )

    return unique(
        results
    )[:20]


# =========================================================
# AVANTAJ - V3
# =========================================================

def extract_advantages(
    text,
    direct_finance
):

    results = []

    keywords = [
        "bonus",
        "nakit ödül",
        "nakit odul",
        "promosyon",
        "indirim",
        "kâr paysız",
        "kar paysız",
        "masrafsız",
        "ücretsiz",
        "sıfır komisyon",
        "komisyon ödemeden",
        "öteleme",
        "taksit",
        "hoş geldin",
        "avantajlı getiri",
        "yüksek getiri",
        "kâr paylaşım oran",
        "kar paylaşım oran"
    ]

    benefit_patterns = [
        r"\bkazan",
        r"\byararlan",
        r"\bfaydalan",
        r"\bsunul",
        r"\buygulan",
        r"\böden",
        r"\byüklen",
        r"\bkullan",
        r"\bçek",
        r"\byatır"
    ]

    for unit in sentence_units(
        text
    ):

        if is_heading_like(
            unit
        ):

            continue

        if len(
            unit
        ) > 500:

            continue

        lower = tr_lower(
            unit
        )

        if not any(
            tr_lower(keyword)
            in lower

            for keyword
            in keywords
        ):

            continue

        # -------------------------------------------------
        # AÇIK KİRLİLİK
        # -------------------------------------------------

        if contains_any(
            unit,
            [
                "örnek hesaplama tabloları",
                "örnek ödeme tabloları",
                "yazım hataları",
                "değişiklik yapma hakkını",
                "kampanya koşullarını değiştirme"
            ]
        ):

            continue

        if (
            unit.startswith(
                "’nden"
            )
            or unit.startswith(
                "'nden"
            )
        ):

            continue

        # Finansman kampanyasının içindeki unrelated
        # Yedek Hesap çapraz satırlarını at.
        if (
            direct_finance
            and (
                "yedek hesap"
                in lower
                or (
                    "2.500 tl"
                    in lower
                    and "ihtiyaç finansman"
                    not in lower
                )
            )
        ):

            continue

        # Tahsis ücreti/maliyet açıklaması avantaj değildir.
        if (
            "tahsis ücreti"
            in lower
            and "indirim"
            in lower
        ):

            continue

        has_value = bool(
            re.search(
                r"\d|%|TL|₺",
                unit,
                flags=re.IGNORECASE
            )
        )

        has_benefit = any(
            re.search(
                pattern,
                lower
            )

            for pattern
            in benefit_patterns
        )

        if not (
            has_value
            or has_benefit
        ):

            continue

        results.append(
            unit
        )

    return unique(
        results
    )[:20]


# =========================================================
# HEDEF KİTLE - V3
# =========================================================

def extract_target_audience(text):

    results = []

    strong_patterns = [
        r"bireysel.{0,120}müşter.{0,120}"
        r"(?:yararlanabilir|geçerlidir|faydalanabilir)",

        r"emekli.{0,120}müşter.{0,120}"
        r"(?:yararlanabilir|geçerlidir|faydalanabilir)",

        r"maaş.{0,160}müşter.{0,120}"
        r"(?:yararlanabilir|geçerlidir|faydalanabilir)",

        r"maaş ödemesini.{0,180}"
        r"(?:müşter|türkiye finans).{0,100}"
        r"yararlanabilir",

        r"banka çalışan.{0,160}"
        r"(?:yararlanabilir|geçerlidir)",

        r"kamu çalışan.{0,160}"
        r"(?:yararlanabilir|geçerlidir)",

        r"bereket sigorta çalışan.{0,180}"
        r"(?:yararlanabilir|geçerlidir)",

        r"tüketici vasf.{0,120}"
        r"(?:yararlanabilir|faydalanabilir)",

        r"kredi kart.{0,160}"
        r"(?:sahip|sahibi).{0,120}"
        r"(?:müşter|yararlanabilir)",

        r"tüm müşterilerimiz.{0,120}"
        r"yararlanabilir",

        r"bireysel ve şahıs firması müşteriler"
        r".{0,120}geçerlidir",

        r"yalnızca.{0,120}müşter.{0,120}"
        r"geçerlidir",

        r"sadece.{0,120}müşter.{0,120}"
        r"geçerlidir",

        r"yeni müşter.{0,160}"
        r"(?:yararlanabilir|geçerlidir|faydalanabilir)"
    ]

    compiled_patterns = [
        re.compile(
            pattern,
            flags=re.IGNORECASE
        )

        for pattern
        in strong_patterns
    ]

    for unit in sentence_units(
        text
    ):

        if is_heading_like(
            unit
        ):

            continue

        if len(
            unit
        ) > 600:

            continue

        lower = tr_lower(
            unit
        )

        if contains_any(
            unit,
            [
                "müşteri iletişim merkezi",
                "0850 222",
                "yazım hataları",
                "değişiklik yapma hakkını"
            ]
        ):

            continue

        if (
            "yararlanamam"
            in lower
            or "faydalanamam"
            in lower
        ):

            continue

        if any(
            pattern.search(
                unit
            )

            for pattern
            in compiled_patterns
        ):

            results.append(
                unit
            )

    return unique(
        results
    )[:15]


# =========================================================
# KOŞULLAR
# =========================================================

def extract_conditions(text):

    lines = get_lines(
        text
    )

    results = []

    start_index = None

    for index, line in enumerate(
        lines
    ):

        if (
            tr_lower(line)
            == "kampanya koşulları"
        ):

            start_index = index + 1

            break

    if start_index is not None:

        for line in lines[
            start_index:
        ]:

            lower = tr_lower(
                line
            )

            if (
                "maliyet tablosu"
                in lower
            ):

                break

            if contains_any(
                line,
                [
                    "Başvuru Merkezi",
                    "Hesaplama Araçları",
                    "Müşteri Memnuniyet",
                    "Yatırımcı İlişkileri",
                    "Türkiye Finans Blog",
                    "Sıkça Ziyaret Edilen Sayfalar"
                ]
            ):

                break

            if len(
                line
            ) < 15:

                continue

            results.append(
                line
            )

    if not results:

        keywords = [
            "gerekmektedir",
            "geçerlidir",
            "yararlanabilir",
            "faydalanabilir",
            "kampanya kapsamında",
            "kampanyaya dahil",
            "kampanyaya katıl",
            "minimum",
            "maksimum",
            "en fazla",
            "en az",
            "sınırlıdır",
            "kullanılmayan",
            "iade ve iptal",
            "birleştirilemez"
        ]

        for unit in sentence_units(
            text
        ):

            lower = tr_lower(
                unit
            )

            if any(
                tr_lower(keyword)
                in lower

                for keyword
                in keywords
            ):

                results.append(
                    unit
                )

    cleaned = []

    for item in results:

        if contains_any(
            item,
            [
                "web sayfaları, e-posta",
                "yazım hataları bağlayıcı",
                "tüm kampanyalarda değişiklik yapma hakkını",
                "kampanya şartlarını değiştirme ve/veya",
                "kampanyayı tek taraflı olarak sonlandırma hakkını"
            ]
        ):

            continue

        cleaned.append(
            item
        )

    return unique(
        cleaned
    )[:35]


# =========================================================
# RECORD
# =========================================================

def create_record(raw_record):

    title = normalize_spaces(
        raw_record.get(
            "urun_adi",
            ""
        )
    )

    raw_category = normalize_spaces(
        raw_record.get(
            "kampanya_kategorisi",
            ""
        )
    )

    raw_text = str(
        raw_record.get(
            "ham_metin",
            ""
        )
    ).strip()

    direct_finance = (
        is_direct_finance_campaign(
            raw_category,
            title
        )
    )

    account_campaign = (
        is_account_campaign(
            raw_category,
            title
        )
    )

    (
        _,
        table_fees
    ) = extract_rate_tables(
        raw_text
    )

    record = {
        "banka": BANK_NAME,

        "kayit_turu": (
            "kampanya"
        ),

        "urun_adi": (
            title
        ),

        "urun_kategorisi": (
            detect_product_category(
                raw_category
            )
        ),

        "kar_payi_orani": (
            extract_profit_rates(
                raw_text,
                direct_finance,
                account_campaign
            )
        ),

        "finansman_orani": (
            extract_finance_ratio(
                raw_text,
                direct_finance
            )
        ),

        "finansman_tutari": (
            extract_finance_amount(
                raw_text,
                direct_finance
            )
        ),

        "vade": (
            extract_term(
                raw_text,
                title,
                direct_finance
            )
        ),

        "taksit_sayisi": (
            extract_installments(
                raw_text
            )
        ),

        "masraf_bilgisi": (
            extract_expenses(
                raw_text,
                table_fees
            )
        ),

        "kampanya_turu": (
            detect_campaign_type(
                raw_category,
                title
            )
        ),

        "kampanya_avantaji": (
            extract_advantages(
                raw_text,
                direct_finance
            )
        ),

        "kampanya_suresi": (
            extract_campaign_period(
                raw_record
            )
        ),

        "hedef_kitle": (
            extract_target_audience(
                raw_text
            )
        ),

        "para_birimi": (
            extract_currency(
                raw_text
            )
        ),

        "kosullar": (
            extract_conditions(
                raw_text
            )
        ),

        "kaynak_url": (
            normalize_spaces(
                raw_record.get(
                    "kaynak_url",
                    ""
                )
            )
        ),

        "ham_metin": (
            raw_text
        )
    }

    return record


# =========================================================
# ŞEMA
# =========================================================

def validate_record(record):

    missing = [
        field

        for field
        in REQUIRED_FIELDS

        if field not in record
    ]

    if missing:

        raise ValueError(
            (
                f"{record.get('urun_adi')} "
                f"eksik alan: {missing}"
            )
        )

    for field in LIST_FIELDS:

        if not isinstance(
            record[field],
            list
        ):

            raise ValueError(
                (
                    f"{record['urun_adi']} -> "
                    f"{field} list değil."
                )
            )

    string_fields = [
        "banka",
        "kayit_turu",
        "urun_adi",
        "urun_kategorisi",
        "kampanya_turu",
        "kampanya_suresi",
        "kaynak_url",
        "ham_metin"
    ]

    for field in string_fields:

        if not isinstance(
            record[field],
            str
        ):

            raise ValueError(
                (
                    f"{record['urun_adi']} -> "
                    f"{field} string değil."
                )
            )

    if (
        record["banka"]
        != BANK_NAME
    ):

        raise ValueError(
            "Banka adı hatalı."
        )

    if (
        record["kayit_turu"]
        != "kampanya"
    ):

        raise ValueError(
            "Kayıt türü hatalı."
        )

    if not record[
        "urun_adi"
    ]:

        raise ValueError(
            "Ürün adı boş."
        )

    if not record[
        "kaynak_url"
    ]:

        raise ValueError(
            (
                f"{record['urun_adi']} -> "
                "kaynak_url boş."
            )
        )

    if not record[
        "ham_metin"
    ]:

        raise ValueError(
            (
                f"{record['urun_adi']} -> "
                "ham_metin boş."
            )
        )


# =========================================================
# DUPLICATE
# =========================================================

def find_duplicates(records):

    duplicate_urls = []

    duplicate_titles = []

    seen_urls = {}

    seen_titles = {}

    for record in records:

        url_key = tr_lower(
            record[
                "kaynak_url"
            ]
        )

        title_key = tr_lower(
            record[
                "urun_adi"
            ]
        )

        if url_key in seen_urls:

            duplicate_urls.append(
                (
                    seen_urls[
                        url_key
                    ],
                    record[
                        "urun_adi"
                    ]
                )
            )

        else:

            seen_urls[
                url_key
            ] = record[
                "urun_adi"
            ]

        if title_key in seen_titles:

            duplicate_titles.append(
                (
                    seen_titles[
                        title_key
                    ],
                    record[
                        "urun_adi"
                    ]
                )
            )

        else:

            seen_titles[
                title_key
            ] = record[
                "urun_adi"
            ]

    return (
        duplicate_urls,
        duplicate_titles
    )


# =========================================================
# BEKLENEN TÜRLER
# =========================================================

EXPECTED_TYPES = {
    "Banka Çalışanlarına Özel": (
        "Finansman Kampanyası"
    ),

    "Bereket Sigorta Çalışanlarına": (
        "Çalışan Avantaj Paketi"
    ),

    "BES ile Hem": (
        "BES Kampanyası"
    ),

    "Faturaları Unutun": (
        "Bonus / Ödül Kampanyası"
    ),

    "Günlük Hesap": (
        "Hesap / Getiri Kampanyası"
    ),

    "Kamu Çalışanlarına Özel": (
        "Finansman Kampanyası"
    ),

    "Katılım Hesabınızı": (
        "Hesap / Getiri Kampanyası"
    ),

    "Maaş Müşterilerine": (
        "Maaş Müşterisi Avantaj Kampanyası"
    ),

    "Emekliler Kazanıyor": (
        "Emekli Promosyonu"
    ),

    "Masrafsız Bankacılık": (
        "Bankacılık Avantajı"
    ),

    "Kâr Paysız 50.000": (
        "Finansman Kampanyası"
    ),

    "Sevdiklerinize Fırsat": (
        "Bonus / Ödül Kampanyası"
    ),

    "Kazancı Bol Hoş Geldin": (
        "Hoş Geldin / Bonus Paketi"
    ),

    "Sıfır Komisyon": (
        "Yatırım Kampanyası"
    ),

    "Avantajlı Bankacılıkla": (
        "Bankacılık Avantaj Paketi"
    )
}


# =========================================================
# RECORD BUL
# =========================================================

def find_record(
    records,
    query
):

    query_lower = tr_lower(
        query
    )

    for record in records:

        if query_lower in tr_lower(
            record[
                "urun_adi"
            ]
        ):

            return record

    return None


# =========================================================
# TÜR KONTROLÜ
# =========================================================

def check_expected_types(records):

    errors = []

    missing = []

    for (
        fragment,
        expected
    ) in EXPECTED_TYPES.items():

        record = find_record(
            records,
            fragment
        )

        if record is None:

            missing.append(
                fragment
            )

            continue

        actual = record[
            "kampanya_turu"
        ]

        if actual != expected:

            errors.append(
                {
                    "urun": (
                        record[
                            "urun_adi"
                        ]
                    ),
                    "beklenen": (
                        expected
                    ),
                    "gercek": (
                        actual
                    )
                }
            )

    return (
        errors,
        missing
    )


# =========================================================
# FİNANSMAN TUTARI KİRLİLİĞİ
# =========================================================

def find_suspicious_finance_amounts(
    records
):

    suspicious = []

    bad_phrases = [
        "maliyet tablosu",
        "ürün hizmet ücretleri",
        "urun hizmet ucretleri",
        "örnek hesaplama",
        "örnek ödeme",
        "kar payı oranları ürün",
        "kâr payı oranları ürün"
    ]

    for record in records:

        for item in record[
            "finansman_tutari"
        ]:

            if contains_any(
                item,
                bad_phrases
            ):

                suspicious.append(
                    (
                        record[
                            "urun_adi"
                        ],
                        item
                    )
                )

    return suspicious


# =========================================================
# 50K VADE KİRLİLİĞİ
# =========================================================

def find_irrelevant_50k_terms(
    records
):

    suspicious = []

    for record in records:

        if (
            "50.000"
            not in record[
                "urun_adi"
            ]
        ):

            continue

        for item in record[
            "vade"
        ]:

            if (
                "125.000"
                in item
                or "250.000"
                in item
            ):

                suspicious.append(
                    (
                        record[
                            "urun_adi"
                        ],
                        item
                    )
                )

    return suspicious


# =========================================================
# AVANTAJ KİRLİLİĞİ
# =========================================================

def find_suspicious_advantages(
    records
):

    suspicious = []

    bad_phrases = [
        "örnek hesaplama tabloları",
        "örnek ödeme tabloları"
    ]

    for record in records:

        for item in record[
            "kampanya_avantaji"
        ]:

            if (
                contains_any(
                    item,
                    bad_phrases
                )
                or item.startswith(
                    "’nden"
                )
                or item.startswith(
                    "'nden"
                )
            ):

                suspicious.append(
                    (
                        record[
                            "urun_adi"
                        ],
                        item
                    )
                )

    return suspicious


# =========================================================
# DETAY YAZDIR
# =========================================================

def print_items(
    label,
    items,
    max_items=7
):

    print(
        label
    )

    if not items:

        print(
            "  []"
        )

        return

    for item in items[
        :max_items
    ]:

        print(
            "  -",
            item
        )

    if len(
        items
    ) > max_items:

        print(
            (
                f"  ... "
                f"(+{len(items) - max_items} kayıt)"
            )
        )


def print_record_details(
    records,
    query
):

    record = find_record(
        records,
        query
    )

    if not record:

        print()

        print(
            "[BULUNAMADI]",
            query
        )

        return

    print()

    print(
        "-" * 100
    )

    print(
        record[
            "urun_adi"
        ]
    )

    print(
        "Kategori:",
        record[
            "urun_kategorisi"
        ]
    )

    print(
        "Tür:",
        record[
            "kampanya_turu"
        ]
    )

    print(
        "Süre:",
        (
            record[
                "kampanya_suresi"
            ]
            or "[]"
        )
    )

    print_items(
        "Kâr payı:",
        record[
            "kar_payi_orani"
        ]
    )

    print_items(
        "Finansman tutarı:",
        record[
            "finansman_tutari"
        ]
    )

    print_items(
        "Vade:",
        record[
            "vade"
        ]
    )

    print_items(
        "Taksit:",
        record[
            "taksit_sayisi"
        ]
    )

    print_items(
        "Masraf:",
        record[
            "masraf_bilgisi"
        ]
    )

    print_items(
        "Avantaj:",
        record[
            "kampanya_avantaji"
        ]
    )

    print_items(
        "Hedef:",
        record[
            "hedef_kitle"
        ]
    )


# =========================================================
# MAIN
# =========================================================

def main():

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        raw_data = json.load(
            file
        )

    campaigns = raw_data.get(
        "kampanyalar",
        []
    )

    declared_count = raw_data.get(
        "aktif_kampanya_sayisi"
    )

    print()

    print(
        "=" * 100
    )

    print(
        "TÜRKİYE FİNANS KAMPANYA EXTRACTOR V3"
    )

    print(
        "=" * 100
    )

    print(
        "RAW beyan edilen aktif kampanya:",
        declared_count
    )

    print(
        "RAW gerçek kampanya:",
        len(
            campaigns
        )
    )

    if not campaigns:

        raise ValueError(
            "RAW kampanya listesi boş."
        )

    if (
        declared_count is not None
        and declared_count
        != len(campaigns)
    ):

        raise ValueError(
            (
                "RAW aktif_kampanya_sayisi "
                "kampanyalar dizisiyle uyuşmuyor."
            )
        )

    records = []

    for (
        index,
        raw_record
    ) in enumerate(
        campaigns,
        start=1
    ):

        record = create_record(
            raw_record
        )

        validate_record(
            record
        )

        records.append(
            record
        )

        print()

        print(
            "-" * 100
        )

        print(
            (
                f"[{index}/"
                f"{len(campaigns)}] "
                f"{record['urun_adi']}"
            )
        )

        print(
            "Kategori:",
            record[
                "urun_kategorisi"
            ]
        )

        print(
            "Tür:",
            record[
                "kampanya_turu"
            ]
        )

        print(
            "Kâr payı:",
            len(
                record[
                    "kar_payi_orani"
                ]
            )
        )

        print(
            "Finansman tutarı:",
            len(
                record[
                    "finansman_tutari"
                ]
            )
        )

        print(
            "Vade:",
            len(
                record[
                    "vade"
                ]
            )
        )

        print(
            "Taksit:",
            len(
                record[
                    "taksit_sayisi"
                ]
            )
        )

        print(
            "Masraf:",
            len(
                record[
                    "masraf_bilgisi"
                ]
            )
        )

        print(
            "Avantaj:",
            len(
                record[
                    "kampanya_avantaji"
                ]
            )
        )

        print(
            "Hedef:",
            len(
                record[
                    "hedef_kitle"
                ]
            )
        )

        print(
            "Koşul:",
            len(
                record[
                    "kosullar"
                ]
            )
        )

        print(
            "Süre:",
            (
                record[
                    "kampanya_suresi"
                ]
                or "-"
            )
        )

    # =====================================================
    # KONTROLLER
    # =====================================================

    (
        duplicate_urls,
        duplicate_titles
    ) = find_duplicates(
        records
    )

    (
        classification_errors,
        missing_expected
    ) = check_expected_types(
        records
    )

    suspicious_amounts = (
        find_suspicious_finance_amounts(
            records
        )
    )

    irrelevant_50k_terms = (
        find_irrelevant_50k_terms(
            records
        )
    )

    suspicious_advantages = (
        find_suspicious_advantages(
            records
        )
    )

    no_advantage = [
        record[
            "urun_adi"
        ]

        for record
        in records

        if not record[
            "kampanya_avantaji"
        ]
    ]

    no_target = [
        record[
            "urun_adi"
        ]

        for record
        in records

        if not record[
            "hedef_kitle"
        ]
    ]

    no_conditions = [
        record[
            "urun_adi"
        ]

        for record
        in records

        if not record[
            "kosullar"
        ]
    ]

    no_period = [
        record[
            "urun_adi"
        ]

        for record
        in records

        if not record[
            "kampanya_suresi"
        ]
    ]

    finance_term_missing = [
        record[
            "urun_adi"
        ]

        for record
        in records

        if (
            record[
                "kampanya_turu"
            ]
            == "Finansman Kampanyası"

            and not record[
                "vade"
            ]
        )
    ]

    # =====================================================
    # OUTPUT
    # =====================================================

    output = {
        "banka": BANK_NAME,

        "kayit_turu": (
            "kampanya"
        ),

        "toplam_kayit": (
            len(records)
        ),

        "urunler": (
            records
        )
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
            output,
            file,
            ensure_ascii=False,
            indent=4
        )

    # =====================================================
    # GENEL KONTROL
    # =====================================================

    print()

    print(
        "=" * 100
    )

    print(
        "GENEL KONTROL"
    )

    print(
        "=" * 100
    )

    print(
        "Toplam kayıt:",
        len(records)
    )

    print(
        "Avantaj boş:",
        len(no_advantage)
    )

    print(
        "Hedef kitle boş:",
        len(no_target)
    )

    print(
        "Koşullar boş:",
        len(no_conditions)
    )

    print(
        "Kampanya süresi boş:",
        len(no_period)
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
        "Yanlış kampanya türü:",
        len(
            classification_errors
        )
    )

    print(
        "Beklenen kampanya bulunamadı:",
        len(
            missing_expected
        )
    )

    print(
        "Şüpheli finansman tutarı:",
        len(
            suspicious_amounts
        )
    )

    print(
        "50K kampanyasında alakasız vade:",
        len(
            irrelevant_50k_terms
        )
    )

    print(
        "Şüpheli avantaj:",
        len(
            suspicious_advantages
        )
    )

    print(
        "Finansman kampanyasında vade boş:",
        len(
            finance_term_missing
        )
    )

    # =====================================================
    # HATALAR
    # =====================================================

    if suspicious_amounts:

        print()

        print(
            "ŞÜPHELİ FİNANSMAN TUTARI:"
        )

        for (
            name,
            item
        ) in suspicious_amounts:

            print(
                "-",
                name
            )

            print(
                " ",
                item
            )

    if irrelevant_50k_terms:

        print()

        print(
            "50K KAMPANYASINDA ALakasız VADE:"
        )

        for (
            name,
            item
        ) in irrelevant_50k_terms:

            print(
                "-",
                name
            )

            print(
                " ",
                item
            )

    if suspicious_advantages:

        print()

        print(
            "ŞÜPHELİ AVANTAJ:"
        )

        for (
            name,
            item
        ) in suspicious_advantages:

            print(
                "-",
                name
            )

            print(
                " ",
                item
            )

    # =====================================================
    # BOŞ HEDEFLER
    # =====================================================

    if no_target:

        print()

        print(
            "HEDEF KİTLE BULUNAMAYANLAR:"
        )

        for item in no_target:

            print(
                "-",
                item
            )

    # =====================================================
    # TÜR DAĞILIMI
    # =====================================================

    type_counts = {}

    for record in records:

        campaign_type = (
            record[
                "kampanya_turu"
            ]
        )

        type_counts[
            campaign_type
        ] = (
            type_counts.get(
                campaign_type,
                0
            )
            + 1
        )

    print()

    print(
        "=" * 100
    )

    print(
        "KAMPANYA TÜR DAĞILIMI"
    )

    print(
        "=" * 100
    )

    for (
        campaign_type,
        count
    ) in sorted(
        type_counts.items()
    ):

        print(
            (
                f"- "
                f"{campaign_type}: "
                f"{count}"
            )
        )

    # =====================================================
    # KRİTİK KAMPANYALAR
    # =====================================================

    print()

    print(
        "=" * 100
    )

    print(
        "KRİTİK KAMPANYA KONTROLLERİ"
    )

    print(
        "=" * 100
    )

    critical_campaigns = [
        "Banka Çalışanlarına Özel",
        "Kamu Çalışanlarına Özel",
        "Faturaları Unutun",
        "BES ile Hem",
        "Katılım Hesabınızı",
        "Maaş Müşterilerine",
        "Emekliler Kazanıyor",
        "Masrafsız Bankacılık",
        "Kâr Paysız 50.000",
        "Sevdiklerinize Fırsat",
        "Kazancı Bol Hoş Geldin",
        "Sıfır Komisyon",
        "Avantajlı Bankacılıkla"
    ]

    for campaign in critical_campaigns:

        print_record_details(
            records,
            campaign
        )

    # =====================================================
    # FINAL
    # =====================================================

    print()

    print(
        "=" * 100
    )

    print(
        "TÜRKİYE FİNANS KAMPANYA EXTRACTOR V3 TAMAMLANDI"
    )

    print(
        "=" * 100
    )

    print(
        "İşlenen kampanya:",
        len(records)
    )

    print(
        "Şema kontrolü: BAŞARILI"
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
        "Yanlış kampanya türü:",
        len(
            classification_errors
        )
    )

    print(
        "Hedef kitle boş:",
        len(no_target)
    )

    print(
        "Şüpheli finansman tutarı:",
        len(
            suspicious_amounts
        )
    )

    print(
        "50K kampanyasında alakasız vade:",
        len(
            irrelevant_50k_terms
        )
    )

    print(
        "Şüpheli avantaj:",
        len(
            suspicious_advantages
        )
    )

    print(
        "Finansman kampanyasında vade boş:",
        len(
            finance_term_missing
        )
    )

    print(
        "JSON:",
        OUTPUT_FILE
    )

    print(
        "=" * 100
    )


if __name__ == "__main__":

    main()