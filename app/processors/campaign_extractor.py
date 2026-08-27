import json
import os
import re
import unicodedata


INPUT_FILE = "data/raw/emlak_katilim_kampanyalar.json"

OUTPUT_FILE = (
    "data/processed/"
    "emlak_katilim_kampanya_extracted.json"
)


# =========================================================
# YARDIMCI FONKSİYONLAR
# =========================================================

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
        text or ""
    ).strip()


def normalize_for_comparison(text):
    text = text or ""

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
        "Ü": "u",
        "â": "a",
        "Â": "a"
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new
        )

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(
            character
        )
    )

    return text.lower()


def get_clean_lines(text):
    result = []

    for line in (text or "").splitlines():

        line = normalize_spaces(
            line
        )

        if not line:
            continue

        normalized = normalize_for_comparison(
            line
        )

        if (
            "your browser does not support"
            in normalized
        ):
            continue

        if (
            "tarayiciniz audio elementini desteklemiyor"
            in normalized
        ):
            continue

        result.append(
            line
        )

    return result


def is_negative_benefit_line(line):
    normalized = normalize_for_comparison(
        line
    )

    negative_phrases = [
        "dahil degildir",
        "dahil edilmez",
        "kullanilarak yapilan islemler",
        "kullanarak yapilan islemler",
        "kullanilarak yapilan alisverisler",
        "uygulanamaz",
        "yapilamaz"
    ]

    return any(
        phrase in normalized
        for phrase in negative_phrases
    )


# =========================================================
# PARA BİRİMİ
# =========================================================

def extract_para_birimi(text):
    values = []

    normalized = normalize_for_comparison(
        text
    )

    if (
        re.search(
            r"\btl\b",
            normalized
        )
        or "₺" in (text or "")
        or "turk lirasi" in normalized
    ):
        values.append(
            "TRY"
        )

    if re.search(
        r"\busd\b",
        normalized
    ):
        values.append(
            "USD"
        )

    if re.search(
        r"\beur\b",
        normalized
    ):
        values.append(
            "EUR"
        )

    return unique(
        values
    )


# =========================================================
# POZİTİF PARAFPARA KONTROLÜ
# =========================================================

def has_positive_parafpara(
    campaign_name,
    text
):
    if (
        "parafpara"
        in normalize_for_comparison(
            campaign_name
        )
    ):
        return True

    for line in get_clean_lines(
        text
    ):

        normalized = normalize_for_comparison(
            line
        )

        if "parafpara" not in normalized:
            continue

        if is_negative_benefit_line(
            line
        ):
            continue

        positive_words = [
            "verilecektir",
            "verilir",
            "kazanabilir",
            "kazanilabilir",
            "kazanilir",
            "kazanacaktir",
            "hediye",
            "yuklenecek",
            "yuklenir",
            "yansitilacak",
            "tanimlanir"
        ]

        if any(
            word in normalized
            for word in positive_words
        ):
            return True

    return False


# =========================================================
# POZİTİF İNDİRİM KONTROLÜ
# =========================================================

def has_positive_discount(
    campaign_name,
    text
):
    title_normalized = (
        normalize_for_comparison(
            campaign_name
        )
    )

    if "indirim" in title_normalized:
        return True

    for line in get_clean_lines(
        text
    ):

        normalized = normalize_for_comparison(
            line
        )

        if "indirim" not in normalized:
            continue

        if is_negative_benefit_line(
            line
        ):
            continue

        if re.search(
            r"%\s*\d+(?:[.,]\d+)?",
            line
        ):
            return True

        if re.search(
            r"[\d.]+(?:,\d+)?\s*TL.*indirim",
            line,
            re.IGNORECASE
        ):
            return True

        positive_phrases = [
            "indirim saglan",
            "indirim uygulan",
            "indirim sunul",
            "indirim firsati",
            "indirim kazan"
        ]

        if any(
            phrase in normalized
            for phrase in positive_phrases
        ):
            return True

    return False


# =========================================================
# NAKİT İADE KONTROLÜ
# =========================================================

def has_positive_cashback(
    campaign_name,
    text
):
    if (
        "nakit iade"
        in normalize_for_comparison(
            campaign_name
        )
    ):
        return True

    for line in get_clean_lines(
        text
    ):

        normalized = normalize_for_comparison(
            line
        )

        if (
            "nakit iade" in normalized
            and not is_negative_benefit_line(
                line
            )
        ):
            return True

    return False


# =========================================================
# TAKSİT KONTROLÜ
# =========================================================

def has_positive_installment(
    campaign_name,
    text
):
    if (
        "taksit"
        in normalize_for_comparison(
            campaign_name
        )
    ):
        return True

    for line in get_clean_lines(
        text
    )[:25]:

        normalized = normalize_for_comparison(
            line
        )

        if "taksit" not in normalized:
            continue

        if is_negative_benefit_line(
            line
        ):
            continue

        positive_phrases = [
            "taksit imkani",
            "taksit firsati",
            "vade farksiz",
            "pesin fiyatina",
            "taksit kampanyasindan yararlan"
        ]

        if any(
            phrase in normalized
            for phrase in positive_phrases
        ):
            return True

    return False


# =========================================================
# KAMPANYA TÜRÜ
# =========================================================

def detect_campaign_type(
    campaign_name,
    text
):
    types = []

    name_normalized = (
        normalize_for_comparison(
            campaign_name
        )
    )

    if has_positive_parafpara(
        campaign_name,
        text
    ):
        types.append(
            "parafpara"
        )

    if has_positive_cashback(
        campaign_name,
        text
    ):
        types.append(
            "nakit_iade"
        )

    if has_positive_discount(
        campaign_name,
        text
    ):
        types.append(
            "indirim"
        )

    if has_positive_installment(
        campaign_name,
        text
    ):
        types.append(
            "taksit"
        )

    if "ayricalik" in name_normalized:
        types.append(
            "ayricalik"
        )

    if not types:
        types.append(
            "diger"
        )

    return "+".join(
        unique(types)
    )


# =========================================================
# TARİH AY DESENİ
# =========================================================

MONTH_PATTERN = (
    r"(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|"
    r"Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)"
)


def clean_date_text(value):
    value = normalize_spaces(
        value
    )

    return value.strip(
        " ,.;"
    )


# =========================================================
# KAMPANYA SÜRESİ
# =========================================================

def extract_campaign_period(text):

    flat_text = normalize_spaces(
        text
    )

    if not flat_text:
        return ""


    # -----------------------------------------------------
    # GERÇEK TARİH ARALIĞI DESENLERİ
    #
    # ÖNEMLİ:
    #
    # (?<![\d.:])
    #
    # kullanıyoruz.
    #
    # Böylece:
    #
    # saat 09.00 – 7 Temmuz
    #
    # içindeki:
    #
    # 00 – 7 Temmuz
    #
    # yanlışlıkla tarih olarak algılanmıyor.
    # -----------------------------------------------------

    range_patterns = [

        # -------------------------------------------------
        # 10 Haziran 2026 saat 00.01
        # –
        # 31 Ağustos 2026 saat 23.59
        # -------------------------------------------------

        (
            rf"(?<![\d.:])"
            rf"\d{{1,2}}\s+"
            rf"{MONTH_PATTERN}\s+"
            rf"\d{{4}}"
            rf"(?:\s+saat\s+\d{{1,2}}[.:]\d{{2}})?"
            rf"\s*[–-]\s*"
            rf"\d{{1,2}}\s+"
            rf"{MONTH_PATTERN}\s+"
            rf"\d{{4}}"
            rf"(?:\s+(?:saat\s+)?"
            rf"\d{{1,2}}[.:]\d{{2}})?"
            rf"(?![\d.:])"
        ),


        # -------------------------------------------------
        # 18 Ağustos - 18 Eylül 2026
        # -------------------------------------------------

        (
            rf"(?<![\d.:])"
            rf"\d{{1,2}}\s+"
            rf"{MONTH_PATTERN}"
            rf"\s*[–-]\s*"
            rf"\d{{1,2}}\s+"
            rf"{MONTH_PATTERN}\s+"
            rf"\d{{4}}"
            rf"(?![\d.:])"
        ),


        # -------------------------------------------------
        # 01 Ağustos – 31 Ağustos 2026
        # -------------------------------------------------

        (
            rf"(?<![\d.:])"
            rf"\d{{1,2}}\s+"
            rf"{MONTH_PATTERN}"
            rf"\s*[–-]\s*"
            rf"\d{{1,2}}\s+"
            rf"{MONTH_PATTERN}\s+"
            rf"\d{{4}}"
            rf"(?![\d.:])"
        ),


        # -------------------------------------------------
        # 01-31 Ağustos 2026
        # 1-31 Ağustos 2026
        # -------------------------------------------------

        (
            rf"(?<![\d.:])"
            rf"\d{{1,2}}\s*"
            rf"[-–]\s*"
            rf"\d{{1,2}}\s+"
            rf"{MONTH_PATTERN}\s+"
            rf"\d{{4}}"
            rf"(?![\d.:])"
        ),


        # -------------------------------------------------
        # 01.08.2026 - 31.08.2026
        # -------------------------------------------------

        (
            r"(?<![\d.:])"
            r"\d{1,2}[./]\d{1,2}[./]\d{4}"
            r"\s*[–-]\s*"
            r"\d{1,2}[./]\d{1,2}[./]\d{4}"
            r"(?![\d.:])"
        )
    ]


    # -----------------------------------------------------
    # TARİH ARALIKLARINI TOPLA
    # -----------------------------------------------------

    candidates = []

    for pattern in range_patterns:

        for match in re.finditer(
            pattern,
            flat_text,
            re.IGNORECASE
        ):

            value = clean_date_text(
                match.group(0)
            )

            candidates.append(
                {
                    "value": value,
                    "start": match.start(),
                    "end": match.end()
                }
            )


    # -----------------------------------------------------
    # AYNI TARİHİ BİRDEN FAZLA REGEX
    # BULDUYSA TEKİL HALE GETİR
    # -----------------------------------------------------

    candidates.sort(
        key=lambda item: (
            item["start"],
            -len(item["value"])
        )
    )

    cleaned_candidates = []

    for candidate in candidates:

        candidate_normalized = (
            normalize_for_comparison(
                candidate["value"]
            )
        )

        duplicate = False

        for existing in cleaned_candidates:

            existing_normalized = (
                normalize_for_comparison(
                    existing["value"]
                )
            )

            # Aynı değer.
            if (
                candidate_normalized
                == existing_normalized
            ):
                duplicate = True
                break

            # Aynı karakter aralığının içinde
            # daha kısa eşleşme varsa alma.
            if (
                candidate["start"]
                >= existing["start"]
                and candidate["end"]
                <= existing["end"]
            ):
                duplicate = True
                break

        if not duplicate:

            cleaned_candidates.append(
                candidate
            )


    # -----------------------------------------------------
    # TARİH ARALIĞI VARSA
    #
    # Gerçek kampanya dönemi genellikle sayfanın
    # ilk bölümünde bulunuyor.
    #
    # İlk bulunan gerçek tarih aralığını temel alıyoruz.
    #
    # Pazarama gibi arka arkaya birden fazla kampanya
    # dönemi varsa, ilk tarihin yakınındaki diğer
    # tarihleri de alıyoruz.
    # -----------------------------------------------------

    if cleaned_candidates:

        first_candidate = cleaned_candidates[
            0
        ]

        selected = [
            first_candidate
        ]


        # İlk gerçek tarihten sonraki 650 karakter
        # içerisinde başka tarih aralıkları varsa,
        # bunları aynı kampanya döneminin parçaları
        # kabul ediyoruz.
        #
        # Pazarama:
        #
        # Temmuz
        # Ağustos
        # Eylül
        #
        # dönemlerini bu şekilde birlikte tutuyoruz.

        cluster_limit = (
            first_candidate["start"]
            + 650
        )


        for candidate in cleaned_candidates[
            1:
        ]:

            if (
                candidate["start"]
                <= cluster_limit
            ):

                selected.append(
                    candidate
                )

            else:
                break


        return " | ".join(
            unique(
                [
                    item["value"]
                    for item in selected
                ]
            )
        )


    # -----------------------------------------------------
    # TARİH ARALIĞI YOKSA
    # TEK BİTİŞ TARİHİ ARA
    #
    # Örnek:
    #
    # 31 Ağustos 2026 tarihine kadar
    #
    # 31.12.2026 tarihine kadar
    #
    # 31 Aralık 2026 saat 23:59'a kadar kullanılabilir
    # -----------------------------------------------------

    single_date_patterns = [

        (
            r"(?<![\d.:])"
            r"\d{1,2}[./]\d{1,2}[./]\d{4}"
            r"(?:\s+saat\s+\d{1,2}[.:]\d{2})?"
            r"(?![\d.:])"
        ),

        (
            rf"(?<![\d.:])"
            rf"\d{{1,2}}\s+"
            rf"{MONTH_PATTERN}\s+"
            rf"\d{{4}}"
            rf"(?:\s+saat\s+\d{{1,2}}[.:]\d{{2}})?"
            rf"(?![\d.:])"
        )
    ]


    end_candidates = []


    for pattern in single_date_patterns:

        for match in re.finditer(
            pattern,
            flat_text,
            re.IGNORECASE
        ):

            # Tarihin hemen sonrasını kontrol ediyoruz.
            after = flat_text[
                match.end():
                min(
                    len(flat_text),
                    match.end() + 130
                )
            ]

            before = flat_text[
                max(
                    0,
                    match.start() - 180
                ):
                match.start()
            ]


            normalized_after = (
                normalize_for_comparison(
                    after
                )
            )

            normalized_before = (
                normalize_for_comparison(
                    before
                )
            )


            # -------------------------------------------------
            # BU TARİH GERÇEKTEN BİR SON TARİH Mİ?
            # -------------------------------------------------

            until_signal = (
                "tarihine kadar"
                in normalized_after
                or "tarihine dek"
                in normalized_after
                or "a kadar kullanilabilir"
                in normalized_after
                or "e kadar kullanilabilir"
                in normalized_after
                or "kadar kullanilabilir"
                in normalized_after
                or "kadar gecerlidir"
                in normalized_after
                or "kadar yapilacak"
                in normalized_after
            )

            if not until_signal:
                continue


            # -------------------------------------------------
            # PARAFPARA ÖDÜL SON KULLANIM TARİHİ GİBİ
            # KAMPANYA SÜRESİ OLMAYAN TARİHLERİ ELE
            # -------------------------------------------------

            negative_context = [
                "parafpara'larin son kullanim",
                "parafparalarin son kullanim",
                "parafpara son kullanim",
                "kazanilan parafpara",
                "kullanilmayan parafpara",
                "odul son kullanim",
                "odul yukleme",
                "geri alinacaktir"
            ]

            if any(
                phrase in normalized_before
                for phrase in negative_context
            ):
                continue


            value = clean_date_text(
                match.group(0)
            )


            # -------------------------------------------------
            # PUANLAMA
            # -------------------------------------------------

            score = 0


            # Sayfanın başındaysa kampanya tarihi
            # olma ihtimali yüksek.
            if match.start() < 1800:
                score += 5


            if (
                "kampanya"
                in normalized_before
            ):
                score += 5


            if (
                "gecerli"
                in normalized_after
            ):
                score += 5


            if (
                "indirim kod"
                in normalized_before
                and "kullanilabilir"
                in normalized_after
            ):
                score += 4


            end_candidates.append(
                {
                    "value": value,
                    "start": match.start(),
                    "score": score
                }
            )


    # -----------------------------------------------------
    # EN UYGUN BİTİŞ TARİHİNİ SEÇ
    # -----------------------------------------------------

    if end_candidates:

        end_candidates.sort(
            key=lambda item: (
                -item["score"],
                item["start"]
            )
        )

        best = end_candidates[
            0
        ]

        return (
            best["value"]
            + " tarihine kadar"
        )


    return ""


# =========================================================
# TAKSİT SAYILARI
# =========================================================

def extract_numbers_from_installment_line(
    line
):
    values = []


    # -----------------------------------------------------
    # 3-6 taksit
    # -----------------------------------------------------

    for match in re.finditer(
        r"(\d+)\s*[-–]\s*(\d+)\s*taksit",
        line,
        re.IGNORECASE
    ):

        values.append(
            f"{match.group(1)} taksit"
        )

        values.append(
            f"{match.group(2)} taksit"
        )


    # -----------------------------------------------------
    # 3 veya 5 taksit
    # -----------------------------------------------------

    for match in re.finditer(
        r"(\d+)\s+veya\s+(\d+)\s+taksit",
        line,
        re.IGNORECASE
    ):

        values.append(
            f"{match.group(1)} taksit"
        )

        values.append(
            f"{match.group(2)} taksit"
        )


    patterns = [
        r"(\d+)\s*aya\s+varan\s+taksit",
        r"(\d+)\s*aya\s+kadar\s+taksit",
        r"(\d+)\s*taksite",
        r"(\d+)\s*taksit"
    ]


    for pattern in patterns:

        matches = re.findall(
            pattern,
            line,
            re.IGNORECASE
        )

        for match in matches:

            values.append(
                f"{match} taksit"
            )


    return unique(
        values
    )


def extract_taksit_sayisi(
    campaign_name,
    text
):
    values = []


    # -----------------------------------------------------
    # BAŞLIK
    # -----------------------------------------------------

    values.extend(
        extract_numbers_from_installment_line(
            campaign_name
        )
    )


    # -----------------------------------------------------
    # KAMPANYA METNİNİN İLK KISMI
    # -----------------------------------------------------

    for line in get_clean_lines(
        text
    )[:25]:

        normalized = normalize_for_comparison(
            line
        )

        if "taksit" not in normalized:
            continue


        # Yasal mevzuat rakamlarını kampanya
        # taksiti olarak alma.
        if (
            "yasal mevzuat"
            in normalized
            or "azami taksit"
            in normalized
        ):
            continue


        positive_phrases = [
            "taksit imkani",
            "taksit firsati",
            "vade farksiz",
            "pesin fiyatina",
            "taksit kampanyasindan yararlan",
            "taksitin secilmesi",
            "taksitlerin secilmesi"
        ]


        if not any(
            phrase in normalized
            for phrase in positive_phrases
        ):
            continue


        values.extend(
            extract_numbers_from_installment_line(
                line
            )
        )


    return unique(
        values
    )


# =========================================================
# HEDEF KİTLE
# =========================================================

def extract_hedef_kitle(text):
    values = []

    lines = get_clean_lines(
        text
    )

    normalized_full = (
        normalize_for_comparison(
            text
        )
    )

    audience_lines = []


    for line in lines:

        normalized = (
            normalize_for_comparison(
                line
            )
        )

        if (
            (
                "kampanyadan" in normalized
                or "kampanya " in normalized
            )
            and (
                "yararlan" in normalized
                or "faydalan" in normalized
                or "gecerlidir" in normalized
            )
        ):
            audience_lines.append(
                line
            )


    audience_text = " ".join(
        audience_lines
    )

    normalized_audience = (
        normalize_for_comparison(
            audience_text
        )
    )


    # -----------------------------------------------------
    # PARAF PREMIUM
    # -----------------------------------------------------

    if (
        "paraf premium"
        in normalized_audience
    ):
        values.append(
            "Emlak Katılım Paraf Premium kart sahipleri"
        )


    # -----------------------------------------------------
    # PARAF
    # -----------------------------------------------------

    if re.search(
        r"emlak katilim paraf"
        r"(?! premium)",
        normalized_audience
    ):
        values.append(
            "Emlak Katılım Paraf kart sahipleri"
        )


    # -----------------------------------------------------
    # DEBIT
    # -----------------------------------------------------

    debit_excluded = bool(
        re.search(
            r"debit kart(?:lar)?"
            r".{0,80}"
            r"dahil degildir",
            normalized_full
        )
    )


    if (
        "debit"
        in normalized_audience
        and not debit_excluded
    ):
        values.append(
            "Emlak Katılım Debit kart sahipleri"
        )


    # -----------------------------------------------------
    # TROY
    # -----------------------------------------------------

    if (
        "troy logolu"
        in normalized_full
    ):
        values.append(
            "TROY logolu Emlak Katılım kart sahipleri"
        )


    # -----------------------------------------------------
    # SANAL VE EK KARTLAR
    # -----------------------------------------------------

    if re.search(
        r"sanal\s+ve\s+ek\s+kartlar\s+"
        r"kampanyaya\s+dahildir",
        normalized_full
    ):
        values.append(
            "Sanal ve ek kartlar"
        )


    if (
        "ek kart sahipleri kampanyadan yararlanabilir"
        in normalized_full
    ):
        values.append(
            "Ek kart sahipleri"
        )


    # -----------------------------------------------------
    # YENİ MÜŞTERİ
    # -----------------------------------------------------

    if (
        "ilk defa emlak katilim"
        in normalized_full
        and "muster" in normalized_full
    ):
        values.append(
            "İlk defa Emlak Katılım müşterisi olan bireysel müşteriler"
        )


    if (
        "ilk kez emlak katilim kredi karti"
        in normalized_full
    ):
        values.append(
            "İlk kez Emlak Katılım kredi kartı onaylanan bireysel müşteriler"
        )


    if (
        "sms ile bilgilendirme yapilan"
        in normalized_full
    ):
        values.append(
            "SMS ile bilgilendirilen bireysel müşteriler"
        )


    # -----------------------------------------------------
    # EMEKLİ
    # -----------------------------------------------------

    if (
        "emekli musterilerimiz"
        in normalized_full
        and (
            "faydalanabilecektir"
            in normalized_full
            or "yararlan"
            in normalized_full
        )
    ):
        values.append(
            "Emekli müşteriler"
        )


    return unique(
        values
    )


# =========================================================
# PARA DEĞERİNİ SAYIYA ÇEVİR
# =========================================================

def parse_money_value(value):
    value = value.strip()


    if (
        "." in value
        and "," in value
    ):

        value = value.replace(
            ".",
            ""
        )

        value = value.replace(
            ",",
            "."
        )


    elif "." in value:

        parts = value.split(
            "."
        )

        if all(
            len(part) == 3
            for part in parts[1:]
        ):
            value = "".join(
                parts
            )


    elif "," in value:

        value = value.replace(
            ",",
            "."
        )


    try:

        return float(
            value
        )

    except ValueError:

        return 0.0


def get_highest_money_string(values):
    if not values:
        return None

    pairs = []

    for value in values:

        pairs.append(
            (
                parse_money_value(
                    value
                ),
                value
            )
        )

    pairs.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return pairs[
        0
    ][1]


# =========================================================
# KAMPANYA AVANTAJLARI
# =========================================================

def extract_campaign_advantages(
    campaign_name,
    text
):
    values = []

    lines = get_clean_lines(
        text
    )

    flat_text = normalize_spaces(
        text
    )

    benefit_text = (
        campaign_name
        + " "
        + flat_text[:5000]
    )


    # -----------------------------------------------------
    # % İNDİRİM
    # -----------------------------------------------------

    discount_percentages = []

    patterns = [
        (
            r"%\s*(\d+(?:[.,]\d+)?)\s*"
            r"(?:oranında\s+)?"
            r"(?:ek\s+)?indirim"
        ),

        (
            r"indirim\s+oran[ıi].{0,80}?"
            r"%\s*(\d+(?:[.,]\d+)?)"
        )
    ]


    for pattern in patterns:

        matches = re.findall(
            pattern,
            benefit_text,
            re.IGNORECASE
        )

        discount_percentages.extend(
            matches
        )


    for percentage in unique(
        discount_percentages
    ):

        values.append(
            f"%{percentage} indirim"
        )


    # -----------------------------------------------------
    # TL'YE VARAN İNDİRİM
    # -----------------------------------------------------

    tl_discount_varan = re.findall(
        r"([\d.]+(?:,\d+)?)\s*TL"
        r"(?:['’]ye|ye)\s+varan\s+"
        r"(?:anında\s+)?indirim",
        benefit_text,
        re.IGNORECASE
    )


    if tl_discount_varan:

        highest = get_highest_money_string(
            tl_discount_varan
        )

        values.append(
            f"{highest} TL'ye varan indirim"
        )

    else:

        total_discount_limits = re.findall(
            r"toplam\s+indirim\s+tutar[ıi]"
            r".{0,40}?"
            r"([\d.]+(?:,\d+)?)\s*TL"
            r"\s+ile\s+s[ıi]n[ıi]rl[ıi]",
            benefit_text,
            re.IGNORECASE
        )


        if total_discount_limits:

            highest = get_highest_money_string(
                total_discount_limits
            )

            values.append(
                f"En fazla {highest} TL indirim"
            )

        else:

            generic_tl_discounts = re.findall(
                r"([\d.]+(?:,\d+)?)\s*TL"
                r"\s+(?:anında\s+)?indirim",
                benefit_text,
                re.IGNORECASE
            )


            if generic_tl_discounts:

                highest = get_highest_money_string(
                    generic_tl_discounts
                )

                values.append(
                    f"{highest} TL indirim"
                )


    # -----------------------------------------------------
    # NAKİT İADE %
    # -----------------------------------------------------

    cashback_percentages = re.findall(
        r"%\s*(\d+(?:[.,]\d+)?)"
        r"(?:['’]si)?\s+nakit\s+iade",
        benefit_text,
        re.IGNORECASE
    )


    for percentage in unique(
        cashback_percentages
    ):

        values.append(
            f"%{percentage} nakit iade"
        )


    # -----------------------------------------------------
    # NAKİT İADE TL
    # -----------------------------------------------------

    cashback_amounts = re.findall(
        r"([\d.]+(?:,\d+)?)\s*TL"
        r"(?:['’]ye|ye)\s+varan\s+"
        r"nakit\s+iade",
        benefit_text,
        re.IGNORECASE
    )


    if cashback_amounts:

        highest = get_highest_money_string(
            cashback_amounts
        )

        values.append(
            f"{highest} TL'ye varan nakit iade"
        )


    # -----------------------------------------------------
    # PARAFPARA
    # -----------------------------------------------------

    positive_parafpara_lines = []


    if (
        "parafpara"
        in normalize_for_comparison(
            campaign_name
        )
    ):

        positive_parafpara_lines.append(
            campaign_name
        )


    for line in lines:

        normalized = normalize_for_comparison(
            line
        )

        if "parafpara" not in normalized:
            continue

        if is_negative_benefit_line(
            line
        ):
            continue

        positive_words = [
            "verilecektir",
            "verilir",
            "kazanabilir",
            "kazanilabilir",
            "kazanilir",
            "kazanacaktir",
            "hediye",
            "en fazla",
            "yuklenecek",
            "yansitilacak"
        ]

        if any(
            word in normalized
            for word in positive_words
        ):

            positive_parafpara_lines.append(
                line
            )


    parafpara_text = " ".join(
        positive_parafpara_lines
    )


    parafpara_amounts = re.findall(
        r"([\d.]+(?:,\d+)?)\s*TL"
        r"(?:['’]ye|ye)?"
        r"(?:\s+varan)?\s+ParafPara",
        parafpara_text,
        re.IGNORECASE
    )


    if parafpara_amounts:

        highest = get_highest_money_string(
            parafpara_amounts
        )


        if re.search(
            rf"{re.escape(highest)}\s*TL"
            rf"(?:['’]ye|ye)\s+varan\s+ParafPara",
            parafpara_text,
            re.IGNORECASE
        ):

            values.append(
                f"{highest} TL'ye varan ParafPara"
            )


        elif re.search(
            rf"en\s+fazla\s+"
            rf"{re.escape(highest)}\s*TL\s+ParafPara",
            parafpara_text,
            re.IGNORECASE
        ):

            values.append(
                f"En fazla {highest} TL ParafPara"
            )


        else:

            values.append(
                f"{highest} TL ParafPara"
            )


    # -----------------------------------------------------
    # TAKSİT
    # -----------------------------------------------------

    installments = extract_taksit_sayisi(
        campaign_name,
        text
    )

    for installment in installments:

        values.append(
            installment
        )


    # -----------------------------------------------------
    # PUAN İNDİRİM
    # -----------------------------------------------------

    point_discounts = re.findall(
        r"(\d+(?:[.,]\d+)?)\s*puan\s+indirim",
        benefit_text,
        re.IGNORECASE
    )


    for point in unique(
        point_discounts
    ):

        values.append(
            f"{point} puan indirim"
        )


    # -----------------------------------------------------
    # KÂR PAYLAŞIM ORANI
    # -----------------------------------------------------

    profit_share = re.findall(
        r"(\d+\s*/\s*\d+)\s+"
        r"k[aâ]r\s+payla[şs][ıi]m\s+oran[ıi]",
        benefit_text,
        re.IGNORECASE
    )


    for ratio in unique(
        profit_share
    ):

        ratio = ratio.replace(
            " ",
            ""
        )

        values.append(
            f"{ratio} kâr paylaşım oranı"
        )


    # -----------------------------------------------------
    # ÜCRETSİZ PARA TRANSFERİ
    # -----------------------------------------------------

    normalized_benefit = (
        normalize_for_comparison(
            benefit_text
        )
    )


    if (
        "ucretsiz para transfer"
        in normalized_benefit
    ):

        values.append(
            "Ücretsiz para transferi"
        )


    return unique(
        values
    )


# =========================================================
# KAMPANYA KOŞULLARI
# =========================================================

def extract_kosullar(text):
    values = []

    lines = get_clean_lines(
        text
    )

    keywords = [
        "kampanyaya katıl",
        "kampanyadan",
        "geçerlidir",
        "yararlanabilir",
        "faydalanabilir",
        "tek seferde",
        "müşteri baz",
        "en fazla",
        "dahil değildir",
        "dahildir",
        "iptal",
        "iade",
        "birleştirilemez",
        "birleştirilmez",
        "sms",
        "kupon kod",
        "kampanya kod",
        "taksit",
        "parafpara",
        "ödül",
        "stoklarla sınırlı",
        "online işlemlerde",
        "belgenin",
        "ibraz"
    ]


    normalized_keywords = [
        normalize_for_comparison(
            keyword
        )
        for keyword in keywords
    ]


    for line in lines:

        normalized_line = (
            normalize_for_comparison(
                line
            )
        )


        if normalized_line in [
            "kampanya kosullari",
            "kampanyaya nasil katilirim?",
            "kampanyanin avantajlari:",
            "kampanyadan yararlanma sartlari:"
        ]:
            continue


        if (
            "kampanyayi diledigi zaman"
            in normalized_line
            or "kosullarinin tamaminda degisiklik"
            in normalized_line
            or "kampanyayi istedigi zaman degistirme"
            in normalized_line
        ):
            continue


        for keyword in normalized_keywords:

            if keyword in normalized_line:

                if len(line) <= 900:

                    values.append(
                        line
                    )

                break


    return unique(
        values
    )[:20]


# =========================================================
# STANDART KAYIT
# =========================================================

def create_standard_record(
    raw_campaign
):
    text = raw_campaign.get(
        "ham_metin",
        ""
    )

    campaign_name = raw_campaign.get(
        "kampanya_adi",
        ""
    )


    return {

        "banka": raw_campaign.get(
            "banka",
            ""
        ),

        "kayit_turu": "kampanya",

        "urun_adi": campaign_name,

        "urun_kategorisi": "kampanya",

        "kar_payi_orani": [],

        "finansman_orani": [],

        "finansman_tutari": [],

        "vade": [],

        "taksit_sayisi": (
            extract_taksit_sayisi(
                campaign_name,
                text
            )
        ),

        "masraf_bilgisi": [],

        "kampanya_turu": (
            detect_campaign_type(
                campaign_name,
                text
            )
        ),

        "kampanya_avantaji": (
            extract_campaign_advantages(
                campaign_name,
                text
            )
        ),

        "kampanya_suresi": (
            extract_campaign_period(
                text
            )
        ),

        "hedef_kitle": (
            extract_hedef_kitle(
                text
            )
        ),

        "para_birimi": (
            extract_para_birimi(
                text
            )
        ),

        "kosullar": (
            extract_kosullar(
                text
            )
        ),

        "kaynak_url": raw_campaign.get(
            "kaynak_url",
            ""
        ),

        "ham_metin": text
    }


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


    raw_campaigns = raw_data.get(
        "kampanyalar",
        []
    )


    records = []


    for raw_campaign in raw_campaigns:

        record = create_standard_record(
            raw_campaign
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


    print()

    print(
        f"Toplam işlenen kampanya: "
        f"{len(records)}"
    )

    print()


    for index, record in enumerate(
        records,
        start=1
    ):

        print(
            "-----------------------------------------"
        )

        print(
            f"[{index}/{len(records)}]"
        )

        print(
            "Kampanya:",
            record["urun_adi"]
        )

        print(
            "Tür:",
            record["kampanya_turu"]
        )

        print(
            "Avantaj:",
            record["kampanya_avantaji"]
        )

        print(
            "Süre:",
            record["kampanya_suresi"]
        )

        print(
            "Taksit:",
            record["taksit_sayisi"]
        )

        print(
            "Hedef Kitle:",
            record["hedef_kitle"]
        )

        print(
            "Para Birimi:",
            record["para_birimi"]
        )


    print()

    print(
        "========================================="
    )

    print(
        f"Toplam kayıt: "
        f"{len(records)}"
    )

    print(
        f"JSON kaydedildi: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()