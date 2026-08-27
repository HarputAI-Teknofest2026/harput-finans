import json
import os
import re


INPUT_FILE = (
    "data/raw/"
    "turkiye_finans_finansman_urunleri.json"
)

OUTPUT_FILE = (
    "data/processed/"
    "turkiye_finans_finansman_extracted.json"
)


EXPECTED_COUNT = 16


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
# TÜRKÇE NORMALİZASYON
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


def normalize_percent(value):

    value = normalize_spaces(
        value
    )

    match = re.fullmatch(
        r"%?\s*"
        r"(\d+(?:[.,]\d+)?)"
        r"\s*%",
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
        r"%\s*"
        r"(\d+(?:[.,]\d+)?)",
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
# SATIRLAR
# =========================================================

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

        if line in {
            "/",
            "ButtonHtml",
            "BannerImage"
        }:

            continue

        result.append(
            line
        )

    return result


def get_content_lines(
    text,
    title
):

    lines = get_lines(
        text
    )

    if not lines:

        return []

    page_content_indexes = [
        index

        for index, line in enumerate(
            lines
        )

        if (
            tr_lower(
                line
            )
            == tr_lower(
                "Sayfa İçeriği"
            )
        )
    ]

    if page_content_indexes:

        lines = lines[
            page_content_indexes[-1] + 1:
        ]

    else:

        title_indexes = [
            index

            for index, line in enumerate(
                lines
            )

            if (
                tr_lower(
                    line
                )
                == tr_lower(
                    title
                )
            )
        ]

        if title_indexes:

            lines = lines[
                title_indexes[-1] + 1:
            ]

    noise = {
        "Ana Sayfa",
        "Bireysel",
        "EN YAKIN ŞUBE",
        "HESAPLAMA ARAÇLARI",
        "HEMEN BAŞVUR",
        "Başvuru Merkezi",
        "Hesaplama Araçları",
        "MOBİL ŞUBE İNDİR"
    }

    result = []

    for line in lines:

        if line in noise:

            continue

        if contains_any(
            line,
            [
                "bu bağlantı yeni sekmede",
                "şube ve atm listesi için tıklayın"
            ]
        ):

            continue

        result.append(
            line
        )

    return result


def sentence_units(
    text,
    title
):

    result = []

    for line in get_content_lines(
        text,
        title
    ):

        parts = re.split(
            (
                r"(?<=[!?])\s+"
                r"|"
                r"(?<=[a-zA-ZçğıöşüÇĞİÖŞÜ])"
                r"\.\s+"
            ),
            line
        )

        for part in parts:

            part = normalize_spaces(
                part
            )

            if not part:

                continue

            if re.match(
                r"^El\s+araç",
                part,
                flags=re.IGNORECASE
            ):

                continue

            result.append(
                part
            )

    return result


# =========================================================
# PARÇALANMIŞ YÜZDELER
# =========================================================

def repair_percent_lines(lines):

    result = []

    index = 0

    while index < len(
        lines
    ):

        current = lines[
            index
        ]

        if re.fullmatch(
            r"%?\d+(?:[.,]\d+)?%",
            current
        ):

            result.append(
                current
            )

            index += 1

            continue

        if (
            re.fullmatch(
                r"\d+(?:[.,]\d+)?",
                current
            )

            and index + 1
            < len(lines)

            and lines[
                index + 1
            ] == "%"
        ):

            result.append(
                current + "%"
            )

            index += 2

            continue

        if re.fullmatch(
            r"\d+",
            current
        ):

            if (
                index + 2
                < len(lines)

                and re.fullmatch(
                    r"\d+",
                    lines[
                        index + 1
                    ]
                )

                and (
                    lines[
                        index + 2
                    ]
                    in {
                        ".",
                        ","
                    }

                    or lines[
                        index + 2
                    ].startswith(
                        (
                            ".",
                            ","
                        )
                    )
                )
            ):

                result.append(
                    current
                )

                index += 1

                continue

            if (
                index + 1
                < len(lines)

                and re.fullmatch(
                    r"\d+(?:[.,]\d+)?%",
                    lines[
                        index + 1
                    ]
                )
            ):

                result.append(
                    current
                )

                index += 1

                continue

        parts = [
            current
        ]

        merged = None

        end_index = None

        if re.fullmatch(
            r"[0-9.,]+",
            current
        ):

            for next_index in range(
                index + 1,
                min(
                    len(lines),
                    index + 5
                )
            ):

                token = lines[
                    next_index
                ]

                if not re.fullmatch(
                    r"[0-9.,%]+",
                    token
                ):

                    break

                parts.append(
                    token
                )

                candidate = "".join(
                    parts
                )

                if re.fullmatch(
                    r"\d+(?:[.,]\d+)?%",
                    candidate
                ):

                    fragmentation = any(
                        (
                            part
                            in {
                                ".",
                                ","
                            }

                            or part.startswith(
                                (
                                    ".",
                                    ","
                                )
                            )

                            or part.endswith(
                                (
                                    ".",
                                    ","
                                )
                            )
                        )

                        for part
                        in parts[:-1]
                    )

                    if fragmentation:

                        merged = candidate

                        end_index = (
                            next_index + 1
                        )

                    break

        if merged:

            result.append(
                merged
            )

            index = end_index

            continue

        result.append(
            current
        )

        index += 1

    return result


# =========================================================
# KATEGORİ
# =========================================================

def detect_category(title):

    lower = tr_lower(
        title
    )

    if (
        "eğitim finansmanı"
        in lower
    ):

        return (
            "Eğitim Finansmanı"
        )

    if (
        "trendyol"
        in lower

        or "alışveriş finansmanı"
        in lower
    ):

        return (
            "Alışveriş Finansmanı"
        )

    if (
        "konut"
        in lower
    ):

        return (
            "Konut Finansmanı"
        )

    if (
        "arsa"
        in lower
    ):

        return (
            "Arsa Finansmanı"
        )

    if (
        "iş yeri"
        in lower

        or "işyeri"
        in lower
    ):

        return (
            "İş Yeri Finansmanı"
        )

    if any(
        keyword
        in lower

        for keyword
        in [
            "taşıt",
            "motosiklet",
            "ticari hat",
            "ticari plaka"
        ]
    ):

        return (
            "Taşıt Finansmanı"
        )

    if (
        "ihtiyaç"
        in lower

        or "extra limit"
        in lower
    ):

        return (
            "İhtiyaç Finansmanı"
        )

    return "Finansman"


# =========================================================
# TABLO BAŞLIĞI
# =========================================================

def find_table_section_title(
    lines,
    vade_index
):

    for index in range(
        vade_index - 1,
        max(
            -1,
            vade_index - 9
        ),
        -1
    ):

        lower = tr_lower(
            lines[
                index
            ]
        )

        if any(
            keyword
            in lower

            for keyword
            in [
                "maliyet tablosu",
                "sigortalı",
                "sigortasız"
            ]
        ):

            return lines[
                index
            ]

    skip = {
        "finansman tutarı",
        "taksit tutarı",
        "kâr payı oranı",
        "kâr oranı",
        "kâr",
        "oranı",
        "tahsis ücreti",
        "aylık toplam maliyet",
        "yıllık toplam maliyet",
        "geri ödeme tutarı"
    }

    for index in range(
        vade_index - 1,
        max(
            -1,
            vade_index - 9
        ),
        -1
    ):

        line = lines[
            index
        ]

        if (
            tr_lower(
                line
            )
            in skip
        ):

            continue

        if len(
            line
        ) < 4:

            continue

        return line

    return "Maliyet Tablosu"


# =========================================================
# KÂR PAYI TABLOLARI
# =========================================================

def extract_rate_tables(
    text,
    title
):

    lines = repair_percent_lines(
        get_content_lines(
            text,
            title
        )
    )

    rates = []

    tahsis_fees = []

    header_terms = {
        "taksit tutarı",
        "kâr payı oranı",
        "kâr oranı",
        "kâr",
        "oranı",
        "tahsis ücreti",
        "aylık toplam maliyet",
        "yıllık toplam maliyet",
        "geri ödeme tutarı"
    }

    for vade_index, line in enumerate(
        lines
    ):

        if (
            tr_lower(
                line
            )
            != "vade"
        ):

            continue

        section = (
            find_table_section_title(
                lines,
                vade_index
            )
        )

        fast_amount_table = any(
            (
                tr_lower(
                    lines[
                        index
                    ]
                )
                == "finansman tutarı"
            )

            for index in range(
                max(
                    0,
                    vade_index - 3
                ),
                vade_index
            )
        )

        cursor = (
            vade_index + 1
        )

        while (
            cursor
            < len(lines)

            and tr_lower(
                lines[
                    cursor
                ]
            )
            in header_terms
        ):

            cursor += 1

        # =================================================
        # HIZLI FİNANSMAN İHTİYAÇ / EĞİTİM
        # =================================================

        if fast_amount_table:

            while (
                cursor
                < len(lines)
            ):

                current = lines[
                    cursor
                ]

                current_lower = (
                    tr_lower(
                        current
                    )
                )

                if (
                    cursor
                    > vade_index + 1

                    and current_lower
                    == "vade"
                ):

                    break

                if (
                    len(current) > 180

                    and not re.fullmatch(
                        r"\d+",
                        current
                    )
                ):

                    break

                vade_match = (
                    re.fullmatch(
                        r"(\d{1,3})",
                        current
                    )
                )

                if (
                    vade_match

                    and 1
                    <= int(
                        vade_match.group(1)
                    )
                    <= 180

                    and cursor + 1
                    < len(lines)

                    and "TL"
                    in lines[
                        cursor + 1
                    ].upper()
                ):

                    vade = int(
                        vade_match.group(1)
                    )

                    for rate_index in range(
                        cursor + 2,
                        min(
                            len(lines),
                            cursor + 7
                        )
                    ):

                        candidate = (
                            lines[
                                rate_index
                            ]
                        )

                        if re.fullmatch(
                            (
                                r"%?"
                                r"\d+"
                                r"(?:[.,]\d+)?"
                                r"%"
                            ),
                            candidate
                        ):

                            rates.append(
                                (
                                    f"{section} | "
                                    f"{vade} ay: "
                                    f"{normalize_percent(candidate)}"
                                )
                            )

                            break

                cursor += 1

            continue

        # =================================================
        # NORMAL 5 KOLONLU TABLOLAR
        # =================================================

        found_row = False

        while (
            cursor + 4
            < len(lines)
        ):

            current = lines[
                cursor
            ]

            current_lower = (
                tr_lower(
                    current
                )
            )

            if (
                current_lower
                == "vade"
            ):

                break

            if (
                found_row

                and (
                    "sigortalı"
                    in current_lower

                    or "sigortasız"
                    in current_lower

                    or "maliyet tablosu"
                    in current_lower
                )

                and not re.match(
                    r"^\d",
                    current
                )
            ):

                break

            if (
                len(current) > 180

                and not re.fullmatch(
                    r"\d+(?:\s*ay)?",
                    current,
                    flags=re.IGNORECASE
                )
            ):

                break

            vade_match = (
                re.fullmatch(
                    (
                        r"(\d{1,3})"
                        r"(?:\s*Ay)?"
                    ),
                    current,
                    flags=re.IGNORECASE
                )
            )

            if vade_match:

                vade = int(
                    vade_match.group(1)
                )

                values = lines[
                    cursor + 1:
                    cursor + 5
                ]

                if (
                    1
                    <= vade
                    <= 180

                    and len(
                        values
                    ) == 4

                    and all(
                        re.fullmatch(
                            (
                                r"%?"
                                r"\d+"
                                r"(?:[.,]\d+)?"
                                r"%"
                            ),
                            value
                        )

                        for value
                        in values
                    )
                ):

                    kar_orani = (
                        normalize_percent(
                            values[0]
                        )
                    )

                    tahsis_orani = (
                        normalize_percent(
                            values[1]
                        )
                    )

                    rates.append(
                        (
                            f"{section} | "
                            f"{vade} ay: "
                            f"{kar_orani}"
                        )
                    )

                    fee = (
                        f"{section} | "
                        f"Tahsis Ücreti: "
                        f"{tahsis_orani}"
                    )

                    if (
                        fee
                        not in tahsis_fees
                    ):

                        tahsis_fees.append(
                            fee
                        )

                    found_row = True

                    cursor += 5

                    continue

            cursor += 1

    return (
        unique(
            rates
        ),
        unique(
            tahsis_fees
        )
    )


# =========================================================
# KONUT FİNANSMAN ORANLARI
# =========================================================

def extract_konut_finansman_orani(
    text,
    title
):

    if (
        "konut"
        not in tr_lower(
            title
        )
    ):

        return []

    lines = repair_percent_lines(
        get_content_lines(
            text,
            title
        )
    )

    results = []

    current_table = ""

    for index, line in enumerate(
        lines
    ):

        lower = tr_lower(
            line
        )

        if (
            "ilk konut alımlarında "
            "ekspertiz değerine göre "
            "finansman tutarları"
            in lower
        ):

            current_table = (
                "İlk Konut"
            )

        elif (
            "mevcut konutu olup "
            "ikinci konut alımlarında "
            "ekspertiz değerine göre "
            "finansman tutarları"
            in lower
        ):

            current_table = (
                "İkinci Konut"
            )

        if not current_table:

            continue

        is_amount_band = (
            "milyon"
            in lower

            or bool(
                re.search(
                    (
                        r"\d[\d.]*"
                        r"\s*[–-]\s*"
                        r"\d[\d.]*"
                    ),
                    line
                )
            )
        )

        if not is_amount_band:

            continue

        percentages = []

        for next_index in range(
            index + 1,
            min(
                len(lines),
                index + 8
            )
        ):

            next_line = lines[
                next_index
            ]

            next_lower = tr_lower(
                next_line
            )

            if (
                next_index
                > index + 1

                and (
                    "milyon"
                    in next_lower

                    or re.search(
                        (
                            r"\d[\d.]*"
                            r"\s*[–-]\s*"
                            r"\d[\d.]*"
                        ),
                        next_line
                    )
                )
            ):

                break

            if re.fullmatch(
                (
                    r"%?"
                    r"\d+"
                    r"(?:[.,]\d+)?"
                    r"%"
                ),
                next_line
            ):

                percentages.append(
                    normalize_percent(
                        next_line
                    )
                )

                if len(
                    percentages
                ) == 3:

                    break

        if len(
            percentages
        ) == 3:

            results.append(
                (
                    f"{current_table} | "
                    f"{line}: "
                    f"A-B {percentages[0]}; "
                    f"C {percentages[1]}; "
                    f"D ve altı "
                    f"{percentages[2]}"
                )
            )

    return unique(
        results
    )


# =========================================================
# TAŞIT FİNANSMAN ORANI
# =========================================================

def percent_pattern(number):

    return (
        rf"(?:"
        rf"%\s*{number}\b"
        rf"|"
        rf"\b{number}\s*%"
        rf")"
    )


def extract_vehicle_finansman_orani(
    text,
    title
):

    if (
        detect_category(
            title
        )
        != "Taşıt Finansmanı"
    ):

        return []

    clean_text = (
        normalize_spaces(
            remove_invisible(
                text
            )
        )
    )

    results = []

    patterns = [
        (
            (
                r"(?:0\s*(?:TL)?\s*[-–]\s*)?"
                r"400\.?000\s*TL?"
                r"[^.!?]{0,180}?"
                + percent_pattern(
                    70
                )
            ),

            (
                "Araç değeri 0–400.000 TL: "
                "azami finansman oranı %70"
            )
        ),

        (
            (
                r"400\.?00[01]"
                r"[^.!?]{0,100}?"
                r"800\.?000\s*TL?"
                r"[^.!?]{0,180}?"
                + percent_pattern(
                    50
                )
            ),

            (
                "Araç değeri "
                "400.001–800.000 TL: "
                "azami finansman oranı %50"
            )
        ),

        (
            (
                r"800\.?00[01]"
                r"[^.!?]{0,100}?"
                r"1\.?200\.?000\s*TL?"
                r"[^.!?]{0,180}?"
                + percent_pattern(
                    30
                )
            ),

            (
                "Araç değeri "
                "800.001–1.200.000 TL: "
                "azami finansman oranı %30"
            )
        ),

        (
            (
                r"1\.?200\.?00[01]"
                r"[^.!?]{0,100}?"
                r"2\.?000\.?000\s*TL?"
                r"[^.!?]{0,180}?"
                + percent_pattern(
                    20
                )
            ),

            (
                "Araç değeri "
                "1.200.001–2.000.000 TL: "
                "azami finansman oranı %20"
            )
        )
    ]

    for (
        pattern,
        label
    ) in patterns:

        if re.search(
            pattern,
            clean_text,
            flags=re.IGNORECASE
        ):

            results.append(
                label
            )

    if re.search(
        (
            r"2\.?000\.?000\s*TL"
            r"[^.!?]{0,120}?"
            + percent_pattern(
                0
            )
        ),
        clean_text,
        flags=re.IGNORECASE
    ):

        results.append(
            (
                "Araç değeri 2.000.000 TL "
                "üzeri: finansman oranı %0"
            )
        )

    elif re.search(
        (
            r"2\.?000\.?001\s*TL"
            r"[^.!?]{0,160}?"
            r"kullandırım\s+yapılmayacaktır"
        ),
        clean_text,
        flags=re.IGNORECASE
    ):

        results.append(
            (
                "Araç değeri 2.000.001 TL "
                "üzeri: finansman kullandırılmaz"
            )
        )

    return unique(
        results
    )


def extract_finansman_orani(
    text,
    title
):

    category = detect_category(
        title
    )

    if (
        category
        == "Konut Finansmanı"
    ):

        return (
            extract_konut_finansman_orani(
                text,
                title
            )
        )

    if (
        category
        == "Taşıt Finansmanı"
    ):

        return (
            extract_vehicle_finansman_orani(
                text,
                title
            )
        )

    results = []

    for unit in sentence_units(
        text,
        title
    ):

        if "%" not in unit:

            continue

        if contains_any(
            unit,
            [
                "kâr",
                "kar oran",
                "maliyet",
                "tahsis"
            ]
        ):

            continue

        if contains_any(
            unit,
            [
                "finansman oranı",
                "oranında finansman",
                "kadar finansman"
            ]
        ):

            results.append(
                unit
            )

    return unique(
        results
    )


# =========================================================
# PARA / FİNANSMAN TUTARI
# =========================================================

def has_money(value):

    return bool(
        re.search(
            (
                r"\b"
                r"\d[\d.,]*"
                r"\s*"
                r"(?:bin\s+)?"
                r"TL\b"
            ),
            remove_invisible(
                value
            ),
            flags=re.IGNORECASE
        )
    )


def money_mention_count(value):

    return len(
        re.findall(
            (
                r"\b"
                r"\d[\d.]*"
                r"\s*TL\b"
            ),
            remove_invisible(
                value
            ),
            flags=re.IGNORECASE
        )
    )


def clean_finansman_tutari(
    results
):

    concise_tier_count = sum(
        1

        for item in results

        if (
            len(
                item
            ) < 180

            and "finansman tutar"
            in tr_lower(
                item
            )
        )
    )

    if (
        concise_tier_count
        >= 3
    ):

        results = [
            item

            for item in results

            if not (
                "125.000"
                in item

                and "250.000"
                in item

                and "36 ay"
                in tr_lower(
                    item
                )

                and "24 ay"
                in tr_lower(
                    item
                )

                and "12 ay"
                in tr_lower(
                    item
                )
            )
        ]

    return unique(
        results
    )


def extract_finansman_tutari(
    text,
    title
):

    title_lower = tr_lower(
        title
    )

    category = detect_category(
        title
    )

    results = []

    for unit in sentence_units(
        text,
        title
    ):

        lower = tr_lower(
            unit
        )

        if not has_money(
            unit
        ):

            continue

        if contains_any(
            unit,
            [
                "baz alınarak",
                "örnek ödeme",
                "örnek maliyet",
                "taksit tutarı",
                "geri ödeme tutarı"
            ]
        ):

            continue

        if (
            "trendyol"
            in title_lower

            and any(
                value
                in unit

                for value
                in [
                    "125.000",
                    "125.001",
                    "250.000"
                ]
            )
        ):

            continue

        if (
            category
            == "Taşıt Finansmanı"
        ):

            explicit_amount = (
                contains_any(
                    unit,
                    [
                        "finansman tutarı",
                        "finansman limiti",
                        "maksimum finansman"
                    ]
                )
            )

            explicit_single_amount = (
                (
                    "finansman kullanabilirsiniz"
                    in lower
                )

                and money_mention_count(
                    unit
                ) == 1

                and "%"
                not in unit

                and "oran"
                not in lower
            )

            if not (
                explicit_amount
                or explicit_single_amount
            ):

                continue

            if (
                contains_any(
                    unit,
                    [
                        "taşıt bedelinin",
                        "fatura değerinin"
                    ]
                )

                and "finansman tutarı"
                not in lower
            ):

                continue

        else:

            if not contains_any(
                unit,
                [
                    "finansman tutarı",
                    "finansman limiti",
                    "maksimum finansman",
                    "maximum finansman",
                    "finansman desteği",
                    "harcamanız",
                    "harcamalarınız",
                    "limit"
                ]
            ):

                continue

        results.append(
            unit
        )

    return (
        clean_finansman_tutari(
            results
        )[:15]
    )


# =========================================================
# VADE
# =========================================================

def clean_vade_entries(
    items,
    title
):

    title_lower = tr_lower(
        title
    )

    filtered = []

    for item in items:

        lower = tr_lower(
            item
        )

        if lower.startswith(
            "alınacak ücretler"
        ):

            continue

        if any(
            keyword
            in title_lower

            for keyword
            in [
                "trendyol",
                "extra limit"
            ]
        ):

            if (
                "125.000"
                in item

                and "250.000"
                in item
            ):

                continue

        filtered.append(
            item
        )

    items = filtered

    individual_need_rules = sum(
        1

        for item in items

        if (
            (
                "125.000"
                in item

                or "250.000"
                in item
            )

            and len(
                re.findall(
                    (
                        r"\b"
                        r"(?:12|24|36)"
                        r"\s*ay"
                    ),
                    tr_lower(
                        item
                    )
                )
            ) == 1
        )
    )

    if (
        individual_need_rules
        >= 3
    ):

        items = [
            item

            for item in items

            if not (
                "125.000"
                in item

                and "250.000"
                in item

                and "36 ay"
                in tr_lower(
                    item
                )

                and "24 ay"
                in tr_lower(
                    item
                )

                and "12 ay"
                in tr_lower(
                    item
                )
            )
        ]

    individual_band_count = 0

    for item in items:

        amounts = re.findall(
            (
                r"\b"
                r"\d{1,3}"
                r"(?:\.\d{3})+"
                r"\b"
            ),
            item
        )

        months = re.findall(
            r"\b(\d{1,3})\s*ay",
            tr_lower(
                item
            )
        )

        if (
            1
            <= len(amounts)
            <= 2

            and len(
                months
            ) == 1
        ):

            individual_band_count += 1

    result = []

    seen_band_signatures = set()

    for item in items:

        amounts = re.findall(
            (
                r"\b"
                r"\d{1,3}"
                r"(?:\.\d{3})+"
                r"\b"
            ),
            item
        )

        months = re.findall(
            r"\b(\d{1,3})\s*ay",
            tr_lower(
                item
            )
        )

        if (
            len(
                amounts
            ) > 2

            and individual_band_count
            >= 4
        ):

            continue

        if (
            1
            <= len(amounts)
            <= 2

            and len(
                months
            ) == 1
        ):

            signature = (
                tuple(
                    amount.replace(
                        ".",
                        ""
                    )

                    for amount
                    in amounts
                ),
                months[0]
            )

            if (
                signature
                in seen_band_signatures
            ):

                continue

            seen_band_signatures.add(
                signature
            )

        result.append(
            item
        )

    return unique(
        result
    )


def extract_vade(
    text,
    title
):

    results = []

    title_lower = tr_lower(
        title
    )

    for unit in sentence_units(
        text,
        title
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
                "tazminat",
                "vadesinden önce",
                "kaç ay vade"
            ]
        ):

            continue

        if lower.startswith(
            "alınacak ücretler"
        ):

            continue

        if (
            "trendyol"
            in title_lower

            and (
                "125.000"
                in unit

                or "250.000"
                in unit
            )
        ):

            continue

        if (
            "extra limit"
            in title_lower

            and (
                "125.000"
                in unit

                and "250.000"
                in unit
            )
        ):

            continue

        if not re.search(
            (
                r"\b"
                r"\d{1,3}"
                r"\s*"
                r"(?:"
                r"ay"
                r"|aya"
                r"|ayı"
                r"|aydır"
                r"|aylık"
                r")"
                r"\b"
            ),
            lower
        ):

            continue

        results.append(
            unit
        )

    return (
        clean_vade_entries(
            unique(
                results
            ),
            title
        )[:20]
    )


# =========================================================
# TAKSİT SAYISI - V4
#
# SADECE GERÇEK TAKSİT SAYISI / TAKSİTLENDİRME BİLGİSİ
#
# Artık şunları ALMIYOR:
#
# "Minimum taksitlendirme tutarı 100 TL"
# "ilk taksitte tahsil edilir"
# "taksit sayısını ertesi gün değiştirebilirsiniz"
# "Taksitli Ticari Araç ..." (ürün adı)
#
# =========================================================

def extract_taksit_sayisi(
    text,
    title
):

    results = []

    for unit in sentence_units(
        text,
        title
    ):

        lower = tr_lower(
            unit
        )

        if (
            "taksit"
            not in lower
        ):

            continue

        # =================================================
        # KESİN FALSE POSITIVE
        # =================================================

        if contains_any(
            unit,
            [
                "taksit tutarı",
                "minimum taksitlendirme tutarı",
                "ilk taksitte tahsil",
                "taksit sayısını harcama yaptığınız",
                "taksit sayınızı harcama yaptığınız",
                "taksit sayısını değiştirebilirsiniz",
                "taksit sayınızı değiştirebilirsiniz",
                "aylık maksimum taksit tutarı"
            ]
        ):

            continue

        # =================================================
        # SADECE ÜRÜN ADINDA "TAKSİTLİ" GEÇMESİ
        #
        # Örnek:
        # "Taksitli Ticari Araç Finansmanını
        # 0 km veya 2. el araçlarda kullanabilirsiniz"
        #
        # Bu taksit sayısı değildir.
        # =================================================

        direct_installment_number = bool(
            re.search(
                (
                    r"\b"
                    r"\d{1,3}"
                    r"\s*"
                    r"(?:"
                    r"taksit"
                    r"|taksitle"
                    r"|taksitli"
                    r")"
                    r"\b"
                ),
                lower
            )
        )

        month_installment = bool(
            re.search(
                (
                    r"\b"
                    r"\d{1,3}"
                    r"\s*"
                    r"(?:ay|aya)"
                    r"\s*"
                    r"(?:kadar\s*)?"
                    r"(?:"
                    r"taksitlendir"
                    r"|taksitlendirme"
                    r")"
                ),
                lower
            )
        )

        category_installment_limits = (
            contains_any(
                unit,
                [
                    "taksit ile sınırlandırılmıştır",
                    "taksitle sınırlandırılmıştır",
                    "taksit ile sınırlıdır",
                    "taksitle sınırlıdır"
                ]
            )

            and bool(
                re.search(
                    r"\b(?:2|3|4|5|6|9|10|12|18|24|36|48)\b",
                    lower
                )
            )
        )

        explicit_installment_count = bool(
            re.search(
                (
                    r"taksit\s+sayısı"
                    r"\s*[:\-]?\s*"
                    r"\d{1,3}"
                ),
                lower
            )
        )

        # =================================================
        # HIZLI TAŞIT'TAKİ ORAN/Vade CÜMLESİ
        #
        # "... %70 ... %50 ... %30 ... %20'ye kadar
        # taksit yapabilirsiniz"
        #
        # Bu bir taksit sayısı değil.
        # =================================================

        if (
            contains_any(
                unit,
                [
                    "azami oranı",
                    "fatura değerinin"
                ]
            )

            and "%"
            in unit
        ):

            continue

        if not any(
            [
                direct_installment_number,
                month_installment,
                category_installment_limits,
                explicit_installment_count
            ]
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

def extract_masraf_bilgisi(
    text,
    title,
    table_tahsis
):

    results = []

    for unit in sentence_units(
        text,
        title
    ):

        if contains_any(
            unit,
            [
                "tahsis ücreti",
                "ekspertiz ücreti",
                "ipotek tesis ücreti",
                "ipotek fek",
                "sigorta masrafları",
                "ücret ve masraf"
            ]
        ):

            if (
                tr_lower(
                    unit
                )
                == "tahsis ücreti"
            ):

                continue

            results.append(
                unit
            )

    results.extend(
        table_tahsis
    )

    return unique(
        results
    )[:20]


# =========================================================
# HEDEF KİTLE
# =========================================================

def extract_hedef_kitle(
    text,
    title
):

    results = []

    for unit in sentence_units(
        text,
        title
    ):

        lower = tr_lower(
            unit
        )

        if len(
            unit
        ) > 450:

            continue

        if (
            "kimler yararlanabilir"
            in lower

            or "kimler başvurabilir"
            in lower
        ):

            continue

        strong_target = (
            (
                "başvurusu yapabilir"
                in lower

                and any(
                    keyword
                    in lower

                    for keyword
                    in [
                        "müşteri",
                        "18 yaş",
                        "bireysel"
                    ]
                )
            )

            or (
                "yararlanabilir"
                in lower

                and any(
                    keyword
                    in lower

                    for keyword
                    in [
                        "gerçek kişiler",
                        "sahibi olan",
                        "müşteri"
                    ]
                )
            )

            or (
                "müşterisi olmanız gerekir"
                in lower
            )

            or (
                "bireysel kişiler"
                in lower

                and "finansman"
                in lower
            )

            or (
                "gerçek kişilere"
                in lower

                and "finansman"
                in lower
            )

            or (
                "kendiniz ya da çocuğunuz"
                in lower

                and "eğitim"
                in lower
            )

            or (
                "özel okullar"
                in lower

                and "eğitim finansmanı"
                in lower
            )
        )

        if not strong_target:

            continue

        if contains_any(
            unit,
            [
                "ekspertiz ücreti",
                "müşterisi değilseniz",
                "atm",
                "eft",
                "havale"
            ]
        ):

            continue

        results.append(
            unit
        )

    return unique(
        results
    )[:10]


# =========================================================
# AVANTAJ
# =========================================================

def extract_advantages(
    text,
    title
):

    results = []

    for unit in sentence_units(
        text,
        title
    ):

        if len(
            unit
        ) > 400:

            continue

        lower = tr_lower(
            unit
        )

        if not any(
            keyword
            in lower

            for keyword
            in [
                "avantajlı",
                "ödemeye 3 ay sonra",
                "ücretsiz",
                "masrafsız",
                "indirim",
                "kart aidatı",
                "üyelik ücreti",
                "hesap ücreti"
            ]
        ):

            continue

        if (
            "avantajları"
            in lower

            and len(
                unit
            ) < 90
        ):

            continue

        results.append(
            unit
        )

    return unique(
        results
    )[:10]


# =========================================================
# PARA BİRİMİ
# =========================================================

def extract_para_birimi(text):

    results = []

    if re.search(
        r"\bTL\b|₺|Türk\s+Lirası",
        text,
        flags=re.IGNORECASE
    ):

        results.append(
            "TRY"
        )

    if re.search(
        r"\bUSD\b|ABD\s+Doları",
        text,
        flags=re.IGNORECASE
    ):

        results.append(
            "USD"
        )

    if re.search(
        r"\bEUR\b|\bEuro\b|\bAvro\b",
        text,
        flags=re.IGNORECASE
    ):

        results.append(
            "EUR"
        )

    if (
        "döviz"
        in tr_lower(
            text
        )

        and "USD"
        not in results

        and "EUR"
        not in results
    ):

        results.append(
            "DÖVİZ"
        )

    return results


# =========================================================
# KOŞULLAR
# =========================================================

def extract_kosullar(
    text,
    title
):

    results = []

    title_lower = tr_lower(
        title
    )

    keywords = [
        "maksimum",
        "maximum",
        "en fazla",
        "en az",

        "gerekmektedir",
        "gerekir",
        "gereklidir",

        "başvuru",

        "kefil",
        "teminat",

        "proforma",
        "ruhsat",
        "gelir belgesi",
        "kimlik",

        "müşterisi olmanız",

        "sınırl",
        "aşamaz",

        "kullanabilirsiniz",
        "kullanılamaz",

        "kullandırım yapılmayacaktır",

        "0 km",
        "2. el",

        "7 yaş",
        "100 cc",

        "finansman tutarı"
    ]

    for unit in sentence_units(
        text,
        title
    ):

        lower = tr_lower(
            unit
        )

        if (
            len(unit) < 20

            or len(unit) > 600
        ):

            continue

        if contains_any(
            unit,
            [
                "başvuru merkezi",
                "hesaplama aracına gitmek",
                "başvuru sonucumu nasıl"
            ]
        ):

            continue

        if (
            "trendyol"
            in title_lower

            and (
                "125.000"
                in unit

                or "250.000"
                in unit
            )
        ):

            continue

        if (
            "extra limit"
            in title_lower

            and (
                "125.000"
                in unit

                and "250.000"
                in unit
            )
        ):

            continue

        if any(
            keyword
            in lower

            for keyword
            in keywords
        ):

            results.append(
                unit
            )

    return unique(
        results
    )[:35]


# =========================================================
# KAYNAK UYARILARI
# =========================================================

def detect_source_warnings(
    record
):

    warnings = []

    title = tr_lower(
        record[
            "urun_adi"
        ]
    )

    if (
        "hızlı finansman - eğitim finansmanı"
        in title
    ):

        joined_vade = tr_lower(
            " ".join(
                record[
                    "vade"
                ]
            )
        )

        has_12 = bool(
            re.search(
                r"\b12\s+aya",
                joined_vade
            )
        )

        has_18 = bool(
            re.search(
                r"\b18\s+ay",
                joined_vade
            )
        )

        if (
            has_12
            and has_18
        ):

            warnings.append(
                (
                    "Kaynak vade tutarsızlığı: "
                    "sayfanın açıklama bölümünde "
                    "12 aya varan vade, maliyet "
                    "tablosu açıklamasında ise "
                    "maksimum 18 ay yazıyor. "
                    "Her iki kaynak bilgisi de "
                    "korundu."
                )
            )

    return warnings


# =========================================================
# ŞÜPHELİ KÂR
# =========================================================

def find_suspicious_rates(
    records
):

    suspicious = []

    for record in records:

        for item in record[
            "kar_payi_orani"
        ]:

            match = re.search(
                r":\s*%(\d+(?:,\d+)?)",
                item
            )

            if not match:

                continue

            try:

                value = float(
                    match.group(1).replace(
                        ",",
                        "."
                    )
                )

            except ValueError:

                continue

            if value > 20:

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
# ŞÜPHELİ TAHSİS
# =========================================================

def find_suspicious_tahsis(
    records
):

    suspicious = []

    for record in records:

        for item in record[
            "masraf_bilgisi"
        ]:

            if (
                "Tahsis Ücreti:"
                not in item
            ):

                continue

            match = re.search(
                r"%(\d+(?:,\d+)?)",
                item
            )

            if not match:

                continue

            try:

                value = float(
                    match.group(1).replace(
                        ",",
                        "."
                    )
                )

            except ValueError:

                continue

            if value > 2:

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
# ŞÜPHELİ VADE
# =========================================================

def find_suspicious_vade(
    records
):

    suspicious = []

    for record in records:

        title_lower = tr_lower(
            record[
                "urun_adi"
            ]
        )

        for item in record[
            "vade"
        ]:

            lower = tr_lower(
                item
            )

            bad = False

            if lower.startswith(
                "alınacak ücretler"
            ):

                bad = True

            if contains_any(
                item,
                [
                    "erken ödeme",
                    "kalan vade",
                    "tazminat"
                ]
            ):

                bad = True

            if (
                "trendyol"
                in title_lower

                and (
                    "125.000"
                    in item

                    or "250.000"
                    in item
                )
            ):

                bad = True

            if bad:

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
# ŞÜPHELİ FİNANSMAN TUTARI
# =========================================================

def find_suspicious_amounts(
    records
):

    suspicious = []

    for record in records:

        if (
            record[
                "urun_kategorisi"
            ]
            != "Taşıt Finansmanı"
        ):

            continue

        for item in record[
            "finansman_tutari"
        ]:

            lower = tr_lower(
                item
            )

            if (
                contains_any(
                    item,
                    [
                        "araçlar için maksimum vade",
                        "taşıt bedelinin",
                        "fatura değerinin"
                    ]
                )

                and "finansman tutarı"
                not in lower
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
# ŞÜPHELİ TAKSİT - V4
# =========================================================

def find_suspicious_taksit(
    records
):

    suspicious = []

    for record in records:

        for item in record[
            "taksit_sayisi"
        ]:

            lower = tr_lower(
                item
            )

            if contains_any(
                item,
                [
                    "minimum taksitlendirme tutarı",
                    "ilk taksitte tahsil",
                    "taksit sayısını harcama yaptığınız",
                    "taksit sayınızı harcama yaptığınız",
                    "taksit tutarı"
                ]
            ):

                suspicious.append(
                    (
                        record[
                            "urun_adi"
                        ],
                        item
                    )
                )

                continue

            if (
                contains_any(
                    item,
                    [
                        "azami oranı",
                        "fatura değerinin"
                    ]
                )

                and "%"
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

                continue

            has_direct_number = bool(
                re.search(
                    (
                        r"\b"
                        r"\d{1,3}"
                        r"\s*"
                        r"(?:"
                        r"taksit"
                        r"|taksitle"
                        r"|taksitli"
                        r")"
                    ),
                    lower
                )
            )

            has_month_installment = bool(
                re.search(
                    (
                        r"\b"
                        r"\d{1,3}"
                        r"\s*"
                        r"(?:ay|aya)"
                        r"\s*"
                        r"(?:kadar\s*)?"
                        r"(?:"
                        r"taksitlendir"
                        r"|taksitlendirme"
                        r")"
                    ),
                    lower
                )
            )

            has_limit = (
                contains_any(
                    item,
                    [
                        "taksit ile sınırlandırılmıştır",
                        "taksitle sınırlandırılmıştır",
                        "taksit ile sınırlıdır",
                        "taksitle sınırlıdır"
                    ]
                )
            )

            if not (
                has_direct_number
                or has_month_installment
                or has_limit
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
# RECORD
# =========================================================

def create_record(product):

    title = normalize_spaces(
        product.get(
            "urun_adi",
            ""
        )
    )

    raw_text = str(
        product.get(
            "ham_metin",
            ""
        )
    ).strip()

    (
        kar_rates,
        table_tahsis
    ) = extract_rate_tables(
        raw_text,
        title
    )

    record = {
        "banka": (
            "Türkiye Finans Katılım Bankası"
        ),

        "kayit_turu": (
            "finansman"
        ),

        "urun_adi": (
            title
        ),

        "urun_kategorisi": (
            detect_category(
                title
            )
        ),

        "kar_payi_orani": (
            kar_rates
        ),

        "finansman_orani": (
            extract_finansman_orani(
                raw_text,
                title
            )
        ),

        "finansman_tutari": (
            extract_finansman_tutari(
                raw_text,
                title
            )
        ),

        "vade": (
            extract_vade(
                raw_text,
                title
            )
        ),

        "taksit_sayisi": (
            extract_taksit_sayisi(
                raw_text,
                title
            )
        ),

        "masraf_bilgisi": (
            extract_masraf_bilgisi(
                raw_text,
                title,
                table_tahsis
            )
        ),

        "kampanya_turu": "",

        "kampanya_avantaji": (
            extract_advantages(
                raw_text,
                title
            )
        ),

        "kampanya_suresi": "",

        "hedef_kitle": (
            extract_hedef_kitle(
                raw_text,
                title
            )
        ),

        "para_birimi": (
            extract_para_birimi(
                raw_text
            )
        ),

        "kosullar": (
            extract_kosullar(
                raw_text,
                title
            )
        ),

        "kaynak_url": (
            normalize_spaces(
                product.get(
                    "kaynak_url",
                    ""
                )
            )
        ),

        "ham_metin": (
            raw_text
        )
    }

    warnings = (
        detect_source_warnings(
            record
        )
    )

    return (
        record,
        warnings
    )


# =========================================================
# ŞEMA
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
                f"{record.get('urun_adi')} -> "
                f"eksik alan: {missing}"
            )
        )

    for field in LIST_FIELDS:

        if not isinstance(
            record[
                field
            ],
            list
        ):

            raise ValueError(
                (
                    f"{record['urun_adi']} -> "
                    f"{field} list değil."
                )
            )

    if (
        record[
            "kayit_turu"
        ]
        != "finansman"
    ):

        raise ValueError(
            (
                f"{record['urun_adi']} -> "
                "kayit_turu hatalı."
            )
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
                "kaynak URL boş."
            )
        )

    if not record[
        "ham_metin"
    ]:

        raise ValueError(
            (
                f"{record['urun_adi']} -> "
                "ham metin boş."
            )
        )


# =========================================================
# ÜRÜN BUL
# =========================================================

def find_product(
    records,
    target_name
):

    target = tr_lower(
        target_name
    )

    for record in records:

        if (
            tr_lower(
                record[
                    "urun_adi"
                ]
            )
            == target
        ):

            return record

    for record in records:

        if (
            target
            in tr_lower(
                record[
                    "urun_adi"
                ]
            )
        ):

            return record

    return None


# =========================================================
# TABLO KONTROL
# =========================================================

def print_table_check(
    records,
    product_name,
    expected_count
):

    record = find_product(
        records,
        product_name
    )

    if not record:

        print(
            (
                f"{product_name}: "
                "ÜRÜN BULUNAMADI"
            )
        )

        return

    actual = len(
        record[
            "kar_payi_orani"
        ]
    )

    status = (
        "OK"
        if actual == expected_count
        else "KONTROL"
    )

    print(
        (
            f"{product_name}: "
            f"{actual} "
            f"(beklenen {expected_count}) "
            f"[{status}]"
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

    products = raw_data.get(
        "urunler",
        []
    )

    print()

    print(
        "=" * 95
    )

    print(
        "TÜRKİYE FİNANS FİNANSMAN EXTRACTOR V4"
    )

    print(
        "=" * 95
    )

    print(
        "RAW ürün:",
        len(
            products
        )
    )

    if len(
        products
    ) != EXPECTED_COUNT:

        raise ValueError(
            (
                "Beklenen RAW ürün sayısı "
                f"{EXPECTED_COUNT}, "
                f"gelen {len(products)}."
            )
        )

    records = []

    all_warnings = []

    for index, product in enumerate(
        products,
        start=1
    ):

        (
            record,
            warnings
        ) = create_record(
            product
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

                    "warning": (
                        warning
                    )
                }
            )

        print()

        print(
            "-" * 95
        )

        print(
            (
                f"[{index}/{len(products)}] "
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
            "Kâr oranı:",
            len(
                record[
                    "kar_payi_orani"
                ]
            )
        )

        print(
            "Finansman oranı:",
            len(
                record[
                    "finansman_orani"
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
    # SEMANTİK KONTROLLER
    # =====================================================

    suspicious_rates = (
        find_suspicious_rates(
            records
        )
    )

    suspicious_tahsis = (
        find_suspicious_tahsis(
            records
        )
    )

    suspicious_vade = (
        find_suspicious_vade(
            records
        )
    )

    suspicious_amounts = (
        find_suspicious_amounts(
            records
        )
    )

    suspicious_taksit = (
        find_suspicious_taksit(
            records
        )
    )

    # =====================================================
    # JSON
    # =====================================================

    output = {
        "banka": (
            "Türkiye Finans Katılım Bankası"
        ),

        "kayit_turu": (
            "finansman"
        ),

        "toplam_kayit": (
            len(
                records
            )
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

    no_kar = [
        record[
            "urun_adi"
        ]

        for record in records

        if not record[
            "kar_payi_orani"
        ]
    ]

    no_vade = [
        record[
            "urun_adi"
        ]

        for record in records

        if not record[
            "vade"
        ]
    ]

    no_amount = [
        record[
            "urun_adi"
        ]

        for record in records

        if not record[
            "finansman_tutari"
        ]
    ]

    no_target = [
        record[
            "urun_adi"
        ]

        for record in records

        if not record[
            "hedef_kitle"
        ]
    ]

    print()

    print(
        "=" * 95
    )

    print(
        "GENEL KONTROL"
    )

    print(
        "=" * 95
    )

    print(
        "Toplam kayıt:",
        len(
            records
        )
    )

    print(
        "Kâr oranı boş:",
        len(
            no_kar
        )
    )

    print(
        "Vade boş:",
        len(
            no_vade
        )
    )

    print(
        "Açık finansman tutarı bulunmayan:",
        len(
            no_amount
        )
    )

    print(
        "Açık hedef kitle bulunmayan:",
        len(
            no_target
        )
    )

    print(
        "Şüpheli kâr oranı:",
        len(
            suspicious_rates
        )
    )

    print(
        "Şüpheli tahsis ücreti:",
        len(
            suspicious_tahsis
        )
    )

    print(
        "Yanlış vade bağlamı:",
        len(
            suspicious_vade
        )
    )

    print(
        "Şüpheli finansman tutarı:",
        len(
            suspicious_amounts
        )
    )

    print(
        "Şüpheli taksit bilgisi:",
        len(
            suspicious_taksit
        )
    )

    print(
        "Kaynak uyarısı:",
        len(
            all_warnings
        )
    )

    if suspicious_taksit:

        print()

        print(
            "ŞÜPHELİ TAKSİT BİLGİLERİ:"
        )

        for (
            name,
            item
        ) in suspicious_taksit:

            print(
                "-",
                name
            )

            print(
                " ",
                item
            )

    if all_warnings:

        print()

        print(
            "KAYNAK UYARILARI:"
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
    # KÂR TABLO KONTROLLERİ
    # =====================================================

    print()

    print(
        "=" * 95
    )

    print(
        "KRİTİK KÂR ORANI TABLO KONTROLLERİ"
    )

    print(
        "=" * 95
    )

    table_checks = [
        (
            "İhtiyaç Finansmanı (İhtiyaç Kredisi)*",
            12
        ),
        (
            "Taşıt Finansmanı (Taşıt Kredisi)*",
            28
        ),
        (
            "Konut Finansmanı (Konut Kredisi)*",
            40
        ),
        (
            "Arsa Finansmanı (Arsa Kredisi)*",
            18
        ),
        (
            "İş yeri Finansmanı (İş yeri Kredisi)*",
            18
        ),
        (
            "eXtra Limit",
            4
        ),
        (
            "Dijital İhtiyaç Finansmanı (Dijital İhtiyaç Kredisi)*",
            12
        ),
        (
            "Trendyol Alışveriş Finansmanı",
            4
        ),
        (
            "Dijital Taşıt Finansmanı",
            28
        ),
        (
            "Motosiklet Finansmanı (Motosiklet Kredisi)*",
            14
        ),
        (
            "Ticari Hat / Ticari Plaka Finansmanı (Ticari Hat / Ticari Plaka Kredisi)*",
            4
        ),
        (
            "Taksitli Ticari Taşıt Finansmanı (Taksitli Ticari Taşıt Kredisi)*",
            4
        ),
        (
            "Hızlı Finansman - İhtiyaç Finansmanı",
            6
        ),
        (
            "Hızlı Finansman - Eğitim Finansmanı",
            2
        ),
        (
            "Hızlı Finansman - Taşıt Finansmanı",
            4
        ),
        (
            "Hızlı Finansman - Motosiklet Finansmanı",
            4
        )
    ]

    for (
        product_name,
        expected
    ) in table_checks:

        print_table_check(
            records,
            product_name,
            expected
        )

    # =====================================================
    # V4 TAKSİT KONTROLLERİ
    # =====================================================

    print()

    print(
        "=" * 95
    )

    print(
        "V4 TAKSİT SAYISI KONTROLLERİ"
    )

    print(
        "=" * 95
    )

    taksit_check_products = [
        "Taşıt Finansmanı (Taşıt Kredisi)*",
        "eXtra Limit",
        "Trendyol Alışveriş Finansmanı",
        "Taksitli Ticari Taşıt Finansmanı (Taksitli Ticari Taşıt Kredisi)*",
        "Hızlı Finansman - İhtiyaç Finansmanı",
        "Hızlı Finansman - Taşıt Finansmanı",
        "Hızlı Finansman - Motosiklet Finansmanı"
    ]

    for name in taksit_check_products:

        record = find_product(
            records,
            name
        )

        if not record:

            continue

        print()

        print(
            record[
                "urun_adi"
            ]
        )

        print(
            "  Taksit sayısı:"
        )

        if not record[
            "taksit_sayisi"
        ]:

            print(
                "    []"
            )

        else:

            for item in record[
                "taksit_sayisi"
            ]:

                print(
                    "    -",
                    item
                )

    # =====================================================
    # FINAL
    # =====================================================

    print()

    print(
        "=" * 95
    )

    print(
        "EXTRACTOR V4 TAMAMLANDI"
    )

    print(
        "=" * 95
    )

    print(
        "İşlenen ürün:",
        len(
            records
        )
    )

    print(
        "Şema kontrolü: BAŞARILI"
    )

    print(
        "Şüpheli kâr oranı:",
        len(
            suspicious_rates
        )
    )

    print(
        "Şüpheli tahsis ücreti:",
        len(
            suspicious_tahsis
        )
    )

    print(
        "Yanlış vade bağlamı:",
        len(
            suspicious_vade
        )
    )

    print(
        "Şüpheli finansman tutarı:",
        len(
            suspicious_amounts
        )
    )

    print(
        "Şüpheli taksit bilgisi:",
        len(
            suspicious_taksit
        )
    )

    print(
        "JSON:",
        OUTPUT_FILE
    )

    print(
        "=" * 95
    )


if __name__ == "__main__":

    main()