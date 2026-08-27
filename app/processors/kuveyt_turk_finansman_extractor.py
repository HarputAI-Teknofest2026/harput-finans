import json
import os
import re


INPUT_FILE = (
    "data/raw/"
    "kuveyt_turk_finansman_urunleri.json"
)

OUTPUT_FILE = (
    "data/processed/"
    "kuveyt_turk_finansman_extracted.json"
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

    # 10,000 TL -> 10.000 TL
    value = re.sub(
        r"\b(\d{1,3}),(\d{3})\s*TL\b",
        r"\1.\2 TL",
        value
    )

    # % 4.82 -> %4,82
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

    # 4,82 % -> %4,82
    value = re.sub(
        r"(?<![%\d])"
        r"(\d+(?:[.,]\d+)?)\s*%",
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


        key = item.casefold()


        if key in seen:
            continue


        seen.add(
            key
        )

        result.append(
            item
        )


    return result


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


def contains_any(
    text,
    words
):

    lowered = text.casefold()


    return any(
        word.casefold()
        in lowered

        for word
        in words
    )


# =========================================================
# YÜZDE SATIRI
# =========================================================

def parse_percent_line(line):

    match = re.fullmatch(
        r"\s*%?\s*"
        r"(\d+(?:[.,]\d+)?)"
        r"\s*%?\s*",
        line
    )


    if not match:
        return None


    if "%" not in line:
        return None


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

        return None


    return (
        value,
        numeric
    )


# =========================================================
# KATEGORİ
# =========================================================

def detect_category(
    url,
    title
):

    url_lower = url.casefold()

    title_lower = title.casefold()


    if (
        "/surdurulebilir-finansmanlar/"
        in url_lower
    ):

        return (
            "Sürdürülebilir Finansman"
        )


    if (
        "/konut-finansmanlari/"
        in url_lower
    ):

        return (
            "Konut Finansmanı"
        )


    if (
        "/arac-finansmanlari/"
        in url_lower
    ):

        return (
            "Araç Finansmanı"
        )


    if (
        "/alisveris-finansmanlari/"
        in url_lower
    ):

        return (
            "Alışveriş Finansmanı"
        )


    if (
        "/ihtiyac-finansmanlari/"
        in url_lower
    ):

        return (
            "İhtiyaç Finansmanı"
        )


    if "konut" in title_lower:

        return (
            "Konut Finansmanı"
        )


    if contains_any(
        title,
        [
            "araç",
            "motosiklet",
            "togg"
        ]
    ):

        return (
            "Araç Finansmanı"
        )


    return "Finansman"


# =========================================================
# PARA BİRİMİ
# =========================================================

def extract_para_birimi(text):

    result = []


    # TL
    if re.search(
        r"(?:"
        r"\bTL\b"
        r"|₺"
        r"|\bTürk\s+Lirası\b"
        r")",
        text,
        flags=re.IGNORECASE
    ):

        result.append(
            "TRY"
        )


    # USD
    if re.search(
        r"\b(?:"
        r"USD"
        r"|ABD\s+Doları"
        r"|Amerikan\s+Doları"
        r")\b",
        text,
        flags=re.IGNORECASE
    ):

        result.append(
            "USD"
        )


    # EUR
    #
    # Word boundary önemli:
    # Europeprintshop -> EUR SAYILMAMALI.
    if re.search(
        r"\b(?:"
        r"EUR"
        r"|Euro"
        r"|Avro"
        r")\b",
        text,
        flags=re.IGNORECASE
    ):

        result.append(
            "EUR"
        )


    # Kaynak sadece "döviz" diyorsa
    # hangi döviz olduğunu uydurmuyoruz.
    if re.search(
        r"(?:"
        r"\bdöviz\s+cinsinden\b"
        r"|"
        r"\byabancı\s+para\s+cinsinden\b"
        r")",
        text,
        flags=re.IGNORECASE
    ):

        result.append(
            "DÖVİZ"
        )


    return unique(
        result
    )


# =========================================================
# ÖRNEK MALİYET TABLOSUNDAN
# KÂR ORANI
# =========================================================

def extract_kar_payi_orani(text):

    lines = get_lines(
        text
    )

    results = []


    valid_headers = {
        "kâr oranı",
        "kar oranı",
        "aylık kâr oranı",
        "aylık kar oranı"
    }


    for index, line in enumerate(
        lines
    ):

        header = line.casefold()


        if (
            header
            not in valid_headers
        ):

            continue


        amount = None

        term = None


        # Header'dan sonraki tablo değerlerini tara.
        for position in range(
            index + 1,
            min(
                len(lines),
                index + 16
            )
        ):

            current = lines[
                position
            ]


            # 10.000 TL / 10,000 TL
            if re.fullmatch(
                r"\d[\d.,]*\s*TL",
                current,
                flags=re.IGNORECASE
            ):

                amount = (
                    normalize_financial_text(
                        current
                    )
                )


            # 12 Ay
            if re.fullmatch(
                r"\d+\s*Ay",
                current,
                flags=re.IGNORECASE
            ):

                term = (
                    normalize_spaces(
                        current
                    )
                )


            percent = (
                parse_percent_line(
                    current
                )
            )


            if not percent:
                continue


            value, numeric = percent


            # Hesaplama widget'ındaki %0
            # gerçek oran değildir.
            if numeric == 0:
                continue


            # Örnek tablo olduğunu doğrula
            if (
                amount
                and term
            ):

                if (
                    "aylık"
                    in header
                ):

                    label = (
                        "aylık kâr oranı"
                    )

                else:

                    label = (
                        "kâr oranı"
                    )


                results.append(
                    (
                        f"Örnek hesaplama "
                        f"({amount}, {term}): "
                        f"{label} %{value}"
                    )
                )

                break


    return unique(
        results
    )


# =========================================================
# ARAÇ / MOTOSİKLET / TOGG TABLOLARI
# =========================================================

def extract_vehicle_table(text):

    lines = get_lines(
        text
    )

    results = []


    for index in range(
        len(lines) - 2
    ):

        band = lines[
            index
        ]


        if "TL" not in band:
            continue


        # Fiyat aralığı mı?
        if not re.search(
            r"(?:"
            r"\d[\d.]*\s*-\s*\d[\d.]*"
            r"|"
            r"ve\s+üzeri"
            r"|"
            r"ve\s+altında"
            r"|"
            r"ila"
            r")",
            band,
            flags=re.IGNORECASE
        ):

            continue


        percent = (
            parse_percent_line(
                lines[
                    index + 1
                ]
            )
        )


        if not percent:
            continue


        value, _ = percent


        next_line = lines[
            index + 2
        ]


        # Örnek:
        #
        # 0 - 400.000 TL
        # %70
        # 48
        if re.fullmatch(
            r"\d+",
            next_line
        ):

            results.append(
                (
                    f"{band}: "
                    f"azami finansman oranı "
                    f"%{value}, "
                    f"vade üst sınırı "
                    f"{next_line} ay"
                )
            )


        # Örnek:
        #
        # 2.000.001 TL ve üzeri
        # %0
        # Kullandırım yapılmayacaktır.
        elif (
            "kullandırım"
            in next_line.casefold()
        ):

            results.append(
                (
                    f"{band}: "
                    f"finansman oranı "
                    f"%{value}; "
                    f"{next_line.rstrip('.')}"
                )
            )


    return unique(
        results
    )


# =========================================================
# KONUT ENERJİ SINIFI TABLOSU
# =========================================================

def extract_housing_table(text):

    results = []


    normalized = normalize_spaces(
        text
    )


    pattern = re.compile(
        r"("
        r"5\s*milyona\s+kadar\s+konutlar"
        r"|"
        r"5\s*-\s*7\s*milyon\s+arasındaki\s+konutlar"
        r"|"
        r"7\s*-\s*10\s*milyon\s+arasındaki\s+konutlar"
        r"|"
        r"10\s*-\s*20\s*milyon\s+arasındaki\s+konutlar"
        r"|"
        r"20\s*milyon\s+üzeri\s+konutlar"
        r")"
        r"\s*%?\s*(\d+(?:[.,]\d+)?)"
        r"\s*%?\s*(\d+(?:[.,]\d+)?)"
        r"\s*%?\s*(\d+(?:[.,]\d+)?)",
        flags=re.IGNORECASE
    )


    for match in pattern.finditer(
        normalized
    ):

        band = normalize_spaces(
            match.group(1)
        )


        ab = (
            match.group(2)
            .replace(
                ".",
                ","
            )
        )

        c_class = (
            match.group(3)
            .replace(
                ".",
                ","
            )
        )

        other = (
            match.group(4)
            .replace(
                ".",
                ","
            )
        )


        results.append(
            (
                f"{band}: "
                f"A-B enerji sınıfı %{ab}; "
                f"C enerji sınıfı %{c_class}; "
                f"diğer %{other}"
            )
        )


    return unique(
        results
    )


# =========================================================
# FİNANSMAN ORANI
# =========================================================

def extract_finansman_orani(text):

    results = []


    # Araç / motosiklet / TOGG
    results.extend(
        extract_vehicle_table(
            text
        )
    )


    # Konut tabloları
    results.extend(
        extract_housing_table(
            text
        )
    )


    for line in get_lines(
        text
    ):

        lower = line.casefold()


        if "%" not in line:
            continue


        # Bunlar finansman oranı değildir.
        if contains_any(
            line,
            [
                "tahsis ücreti",
                "dosya masrafı",
                "maliyet oranı",
                "kâr oranı",
                "kar oranı",
                "indirim",
                "azalmaktadır",
                "azalır",
                "tamamlanmış"
            ]
        ):

            continue


        # Örnek:
        # Arazi değerinin %100’üne kadar
        # finansman kullanılabilir.
        #
        # Ekspertiz değerinin %50’si
        # tutarında finansman kullanılabilir.
        if (
            "finansman"
            in lower
            and contains_any(
                line,
                [
                    "değerinin",
                    "tutarının",
                    "finansman oranı",
                    "finansman kullanılabilir",
                    "finansman kullanabilir",
                    "kadar finansman"
                ]
            )
        ):

            results.append(
                line
            )


    return unique(
        results
    )


# =========================================================
# FİNANSMAN TUTARI / LİMİT
# =========================================================

def extract_finansman_tutari(text):

    results = []


    for line in get_lines(
        text
    ):

        lower = line.casefold()


        # En az bir TL değeri olmalı.
        if not re.search(
            r"\b\d[\d.,]*\s*TL\b",
            line,
            flags=re.IGNORECASE
        ):

            continue


        # Araç satış/kasko değerleri
        # finansman tutarı değildir.
        if contains_any(
            line,
            [
                "kasko değeri",
                "satış değeri",
                "ekspertiz değeri",
                "örnek hesaplama",
                "örnek maliyet",
                "geri ödeme detayları"
            ]
        ):

            continue


        # Alt ürün kısıtlarını genel
        # finansman limiti olarak yazma.
        if contains_any(
            line,
            [
                "cep telefonu",
                "tablet",
                "bilgisayar"
            ]
        ):

            continue


        # 200.000 TL'ye kadar vb.
        has_up_to_amount = bool(
            re.search(
                r"\b\d[\d.,]*\s*TL"
                r"(?:[’']?(?:ye|ya))?"
                r"\s+kadar\b",
                line,
                flags=re.IGNORECASE
            )
        )


        if (
            has_up_to_amount
            and (
                "finansman"
                in lower

                or "limit"
                in lower

                or "alışveriş"
                in lower
            )
        ):

            results.append(
                line
            )

            continue


        # Açık limit ifadesi
        if (
            "limit"
            in lower
            and "TL" in line
        ):

            results.append(
                line
            )


    return unique(
        results
    )


# =========================================================
# VADE
# =========================================================

def extract_vade(text):

    results = []


    for line in get_lines(
        text
    ):

        lower = line.casefold()


        # Soru cümlelerini veri diye yazma.
        if "?" in line:
            continue


        if not re.search(
            r"\b\d+\s*"
            r"(?:aya|aylık|aydan|ay)\b",
            lower
        ):

            continue


        if contains_any(
            line,
            [
                "vade",
                "taksit",
                "ödemesiz",
                "ertelemeli",
                "geri ödeme"
            ]
        ):

            results.append(
                line
            )


    # Koşullu araç vade tablosu
    results.extend(
        extract_vehicle_table(
            text
        )
    )


    return unique(
        results
    )


# =========================================================
# TAKSİT
# =========================================================

def extract_taksit_sayisi(text):

    results = []


    for line in get_lines(
        text
    ):

        lower = line.casefold()


        if "?" in line:
            continue


        if "taksit" not in lower:
            continue


        if not re.search(
            r"\d",
            line
        ):

            continue


        if contains_any(
            line,
            [
                "tahsis ücreti",
                "taksit tutarı"
            ]
        ):

            continue


        results.append(
            line
        )


    return unique(
        results
    )


# =========================================================
# MASRAF
# =========================================================

def extract_masraf_bilgisi(text):

    results = []


    keywords = [
        "tahsis ücreti",
        "dosya masrafı",
        "ekspertiz ücreti",
        "ipotek tesis",
        "toplam masraf",
        "bsmv",
        "kkdf"
    ]


    for line in get_lines(
        text
    ):

        if "?" in line:
            continue


        if not contains_any(
            line,
            keywords
        ):

            continue


        if (
            re.search(
                r"\d",
                line
            )

            or contains_any(
                line,
                [
                    "tahsil",
                    "alın",
                    "yansıt",
                    "ücretsiz",
                    "muaf",
                    "dâhil",
                    "dahil"
                ]
            )
        ):

            results.append(
                line
            )


    return unique(
        results
    )


# =========================================================
# ÜRÜN AVANTAJLARI
# =========================================================

def extract_advantages(text):

    results = []


    for line in get_lines(
        text
    ):

        if "?" in line:
            continue


        if contains_any(
            line,
            [
                "ertelemeli",
                "ödemesiz dönem",
                "yansıtılmayacaktır",
                "ücretsiz",
                "vade farksız",
                "indirim"
            ]
        ):

            if (
                re.search(
                    r"\d",
                    line
                )

                or contains_any(
                    line,
                    [
                        "yansıtılmayacaktır",
                        "ücretsiz",
                        "indirim"
                    ]
                )
            ):

                results.append(
                    line
                )


    return unique(
        results
    )


# =========================================================
# HEDEF KİTLE
# =========================================================

def extract_hedef_kitle(text):

    results = []


    keywords = [
        "18 yaşından büyük",
        "18 yaşını tamamlamış",
        "18 yaşını dolduran",

        "türkiye'de yerleşik",
        "türkiye’de yerleşik",

        "yurt dışında yaşayan",
        "yurt dışında yerleşik",

        "ilk evini almak isteyen",

        "tüm öğrenciler",
        "öğrenciler faydalanabilir",

        "hak sahibi olduğunuz",
        "hak sahibiyseniz",

        "kirasını toplu ödemek isteyen"
    ]


    for line in get_lines(
        text
    ):

        lower = line.casefold()


        if "?" in line:
            continue


        # 18 yaş altı çocuk bilgisi
        # hedef kitle değildir.
        if (
            "18 yaş alt"
            in lower

            and not contains_any(
                line,
                [
                    "18 yaşından büyük",
                    "18 yaşını tamamlamış",
                    "18 yaşını dolduran"
                ]
            )
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
    )


# =========================================================
# KOŞULLAR
# =========================================================

def extract_kosullar(text):

    results = []


    keywords = [
        "maksimum",
        "en fazla",
        "en az",
        "aya kadar",
        "kadar vade",

        "taksit",

        "finansman kullanılabilir",
        "finansmandan yararlan",
        "finansman desteğinden",

        "kasko değeri",
        "satış değeri",
        "ekspertiz değeri",
        "enerji sınıfı",

        "bulunmamalıdır",
        "kullanılamaz",
        "kullandırım yapıl",

        "zorunlu",
        "geçerlilik süresi",

        "rehin",
        "ipotek",
        "peşinat",

        "sıfır ve ikinci el",
        "sıfır araç",
        "ikinci el araç",
        "sıfır konut",
        "ikinci el konut",

        "başvurabilir",
        "yararlanabilir",
        "yararlanılabilir",

        "hizmet vermemektedir",

        "hak sahibi",

        "yetkili olması gerekir"
    ]


    skip_words = [
        "hesaplama aracı",
        "bu tablo bilgi amaçlıdır",
        "tahsis ücreti",
        "dosya masrafı"
    ]


    for line in get_lines(
        text
    ):

        if "?" in line:
            continue


        if len(line) < 25:
            continue


        if contains_any(
            line,
            skip_words
        ):

            continue


        if contains_any(
            line,
            keywords
        ):

            results.append(
                line
            )


    # Koşullu tabloları da ekle.
    results.extend(
        extract_vehicle_table(
            text
        )
    )


    results.extend(
        extract_housing_table(
            text
        )
    )


    return unique(
        results
    )


# =========================================================
# STANDART KAYIT
# =========================================================

def create_standard_record(
    product
):

    title = normalize_spaces(
        product.get(
            "urun_adi",
            ""
        )
    )


    url = normalize_spaces(
        product.get(
            "kaynak_url",
            ""
        )
    )


    raw_text = str(
        product.get(
            "ham_metin",
            ""
        )
    ).strip()


    return {

        "banka": (
            "Kuveyt Türk Katılım Bankası"
        ),

        "kayit_turu": "finansman",

        "urun_adi": title,

        "urun_kategorisi": (
            detect_category(
                url,
                title
            )
        ),


        "kar_payi_orani": (
            extract_kar_payi_orani(
                raw_text
            )
        ),


        "finansman_orani": (
            extract_finansman_orani(
                raw_text
            )
        ),


        "finansman_tutari": (
            extract_finansman_tutari(
                raw_text
            )
        ),


        "vade": (
            extract_vade(
                raw_text
            )
        ),


        "taksit_sayisi": (
            extract_taksit_sayisi(
                raw_text
            )
        ),


        "masraf_bilgisi": (
            extract_masraf_bilgisi(
                raw_text
            )
        ),


        "kampanya_turu": "",


        "kampanya_avantaji": (
            extract_advantages(
                raw_text
            )
        ),


        "kampanya_suresi": "",


        "hedef_kitle": (
            extract_hedef_kitle(
                raw_text
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


# =========================================================
# VALIDATION
# =========================================================

def validate_record(
    record
):

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


    products = raw_data.get(
        "urunler",
        []
    )


    print()

    print(
        "=" * 75
    )

    print(
        "KUVEYT TÜRK FİNANSMAN EXTRACTOR V2"
    )

    print(
        "=" * 75
    )


    print(
        "Raw ürün:",
        len(products)
    )


    records = []


    for index, product in enumerate(
        products,
        start=1
    ):

        record = create_standard_record(
            product
        )


        validate_record(
            record
        )


        records.append(
            record
        )


        print()

        print(
            "-" * 75
        )


        print(
            f"[{index}/{len(products)}] "
            f"{record['urun_adi']}"
        )


        print(
            "Kategori:",
            record[
                "urun_kategorisi"
            ]
        )


        print(
            "Kâr:",
            record[
                "kar_payi_orani"
            ]
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


    # =====================================================
    # OUTPUT
    # =====================================================

    output = {

        "banka": (
            "Kuveyt Türk Katılım Bankası"
        ),

        "kayit_turu": "finansman",

        "toplam_kayit": len(
            records
        ),

        "urunler": records
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
    # ÖZEL KONTROLLER
    # =====================================================

    by_name = {
        item[
            "urun_adi"
        ]: item

        for item
        in records
    }


    print()

    print(
        "=" * 75
    )

    print(
        "KRİTİK KONTROLLER"
    )

    print(
        "=" * 75
    )


    checks = [
        "2B Finansmanı",
        "Gurbetten Sılaya Gayrimenkul Finansmanı",
        "Alışveriş Finansmanı",
        "Hac-Umre Finansmanı",
        "Eğitim Finansmanı",
        "Seyahat Finansmanı",
        "Yeşil Konut Finansmanı",
        "Sürdürülebilir Araç Finansmanı",
        "Çatı GES Finansmanı"
    ]


    for name in checks:

        item = by_name.get(
            name
        )


        if not item:
            continue


        print()

        print(
            name
        )


        print(
            "  Kâr:",
            item[
                "kar_payi_orani"
            ]
        )


        print(
            "  Oran:",
            item[
                "finansman_orani"
            ]
        )


        print(
            "  Vade:",
            item[
                "vade"
            ]
        )


        print(
            "  Hedef:",
            item[
                "hedef_kitle"
            ]
        )


        print(
            "  Para:",
            item[
                "para_birimi"
            ]
        )


    print()

    print(
        "=" * 75
    )

    print(
        "EXTRACTOR TAMAMLANDI"
    )

    print(
        "=" * 75
    )


    print(
        "İşlenen ürün:",
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
        "=" * 75
    )


if __name__ == "__main__":
    main()