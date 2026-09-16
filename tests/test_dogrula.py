"""Veri bütünlüğü ve projenin analitik çıpası.

İki ayrı iş yapıyor:

1. **Muhasebe kimlikleri.** Veri denetim raporlarından elle çıkarıldı;
   atlanan bir satır ya da yanlış kolona yazılmış bir tutar sessiz
   hatadır. Bilanço kimliği bunları yakalar.

2. **Kontrol testi (analitik çıpa).** Projenin bütün iddiası "enflasyon
   düzeltmesi oranları değiştirir" üzerine kurulu. Ama bu yalnızca
   düzeltme *düzgün bir çarpma olmadığı için* doğru. Zaten düzeltilmiş
   iki fiyat seviyesi arasındaki geçiş (2023 SAG -> 2024 SAG) düzgün bir
   çarpmadır ve hiçbir oranı değiştirmemelidir.

   Bu test tutmazsa ya veri bozuktur ya kavrayışım yanlıştır; ikisi de
   projeyi durdurur. mcvar'daki analitik VaR çıpasının karşılığı budur:
   cevabı önceden bilinen bir durumda ölçüm aletini sınamak.
"""

import numpy as np
import pytest

from tms29.dogrula import kapsama_raporu, kimlikleri_dogrula
from tms29.veri import panel_yukle


@pytest.fixture(scope="module")
def panel():
    return panel_yukle()


# --- 1. VERİ BÜTÜNLÜĞÜ ----------------------------------------------------


def test_muhasebe_kimlikleri_tutuyor(panel):
    ihlaller = kimlikleri_dogrula(panel)
    assert not ihlaller, "\n".join(str(i) for i in ihlaller[:10])


def test_panel_beklenen_boyutta(panel):
    """7 şirket; kaza eseri bir şirket düşerse burada görünür."""
    assert sorted(panel.sirket.unique()) == [
        "AKSEN",
        "ASTOR",
        "AYDEM",
        "AYEN",
        "ENJSA",
        "GWIND",
        "ZOREN",
    ]
    assert len(panel) >= 60


def test_olculebilir_hucreler(panel):
    """Ölçüm, aynı yılın iki fiyat seviyesinde bulunmasına dayanıyor."""
    k = kapsama_raporu(panel)
    assert k.olculebilir.sum() == 21  # 7 şirket x 2022, 2023, 2024
    assert set(k[k.olculebilir].yil) == {2022, 2023, 2024}


def test_ozkaynak_pozitif(panel):
    """Negatif özkaynak, oranları anlamsızlaştırır; bu veride yok."""
    assert (panel.ozkaynak.dropna() > 0).all()


# --- 2. ANALİTİK ÇIPA -----------------------------------------------------


def _oranlar(satir):
    return {
        "borc_ozkaynak": satir.toplam_yukumluluk / satir.ozkaynak,
        "cari": satir.donen_varlik / satir.kv_yukumluluk,
        "ozkaynak_varlik": satir.ozkaynak / satir.toplam_varlik,
    }


@pytest.mark.parametrize(
    "yil,a,b", [(2023, "sag2023", "sag2024"), (2024, "sag2024", "sag2025")]
)
def test_duzeltilmis_seviyeler_arasi_gecis_oran_notr(panel, yil, a, b):
    """İki SAG seviyesi arasındaki geçiş düzgün çarpmadır: oranlar sabit.

    Bu tutmazsa projenin ölçüm aleti bozuk demektir.
    """
    for sirket in panel.sirket.unique():
        x = panel[(panel.sirket == sirket) & (panel.yil == yil) & (panel.seviye == a)]
        y = panel[(panel.sirket == sirket) & (panel.yil == yil) & (panel.seviye == b)]
        if x.empty or y.empty:
            continue
        ox, oy = _oranlar(x.iloc[0]), _oranlar(y.iloc[0])
        for ad in ox:
            assert abs(oy[ad] - ox[ad]) / abs(ox[ad]) < 0.01, (
                f"{sirket} {yil} {ad}: {ox[ad]:.4f} -> {oy[ad]:.4f}"
            )


@pytest.mark.parametrize(
    "yil,a,b", [(2023, "sag2023", "sag2024"), (2024, "sag2024", "sag2025")]
)
def test_duzeltilmis_seviyeler_arasi_gecis_tek_katsayi(panel, yil, a, b):
    """Daha güçlü hâli: bütün kalemler *aynı* katsayıyla çarpılmış olmalı."""
    kalemler = [
        "toplam_varlik",
        "ozkaynak",
        "toplam_yukumluluk",
        "donen_varlik",
        "kv_yukumluluk",
    ]
    for sirket in panel.sirket.unique():
        x = panel[(panel.sirket == sirket) & (panel.yil == yil) & (panel.seviye == a)]
        y = panel[(panel.sirket == sirket) & (panel.yil == yil) & (panel.seviye == b)]
        if x.empty or y.empty:
            continue
        katsayilar = [y.iloc[0][k] / x.iloc[0][k] for k in kalemler]
        assert np.std(katsayilar) / np.mean(katsayilar) < 0.01, (
            f"{sirket} {yil}: katsayılar tek değil -> {katsayilar}"
        )


def test_nominal_gecis_oranlari_gercekten_degistiriyor(panel):
    """Karşıt test: 2022 nominal -> ilk düzeltme oranları DEĞİŞTİRMELİ.

    Yukarıdaki iki test 'değişmemeli' diyor. Bu test olmasa, her şeyi
    sabit döndüren bozuk bir ölçüm aleti de o testleri geçerdi.
    """
    degisimler = []
    for sirket in panel.sirket.unique():
        x = panel[
            (panel.sirket == sirket) & (panel.yil == 2022) & (panel.seviye == "nominal")
        ]
        y = panel[
            (panel.sirket == sirket) & (panel.yil == 2022) & (panel.seviye == "sag2023")
        ]
        if x.empty or y.empty:
            continue
        ox, oy = _oranlar(x.iloc[0]), _oranlar(y.iloc[0])
        degisimler.append(
            abs(oy["borc_ozkaynak"] - ox["borc_ozkaynak"]) / ox["borc_ozkaynak"]
        )
    assert len(degisimler) == 7
    assert max(degisimler) > 0.10, f"beklenen değişim yok: {degisimler}"
