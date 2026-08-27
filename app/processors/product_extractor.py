import json
import os
import re
import unicodedata


INPUT_FILE = "data/raw/emlak_katilim_finansman_urunleri.json"

OUTPUT_FILE = "data/processed/emlak_katilim_finansman_extracted.json"


# ---------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------

def unique(values):
    result = []

    for value in values:
        if value and value not in result:
            result.append(value)

    return result


def normalize_spaces(text):
    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def normalize_for_comparison(text):
    replacements = {
        "ç": "c",
        "Ç": "c",
        "ğ": "g",
        "Ğ": "g",
        "ı": "i",
        "İ": "i",
        "ö": "o",
        "Ö": "o",
        "ş": "s",
        "Ş": "s",
        "ü": "u",
        "Ü": "u"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    return text.lower()


# ---------------------------------------------------------
# ÜRÜN KATEGORİSİ
# ---------------------------------------------------------

def detect_category(product_name):
    name = normalize_for_comparison(
        product_name
    )

    if "kentsel donusum" in name:
        return "kentsel_donusum"

    if "gayrimenkul sertifikasi" in name:
        return "yatirim"

    if "elus" in name:
        return "yatirim"

    if "konut" in name:
        return "konut"

    if "isyeri" in name:
        return "isyeri"

    if "arsa" in name:
        return "arsa"

    if "tasit" in name:
        return "tasit"

    if "ihtiyac" in name:
        return "ihtiyac"

    if "toki" in name:
        return "toki"

    return "diger"


# ---------------------------------------------------------
# PARA BİRİMİ
# ---------------------------------------------------------

def extract_para_birimi(text):
    currencies = []

    normalized = normalize_spaces(
        text
    ).lower()

    if (
        "türk lirası" in normalized
        or re.search(r"\btl\b", normalized)
        or "₺" in text
    ):
        currencies.append(
            "TRY"
        )

    if (
        re.search(r"\busd\b", normalized)
        or "amerikan doları" in normalized
    ):
        currencies.append(
            "USD"
        )

    if (
        re.search(r"\beur\b", normalized)
        or "euro" in normalized
    ):
        currencies.append(
            "EUR"
        )

    return unique(
        currencies
    )


# ---------------------------------------------------------
# İHTİYAÇ FİNANSMANI ÖRNEK TABLOSU
# ---------------------------------------------------------

def extract_ihtiyac_table(text):
    normalized = normalize_spaces(
        text
    )

    pattern = (
        r"Finansman\s+Tutarı\s+"
        r"Vade\s+"
        r"Kar\s+Oranı\s+"
        r"Taksit\s+Tutarı\s+"
        r"Finansman\s+Tahsis\s+Ücreti\s+"
        r"([\d.,]+)\s*₺\s+"
        r"(\d+)\s*Ay\s+"
        r"([\d.,]+)%\s+"
        r"([\d.,]+)\s*₺\s+"
        r"([\d.,]+)\s*₺"
    )

    match = re.search(
        pattern,
        normalized,
        re.IGNORECASE
    )

    if not match:
        return None

    return {
        "finansman_tutari": match.group(1),
        "vade": match.group(2),
        "kar_payi": match.group(3),
        "taksit_tutari": match.group(4),
        "tahsis_ucreti": match.group(5)
    }


# ---------------------------------------------------------
# KÂR PAYI ORANI
# ---------------------------------------------------------

def extract_kar_payi_orani(text):
    values = []

    normalized = normalize_spaces(
        text
    )

    if re.search(
        r"sıfır\s+k[âa]r\s+oranı",
        normalized,
        re.IGNORECASE
    ):
        values.append(
            "%0"
        )

    patterns = [
        r"K[âa]r\s+Oranı\s*[:\-]?\s*%?\s*([\d.,]+)",
        r"K[âa]r\s+Payı\s+Oranı\s*[:\-]?\s*%?\s*([\d.,]+)",
        r"%\s*([\d.,]+)\s+k[âa]r\s+payı",
        r"([\d.,]+)\s*%\s+k[âa]r"
    ]

    for pattern in patterns:
        matches = re.findall(
            pattern,
            normalized,
            re.IGNORECASE
        )

        for match in matches:
            values.append(
                f"%{match}"
            )

    ihtiyac_table = extract_ihtiyac_table(
        text
    )

    if ihtiyac_table:
        values.append(
            f"%{ihtiyac_table['kar_payi']}"
        )

    return unique(
        values
    )


# ---------------------------------------------------------
# FİNANSMAN ORANI
# ---------------------------------------------------------

def extract_finansman_orani(text):
    values = []

    normalized = normalize_spaces(
        text
    )

    patterns = [
        r"ekspertiz(?:\*)?\s+değerinin\s*%(\d+(?:[.,]\d+)?)",
        r"ekspertiz\s+değerinin\s*%(\d+(?:[.,]\d+)?)",
        r"Finansman\s+Oranı\s*:\s*[^%]{0,150}%(\d+(?:[.,]\d+)?)"
    ]

    for pattern in patterns:
        matches = re.findall(
            pattern,
            normalized,
            re.IGNORECASE
        )

        for match in matches:
            values.append(
                f"%{match}"
            )

    return unique(
        values
    )


# ---------------------------------------------------------
# GENEL VADE ÇIKARIMI
# ---------------------------------------------------------

def extract_vade(text):
    values = []

    normalized = normalize_spaces(
        text
    )

    patterns = [
        r"Azami\s+Vade\s*:\s*(\d+)\s*ay",
        r"azami\s+vade\s+(\d+)\s*ay",
        r"finansman\s+vadesi\s+azami\s+(\d+)\s*ay",
        r"(\d+)\s*aya\s+kadar\s+vade",
        r"(\d+)\s*aya\s+varan\s+vadeler",
        r"(\d+)\s*ay\s+vadeye\s+kadar",
    ]

    for pattern in patterns:
        matches = re.findall(
            pattern,
            normalized,
            re.IGNORECASE
        )

        for match in matches:
            values.append(
                f"{match} ay"
            )

    ihtiyac_table = extract_ihtiyac_table(
        text
    )

    if ihtiyac_table:
        values.append(
            f"{ihtiyac_table['vade']} ay"
        )

    return unique(
        values
    )


# ---------------------------------------------------------
# FİNANSMAN TUTARI
# ---------------------------------------------------------

def extract_finansman_tutari(text):
    values = []

    ihtiyac_table = extract_ihtiyac_table(
        text
    )

    if ihtiyac_table:
        values.append(
            f"{ihtiyac_table['finansman_tutari']} TL"
        )

    return unique(
        values
    )


# ---------------------------------------------------------
# TAKSİT SAYISI
# ---------------------------------------------------------

def extract_taksit_sayisi(text):
    values = []

    patterns = [
        r"Taksit\s+sayısı\s+azami\s+(\d+)\s*ay",
        r"azami\s+(\d+)\s+taksit"
    ]

    for pattern in patterns:
        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE
        )

        for match in matches:
            values.append(
                f"{match} taksit"
            )

    return unique(
        values
    )


# ---------------------------------------------------------
# MASRAF BİLGİSİ
# ---------------------------------------------------------

def extract_masraf_bilgisi(text):
    values = []

    normalized = normalize_spaces(
        text
    )

    ihtiyac_table = extract_ihtiyac_table(
        text
    )

    if ihtiyac_table:
        values.append(
            "Finansman tahsis ücreti: "
            f"{ihtiyac_table['tahsis_ucreti']} TL"
        )

    if (
        "KKDF’den muaf" in text
        or "KKDF'den muaf" in text
    ):
        values.append(
            "KKDF muafiyeti"
        )

    if (
        "KKDF" in normalized
        and "BSMV" in normalized
        and "muaf" in normalized.lower()
    ):
        values.append(
            "KKDF ve BSMV muafiyeti"
        )

    if re.search(
        r"herhangi\s+bir\s+sistem\s+ücreti\s+ve\s+ceza\s+şartı\s+uygulanmayacaktır",
        normalized,
        re.IGNORECASE
    ):
        values.append(
            "Sistem ücreti ve ceza uygulanmıyor"
        )

    return unique(
        values
    )


# ---------------------------------------------------------
# AVANTAJ ÇIKARIMI
# ---------------------------------------------------------

def extract_kampanya_avantaji(text):
    values = []

    normalized = normalize_spaces(
        text
    )

    patterns = [
        r"(\d+(?:[.,]\d+)?)\s+puan\s+k[âa]r\s+payı\s+indirimi",
        r"(\d+(?:[.,]\d+)?)\s+puan\s+indirimli"
    ]

    for pattern in patterns:
        matches = re.findall(
            pattern,
            normalized,
            re.IGNORECASE
        )

        for match in matches:
            values.append(
                f"{match} puan kâr payı indirimi"
            )

    return unique(
        values
    )


# ---------------------------------------------------------
# AVANTAJ BAĞLAMI
# ---------------------------------------------------------

def contextualize_advantages(
    product_name,
    advantages
):
    contextualized = []

    for advantage in advantages:

        normalized = normalize_for_comparison(
            advantage
        )

        if (
            product_name == "Konut Finansmanı"
            and "2 puan" in normalized
        ):
            contextualized.append(
                "Çevreci Konut Finansmanı: "
                "2 puan kâr payı indirimi"
            )

        elif (
            product_name == "Taşıt Finansmanı"
            and "2 puan" in normalized
        ):
            contextualized.append(
                "Çevreci Araç Finansmanı: "
                "2 puan kâr payı indirimi"
            )

        else:
            contextualized.append(
                advantage
            )

    return unique(
        contextualized
    )


# ---------------------------------------------------------
# HEDEF KİTLE
# ---------------------------------------------------------

def extract_hedef_kitle(text):
    values = []

    normalized = normalize_spaces(
        text
    )

    if re.search(
        r"gerçek\s+ve\s+tüzel\s+müşter",
        normalized,
        re.IGNORECASE
    ):
        values.append(
            "Gerçek ve tüzel kişiler"
        )

    elif re.search(
        r"gerçek\s+kişi",
        normalized,
        re.IGNORECASE
    ):
        values.append(
            "Gerçek kişiler"
        )

    match = re.search(
        r"en\s+az\s+(\d+)\s+kişi.*?"
        r"en\s+fazla\s+(\d+)\s+kişi",
        normalized,
        re.IGNORECASE
    )

    if match:
        values.append(
            f"En az {match.group(1)}, "
            f"en fazla {match.group(2)} ortak"
        )

    if re.search(
        r"yurtdışında\s+yerleşik\s+Türkiye\s+Cumhuriyeti\s+vatandaş",
        normalized,
        re.IGNORECASE
    ):
        values.append(
            "Yurt dışında yerleşik Türkiye Cumhuriyeti vatandaşları"
        )

    if re.search(
        r"kat\s+malikleri",
        normalized,
        re.IGNORECASE
    ):
        values.append(
            "Kat malikleri"
        )

    if re.search(
        r"Tasarruf\s+Finansman\s+Şirketi\s+ile\s+konut\s+sözleşmesi",
        normalized,
        re.IGNORECASE
    ):
        values.append(
            "Emlak Katılım Tasarruf Finansman ile "
            "konut sözleşmesi bulunan müşteriler"
        )

    return unique(
        values
    )


# ---------------------------------------------------------
# KOŞULLAR
# ---------------------------------------------------------

def extract_kosullar(text):
    values = []

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    keywords = [
        "ipotek",
        "çapraz kefalet",
        "yalnızca",
        "zorunluluğu",
        "teminata alın",
        "blokaj",
        "ekspertiz değerinin",
        "bdkk",
        "bddk"
    ]

    for line in lines:

        normalized_line = normalize_for_comparison(
            line
        )

        for keyword in keywords:

            normalized_keyword = normalize_for_comparison(
                keyword
            )

            if normalized_keyword in normalized_line:

                if len(line) <= 500:
                    values.append(
                        line
                    )

                break

    return unique(
        values
    )[:10]


# ---------------------------------------------------------
# TAŞIT FİNANSMANI TABLOSU
# ---------------------------------------------------------

def extract_vehicle_table(text):
    financing_ratios = []
    terms = []

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    try:
        start = lines.index(
            "Aracın Nihai Fatura Tutarı /Kasko Değeri"
        )

    except ValueError:
        return (
            financing_ratios,
            terms
        )

    try:
        end = lines.index(
            "Gerekli Belgeler",
            start
        )

    except ValueError:
        end = len(
            lines
        )

    table_lines = lines[
        start:end
    ]

    for index, line in enumerate(
        table_lines
    ):

        if not re.fullmatch(
            r"%\d+(?:[.,]\d+)?",
            line
        ):
            continue

        if index == 0:
            continue

        if index + 1 >= len(
            table_lines
        ):
            continue

        amount_range = table_lines[
            index - 1
        ]

        term = table_lines[
            index + 1
        ]

        if not re.fullmatch(
            r"\d+",
            term
        ):
            continue

        financing_ratios.append(
            f"{amount_range} için {line}"
        )

        terms.append(
            f"{amount_range} için {term} ay"
        )

    return (
        unique(
            financing_ratios
        ),
        unique(
            terms
        )
    )


# ---------------------------------------------------------
# GAYRİMENKUL SERTİFİKASI VADELERİ
# ---------------------------------------------------------

def extract_gsf_terms(text):
    values = []

    normalized = normalize_spaces(
        text
    )

    patterns = [
        (
            r"125\.000\s*TL.?ye\s+kadar.*?"
            r"36\s+aya\s+kadar",

            "125.000 TL'ye kadar: 36 ay"
        ),

        (
            r"125\.001\s*TL.*?"
            r"250\.000\s*TL\s+arası.*?"
            r"24\s+aya\s+kadar",

            "125.001-250.000 TL arası: 24 ay"
        ),

        (
            r"250\.001\s*TL.*?"
            r"12\s+aya\s+kadar",

            "250.001 TL ve üzeri: 12 ay"
        )
    ]

    for pattern, value in patterns:

        if re.search(
            pattern,
            normalized,
            re.IGNORECASE
        ):
            values.append(
                value
            )

    return unique(
        values
    )


# ---------------------------------------------------------
# KENTSEL DÖNÜŞÜM TABLOSU
# ---------------------------------------------------------

def extract_kentsel_donusum_table(text):
    vade = []
    finansman_tutari = []
    avantaj = []

    normalized = normalize_spaces(
        text
    )

    rows = [
        "Güçlendirme Kredisi",
        "Konut Yapım Kredisi",
        "Konut Edinme Kredisi",
        "İşyeri Yapım Kredisi",
        "İşyeri Edinme Kredisi"
    ]

    for row in rows:

        pattern = (
            re.escape(
                row
            )
            + r"\*?\s+"
            + r"(\d+)\s+baz\s+puan\s+"
            + r"(\d+)\s+[Yy]ıl\s+"
            + r"%([\d.,]+)\s+"
            + r"([\d.]+)\s*TL"
        )

        match = re.search(
            pattern,
            normalized,
            re.IGNORECASE
        )

        if not match:
            continue

        years = int(
            match.group(2)
        )

        months = years * 12

        vade.append(
            f"{row}: {months} ay"
        )

        finansman_tutari.append(
            f"{row}: "
            f"{match.group(4)} TL üst limit"
        )

        avantaj.append(
            f"{row}: "
            f"aylık %{match.group(3)} "
            f"devlet kâr payı desteği"
        )

    return {
        "vade": unique(
            vade
        ),

        "finansman_tutari": unique(
            finansman_tutari
        ),

        "avantaj": unique(
            avantaj
        )
    }


# ---------------------------------------------------------
# KONUT FİNANSMANI ALT ÜRÜN VADELERİ
# ---------------------------------------------------------

def extract_konut_special_terms(text):
    values = []

    normalized = normalize_spaces(
        text
    )

    if re.search(
        r"TL\s+cinsinden\s+120\s+aya\s+kadar",
        normalized,
        re.IGNORECASE
    ):
        values.append(
            "Memlekette Konut Finansmanı - TL: 120 ay"
        )

    if re.search(
        r"USD\s+veya\s+EUR\s+cinsinden\s+ise\s+azami\s+60\s+ay",
        normalized,
        re.IGNORECASE
    ):
        values.append(
            "Memlekette Konut Finansmanı - USD/EUR: 60 ay"
        )

    return unique(
        values
    )


# ---------------------------------------------------------
# STANDART KAYIT OLUŞTUR
# ---------------------------------------------------------

def create_standard_record(raw_product):
    text = raw_product.get(
        "ham_metin",
        ""
    )

    product_name = raw_product.get(
        "urun_adi",
        ""
    )

    category = detect_category(
        product_name
    )

    kar_payi = extract_kar_payi_orani(
        text
    )

    finansman_orani = extract_finansman_orani(
        text
    )

    finansman_tutari = extract_finansman_tutari(
        text
    )

    vade = extract_vade(
        text
    )

    taksit = extract_taksit_sayisi(
        text
    )

    masraf = extract_masraf_bilgisi(
        text
    )

    avantaj = extract_kampanya_avantaji(
        text
    )


    # -----------------------------------------------------
    # TAŞIT FİNANSMANI
    # -----------------------------------------------------

    if product_name == "Taşıt Finansmanı":

        vehicle_ratios, vehicle_terms = (
            extract_vehicle_table(
                text
            )
        )

        finansman_orani = vehicle_ratios

        vade = vehicle_terms


    # -----------------------------------------------------
    # GAYRİMENKUL SERTİFİKASI
    # -----------------------------------------------------

    if (
        product_name
        == "Gayrimenkul Sertifikası Finansmanı"
    ):

        vade = extract_gsf_terms(
            text
        )


    # -----------------------------------------------------
    # KENTSEL DÖNÜŞÜM
    # -----------------------------------------------------

    if (
        product_name
        == "Kentsel Dönüşüm Finansmanı"
    ):

        kentsel = extract_kentsel_donusum_table(
            text
        )

        vade = kentsel[
            "vade"
        ]

        finansman_tutari = kentsel[
            "finansman_tutari"
        ]

        avantaj = unique(
            avantaj
            + kentsel["avantaj"]
        )


    # -----------------------------------------------------
    # KONUT FİNANSMANI
    # -----------------------------------------------------

    if product_name == "Konut Finansmanı":

        vade = extract_konut_special_terms(
            text
        )


    # -----------------------------------------------------
    # AVANTAJ BAĞLAMLARINI DÜZELT
    # -----------------------------------------------------

    avantaj = contextualize_advantages(
        product_name,
        avantaj
    )


    # -----------------------------------------------------
    # STANDART JSON
    # -----------------------------------------------------

    return {

        "banka": raw_product.get(
            "banka",
            ""
        ),

        "kayit_turu": "finansman",

        "urun_adi": product_name,

        "urun_kategorisi": category,

        "kar_payi_orani": unique(
            kar_payi
        ),

        "finansman_orani": unique(
            finansman_orani
        ),

        "finansman_tutari": unique(
            finansman_tutari
        ),

        "vade": unique(
            vade
        ),

        "taksit_sayisi": unique(
            taksit
        ),

        "masraf_bilgisi": unique(
            masraf
        ),

        "kampanya_turu": "",

        "kampanya_avantaji": unique(
            avantaj
        ),

        "kampanya_suresi": "",

        "hedef_kitle": extract_hedef_kitle(
            text
        ),

        "para_birimi": extract_para_birimi(
            text
        ),

        "kosullar": extract_kosullar(
            text
        ),

        "kaynak_url": raw_product.get(
            "kaynak_url",
            ""
        ),

        "ham_metin": text
    }


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        raw_data = json.load(
            file
        )

    records = []

    for raw_product in raw_data["urunler"]:

        record = create_standard_record(
            raw_product
        )

        records.append(
            record
        )

    output_data = {

        "banka": raw_data.get(
            "banka",
            "Türkiye Emlak Katılım Bankası"
        ),

        "kayit_sayisi": len(
            records
        ),

        "kayitlar": records
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
            output_data,
            file,
            ensure_ascii=False,
            indent=4
        )

    print(
        f"\nToplam işlenen kayıt: {len(records)}\n"
    )

    for record in records:

        print(
            "-----------------------------------------"
        )

        print(
            "Ürün:",
            record["urun_adi"]
        )

        print(
            "Kategori:",
            record["urun_kategorisi"]
        )

        print(
            "Kâr Payı:",
            record["kar_payi_orani"]
        )

        print(
            "Finansman Oranı:",
            record["finansman_orani"]
        )

        print(
            "Finansman Tutarı:",
            record["finansman_tutari"]
        )

        print(
            "Vade:",
            record["vade"]
        )

        print(
            "Masraf:",
            record["masraf_bilgisi"]
        )

        print(
            "Avantaj:",
            record["kampanya_avantaji"]
        )

    print(
        "\n-----------------------------------------"
    )

    print(
        f"JSON kaydedildi: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()