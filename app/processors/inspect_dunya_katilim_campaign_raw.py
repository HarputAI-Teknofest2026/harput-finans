import json
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse


# =========================================================
# CONFIG
# =========================================================

ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    ROOT
    / "data"
    / "raw"
    / "dunya_katilim_kampanyalar.json"
)

EXPECTED_COUNT = 43


ALLOWED_CATEGORIES = {
    "Yeni Müşteri Kampanyaları",
    "Paraf Kampanyaları",
    "Finansman Kampanyaları",
    "Sigorta Kampanyaları",
    "Yatırım Kampanyaları",
    "Kart Kampanyaları",
}


TURKISH_MONTHS = {
    "ocak": 1,
    "şubat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "eylül": 9,
    "ekim": 10,
    "kasım": 11,
    "aralık": 12,
}


# =========================================================
# CRITICAL SEMANTIC RULES
# =========================================================
#
# Bunlar tüm 43 kampanyayı hard-code etmek için değil,
# önemli ve birbirinden farklı kampanya tiplerinin RAW
# kaynağında kritik bilgilerin gerçekten bulunduğunu
# doğrulamak için kullanılır.
#
# =========================================================

CRITICAL_RULES = {
    "davetetkazan": {
        "name": "Davet Et, Altın Kazan!",
        "category": "Yeni Müşteri Kampanyaları",
        "list_end_date": "-",
        "patterns": [
            r"0[,\.]1\s*gram",
            r"1\s*gram",
            r"paraf\s*kart",
            r"bireysel\s+müşter",
            r"davet\s*kod",
        ],
    },

    "troy-idefix": {
        "name": "TROY idefix",
        "category": "Kart Kampanyaları",
        "list_end_date": "31 Ağustos 2026",
        "patterns": [
            r"1\.000\s*TL",
            r"200\s*TL",
            r"3\.000\s*TL",
            r"10\s*Haziran\s*2026",
            r"31\s*Ağustos\s*2026",
            r"TROY",
        ],
    },

    "hepsiburada": {
        "name": "Hepsiburada",
        "category": "Paraf Kampanyaları",
        "list_end_date": "31 Ağustos 2026",
        "patterns": [
            r"100\s*TL",
            r"1\.000\s*TL",
            r"6\.000\s*TL",
            r"3[-\s]*6\s*taksit",
            r"Paraf",
        ],
    },

    "koton": {
        "name": "Koton",
        "category": "Kart Kampanyaları",
        "list_end_date": "31 Ağustos 2026",
        "patterns": [
            r"%\s*8",
            r"nakit\s+iade",
            r"30\.04\.2026",
            r"bireysel\s+müşter",
        ],
        "expected_source_date_warning": True,
    },

    "jack-jones": {
        "name": "Jack & Jones",
        "category": "Kart Kampanyaları",
        "list_end_date": "31 Ağustos 2026",
        "patterns": [
            r"%\s*18",
            r"nakit\s+iade",
            r"30\.04\.2026",
            r"bireysel\s+müşter",
        ],
        "expected_source_date_warning": True,
    },

    "trendyol": {
        "name": "Trendyol",
        "category": "Paraf Kampanyaları",
        "list_end_date": "31 Ağustos 2026",
        "patterns": [
            r"1\.000\s*TL",
            r"6\.000\s*TL",
            r"10\.000\s*TL",
            r"200\.000\s*TL",
            r"3\s*taksit",
            r"6\s*taksit",
            r"9\s*taksit",
        ],
    },

    "n11": {
        "name": "N11",
        "category": "Paraf Kampanyaları",
        "list_end_date": "31 Ağustos 2026",
        "patterns": [
            r"2\.000\s*TL",
            r"3\s*(?:aya\s*varan\s*)?taksit",
            r"Paraf",
        ],
    },

    "a-101-paraf": {
        "name": "A101",
        "category": "Paraf Kampanyaları",
        "list_end_date": "31 Ağustos 2026",
        "patterns": [
            r"300\s*TL",
            r"6\s*aya\s*varan\s*taksit",
            r"A101",
            r"Paraf",
        ],
    },

    "yolcu360": {
        "name": "Yolcu360",
        "category": "Paraf Kampanyaları",
        "list_end_date": "31 Ağustos 2026",
        "patterns": [
            r"(?:%\s*10|10\s*%)",
            r"3\s*taksit",
            r"PARAFYD360",
            r"yurt\s*içi\s*araç\s*kiralama",
        ],
    },

    "ider": {
        "name": "İder",
        "category": "Paraf Kampanyaları",
        "list_end_date": "31 Ağustos 2026",
        "patterns": [
            r"%\s*15",
            r"7\s*taksit",
        ],
    },

    "vatan": {
        "name": "Vatan",
        "category": "Paraf Kampanyaları",
        "list_end_date": "31 Ağustos 2026",
        "patterns": [
            r"6\s*aya\s*varan\s*taksit",
            r"2\s*,\s*3\s*,\s*4\s*,\s*5\s*veya\s*6",
            r"Paraf",
        ],
    },

    "monster": {
        "name": "Monster",
        "category": "Paraf Kampanyaları",
        "list_end_date": "31 Ağustos 2026",
        "patterns": [
            r"12\s*aya\s*varan\s*taksit",
            r"Monster",
            r"Paraf",
        ],
    },

    "avantajli-kurlar": {
        "name": "Kur Farkıyla Öndesin!",
        "category": "Yatırım Kampanyaları",
        "list_end_date": "-",
        "patterns": [
            r"döviz",
            r"altın",
            r"gümüş",
            r"kur",
        ],
    },

    "enerya-finansmani": {
        "name": "Enerya Finansmanı",
        "category": "Finansman Kampanyaları",
        "list_end_date": "-",
        "patterns": [
            r"Enerya",
            r"abonelik",
            r"doğalgaz",
            r"finansman",
        ],
    },
}


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
        value = value.replace(old, new)

    value = re.sub(
        r"[ \t]+",
        " ",
        value,
    )

    return value.strip()


def normalize_match(value):
    value = normalize_text(value)

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


# =========================================================
# URL
# =========================================================

def get_slug(url):
    try:
        parsed = urlparse(
            str(url or "")
        )

    except Exception:
        return ""

    parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if len(parts) != 2:
        return ""

    if parts[0] != "kampanyalar":
        return ""

    return parts[1]


# =========================================================
# DATE
# =========================================================

def parse_numeric_date(value):
    match = re.search(
        r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b",
        str(value or ""),
    )

    if not match:
        return None

    try:
        return date(
            int(match.group(3)),
            int(match.group(2)),
            int(match.group(1)),
        )

    except ValueError:
        return None


def parse_turkish_date(value):
    value = normalize_match(
        value
    )

    match = re.search(
        r"(\d{1,2})\s+([a-zçğıöşü]+)\s+(\d{4})",
        value,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    day = int(
        match.group(1)
    )

    month_name = match.group(
        2
    )

    year = int(
        match.group(3)
    )

    month = TURKISH_MONTHS.get(
        month_name
    )

    if month is None:
        return None

    try:
        return date(
            year,
            month,
            day,
        )

    except ValueError:
        return None


def parse_scrape_date(value):
    try:
        return datetime.fromisoformat(
            str(value)
        ).date()

    except Exception:
        return None


# =========================================================
# SOURCE INTERNAL DATE WARNINGS
# =========================================================

def find_internal_past_expiry_dates(
    raw_text,
    scrape_date,
):
    if scrape_date is None:
        return []

    patterns = [
        (
            r"Kampanya\s+"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})"
            r"\s+tarihine\s+kadar\s+geçerli"
        ),
        (
            r"Kampanya\s+"
            r"(\d{1,2}[./]\d{1,2}[./]\d{4})"
            r"\s+tarihine\s+kadar"
        ),
        (
            r"Kampanya\s+"
            r"(\d{1,2}\s+"
            r"[A-Za-zÇĞİÖŞÜçğıöşü]+\s+"
            r"\d{4})"
            r"\s+tarihine\s+kadar"
        ),
    ]

    findings = []

    for pattern in patterns:
        matches = re.finditer(
            pattern,
            raw_text,
            flags=re.IGNORECASE,
        )

        for match in matches:
            raw_date = normalize_text(
                match.group(1)
            )

            parsed = (
                parse_numeric_date(
                    raw_date
                )
                or parse_turkish_date(
                    raw_date
                )
            )

            if (
                parsed is not None
                and parsed < scrape_date
            ):
                findings.append(
                    (
                        raw_date,
                        parsed,
                    )
                )

    unique = []
    seen = set()

    for raw_date, parsed in findings:
        key = (
            raw_date,
            parsed.isoformat(),
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        unique.append(
            (
                raw_date,
                parsed,
            )
        )

    return unique


# =========================================================
# GENERAL SAFETY CHECK
# =========================================================

def inspect_general_record(
    record,
    scrape_date,
):
    errors = []
    warnings = []

    title = normalize_text(
        record.get(
            "kampanya_adi",
            "",
        )
    )

    category = normalize_text(
        record.get(
            "liste_kategorisi",
            "",
        )
    )

    status = normalize_text(
        record.get(
            "liste_durumu",
            "",
        )
    )

    end_date = normalize_text(
        record.get(
            "liste_bitis_tarihi",
            "",
        )
    )

    url = normalize_text(
        record.get(
            "kaynak_url",
            "",
        )
    )

    raw_text = normalize_text(
        record.get(
            "ham_metin",
            "",
        )
    )

    listing_text = normalize_text(
        record.get(
            "listing_text",
            "",
        )
    )

    # -----------------------------------------------------
    # BASIC FIELDS
    # -----------------------------------------------------

    if not title:
        errors.append(
            "Başlık boş."
        )

    if category not in ALLOWED_CATEGORIES:
        errors.append(
            (
                "Kategori geçersiz: "
                f"{category!r}"
            )
        )

    if status != "Devam ediyor":
        errors.append(
            (
                "Aktif RAW kaydında durum "
                f"'Devam ediyor' değil: {status!r}"
            )
        )

    if not end_date:
        errors.append(
            "Bitiş metadata'sı boş."
        )

    if not url:
        errors.append(
            "kaynak_url boş."
        )

    if not raw_text:
        errors.append(
            "ham_metin boş."
        )

    # -----------------------------------------------------
    # CONTENT LENGTH
    # -----------------------------------------------------

    if raw_text:
        if len(raw_text) < 250:
            errors.append(
                (
                    "ham_metin anlamsal inceleme "
                    "için çok kısa: "
                    f"{len(raw_text)} karakter."
                )
            )

        elif len(raw_text) < 500:
            warnings.append(
                (
                    "ham_metin kısa fakat kabul "
                    f"edilebilir: {len(raw_text)} karakter."
                )
            )

    # -----------------------------------------------------
    # TITLE / CATEGORY PROVENANCE
    # -----------------------------------------------------

    if (
        title
        and normalize_match(title)
        not in normalize_match(raw_text)
    ):
        errors.append(
            "Başlık ham_metin içinde doğrulanamıyor."
        )

    if (
        category
        and normalize_match(category)
        not in normalize_match(raw_text)
        and normalize_match(category)
        not in normalize_match(listing_text)
    ):
        errors.append(
            "Kategori kaynakta doğrulanamıyor."
        )

    # -----------------------------------------------------
    # LIST END DATE PROVENANCE
    # -----------------------------------------------------

    if end_date == "-":
        combined = normalize_match(
            (
                f"{listing_text}\n"
                f"{raw_text}"
            )
        )

        if (
            "bitiş tarihi: -"
            not in combined
        ):
            warnings.append(
                (
                    "Metadata bitiş '-' fakat "
                    "literal 'Bitiş Tarihi: -' "
                    "kaynak metinde bulunamadı."
                )
            )

    else:
        if (
            normalize_match(end_date)
            not in normalize_match(
                (
                    f"{listing_text}\n"
                    f"{raw_text}"
                )
            )
        ):
            errors.append(
                (
                    "Liste bitiş tarihi kaynak "
                    "metinde doğrulanamıyor: "
                    f"{end_date}"
                )
            )

    # -----------------------------------------------------
    # PAGE NOISE
    # -----------------------------------------------------

    noise_markers = [
        "Zorunlu Çerezler",
        "Çerez Aydınlatma Metni",
        (
            "ÇEREZ KULLANIMINA İLİŞKİN "
            "AYDINLATMA METNİ"
        ),
        (
            "Tüm site ziyaretçilerimizi "
            "daha iyi tanımak"
        ),
    ]

    raw_norm = normalize_match(
        raw_text
    )

    for marker in noise_markers:
        if normalize_match(marker) in raw_norm:
            errors.append(
                (
                    "Cookie/footer gürültüsü "
                    f"bulundu: {marker}"
                )
            )
            break

    # -----------------------------------------------------
    # COMMERCIAL URL LEAK
    # -----------------------------------------------------

    url_norm = normalize_match(
        url
    )

    if (
        "ticari" in url_norm
        or "/isim-icin/" in url_norm
        or "/isimicin/" in url_norm
    ):
        errors.append(
            "Ticari URL bireysel RAW'a sızmış."
        )

    # -----------------------------------------------------
    # INTERNAL PAST DATE CONTRADICTIONS
    # -----------------------------------------------------

    internal_dates = (
        find_internal_past_expiry_dates(
            raw_text,
            scrape_date,
        )
    )

    for raw_date, parsed in internal_dates:
        warnings.append(
            (
                "Kaynak içi geçmiş kampanya tarihi: "
                f"{raw_date}. Listing metadata="
                f"{end_date!r}. Extractor "
                "kampanya_suresi için listing "
                "metadata'sını önceliklendirmeli."
            )
        )

    return (
        errors,
        warnings,
    )


# =========================================================
# CRITICAL RULE CHECK
# =========================================================

def inspect_critical_record(
    slug,
    record,
    rule,
):
    errors = []

    raw_text = normalize_text(
        record.get(
            "ham_metin",
            "",
        )
    )

    category = normalize_text(
        record.get(
            "liste_kategorisi",
            "",
        )
    )

    end_date = normalize_text(
        record.get(
            "liste_bitis_tarihi",
            "",
        )
    )

    expected_category = rule.get(
        "category",
        "",
    )

    expected_end_date = rule.get(
        "list_end_date",
        "",
    )

    if (
        expected_category
        and category != expected_category
    ):
        errors.append(
            (
                "Kategori uyuşmuyor: "
                f"beklenen={expected_category!r}, "
                f"actual={category!r}"
            )
        )

    if (
        expected_end_date
        and end_date != expected_end_date
    ):
        errors.append(
            (
                "Bitiş metadata uyuşmuyor: "
                f"beklenen={expected_end_date!r}, "
                f"actual={end_date!r}"
            )
        )

    for pattern in rule.get(
        "patterns",
        [],
    ):
        if not re.search(
            pattern,
            raw_text,
            flags=re.IGNORECASE,
        ):
            errors.append(
                (
                    "Kritik kaynak bilgisi "
                    "bulunamadı. Regex: "
                    f"{pattern!r}"
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
        "DÜNYA KATILIM - CAMPAIGN RAW SEMANTIC INSPECTOR V1"
    )
    print(
        "=" * 118
    )
    print(
        "Input:",
        INPUT_FILE,
    )
    print()

    if not INPUT_FILE.exists():
        print(
            "Input dosyası bulunamadı ❌"
        )
        sys.exit(1)

    try:
        with INPUT_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(
                file
            )

    except Exception as error:
        print(
            "JSON okunamadı ❌"
        )
        print(
            error
        )
        sys.exit(1)

    records = data.get(
        "kampanyalar",
        [],
    )

    if not isinstance(
        records,
        list,
    ):
        print(
            "'kampanyalar' list değil ❌"
        )
        sys.exit(1)

    errors = []
    warnings = []

    # =====================================================
    # COUNT
    # =====================================================

    if len(records) != EXPECTED_COUNT:
        errors.append(
            (
                "Kayıt sayısı uyuşmuyor: "
                f"beklenen={EXPECTED_COUNT}, "
                f"actual={len(records)}"
            )
        )

    scrape_date = parse_scrape_date(
        data.get(
            "scrape_zamani",
            "",
        )
    )

    if scrape_date is None:
        errors.append(
            "scrape_zamani parse edilemedi."
        )

    # =====================================================
    # URL INDEX
    # =====================================================

    records_by_slug = {}

    for record in records:
        if not isinstance(
            record,
            dict,
        ):
            continue

        slug = get_slug(
            record.get(
                "kaynak_url",
                "",
            )
        )

        if slug:
            records_by_slug[
                slug
            ] = record

    # =====================================================
    # DUPLICATES
    # =====================================================

    url_counts = Counter(
        normalize_match(
            item.get(
                "kaynak_url",
                "",
            )
        )
        for item in records
        if isinstance(
            item,
            dict,
        )
    )

    duplicate_urls = [
        url
        for url, count
        in url_counts.items()
        if url
        and count > 1
    ]

    if duplicate_urls:
        errors.append(
            (
                "Duplicate URL bulundu: "
                f"{duplicate_urls}"
            )
        )

    # =====================================================
    # GENERAL SEMANTIC INSPECTION
    # =====================================================

    print(
        "GENEL SEMANTİK KONTROLLER"
    )
    print(
        "=" * 118
    )

    for index, record in enumerate(
        records,
        start=1,
    ):
        if not isinstance(
            record,
            dict,
        ):
            errors.append(
                (
                    f"[{index}] kayıt "
                    "dict değil."
                )
            )
            continue

        title = normalize_text(
            record.get(
                "kampanya_adi",
                "",
            )
        )

        slug = get_slug(
            record.get(
                "kaynak_url",
                "",
            )
        )

        record_errors, record_warnings = (
            inspect_general_record(
                record,
                scrape_date,
            )
        )

        print(
            (
                f"[{index:02d}/{len(records)}] "
                f"{title}"
            )
        )

        if record_errors:
            print(
                "  SEMANTIC: ❌"
            )

            for error in record_errors:
                print(
                    "   ERROR:",
                    error,
                )

                errors.append(
                    (
                        f"{slug or title} "
                        f"-> {error}"
                    )
                )

        else:
            print(
                "  SEMANTIC: ✅"
            )

        for warning in record_warnings:
            print(
                "   WARNING:",
                warning,
            )

            warnings.append(
                (
                    f"{slug or title} "
                    f"-> {warning}"
                )
            )

    # =====================================================
    # CRITICAL CAMPAIGN CHECKS
    # =====================================================

    print()
    print(
        "=" * 118
    )
    print(
        "KRİTİK KAMPANYA İÇERİK KONTROLLERİ"
    )
    print(
        "=" * 118
    )

    critical_pass = 0
    critical_fail = 0

    for slug, rule in CRITICAL_RULES.items():
        record = records_by_slug.get(
            slug
        )

        print()
        print(
            f"[{slug}] {rule['name']}"
        )

        if record is None:
            message = (
                "Kritik kampanya RAW içinde bulunamadı."
            )

            print(
                "  ❌",
                message,
            )

            errors.append(
                f"{slug} -> {message}"
            )

            critical_fail += 1
            continue

        critical_errors = (
            inspect_critical_record(
                slug,
                record,
                rule,
            )
        )

        if critical_errors:
            critical_fail += 1

            print(
                "  CRITICAL CHECK: ❌"
            )

            for error in critical_errors:
                print(
                    "   ERROR:",
                    error,
                )

                errors.append(
                    (
                        f"{slug} -> "
                        f"{error}"
                    )
                )

        else:
            critical_pass += 1

            print(
                "  CRITICAL CHECK: ✅"
            )

    # =====================================================
    # CATEGORY DISTRIBUTION
    # =====================================================

    category_counts = Counter(
        normalize_text(
            item.get(
                "liste_kategorisi",
                "",
            )
        )
        for item in records
        if isinstance(
            item,
            dict,
        )
    )

    # =====================================================
    # REPORT
    # =====================================================

    print()
    print(
        "=" * 118
    )
    print(
        "CAMPAIGN RAW SEMANTIC INSPECTION SONUCU"
    )
    print(
        "=" * 118
    )

    print(
        "Beklenen kayıt:",
        EXPECTED_COUNT,
    )

    print(
        "Gerçek kayıt:",
        len(
            records
        ),
    )

    print(
        "Critical check başarılı:",
        critical_pass,
    )

    print(
        "Critical check başarısız:",
        critical_fail,
    )

    print(
        "Duplicate URL:",
        len(
            duplicate_urls
        ),
    )

    print(
        "Safety / semantic warning:",
        len(
            warnings
        ),
    )

    print(
        "Semantic error:",
        len(
            errors
        ),
    )

    print()
    print(
        "KATEGORİ DAĞILIMI:"
    )

    for category, count in sorted(
        category_counts.items()
    ):
        print(
            f"- {category}: {count}"
        )

    if warnings:
        print()
        print(
            "UYARILAR:"
        )

        for warning in warnings:
            print(
                "-",
                warning,
            )

    if errors:
        print()
        print(
            "HATALAR:"
        )

        for error in errors:
            print(
                "-",
                error,
            )

    print()

    if not errors:
        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "CAMPAIGN RAW SEMANTİK "
                "INSPECTION BAŞARILI ✅"
            )
        )

        print(
            (
                "RAW artık campaign extractor "
                "yazmak için yeterli durumda ✅"
            )
        )

    else:
        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "CAMPAIGN RAW SEMANTİK "
                "INSPECTION BAŞARISIZ ❌"
            )
        )

        print(
            (
                "Extractor yazmadan önce "
                "RAW sorunları düzeltilmeli."
            )
        )

    print(
        "=" * 118
    )

    if errors:
        sys.exit(
            1
        )


if __name__ == "__main__":
    main()