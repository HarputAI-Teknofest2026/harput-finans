import json
import re
import shutil
import unicodedata
from collections import Counter
from copy import deepcopy
from pathlib import Path


# ==================================================================================================
# ZİRAAT KATILIM - FINAL TAG / KAZANÇ CLEANUP
# ==================================================================================================
#
# Bu script SADECE kampanya kayıtlarındaki "kosullar" alanını temizler.
#
# Güvenli çalışma mantığı:
#
#   ham_metin:
#
#       Etiketler
#       Anne, Bebek & Oyuncak
#       Ebebek
#       SPONSORLU
#
#   veya:
#
#       KAZANÇ
#       Peşin Fiyatına 6 Taksit
#       Hemen Katıl
#
# Eğer "kosullar" içinde bu bloklardaki satırlarla TAM EŞLEŞEN bir değer varsa
# kaldırılır.
#
# Cümle içinde geçen marka / avantaj metinlerine dokunulmaz.
# ham_metin değiştirilmez.
# kampanya_avantaji değiştirilmez.
# finansman kayıtlarına dokunulmaz.
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


STRING_FIELDS = (
    set(FINAL_KEYS)
    - LIST_FIELDS
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)


INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ziraat_katilim_all.json"
)


BACKUP_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "ziraat_katilim_all_before_tag_cleanup.json"
)


# ==================================================================================================
# NORMALIZATION
# ==================================================================================================


def clean_visible_text(value):
    """
    Görünür metni bozmadan yalnız whitespace normalize eder.
    """

    if not isinstance(value, str):
        return ""

    value = unicodedata.normalize(
        "NFKC",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def comparison_key(value):
    """
    Sadece eşitlik kontrolü için kullanılır.
    Dosyaya yazılmaz.
    """

    value = clean_visible_text(
        value
    )

    return value.casefold()


# ==================================================================================================
# SOURCE SECTION EXTRACTION
# ==================================================================================================


def get_source_lines(ham_metin):
    """
    ham_metin'i satır satır normalize ederek döndürür.
    ham_metin'in kendisini DEĞİŞTİRMEZ.
    """

    if not isinstance(
        ham_metin,
        str,
    ):

        return []

    result = []

    for line in ham_metin.splitlines():

        line = clean_visible_text(
            line
        )

        if line:
            result.append(
                line
            )

    return result


def extract_section(
    ham_metin,
    start_marker,
    end_marker,
):
    """
    Örnek:

        Etiketler
        Market & Gıda
        A101
        SPONSORLU

    ->
        ["Market & Gıda", "A101"]

    Güvenlik:
    End marker bulunmazsa hiçbir şey çıkarılmaz.
    Böylece sayfanın geri kalanını yanlışlıkla UI bölümü kabul etmeyiz.
    """

    lines = get_source_lines(
        ham_metin
    )

    if not lines:
        return []

    start_key = comparison_key(
        start_marker
    )

    end_key = comparison_key(
        end_marker
    )

    for start_index, line in enumerate(
        lines
    ):

        if (
            comparison_key(line)
            != start_key
        ):
            continue

        section = []

        for index in range(
            start_index + 1,
            len(lines),
        ):

            current = lines[index]

            if (
                comparison_key(current)
                == end_key
            ):

                return section

            section.append(
                current
            )

        # start bulundu fakat end yok.
        # Güvenli olması için boş dön.
        return []

    return []


def extract_ui_residue_candidates(
    ham_metin,
):
    """
    Yalnız iki kesin kaynak bloğunu kullanıyoruz:

      Etiketler -> SPONSORLU
      KAZANÇ    -> Hemen Katıl
    """

    tags = extract_section(
        ham_metin,
        "Etiketler",
        "SPONSORLU",
    )

    gains = extract_section(
        ham_metin,
        "KAZANÇ",
        "Hemen Katıl",
    )

    candidates = (
        tags
        + gains
    )

    result = {}

    for value in candidates:

        key = comparison_key(
            value
        )

        if not key:
            continue

        result[key] = value

    return result


# ==================================================================================================
# RECORD CLEANUP
# ==================================================================================================


def clean_campaign_record(
    record,
):
    """
    Return:
        cleaned_record
        removed_values
    """

    cleaned = deepcopy(
        record
    )

    if (
        cleaned.get(
            "kayit_turu"
        )
        != "kampanya"
    ):

        return (
            cleaned,
            [],
        )

    kosullar = cleaned.get(
        "kosullar",
        [],
    )

    if not isinstance(
        kosullar,
        list,
    ):

        return (
            cleaned,
            [],
        )

    candidates = (
        extract_ui_residue_candidates(
            cleaned.get(
                "ham_metin",
                "",
            )
        )
    )

    if not candidates:

        return (
            cleaned,
            [],
        )

    new_conditions = []

    removed = []

    for condition in kosullar:

        if not isinstance(
            condition,
            str,
        ):

            new_conditions.append(
                condition
            )

            continue

        key = comparison_key(
            condition
        )

        # SADECE exact match.
        if key in candidates:

            removed.append(
                condition
            )

            continue

        new_conditions.append(
            condition
        )

    cleaned[
        "kosullar"
    ] = new_conditions

    return (
        cleaned,
        removed,
    )


# ==================================================================================================
# RESIDUAL AUDIT
# ==================================================================================================


def find_remaining_residues(
    records,
):
    """
    Cleanup sonrası kosullar içinde Etiketler/KAZANÇ
    kaynak bloklarıyla exact eşleşen bir değer kalmış mı?
    """

    residues = []

    for record in records:

        if (
            record.get(
                "kayit_turu"
            )
            != "kampanya"
        ):

            continue

        candidates = (
            extract_ui_residue_candidates(
                record.get(
                    "ham_metin",
                    "",
                )
            )
        )

        if not candidates:
            continue

        for condition in record.get(
            "kosullar",
            [],
        ):

            if not isinstance(
                condition,
                str,
            ):
                continue

            key = comparison_key(
                condition
            )

            if key in candidates:

                residues.append(
                    {
                        "urun_adi":
                            record.get(
                                "urun_adi",
                                "",
                            ),

                        "deger":
                            condition,
                    }
                )

    return residues


# ==================================================================================================
# VALIDATION
# ==================================================================================================


def validate_records(
    original_records,
    final_records,
):
    errors = []

    # ----------------------------------------------------------------------------------------------
    # COUNTS
    # ----------------------------------------------------------------------------------------------

    if len(
        final_records
    ) != 107:

        errors.append(
            f"Toplam kayıt 107 bekleniyordu, "
            f"{len(final_records)} bulundu."
        )

    finance_count = sum(
        record.get(
            "kayit_turu"
        )
        == "finansman"

        for record
        in final_records
    )

    campaign_count = sum(
        record.get(
            "kayit_turu"
        )
        == "kampanya"

        for record
        in final_records
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

    # ----------------------------------------------------------------------------------------------
    # RECORD VALIDATION
    # ----------------------------------------------------------------------------------------------

    urls = []

    for index, record in enumerate(
        final_records,
        start=1,
    ):

        prefix = (
            f"[{index:03d}] "
            f"{record.get('urun_adi', '')}"
        )

        if list(
            record.keys()
        ) != FINAL_KEYS:

            errors.append(
                f"{prefix} -> "
                "Exact 18-key schema/order bozuldu."
            )

        if (
            record.get(
                "banka"
            )
            != BANK_NAME
        ):

            errors.append(
                f"{prefix} -> "
                "Banka adı bozuldu."
            )

        if (
            record.get(
                "kayit_turu"
            )
            not in {
                "finansman",
                "kampanya",
            }
        ):

            errors.append(
                f"{prefix} -> "
                "kayit_turu geçersiz."
            )

        for field in LIST_FIELDS:

            if not isinstance(
                record.get(
                    field
                ),
                list,
            ):

                errors.append(
                    f"{prefix} -> "
                    f"{field} list değil."
                )

        for field in STRING_FIELDS:

            if not isinstance(
                record.get(
                    field
                ),
                str,
            ):

                errors.append(
                    f"{prefix} -> "
                    f"{field} string değil."
                )

        if (
            "TRY"
            in record.get(
                "para_birimi",
                [],
            )
        ):

            errors.append(
                f"{prefix} -> "
                "TRY bulundu."
            )

        if (
            "[RESMİ KAYNAK ÖZETİ]"
            in record.get(
                "ham_metin",
                ""
            )
        ):

            errors.append(
                f"{prefix} -> "
                "RESMİ KAYNAK ÖZETİ marker bulundu."
            )

        url = record.get(
            "kaynak_url",
            "",
        )

        if url:
            urls.append(
                url
            )

    # ----------------------------------------------------------------------------------------------
    # DUPLICATE URL
    # ----------------------------------------------------------------------------------------------

    duplicate_urls = [
        url
        for url, count in Counter(
            urls
        ).items()
        if count > 1
    ]

    for url in duplicate_urls:

        errors.append(
            f"Duplicate URL: {url}"
        )

    # ----------------------------------------------------------------------------------------------
    # ENSURE ONLY KOSULLAR CHANGED
    # ----------------------------------------------------------------------------------------------

    if (
        len(original_records)
        != len(final_records)
    ):

        errors.append(
            "Original/final kayıt sayısı farklı; "
            "field-change audit yapılamadı."
        )

    else:

        for index, (
            original,
            final,
        ) in enumerate(
            zip(
                original_records,
                final_records,
            ),
            start=1,
        ):

            name = final.get(
                "urun_adi",
                "",
            )

            for key in FINAL_KEYS:

                if key == "kosullar":
                    continue

                if (
                    original.get(key)
                    != final.get(key)
                ):

                    errors.append(
                        f"[{index:03d}] {name} -> "
                        f"İzin verilmeyen alan değişti: "
                        f"{key}"
                    )

    # ----------------------------------------------------------------------------------------------
    # RESIDUAL CHECK
    # ----------------------------------------------------------------------------------------------

    residues = (
        find_remaining_residues(
            final_records
        )
    )

    if residues:

        for residue in residues[:20]:

            errors.append(
                "UI residue kaldı -> "
                f"{residue['urun_adi']} :: "
                f"{residue['deger']}"
            )

        if len(residues) > 20:

            errors.append(
                f"... ayrıca "
                f"{len(residues) - 20} "
                f"residue daha var."
            )

    return errors


# ==================================================================================================
# AUDIT
# ==================================================================================================


def print_audit(
    original_records,
    final_records,
    removed_log,
):
    finance_count = sum(
        record.get(
            "kayit_turu"
        )
        == "finansman"

        for record
        in final_records
    )

    campaign_count = sum(
        record.get(
            "kayit_turu"
        )
        == "kampanya"

        for record
        in final_records
    )

    exact_schema = sum(
        list(
            record.keys()
        )
        == FINAL_KEYS

        for record
        in final_records
    )

    urls = [
        record.get(
            "kaynak_url"
        )
        for record
        in final_records
        if record.get(
            "kaynak_url"
        )
    ]

    duplicate_urls = [
        url
        for url, count in Counter(
            urls
        ).items()
        if count > 1
    ]

    try_count = sum(
        "TRY"
        in record.get(
            "para_birimi",
            [],
        )

        for record
        in final_records
    )

    summary_marker_count = sum(
        "[RESMİ KAYNAK ÖZETİ]"
        in record.get(
            "ham_metin",
            ""
        )

        for record
        in final_records
    )

    residues = (
        find_remaining_residues(
            final_records
        )
    )

    changed_records = sum(
        original.get(
            "kosullar"
        )
        != final.get(
            "kosullar"
        )

        for original, final
        in zip(
            original_records,
            final_records,
        )
    )

    print()
    print("=" * 120)
    print(
        "ZİRAAT KATILIM - FINAL TAG / KAZANÇ CLEANUP AUDIT"
    )
    print("=" * 120)

    print(
        f"Toplam kayıt          : "
        f"{len(final_records)}"
    )

    print(
        f"Finansman             : "
        f"{finance_count}"
    )

    print(
        f"Kampanya              : "
        f"{campaign_count}"
    )

    print(
        f"Exact 18-key schema   : "
        f"{exact_schema}/{len(final_records)}"
    )

    print(
        f"Duplicate URL         : "
        f"{len(duplicate_urls)}"
    )

    print(
        f"TRY kalan             : "
        f"{try_count}"
    )

    print(
        f"Summary marker        : "
        f"{summary_marker_count}"
    )

    print(
        f"Değişen kayıt         : "
        f"{changed_records}"
    )

    print(
        f"Kaldırılan residue    : "
        f"{len(removed_log)}"
    )

    print(
        f"Kalan residue         : "
        f"{len(residues)}"
    )

    print()

    print(
        "KALDIRILANLAR"
    )

    print("-" * 120)

    if not removed_log:

        print(
            "Dosyada kaldırılacak residue bulunamadı."
        )

    else:

        for item in removed_log:

            print(
                f"✅ {item['urun_adi']}"
            )

            print(
                f"   Removed: "
                f"{item['deger']}"
            )

    print("=" * 120)


# ==================================================================================================
# MAIN
# ==================================================================================================


def main():

    print()
    print("=" * 120)
    print(
        "ZİRAAT KATILIM - FINAL TAG / KAZANÇ CLEANUP"
    )
    print("=" * 120)

    print(
        f"Input/Output: "
        f"{INPUT_FILE}"
    )

    print()

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Dosya bulunamadı: "
            f"{INPUT_FILE}"
        )

    # ----------------------------------------------------------------------------------------------
    # LOAD
    # ----------------------------------------------------------------------------------------------

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        records = json.load(
            file
        )

    if not isinstance(
        records,
        list,
    ):

        raise ValueError(
            "ziraat_katilim_all.json "
            "root list olmalı."
        )

    original_records = deepcopy(
        records
    )

    print(
        f"Input kayıt: "
        f"{len(records)}"
    )

    # ----------------------------------------------------------------------------------------------
    # CLEAN
    # ----------------------------------------------------------------------------------------------

    final_records = []

    removed_log = []

    for index, record in enumerate(
        records,
        start=1,
    ):

        cleaned, removed = (
            clean_campaign_record(
                record
            )
        )

        final_records.append(
            cleaned
        )

        if removed:

            for value in removed:

                removed_log.append(
                    {
                        "urun_adi":
                            cleaned.get(
                                "urun_adi",
                                "",
                            ),

                        "deger":
                            value,
                    }
                )

            print(
                f"[{index:03d}/{len(records)}] "
                f"CLEAN ✅ "
                f"{cleaned.get('urun_adi', '')} "
                f"(-{len(removed)})"
            )

    # ----------------------------------------------------------------------------------------------
    # AUDIT
    # ----------------------------------------------------------------------------------------------

    print_audit(
        original_records,
        final_records,
        removed_log,
    )

    # ----------------------------------------------------------------------------------------------
    # VALIDATE BEFORE WRITE
    # ----------------------------------------------------------------------------------------------

    errors = validate_records(
        original_records,
        final_records,
    )

    if errors:

        print()
        print("=" * 120)
        print(
            "VALIDATION ERRORS"
        )
        print("=" * 120)

        for error in errors:

            print(
                f"❌ {error}"
            )

        print()

        print(
            "ZİRAAT KATILIM CLEANUP BAŞARISIZ ❌"
        )

        print(
            "Final dosya yazılmadı."
        )

        raise SystemExit(1)

    # ----------------------------------------------------------------------------------------------
    # BACKUP
    # ----------------------------------------------------------------------------------------------

    if not BACKUP_FILE.exists():

        shutil.copy2(
            INPUT_FILE,
            BACKUP_FILE,
        )

        print()
        print(
            f"Backup oluşturuldu: "
            f"{BACKUP_FILE}"
        )

    # ----------------------------------------------------------------------------------------------
    # WRITE
    # ----------------------------------------------------------------------------------------------

    with open(
        INPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            final_records,
            file,
            ensure_ascii=False,
            indent=2,
        )

    # ----------------------------------------------------------------------------------------------
    # RE-READ
    # ----------------------------------------------------------------------------------------------

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        saved_records = json.load(
            file
        )

    final_errors = validate_records(
        original_records,
        saved_records,
    )

    if final_errors:

        print()
        print(
            "Re-read validation başarısız ❌"
        )

        for error in final_errors:

            print(
                f"❌ {error}"
            )

        raise SystemExit(1)

    # ----------------------------------------------------------------------------------------------
    # FINAL
    # ----------------------------------------------------------------------------------------------

    print()
    print("=" * 120)
    print(
        "ZİRAAT KATILIM FINAL CLEANUP BAŞARILI ✅"
    )
    print("=" * 120)

    print(
        f"JSON: "
        f"{INPUT_FILE}"
    )

    print()

    print(
        "Finansman kayıtlarına dokunulmadı ✅"
    )

    print(
        "ham_metin tamamen korundu ✅"
    )

    print(
        "kampanya_avantaji tamamen korundu ✅"
    )

    print(
        "Sadece kosullar içindeki exact "
        "Etiketler/KAZANÇ residue'ları kaldırıldı ✅"
    )

    print(
        f"Kaldırılan toplam residue: "
        f"{len(removed_log)}"
    )

    print(
        "Kalan residue: 0 ✅"
    )

    print(
        "107 kayıt korundu ✅"
    )

    print(
        "20 finansman + 87 kampanya korundu ✅"
    )

    print(
        "Exact 18-key schema korundu ✅"
    )

    print(
        "Duplicate URL: 0 ✅"
    )

    print("=" * 120)


if __name__ == "__main__":
    main()