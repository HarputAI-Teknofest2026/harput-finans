import json
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path


BANK = "Kuveyt Türk Katılım Bankası A.Ş."
SNAPSHOT = date(2026, 8, 23)


KEYS = [
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


LISTS = {
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


STRINGS = set(KEYS) - LISTS


ROOT = Path(__file__).resolve().parents[2]

PROC = ROOT / "data" / "processed"


CANDIDATES = [
    PROC / "kuveyt_turk_all.json",
    PROC / "kuveyt_turk_final.json",
    PROC / "kuveyt_turk_all(1).json",
]


OUT = PROC / "kuveyt_turk_all.json"


BACKUP = (
    PROC
    / "kuveyt_turk_all_before_normalization.json"
)


MONTH_NUM = {
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
    "aralik": 12,
}


MONTH_NAME = {
    1: "Ocak",
    2: "Şubat",
    3: "Mart",
    4: "Nisan",
    5: "Mayıs",
    6: "Haziran",
    7: "Temmuz",
    8: "Ağustos",
    9: "Eylül",
    10: "Ekim",
    11: "Kasım",
    12: "Aralık",
}


TYPE_MAP = {
    "taksit": "Taksit",
    "hediye": "Hediye",
    "indirim": "İndirim",
    "indirim+taksit": "İndirim + Taksit",
    "taksit+kar_payi": "Taksit + Kâr Payı",
    "mil+hediye": "Mil + Hediye",
    "hediye+indirim+kur_avantaji":
        "Hediye + İndirim + Kur Avantajı",
    "kur_avantaji": "Kur Avantajı",
    "indirim+taksit+kar_payi":
        "İndirim + Taksit + Kâr Payı",
    "ayricalik": "Ayrıcalık",
    "mil+hediye+indirim+taksit+kur_avantaji":
        "Mil + Hediye + İndirim + Taksit + Kur Avantajı",
}


TARGETS = {
    "Konut Finansmanı": [
        "18 yaşından büyük ve Türkiye'de yerleşik kişiler",
    ],

    "İlk Evim Konut Finansmanı": [
        "İlk evini alacak, 18 yaşından büyük ve Türkiye'de yerleşik kişiler",
    ],

    "2B Finansmanı": [
        "6292 sayılı Kanun kapsamında 2B arazisinde hak sahibi olan kişiler",
    ],

    "Gurbetten Sılaya Gayrimenkul Finansmanı": [
        "Yurt dışında yaşayan ve geliri yabancı para cinsinden olan Türkiye Cumhuriyeti vatandaşları",
        "Mütekabiliyet kapsamındaki yabancı ülke vatandaşları",
    ],

    "Hac-Umre Finansmanı": [
        "18 yaşını tamamlamış Kuveyt Türk müşterileri",
    ],

    "Eğitim Finansmanı": [
        "Öğrenciler",
        "Gelir belgesi olmayan öğrenciler için veli veya yasal vasiler",
    ],

    "Seyahat Finansmanı": [
        "18 yaşını tamamlamış Kuveyt Türk müşterileri",
    ],

    "Kira Finansmanı": [
        "Kirasını toplu ödemek isteyen Kuveyt Türk müşterileri",
    ],

    "Yeşil Konut Finansmanı": [
        "18 yaşından büyük ve Türkiye'de yerleşik Kuveyt Türk müşterileri",
    ],

    "Sürdürülebilir Araç Finansmanı": [
        "18 yaşını doldurmuş Kuveyt Türk müşterileri",
    ],
}


UI_NOISE = {
    "kampanya son geçerlilik tarihi",
    "kampanyaya katılmak için hemen başvurun",
    "t.c. kimlik numarası",
    "telefon",
    "doğum tarihi",
    "kişisel verilerle ilgili",
    "aydınlatma metni",
    "kabul ediyorum",
    "kabul etmiyorum",
    "devam",
    "kampanyayı paylaş",
    "facebook'da paylaş",
    "x'de paylaş",
    "linkedin'de paylaş",
    "whatsapp'da paylaş",
}


def space(value):
    if not isinstance(
        value,
        str,
    ):
        return ""

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def uniq(values):
    result = []
    seen = set()

    if not isinstance(
        values,
        list,
    ):
        return []

    for value in values:

        if not isinstance(
            value,
            str,
        ):
            continue

        value = space(
            value
        )

        if not value:
            continue

        key = value.casefold()

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            value
        )

    return result


def input_file():

    for path in CANDIDATES:

        if path.exists():
            return path

    raise FileNotFoundError(
        "Kuveyt Türk input bulunamadı. "
        "Beklenen: data/processed/kuveyt_turk_all.json "
        "veya kuveyt_turk_all(1).json"
    )


def pct_text(value):

    value = space(
        value
    )

    # 0,5% -> %0,5
    # 1.10% -> %1,10

    value = re.sub(
        r"(?<!%)\b(\d+(?:[.,]\d+)?)\s*%",
        lambda match:
            "%"
            + match.group(1).replace(
                ".",
                ",",
            ),
        value,
    )

    # %1.99 -> %1,99

    value = re.sub(
        r"%\s*(\d+)\.(\d+)",
        r"%\1,\2",
        value,
    )

    value = re.sub(
        r"%\s+",
        "%",
        value,
    )

    return value


def money_num(value):

    value = (
        value
        .strip()
        .replace(
            " ",
            "",
        )
    )

    if value.endswith(
        ",00"
    ):
        value = value[:-3]

    # 5000 -> 5.000

    if re.fullmatch(
        r"\d+",
        value,
    ):
        value = (
            f"{int(value):,}"
            .replace(
                ",",
                ".",
            )
        )

    return value


def pct_list(
    values,
    conditions,
):

    result = []

    if not isinstance(
        values,
        list,
    ):
        return result

    for value in values:

        if not isinstance(
            value,
            str,
        ):
            continue

        value = pct_text(
            value
        )

        if not value:
            continue

        lower = (
            value.casefold()
        )

        # Örnek calculator değerlerini
        # ana finansman alanına alma.

        if (
            "örnek" in lower
            and (
                "hesap" in lower
                or "tablo" in lower
            )
        ):

            conditions.append(
                "Örnek hesaplama verisi: "
                + value
            )

            continue

        matches = re.findall(
            r"%\d+(?:[.,]\d+)?",
            value,
        )

        if (
            matches
            and not re.fullmatch(
                r"%\d+(?:[.,]\d+)?",
                value,
            )
        ):

            # Mapping bilgisini kaybetme.
            conditions.append(
                value
            )

        for match in matches:

            result.append(
                match.replace(
                    ".",
                    ",",
                )
            )

    return uniq(
        result
    )


def money_list(
    values,
    conditions,
):

    result = []

    if not isinstance(
        values,
        list,
    ):
        return result

    for value in values:

        if not isinstance(
            value,
            str,
        ):
            continue

        value = (
            space(value)
            .replace(
                "TRY",
                "TL",
            )
        )

        matches = re.findall(
            r"(?<!\d)"
            r"(\d[\d.]*(?:,\d{1,2})?)"
            r"\s*(?:TL|₺)\b",
            value,
        )

        pure = bool(
            re.fullmatch(
                r"\d[\d.]*(?:,\d{1,2})?"
                r"\s*(?:TL|₺)",
                value,
            )
        )

        if (
            matches
            and not pure
        ):

            # Orijinal açıklamayı kosullar'da koru.
            conditions.append(
                value
            )

        for match in matches:

            result.append(
                f"{money_num(match)} TL"
            )

    return uniq(
        result
    )


def vade_list(
    values,
    conditions,
):

    result = []

    if not isinstance(
        values,
        list,
    ):
        return result

    for value in values:

        if not isinstance(
            value,
            str,
        ):
            continue

        value = space(
            value
        )

        if not value:
            continue

        # Erteleme süresi gerçek vade değildir.

        if "ertelem" in value.casefold():

            conditions.append(
                value
            )

            continue

        matches = re.findall(
            r"(?<!\d)"
            r"(\d+)\s*"
            r"(aya|ay|yıla|yıl|yila|yil|güne|gün|gune|gun)\b",
            value,
            flags=re.IGNORECASE,
        )

        pure = bool(
            re.fullmatch(
                r"\d+\s*"
                r"(?:aya|ay|yıla|yıl|yila|yil|güne|gün|gune|gun)",
                value,
                flags=re.IGNORECASE,
            )
        )

        if (
            matches
            and not pure
        ):

            conditions.append(
                value
            )

        for number, unit in matches:

            number = int(
                number
            )

            if number == 0:
                continue

            unit = (
                unit.casefold()
            )

            if unit in {
                "aya",
                "ay",
            }:

                normalized_unit = "ay"

            elif unit in {
                "yıla",
                "yıl",
                "yila",
                "yil",
            }:

                normalized_unit = "yıl"

            else:

                normalized_unit = "gün"

            result.append(
                f"{number} {normalized_unit}"
            )

    return uniq(
        result
    )


def installment_list(
    values,
    conditions,
):

    result = []

    if not isinstance(
        values,
        list,
    ):
        return result

    for value in values:

        if not isinstance(
            value,
            str,
        ):
            continue

        value = space(
            value
        )

        if not value:
            continue

        if re.fullmatch(
            r"\d+",
            value,
        ):

            result.append(
                str(
                    int(value)
                )
            )

            continue

        # Orijinal taksit mappingini kaybetme.

        conditions.append(
            value
        )

        # 2-5 taksit
        # ->
        # 2,3,4,5

        ranges = re.findall(
            r"(\d+)\s*[-–]\s*(\d+)\s*taksit",
            value,
            flags=re.IGNORECASE,
        )

        for start, end in ranges:

            start = int(
                start
            )

            end = int(
                end
            )

            if (
                0 < start <= end
                and end - start <= 12
            ):

                result.extend(
                    str(number)
                    for number in range(
                        start,
                        end + 1,
                    )
                )

        # 6-7 aya varan taksit

        ranges_aya = re.findall(
            r"(\d+)\s*[-–]\s*(\d+)"
            r"\s*aya?\s+varan"
            r"[^,.]{0,30}taksit",
            value,
            flags=re.IGNORECASE,
        )

        for start, end in ranges_aya:

            start = int(
                start
            )

            end = int(
                end
            )

            if (
                0 < start <= end
                and end - start <= 12
            ):

                result.extend(
                    str(number)
                    for number in range(
                        start,
                        end + 1,
                    )
                )

        patterns = [
            r"(?<![-\d])(\d+)\s*taksit(?:e|li)?\b",
            r"(?<![-\d])(\d+)\s*aya?\s+varan[^,.]{0,20}taksit",
            r"(?<![-\d])(\d+)\s*ay\s+taksit\b",
        ]

        for pattern in patterns:

            for number in re.findall(
                pattern,
                value,
                flags=re.IGNORECASE,
            ):

                number = int(
                    number
                )

                if number > 0:

                    result.append(
                        str(number)
                    )

    return uniq(
        result
    )


def fee_list(values):

    result = []

    if not isinstance(
        values,
        list,
    ):
        return result

    for value in values:

        if not isinstance(
            value,
            str,
        ):
            continue

        value = pct_text(
            value
        )

        lower = (
            value.casefold()
        )

        # Calculator boilerplate.

        if (
            "bu tablo bilgi amaçlıdır"
            in lower
        ):

            if (
                "tahsis ücreti müşteriden peşin"
                in lower
            ):

                result.append(
                    "Tahsis ücreti müşteriden peşin tahsil edilir"
                )

            continue

        if value:

            result.append(
                value
            )

    return uniq(
        result
    )


def targets(record):

    name = space(
        record.get(
            "urun_adi",
            "",
        )
    )

    if (
        record.get(
            "kayit_turu"
        )
        == "finansman"
        and name in TARGETS
    ):

        return TARGETS[name]

    result = []

    for value in record.get(
        "hedef_kitle",
        [],
    ):

        if not isinstance(
            value,
            str,
        ):
            continue

        value = space(
            value
        )

        if not value:
            continue

        # Başlık / FAQ sorusu hedef kitle değildir.

        if (
            value.casefold()
            == name.casefold()
        ):
            continue

        if "?" in value:
            continue

        result.append(
            value
        )

    return uniq(
        result
    )


def clean_conditions(
    values,
    name,
):

    result = []

    for value in values:

        if not isinstance(
            value,
            str,
        ):
            continue

        value = pct_text(
            value
        )

        lower = (
            value.casefold()
        )

        if not value:
            continue

        if lower in UI_NOISE:
            continue

        if (
            lower
            == name.casefold()
        ):
            continue

        if (
            len(value) <= 80
            and lower in {
                "bireysel kredi kartı başvurularını",
                "şubelerimize",
                "şubemize",
                "tıklayınız.",
                "tıklayınız",
                "tıklayın.",
                "tıklayın",
            }
        ):
            continue

        result.append(
            value
        )

    return uniq(
        result
    )


def parse_period(value):

    value = space(
        value
    )

    if not value:
        return None

    # 01.05.2026 - 31.12.2026

    match = re.fullmatch(
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})"
        r"\s*-\s*"
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})",
        value,
    )

    if match:

        try:

            return (
                date(
                    int(match.group(3)),
                    int(match.group(2)),
                    int(match.group(1)),
                ),
                date(
                    int(match.group(6)),
                    int(match.group(5)),
                    int(match.group(4)),
                ),
            )

        except ValueError:

            return None

    # 31.12.2026 tarihine kadar

    match = re.fullmatch(
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})"
        r"\s+tarihine kadar",
        value,
        flags=re.IGNORECASE,
    )

    if match:

        try:

            return (
                None,
                date(
                    int(match.group(3)),
                    int(match.group(2)),
                    int(match.group(1)),
                ),
            )

        except ValueError:

            return None

    month_re = (
        r"(Ocak|Şubat|Subat|Mart|Nisan|Mayıs|Mayis|"
        r"Haziran|Temmuz|Ağustos|Agustos|Eylül|Eylul|"
        r"Ekim|Kasım|Kasim|Aralık|Aralik)"
    )

    # 1 Mayıs 2026 - 31 Aralık 2026

    match = re.fullmatch(
        rf"(\d{{1,2}})\s+{month_re}\s+(\d{{4}})"
        rf"\s*-\s*"
        rf"(\d{{1,2}})\s+{month_re}\s+(\d{{4}})",
        value,
        flags=re.IGNORECASE,
    )

    if match:

        start_month = MONTH_NUM.get(
            match.group(2).casefold()
        )

        end_month = MONTH_NUM.get(
            match.group(5).casefold()
        )

        if (
            start_month
            and end_month
        ):

            try:

                return (
                    date(
                        int(match.group(3)),
                        start_month,
                        int(match.group(1)),
                    ),
                    date(
                        int(match.group(6)),
                        end_month,
                        int(match.group(4)),
                    ),
                )

            except ValueError:

                return None

    # 31 Aralık 2026

    match = re.fullmatch(
        rf"(\d{{1,2}})\s+{month_re}\s+(\d{{4}})",
        value,
        flags=re.IGNORECASE,
    )

    if match:

        month = MONTH_NUM.get(
            match.group(2).casefold()
        )

        if month:

            try:

                return (
                    None,
                    date(
                        int(match.group(3)),
                        month,
                        int(match.group(1)),
                    ),
                )

            except ValueError:

                return None

    return None


def fmt(value):

    return (
        f"{value.day} "
        f"{MONTH_NAME[value.month]} "
        f"{value.year}"
    )


def norm_period(value):

    parsed = parse_period(
        value
    )

    if not parsed:

        return space(
            value
        )

    start, end = parsed

    if start is None:

        return fmt(
            end
        )

    return (
        f"{fmt(start)}"
        f" - "
        f"{fmt(end)}"
    )


def active(value):

    parsed = parse_period(
        value
    )

    # Parse edilemeyen kaydı otomatik silme.

    if not parsed:

        return True

    start, end = parsed

    if start is None:

        return (
            SNAPSHOT
            <= end
        )

    return (
        start
        <= SNAPSHOT
        <= end
    )


def patch(original):

    record = dict(
        original
    )

    record[
        "banka"
    ] = BANK

    name = space(
        record.get(
            "urun_adi",
            "",
        )
    )

    conditions = uniq(
        record.get(
            "kosullar",
            [],
        )
    )

    fees = fee_list(
        record.get(
            "masraf_bilgisi",
            [],
        )
    )

    # ==============================================================================================
    # FINANCE -> CAMPAIGN LEAKAGE
    # ==============================================================================================

    if (
        record.get(
            "kayit_turu"
        )
        == "finansman"
    ):

        for value in record.get(
            "kampanya_avantaji",
            [],
        ):

            if not isinstance(
                value,
                str,
            ):
                continue

            value = pct_text(
                value
            )

            if not value:
                continue

            lower = (
                value.casefold()
            )

            if (
                "tahsis ücreti"
                in lower
                or "sigorta"
                in lower
            ):

                fees.append(
                    value
                )

            else:

                conditions.append(
                    value
                )

        record[
            "kampanya_turu"
        ] = ""

        record[
            "kampanya_avantaji"
        ] = []

        record[
            "kampanya_suresi"
        ] = ""

    else:

        raw_type = space(
            record.get(
                "kampanya_turu",
                "",
            )
        )

        record[
            "kampanya_turu"
        ] = TYPE_MAP.get(
            raw_type,
            raw_type,
        )

        record[
            "kampanya_avantaji"
        ] = uniq(
            [
                pct_text(
                    value
                )
                for value
                in record.get(
                    "kampanya_avantaji",
                    [],
                )
                if isinstance(
                    value,
                    str,
                )
            ]
        )

        record[
            "kampanya_suresi"
        ] = norm_period(
            record.get(
                "kampanya_suresi",
                "",
            )
        )

    # ==============================================================================================
    # STRUCTURED FIELDS
    # ==============================================================================================

    record[
        "kar_payi_orani"
    ] = pct_list(
        record.get(
            "kar_payi_orani",
            [],
        ),
        conditions,
    )

    evlilik = (
        record.get(
            "kayit_turu"
        )
        == "kampanya"
        and name
        == "Evlenecek Olan veya Yeni Evli Çiftlere Kuveyt Türk’ten Müjde Evlilik Paketi!"
    )

    # Evlilik Paketi içine Diyanet Umre'den
    # %60 finansman oranı sızmış durumda.
    # Ana alandan kaldır, koşullarda provenance olarak tut.

    if evlilik:

        for value in record.get(
            "finansman_orani",
            [],
        ):

            if isinstance(
                value,
                str,
            ):

                conditions.append(
                    pct_text(
                        value
                    )
                )

        record[
            "finansman_orani"
        ] = []

    else:

        record[
            "finansman_orani"
        ] = pct_list(
            record.get(
                "finansman_orani",
                [],
            ),
            conditions,
        )

    record[
        "finansman_tutari"
    ] = money_list(
        record.get(
            "finansman_tutari",
            [],
        ),
        conditions,
    )

    record[
        "vade"
    ] = vade_list(
        record.get(
            "vade",
            [],
        ),
        conditions,
    )

    record[
        "taksit_sayisi"
    ] = installment_list(
        record.get(
            "taksit_sayisi",
            [],
        ),
        conditions,
    )

    record[
        "masraf_bilgisi"
    ] = uniq(
        fees
    )

    record[
        "hedef_kitle"
    ] = targets(
        record
    )

    # ==============================================================================================
    # CURRENCY
    # ==============================================================================================

    currencies = []

    for currency in record.get(
        "para_birimi",
        [],
    ):

        if not isinstance(
            currency,
            str,
        ):
            continue

        currency = space(
            currency
        )

        if currency == "TRY":
            currency = "TL"

        # "DÖVİZ" bir concrete para birimi değildir.

        if (
            currency.casefold()
            in {
                "döviz",
                "doviz",
            }
        ):

            conditions.append(
                "Para birimi kaynakta genel olarak döviz şeklinde belirtilmiştir."
            )

            continue

        if currency:

            currencies.append(
                currency
            )

    structured_for_currency = (
        record.get(
            "finansman_tutari",
            [],
        )
        + record.get(
            "kampanya_avantaji",
            [],
        )
    )

    if any(
        re.search(
            r"\bTL\b",
            value,
        )
        for value
        in structured_for_currency
        if isinstance(
            value,
            str,
        )
    ):

        currencies.append(
            "TL"
        )

    record[
        "para_birimi"
    ] = uniq(
        currencies
    )

    # ==============================================================================================
    # TARGETED FINANCE FIXES
    # ==============================================================================================

    if (
        record.get(
            "kayit_turu"
        )
        == "finansman"
    ):

        # 3 ay erteleme vade değildir.
        # Ana vade 120 aydır.

        if name in {
            "Konut Finansmanı",
            "İlk Evim Konut Finansmanı",
        }:

            record[
                "vade"
            ] = [
                "120 ay"
            ]

        # İhtiyaç Kart:
        # 2 ay ödemesiz dönem + 6-34 ay repayment
        # tek bir vade gibi yazılmamalı.
        # Telefon alışverişinde kaynak açıkça 10 taksit diyor.

        if (
            name
            == "İhtiyaç Kart"
        ):

            record[
                "vade"
            ] = []

            has_10 = any(
                "10 taksit"
                in space(
                    value
                ).casefold()
                for value
                in original.get(
                    "taksit_sayisi",
                    [],
                )
                if isinstance(
                    value,
                    str,
                )
            )

            record[
                "taksit_sayisi"
            ] = (
                ["10"]
                if has_10
                else []
            )

    # ==============================================================================================
    # EVLİLİK PAKETİ
    # ==============================================================================================

    if evlilik:

        record[
            "finansman_tutari"
        ] = [
            "100.000 TL"
        ]

        record[
            "vade"
        ] = [
            "12 ay"
        ]

        record[
            "taksit_sayisi"
        ] = [
            "5",
            "10",
            "12",
        ]

        record[
            "hedef_kitle"
        ] = [
            "2026 yılında evlenmiş veya evlenecek yeni müşteriler",
            "KTAILE26 referans kodu ile müşteri olan yeni müşteriler",
        ]

        record[
            "kampanya_avantaji"
        ] = [
            "10.000 TL - 50.000 TL arasındaki ilk 3 harcamaya vade farksız 10 taksit",
            "50.000 TL - 100.000 TL arası harcamalarda vade farksız 5 taksit",
            "Araç finansmanında 10 puan indirim",
            "Konut finansmanında 5 puan indirim",
            "İhtiyaç Kart'ta 100.000 TL'ye kadar %1,99 oranla 12 aya varan taksit",
        ]

        record[
            "para_birimi"
        ] = [
            "TL"
        ]

    # ==============================================================================================
    # CONDITIONS
    # ==============================================================================================

    record[
        "kosullar"
    ] = clean_conditions(
        conditions,
        name,
    )

    # ==============================================================================================
    # TYPES
    # ==============================================================================================

    for field in LISTS:

        if not isinstance(
            record.get(
                field
            ),
            list,
        ):

            record[field] = []

        record[
            field
        ] = uniq(
            record[field]
        )

    for field in STRINGS:

        value = record.get(
            field,
            "",
        )

        if value is None:
            value = ""

        if not isinstance(
            value,
            str,
        ):
            value = str(
                value
            )

        if field == "ham_metin":

            record[
                field
            ] = value.strip()

        else:

            record[
                field
            ] = space(
                value
            )

    # Exact 18-key + exact order

    return {
        key: record[key]
        for key in KEYS
    }


def validate(records):

    errors = []

    if len(
        records
    ) != 103:

        errors.append(
            f"Toplam 103 bekleniyordu, "
            f"{len(records)} bulundu."
        )

    finance_count = sum(
        record[
            "kayit_turu"
        ] == "finansman"
        for record
        in records
    )

    campaign_count = sum(
        record[
            "kayit_turu"
        ] == "kampanya"
        for record
        in records
    )

    if (
        finance_count
        != 30
    ):

        errors.append(
            f"Finansman 30 bekleniyordu, "
            f"{finance_count} bulundu."
        )

    if (
        campaign_count
        != 73
    ):

        errors.append(
            f"Kampanya 73 bekleniyordu, "
            f"{campaign_count} bulundu."
        )

    urls = []

    for index, record in enumerate(
        records,
        start=1,
    ):

        prefix = (
            f"[{index:03d}] "
            f"{record.get('urun_adi', '')}"
        )

        if list(
            record.keys()
        ) != KEYS:

            errors.append(
                f"{prefix} -> schema/order yanlış"
            )

        if (
            record[
                "banka"
            ]
            != BANK
        ):

            errors.append(
                f"{prefix} -> banka adı yanlış"
            )

        if (
            record[
                "kayit_turu"
            ]
            not in {
                "finansman",
                "kampanya",
            }
        ):

            errors.append(
                f"{prefix} -> kayit_turu yanlış"
            )

        for field in LISTS:

            if not isinstance(
                record[field],
                list,
            ):

                errors.append(
                    f"{prefix} -> {field} list değil"
                )

        for field in STRINGS:

            if not isinstance(
                record[field],
                str,
            ):

                errors.append(
                    f"{prefix} -> {field} string değil"
                )

        if (
            "TRY"
            in record[
                "para_birimi"
            ]
        ):

            errors.append(
                f"{prefix} -> TRY bulundu"
            )

        if any(
            currency.casefold()
            in {
                "döviz",
                "doviz",
            }
            for currency
            in record[
                "para_birimi"
            ]
        ):

            errors.append(
                f"{prefix} -> "
                "DÖVİZ concrete currency değil"
            )

        for value in record[
            "taksit_sayisi"
        ]:

            if not re.fullmatch(
                r"\d+",
                value,
            ):

                errors.append(
                    f"{prefix} -> "
                    f"bozuk taksit: {value}"
                )

        for field in (
            "kar_payi_orani",
            "finansman_orani",
        ):

            for value in record[
                field
            ]:

                if not re.fullmatch(
                    r"%\d+(?:,\d+)?",
                    value,
                ):

                    errors.append(
                        f"{prefix} -> "
                        f"bozuk {field}: {value}"
                    )

        if (
            record[
                "kayit_turu"
            ]
            == "finansman"
        ):

            if (
                record[
                    "kampanya_turu"
                ]
                or record[
                    "kampanya_avantaji"
                ]
                or record[
                    "kampanya_suresi"
                ]
            ):

                errors.append(
                    f"{prefix} -> "
                    "finance campaign leakage"
                )

            # Bu snapshot'taki finance kâr oranları
            # sadece calculator example idi.

            if record[
                "kar_payi_orani"
            ]:

                errors.append(
                    f"{prefix} -> "
                    "örnek kâr oranı ana alanda kalmış olabilir"
                )

        else:

            if not record[
                "kampanya_suresi"
            ]:

                errors.append(
                    f"{prefix} -> "
                    "kampanya_suresi boş"
                )

            elif not active(
                record[
                    "kampanya_suresi"
                ]
            ):

                errors.append(
                    f"{prefix} -> "
                    "snapshot tarihinde aktif değil"
                )

            # Campaign finansman_orani sadece
            # Diyanet Umre kampanyasında source-backed.

            if (
                record[
                    "finansman_orani"
                ]
                and record[
                    "urun_adi"
                ]
                !=
                "Diyanet Umre Finansmanı ile Vade Farksız 3 Taksit İmkanı!"
            ):

                errors.append(
                    f"{prefix} -> "
                    "campaign finansman_orani leakage"
                )

        if record[
            "kaynak_url"
        ]:

            urls.append(
                record[
                    "kaynak_url"
                ]
            )

    for url, count in Counter(
        urls
    ).items():

        if count > 1:

            errors.append(
                f"Duplicate URL ({count}): {url}"
            )

    return errors


def audit(
    input_count,
    records,
    skipped,
):

    finance = [
        record
        for record in records
        if record[
            "kayit_turu"
        ] == "finansman"
    ]

    campaigns = [
        record
        for record in records
        if record[
            "kayit_turu"
        ] == "kampanya"
    ]

    duplicate_urls = [
        url
        for url, count in Counter(
            record[
                "kaynak_url"
            ]
            for record
            in records
            if record[
                "kaynak_url"
            ]
        ).items()
        if count > 1
    ]

    bad_installments = [
        (
            record[
                "urun_adi"
            ],
            value,
        )
        for record
        in records
        for value
        in record[
            "taksit_sayisi"
        ]
        if not value.isdigit()
    ]

    bad_percentages = [
        (
            record[
                "urun_adi"
            ],
            field,
            value,
        )
        for record
        in records
        for field
        in (
            "kar_payi_orani",
            "finansman_orani",
        )
        for value
        in record[field]
        if not re.fullmatch(
            r"%\d+(?:,\d+)?",
            value,
        )
    ]

    finance_leakage = [
        record[
            "urun_adi"
        ]
        for record
        in finance
        if (
            record[
                "kampanya_turu"
            ]
            or record[
                "kampanya_avantaji"
            ]
            or record[
                "kampanya_suresi"
            ]
        )
    ]

    campaign_ratio = [
        record[
            "urun_adi"
        ]
        for record
        in campaigns
        if record[
            "finansman_orani"
        ]
    ]

    print()

    print(
        "=" * 120
    )

    print(
        "KUVEYT TÜRK - FINAL PATCH AUDIT"
    )

    print(
        "=" * 120
    )

    print(
        f"Input kayıt           : {input_count}"
    )

    print(
        f"Final kayıt           : {len(records)}"
    )

    print(
        f"Finansman             : {len(finance)}"
    )

    print(
        f"Kampanya              : {len(campaigns)}"
    )

    print(
        f"Çıkarılan kampanya    : {len(skipped)}"
    )

    print(
        "Exact 18-key schema   : "
        f"{sum(list(r.keys()) == KEYS for r in records)}"
        f"/{len(records)}"
    )

    print(
        f"Duplicate URL         : {len(duplicate_urls)}"
    )

    print(
        "TRY kalan             : "
        f"{sum('TRY' in r['para_birimi'] for r in records)}"
    )

    print(
        "DÖVİZ kalan           : "
        f"{sum(any(c.casefold() in {'döviz', 'doviz'} for c in r['para_birimi']) for r in records)}"
    )

    print(
        f"Bozuk taksit          : {len(bad_installments)}"
    )

    print(
        f"Bozuk yüzde           : {len(bad_percentages)}"
    )

    print(
        f"Finance leakage       : {len(finance_leakage)}"
    )

    print(
        f"Campaign fin. oranı   : {len(campaign_ratio)}"
    )

    print()

    print(
        "SNAPSHOT DIŞI ÇIKARILAN KAMPANYALAR"
    )

    print(
        "-" * 120
    )

    if skipped:

        for name, duration in skipped:

            print(
                f"❌ {name}"
            )

            print(
                f"   Süre: {duration}"
            )

    else:

        print(
            "Çıkarılan kampanya yok."
        )

    print()

    print(
        "KRİTİK KAYIT KONTROLLERİ"
    )

    print(
        "-" * 120
    )

    names = [
        "Araç Finansmanı",
        "Konut Finansmanı",
        "İlk Evim Konut Finansmanı",
        "Taksitlio Alışveriş Finansmanı",
        "Alışveriş Finansmanı",
        "Evlenecek Olan veya Yeni Evli Çiftlere Kuveyt Türk’ten Müjde Evlilik Paketi!",
        "Diyanet Umre Finansmanı ile Vade Farksız 3 Taksit İmkanı!",
    ]

    by_name = {
        record[
            "urun_adi"
        ]: record
        for record
        in records
    }

    for name in names:

        record = by_name.get(
            name
        )

        if not record:
            continue

        print(
            f"✅ {name}"
        )

        print(
            f"   Kâr Payı : {record['kar_payi_orani']}"
        )

        print(
            f"   Fin.Oranı: {record['finansman_orani']}"
        )

        print(
            f"   Tutar    : {record['finansman_tutari']}"
        )

        print(
            f"   Vade     : {record['vade']}"
        )

        print(
            f"   Taksit   : {record['taksit_sayisi']}"
        )

        print(
            f"   Currency : {record['para_birimi']}"
        )

    print(
        "=" * 120
    )


def main():

    print()

    print(
        "=" * 120
    )

    print(
        "KUVEYT TÜRK - FINAL NORMALIZATION PATCH"
    )

    print(
        "=" * 120
    )

    source = input_file()

    print(
        f"Input : {source}"
    )

    print(
        f"Output: {OUT}"
    )

    print(
        "Snapshot tarihi: 23.08.2026"
    )

    print()

    with open(
        source,
        "r",
        encoding="utf-8",
    ) as file:

        raw = json.load(
            file
        )

    if isinstance(
        raw,
        dict,
    ):

        records = raw.get(
            "kayitlar"
        )

        if not isinstance(
            records,
            list,
        ):

            raise ValueError(
                "Eski wrapper bulundu ama "
                "'kayitlar' listesi yok."
            )

        print(
            "Eski wrapper formatı bulundu ✅"
        )

    elif isinstance(
        raw,
        list,
    ):

        records = raw

        print(
            "Root zaten list formatında."
        )

    else:

        raise ValueError(
            "JSON root dict veya list olmalı."
        )

    input_count = len(
        records
    )

    print(
        f"Input kayıt sayısı: {input_count}"
    )

    print()

    final = []

    skipped = []

    for index, old in enumerate(
        records,
        start=1,
    ):

        name = space(
            old.get(
                "urun_adi",
                "",
            )
        )

        if (
            old.get(
                "kayit_turu"
            )
            == "kampanya"
            and not active(
                old.get(
                    "kampanya_suresi",
                    "",
                )
            )
        ):

            print(
                f"[{index:03d}/{input_count}] "
                f"SKIP ❌ {name}"
            )

            skipped.append(
                (
                    name,
                    old.get(
                        "kampanya_suresi",
                        "",
                    ),
                )
            )

            continue

        final.append(
            patch(
                old
            )
        )

        print(
            f"[{index:03d}/{input_count}] "
            f"OK ✅ {name}"
        )

    audit(
        input_count,
        final,
        skipped,
    )

    errors = validate(
        final
    )

    if errors:

        print()

        print(
            "=" * 120
        )

        print(
            "VALIDATION ERRORS"
        )

        print(
            "=" * 120
        )

        for error in errors:

            print(
                "❌",
                error,
            )

        print()

        print(
            "KUVEYT TÜRK FINAL PATCH BAŞARISIZ ❌"
        )

        print(
            "Final dosya yazılmadı."
        )

        raise SystemExit(
            1
        )

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if (
        source.resolve()
        == OUT.resolve()
        and not BACKUP.exists()
    ):

        shutil.copy2(
            source,
            BACKUP,
        )

        print()

        print(
            f"Backup oluşturuldu: {BACKUP}"
        )

    with open(
        OUT,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            final,
            file,
            ensure_ascii=False,
            indent=2,
        )

    # Final dosyayı tekrar oku ve tekrar validate et.

    with open(
        OUT,
        "r",
        encoding="utf-8",
    ) as file:

        saved = json.load(
            file
        )

    errors = validate(
        saved
    )

    if errors:

        print()

        print(
            "Re-read validation başarısız ❌"
        )

        for error in errors:

            print(
                "❌",
                error,
            )

        raise SystemExit(
            1
        )

    print()

    print(
        "=" * 120
    )

    print(
        "KUVEYT TÜRK FINAL PATCH BAŞARILI ✅"
    )

    print(
        "=" * 120
    )

    print(
        f"JSON: {OUT}"
    )

    print()

    print(
        "Wrapper kaldırıldı ✅"
    )

    print(
        "Banka adı standardize edildi ✅"
    )

    print(
        "TRY -> TL normalize edildi ✅"
    )

    print(
        "DÖVİZ etiketi concrete currency alanından çıkarıldı ✅"
    )

    print(
        "Taksit sayıları numeric string yapıldı ✅"
    )

    print(
        "Finansman oranları normalize edildi ✅"
    )

    print(
        "Vade ve tutar alanları normalize edildi ✅"
    )

    print(
        "Örnek hesaplama kâr oranları ana alandan çıkarıldı ✅"
    )

    print(
        "Finance -> campaign leakage temizlendi ✅"
    )

    print(
        "Evlilik Paketi structured leakage temizlendi ✅"
    )

    print(
        "Snapshot dışı kampanyalar çıkarıldı ✅"
    )

    print(
        "Exact 18-key schema korundu ✅"
    )

    print(
        "Duplicate URL kontrolü geçti ✅"
    )

    print(
        "=" * 120
    )


if __name__ == "__main__":
    main()