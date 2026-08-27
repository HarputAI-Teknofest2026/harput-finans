import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


# =========================================================
# CONFIG
# =========================================================

BANK_NAME = "Dünya Katılım Bankası A.Ş."
LIST_URL = "https://dunyakatilim.com.tr/kampanyalar"

ROOT = Path(__file__).resolve().parents[2]

OUTPUT_FILE = (
    ROOT
    / "data"
    / "raw"
    / "dunya_katilim_campaign_discovery.json"
)

HEADLESS = True
MAX_MORE_CLICKS = 50


CAMPAIGN_CATEGORIES = [
    "Yeni Müşteri Kampanyaları",
    "Paraf Kampanyaları",
    "Finansman Kampanyaları",
    "Sigorta Kampanyaları",
    "Yatırım Kampanyaları",
    "Kart Kampanyaları",
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
# DATE
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


def detect_end_date(text):
    """
    Yalnızca gerçek tarih kısmını döndürür.

    Örnek:
        Bitiş Tarihi: 31 Ağustos 2026 Kampanya Detayları
    ->
        31 Ağustos 2026

    Ayrıca:
        Bitiş Tarihi: -
    ->
        -
    """

    text = normalize_text(
        text
    )

    # Önce açık uçlu "-" kontrolü.
    dash_match = re.search(
        r"Bitiş\s*Tarihi\s*:\s*-(?:\s|$)",
        text,
        flags=re.IGNORECASE,
    )

    if dash_match:
        return "-"

    # Tam tarih.
    date_match = re.search(
        (
            r"Bitiş\s*Tarihi\s*:\s*"
            r"(\d{1,2}\s+"
            r"[A-Za-zÇĞİÖŞÜçğıöşü]+\s+"
            r"\d{4})"
        ),
        text,
        flags=re.IGNORECASE,
    )

    if date_match:
        return normalize_text(
            date_match.group(1)
        )

    # Alternatif ifade:
    # "31 Ağustos 2026 tarihine kadar"
    until_match = re.search(
        (
            r"(\d{1,2}\s+"
            r"[A-Za-zÇĞİÖŞÜçğıöşü]+\s+"
            r"\d{4})"
            r"\s+tarihine\s+kadar"
        ),
        text,
        flags=re.IGNORECASE,
    )

    if until_match:
        return normalize_text(
            until_match.group(1)
        )

    return ""


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
                        400
                    )

                    return True

            except Exception:
                continue

    return False


# =========================================================
# KENDİM İÇİN
# =========================================================

def activate_individual_tab(page):
    locator = page.locator(
        "a, button, [role='button']"
    ).filter(
        has_text=re.compile(
            r"^\s*KENDİM İÇİN\s*$",
            re.IGNORECASE,
        )
    )

    candidates = []

    try:
        count = locator.count()

    except Exception:
        count = 0

    for index in range(count):
        item = locator.nth(
            index
        )

        try:
            if not item.is_visible():
                continue

            box = item.bounding_box()

            y = (
                box.get(
                    "y",
                    0,
                )
                if box
                else 0
            )

            candidates.append(
                (
                    index,
                    y,
                )
            )

        except Exception:
            continue

    if not candidates:
        return False

    candidates.sort(
        key=lambda item: item[1]
    )

    selected_index = candidates[
        -1
    ][0]

    try:
        target = locator.nth(
            selected_index
        )

        target.scroll_into_view_if_needed()

        target.click(
            timeout=3000
        )

        page.wait_for_timeout(
            1200
        )

        return True

    except Exception:
        return False


# =========================================================
# LISTING
# =========================================================

def collect_visible_campaign_links(page):
    return page.evaluate(
        """
        () => {

            function isVisible(element) {

                if (!element) {
                    return false;
                }

                const style =
                    window.getComputedStyle(element);

                if (
                    style.display === "none" ||
                    style.visibility === "hidden" ||
                    Number(style.opacity) === 0
                ) {
                    return false;
                }

                const rect =
                    element.getBoundingClientRect();

                if (
                    rect.width <= 0 ||
                    rect.height <= 0
                ) {
                    return false;
                }

                let parent =
                    element.parentElement;

                while (parent) {

                    const parentStyle =
                        window.getComputedStyle(parent);

                    if (
                        parentStyle.display === "none" ||
                        parentStyle.visibility === "hidden"
                    ) {
                        return false;
                    }

                    parent =
                        parent.parentElement;
                }

                return true;
            }


            function compactText(value) {

                return String(value || "")
                    .replace(/\\s+/g, " ")
                    .trim();
            }


            const output = [];
            const seen = new Set();

            const anchors =
                document.querySelectorAll("a[href]");

            for (const anchor of anchors) {

                if (!isVisible(anchor)) {
                    continue;
                }

                let url;

                try {

                    url = new URL(
                        anchor.href,
                        window.location.href
                    );

                } catch {

                    continue;
                }

                if (
                    url.hostname !==
                    "dunyakatilim.com.tr"
                ) {
                    continue;
                }

                const path =
                    url.pathname.replace(
                        /\\/+$/,
                        ""
                    );

                if (
                    !path.startsWith(
                        "/kampanyalar/"
                    )
                ) {
                    continue;
                }

                const parts =
                    path
                        .split("/")
                        .filter(Boolean);

                if (
                    parts.length !== 2
                ) {
                    continue;
                }

                const slug =
                    parts[1];

                if (!slug) {
                    continue;
                }

                const normalizedUrl =
                    `${url.origin}/kampanyalar/${slug}`;

                if (
                    seen.has(
                        normalizedUrl
                    )
                ) {
                    continue;
                }

                seen.add(
                    normalizedUrl
                );

                let listingText =
                    compactText(
                        anchor.innerText
                    );

                /*
                 * Link bazen yalnızca
                 * "Detaylı Bilgi" içeriyor.
                 *
                 * Böyle durumlarda kart parent'ına
                 * çıkarak title/category/status/date
                 * metnini almaya çalışıyoruz.
                 */
                if (
                    !listingText ||
                    listingText.toLowerCase() ===
                    "detaylı bilgi"
                ) {

                    let parent =
                        anchor.parentElement;

                    for (
                        let depth = 0;
                        depth < 7 && parent;
                        depth++
                    ) {

                        const candidate =
                            compactText(
                                parent.innerText
                            );

                        if (
                            candidate.length >= 10 &&
                            candidate.length <= 1200
                        ) {

                            if (
                                candidate.includes(
                                    "Kampanyaları"
                                ) ||
                                candidate.includes(
                                    "Bitiş Tarihi"
                                ) ||
                                candidate.includes(
                                    "Devam ediyor"
                                )
                            ) {

                                listingText =
                                    candidate;

                                break;
                            }
                        }

                        parent =
                            parent.parentElement;
                    }
                }

                output.push({
                    url: normalizedUrl,
                    listing_text: listingText
                });
            }

            return output;
        }
        """
    )


# =========================================================
# LOAD MORE
# =========================================================

def find_visible_more_button(page):
    locator = page.locator(
        "button, a, [role='button']"
    ).filter(
        has_text=re.compile(
            r"^\s*Daha Fazla\s*$",
            re.IGNORECASE,
        )
    )

    try:
        count = locator.count()

    except Exception:
        return None

    for index in range(count):
        item = locator.nth(
            index
        )

        try:
            if item.is_visible():
                return item

        except Exception:
            continue

    return None


def load_all_visible_campaigns(page):
    previous_count = -1
    stable_rounds = 0
    click_count = 0

    while click_count < MAX_MORE_CLICKS:
        campaigns = collect_visible_campaign_links(
            page
        )

        current_count = len(
            campaigns
        )

        print(
            (
                "  Görünen benzersiz "
                "kampanya URL sayısı: "
                f"{current_count}"
            )
        )

        if current_count == previous_count:
            stable_rounds += 1

        else:
            stable_rounds = 0

        previous_count = current_count

        more_button = find_visible_more_button(
            page
        )

        if more_button is None:
            break

        try:
            more_button.scroll_into_view_if_needed()

            more_button.click(
                timeout=3000
            )

            click_count += 1

            page.wait_for_timeout(
                1200
            )

        except Exception:
            break

        if stable_rounds >= 2:
            break

    return collect_visible_campaign_links(
        page
    )


# =========================================================
# DETAIL TEXT
# =========================================================

def clean_detail_text(text):
    stop_markers = [
        "Diğer Kampanyalar",
        "Zorunlu Çerezler",
        (
            "Tüm site ziyaretçilerimizi "
            "daha iyi tanımak"
        ),
        "Çerez Aydınlatma Metni",
        (
            "ÇEREZ KULLANIMINA İLİŞKİN "
            "AYDINLATMA METNİ"
        ),
    ]

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

        normalized_line = normalize_match(
            line
        )

        should_stop = False

        for marker in stop_markers:
            if (
                normalize_match(marker)
                in normalized_line
            ):
                should_stop = True
                break

        if should_stop:
            break

        if line == previous:
            continue

        lines.append(
            line
        )

        previous = line

    return "\n".join(
        lines
    ).strip()


def get_detail_text(page):
    try:
        body_text = page.locator(
            "body"
        ).inner_text(
            timeout=5000
        )

    except Exception:
        return ""

    return clean_detail_text(
        body_text
    )


# =========================================================
# CATEGORY
# =========================================================

def detect_category(
    listing_text,
    detail_text,
):
    # Öncelik listing kartında.
    # Çünkü kategori kampanyaya özel olarak
    # listing card içerisinde bulunuyor.

    listing_normalized = normalize_match(
        listing_text
    )

    listing_matches = []

    for category in CAMPAIGN_CATEGORIES:
        if (
            normalize_match(category)
            in listing_normalized
        ):
            listing_matches.append(
                category
            )

    if len(listing_matches) == 1:
        return listing_matches[0]

    # Listing kartından çıkmazsa
    # detay sayfasına bak.
    detail_normalized = normalize_match(
        detail_text
    )

    detail_matches = []

    for category in CAMPAIGN_CATEGORIES:
        if (
            normalize_match(category)
            in detail_normalized
        ):
            detail_matches.append(
                category
            )

    if len(detail_matches) == 1:
        return detail_matches[0]

    return ""


# =========================================================
# COMMERCIAL
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


# =========================================================
# STATUS
# =========================================================

def classify_status(
    title,
    listing_text,
    detail_text,
    end_date_text,
):
    combined = normalize_match(
        (
            f"{title}\n"
            f"{listing_text}\n"
            f"{detail_text}"
        )
    )

    # -----------------------------------------------------
    # 1 - EXPLICIT END MARKERS
    # -----------------------------------------------------

    ended_markers = [
        "kampanya süresi dolmuştur",
        "kampanya suresi dolmustur",
        "kampanya sona erdi",
        "kampanya sona ermiştir",
        "sona erdi",
        "süresi doldu",
        "süresi dolmuştur",
    ]

    for marker in ended_markers:
        if (
            normalize_match(marker)
            in combined
        ):
            return (
                "Sona erdi",
                (
                    "Metinde sona erme "
                    f"ifadesi bulundu: {marker}"
                ),
            )

    # -----------------------------------------------------
    # 2 - REAL DATE
    # -----------------------------------------------------

    if (
        end_date_text
        and end_date_text != "-"
    ):
        parsed = parse_turkish_date(
            end_date_text
        )

        if parsed is not None:
            if parsed < date.today():
                return (
                    "Sona erdi",
                    (
                        "Bitiş tarihi geçmiş: "
                        f"{end_date_text}"
                    ),
                )

            return (
                "Devam ediyor",
                (
                    "Bitiş tarihi gelecekte/bugün: "
                    f"{end_date_text}"
                ),
            )

    # -----------------------------------------------------
    # 3 - EXPLICIT ACTIVE
    # -----------------------------------------------------

    if "devam ediyor" in combined:
        return (
            "Devam ediyor",
            (
                "Kaynakta açık 'Devam ediyor' "
                "ifadesi bulundu."
            ),
        )

    # -----------------------------------------------------
    # 4 - OPEN-ENDED
    # -----------------------------------------------------

    if end_date_text == "-":
        return (
            "Devam ediyor",
            (
                "Kaynakta Bitiş Tarihi '-' "
                "olarak belirtilmiş ve sona "
                "erme ifadesi bulunmuyor."
            ),
        )

    return (
        "",
        (
            "Açık durum veya geçerli "
            "bitiş bilgisi bulunamadı."
        ),
    )


# =========================================================
# DETAIL INSPECTION
# =========================================================

def inspect_campaign_detail(
    page,
    campaign,
):
    url = campaign[
        "url"
    ]

    response = page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=45000,
    )

    page.wait_for_timeout(
        650
    )

    http_status = (
        response.status
        if response
        else None
    )

    final_url = page.url

    try:
        title = normalize_text(
            page.locator(
                "h1"
            ).first.inner_text(
                timeout=3000
            )
        )

    except Exception:
        title = ""

    detail_text = get_detail_text(
        page
    )

    listing_text = campaign.get(
        "listing_text",
        "",
    )

    # Listing önce geliyor.
    # Çünkü listing kartındaki tarih bilgisi
    # çoğu kayıtta kampanyaya özeldir.
    date_source = (
        f"{listing_text}\n"
        f"{detail_text}"
    )

    end_date_text = detect_end_date(
        date_source
    )

    category = detect_category(
        listing_text,
        detail_text,
    )

    status, status_reason = classify_status(
        title,
        listing_text,
        detail_text,
        end_date_text,
    )

    commercial = is_commercial_url(
        url
    )

    return {
        "kampanya_basligi": title,
        "kategori": category,
        "durum": status,
        "durum_nedeni": status_reason,
        "bitis_tarihi": end_date_text,
        "kapsam": (
            "ticari_haric"
            if commercial
            else "kendim_icin"
        ),
        "ticari_url": commercial,
        "kaynak_url": url,
        "final_url": final_url,
        "http_status": http_status,
        "listing_text": listing_text,
    }


# =========================================================
# DUPLICATE
# =========================================================

def find_duplicate_urls(campaigns):
    seen = set()
    duplicates = []

    for campaign in campaigns:
        url = str(
            campaign.get(
                "kaynak_url",
                "",
            )
        ).rstrip(
            "/"
        ).lower()

        if not url:
            continue

        if url in seen:
            duplicates.append(
                url
            )

        else:
            seen.add(
                url
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
        "DÜNYA KATILIM - CAMPAIGN DISCOVERY V5"
    )
    print(
        "=" * 118
    )
    print(
        "Liste:",
        LIST_URL,
    )
    print(
        "Kapsam: görünür KENDİM İÇİN kampanyaları"
    )
    print()

    errors = []
    warnings = []

    listing_campaigns = []
    campaigns = []

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

            response = page.goto(
                LIST_URL,
                wait_until="domcontentloaded",
                timeout=45000,
            )

            list_status = (
                response.status
                if response
                else None
            )

            print(
                "Liste HTTP:",
                list_status,
            )

            if (
                list_status is not None
                and list_status != 200
            ):
                errors.append(
                    (
                        "Liste HTTP status "
                        f"{list_status}"
                    )
                )

            page.wait_for_timeout(
                1400
            )

            cookie_closed = dismiss_cookie_banner(
                page
            )

            print(
                "Cookie popup:",
                (
                    "KAPATILDI ✅"
                    if cookie_closed
                    else "YOK / GEREKMEDİ"
                ),
            )

            individual_clicked = activate_individual_tab(
                page
            )

            print(
                "KENDİM İÇİN sekmesi:",
                (
                    "AKTİFLEŞTİRİLDİ ✅"
                    if individual_clicked
                    else "TIKLANAMADI ⚠️"
                ),
            )

            page.wait_for_timeout(
                1000
            )

            print()
            print(
                "Görünür kampanyalar yükleniyor..."
            )

            listing_campaigns = (
                load_all_visible_campaigns(
                    page
                )
            )

            print()
            print(
                "Listing görünür benzersiz URL:",
                len(
                    listing_campaigns
                ),
            )

            if not listing_campaigns:
                errors.append(
                    (
                        "Görünür kampanya "
                        "URL'si bulunamadı."
                    )
                )

            for index, campaign in enumerate(
                listing_campaigns,
                start=1,
            ):
                print()
                print(
                    "-" * 118
                )

                print(
                    (
                        f"[{index}/"
                        f"{len(listing_campaigns)}] "
                        f"{campaign['url']}"
                    )
                )

                try:
                    detail = inspect_campaign_detail(
                        page,
                        campaign,
                    )

                    campaigns.append(
                        detail
                    )

                    print(
                        "Başlık:",
                        detail[
                            "kampanya_basligi"
                        ]
                        or "BULUNAMADI",
                    )

                    print(
                        "HTTP:",
                        detail[
                            "http_status"
                        ],
                    )

                    print(
                        "Kategori:",
                        detail[
                            "kategori"
                        ]
                        or "BELİRSİZ",
                    )

                    print(
                        "Durum:",
                        detail[
                            "durum"
                        ]
                        or "BELİRSİZ",
                    )

                    print(
                        "Neden:",
                        detail[
                            "durum_nedeni"
                        ],
                    )

                    print(
                        "Bitiş:",
                        detail[
                            "bitis_tarihi"
                        ]
                        or "YOK",
                    )

                    print(
                        "Ticari URL:",
                        (
                            "EVET ⚠️"
                            if detail[
                                "ticari_url"
                            ]
                            else "HAYIR ✅"
                        ),
                    )

                    if (
                        detail[
                            "http_status"
                        ]
                        != 200
                    ):
                        errors.append(
                            (
                                f"{campaign['url']} "
                                "-> HTTP "
                                f"{detail['http_status']}"
                            )
                        )

                    if not detail[
                        "kampanya_basligi"
                    ]:
                        errors.append(
                            (
                                f"{campaign['url']} "
                                "-> H1 başlık bulunamadı."
                            )
                        )

                except Exception as error:
                    errors.append(
                        (
                            f"{campaign['url']} "
                            "-> "
                            f"{type(error).__name__}: "
                            f"{error}"
                        )
                    )

                    print(
                        "DETAIL HATA ❌:",
                        error,
                    )

        finally:
            browser.close()

    # =====================================================
    # GLOBAL
    # =====================================================

    duplicate_urls = find_duplicate_urls(
        campaigns
    )

    if duplicate_urls:
        errors.append(
            (
                "Duplicate campaign URL bulundu: "
                f"{duplicate_urls}"
            )
        )

    commercial_campaigns = [
        item
        for item in campaigns
        if item.get(
            "ticari_url"
        )
    ]

    individual_campaigns = [
        item
        for item in campaigns
        if not item.get(
            "ticari_url"
        )
    ]

    active_campaigns = [
        item
        for item in individual_campaigns
        if item.get(
            "durum"
        ) == "Devam ediyor"
    ]

    inactive_campaigns = [
        item
        for item in individual_campaigns
        if item.get(
            "durum"
        ) == "Sona erdi"
    ]

    unknown_campaigns = [
        item
        for item in individual_campaigns
        if not item.get(
            "durum"
        )
    ]

    category_unknown_active = [
        item
        for item in active_campaigns
        if not item.get(
            "kategori"
        )
    ]

    if unknown_campaigns:
        errors.append(
            (
                "Durumu belirsiz bireysel "
                "kampanya var: "
                f"{len(unknown_campaigns)}"
            )
        )

    if category_unknown_active:
        errors.append(
            (
                "Kategori belirsiz aktif "
                "kampanya var: "
                f"{len(category_unknown_active)}"
            )
        )

    if commercial_campaigns:
        warnings.append(
            (
                "Listing içinde ticari URL "
                "tespit edildi ve bireysel "
                "kapsamdan çıkarıldı: "
                f"{len(commercial_campaigns)}"
            )
        )

    # =====================================================
    # CATEGORY COUNTS
    # =====================================================

    category_counts = {}

    for item in active_campaigns:
        category = item.get(
            "kategori",
            "",
        )

        if not category:
            continue

        category_counts[
            category
        ] = (
            category_counts.get(
                category,
                0,
            )
            + 1
        )

    # =====================================================
    # SAVE
    # =====================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "banka": BANK_NAME,
        "liste_url": LIST_URL,
        "discovery_zamani": (
            datetime.now().isoformat(
                timespec="seconds"
            )
        ),
        "kapsam": "kendim_icin",
        "listing_gorunur_url_sayisi": len(
            listing_campaigns
        ),
        "detay_sayisi": len(
            campaigns
        ),
        "ticari_haric_tutulan_sayisi": len(
            commercial_campaigns
        ),
        "bireysel_aday_sayisi": len(
            individual_campaigns
        ),
        "aktif_kampanya_sayisi": len(
            active_campaigns
        ),
        "sona_ermis_kampanya_sayisi": len(
            inactive_campaigns
        ),
        "durumu_belirsiz_sayisi": len(
            unknown_campaigns
        ),
        "kategori_belirsiz_aktif_sayisi": len(
            category_unknown_active
        ),
        "duplicate_url_sayisi": len(
            duplicate_urls
        ),
        "aktif_kategori_dagilimi": (
            category_counts
        ),
        "aktif_kampanyalar": (
            active_campaigns
        ),
        "sona_ermis_kampanyalar": (
            inactive_campaigns
        ),
        "ticari_haric_tutulanlar": (
            commercial_campaigns
        ),
        "durumu_belirsiz_kampanyalar": (
            unknown_campaigns
        ),
        "kategori_belirsiz_aktifler": (
            category_unknown_active
        ),
        "tum_detaylar": campaigns,
    }

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
        "CAMPAIGN DISCOVERY V5 SONUCU"
    )
    print(
        "=" * 118
    )

    print(
        "Listing görünür URL:",
        len(
            listing_campaigns
        ),
    )

    print(
        "Detay:",
        len(
            campaigns
        ),
    )

    print(
        "Ticari hariç:",
        len(
            commercial_campaigns
        ),
    )

    print(
        "Bireysel aday:",
        len(
            individual_campaigns
        ),
    )

    print(
        "Aktif bireysel:",
        len(
            active_campaigns
        ),
    )

    print(
        "Sona ermiş bireysel:",
        len(
            inactive_campaigns
        ),
    )

    print(
        "Durumu belirsiz:",
        len(
            unknown_campaigns
        ),
    )

    print(
        "Kategori belirsiz aktif:",
        len(
            category_unknown_active
        ),
    )

    print(
        "Duplicate URL:",
        len(
            duplicate_urls
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

    print()
    print(
        "AKTİF KATEGORİ DAĞILIMI:"
    )

    if category_counts:
        for category, count in sorted(
            category_counts.items()
        ):
            print(
                f"- {category}: {count}"
            )

    else:
        print(
            "- Yok"
        )

    print()
    print(
        "SONA ERMİŞ BİREYSEL KAMPANYALAR:"
    )

    if inactive_campaigns:
        for item in inactive_campaigns:
            print(
                "-",
                item[
                    "kampanya_basligi"
                ],
                "|",
                (
                    item[
                        "bitis_tarihi"
                    ]
                    or item[
                        "durum_nedeni"
                    ]
                ),
            )

    else:
        print(
            "- Yok"
        )

    print()
    print(
        "TİCARİ HARİÇ TUTULANLAR:"
    )

    if commercial_campaigns:
        for item in commercial_campaigns:
            print(
                "-",
                item[
                    "kaynak_url"
                ],
            )

    else:
        print(
            "- Yok"
        )

    if unknown_campaigns:
        print()
        print(
            "DURUMU BELİRSİZLER:"
        )

        for item in unknown_campaigns:
            print(
                "-",
                item[
                    "kampanya_basligi"
                ],
                "|",
                item[
                    "kaynak_url"
                ],
            )

    if category_unknown_active:
        print()
        print(
            "KATEGORİSİ BELİRSİZ AKTİFLER:"
        )

        for item in category_unknown_active:
            print(
                "-",
                item[
                    "kampanya_basligi"
                ],
                "|",
                item[
                    "kaynak_url"
                ],
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
                "CAMPAIGN DISCOVERY V5 "
                "TEMİZ ✅"
            )
        )

    else:
        print(
            (
                "SONUÇ: DÜNYA KATILIM "
                "CAMPAIGN DISCOVERY V5 "
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