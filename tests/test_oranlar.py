"""Oran motoru testleri.

Merkezdeki iddia: oran hesabı fiyat seviyesinden habersiz. Aynı
fonksiyon nominal ve düzeltilmiş rakamlarda çalışıyor, hiçbir yerde
"eğer düzeltilmişse" dalı yok. Olsaydı, ölçtüğümüz fark kısmen kendi
kodumuzdan gelirdi.
"""

import pandas as pd
import pytest

from tms29.oranlar import ORANLAR, oranlari_hesapla, seviye_karsilastir
from tms29.veri import panel_yukle


@pytest.fixture(scope="module")
def oranlar():
    return oranlari_hesapla(panel_yukle())


def test_butun_oranlar_hesaplaniyor(oranlar):
    for ad in ORANLAR:
        assert oranlar[ad].notna().sum() >= 60, ad


def test_her_oranin_aciklamasi_var():
    """Açıklaması olmayan oran, savunulamayan oran."""
    for ad, (_, aciklama) in ORANLAR.items():
        assert len(aciklama) > 20, ad


def test_oran_hesabi_seviyeden_habersiz():
    """Aynı satır, seviye etiketi değiştirilse bile aynı oranı vermeli."""
    satir = pd.DataFrame(
        [
            {
                "sirket": "X",
                "yil": 2022,
                "seviye": "nominal",
                "toplam_yukumluluk": 100.0,
                "ozkaynak": 50.0,
                "donen_varlik": 60.0,
                "kv_yukumluluk": 40.0,
                "toplam_varlik": 150.0,
                "duran_varlik": 90.0,
                "net_kar": 10.0,
                "hasilat": 200.0,
            }
        ]
    )
    a = oranlari_hesapla(satir)
    b = oranlari_hesapla(satir.assign(seviye="sag2023"))
    for ad in ORANLAR:
        assert a[ad].iloc[0] == b[ad].iloc[0]


def test_eksik_kalem_orani_nan_yapiyor_satiri_dusurmuyor():
    satir = pd.DataFrame(
        [
            {
                "sirket": "X",
                "yil": 2022,
                "seviye": "nominal",
                "toplam_yukumluluk": 100.0,
                "ozkaynak": 50.0,
                "donen_varlik": 60.0,
                "kv_yukumluluk": 40.0,
                "toplam_varlik": 150.0,
                "duran_varlik": 90.0,
                "net_kar": None,
                "hasilat": 200.0,
            }
        ]
    )
    r = oranlari_hesapla(satir)
    assert len(r) == 1
    assert pd.notna(r.borc_ozkaynak.iloc[0])
    assert pd.isna(r.net_kar_marji.iloc[0])


def test_likidite_orani_duzeltmeden_neredeyse_etkilenmiyor(oranlar):
    """Dönen varlık ve kısa vadeli borç ağırlıklı parasaldır: birlikte ölçeklenir.

    Bu, mekanizmanın test edilebilir bir öngörüsü -- tutmasaydı
    parasal/parasal olmayan ayrımı yanlış olurdu.
    """
    k = seviye_karsilastir(oranlar, 2022, "nominal", "sag2023")
    cari = k[k.oran == "cari"]
    assert len(cari) == 7
    assert cari.degisim.abs().max() < 0.05


def test_kaldirac_orani_duzeltmeden_belirgin_etkileniyor(oranlar):
    """Karşıt öngörü: özkaynak parasal değil, borç parasal -> oran düşmeli."""
    k = seviye_karsilastir(oranlar, 2022, "nominal", "sag2023")
    kaldirac = k[k.oran == "borc_ozkaynak"]
    assert len(kaldirac) == 7
    assert (kaldirac.degisim < 0).all(), "her şirkette düşmesi bekleniyor"
    assert kaldirac.degisim.abs().max() > 0.10
