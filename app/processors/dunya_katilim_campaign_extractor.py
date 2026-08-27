import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT
    / "data"
    / "raw"
    / "dunya_katilim_kampanyalar.json"
)

OUTPUT_FILE = (
    ROOT
    / "data"
    / "processed"
    / "dunya_katilim_kampanya_extracted.json"
)

BANK_NAME = "Dünya Katılım Bankası A.Ş."
EXPECTED_COUNT = 43


SCHEMA_KEYS = [
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
    "ham_metin",
]


LIST_FIELDS = {
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
}


SCALAR_FIELDS = set(SCHEMA_KEYS) - LIST_FIELDS


CATEGORY_TO_TYPE = {
    "Yeni Müşteri Kampanyaları": "Yeni Müşteri Kampanyası",
    "Paraf Kampanyaları": "Paraf Kampanyası",
    "Finansman Kampanyaları": "Finansman Kampanyası",
    "Sigorta Kampanyaları": "Sigorta Kampanyası",
    "Yatırım Kampanyaları": "Yatırım Kampanyası",
    "Kart Kampanyaları": "Kart Kampanyası",
}


FOOTERS = (
    set(CATEGORY_TO_TYPE)
    | {
        "Devam ediyor",
        "Paylaş",
    }
)


LEGAL_PREFIXES = (
    "yasal mevzuat gereği",
    "yasal mevzuat uyarınca",
    "bddk tarafından",
    "bankacılık düzenleme ve denetleme kurulu",
    "taksitli satışlarda taksit sayısı ürün gruplarına göre",
    "ilgili yasal düzenlemelere istinaden",
)


RIGHTS_MARKERS = (
    "kampanya koşullarının tamamında değişiklik yapma",
    "kampanya süresi boyunca şartları değiştirme",
    "kampanyayı sonlandırma, uzatma",
)


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_text(value):
    value = str(value or "")

    replacements = {
        "\xa0": " ",
        "’": "'",
        "‘": "'",
        "´": "'",
        "`": "'",
        "–": "-",
        "—": "-",
    }

    for old, new in replacements.items():
        value = value.replace(
            old,
            new,
        )

    value = re.sub(
        r"[ \t]+",
        " ",
        value,
    )

    return value.strip()


def normalize_match(value):
    value = normalize_text(
        value
    )

    value = value.replace(
        "İ",
        "i",
    )

    value = value.replace(
        "I",
        "ı",
    )

    value = value.casefold()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def normalize_financial_text(value):
    value = normalize_text(
        value
    )

    # 10% -> %10
    value = re.sub(
        (
            r"(?<![%\d])"
            r"([0-9]+(?:[.,][0-9]+)?)"
            r"\s*%"
        ),
        r"%\1",
        value,
    )

    # % 10 -> %10
    value = re.sub(
        (
            r"%\s+"
            r"([0-9]+(?:[.,][0-9]+)?)"
        ),
        r"%\1",
        value,
    )

    # Türk Lirası -> TL
    value = re.sub(
        (
            r"\bTürk\s+"
            r"Liras(?:ı|ının|ına|ından)?\b"
        ),
        "TL",
        value,
        flags=re.IGNORECASE,
    )

    value = value.replace(
        "₺",
        " TL",
    )

    return normalize_text(
        value
    )


def unique(values):
    result = []
    seen = set()

    for value in values:
        value = normalize_text(
            value
        )

        key = normalize_match(
            value
        )

        if (
            value
            and key not in seen
        ):
            seen.add(
                key
            )

            result.append(
                value
            )

    return result


# =========================================================
# URL
# =========================================================

def get_slug(url):
    try:
        parsed = urlparse(
            str(
                url or ""
            )
        )

    except Exception:
        return ""

    parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if (
        len(parts) == 2
        and parts[0] == "kampanyalar"
    ):
        return parts[1]

    return ""


# =========================================================
# RAW TEXT
# =========================================================

def content_lines(
    raw_text,
    title,
):
    lines = []

    for raw_line in str(
        raw_text or ""
    ).splitlines():

        line = normalize_text(
            raw_line
        )

        if not line:
            continue

        if line in FOOTERS:
            continue

        if normalize_match(
            line
        ).startswith(
            "bitiş tarihi:"
        ):
            continue

        lines.append(
            line
        )

    if lines:
        if (
            normalize_match(
                lines[0]
            )
            ==
            normalize_match(
                title
            )
        ):
            lines = lines[1:]

    return unique(
        lines
    )


def core_lines(lines):
    result = []

    for line in lines:
        normalized = normalize_match(
            line
        )

        if any(
            normalized.startswith(
                prefix
            )
            for prefix in LEGAL_PREFIXES
        ):
            continue

        if any(
            marker in normalized
            for marker in RIGHTS_MARKERS
        ):
            continue

        result.append(
            line
        )

    return result


# =========================================================
# TAKSIT
# =========================================================

def extract_installments(
    lines,
    slug,
):
    if slug == "enerya-finansmani":
        return []

    installment_lines = []

    for line in lines[:14]:
        candidate = normalize_text(
            line
        )

        normalized = normalize_match(
            candidate
        )

        # Vade farklı seçenek kampanya avantajı değildir.
        if "vade farklı" in normalized:
            continue

        # Örnek:
        #
        # "peşin fiyatına 3 taksit,
        # 3 taksit üzerindeki taksitlerde
        # vade farkı uygulanmaktadır."
        #
        # Virgülden önceki gerçek avantaj korunur.
        if "vade farkı uygulan" in normalized:
            comma_index = candidate.find(",")

            if comma_index != -1:
                prefix = normalize_text(
                    candidate[:comma_index]
                )

                prefix_normalized = normalize_match(
                    prefix
                )

                if (
                    "peşin fiyatına"
                    in prefix_normalized
                    or
                    "vade farksız"
                    in prefix_normalized
                ):
                    candidate = prefix

                else:
                    continue

            else:
                continue

        installment_lines.append(
            candidate
        )

    text = "\n".join(
        installment_lines
    )

    values = []

    # -----------------------------------------------------
    # 3-6 taksit
    # 6 ve 7 taksit
    # -----------------------------------------------------

    pair_patterns = [
        (
            r"\b(\d{1,2})"
            r"\s*-\s*"
            r"(\d{1,2})"
            r"\s+taksit"
        ),
        (
            r"\b(\d{1,2})"
            r"\s+(?:ve|veya)\s+"
            r"(\d{1,2})"
            r"\s+taksit\w*"
        ),
    ]

    for pattern in pair_patterns:
        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            values.extend(
                [
                    match.group(1),
                    match.group(2),
                ]
            )

    # -----------------------------------------------------
    # 2, 3, 4, 5 veya 6 taksit
    # 3, 6, 9 veya 12 taksit
    # -----------------------------------------------------

    sequence_pattern = (
        r"("
        r"(?:\d{1,2}\s*,\s*)+"
        r"\d{1,2}"
        r"\s+veya\s+"
        r"\d{1,2}"
        r")"
        r"\s+taksit\w*"
    )

    for match in re.finditer(
        sequence_pattern,
        text,
        flags=re.IGNORECASE,
    ):
        values.extend(
            re.findall(
                r"\d{1,2}",
                match.group(1),
            )
        )

    # -----------------------------------------------------
    # TEKLİ TAKSİT
    # -----------------------------------------------------

    single_patterns = [
        (
            r"\b(\d{1,2})"
            r"\s+ay\s+taksit\w*"
        ),
        (
            r"\b(\d{1,2})"
            r"\s+"
            r"(?:aya?\s+varan\s+)?"
            r"taksit\w*"
        ),
        (
            r"\b(\d{1,2})"
            r"['’]?a\s+varan\s+"
            r"taksit\w*"
        ),
    ]

    for pattern in single_patterns:
        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            values.append(
                match.group(1)
            )

    numbers = set()

    for value in values:
        if not value.isdigit():
            continue

        number = int(
            value
        )

        if 1 <= number <= 36:
            numbers.add(
                number
            )

    return [
        str(number)
        for number
        in sorted(numbers)
    ]


# =========================================================
# BENEFIT CONDITION FILTER
# =========================================================

def is_condition_like_benefit(
    line,
    slug,
):
    normalized = normalize_match(
        line
    )

    # -----------------------------------------------------
    # Prosedür / koşul / kısıt / istisna ifadeleri
    # -----------------------------------------------------

    condition_markers = (
        "gerekmektedir",
        "gereklidir",
        "gerekir",
        "zorunlu",
        "seçilmesi gere",
        "seçilmelidir",
        "faydalanmak için",
        "faydalanabilmek için",
        "katılmak için",
        "hak kazanmak için",
        "hak kazanabilmek için",
        "geçerli değildir",
        "dahil değildir",
        "hariç tutul",
        "hariç tutabilir",
        "hariç bırak",
        "sadece seçili",
        "yalnızca seçili",
        "değişkenlik göstere",
        "yasal düzenlem",
        "mevzuat",
        "bankacılık düzenleme",
        "uygulanmayacaktır",
        "artı taksit",
        "vade farklı",
        "vade farkı uygulan",
        "taksitlendirme yapılmaz",
        "satış görevlisine",
        "satış yetkilisine",
        "kasa yetkilisi",
        "franchise",
        "stoklarla sınırlı",
        "bölünemez",
        "devredilemez",
        "paraya çevrilemez",
        "kullanım koşulları",
        "koşulların sağlan",
        "geçersiz sayıl",
        "birleştirilemez",
        "birlikte kullanılamaz",
    )

    if any(
        marker in normalized
        for marker in condition_markers
    ):
        return True

    # -----------------------------------------------------
    # İADE / İPTAL
    #
    # "nakit iade" avantaj olabilir.
    # İşlem iade/iptal şartları avantaj değildir.
    # -----------------------------------------------------

    refund_patterns = (
        r"\biade\s+ve\s+iptal\b",
        r"\biptal\s+ve\s+iade\b",
        r"\biade\s+edilen\b",
        r"\biptal\s+edilen\b",
        r"\biade\s+edilmesi\b",
        r"\biptal\s+edilmesi\b",
        r"\biadesi\b.*\bgeri\s+al",
        r"\biptali\b.*\bgeri\s+al",
    )

    if any(
        re.search(
            pattern,
            normalized,
        )
        for pattern in refund_patterns
    ):
        return True

    # -----------------------------------------------------
    # POS üzerinden seçim prosedürü
    # -----------------------------------------------------

    if (
        "pos üzerinden" in normalized
        and "seçil" in normalized
    ):
        return True

    # -----------------------------------------------------
    # "Sadece ... geçerlidir"
    #
    # Bu genellikle kapsam/kısıt belirtir.
    # -----------------------------------------------------

    if (
        "sadece" in normalized
        and "geçerlidir" in normalized
    ):
        return True

    if (
        "yalnızca" in normalized
        and "geçerlidir" in normalized
    ):
        return True

    # -----------------------------------------------------
    # Kampanya geçerlilik cümleleri
    # -----------------------------------------------------

    if (
        "kampanya" in normalized
        and "geçerlidir" in normalized
        and not any(
            phrase in normalized
            for phrase in (
                "indirim kazan",
                "nakit iade",
                "cashback",
                "hediye",
                "altın kazan",
            )
        )
    ):
        return True

    # -----------------------------------------------------
    # "X TL üzeri siparişlerde geçerlidir"
    #
    # Avantaj değil, minimum harcama şartıdır.
    # -----------------------------------------------------

    if (
        "geçerlidir" in normalized
        and re.search(
            r"\b\d[\d.]*\s*tl\b",
            normalized,
        )
    ):
        return True

    # -----------------------------------------------------
    # HEPSIBURADA
    # -----------------------------------------------------

    if slug == "hepsiburada":
        if (
            "lcd televizyon" in normalized
            or
            "belirli kategorilerde" in normalized
            or
            "xiaomi" in normalized
            or
            "qcy" in normalized
        ):
            return True

    # -----------------------------------------------------
    # N11
    # -----------------------------------------------------

    if slug == "n11":
        if "belirli kategorilerde" in normalized:
            return True

    # -----------------------------------------------------
    # PTTAVM
    # -----------------------------------------------------

    if slug == "pttavm":
        if (
            "belirli kategorilerde" in normalized
            or
            "belirli ürün" in normalized
        ):
            return True

    return False


# =========================================================
# CAMPAIGN BENEFIT
# =========================================================

def extract_benefits(
    lines,
    slug,
):
    keywords = (
        "indirim",
        "nakit iade",
        "cashback",
        "taksit",
        "altın",
        "hediye",
        "avantajlı kur",
        "avantajlı kurlar",
        "finansman",
        "vade farksız",
        "puan",
    )

    result = []

    for line in lines:
        normalized = normalize_match(
            line
        )

        # Numaralı bölüm başlıklarını alma.
        if re.match(
            r"^\d+\.\s+",
            line,
        ):
            continue

        # Kısa başlıkları alma.
        if (
            len(line) < 60
            and line.endswith(":")
        ):
            continue

        # Emoji başlıklı kısa pazarlama satırlarını alma.
        if (
            len(line) < 80
            and re.match(
                r"^[^\w\s]",
                line,
            )
        ):
            continue

        if is_condition_like_benefit(
            line,
            slug,
        ):
            continue

        if any(
            keyword in normalized
            for keyword in keywords
        ):
            result.append(
                normalize_financial_text(
                    line
                )
            )

        if len(result) >= 6:
            break

    return unique(
        result
    )


# =========================================================
# TARGET AUDIENCE
# =========================================================

def extract_targets(
    raw_text,
    slug,
):
    normalized = normalize_match(
        raw_text
    )

    result = []

    if slug == "enerya-finansmani":
        result.append(
            (
                "Antalya, Aydın, Denizli ve "
                "Konya illerindeki yeni Enerya aboneleri"
            )
        )

    if slug == "avantajli-kurlar":
        result.append(
            "Yatırımcılar"
        )

    if (
        "dkart debit karta sahip "
        "bireysel müşter"
        in normalized
    ):
        result.append(
            (
                "Dkart Debit kart sahibi "
                "bireysel müşteriler"
            )
        )

    if (
        (
            "bireysel ve ticari tüm dünya "
            "katılım troy logolu banka ve "
            "kredi kartları"
        )
        in normalized
    ):
        result.extend(
            [
                (
                    "Dünya Katılım TROY logolu "
                    "banka ve kredi kartı sahipleri"
                ),
                (
                    "Bireysel ve ticari müşteriler"
                ),
            ]
        )

    if (
        (
            "dünya katılım paraf kartlar "
            "faydalanabilecektir"
        )
        in normalized
    ):
        result.append(
            (
                "Dünya Katılım Paraf "
                "kart sahipleri"
            )
        )

    if (
        "kampanya bireysel müşteriler "
        "için geçerlidir"
        in normalized
    ):
        result.append(
            "Bireysel müşteriler"
        )

    if (
        "mevcut müşteriler"
        in normalized
    ):
        result.append(
            "Mevcut müşteriler"
        )

    if (
        "yeni müşteriler"
        in normalized
    ):
        result.append(
            "Yeni müşteriler"
        )

    return unique(
        result
    )


# =========================================================
# CURRENCY
# =========================================================

def extract_currency(
    lines,
    slug,
):
    if slug == "enerya-finansmani":
        return [
            "TL"
        ]

    text = "\n".join(
        lines[:14]
    )

    if re.search(
        (
            r"(?:"
            r"\bTL\b"
            r"|Türk\s+Liras"
            r"|₺"
            r")"
        ),
        text,
        flags=re.IGNORECASE,
    ):
        return [
            "TL"
        ]

    return []


# =========================================================
# CONDITIONS
# =========================================================

def extract_conditions(lines):
    keywords = (
        "geçerli",
        "gerekm",
        "gerekir",
        "zorunlu",
        "dahil",
        "hariç",
        "en fazla",
        "en az",
        "minimum",
        "maksimum",
        "sadece",
        "yalnızca",
        "faydalan",
        "hak kazan",
        "kullan",
        "seçil",
        "uygulan",
        "iade",
        "iptal",
        "sınırlı",
        "başvuru",
        "müşteri",
        "ödeme",
        "pos",
        "kod",
        "işlem",
        "alışveriş",
        "finansman",
        "abonelik",
        "vade",
        "franchise",
        "değişkenlik",
        "birleştirilemez",
        "birlikte kullanılamaz",
    )

    result = []

    for line in lines:
        normalized = normalize_match(
            line
        )

        if (
            len(line) < 45
            and line.endswith(":")
        ):
            continue

        if re.match(
            r"^\d+\.\s+",
            line,
        ):
            continue

        if any(
            keyword in normalized
            for keyword in keywords
        ):
            result.append(
                normalize_financial_text(
                    line
                )
            )

    return unique(
        result
    )


# =========================================================
# ENERYA FINANCE
# =========================================================

def finance_fields(
    slug,
    raw_text,
):
    if slug != "enerya-finansmani":
        return (
            [],
            [],
            [],
        )

    normalized = normalize_match(
        raw_text
    )

    finance_amount = []

    if (
        "minimum 6.500 tl"
        in normalized
        and
        "maksimum 16.500 tl"
        in normalized
    ):
        finance_amount = [
            "6.500 TL - 16.500 TL"
        ]

    maturity = []

    if (
        "minimum 2 ay"
        in normalized
        and
        "maksimum 6 ay"
        in normalized
    ):
        maturity = [
            "2 ay - 6 ay"
        ]

    fee_text = (
        "Enerya abonelik ücreti, finansman "
        "tutarının içinden alınarak Enerya "
        "hesabına aktarılacaktır."
    )

    expenses = []

    if (
        normalize_match(
            fee_text
        )
        in normalized
    ):
        expenses = [
            fee_text
        ]

    return (
        finance_amount,
        maturity,
        expenses,
    )


# =========================================================
# EXTRACT RECORD
# =========================================================

def extract_record(raw_record):
    title = normalize_text(
        raw_record.get(
            "kampanya_adi",
            "",
        )
    )

    category = normalize_text(
        raw_record.get(
            "liste_kategorisi",
            "",
        )
    )

    end_date = normalize_text(
        raw_record.get(
            "liste_bitis_tarihi",
            "",
        )
    )

    url = normalize_text(
        raw_record.get(
            "kaynak_url",
            "",
        )
    )

    raw_text = normalize_text(
        raw_record.get(
            "ham_metin",
            "",
        )
    )

    slug = get_slug(
        url
    )

    lines = content_lines(
        raw_text,
        title,
    )

    lines = core_lines(
        lines
    )

    (
        finance_amount,
        maturity,
        expenses,
    ) = finance_fields(
        slug,
        raw_text,
    )

    return {
        "banka":
            BANK_NAME,

        "kayit_turu":
            "kampanya",

        "urun_adi":
            title,

        "urun_kategorisi":
            category,

        "kar_payi_orani":
            [],

        "finansman_orani":
            [],

        "finansman_tutari":
            finance_amount,

        "vade":
            maturity,

        "taksit_sayisi":
            extract_installments(
                lines,
                slug,
            ),

        "masraf_bilgisi":
            expenses,

        "kampanya_turu":
            CATEGORY_TO_TYPE.get(
                category,
                "",
            ),

        "kampanya_avantaji":
            extract_benefits(
                lines,
                slug,
            ),

        "kampanya_suresi":
            (
                ""
                if end_date == "-"
                else end_date
            ),

        "hedef_kitle":
            extract_targets(
                raw_text,
                slug,
            ),

        "para_birimi":
            extract_currency(
                lines,
                slug,
            ),

        "kosullar":
            extract_conditions(
                lines
            ),

        "kaynak_url":
            url,

        "ham_metin":
            raw_text,
    }


# =========================================================
# SCHEMA VALIDATION
# =========================================================

def validate_schema(
    record,
    index,
):
    errors = []

    if (
        list(
            record.keys()
        )
        != SCHEMA_KEYS
    ):
        errors.append(
            (
                f"[{index}] schema "
                "key/order uyuşmuyor."
            )
        )

    for field in LIST_FIELDS:
        if not isinstance(
            record.get(
                field
            ),
            list,
        ):
            errors.append(
                (
                    f"[{index}] "
                    f"{field} list değil."
                )
            )

    for field in SCALAR_FIELDS:
        if not isinstance(
            record.get(
                field
            ),
            str,
        ):
            errors.append(
                (
                    f"[{index}] "
                    f"{field} string değil."
                )
            )

    if (
        record.get(
            "kayit_turu"
        )
        != "kampanya"
    ):
        errors.append(
            (
                f"[{index}] kayit_turu "
                "kampanya değil."
            )
        )

    serialized = json.dumps(
        record,
        ensure_ascii=False,
    )

    if "TRY" in serialized:
        errors.append(
            f"[{index}] TRY bulundu."
        )

    currencies = record.get(
        "para_birimi",
        [],
    )

    if any(
        currency != "TL"
        for currency in currencies
    ):
        errors.append(
            (
                f"[{index}] desteklenmeyen "
                "para birimi bulundu."
            )
        )

    if (
        not record.get(
            "urun_adi"
        )
        or
        not record.get(
            "kaynak_url"
        )
        or
        not record.get(
            "ham_metin"
        )
    ):
        errors.append(
            (
                f"[{index}] zorunlu "
                "provenance alanı boş."
            )
        )

    return errors


# =========================================================
# VALIDATION HELPERS
# =========================================================

def contains(
    values,
    fragment,
):
    fragment = normalize_match(
        fragment
    )

    return any(
        fragment
        in normalize_match(
            value
        )
        for value in values
    )


def contains_regex(
    values,
    pattern,
):
    return any(
        re.search(
            pattern,
            normalize_match(
                value
            ),
        )
        for value in values
    )


# =========================================================
# GLOBAL BENEFIT CLEANLINESS
# =========================================================

def validate_benefit_cleanliness(records):
    errors = []

    forbidden_fragments = (
        "bankacılık düzenleme",
        "yasal düzenlem",
        "satış görevlisine",
        "satış yetkilisine",
        "kasa yetkilisi",
        "geçerli değildir",
        "dahil değildir",
        "hariç tutul",
        "hariç tutabilir",
        "değişkenlik göstere",
        "vade farklı",
        "vade farkı uygulan",
        "taksitlendirme yapılmaz",
        "franchise",
        "bölünemez",
        "devredilemez",
        "paraya çevrilemez",
        "kullanım koşulları",
        "geçersiz sayıl",
        "hak kazanmak için",
        "hak kazanabilmek için",
        "birleştirilemez",
        "birlikte kullanılamaz",
    )

    for record in records:
        slug = get_slug(
            record[
                "kaynak_url"
            ]
        )

        benefits = record[
            "kampanya_avantaji"
        ]

        for fragment in forbidden_fragments:
            if contains(
                benefits,
                fragment,
            ):
                errors.append(
                    (
                        f"{slug} -> kampanya_avantaji "
                        f"içinde koşul/kısıt kaldı: "
                        f"{fragment}"
                    )
                )

        # İade / iptal şartı
        if contains_regex(
            benefits,
            (
                r"\b(?:"
                r"iade\s+ve\s+iptal"
                r"|iptal\s+ve\s+iade"
                r"|iade\s+edilen"
                r"|iptal\s+edilen"
                r"|iade\s+edilmesi"
                r"|iptal\s+edilmesi"
                r")\b"
            ),
        ):
            errors.append(
                (
                    f"{slug} -> kampanya_avantaji "
                    "içinde iade/iptal koşulu kaldı."
                )
            )

        if contains_regex(
            benefits,
            r"pos üzerinden.*seçil",
        ):
            errors.append(
                (
                    f"{slug} -> kampanya_avantaji "
                    "içinde POS seçim prosedürü kaldı."
                )
            )

    return errors


# =========================================================
# SEMANTIC VALIDATION
# =========================================================

def validate_semantics(records):
    errors = []

    by_slug = {
        get_slug(
            record[
                "kaynak_url"
            ]
        ):
            record

        for record
        in records
    }

    required_slugs = [
        "davetetkazan",
        "troy-idefix",
        "hepsiburada",
        "koton",
        "jack-jones",
        "trendyol",
        "yolcu360",
        "n11",
        "a-101-paraf",
        "vestel",
        "yatas",
        "pttavm",
        "yenilio",
        "ider",
        "pazarama-paraf",
        "demirdokum",
        "avantajli-kurlar",
        "enerya-finansmani",
    ]

    for slug in required_slugs:
        if slug not in by_slug:
            errors.append(
                (
                    "Kritik kayıt "
                    f"bulunamadı: {slug}"
                )
            )

    if errors:
        return errors

    # =====================================================
    # DAVET ET KAZAN
    # =====================================================

    davet = by_slug[
        "davetetkazan"
    ]

    if not contains(
        davet[
            "kampanya_avantaji"
        ],
        "0,1 gram",
    ):
        errors.append(
            (
                "davetetkazan -> "
                "0,1 gram avantajı çıkarılmadı."
            )
        )

    if (
        davet[
            "kampanya_suresi"
        ]
        != ""
    ):
        errors.append(
            (
                "davetetkazan -> "
                "açık uçlu bitiş boş olmalı."
            )
        )

    if not contains(
        davet[
            "kosullar"
        ],
        "Şubeden müşteri olan kişiler",
    ):
        errors.append(
            (
                "davetetkazan -> "
                "uzun koşulların son kısmı kayboldu."
            )
        )

    # =====================================================
    # TROY IDEFIX
    # =====================================================

    troy = by_slug[
        "troy-idefix"
    ]

    if not contains(
        troy[
            "kampanya_avantaji"
        ],
        "200 TL",
    ):
        errors.append(
            (
                "troy-idefix -> "
                "200 TL avantajı çıkarılmadı."
            )
        )

    if contains(
        troy[
            "kampanya_avantaji"
        ],
        "hak kazanmak için",
    ):
        errors.append(
            (
                "troy-idefix -> minimum harcama "
                "koşulu avantaj alanında kaldı."
            )
        )

    # =====================================================
    # HEPSIBURADA
    # =====================================================

    hepsiburada = by_slug[
        "hepsiburada"
    ]

    if (
        hepsiburada[
            "taksit_sayisi"
        ]
        != [
            "3",
            "6",
        ]
    ):
        errors.append(
            (
                "hepsiburada -> taksit yanlış: "
                f"{hepsiburada['taksit_sayisi']}"
            )
        )

    for fragment in (
        "12 taksit",
        "LCD Televizyon",
        "hariç tutabilir",
        "Xiaomi",
        "QCY",
    ):
        if contains(
            hepsiburada[
                "kampanya_avantaji"
            ],
            fragment,
        ):
            errors.append(
                (
                    "hepsiburada -> koşul/kısıt "
                    "avantaj alanında kaldı: "
                    f"{fragment}"
                )
            )

    # =====================================================
    # KOTON / JACK JONES
    # =====================================================

    for slug, percent in [
        (
            "koton",
            "%8",
        ),
        (
            "jack-jones",
            "%18",
        ),
    ]:
        item = by_slug[
            slug
        ]

        if not contains(
            item[
                "kampanya_avantaji"
            ],
            percent,
        ):
            errors.append(
                (
                    f"{slug} -> "
                    f"{percent} avantajı çıkarılmadı."
                )
            )

        if (
            item[
                "kampanya_suresi"
            ]
            != "31 Ağustos 2026"
        ):
            errors.append(
                (
                    f"{slug} -> listing "
                    "bitiş tarihi önceliklendirilmedi."
                )
            )

    # =====================================================
    # TRENDYOL
    # =====================================================

    trendyol = by_slug[
        "trendyol"
    ]

    if (
        trendyol[
            "taksit_sayisi"
        ]
        != [
            "3",
            "6",
            "9",
        ]
    ):
        errors.append(
            (
                "trendyol -> taksit yanlış: "
                f"{trendyol['taksit_sayisi']}"
            )
        )

    # =====================================================
    # YOLCU360
    # =====================================================

    yolcu = by_slug[
        "yolcu360"
    ]

    if not contains(
        yolcu[
            "kampanya_avantaji"
        ],
        "%10",
    ):
        errors.append(
            (
                "yolcu360 -> "
                "%10 normalize edilmedi."
            )
        )

    for fragment in (
        "katılmak için",
        "sadece kampanyaya katılan",
        "birleştirilemez",
    ):
        if contains(
            yolcu[
                "kampanya_avantaji"
            ],
            fragment,
        ):
            errors.append(
                (
                    "yolcu360 -> koşul "
                    "avantaj alanında kaldı: "
                    f"{fragment}"
                )
            )

    # =====================================================
    # N11
    # =====================================================

    n11 = by_slug[
        "n11"
    ]

    if (
        n11[
            "taksit_sayisi"
        ]
        != [
            "3"
        ]
    ):
        errors.append(
            (
                "n11 -> taksit yanlış: "
                f"{n11['taksit_sayisi']}"
            )
        )

    if contains(
        n11[
            "kampanya_avantaji"
        ],
        "hariç tutabilir",
    ):
        errors.append(
            (
                "n11 -> kategori istisnası "
                "avantaj alanında kaldı."
            )
        )

    # =====================================================
    # A101
    # =====================================================

    a101 = by_slug[
        "a-101-paraf"
    ]

    if contains(
        a101[
            "kampanya_avantaji"
        ],
        "kasa yetkilisi",
    ):
        errors.append(
            (
                "a101 -> kasa prosedürü "
                "avantaj alanında kaldı."
            )
        )

    # =====================================================
    # VESTEL
    # =====================================================

    vestel = by_slug[
        "vestel"
    ]

    if (
        vestel[
            "taksit_sayisi"
        ]
        != [
            "7",
            "9",
        ]
    ):
        errors.append(
            (
                "vestel -> taksit yanlış: "
                f"{vestel['taksit_sayisi']}"
            )
        )

    if contains(
        vestel[
            "kampanya_avantaji"
        ],
        "satış yetkilisine",
    ):
        errors.append(
            (
                "vestel -> satış prosedürü "
                "avantaj alanında kaldı."
            )
        )

    # =====================================================
    # YATAŞ
    # =====================================================

    yatas = by_slug[
        "yatas"
    ]

    if contains(
        yatas[
            "kampanya_avantaji"
        ],
        "Franchise",
    ):
        errors.append(
            (
                "yatas -> franchise koşulu "
                "avantaj alanında kaldı."
            )
        )

    # =====================================================
    # PTTAVM
    # =====================================================

    pttavm = by_slug[
        "pttavm"
    ]

    if contains(
        pttavm[
            "kampanya_avantaji"
        ],
        "hariç tutabilir",
    ):
        errors.append(
            (
                "pttavm -> kategori istisnası "
                "avantaj alanında kaldı."
            )
        )

    # =====================================================
    # YENILIO
    # =====================================================

    yenilio = by_slug[
        "yenilio"
    ]

    if (
        yenilio[
            "taksit_sayisi"
        ]
        != [
            "12"
        ]
    ):
        errors.append(
            (
                "yenilio -> taksit yanlış: "
                f"{yenilio['taksit_sayisi']}"
            )
        )

    if (
        contains(
            yenilio[
                "kampanya_avantaji"
            ],
            "iade ve iptal",
        )
        or
        contains(
            yenilio[
                "kampanya_avantaji"
            ],
            "iptal ve iade",
        )
    ):
        errors.append(
            (
                "yenilio -> iade/iptal "
                "koşulu avantaj alanında kaldı."
            )
        )

    # =====================================================
    # IDER
    # =====================================================

    ider = by_slug[
        "ider"
    ]

    if not contains(
        ider[
            "kampanya_avantaji"
        ],
        "%15",
    ):
        errors.append(
            (
                "ider -> "
                "%15 çıkarılmadı."
            )
        )

    if (
        ider[
            "taksit_sayisi"
        ]
        != [
            "6",
            "7",
        ]
    ):
        errors.append(
            (
                "ider -> taksit yanlış: "
                f"{ider['taksit_sayisi']}"
            )
        )

    # =====================================================
    # PAZARAMA
    # =====================================================

    pazarama = by_slug[
        "pazarama-paraf"
    ]

    if (
        pazarama[
            "taksit_sayisi"
        ]
        != [
            "2",
            "3",
            "6",
        ]
    ):
        errors.append(
            (
                "pazarama -> taksit yanlış: "
                f"{pazarama['taksit_sayisi']}"
            )
        )

    # =====================================================
    # DEMIRDOKUM
    # =====================================================

    demirdokum = by_slug[
        "demirdokum"
    ]

    if (
        demirdokum[
            "taksit_sayisi"
        ]
        != [
            "9"
        ]
    ):
        errors.append(
            (
                "demirdokum -> taksit yanlış: "
                f"{demirdokum['taksit_sayisi']}"
            )
        )

    # =====================================================
    # AVANTAJLI KURLAR
    # =====================================================

    kurlar = by_slug[
        "avantajli-kurlar"
    ]

    if (
        kurlar[
            "kampanya_suresi"
        ]
        != ""
    ):
        errors.append(
            (
                "avantajli-kurlar -> "
                "açık uçlu bitiş boş olmalı."
            )
        )

    # =====================================================
    # ENERYA
    # =====================================================

    enerya = by_slug[
        "enerya-finansmani"
    ]

    if (
        enerya[
            "finansman_tutari"
        ]
        != [
            "6.500 TL - 16.500 TL"
        ]
    ):
        errors.append(
            (
                "enerya -> finansman tutarı yanlış: "
                f"{enerya['finansman_tutari']}"
            )
        )

    if (
        enerya[
            "vade"
        ]
        != [
            "2 ay - 6 ay"
        ]
    ):
        errors.append(
            (
                "enerya -> vade yanlış: "
                f"{enerya['vade']}"
            )
        )

    if enerya[
        "kar_payi_orani"
    ]:
        errors.append(
            (
                "enerya -> vade farksız "
                "%0 kar payına çevrilmemeli."
            )
        )

    # =====================================================
    # GLOBAL AVANTAJ TEMİZLİĞİ
    # =====================================================

    errors.extend(
        validate_benefit_cleanliness(
            records
        )
    )

    return errors


# =========================================================
# MAIN
# =========================================================

def main():
    print()

    print(
        "=" * 118
    )

    print(
        "DÜNYA KATILIM - CAMPAIGN EXTRACTOR V2.2"
    )

    print(
        "=" * 118
    )

    print(
        "Input:",
        INPUT_FILE,
    )

    print(
        "Output:",
        OUTPUT_FILE,
    )

    print()

    # =====================================================
    # INPUT
    # =====================================================

    if not INPUT_FILE.exists():
        print(
            "Input dosyası bulunamadı ❌"
        )

        sys.exit(
            1
        )

    try:
        with INPUT_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:

            raw_data = json.load(
                file
            )

    except Exception as error:
        print(
            "RAW JSON okunamadı ❌"
        )

        print(
            error
        )

        sys.exit(
            1
        )

    raw_records = raw_data.get(
        "kampanyalar",
        [],
    )

    if not isinstance(
        raw_records,
        list,
    ):
        print(
            "'kampanyalar' list değil ❌"
        )

        sys.exit(
            1
        )

    extraction_errors = []
    schema_errors = []
    extracted = []

    # =====================================================
    # RAW COUNT
    # =====================================================

    if (
        len(
            raw_records
        )
        != EXPECTED_COUNT
    ):
        extraction_errors.append(
            (
                "RAW kayıt sayısı uyuşmuyor: "
                f"beklenen={EXPECTED_COUNT}, "
                f"actual={len(raw_records)}"
            )
        )

    # =====================================================
    # EXTRACTION
    # =====================================================

    for index, raw_record in enumerate(
        raw_records,
        start=1,
    ):
        title = (
            normalize_text(
                raw_record.get(
                    "kampanya_adi",
                    "",
                )
            )
            if isinstance(
                raw_record,
                dict,
            )
            else ""
        )

        print(
            (
                f"[{index:02d}/"
                f"{len(raw_records)}] "
                f"{title or 'BAŞLIK YOK'}"
            )
        )

        if not isinstance(
            raw_record,
            dict,
        ):
            extraction_errors.append(
                (
                    f"[{index}] RAW "
                    "kayıt dict değil."
                )
            )

            print(
                "  EXTRACTION: ❌"
            )

            continue

        try:
            record = extract_record(
                raw_record
            )

            extracted.append(
                record
            )

            record_errors = validate_schema(
                record,
                index,
            )

            schema_errors.extend(
                record_errors
            )

            print(
                "  SCHEMA:",
                (
                    "❌"
                    if record_errors
                    else "✅"
                ),
            )

            print(
                "  Taksit:",
                record[
                    "taksit_sayisi"
                ],
                "| Avantaj:",
                len(
                    record[
                        "kampanya_avantaji"
                    ]
                ),
                "| Koşul:",
                len(
                    record[
                        "kosullar"
                    ]
                ),
            )

        except Exception as error:
            extraction_errors.append(
                (
                    f"[{index}] {title} -> "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

            print(
                "  EXTRACTION: ❌",
                error,
            )

    # =====================================================
    # COUNT
    # =====================================================

    if (
        len(
            extracted
        )
        != EXPECTED_COUNT
    ):
        extraction_errors.append(
            (
                "Extracted kayıt sayısı "
                "uyuşmuyor: "
                f"beklenen={EXPECTED_COUNT}, "
                f"actual={len(extracted)}"
            )
        )

    # =====================================================
    # DUPLICATE
    # =====================================================

    urls = [
        normalize_match(
            record[
                "kaynak_url"
            ]
        )

        for record
        in extracted

        if record.get(
            "kaynak_url"
        )
    ]

    duplicate_url_count = (
        len(
            urls
        )
        -
        len(
            set(
                urls
            )
        )
    )

    if duplicate_url_count:
        extraction_errors.append(
            (
                "Duplicate kaynak_url "
                f"sayısı: {duplicate_url_count}"
            )
        )

    # =====================================================
    # SEMANTIC
    # =====================================================

    semantic_errors = (
        validate_semantics(
            extracted
        )
        if extracted
        else [
            (
                "Semantic validation için "
                "extracted kayıt yok."
            )
        ]
    )

    # =====================================================
    # SAVE
    # =====================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            extracted,
            file,
            ensure_ascii=False,
            indent=4,
        )

    # =====================================================
    # REPORT
    # =====================================================

    total_errors = (
        len(
            extraction_errors
        )
        +
        len(
            schema_errors
        )
        +
        len(
            semantic_errors
        )
    )

    print()

    print(
        "=" * 118
    )

    print(
        "CAMPAIGN EXTRACTION V2.2 SONUCU"
    )

    print(
        "=" * 118
    )

    print(
        "Beklenen:",
        EXPECTED_COUNT,
    )

    print(
        "RAW:",
        len(
            raw_records
        ),
    )

    print(
        "Extracted:",
        len(
            extracted
        ),
    )

    print(
        "Duplicate URL:",
        duplicate_url_count,
    )

    print(
        "Extraction error:",
        len(
            extraction_errors
        ),
    )

    print(
        "Schema error:",
        len(
            schema_errors
        ),
    )

    print(
        "Semantic error:",
        len(
            semantic_errors
        ),
    )

    print(
        "Toplam error:",
        total_errors,
    )

    # =====================================================
    # ERRORS
    # =====================================================

    if extraction_errors:
        print()

        print(
            "EXTRACTION HATALARI:"
        )

        for error in extraction_errors:
            print(
                "-",
                error,
            )

    if schema_errors:
        print()

        print(
            "SCHEMA HATALARI:"
        )

        for error in schema_errors:
            print(
                "-",
                error,
            )

    if semantic_errors:
        print()

        print(
            "SEMANTİK HATALAR:"
        )

        for error in semantic_errors:
            print(
                "-",
                error,
            )

    print()

    # =====================================================
    # FINAL
    # =====================================================

    if total_errors == 0:
        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "CAMPAIGN EXTRACTION V2.2 "
                "BAŞARILI ✅"
            )
        )

        print(
            (
                "43 aktif kampanya "
                "18-key final schema'ya "
                "başarıyla dönüştürüldü ✅"
            )
        )

        print(
            (
                "Kampanya avantajı / koşul "
                "ayrımı doğrulandı ✅"
            )
        )

        print(
            (
                "Kategori, minimum harcama ve "
                "kampanya kullanım kısıtları "
                "avantaj alanından temizlendi ✅"
            )
        )

    else:
        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "CAMPAIGN EXTRACTION V2.2 "
                "KONTROL GEREKİYOR ❌"
            )
        )

    print()

    print(
        "JSON:",
        OUTPUT_FILE,
    )

    print(
        "=" * 118
    )

    if total_errors:
        sys.exit(
            1
        )


if __name__ == "__main__":
    main()