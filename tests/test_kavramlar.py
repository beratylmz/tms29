"""Fiyat seviyesi ayrıştırma testleri.

Bu dosyadaki en önemli test, aynı seviyenin iki farklı yazımının aynı
değere normalize olduğunu kilitleyen olan. Normalize edilmezse "2024 SAG"
ile "2024 TL SAG" iki ayrı seviye sanılır; o zaman aynı yılın iki
kolonu eşleşmez ve projenin ölçtüğü karşılaştırma sessizce boş çıkar.
"""

import pytest

from tms29.kavramlar import fiyat_seviyesi_ayristir as ayristir


@pytest.mark.parametrize(
    ("baslik", "beklenen"),
    [
        ("31.12.2022 (Nominal TL)", (2022, "nominal")),
        ("31.12.2022 (Nominal)", (2022, "nominal")),
        ("31.12.2022 (2023 SAG)", (2022, "sag2023")),
        ("31.12.2023 (2024 TL SAG)", (2023, "sag2024")),
        ("31.12.2025 (2025 SAG)", (2025, "sag2025")),
    ],
)
def test_baslik_ayristirma(baslik, beklenen):
    assert ayristir(baslik) == beklenen


def test_ayni_seviyenin_iki_yazimi_ayni_sonuca_gidiyor():
    """'2024 SAG' ve '2024 TL SAG' aynı fiyat seviyesidir."""
    assert ayristir("31.12.2023 (2024 SAG)") == ayristir("31.12.2023 (2024 TL SAG)")


def test_yil_ve_seviye_ayri_kalıyor():
    """Aynı yıl, farklı seviye -> farklı sonuç. Projenin ölçtüğü fark bu."""
    a = ayristir("31.12.2022 (Nominal)")
    b = ayristir("31.12.2022 (2023 SAG)")
    assert a[0] == b[0] and a[1] != b[1]


def test_taninmayan_baslik_hata_veriyor():
    """Sessizce None dönmek, kolonun sessizce düşmesi demek olurdu."""
    with pytest.raises(ValueError):
        ayristir("Dikey Yüzde")
    with pytest.raises(ValueError):
        ayristir("31.12.2022 (Bilinmeyen Birim)")
