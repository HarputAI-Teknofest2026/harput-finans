import json
import re
import sys
from collections import Counter
from datetime import datetime, date
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
EXPECTED_BANK = "Dünya Katılım Bankası A.Ş."
EXPECTED_LIST_URL = "https://dunyakatilim.com.tr/kampanyalar"

EXPECTED_KEYS = {
    "kampanya_adi",
    "liste_kategorisi",
    "liste_durumu",
    "liste_bitis_tarihi",
    "kaynak_url",
    "final_url",
    "http_status",
    "listing_text",
    "ham_metin",
}

ALLOWED_CATEGORIES = {
    "Yeni Müşteri Kampanyaları",
    "Paraf Kampanyaları",
    "Finansman Kampanyaları",
    "Sigorta Kampanyaları",
    "Yatırım Kampanyaları",
    "Kart Kampanyaları",
}

NOISE_MARKERS = [
    "Zorunlu Çerezler",
    "Çerez Aydınlatma Metni",
    "ÇEREZ KULLANIMINA İLİŞKİN AYDINLATMA METNİ",
    "Tüm site ziyaretçilerimizi daha iyi tanımak",
]

EXPIRED_MARKERS = [
    "kampanya süresi dolmuştur",
    "kampanya suresi dolmustur",
    "kampanya sona erdi",
    "kampanya sona ermiştir",
    "sona erdi",
    "süresi doldu",
    "süresi dolmuştur",
]

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

    value = re.sub(r"[ \t]+", " ", value)

    return value.strip()


def normalize_match(value):
    value = normalize_text(value)

    value = value.replace("İ", "i")
    value = value.replace("I", "ı")
    value = value.casefold()

    value = re.sub(r"\s+", " ", value)

    return value.strip()


# =========================================================
# DATE HELPERS
# =========================================================

def parse_turkish_date(value):
    value = normalize_match(value)

    match = re.search(
        r"(\d{1,2})\s+([a-zçğıöşü]+)\s+(\d{4})",
        value,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    day = int(match.group(1))
    month_name = match.group(2)
    year = int(match.group(3))

    month = TURKISH_MONTHS.get(month_name)

    if not month:
        return None

    try:
        return date(
            year,
            month,
            day,
        )

    except ValueError:
        return None


def parse_numeric_date(value):
    match = re.search(
        r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b",
        value,
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


def parse_scrape_date(value):
    try:
        return datetime.fromisoformat(
            value
        ).date()

    except Exception:
        return None


# =========================================================
# INTERNAL EXPIRY DETECTION
# =========================================================

def find_internal_expiry_dates(text):
    """
    Sadece kampanya bitişi anlamına gelebilecek
    bağlamdaki tarihleri toplar.

    Genel başlangıç tarihleri veya mevzuat
    tarihleri bu kontrole dahil edilmez.
    """

    text = normalize_text(
        text
    )

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
            r"\s+tarihine\s+kadar\s+geçerli"
        ),
    ]

    found = []

    for pattern in patterns:
        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
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

            if parsed is not None:
                found.append(
                    (
                        raw_date,
                        parsed,
                    )
                )

    unique = []
    seen = set()

    for raw_date, parsed in found:
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
# URL HELPERS
# =========================================================

def valid_campaign_url(url):
    try:
        parsed = urlparse(
            url
        )

    except Exception:
        return False

    return (
        parsed.scheme == "https"
        and parsed.netloc == "dunyakatilim.com.tr"
        and parsed.path.startswith(
            "/kampanyalar/"
        )
    )


def is_commercial_url(url):
    normalized = normalize_match(
        url
    )

    markers = [
        "ticari",
        "/isim-icin/",
        "/isimicin/",
    ]

    return any(
        marker in normalized
        for marker in markers
    )


# =========================================================
# LOAD
# =========================================================

def load_json():
    if not INPUT_FILE.exists():
        print(
            f"Input bulunamadı: {INPUT_FILE}"
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

    except json.JSONDecodeError as error:
        print(
            "JSON parse hatası:"
        )
        print(
            error
        )
        sys.exit(1)

    return data


# =========================================================
# MAIN
# =========================================================

def main():
    print()
    print(
        "=" * 118
    )
    print(
        "DÜNYA KATILIM - CAMPAIGN RAW VALIDATOR V1"
    )
    print(
        "=" * 118
    )
    print(
        "Input:",
        INPUT_FILE,
    )
    print()

    data = load_json()

    errors = []
    warnings = []

    # =====================================================
    # ROOT
    # =====================================================

    if not isinstance(
        data,
        dict,
    ):
        print(
            "ROOT JSON object/dict değil ❌"
        )
        sys.exit(1)

    if data.get(
        "banka"
    ) != EXPECTED_BANK:
        errors.append(
            (
                "Banka adı uyuşmuyor: "
                f"{data.get('banka')!r}"
            )
        )

    if data.get(
        "liste_url"
    ) != EXPECTED_LIST_URL:
        errors.append(
            (
                "Liste URL uyuşmuyor: "
                f"{data.get('liste_url')!r}"
            )
        )

    declared_expected = data.get(
        "beklenen_aktif_kampanya_sayisi"
    )

    declared_count = data.get(
        "kampanya_sayisi"
    )

    records = data.get(
        "kampanyalar"
    )

    if not isinstance(
        records,
        list,
    ):
        print(
            "'kampanyalar' list değil ❌"
        )
        sys.exit(1)

    actual_count = len(
        records
    )

    if declared_expected != EXPECTED_COUNT:
        errors.append(
            (
                "beklenen_aktif_kampanya_sayisi "
                f"{EXPECTED_COUNT} değil: "
                f"{declared_expected!r}"
            )
        )

    if declared_count != actual_count:
        errors.append(
            (
                "kampanya_sayisi ile gerçek liste "
                "uzunluğu uyuşmuyor: "
                f"declared={declared_count}, "
                f"actual={actual_count}"
            )
        )

    if actual_count != EXPECTED_COUNT:
        errors.append(
            (
                "Aktif kampanya sayısı uyuşmuyor: "
                f"beklenen={EXPECTED_COUNT}, "
                f"actual={actual_count}"
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
    # DUPLICATES
    # =====================================================

    url_counter = Counter(
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

    title_counter = Counter(
        normalize_match(
            item.get(
                "kampanya_adi",
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
        key
        for key, count
        in url_counter.items()
        if key
        and count > 1
    ]

    duplicate_titles = [
        key
        for key, count
        in title_counter.items()
        if key
        and count > 1
    ]

    if duplicate_urls:
        errors.append(
            (
                "Duplicate kaynak_url bulundu: "
                f"{duplicate_urls}"
            )
        )

    if duplicate_titles:
        errors.append(
            (
                "Duplicate kampanya başlığı bulundu: "
                f"{duplicate_titles}"
            )
        )

    # =====================================================
    # RECORD VALIDATION
    # =====================================================

    print(
        f"Beklenen kayıt: {EXPECTED_COUNT}"
    )

    print(
        f"Gerçek kayıt:   {actual_count}"
    )

    print()

    for index, record in enumerate(
        records,
        start=1,
    ):
        print(
            "-" * 118
        )

        if not isinstance(
            record,
            dict,
        ):
            errors.append(
                (
                    f"[{index}] kayıt "
                    "object/dict değil."
                )
            )

            print(
                f"[{index}] INVALID RECORD ❌"
            )

            continue

        title = normalize_text(
            record.get(
                "kampanya_adi",
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

        print(
            (
                f"[{index}/{actual_count}] "
                f"{title or 'BAŞLIK YOK'}"
            )
        )

        record_errors = []
        record_warnings = []

        # -------------------------------------------------
        # EXACT KEY SET
        # -------------------------------------------------

        actual_keys = set(
            record.keys()
        )

        missing_keys = (
            EXPECTED_KEYS
            - actual_keys
        )

        extra_keys = (
            actual_keys
            - EXPECTED_KEYS
        )

        if missing_keys:
            record_errors.append(
                (
                    "Eksik key: "
                    f"{sorted(missing_keys)}"
                )
            )

        if extra_keys:
            record_errors.append(
                (
                    "Beklenmeyen key: "
                    f"{sorted(extra_keys)}"
                )
            )

        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        if not title:
            record_errors.append(
                "kampanya_adi boş."
            )

        # -------------------------------------------------
        # CATEGORY
        # -------------------------------------------------

        category = normalize_text(
            record.get(
                "liste_kategorisi",
                "",
            )
        )

        if category not in ALLOWED_CATEGORIES:
            record_errors.append(
                (
                    "Geçersiz/boş liste_kategorisi: "
                    f"{category!r}"
                )
            )

        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        status = normalize_text(
            record.get(
                "liste_durumu",
                "",
            )
        )

        if status != "Devam ediyor":
            record_errors.append(
                (
                    "Aktif raw kaydında "
                    "liste_durumu 'Devam ediyor' değil: "
                    f"{status!r}"
                )
            )

        # -------------------------------------------------
        # LIST END DATE
        # -------------------------------------------------

        list_end_date = normalize_text(
            record.get(
                "liste_bitis_tarihi",
                "",
            )
        )

        if not list_end_date:
            record_errors.append(
                "liste_bitis_tarihi boş."
            )

        elif list_end_date != "-":
            parsed_list_end = parse_turkish_date(
                list_end_date
            )

            if parsed_list_end is None:
                record_errors.append(
                    (
                        "liste_bitis_tarihi "
                        "parse edilemedi: "
                        f"{list_end_date!r}"
                    )
                )

            elif (
                scrape_date is not None
                and parsed_list_end < scrape_date
            ):
                record_errors.append(
                    (
                        "Aktif kaydın liste bitiş tarihi "
                        "scrape tarihinden eski: "
                        f"{list_end_date}"
                    )
                )

        # -------------------------------------------------
        # URL
        # -------------------------------------------------

        if not valid_campaign_url(
            url
        ):
            record_errors.append(
                (
                    "Geçersiz kaynak_url: "
                    f"{url!r}"
                )
            )

        if is_commercial_url(
            url
        ):
            record_errors.append(
                (
                    "Ticari URL aktif bireysel "
                    f"RAW'a sızmış: {url}"
                )
            )

        final_url = normalize_text(
            record.get(
                "final_url",
                "",
            )
        )

        if not valid_campaign_url(
            final_url
        ):
            record_errors.append(
                (
                    "Geçersiz final_url: "
                    f"{final_url!r}"
                )
            )

        # -------------------------------------------------
        # HTTP
        # -------------------------------------------------

        if record.get(
            "http_status"
        ) != 200:
            record_errors.append(
                (
                    "HTTP status 200 değil: "
                    f"{record.get('http_status')!r}"
                )
            )

        # -------------------------------------------------
        # LISTING
        # -------------------------------------------------

        listing_text = normalize_text(
            record.get(
                "listing_text",
                "",
            )
        )

        if not listing_text:
            record_warnings.append(
                "listing_text boş."
            )

        # -------------------------------------------------
        # RAW TEXT
        # -------------------------------------------------

        if not raw_text:
            record_errors.append(
                "ham_metin boş."
            )

        elif len(
            raw_text
        ) < 250:
            record_errors.append(
                (
                    "ham_metin çok kısa: "
                    f"{len(raw_text)} karakter"
                )
            )

        # -------------------------------------------------
        # TITLE EXISTS IN RAW
        # -------------------------------------------------

        if (
            title
            and normalize_match(
                title
            )
            not in normalize_match(
                raw_text
            )
        ):
            record_errors.append(
                (
                    "kampanya_adi ham_metin "
                    "içinde bulunamadı."
                )
            )

        # -------------------------------------------------
        # CATEGORY EXISTS IN SOURCE
        # -------------------------------------------------

        if (
            category
            and normalize_match(
                category
            )
            not in normalize_match(
                raw_text
            )
            and normalize_match(
                category
            )
            not in normalize_match(
                listing_text
            )
        ):
            record_errors.append(
                (
                    "liste_kategorisi kaynak "
                    "metinlerde doğrulanamadı."
                )
            )

        # -------------------------------------------------
        # EXPIRED MARKERS
        # -------------------------------------------------

        raw_norm = normalize_match(
            raw_text
        )

        for marker in EXPIRED_MARKERS:
            if (
                normalize_match(
                    marker
                )
                in raw_norm
            ):
                record_errors.append(
                    (
                        "Aktif RAW kaydında sona erme "
                        f"ifadesi bulundu: {marker}"
                    )
                )
                break

        # -------------------------------------------------
        # COOKIE / FOOTER NOISE
        # -------------------------------------------------

        for marker in NOISE_MARKERS:
            if (
                normalize_match(
                    marker
                )
                in raw_norm
            ):
                record_errors.append(
                    (
                        "ham_metin içinde sayfa "
                        f"gürültüsü bulundu: {marker}"
                    )
                )
                break

        # -------------------------------------------------
        # SOURCE-INTERNAL DATE CONTRADICTION
        # -------------------------------------------------

        internal_expiry_dates = (
            find_internal_expiry_dates(
                raw_text
            )
        )

        if scrape_date is not None:
            for (
                raw_date,
                parsed_date,
            ) in internal_expiry_dates:

                if parsed_date < scrape_date:
                    record_warnings.append(
                        (
                            "Kaynak içi tarih çelişkisi: "
                            f"ham_metin '{raw_date}' "
                            "tarihine kadar geçerli diyor; "
                            "ancak listing aktif ve "
                            f"bitiş={list_end_date!r}. "
                            "Extractor kampanya süresi için "
                            "listing metadata'sını "
                            "önceliklendirmeli."
                        )
                    )

        # -------------------------------------------------
        # RECORD RESULT
        # -------------------------------------------------

        if record_errors:
            print(
                "VALIDATION: ❌"
            )

            for error in record_errors:
                print(
                    "  ERROR:",
                    error,
                )

                errors.append(
                    (
                        f"{title or url or index} "
                        f"-> {error}"
                    )
                )

        else:
            print(
                "VALIDATION: ✅"
            )

        if record_warnings:
            for warning in record_warnings:
                print(
                    "  WARNING:",
                    warning,
                )

                warnings.append(
                    (
                        f"{title or url or index} "
                        f"-> {warning}"
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
        "CAMPAIGN RAW VALIDATION SONUCU"
    )

    print(
        "=" * 118
    )

    print(
        "Beklenen:",
        EXPECTED_COUNT,
    )

    print(
        "Gerçek:",
        actual_count,
    )

    print(
        "Duplicate URL:",
        len(
            duplicate_urls
        ),
    )

    print(
        "Duplicate başlık:",
        len(
            duplicate_titles
        ),
    )

    print(
        "Warning:",
        len(
            warnings
        ),
    )

    print(
        "Error:",
        len(
            errors
        ),
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
                "CAMPAIGN RAW VALIDATION "
                "BAŞARILI ✅"
            )
        )

        if warnings:
            print(
                (
                    "NOT: Warning'ler kaynak içi "
                    "tutarsızlık olabilir; RAW kaydı "
                    "bozmaz ancak extractor aşamasında "
                    "dikkate alınmalıdır. ⚠️"
                )
            )

    else:
        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "CAMPAIGN RAW VALIDATION "
                "BAŞARISIZ ❌"
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