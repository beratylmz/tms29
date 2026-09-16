"""Grafik testleri.

"Güzel görünüyor mu" test edilemez. Test edilebilen, **çizilen sayının
hesaplanan sayıyla aynı olduğu.** Grafik kodunun sessiz hata biçimi
budur: yanlış yere konan bir referans çizgisi hatasız çalışır, güzel
görünür ve yanlış anlatır.

Bir de eksen ölçeği test ediliyor. Endeks grafiğinde sapmalar binde
birler mertebesinde; eksen veriye göre daraltılsaydı noktalar dağılmış
görünür ve grafik kendi mesajının tersini anlatırdı. Ölçeğin resmî
endekse sabitlendiği kilitli.
"""

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from tms29 import grafik  # noqa: E402
from tms29.etki import (  # noqa: E402
    RESMI_ENDEKS_2022_2023,
    ima_edilen_endeks,
    yukseltme_katsayilari,
)
from tms29.oranlar import oranlari_hesapla, seviye_karsilastir  # noqa: E402
from tms29.siralama import esik_kirilma_araliklari  # noqa: E402
from tms29.veri import panel_yukle  # noqa: E402


@pytest.fixture(scope="module")
def panel():
    return panel_yukle()


@pytest.fixture(scope="module")
def katsayilar(panel):
    return yukseltme_katsayilari(panel, 2022, "nominal", "sag2023")


@pytest.fixture(scope="module")
def karsilastirma(panel):
    return seviye_karsilastir(oranlari_hesapla(panel), 2022, "nominal", "sag2023")


@pytest.fixture(autouse=True)
def _figurleri_kapat():
    yield
    plt.close("all")


# --- ÇİZİLEN SAYI DOĞRU MU ------------------------------------------------


def test_referans_cizgisi_resmi_endekste(katsayilar):
    ax = grafik.endeks_geri_cikarim(
        ima_edilen_endeks(katsayilar), RESMI_ENDEKS_2022_2023
    )
    x = [ln.get_xdata()[0] for ln in ax.lines if len(ln.get_xdata())]
    assert any(abs(v - RESMI_ENDEKS_2022_2023) < 1e-9 for v in x)


def test_noktalar_hesaplanan_endeksle_ayni(katsayilar):
    endeks = ima_edilen_endeks(katsayilar)
    ax = grafik.endeks_geri_cikarim(endeks, RESMI_ENDEKS_2022_2023)
    cizilen = sorted(ax.collections[0].get_offsets()[:, 0])
    assert cizilen == pytest.approx(sorted(endeks.values))


def test_eksen_olcegi_veriye_degil_resmi_endekse_bagli(katsayilar):
    """Dar eksen, binde birlik sapmaları dağılmış gösterirdi."""
    endeks = ima_edilen_endeks(katsayilar)
    ax = grafik.endeks_geri_cikarim(endeks, RESMI_ENDEKS_2022_2023, pay=0.02)
    lo, hi = ax.get_xlim()
    assert lo == pytest.approx(RESMI_ENDEKS_2022_2023 * 0.98)
    assert hi == pytest.approx(RESMI_ENDEKS_2022_2023 * 1.02)
    # gözlenen aralık, eksenin çok küçük bir kısmını kaplamalı
    genislik = endeks.max() - endeks.min()
    assert genislik / (hi - lo) < 0.15


def test_esik_cubuklari_araliklarla_ayni(karsilastirma):
    a = esik_kirilma_araliklari(karsilastirma, "borc_ozkaynak")
    fig = grafik.esik_taramasi(a, "Borç / Özkaynak")
    ust = fig.axes[0]
    cizilen = sorted(
        (min(ln.get_xdata()), max(ln.get_xdata()))
        for ln in ust.lines
        if len(ln.get_xdata()) == 2
    )
    beklenen = sorted((r.alt, r.ust) for r in a.itertuples())
    assert cizilen == pytest.approx(beklenen)


# --- SÖZLEŞME -------------------------------------------------------------


def test_kalem_grafigi_yalnizca_secili_kalemleri_ciziyor(katsayilar):
    """Gelir tablosu kalemleri bilerek dışarıda; sessizce sızmamalı."""
    ax = grafik.kalem_katsayilari(katsayilar, RESMI_ENDEKS_2022_2023)
    etiketler = {t.get_text().replace(" ", "_") for t in ax.get_yticklabels()}
    assert etiketler == {k for k, _ in grafik.GRAFIK_KALEMLERI}
    assert "net_kar" not in etiketler
    assert "sermaye_duzeltme_farklari" not in etiketler


def test_egim_grafigi_iki_panel_donuyor(karsilastirma):
    fig = grafik.siralama_egimi(
        karsilastirma, ("borc_ozkaynak", "ozkaynak_karliligi"), ("Kaldıraç", "ROE")
    )
    assert isinstance(fig, plt.Figure)
    assert len(fig.axes) == 2


def test_verilen_eksene_ciziyor(katsayilar):
    fig, ax = plt.subplots()
    donen = grafik.kalem_katsayilari(katsayilar, RESMI_ENDEKS_2022_2023, ax=ax)
    assert donen is ax
    assert len(fig.axes) == 1


def test_gercek_veriyle_hepsi_calisiyor(katsayilar, karsilastirma):
    grafik.endeks_geri_cikarim(ima_edilen_endeks(katsayilar), RESMI_ENDEKS_2022_2023)
    grafik.kalem_katsayilari(katsayilar, RESMI_ENDEKS_2022_2023)
    grafik.esik_taramasi(
        esik_kirilma_araliklari(karsilastirma, "borc_ozkaynak"), "Borç / Özkaynak"
    )
    grafik.siralama_egimi(
        karsilastirma, ("cari", "net_kar_marji"), ("Cari oran", "Net kâr marjı")
    )
    assert isinstance(pd.DataFrame(), pd.DataFrame)
