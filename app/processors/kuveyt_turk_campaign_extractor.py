import json
import os
import re


INPUT_FILE = (
    "data/raw/"
    "kuveyt_turk_kampanyalar.json"
)

OUTPUT_FILE = (
    "data/processed/"
    "kuveyt_turk_kampanya_extracted.json"
)


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


TURKISH_MONTHS = {
    "ocak": 1,
    "şubat": 2,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "agustos": 8,
    "eylül": 9,
    "eylul": 9,
    "ekim": 10,
    "kasım": 11,
    "kasim": 11,
    "aralık": 12,
    "aralik": 12
}


NUMBER_WORDS = {
    "on": 10,
    "yirmi": 20,
    "otuz": 30,
    "kırk": 40,
    "kirk": 40,
    "elli": 50,
    "altmış": 60,
    "altmis": 60,
    "yetmiş": 70,
    "yetmis": 70,
    "seksen": 80,
    "doksan": 90,
    "yüz": 100,
    "yuz": 100
}


NOISE_LINES = {
    "Kampanyayı Paylaş",
    "Facebook'da paylaş",
    "X'de paylaş",
    "LinkedIn'de paylaş",
    "Whatsapp'da paylaş",

    "Kampanyaya Katılmak İçin Hemen Başvurun",

    "T.C. Kimlik Numarası",
    "Telefon",
    "Doğum Tarihi",

    "Kabul Ediyorum",
    "Kabul Etmiyorum",
    "Devam",

    "Ana Sayfa",
    "Kampanyalar"
}


# =========================================================
# TÜRKÇE LOWER
#
# Python:
# "İhtiyaç".casefold()
#
# bazı eşleştirmelerde sorun çıkarabildiği için
# önce Türkçe I/İ dönüşümü yapıyoruz.
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

    # Unicode combining dot ihtimalini temizle.
    value = value.replace(
        "\u0307",
        ""
    )

    return value


# =========================================================
# GENEL
# =========================================================

def normalize_spaces(value):

    return re.sub(
        r"\s+",
        " ",
        str(value or "")
    ).strip()


def normalize_financial_text(value):

    value = normalize_spaces(
        value
    )

    value = value.replace(
        "₺",
        "TL"
    )

    # % 2.99 -> %2,99
    value = re.sub(
        r"%\s*(\d+(?:[.,]\d+)?)",
        lambda match: (
            "%"
            + match.group(1).replace(
                ".",
                ","
            )
        ),
        value
    )

    # 2,99 % -> %2,99
    value = re.sub(
        r"(?<![%\d])"
        r"(\d+(?:[.,]\d+)?)"
        r"\s*%",
        lambda match: (
            "%"
            + match.group(1).replace(
                ".",
                ","
            )
        ),
        value
    )

    return value


def unique(items):

    result = []

    seen = set()


    for item in items:

        item = normalize_financial_text(
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
    words
):

    lowered = tr_lower(
        text
    )


    return any(
        tr_lower(
            word
        )
        in lowered

        for word
        in words
    )


def get_lines(text):

    result = []


    for line in str(
        text
    ).splitlines():

        line = normalize_spaces(
            line
        )


        if line:

            result.append(
                line
            )


    return result


# =========================================================
# EXTRACTOR İÇİN TEMİZ METİN
# =========================================================

def get_content_lines(text):

    lines = get_lines(
        text
    )

    result = []


    for line in lines:

        if line in NOISE_LINES:

            continue


        lower = tr_lower(
            line
        )


        if (
            "kişisel verilerle ilgili"
            in lower
        ):

            continue


        if (
            "aydınlatma metni"
            in lower
        ):

            continue


        if (
            "5549 sayılı kanun"
            in lower
        ):

            continue


        if (
            "6563 sayılı kanun"
            in lower
        ):

            continue


        if (
            "sadece kendi adınıza başvuru"
            in lower
        ):

            continue


        # Sağlam Kart fallback footer
        if (
            line == "Diğer Kampanyalar"
            and len(result) > 3
        ):

            break


        result.append(
            line
        )


    return result


def joined_content(text):

    return " ".join(
        get_content_lines(
            text
        )
    )


# =========================================================
# KATEGORİ
# =========================================================

def detect_category(url):

    lower = tr_lower(
        url
    )


    if (
        "/musteri-ol-kampanyalari/"
        in lower
    ):

        return (
            "Müşteri Ol Kampanyası"
        )


    if (
        "/finansman-kampanyalari/"
        in lower
    ):

        return (
            "Finansman Kampanyası"
        )


    if (
        "/seyahat-kampanyalari/"
        in lower
    ):

        return (
            "Seyahat Kampanyası"
        )


    if (
        "/kart-kampanyalari/"
        in lower
    ):

        return (
            "Kart Kampanyası"
        )


    if (
        "saglamkart.kuveytturk.com.tr"
        in lower
    ):

        return (
            "Kart Kampanyası"
        )


    return "Kampanya"


# =========================================================
# TARİH
# =========================================================

def format_date(
    day,
    month,
    year
):

    return (
        f"{int(day):02d}."
        f"{int(month):02d}."
        f"{int(year):04d}"
    )


def parse_numeric_date_range(value):

    match = re.fullmatch(
        r"\s*"
        r"(\d{1,2})\."
        r"(\d{1,2})\."
        r"(\d{4})"
        r"\s*-\s*"
        r"(\d{1,2})\."
        r"(\d{1,2})\."
        r"(\d{4})"
        r"\s*",
        value
    )


    if not match:

        return None


    return {
        "start_day": int(
            match.group(1)
        ),

        "start_month": int(
            match.group(2)
        ),

        "start_year": int(
            match.group(3)
        ),

        "end_day": int(
            match.group(4)
        ),

        "end_month": int(
            match.group(5)
        ),

        "end_year": int(
            match.group(6)
        )
    }


def find_turkish_date(
    text,
    target_day=None,
    target_month=None
):

    pattern = re.compile(
        r"\b"
        r"(\d{1,2})"
        r"\s+"
        r"(Ocak|Şubat|Subat|Mart|Nisan|"
        r"Mayıs|Mayis|Haziran|Temmuz|"
        r"Ağustos|Agustos|Eylül|Eylul|"
        r"Ekim|Kasım|Kasim|Aralık|Aralik)"
        r"\s+"
        r"(20\d{2})"
        r"\b",
        flags=re.IGNORECASE
    )


    for match in pattern.finditer(
        text
    ):

        day = int(
            match.group(1)
        )


        month_name = tr_lower(
            match.group(2)
        )


        month = TURKISH_MONTHS.get(
            month_name
        )


        year = int(
            match.group(3)
        )


        if not month:

            continue


        if (
            target_day is not None
            and day != target_day
        ):

            continue


        if (
            target_month is not None
            and month != target_month
        ):

            continue


        # Absürt gelecek yılını alma.
        if year >= 2040:

            continue


        return {
            "day": day,
            "month": month,
            "year": year
        }


    return None


def extract_campaign_duration(text):

    lines = get_lines(
        text
    )


    warnings = []


    # =====================================================
    # NORMAL SAYFA
    # =====================================================

    for index, line in enumerate(
        lines
    ):

        if (
            tr_lower(
                line
            )
            != "kampanya tarihleri"
        ):

            continue


        for next_index in range(
            index + 1,
            min(
                len(lines),
                index + 5
            )
        ):

            candidate = lines[
                next_index
            ]


            parsed = (
                parse_numeric_date_range(
                    candidate
                )
            )


            if not parsed:

                continue


            start = format_date(
                parsed[
                    "start_day"
                ],
                parsed[
                    "start_month"
                ],
                parsed[
                    "start_year"
                ]
            )


            end = format_date(
                parsed[
                    "end_day"
                ],
                parsed[
                    "end_month"
                ],
                parsed[
                    "end_year"
                ]
            )


            # =============================================
            # Bella Maison gibi kaynak typo kontrolü
            # =============================================

            if (
                parsed[
                    "end_year"
                ] >= 2040
            ):

                alternative = (
                    find_turkish_date(
                        text,
                        target_day=(
                            parsed[
                                "end_day"
                            ]
                        ),
                        target_month=(
                            parsed[
                                "end_month"
                            ]
                        )
                    )
                )


                if alternative:

                    corrected_end = (
                        format_date(
                            alternative[
                                "day"
                            ],
                            alternative[
                                "month"
                            ],
                            alternative[
                                "year"
                            ]
                        )
                    )


                    warnings.append(
                        (
                            "Kaynak tarih tutarsızlığı: "
                            f"'{candidate}' -> "
                            f"'{start} - "
                            f"{corrected_end}'. "
                            "Sayfa gövdesindeki tarih "
                            "esas alındı."
                        )
                    )


                    return (
                        (
                            f"{start} - "
                            f"{corrected_end}"
                        ),
                        warnings
                    )


            return (
                f"{start} - {end}",
                warnings
            )


    # =====================================================
    # SAĞLAM KART FALLBACK
    #
    # 31 Aralık 2026 tarihine kadar
    # =====================================================

    pattern = re.compile(
        r"\b"
        r"(\d{1,2})"
        r"\s+"
        r"(Ocak|Şubat|Subat|Mart|Nisan|"
        r"Mayıs|Mayis|Haziran|Temmuz|"
        r"Ağustos|Agustos|Eylül|Eylul|"
        r"Ekim|Kasım|Kasim|Aralık|Aralik)"
        r"\s+"
        r"(20\d{2})"
        r"\s+tarihine\s+kadar",
        flags=re.IGNORECASE
    )


    match = pattern.search(
        text
    )


    if match:

        month = TURKISH_MONTHS.get(
            tr_lower(
                match.group(2)
            )
        )


        if month:

            date = format_date(
                match.group(1),
                month,
                match.group(3)
            )


            return (
                f"{date} tarihine kadar",
                warnings
            )


    return (
        "",
        warnings
    )


# =========================================================
# PARA BİRİMİ
# =========================================================

def extract_para_birimi(text):

    results = []


    if re.search(
        r"(?:"
        r"\bTL\b"
        r"|₺"
        r"|\bTürk\s+Lirası\b"
        r")",
        text,
        flags=re.IGNORECASE
    ):

        results.append(
            "TRY"
        )


    if re.search(
        r"\b(?:"
        r"USD"
        r"|ABD\s+Doları"
        r"|Amerikan\s+Doları"
        r")\b",
        text,
        flags=re.IGNORECASE
    ):

        results.append(
            "USD"
        )


    if re.search(
        r"\b(?:"
        r"EUR"
        r"|Euro"
        r"|Avro"
        r")\b",
        text,
        flags=re.IGNORECASE
    ):

        results.append(
            "EUR"
        )


    if (
        re.search(
            r"\bdöviz\b",
            tr_lower(
                text
            )
        )

        and (
            "USD" not in results
            and "EUR" not in results
        )
    ):

        results.append(
            "DÖVİZ"
        )


    return unique(
        results
    )


# =========================================================
# TÜRKÇE YAZIYLA YÜZDE
#
# yüzde altmış
# yüzde altmışı
# =========================================================

def replace_turkish_percent_words(text):

    result = text


    for word, number in (
        NUMBER_WORDS.items()
    ):

        result = re.sub(
            (
                rf"\byüzde\s+{word}"
                rf"(?:s?[ıiuü])?\b"
            ),
            f"%{number}",
            result,
            flags=re.IGNORECASE
        )


    return result


# =========================================================
# KÂR PAYI
# =========================================================

def extract_kar_payi_orani(text):

    results = []


    patterns = [
        (
            r"(?:aylık\s+)?"
            r"k[âa]r(?:\s+payı)?"
            r"\s+oran[ıi]"
            r"\s*"
            r"%\s*"
            r"(\d+(?:[.,]\d+)?)"
        ),

        (
            r"%\s*"
            r"(\d+(?:[.,]\d+)?)"
            r"\s*"
            r"(?:avantajlı\s+)?"
            r"k[âa]r\s+payı"
            r"\s+oran"
        ),

        (
            r"%\s*"
            r"(\d+(?:[.,]\d+)?)"
            r"\s*oran(?:lı|la)?"
            r"\s+"
            r"k[âa]r\s+pay"
        )
    ]


    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE
        ):

            value = (
                match.group(1)
                .replace(
                    ".",
                    ","
                )
            )


            try:

                numeric = float(
                    value.replace(
                        ",",
                        "."
                    )
                )

            except ValueError:

                continue


            if numeric <= 0:

                continue


            results.append(
                f"%{value}"
            )


    return unique(
        results
    )


# =========================================================
# FİNANSMAN ORANI
# =========================================================

def extract_finansman_orani(text):

    results = []


    for original_line in get_content_lines(
        text
    ):

        line = (
            replace_turkish_percent_words(
                original_line
            )
        )


        lower = tr_lower(
            line
        )


        if "%" not in line:

            continue


        # Kâr/maliyet/indirim oranlarını alma.
        if contains_any(
            line,
            [
                "kâr payı",
                "kar payı",
                "kâr oran",
                "kar oran",
                "maliyet",
                "indirim"
            ]
        ):

            continue


        context_ok = (
            "finansman"
            in lower

            or "umre tutar"
            in lower

            or "ekspertiz"
            in lower

            or "satış değer"
            in lower
        )


        if not context_ok:

            continue


        ratio_ok = contains_any(
            line,
            [
                "finansman oran",
                "tutarının",
                "değerinin",
                "en fazla",
                "kadar finansman"
            ]
        )


        if ratio_ok:

            results.append(
                line
            )


    return unique(
        results
    )


# =========================================================
# FİNANSMAN TUTARI
# =========================================================

def extract_finansman_tutari(
    text,
    category,
    title
):

    results = []


    title_lower = tr_lower(
        title
    )

    text_lower = tr_lower(
        text
    )


    finance_context = (
        category
        == "Finansman Kampanyası"

        or "finansman"
        in title_lower

        or "ihtiyaç kart"
        in title_lower

        or "finansman"
        in text_lower

        or "ihtiyaç kart"
        in text_lower
    )


    if not finance_context:

        return []


    joined = joined_content(
        text
    )


    parts = re.split(
        r"(?<=[.!?])\s+",
        joined
    )


    amount_pattern = re.compile(
        r"\b"
        r"\d[\d.]*"
        r"\s*TL"
        r"[’']?"
        r"(?:ye|ya)?"
        r"\s+kadar\b",
        flags=re.IGNORECASE
    )


    for part in parts:

        if not amount_pattern.search(
            part
        ):

            continue


        if contains_any(
            part,
            [
                "finansman",
                "ihtiyaç kart",
                "başvuru",
                "alışveriş ödemelerinizi",
                "kampanyalı oran"
            ]
        ):

            results.append(
                part
            )


    return unique(
        results
    )[:10]


# =========================================================
# VADE
# =========================================================

def extract_vade(
    text,
    category,
    title
):

    results = []


    title_lower = tr_lower(
        title
    )

    text_lower = tr_lower(
        text
    )


    finance_context = (
        category
        == "Finansman Kampanyası"

        or "finansman"
        in title_lower

        or "ihtiyaç kart"
        in title_lower

        or "araç finansmanı"
        in text_lower

        or "konut finansmanı"
        in text_lower

        or "ihtiyaç kart"
        in text_lower
    )


    if not finance_context:

        return []


    joined = joined_content(
        text
    )


    parts = re.split(
        r"(?<=[.!?])\s+",
        joined
    )


    for part in parts:

        lower = tr_lower(
            part
        )


        # Örnek ödeme planı advertised vade değildir.
        if contains_any(
            part,
            [
                "örnek ödeme planı",
                "bilgi amaçlı"
            ]
        ):

            continue


        relevant = contains_any(
            part,
            [
                "finansman",
                "ihtiyaç kart",
                "başvuru"
            ]
        )


        if not relevant:

            continue


        # 48 aya varan vade
        for match in re.finditer(
            r"\b"
            r"(\d+)"
            r"\s+aya\s+varan\s+vade",
            lower
        ):

            results.append(
                (
                    f"{match.group(1)} "
                    f"aya varan vade"
                )
            )


        # 36 aya kadar vade
        for match in re.finditer(
            r"\b"
            r"(\d+)"
            r"\s+aya\s+kadar\s+vade",
            lower
        ):

            results.append(
                (
                    f"{match.group(1)} "
                    f"aya kadar vade"
                )
            )


        # İhtiyaç Kart:
        # 12 aya varan taksit
        #
        # Finansman tarafında bu aynı zamanda
        # vade bilgisidir.
        if (
            "ihtiyaç kart"
            in lower
        ):

            for match in re.finditer(
                r"\b"
                r"(\d+)"
                r"\s+aya\s+varan\s+taksit",
                lower
            ):

                results.append(
                    (
                        f"{match.group(1)} "
                        f"ay"
                    )
                )


        # 2 ay ertelemeli
        for match in re.finditer(
            r"\b"
            r"(\d+)"
            r"\s+ay\s+ertelemeli",
            lower
        ):

            results.append(
                (
                    f"{match.group(1)} "
                    f"ay ertelemeli"
                )
            )


    return unique(
        results
    )


# =========================================================
# TAKSİT SAYISI
# =========================================================

def extract_taksit_sayisi(text):

    joined = joined_content(
        text
    )


    joined_lower = tr_lower(
        joined
    )


    results = []


    def has_vade_farksiz(
        start_index
    ):

        left = joined_lower[
            max(
                0,
                start_index - 50
            ):
            start_index
        ]


        return (
            "vade farksız"
            in left
        )


    # =====================================================
    # 2 ila 5 taksit
    # =====================================================

    for match in re.finditer(
        r"\b"
        r"(\d+)"
        r"\s+ila\s+"
        r"(\d+)"
        r"\s+taksit(?:e)?\b",
        joined_lower
    ):

        prefix = (
            "Vade farksız "
            if has_vade_farksiz(
                match.start()
            )
            else ""
        )


        results.append(
            (
                f"{prefix}"
                f"{match.group(1)}-"
                f"{match.group(2)} taksit"
            )
        )


    # =====================================================
    # 2 ile 5 taksit
    # =====================================================

    for match in re.finditer(
        r"\b"
        r"(\d+)"
        r"\s+ile\s+"
        r"(\d+)"
        r"\s+taksit\b",
        joined_lower
    ):

        prefix = (
            "Vade farksız "
            if has_vade_farksiz(
                match.start()
            )
            else ""
        )


        results.append(
            (
                f"{prefix}"
                f"{match.group(1)}-"
                f"{match.group(2)} taksit"
            )
        )


    # =====================================================
    # 6 ila 9 aya varan taksit
    # =====================================================

    for match in re.finditer(
        r"\b"
        r"(\d+)"
        r"\s+ila\s+"
        r"(\d+)"
        r"\s+aya\s+varan"
        r"(?:\s+vade\s+farksız)?"
        r"\s+taksit",
        joined_lower
    ):

        prefix = (
            "Vade farksız "
            if (
                has_vade_farksiz(
                    match.start()
                )

                or "vade farksız"
                in match.group(0)
            )
            else ""
        )


        results.append(
            (
                f"{prefix}"
                f"{match.group(1)}-"
                f"{match.group(2)} "
                f"taksit"
            )
        )


    # =====================================================
    # 5 aya varan taksit
    # =====================================================

    for match in re.finditer(
        r"\b"
        r"(\d+)"
        r"\s+aya\s+varan"
        r"(?:\s+vade\s+farksız)?"
        r"\s+taksit",
        joined_lower
    ):

        prefix = (
            "Vade farksız "
            if (
                has_vade_farksiz(
                    match.start()
                )

                or "vade farksız"
                in match.group(0)
            )
            else ""
        )


        results.append(
            (
                f"{prefix}"
                f"{match.group(1)} "
                f"taksite kadar"
            )
        )


    # =====================================================
    # 4'e varan
    # 5'e varan
    # 12'ye varan
    # 6’ya varan
    # =====================================================

    for match in re.finditer(
        r"\b"
        r"(\d+)"
        r"[’']?"
        r"(?:e|a|ye|ya)"
        r"\s+varan\s+taksit",
        joined_lower
    ):

        prefix = (
            "Vade farksız "
            if has_vade_farksiz(
                match.start()
            )
            else ""
        )


        results.append(
            (
                f"{prefix}"
                f"{match.group(1)} "
                f"taksite kadar"
            )
        )


    # =====================================================
    # 6 taksite kadar
    # =====================================================

    for match in re.finditer(
        r"\b"
        r"(\d+)"
        r"\s+taksite\s+kadar\b",
        joined_lower
    ):

        prefix = (
            "Vade farksız "
            if has_vade_farksiz(
                match.start()
            )
            else ""
        )


        results.append(
            (
                f"{prefix}"
                f"{match.group(1)} "
                f"taksite kadar"
            )
        )


    # =====================================================
    # 10 taksit
    # =====================================================

    for match in re.finditer(
        r"\b"
        r"(\d+)"
        r"\s+taksit\b",
        joined_lower
    ):

        before = joined_lower[
            max(
                0,
                match.start() - 35
            ):
            match.start()
        ]


        # Range içindeki üst değeri tekrar ekleme.
        if re.search(
            r"\d+\s+(?:ila|ile)\s*$",
            before
        ):

            continue


        prefix = (
            "Vade farksız "
            if has_vade_farksiz(
                match.start()
            )
            else ""
        )


        results.append(
            (
                f"{prefix}"
                f"{match.group(1)} taksit"
            )
        )


    results = unique(
        results
    )


    # =====================================================
    # 4 taksit + 4 taksite kadar varsa
    # kısa olanı at.
    # =====================================================

    final_results = []


    for item in results:

        simple_match = re.fullmatch(
            r"(Vade farksız )?"
            r"(\d+)"
            r"\s+taksit",
            item
        )


        if simple_match:

            number = (
                simple_match.group(2)
            )


            more_specific = any(
                re.search(
                    (
                        rf"\b{number}"
                        rf"\s+taksite\s+kadar\b"
                    ),
                    other,
                    flags=re.IGNORECASE
                )

                for other
                in results
            )


            if more_specific:

                continue


        final_results.append(
            item
        )


    return unique(
        final_results
    )


# =========================================================
# MASRAF
# =========================================================

def extract_masraf_bilgisi(text):

    results = []


    for line in get_content_lines(
        text
    ):

        if contains_any(
            line,
            [
                "tahsis ücreti",
                "dosya masrafı",
                "toplam masraf",
                "ekspertiz ücreti",
                "ipotek tesis",
                "bsmv",
                "kkdf"
            ]
        ):

            results.append(
                line
            )


    return unique(
        results
    )


# =========================================================
# KAMPANYA AVANTAJLARI
# =========================================================

def extract_campaign_advantages(
    title,
    text
):

    lines = get_content_lines(
        text
    )


    results = []


    positive_keywords = [
        "hediye",
        "harcama iadesi",
        "altın puan",
        "altin puan",

        "indirim",

        " mil",
        "mil'e",
        "mil’e",
        "mil'lere",
        "mil’lere",

        "taksit",

        "puan indirim",

        "özel kur",
        "avantajlı marj",

        "hediye internet",

        "ücretsiz",

        "kampanyalı oran",

        "kâr payı",
        "kar payı",

        "iade verilecektir",
        "iade edilir",
        "iade kazan",

        "uygun oran"
    ]


    negative_keywords = [
        "dahil değildir",
        "dâhil değildir",

        "uygulanmayacaktır",

        "taksitlendirilmemektedir",

        "yararlanamaz",

        "geçerli değildir",

        "hediye kart",
        "hediye çeki"
    ]


    for line in lines:

        if (
            tr_lower(
                line
            )
            == tr_lower(
                title
            )
        ):

            continue


        if len(line) > 650:

            continue


        if contains_any(
            line,
            negative_keywords
        ):

            continue


        if not contains_any(
            line,
            positive_keywords
        ):

            continue


        strong_signal = bool(
            re.search(
                r"(?:\d|%)",
                line
            )
        )


        textual_signal = contains_any(
            line,
            [
                "özel kur",
                "avantajlı marj",
                "altın puan",
                "altin puan",
                "ücretsiz",
                "iade verilecektir",
                "iade edilir",
                "uygun oran"
            ]
        )


        if (
            strong_signal
            or textual_signal
        ):

            results.append(
                line
            )


    results = unique(
        results
    )


    # =====================================================
    # Hiç yakalanmadıysa başlığı koru.
    # =====================================================

    if not results:

        if contains_any(
            title,
            [
                "hediye",
                "indirim",
                "taksit",
                "mil",
                "fırsat"
            ]
        ):

            results.append(
                title
            )


    # =====================================================
    # Tarım vb. nicel olmayan kampanyalar.
    # =====================================================

    if not results:

        for line in lines[1:]:

            lower = tr_lower(
                line
            )


            if (
                lower
                == "kampanya tarihleri"
            ):

                continue


            if re.fullmatch(
                r"\d{1,2}\."
                r"\d{1,2}\."
                r"\d{4}"
                r"\s*-\s*"
                r"\d{1,2}\."
                r"\d{1,2}\."
                r"\d{4}",
                line
            ):

                continue


            if len(line) < 35:

                continue


            results.append(
                line
            )

            break


    return unique(
        results
    )[:20]


# =========================================================
# KAMPANYA TÜRÜ
#
# Sadece title + gerçek avantajlardan belirlenir.
# =========================================================

def detect_campaign_type(
    title,
    advantages,
    kar_orani,
    taksitler
):

    types = []


    advantage_text = "\n".join(
        advantages
    )


    title_lower = tr_lower(
        title
    )


    advantage_lower = tr_lower(
        advantage_text
    )


    positive_text = (
        title
        + "\n"
        + advantage_text
    )


    # =====================================================
    # MİL
    #
    # "milyon" -> mil olmasın.
    # =====================================================

    title_has_mil = bool(
        re.search(
            r"(?:^|[^a-zçğıöşü])"
            r"mil"
            r"(?:"
            r"['’]?"
            r"(?:e|i|ler|lere|leri)"
            r")?"
            r"(?:[^a-zçğıöşü]|$)",
            title_lower
        )
    )


    advantage_has_mil = bool(
        re.search(
            r"\b"
            r"\d[\d.]*"
            r"\s+mil"
            r"(?:['’]?[a-zçğıöşü]*)?"
            r"\b",
            advantage_lower
        )
    )


    if (
        title_has_mil
        or advantage_has_mil
    ):

        types.append(
            "mil"
        )


    # =====================================================
    # HEDİYE
    # =====================================================

    if (
        "hediye"
        in title_lower

        or contains_any(
            advantage_text,
            [
                "hediye",
                "harcama iadesi",
                "altın puan",
                "altin puan"
            ]
        )
    ):

        types.append(
            "hediye"
        )


    # =====================================================
    # İNDİRİM
    # =====================================================

    if contains_any(
        positive_text,
        [
            "indirim"
        ]
    ):

        types.append(
            "indirim"
        )


    # =====================================================
    # TAKSİT
    # =====================================================

    if taksitler:

        types.append(
            "taksit"
        )


    # =====================================================
    # KÂR PAYI
    # =====================================================

    if kar_orani:

        types.append(
            "kar_payi"
        )


    # =====================================================
    # KUR
    # =====================================================

    if contains_any(
        positive_text,
        [
            "özel kur",
            "avantajlı marj"
        ]
    ):

        types.append(
            "kur_avantaji"
        )


    if not types:

        types.append(
            "ayricalik"
        )


    return "+".join(
        unique(
            types
        )
    )


# =========================================================
# HEDEF KİTLE
# =========================================================

def extract_hedef_kitle(
    title,
    text,
    category
):

    results = []


    lines = get_content_lines(
        text
    )


    audience_keywords = [
        "müşteri",
        "müşteriler",
        "kart sahibi",
        "kart sahipleri",
        "kredi kartları",
        "sağlam kart",
        "miles&smiles",
        "18 yaş",
        "evlenecek",
        "evlenmiş",
        "akademisyen",
        "öğrenci",
        "bireysel",
        "tarım sektör"
    ]


    relation_keywords = [
        "yararlanabilir",
        "faydalanabilir",
        "geçerlidir",
        "dahildir",
        "dâhildir",
        "özel",
        "müşterilerimize"
    ]


    skip_keywords = [
        "müşterisi değilseniz",
        "hemen müşterimiz olun",
        "önceden haber vermeden",
        "müşteri iletişim merkezi"
    ]


    for line in lines:

        if len(line) > 600:

            continue


        if contains_any(
            line,
            skip_keywords
        ):

            continue


        if (
            contains_any(
                line,
                audience_keywords
            )

            and contains_any(
                line,
                relation_keywords
            )
        ):

            results.append(
                line
            )


    results = unique(
        results
    )


    # =====================================================
    # KART FALLBACK
    # =====================================================

    if (
        not results
        and category
        == "Kart Kampanyası"
    ):

        if re.search(
            r"Kuveyt\s+Türk"
            r".{0,60}"
            r"(?:"
            r"Bireysel\s+)?"
            r"(?:Kredi\s+)?"
            r"Kart",
            text,
            flags=re.IGNORECASE
        ):

            results.append(
                (
                    "Kuveyt Türk bireysel "
                    "kart müşterileri"
                )
            )


        elif (
            "Sağlam Kart"
            in text
        ):

            results.append(
                "Sağlam Kart müşterileri"
            )


    # =====================================================
    # YENİ MÜŞTERİ FALLBACK
    # =====================================================

    if (
        not results
        and contains_any(
            title,
            [
                "yeni müşteri",
                "yeni müşterilere",
                "müşterimiz olun"
            ]
        )
    ):

        results.append(
            "Yeni Kuveyt Türk müşterileri"
        )


    # =====================================================
    # AKADEMİSYEN
    # =====================================================

    if (
        not results
        and "akademisyen"
        in tr_lower(
            title
        )
    ):

        results.append(
            "Akademisyenler"
        )


    # =====================================================
    # DAVET KODU KAMPANYASI
    # =====================================================

    if (
        not results
        and "davet kod"
        in tr_lower(
            text
        )
        and "müşteri"
        in tr_lower(
            text
        )
    ):

        results.append(
            (
                "Davet kodu ile Kuveyt Türk "
                "müşterisi olan veya davet eden "
                "uygun müşteriler"
            )
        )


    # =====================================================
    # TARIM
    # Sadece kaynak metinde tarım kitlesi varsa.
    # =====================================================

    if (
        not results
        and "tarım sektör"
        in tr_lower(
            text
        )
    ):

        results.append(
            "Tarım sektöründeki uygun müşteriler"
        )


    return unique(
        results
    )[:12]


# =========================================================
# KOŞULLAR
# =========================================================

def extract_kosullar(text):

    results = []


    keywords = [
        "gerekmektedir",
        "gerekir",
        "olmalıdır",

        "geçerlidir",

        "dahil değildir",
        "dâhil değildir",
        "dahildir",
        "dâhildir",

        "sınırlıdır",
        "sınırlı",

        "birleştirilemez",

        "maksimum",
        "minimum",

        "en az",
        "en fazla",

        "son 30 gün",
        "30 gün içerisinde",

        "başvurusu",
        "başvuru",

        "otomatik",

        "tek kullanımlık",

        "kampanyadan yararlan",
        "kampanyaya katılım",

        "harcama",
        "işlem tutarı",

        "taksit",

        "kart limit",

        "referans kod",
        "kampanya kod",

        "kontenjan",

        "geçerlilik"
    ]


    skip_keywords = [
        "önceden haber vermeden",
        "koşullarında değişiklik",
        "kampanyayı sonlandırma hakkı",

        "kampanyayı paylaş",

        "kişisel veriler"
    ]


    for line in get_content_lines(
        text
    ):

        if len(line) < 20:

            continue


        if len(line) > 700:

            continue


        if contains_any(
            line,
            skip_keywords
        ):

            continue


        if contains_any(
            line,
            keywords
        ):

            results.append(
                line
            )


    return unique(
        results
    )[:35]


# =========================================================
# STANDART KAYIT
# =========================================================

def create_standard_record(campaign):

    title = normalize_spaces(
        campaign.get(
            "urun_adi",
            ""
        )
    )


    url = normalize_spaces(
        campaign.get(
            "kaynak_url",
            ""
        )
    )


    raw_text = str(
        campaign.get(
            "ham_metin",
            ""
        )
    ).strip()


    category = detect_category(
        url
    )


    (
        campaign_duration,
        warnings
    ) = extract_campaign_duration(
        raw_text
    )


    kar_orani = (
        extract_kar_payi_orani(
            raw_text
        )
    )


    taksitler = (
        extract_taksit_sayisi(
            raw_text
        )
    )


    advantages = (
        extract_campaign_advantages(
            title,
            raw_text
        )
    )


    campaign_type = (
        detect_campaign_type(
            title,
            advantages,
            kar_orani,
            taksitler
        )
    )


    record = {

        "banka": (
            "Kuveyt Türk Katılım Bankası"
        ),

        "kayit_turu": "kampanya",

        "urun_adi": title,

        "urun_kategorisi": category,


        "kar_payi_orani": (
            kar_orani
        ),


        "finansman_orani": (
            extract_finansman_orani(
                raw_text
            )
        ),


        "finansman_tutari": (
            extract_finansman_tutari(
                raw_text,
                category,
                title
            )
        ),


        "vade": (
            extract_vade(
                raw_text,
                category,
                title
            )
        ),


        "taksit_sayisi": (
            taksitler
        ),


        "masraf_bilgisi": (
            extract_masraf_bilgisi(
                raw_text
            )
        ),


        "kampanya_turu": (
            campaign_type
        ),


        "kampanya_avantaji": (
            advantages
        ),


        "kampanya_suresi": (
            campaign_duration
        ),


        "hedef_kitle": (
            extract_hedef_kitle(
                title,
                raw_text,
                category
            )
        ),


        "para_birimi": (
            extract_para_birimi(
                raw_text
            )
        ),


        "kosullar": (
            extract_kosullar(
                raw_text
            )
        ),


        "kaynak_url": url,

        "ham_metin": raw_text
    }


    return (
        record,
        warnings
    )


# =========================================================
# VALIDATION
# =========================================================

def validate_record(record):

    missing = [
        field

        for field
        in REQUIRED_FIELDS

        if field
        not in record
    ]


    if missing:

        raise ValueError(
            (
                f"{record.get('urun_adi')} "
                f"eksik alanlar: "
                f"{missing}"
            )
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
        "kosullar"
    ]


    for field in list_fields:

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


    print()

    print(
        "=" * 80
    )

    print(
        "KUVEYT TÜRK KAMPANYA EXTRACTOR V3"
    )

    print(
        "=" * 80
    )


    print(
        "Raw kampanya:",
        len(campaigns)
    )


    records = []

    all_warnings = []


    for index, campaign in enumerate(
        campaigns,
        start=1
    ):

        (
            record,
            warnings
        ) = create_standard_record(
            campaign
        )


        validate_record(
            record
        )


        records.append(
            record
        )


        for warning in warnings:

            all_warnings.append(
                {
                    "urun_adi": (
                        record[
                            "urun_adi"
                        ]
                    ),

                    "warning": warning
                }
            )


        print()

        print(
            "-" * 80
        )


        print(
            f"[{index}/{len(campaigns)}] "
            f"{record['urun_adi']}"
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
                or "YOK"
            )
        )


        print(
            "Kâr:",
            record[
                "kar_payi_orani"
            ]
        )


        print(
            "Finansman oranı:",
            record[
                "finansman_orani"
            ]
        )


        print(
            "Finansman tutarı:",
            record[
                "finansman_tutari"
            ]
        )


        print(
            "Vade:",
            record[
                "vade"
            ]
        )


        print(
            "Taksit:",
            record[
                "taksit_sayisi"
            ]
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
            record[
                "hedef_kitle"
            ]
        )


        print(
            "Para:",
            record[
                "para_birimi"
            ]
        )


        print(
            "Koşul:",
            len(
                record[
                    "kosullar"
                ]
            )
        )


    # =====================================================
    # JSON
    # =====================================================

    output = {

        "banka": (
            "Kuveyt Türk Katılım Bankası"
        ),

        "kayit_turu": "kampanya",

        "toplam_kayit": len(
            records
        ),

        "kampanyalar": records
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

    no_duration = [
        item[
            "urun_adi"
        ]

        for item in records

        if not item[
            "kampanya_suresi"
        ]
    ]


    no_advantage = [
        item[
            "urun_adi"
        ]

        for item in records

        if not item[
            "kampanya_avantaji"
        ]
    ]


    no_target = [
        item[
            "urun_adi"
        ]

        for item in records

        if not item[
            "hedef_kitle"
        ]
    ]


    suspicious_mil = [
        item[
            "urun_adi"
        ]

        for item in records

        if (
            "mil"
            in item[
                "kampanya_turu"
            ].split("+")

            and not re.search(
                r"(?:^|[^a-zçğıöşü])"
                r"mil"
                r"(?:[^a-zçğıöşü]|$)",
                tr_lower(
                    (
                        item[
                            "urun_adi"
                        ]
                        + " "
                        + " ".join(
                            item[
                                "kampanya_avantaji"
                            ]
                        )
                    )
                )
            )
        )
    ]


    print()

    print(
        "=" * 80
    )

    print(
        "GENEL KONTROL"
    )

    print(
        "=" * 80
    )


    print(
        "Toplam kayıt:",
        len(records)
    )


    print(
        "Süresi boş:",
        len(
            no_duration
        )
    )


    print(
        "Avantajı boş:",
        len(
            no_advantage
        )
    )


    print(
        "Hedef kitlesi boş:",
        len(
            no_target
        )
    )


    print(
        "Şüpheli Mil türü:",
        len(
            suspicious_mil
        )
    )


    print(
        "Tarih düzeltme/uyarı:",
        len(
            all_warnings
        )
    )


    if no_target:

        print()

        print(
            "HEDEFİ BOŞ:"
        )


        for name in no_target:

            print(
                "-",
                name
            )


    if suspicious_mil:

        print()

        print(
            "ŞÜPHELİ MİL:"
        )


        for name in suspicious_mil:

            print(
                "-",
                name
            )


    if all_warnings:

        print()

        print(
            "TARİH UYARILARI:"
        )


        for item in all_warnings:

            print()

            print(
                "-",
                item[
                    "urun_adi"
                ]
            )


            print(
                " ",
                item[
                    "warning"
                ]
            )


    # =====================================================
    # KRİTİK KONTROLLER
    # =====================================================

    by_name = {
        record[
            "urun_adi"
        ]: record

        for record
        in records
    }


    critical_names = [
        (
            "Yeni Sağlam Kart Troy'lulara Özel "
            "Vade Farksız 5 Aya Varan Taksit İmkanı!"
        ),

        (
            "Colin’s’de Vade Farksız "
            "4 Aya Varan Taksit Fırsatı"
        ),

        (
            "Barçın Spor’da 4 Taksit Fırsatı!"
        ),

        (
            "Yeni Müşterilere Özel "
            "İhtiyaç Kart'ta %1,99 Oran Fırsatı!"
        ),

        (
            "Bella Maison'da %25 "
            "İndirim Fırsatı!"
        ),

        (
            "Diyanet Umre Finansmanı ile "
            "Vade Farksız 3 Taksit İmkanı!"
        ),

        (
            "Konfor‘da Vade Farksız "
            "9 Aya Varan Taksit Fırsatı!"
        ),

        (
            "Korayspor ile Vade Farksız "
            "4'e Varan Taksit İmkanı!"
        ),

        (
            "Saat&Saat Alışverişlerinizde "
            "5'e Varan Taksit İmkanı!"
        ),

        (
            "Yurt Dışı Çıkış Harcı "
            "Hediye Fırsatı!"
        ),

        (
            "Kuveyt Türk ile Yurt Dışı "
            "Seyahatlerinde Ayrıcalıklar Sizinle!"
        ),

        (
            "Tarımda Kuveyt Türk "
            "ile Büyüme Zamanı!"
        )
    ]


    print()

    print(
        "=" * 80
    )

    print(
        "KRİTİK KAMPANYA KONTROLLERİ"
    )

    print(
        "=" * 80
    )


    for name in critical_names:

        record = by_name.get(
            name
        )


        if not record:

            print()

            print(
                "BULUNAMADI:",
                name
            )

            continue


        print()

        print(
            record[
                "urun_adi"
            ]
        )


        print(
            "  Tür:",
            record[
                "kampanya_turu"
            ]
        )


        print(
            "  Süre:",
            record[
                "kampanya_suresi"
            ]
        )


        print(
            "  Kâr:",
            record[
                "kar_payi_orani"
            ]
        )


        print(
            "  Finansman oranı:",
            record[
                "finansman_orani"
            ]
        )


        print(
            "  Finansman tutarı:",
            record[
                "finansman_tutari"
            ]
        )


        print(
            "  Vade:",
            record[
                "vade"
            ]
        )


        print(
            "  Taksit:",
            record[
                "taksit_sayisi"
            ]
        )


        print(
            "  Avantaj:"
        )


        for advantage in (
            record[
                "kampanya_avantaji"
            ][
                :6
            ]
        ):

            print(
                "    -",
                advantage
            )


        print(
            "  Hedef:"
        )


        for target in (
            record[
                "hedef_kitle"
            ][
                :5
            ]
        ):

            print(
                "    -",
                target
            )


    # =====================================================
    # FINAL
    # =====================================================

    print()

    print(
        "=" * 80
    )

    print(
        "EXTRACTOR TAMAMLANDI"
    )

    print(
        "=" * 80
    )


    print(
        "İşlenen kampanya:",
        len(records)
    )


    print(
        "Şema kontrolü: BAŞARILI"
    )


    print(
        "JSON:",
        OUTPUT_FILE
    )


    print(
        "=" * 80
    )


if __name__ == "__main__":

    main()