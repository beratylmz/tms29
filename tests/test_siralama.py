"""Sıralama, eşik ve parasal pozisyon testleri — projenin asıl bulguları.

Üç iddia kilitleniyor:

1. **Likidite oranı düzeltmeden etkilenmez, kaldıraç az etkilenir,
   kârlılık çok etkilenir.** Üçü de mekanizmadan çıkan öngörüler:
   dönen varlık/kısa vadeli borç ikisi de parasal (birlikte ölçeklenir);
   özkaynak parasal değil (kaldıraç kayar); gelir tablosuna ise yepyeni
   bir kalem giriyor (kârlılık yeniden kuruluyor).

2. **Eşik taraması seçimden bağımsızdır.** Tek bir eşik seçip "bak
   kırılıyor" demek, sonucu veren eşiği seçmek olurdu.

3. **Kaldıraç tek başına enflasyon kazancını belirlemez.** ENJSA karşı
   örneği: yüksek kaldıraç, buna rağmen parasal kayıp.
"""

import pytest

from tms29.etki import parasal_kazanc_etkisi
from tms29.oranlar import oranlari_hesapla, seviye_karsilastir
from tms29.siralama import esik_kirilma_araliklari, esik_tarama, siralama_kaymasi
from tms29.veri import panel_yukle


@pytest.fixture(scope="module")
def karsilastirma():
    return seviye_karsilastir(
        oranlari_hesapla(panel_yukle()), 2022, "nominal", "sag2023"
    )


# --- 1. SIRALAMA: mekanizmanın üç öngörüsü --------------------------------


def test_likidite_siralamasi_hic_degismiyor(karsilastirma):
    sk = siralama_kaymasi(karsilastirma).set_index("oran")
    assert sk.loc["cari", "spearman"] == pytest.approx(1.0)
    assert sk.loc["cari", "yer_degistiren_cift"] == 0


def test_kaldirac_siralamasi_neredeyse_korunuyor(karsilastirma):
    sk = siralama_kaymasi(karsilastirma).set_index("oran")
    assert sk.loc["borc_ozkaynak", "spearman"] > 0.9
    assert sk.loc["borc_ozkaynak", "yer_degistiren_cift"] <= 2


def test_karlilik_siralamasi_bozuluyor(karsilastirma):
    """Bilanço oranlarının aksine kârlılık sıralaması ayakta kalmıyor."""
    sk = siralama_kaymasi(karsilastirma).set_index("oran")
    for oran in ("net_kar_marji", "ozkaynak_karliligi"):
        assert sk.loc[oran, "spearman"] < 0.7, oran
        assert sk.loc[oran, "yer_degistiren_cift"] >= 4, oran


def test_kaldirac_her_sirkette_ayni_yone_gidiyor(karsilastirma):
    """Düzeltme yedi şirketin de kaldıracını düşürüyor -- istisnasız."""
    d = karsilastirma[karsilastirma.oran == "borc_ozkaynak"]
    assert len(d) == 7
    assert (d.degisim < 0).all()


# --- 2. EŞİK TARAMASI -----------------------------------------------------


def test_kaldirac_esiklerinin_cogunda_karar_degisiyor(karsilastirma):
    t = esik_tarama(karsilastirma, "borc_ozkaynak")
    assert t["en_az_bir_karar_degisiyor"] > 0.4


def test_likidite_esiklerinde_karar_neredeyse_hic_degismiyor(karsilastirma):
    t = esik_tarama(karsilastirma, "cari")
    assert t["en_az_bir_karar_degisiyor"] < 0.05


def test_kirilma_araliklari_sirketi_kapsiyor(karsilastirma):
    """Her şirketin aralığı, nominal ve düzeltilmiş değerini kapsamalı."""
    a = esik_kirilma_araliklari(karsilastirma, "borc_ozkaynak")
    d = karsilastirma[karsilastirma.oran == "borc_ozkaynak"].set_index("sirket")
    for r in a.itertuples():
        assert r.alt <= d.loc[r.sirket, "a"] <= r.ust
        assert r.alt <= d.loc[r.sirket, "b"] <= r.ust


# --- 3. PARASAL POZİSYON --------------------------------------------------


def test_parasal_kazanc_nominalde_yok_duzeltilmiste_var():
    p = panel_yukle()
    n = p[(p.yil == 2022) & (p.seviye == "nominal")]
    d = p[(p.yil == 2022) & (p.seviye == "sag2023")]
    assert (n.net_parasal_pozisyon.fillna(0) == 0).all()
    assert (d.net_parasal_pozisyon.abs() > 0).all()


def test_kaldirac_tek_basina_kazanci_belirlemiyor():
    """ENJSA karşı örneği: yüksek kaldıraç ama parasal KAYIP.

    Sebep imtiyaz sözleşmesi finansal varlıkları (TFRS Yorum 12): bunlar
    parasal alacak sayıldığı için ENJSA, borcuna rağmen net parasal
    alacaklı konumda. "Borçlu şirket enflasyondan kazanır" kısayolunun
    neden yetersiz olduğunu gösteren somut örnek.
    """
    t = parasal_kazanc_etkisi(panel_yukle(), 2022, "nominal", "sag2023").set_index(
        "sirket"
    )
    assert t.loc["ENJSA", "kaldirac_nominal"] > 1.5
    assert t.loc["ENJSA", "parasal_kazanc"] < 0
    # ve daha az kaldıraçlı biri kazanç yazıyor
    assert t.loc["AYDEM", "kaldirac_nominal"] < t.loc["ENJSA", "kaldirac_nominal"]
    assert t.loc["AYDEM", "parasal_kazanc"] > 0


def test_nakit_zengini_sirket_enflasyondan_kaybediyor():
    """ASTOR negatif net borçlu; parasal pozisyonu onu kaybettiriyor."""
    t = parasal_kazanc_etkisi(panel_yukle(), 2022, "nominal", "sag2023").set_index(
        "sirket"
    )
    assert t.loc["ASTOR", "parasal_kazanc"] < 0
    assert t.loc["ZOREN", "parasal_kazanc"] > 0
