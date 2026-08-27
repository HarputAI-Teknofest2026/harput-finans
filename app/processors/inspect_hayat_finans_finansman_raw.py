import json
import os
import re


# =========================================================
# AYARLAR
# =========================================================

INPUT_FILE = "data/raw/hayat_finans_finansman_urunleri.json"


# =========================================================
# NORMALİZASYON
# =========================================================

def tr_lower(value):
    value = str(value or "")

    value = value.replace("İ", "i")
    value = value.replace("I", "ı")

    return value.casefold()


def clean_text(value):
    value = str(value or "")

    value = value.replace("\u00a0", " ")
    value = value.replace("\u200b", "")
    value = value.replace("\ufeff", "")

    value = re.sub(
        r"[ \t]+",
        " ",
        value
    )

    value = re.sub(
        r"\n{3,}",
        "\n\n",
        value
    )

    return value.strip()


# =========================================================
# JSON OKU
# =========================================================

def load_json():
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"Dosya bulunamadı: {INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


# =========================================================
# SATIR BUL
# =========================================================

def find_matching_lines(text, keywords):
    lines = [
        line.strip()
        for line in clean_text(text).splitlines()
        if line.strip()
    ]

    results = []

    for line in lines:
        lower_line = tr_lower(line)

        if any(
            tr_lower(keyword) in lower_line
            for keyword in keywords
        ):
            results.append(line)

    return results


# =========================================================
# FİNANSAL / SEMANTİK İFADELER
# =========================================================

SEARCH_GROUPS = {
    "KÂR / ORAN": [
        "kâr",
        "kar ",
        "%",
        "oran",
        "maliyet",
    ],

    "TUTAR / LİMİT": [
        "tl",
        "₺",
        "limit",
        "tutar",
        "finansman üst limiti",
        "kredi limiti",
    ],

    "VADE / TAKSİT": [
        "vade",
        "ay",
        "taksit",
        "erteleme",
    ],

    "MASRAF / ÜCRET": [
        "masraf",
        "ücret",
        "tahsis",
        "sigorta",
        "vade farkı",
    ],

    "HEDEF / BAŞVURU": [
        "müşteri",
        "kimlik",
        "gelir belgesi",
        "başvuru",
        "anlaşmalı",
        "iş ortağı",
        "kurum",
    ],

    "KOŞULLAR": [
        "geçerli",
        "koşul",
        "şart",
        "kullanabilir",
        "yararlan",
        "değerlendirilir",
        "dilediği zaman",
    ],
}


# =========================================================
# ÜRÜN ÖZEL KONTROLLER
# =========================================================

EXPECTED_FACTS = {
    "Bana Bunu Al": [
        "50.000 TL",
        "500 TL",
        "18 aya kadar",
    ],

    "Bana Bunu Al İş Ortağım": [
        "24 aya",
        "avantajlı kâr oranları",
        "kimlik",
    ],

    "Eğitim Finansmanı Sistemi": [
        "600.000TL",
        "3 ay erteleme",
        "masraf",
        "vade farkı",
        "gelir belgesi",
    ],
}


SUSPICIOUS_TERMS = {
    "Bana Bunu Al": [
        "Avantajlı Katılma Hesabı",
        "Eğitim Finansmanı Sistemi",
    ],

    "Bana Bunu Al İş Ortağım": [
        "Avantajlı Katılma Hesabı",
        "Eğitim Finansmanı Sistemi",
    ],

    "Eğitim Finansmanı Sistemi": [
        "Avantajlı Katılma Hesabı",
        "eşit ve yüksek kâr paylaşım oranı",
        "birikimlerinizi değerlendirirken",
    ],
}


# =========================================================
# MAIN
# =========================================================

def main():

    print()
    print("=" * 110)
    print("HAYAT FİNANS - FİNANSMAN RAW INSPECTOR V1")
    print("=" * 110)

    print(
        "Dosya:",
        INPUT_FILE
    )

    data = load_json()

    products = data.get(
        "urunler",
        []
    )

    print()
    print(
        "Toplam kayıt:",
        len(products)
    )

    total_errors = []
    total_warnings = []

    # =====================================================
    # HER ÜRÜNÜ AYRI İNCELE
    # =====================================================

    for index, product in enumerate(
        products,
        start=1
    ):

        title = product.get(
            "urun_adi",
            ""
        )

        url = product.get(
            "kaynak_url",
            ""
        )

        text = clean_text(
            product.get(
                "ham_metin",
                ""
            )
        )

        text_lower = tr_lower(text)

        print()
        print("=" * 110)
        print(
            f"[{index}/{len(products)}] {title}"
        )
        print("=" * 110)

        print(
            "URL:",
            url
        )

        print(
            "Metin uzunluğu:",
            len(text)
        )

        # =================================================
        # BEKLENEN GERÇEKLER
        # =================================================

        print()
        print(
            "BEKLENEN KRİTİK BİLGİLER:"
        )

        expected = EXPECTED_FACTS.get(
            title,
            []
        )

        for fact in expected:

            found = (
                tr_lower(fact)
                in text_lower
            )

            print(
                (
                    "✓"
                    if found
                    else "✗"
                ),
                fact
            )

            if not found:
                total_errors.append(
                    (
                        f"{title} -> "
                        f"kritik bilgi bulunamadı: {fact}"
                    )
                )

        # =================================================
        # ŞÜPHELİ CROSS-CONTAMINATION
        # =================================================

        print()
        print(
            "CROSS-CONTAMINATION:"
        )

        suspicious_found = []

        for term in SUSPICIOUS_TERMS.get(
            title,
            []
        ):

            if tr_lower(term) in text_lower:
                suspicious_found.append(term)

        if suspicious_found:

            for term in suspicious_found:
                print(
                    "✗",
                    term
                )

                total_errors.append(
                    (
                        f"{title} -> "
                        f"başka ürün içeriği bulundu: {term}"
                    )
                )

        else:
            print(
                "✓ Şüpheli başka ürün içeriği yok"
            )

        # =================================================
        # SEMANTİK GRUPLAR
        # =================================================

        for group_name, keywords in (
            SEARCH_GROUPS.items()
        ):

            print()
            print(
                f"{group_name}:"
            )

            matches = find_matching_lines(
                text,
                keywords
            )

            if not matches:
                print(
                    "  - Bulunamadı"
                )
                continue

            # Aynı satırı tekrar basma
            unique_matches = []

            seen = set()

            for match in matches:

                key = tr_lower(match)

                if key not in seen:
                    seen.add(key)
                    unique_matches.append(match)

            for match in unique_matches[:20]:

                print(
                    "  •",
                    match
                )

            if len(unique_matches) > 20:

                print(
                    (
                        "  ... "
                        f"{len(unique_matches) - 20} "
                        "satır daha"
                    )
                )

        # =================================================
        # SAYISAL İFADELER
        # =================================================

        print()
        print(
            "SAYISAL İFADELER:"
        )

        number_patterns = [
            r"\b\d{1,3}(?:\.\d{3})+(?:,\d+)?\s*(?:TL|₺)?",
            r"\b\d+(?:,\d+)?\s*%",
            r"%\s*\d+(?:,\d+)?",
            r"\b\d+\s*aya?\b",
            r"\b\d+\s*ay\b",
        ]

        numeric_matches = []

        for pattern in number_patterns:

            found = re.findall(
                pattern,
                text,
                flags=re.IGNORECASE
            )

            numeric_matches.extend(
                found
            )

        unique_numbers = []

        seen_numbers = set()

        for number in numeric_matches:

            value = number.strip()

            if value not in seen_numbers:

                seen_numbers.add(value)
                unique_numbers.append(value)

        if unique_numbers:

            for number in unique_numbers:

                print(
                    "  •",
                    number
                )

        else:

            print(
                "  - Sayısal ifade bulunamadı"
            )

        # =================================================
        # ÖZEL ÜRÜN YORUMLARI
        # =================================================

        print()
        print(
            "ÜRÜN ÖZEL KONTROL:"
        )

        if title == "Bana Bunu Al":

            if (
                "50.000"
                in text_lower
                and "500 tl"
                in text_lower
                and "18 aya"
                in text_lower
            ):
                print(
                    "✓ Limit / minimum kullanım / vade bilgileri mevcut"
                )
            else:
                total_errors.append(
                    (
                        "Bana Bunu Al -> "
                        "limit/vade bilgileri eksik."
                    )
                )

        elif title == "Bana Bunu Al İş Ortağım":

            if "24 aya" in text_lower:

                print(
                    "✓ 24 aya kadar vade mevcut"
                )

            else:

                total_errors.append(
                    (
                        "Bana Bunu Al İş Ortağım -> "
                        "24 ay vade kayıp."
                    )
                )

            if (
                "avantajlı kâr oranları"
                in text_lower
            ):

                print(
                    "✓ Kâr oranından söz ediliyor"
                )

                print(
                    "⚠ Sayısal kâr payı oranı olmayabilir; "
                    "extractor oran uydurmamalı"
                )

                total_warnings.append(
                    (
                        "Bana Bunu Al İş Ortağım -> "
                        "kâr oranı sözel, sayısal oran "
                        "kaynakta yoksa [] bırakılmalı."
                    )
                )

        elif title == "Eğitim Finansmanı Sistemi":

            if (
                "600.000"
                in text_lower
            ):

                print(
                    "✓ 600.000 TL üst limit mevcut"
                )

            else:

                total_errors.append(
                    (
                        "Eğitim Finansmanı Sistemi -> "
                        "600.000 TL limit kayıp."
                    )
                )

            if (
                "3 ay erteleme"
                in text_lower
            ):

                print(
                    "✓ 3 ay erteleme mevcut"
                )

            if (
                "masraf ya da vade farkı alınmamaktadır"
                in text_lower
            ):

                print(
                    "✓ Masraf/vade farkı alınmadığı açıkça belirtiliyor"
                )

            if (
                "hemen avantajlı olmak için tıklayın"
                in text_lower
            ):

                print(
                    "⚠ Sonda CTA mevcut; extractor bunu koşul/avantaj olarak almamalı"
                )

                total_warnings.append(
                    (
                        "Eğitim Finansmanı Sistemi -> "
                        "CTA metni extractor tarafından "
                        "alanlara taşınmamalı."
                    )
                )

    # =====================================================
    # FINAL RAPOR
    # =====================================================

    print()
    print("=" * 110)
    print("INSPECT SONUCU")
    print("=" * 110)

    print(
        "Toplam kayıt:",
        len(products)
    )

    print(
        "Error:",
        len(total_errors)
    )

    print(
        "Warning:",
        len(total_warnings)
    )

    if total_warnings:

        print()
        print(
            "UYARILAR:"
        )

        for warning in total_warnings:

            print(
                "-",
                warning
            )

    if total_errors:

        print()
        print(
            "HATALAR:"
        )

        for error in total_errors:

            print(
                "-",
                error
            )

    print()

    if not total_errors:

        print(
            "SONUÇ: HAYAT FİNANS FİNANSMAN RAW INSPECT BAŞARILI ✅"
        )

        print()
        print(
            "Extractor'a geçilebilir."
        )

    else:

        print(
            "SONUÇ: HAYAT FİNANS FİNANSMAN RAW INSPECT BAŞARISIZ ❌"
        )

        print()
        print(
            "Extractor'a geçmeden önce RAW düzeltilmeli."
        )

    print("=" * 110)


if __name__ == "__main__":
    main()