import json
import re
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


# =========================================================
# CONFIG
# =========================================================

BANK_NAME = "Dünya Katılım Bankası A.Ş."
LIST_URL = "https://dunyakatilim.com.tr/kampanyalar"

ROOT = Path(__file__).resolve().parents[2]

DISCOVERY_FILE = (
    ROOT
    / "data"
    / "raw"
    / "dunya_katilim_campaign_discovery.json"
)

OUTPUT_FILE = (
    ROOT
    / "data"
    / "raw"
    / "dunya_katilim_kampanyalar.json"
)

EXPECTED_ACTIVE_COUNT = 43
HEADLESS = True


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
# DISCOVERY LOAD
# =========================================================

def load_discovery():
    if not DISCOVERY_FILE.exists():
        print(
            f"Discovery dosyası bulunamadı: "
            f"{DISCOVERY_FILE}"
        )
        sys.exit(1)

    try:
        with DISCOVERY_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except json.JSONDecodeError as error:
        print(
            "Discovery JSON parse hatası:"
        )
        print(error)
        sys.exit(1)

    if not isinstance(
        data,
        dict,
    ):
        print(
            "Discovery JSON root object/dict değil."
        )
        sys.exit(1)

    campaigns = data.get(
        "aktif_kampanyalar"
    )

    if not isinstance(
        campaigns,
        list,
    ):
        print(
            "'aktif_kampanyalar' list değil."
        )
        sys.exit(1)

    declared_count = data.get(
        "aktif_kampanya_sayisi"
    )

    if declared_count != len(
        campaigns
    ):
        print(
            (
                "Discovery sayım uyuşmazlığı: "
                f"aktif_kampanya_sayisi="
                f"{declared_count}, "
                f"liste={len(campaigns)}"
            )
        )
        sys.exit(1)

    if len(
        campaigns
    ) != EXPECTED_ACTIVE_COUNT:
        print(
            (
                "Beklenen aktif kampanya "
                "sayısı değişmiş: "
                f"beklenen={EXPECTED_ACTIVE_COUNT}, "
                f"discovery={len(campaigns)}"
            )
        )
        sys.exit(1)

    return (
        data,
        campaigns,
    )


# =========================================================
# COOKIE
# =========================================================

def dismiss_cookie_banner(page):
    candidates = [
        "Tümünü Kabul Et",
        "Tüm Çerezleri Kabul Et",
        "Kabul Et",
        "Onayla",
        "Reddet",
        "Sadece Zorunlu Çerezler",
    ]

    for text in candidates:
        locator = page.get_by_text(
            text,
            exact=True,
        )

        try:
            count = locator.count()

        except Exception:
            continue

        for index in range(count):
            item = locator.nth(
                index
            )

            try:
                if item.is_visible():
                    item.click(
                        timeout=1500
                    )

                    page.wait_for_timeout(
                        350
                    )

                    return True

            except Exception:
                continue

    return False


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_lines(text):
    lines = []
    previous = None

    for raw_line in str(
        text or ""
    ).splitlines():
        line = normalize_text(
            raw_line
        )

        if not line:
            continue

        if line == previous:
            continue

        lines.append(
            line
        )

        previous = line

    return lines


def trim_campaign_body(
    body_text,
    title,
):
    lines = clean_lines(
        body_text
    )

    if not lines:
        return ""

    title_norm = normalize_match(
        title
    )

    start_index = None

    for index, line in enumerate(
        lines
    ):
        line_norm = normalize_match(
            line
        )

        if not title_norm:
            break

        if line_norm == title_norm:
            start_index = index
            break

        if (
            len(title_norm) >= 12
            and title_norm in line_norm
        ):
            start_index = index
            break

        if (
            len(line_norm) >= 12
            and line_norm in title_norm
        ):
            start_index = index
            break

    if start_index is None:
        start_index = 0

    stop_markers = [
        "Diğer Kampanyalar",
        "Diger Kampanyalar",
        "Size Özel Diğer Kampanyalar",
        "Sizin İçin Seçtiklerimiz",
        "Zorunlu Çerezler",
        "Çerez Aydınlatma Metni",
        (
            "Çerez Kullanımına İlişkin "
            "Aydınlatma Metni"
        ),
        (
            "Tüm site ziyaretçilerimizi "
            "daha iyi tanımak"
        ),
    ]

    kept = []

    for line in lines[
        start_index:
    ]:
        line_norm = normalize_match(
            line
        )

        should_stop = any(
            normalize_match(
                marker
            ) in line_norm
            for marker in stop_markers
        )

        if (
            should_stop
            and kept
        ):
            break

        kept.append(
            line
        )

    return "\n".join(
        kept
    ).strip()


def extract_page_text(
    page,
    title,
):
    try:
        body_text = page.locator(
            "body"
        ).inner_text(
            timeout=6000
        )

    except Exception:
        return ""

    return trim_campaign_body(
        body_text,
        title,
    )


# =========================================================
# SAFETY
# =========================================================

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


def contains_expired_marker(text):
    normalized = normalize_match(
        text
    )

    markers = [
        "kampanya süresi dolmuştur",
        "kampanya suresi dolmustur",
        "kampanya sona erdi",
        "kampanya sona ermiştir",
        "sona erdi",
        "süresi doldu",
        "süresi dolmuştur",
    ]

    return any(
        normalize_match(
            marker
        ) in normalized
        for marker in markers
    )


# =========================================================
# SINGLE CAMPAIGN
# =========================================================

def scrape_campaign(
    page,
    discovery_record,
):
    url = discovery_record.get(
        "kaynak_url",
        "",
    )

    if not url:
        raise ValueError(
            "Discovery kaydında kaynak_url boş."
        )

    if is_commercial_url(
        url
    ):
        raise ValueError(
            (
                "Aktif bireysel discovery "
                "listesine ticari URL sızmış: "
                f"{url}"
            )
        )

    response = page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=45000,
    )

    page.wait_for_timeout(
        700
    )

    # İlk sayfada cookie çıkarsa kapat.
    dismiss_cookie_banner(
        page
    )

    status = (
        response.status
        if response
        else None
    )

    try:
        title = normalize_text(
            page.locator(
                "h1"
            ).first.inner_text(
                timeout=3500
            )
        )

    except Exception:
        title = ""

    raw_text = extract_page_text(
        page,
        title,
    )

    if not title:
        raise ValueError(
            "H1 başlık bulunamadı."
        )

    if not raw_text:
        raise ValueError(
            "ham_metin boş."
        )

    if len(
        raw_text
    ) < 80:
        raise ValueError(
            (
                "ham_metin şüpheli "
                "derecede kısa: "
                f"{len(raw_text)} karakter"
            )
        )

    if contains_expired_marker(
        raw_text
    ):
        raise ValueError(
            (
                "Aktif discovery kaydının "
                "detayında sona erme "
                "ifadesi bulundu."
            )
        )

    return {
        "kampanya_adi": title,
        "liste_kategorisi": normalize_text(
            discovery_record.get(
                "kategori",
                "",
            )
        ),
        "liste_durumu": normalize_text(
            discovery_record.get(
                "durum",
                "",
            )
        ),
        "liste_bitis_tarihi": normalize_text(
            discovery_record.get(
                "bitis_tarihi",
                "",
            )
        ),
        "kaynak_url": url,
        "final_url": page.url,
        "http_status": status,
        "listing_text": normalize_text(
            discovery_record.get(
                "listing_text",
                "",
            )
        ),
        "ham_metin": raw_text,
    }


# =========================================================
# DUPLICATE
# =========================================================

def find_duplicates(
    records,
    field,
):
    seen = set()
    duplicates = []

    for record in records:
        value = normalize_match(
            record.get(
                field,
                "",
            )
        )

        if not value:
            continue

        if value in seen:
            duplicates.append(
                record.get(
                    field,
                    "",
                )
            )

        else:
            seen.add(
                value
            )

    return duplicates


# =========================================================
# MAIN
# =========================================================

def main():
    print()
    print(
        "=" * 118
    )
    print(
        "DÜNYA KATILIM - CAMPAIGN SCRAPER V1"
    )
    print(
        "=" * 118
    )

    print(
        "Discovery:",
        DISCOVERY_FILE,
    )

    print(
        "Output:",
        OUTPUT_FILE,
    )

    print()

    discovery_data, campaign_targets = (
        load_discovery()
    )

    print(
        "Discovery aktif kampanya:",
        len(
            campaign_targets
        ),
    )

    print(
        "Discovery sonucu:",
        "TEMİZ ✅",
    )

    records = []
    errors = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=HEADLESS
        )

        try:
            context = browser.new_context(
                locale="tr-TR",
                viewport={
                    "width": 1440,
                    "height": 1000,
                },
            )

            page = context.new_page()

            for index, target in enumerate(
                campaign_targets,
                start=1,
            ):
                url = target.get(
                    "kaynak_url",
                    "",
                )

                print()
                print(
                    "-" * 118
                )

                print(
                    (
                        f"[{index}/"
                        f"{len(campaign_targets)}] "
                        f"{url}"
                    )
                )

                try:
                    record = scrape_campaign(
                        page,
                        target,
                    )

                    records.append(
                        record
                    )

                    print(
                        "Başlık:",
                        record[
                            "kampanya_adi"
                        ],
                    )

                    print(
                        "Kategori:",
                        (
                            record[
                                "liste_kategorisi"
                            ]
                            or "YOK"
                        ),
                    )

                    print(
                        "Bitiş:",
                        (
                            record[
                                "liste_bitis_tarihi"
                            ]
                            or "YOK"
                        ),
                    )

                    print(
                        "HTTP:",
                        record[
                            "http_status"
                        ],
                    )

                    print(
                        "Ham metin:",
                        len(
                            record[
                                "ham_metin"
                            ]
                        ),
                        "karakter",
                    )

                    if (
                        record[
                            "http_status"
                        ]
                        != 200
                    ):
                        errors.append(
                            (
                                f"{url} -> HTTP "
                                f"{record['http_status']}"
                            )
                        )

                        print(
                            "SCRAPE: ❌"
                        )

                    else:
                        print(
                            "SCRAPE: ✅"
                        )

                except Exception as error:
                    errors.append(
                        (
                            f"{url} -> "
                            f"{type(error).__name__}: "
                            f"{error}"
                        )
                    )

                    print(
                        "SCRAPE: ❌",
                        error,
                    )

        finally:
            browser.close()

    # =====================================================
    # DUPLICATE CHECK
    # =====================================================

    duplicate_urls = find_duplicates(
        records,
        "kaynak_url",
    )

    duplicate_titles = find_duplicates(
        records,
        "kampanya_adi",
    )

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
                "Duplicate kampanya başlığı "
                "bulundu: "
                f"{duplicate_titles}"
            )
        )

    # =====================================================
    # COUNT CHECK
    # =====================================================

    if len(
        records
    ) != EXPECTED_ACTIVE_COUNT:
        errors.append(
            (
                "Kayıt sayısı uyuşmuyor: "
                f"beklenen={EXPECTED_ACTIVE_COUNT}, "
                f"scrape={len(records)}"
            )
        )

    # =====================================================
    # SAVE
    # =====================================================

    output = {
        "banka": BANK_NAME,
        "liste_url": LIST_URL,
        "scrape_zamani": (
            datetime.now().isoformat(
                timespec="seconds"
            )
        ),
        "discovery_dosyasi": str(
            DISCOVERY_FILE
        ),
        "discovery_zamani": (
            discovery_data.get(
                "discovery_zamani",
                "",
            )
        ),
        "beklenen_aktif_kampanya_sayisi": (
            EXPECTED_ACTIVE_COUNT
        ),
        "kampanya_sayisi": len(
            records
        ),
        "kampanyalar": records,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=4,
        )

    # =====================================================
    # REPORT
    # =====================================================

    print()
    print(
        "=" * 118
    )

    print(
        "CAMPAIGN SCRAPER V1 SONUCU"
    )

    print(
        "=" * 118
    )

    print(
        "Beklenen:",
        EXPECTED_ACTIVE_COUNT,
    )

    print(
        "Scrape edilen:",
        len(
            records
        ),
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
        "Error:",
        len(
            errors
        ),
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
                "CAMPAIGN RAW SCRAPE "
                "BAŞARILI ✅"
            )
        )

    else:
        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "CAMPAIGN RAW SCRAPE "
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

    if errors:
        sys.exit(
            1
        )


if __name__ == "__main__":
    main()