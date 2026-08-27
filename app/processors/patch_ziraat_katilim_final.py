import json
import re
import time
from collections import Counter
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ==================================================================================================
# ZİRAAT KATILIM - FINAL PATCH
# ==================================================================================================
#
# INPUT:
#   data/processed/ziraat_katilim_final.json
#   veya
#   data/processed/ziraat_katilim_final(1).json
#
# OUTPUT:
#   data/processed/ziraat_katilim_all.json
#
# Yaptıkları:
#   1) Exact 18-key schema'yı korur.
#   2) Kampanya kosullar alanındaki UI / sayfa navigasyon çöplerini temizler.
#   3) "Daha Fazla Göster" vb. noise'ları temizler.
#   4) [RESMİ KAYNAK ÖZETİ] bulunan 6 finansman ürününün
#      gerçek resmi sayfasını indirip ham_metin'i gerçek kaynak metinle değiştirir.
#   5) Summary marker'ın kosullar'a sızdığı yerleri temizler.
#   6) Duplicate URL / schema / tip / banka adı / summary marker / UI noise audit yapar.
#
# ==================================================================================================


BANK_NAME = "Ziraat Katılım Bankası A.Ş."


FINAL_KEYS = [
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


STRING_FIELDS = set(FINAL_KEYS) - LIST_FIELDS


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


INPUT_CANDIDATES = [
    PROCESSED_DIR / "ziraat_katilim_final.json",
    PROCESSED_DIR / "ziraat_katilim_final(1).json",
]


OUTPUT_FILE = (
    PROCESSED_DIR
    / "ziraat_katilim_all.json"
)


# ==================================================================================================
# GERÇEK HAM METİNİ TEKRAR ÇEKİLECEK 6 ÜRÜN
# ==================================================================================================

RAW_REFETCH_PRODUCTS = {
    "Kolay Fon Finansmanı",
    "Anında Finansman",
    "Yeşil Ev Konut Finansmanı",
    "Yeşil Taşıt Finansmanı",
    "Bireysel Enerji Verimliliği Finansmanı",
    "Enerji Verimliliği Yönetim Finansmanı",
}


# ==================================================================================================
# KAMPANYA UI NOISE
# ==================================================================================================

UI_NOISE_EXACT = {
    "geri",
    "kampanyaya katıl",
    "hemen katıl",
    "kartı keşfet",
    "katılım bankkart",
    "kart başvurusu yap",
    "sponsorlu",
    "kalan süre",
    "kazanç",
    "etiketler",
}


# Sitedeki standalone kategori/etiket satırları.
# Bunlar koşul değildir.
TAG_NOISE = {
    "market & gıda",
    "giyim & aksesuar",
    "e-ticaret",
    "elektronik",
    "mobilya & dekorasyon",
    "mücevherat, optik & saat",
    "kozmetik & sağlık",
    "turizm & konaklama",
    "akaryakıt",
    "restoran",
    "eğitim",
    "market",
    "gıda",
    "sağlık",
    "diğer",
    "otomotiv",
    "seyahat",
    "ev & yaşam",
}


SUMMARY_MARKER = "[RESMİ KAYNAK ÖZETİ]"


# ==================================================================================================
# HTTP
# ==================================================================================================

SESSION = requests.Session()

SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
    }
)


# ==================================================================================================
# HELPERS
# ==================================================================================================

def normalize_space(value):
    if not isinstance(value, str):
        return ""

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def normalize_compare(value):
    value = normalize_space(value)

    return (
        value.casefold()
        .replace("ı", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
    )


def unique_list(values):
    if not isinstance(values, list):
        return []

    result = []
    seen = set()

    for value in values:

        if not isinstance(value, str):
            continue

        value = normalize_space(value)

        if not value:
            continue

        key = value.casefold()

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


def find_input_file():
    for candidate in INPUT_CANDIDATES:

        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "\nZiraat input dosyası bulunamadı.\n\n"
        "Şunlardan birini data/processed içine koy:\n"
        "  ziraat_katilim_final.json\n"
        "  ziraat_katilim_final(1).json\n"
    )


# ==================================================================================================
# UI NOISE DETECTION
# ==================================================================================================

def is_ui_noise(value, record=None):
    text = normalize_space(value)

    if not text:
        return True

    lower = text.casefold()

    # Exact site UI
    if lower in UI_NOISE_EXACT:
        return True

    # Category/tag
    if lower in TAG_NOISE:
        return True

    # Daha Fazla Göster (...)
    if lower.startswith("daha fazla göster"):
        return True

    # "(1 koşul daha)" vb.
    if re.fullmatch(
        r"\(?\s*\d*\s*koşul\s+daha\s*\)?",
        lower,
    ):
        return True

    # "8 Gün Kaldı", "130 Gün Kaldı"
    if re.fullmatch(
        r"\d+\s+gün\s+kaldı",
        lower,
    ):
        return True

    # Site kısa tarih etiketleri: 10 Tem / 31 Ağu / 7 Eyl vb.
    if re.fullmatch(
        r"\d{1,2}\s+"
        r"(oca|şub|sub|mar|nis|may|haz|tem|ağu|agu|eyl|eki|kas|ara)",
        lower,
    ):
        return True

    # Avantaj zaten kampanya_avantaji alanında tutuluyorsa
    # kosullar içerisinde aynı metni ikinci kez tutmaya gerek yok.
    if record:

        advantages = {
            normalize_space(x).casefold()
            for x in record.get(
                "kampanya_avantaji",
                [],
            )
            if isinstance(x, str)
        }

        if lower in advantages:
            return True

    return False


def clean_conditions(record):
    conditions = record.get(
        "kosullar",
        [],
    )

    if not isinstance(conditions, list):
        return []

    cleaned = []

    for item in conditions:

        if not isinstance(item, str):
            continue

        item = normalize_space(item)

        if not item:
            continue

        # Sonradan oluşturulmuş summary satırı final kosullar'a girmesin.
        if SUMMARY_MARKER.casefold() in item.casefold():
            continue

        if is_ui_noise(
            item,
            record,
        ):
            continue

        cleaned.append(item)

    return unique_list(cleaned)


# ==================================================================================================
# OFFICIAL PAGE EXTRACTION
# ==================================================================================================

FOOTER_MARKERS = {
    "ziraat finans grubu",
    "yatırımcı ilişkileri",
    "yatirimci iliskileri",
    "bize ulaşın",
    "bize ulasin",
    "© 2025 ziraat katılım bankası a.ş.",
    "© 2025 ziraat katilim bankasi a.s.",
    "finansman türü",
    "finansman turu",
}


DROP_PAGE_LINES = {
    "müşteri ol",
    "musteri ol",
    "internet şubesi",
    "internet subesi",
    "hemen başvur",
    "hemen basvur",
    "geri",
}


def fetch_page(url, retry_count=3):
    last_error = None

    for attempt in range(
        1,
        retry_count + 1,
    ):

        try:
            response = SESSION.get(
                url,
                timeout=30,
                allow_redirects=True,
            )

            response.raise_for_status()

            if not response.text:
                raise ValueError(
                    "Boş HTML döndü."
                )

            return response.text

        except Exception as exc:
            last_error = exc

            if attempt < retry_count:
                print(
                    f"      HTTP tekrar deneniyor "
                    f"({attempt}/{retry_count})..."
                )

                time.sleep(
                    2 * attempt
                )

    raise RuntimeError(
        f"Sayfa alınamadı: {url}\n"
        f"Hata: {last_error}"
    )


def extract_product_section(
    html,
    product_name,
):
    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    # HTML element noise
    for element in soup.find_all(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "iframe",
            "form",
        ]
    ):
        element.decompose()

    raw_lines = []

    for value in soup.stripped_strings:

        value = normalize_space(
            value
        )

        if not value:
            continue

        raw_lines.append(
            value
        )

    if not raw_lines:
        raise ValueError(
            f"{product_name}: HTML text boş."
        )

    normalized_title = normalize_compare(
        product_name
    )

    start_index = None

    # Öncelikle tam başlığı bul
    for index, line in enumerate(
        raw_lines
    ):

        normalized_line = normalize_compare(
            line
        )

        if normalized_line == normalized_title:
            start_index = index
            break

    # Tam eşleşme yoksa title satırını içeren satırı bul
    if start_index is None:

        for index, line in enumerate(
            raw_lines
        ):

            normalized_line = normalize_compare(
                line
            )

            if (
                normalized_title
                in normalized_line
            ):
                start_index = index
                break

    if start_index is None:
        raise ValueError(
            f"{product_name}: "
            "ürün başlığı resmi HTML içinde bulunamadı."
        )

    selected = []

    for line in raw_lines[
        start_index:
    ]:

        normalized_line = normalize_compare(
            line
        )

        # İlk title satırından sonra footer başladığında kes.
        if (
            selected
            and normalized_line
            in {
                normalize_compare(x)
                for x in FOOTER_MARKERS
            }
        ):
            break

        # Footer marker'ın başlangıç varyasyonları
        if (
            selected
            and (
                normalized_line.startswith(
                    "ziraat finans grubu"
                )
                or normalized_line.startswith(
                    "yatirimci iliskileri"
                )
                or normalized_line.startswith(
                    "finansman turu"
                )
            )
        ):
            break

        if normalized_line in {
            normalize_compare(x)
            for x in DROP_PAGE_LINES
        }:
            continue

        selected.append(
            line
        )

    # Arka arkaya aynı satırları tekilleştir.
    compact = []

    previous = None

    for line in selected:

        if line == previous:
            continue

        compact.append(line)
        previous = line

    text = "\n".join(
        compact
    ).strip()

    if len(text) < 100:
        raise ValueError(
            f"{product_name}: "
            f"çekilen gerçek ürün metni çok kısa ({len(text)} karakter)."
        )

    if SUMMARY_MARKER.casefold() in text.casefold():
        raise ValueError(
            f"{product_name}: "
            "çekilen metinde summary marker bulundu."
        )

    # Ürün adındaki anlamlı sözcüklerden en az biri metinde bulunmalı.
    important_words = [
        word
        for word in re.findall(
            r"[A-Za-zÇĞİÖŞÜçğıöşü]+",
            product_name,
        )
        if len(word) >= 5
    ]

    normalized_text = normalize_compare(
        text
    )

    if important_words:

        if not any(
            normalize_compare(word)
            in normalized_text
            for word in important_words
        ):
            raise ValueError(
                f"{product_name}: "
                "çekilen içerik ürünle eşleşmiyor."
            )

    return text


def refetch_real_raw_text(
    record,
):
    name = record.get(
        "urun_adi",
        "",
    )

    url = record.get(
        "kaynak_url",
        "",
    ).strip()

    if not url:
        raise ValueError(
            f"{name}: kaynak_url boş."
        )

    print(
        f"      GET: {url}"
    )

    html = fetch_page(
        url
    )

    real_text = extract_product_section(
        html,
        name,
    )

    return real_text


# ==================================================================================================
# RECORD PATCH
# ==================================================================================================

def patch_record(
    record,
    refetched,
):
    r = dict(record)

    r["banka"] = BANK_NAME

    # Kampanya kosullar UI cleanup
    if r.get(
        "kayit_turu"
    ) == "kampanya":

        r["kosullar"] = clean_conditions(
            r
        )

    # Finansman kosullar içerisinde summary marker varsa kaldır.
    if r.get(
        "kayit_turu"
    ) == "finansman":

        r["kosullar"] = clean_conditions(
            r
        )

    name = normalize_space(
        r.get(
            "urun_adi",
            "",
        )
    )

    # 6 sentetik ham_metin kaydını gerçek resmi sayfa içeriğiyle değiştir.
    if name in RAW_REFETCH_PRODUCTS:

        current_raw = r.get(
            "ham_metin",
            "",
        )

        if (
            SUMMARY_MARKER.casefold()
            in current_raw.casefold()
        ):

            real_raw = refetch_real_raw_text(
                r
            )

            r["ham_metin"] = real_raw

            refetched.append(
                name
            )

    # ----------------------------------------------------------------------------------------------
    # TYPE NORMALIZATION
    # ----------------------------------------------------------------------------------------------

    for field in LIST_FIELDS:

        value = r.get(
            field,
            [],
        )

        if not isinstance(
            value,
            list,
        ):
            value = []

        r[field] = unique_list(
            value
        )

    for field in STRING_FIELDS:

        value = r.get(
            field,
            "",
        )

        if value is None:
            value = ""

        if not isinstance(
            value,
            str,
        ):
            value = str(value)

        if field == "ham_metin":

            # ham_metin'de newline'ları koruyoruz.
            value = value.strip()

        else:

            value = normalize_space(
                value
            )

        r[field] = value

    # Exact 18-key schema ve sıra
    return {
        key: (
            r.get(
                key,
                [],
            )
            if key in LIST_FIELDS
            else r.get(
                key,
                "",
            )
        )
        for key in FINAL_KEYS
    }


# ==================================================================================================
# AUDIT HELPERS
# ==================================================================================================

def count_ui_noise(records):
    count = 0

    examples = []

    for record in records:

        for condition in record.get(
            "kosullar",
            [],
        ):

            if is_ui_noise(
                condition,
                record,
            ):

                count += 1

                if len(
                    examples
                ) < 10:

                    examples.append(
                        (
                            record.get(
                                "urun_adi",
                                "",
                            ),
                            condition,
                        )
                    )

    return (
        count,
        examples,
    )


def count_summary_markers(records):
    count = 0

    examples = []

    for record in records:

        for field in FINAL_KEYS:

            value = record.get(
                field
            )

            if isinstance(
                value,
                str,
            ):

                values = [
                    value
                ]

            elif isinstance(
                value,
                list,
            ):

                values = [
                    x
                    for x in value
                    if isinstance(
                        x,
                        str,
                    )
                ]

            else:

                values = []

            for item in values:

                if (
                    SUMMARY_MARKER.casefold()
                    in item.casefold()
                ):

                    count += 1

                    if len(
                        examples
                    ) < 10:

                        examples.append(
                            (
                                record.get(
                                    "urun_adi",
                                    "",
                                ),
                                field,
                                item[:150],
                            )
                        )

    return (
        count,
        examples,
    )


# ==================================================================================================
# VALIDATION
# ==================================================================================================

def validate_records(
    records,
    refetched,
):
    errors = []

    urls = []

    for index, record in enumerate(
        records,
        start=1,
    ):

        name = record.get(
            "urun_adi",
            "",
        )

        prefix = (
            f"[{index:03d}] {name}"
        )

        # Exact schema/order
        if list(
            record.keys()
        ) != FINAL_KEYS:

            errors.append(
                f"{prefix} -> "
                "18-key schema/order yanlış"
            )

        # Banka
        if record.get(
            "banka"
        ) != BANK_NAME:

            errors.append(
                f"{prefix} -> banka adı yanlış"
            )

        # Type
        if record.get(
            "kayit_turu"
        ) not in {
            "finansman",
            "kampanya",
        }:

            errors.append(
                f"{prefix} -> kayit_turu yanlış"
            )

        # Lists
        for field in LIST_FIELDS:

            if not isinstance(
                record.get(field),
                list,
            ):

                errors.append(
                    f"{prefix} -> "
                    f"{field} list değil"
                )

        # Strings
        for field in STRING_FIELDS:

            if not isinstance(
                record.get(field),
                str,
            ):

                errors.append(
                    f"{prefix} -> "
                    f"{field} string değil"
                )

        # Currency standard
        if "TRY" in record.get(
            "para_birimi",
            [],
        ):

            errors.append(
                f"{prefix} -> TRY bulundu"
            )

        url = record.get(
            "kaynak_url",
            "",
        ).strip()

        if url:
            urls.append(url)

    # Duplicate URL
    for url, count in Counter(
        urls
    ).items():

        if count > 1:

            errors.append(
                f"Duplicate URL ({count}): {url}"
            )

    # Summary marker zero olmalı
    summary_count, summary_examples = (
        count_summary_markers(
            records
        )
    )

    if summary_count:

        errors.append(
            f"[RESMİ KAYNAK ÖZETİ] "
            f"hala {summary_count} yerde mevcut."
        )

        for example in summary_examples:

            errors.append(
                "SUMMARY -> "
                + " | ".join(
                    str(x)
                    for x in example
                )
            )

    # UI noise zero olmalı
    ui_count, ui_examples = (
        count_ui_noise(
            records
        )
    )

    if ui_count:

        errors.append(
            f"kosullar alanında "
            f"{ui_count} UI noise kaldı."
        )

        for name, value in ui_examples:

            errors.append(
                f"UI NOISE -> "
                f"{name} | {value}"
            )

    # 6 resmi kaynak metni gerçekten yenilenmiş olmalı.
    missing_refetch = (
        RAW_REFETCH_PRODUCTS
        - set(refetched)
    )

    # Eğer inputta marker zaten temizlenmişse refetch listesine girmemiş olabilir.
    # Bu durumda final ham_metin'i kontrol et.
    by_name = {
        r["urun_adi"]: r
        for r in records
    }

    for name in list(
        missing_refetch
    ):

        record = by_name.get(
            name
        )

        if (
            record
            and record.get(
                "ham_metin",
                ""
            )
            and SUMMARY_MARKER.casefold()
            not in record.get(
                "ham_metin",
                "",
            ).casefold()
        ):

            missing_refetch.remove(
                name
            )

    if missing_refetch:

        errors.append(
            "Gerçek raw metni doğrulanamayan ürünler: "
            + ", ".join(
                sorted(
                    missing_refetch
                )
            )
        )

    # Şu dosyaya özel beklenen sayılar
    finance_count = sum(
        1
        for r in records
        if r["kayit_turu"]
        == "finansman"
    )

    campaign_count = sum(
        1
        for r in records
        if r["kayit_turu"]
        == "kampanya"
    )

    if len(records) != 107:

        errors.append(
            f"Toplam kayıt 107 bekleniyordu, "
            f"{len(records)} bulundu."
        )

    if finance_count != 20:

        errors.append(
            f"Finansman 20 bekleniyordu, "
            f"{finance_count} bulundu."
        )

    if campaign_count != 87:

        errors.append(
            f"Kampanya 87 bekleniyordu, "
            f"{campaign_count} bulundu."
        )

    return errors


# ==================================================================================================
# AUDIT
# ==================================================================================================

def print_audit(
    records,
    refetched,
):
    finance = [
        r
        for r in records
        if r["kayit_turu"]
        == "finansman"
    ]

    campaigns = [
        r
        for r in records
        if r["kayit_turu"]
        == "kampanya"
    ]

    exact_schema = sum(
        1
        for r in records
        if list(
            r.keys()
        ) == FINAL_KEYS
    )

    duplicate_urls = [
        url
        for url, count in Counter(
            r["kaynak_url"]
            for r in records
            if r["kaynak_url"]
        ).items()
        if count > 1
    ]

    ui_count, _ = (
        count_ui_noise(
            records
        )
    )

    summary_count, _ = (
        count_summary_markers(
            records
        )
    )

    print()
    print("=" * 120)
    print("ZİRAAT KATILIM - FINAL PATCH AUDIT")
    print("=" * 120)

    print(
        f"Toplam kayıt         : "
        f"{len(records)}"
    )

    print(
        f"Finansman            : "
        f"{len(finance)}"
    )

    print(
        f"Kampanya             : "
        f"{len(campaigns)}"
    )

    print(
        f"Exact 18-key schema  : "
        f"{exact_schema}/{len(records)}"
    )

    print(
        f"Duplicate URL        : "
        f"{len(duplicate_urls)}"
    )

    print(
        f"UI noise             : "
        f"{ui_count}"
    )

    print(
        f"Summary marker       : "
        f"{summary_count}"
    )

    print(
        f"Gerçek raw yenilendi : "
        f"{len(refetched)}/6"
    )

    print()
    print("GERÇEK RESMİ HAM METİNİ YENİLENEN ÜRÜNLER")
    print("-" * 120)

    if refetched:

        for name in refetched:
            print(
                f"✅ {name}"
            )

    else:

        print(
            "Yenilenen kayıt yok."
        )

    print("=" * 120)


# ==================================================================================================
# MAIN
# ==================================================================================================

def main():

    print()
    print("=" * 120)
    print("ZİRAAT KATILIM - FINAL PATCH")
    print("=" * 120)

    input_file = find_input_file()

    print(
        f"Input : {input_file}"
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print()

    with open(
        input_file,
        "r",
        encoding="utf-8",
    ) as f:

        records = json.load(
            f
        )

    if not isinstance(
        records,
        list,
    ):

        raise ValueError(
            "JSON root list olmalı."
        )

    print(
        f"Input kayıt sayısı: "
        f"{len(records)}"
    )

    print()

    patched_records = []

    refetched = []

    for index, record in enumerate(
        records,
        start=1,
    ):

        name = normalize_space(
            record.get(
                "urun_adi",
                "",
            )
        )

        print(
            f"[{index:03d}/{len(records)}] "
            f"{name}"
        )

        if name in RAW_REFETCH_PRODUCTS:

            print(
                "      → Gerçek resmi ham metin kontrolü"
            )

        patched = patch_record(
            record,
            refetched,
        )

        patched_records.append(
            patched
        )

    print_audit(
        patched_records,
        refetched,
    )

    errors = validate_records(
        patched_records,
        refetched,
    )

    if errors:

        print()
        print("=" * 120)
        print("VALIDATION ERRORS")
        print("=" * 120)

        for error in errors:
            print(
                f"❌ {error}"
            )

        print()
        print(
            "SONUÇ: "
            "ZİRAAT KATILIM FINAL PATCH BAŞARISIZ ❌"
        )

        print(
            "ziraat_katilim_all.json YAZILMADI."
        )

        raise SystemExit(1)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            patched_records,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print("=" * 120)
    print(
        "ZİRAAT KATILIM FINAL PATCH BAŞARILI ✅"
    )
    print("=" * 120)

    print(
        f"JSON: {OUTPUT_FILE}"
    )

    print()

    print(
        "87 kampanyadaki UI noise temizlendi ✅"
    )

    print(
        "'Daha Fazla Göster' noise temizlendi ✅"
    )

    print(
        "Summary marker'lar kaldırıldı ✅"
    )

    print(
        "6 finansman ürününün gerçek resmi ham metni çekildi ✅"
    )

    print(
        "Exact 18-key schema korundu ✅"
    )

    print(
        "Duplicate URL kontrolü geçti ✅"
    )

    print("=" * 120)


if __name__ == "__main__":
    main()