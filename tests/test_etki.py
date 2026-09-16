"""Düzeltme mekanizması testleri — bu projenin analitik çıpası burada.

En önemlisi `test_ima_edilen_endeks_resmi_rakamla_uyusuyor`. Fikir şu:
parasal kalemler tanım gereği yalnızca bilanço tarihinden itibaren
endekslenir, dolayısıyla katsayıları **resmî TÜFE endeks oranına eşit
olmak zorundadır.** Yani veriden enflasyon endeksi geri çıkarılabilir.

Yedi şirketin denetim raporundan elle çıkarılmış veri, birbirinden
bağımsız olarak aynı endeksi veriyor ve resmî rakamı tutturuyorsa, hem
veri hem de parasal/parasal olmayan kavrayışı doğrulanmış olur. Bu
test kırmızıya dönerse projenin dayandığı zemin gitmiş demektir.
"""

import pytest

from tms29.etki import (
    RESMI_ENDEKS_2022_2023,
    ima_edilen_endeks,
    parasal_aykiriliklar,
    parasal_ayrisim,
    yukseltme_katsayilari,
)
from tms29.veri import panel_yukle


@pytest.fixture(scope="module")
def katsayilar():
    return yukseltme_katsayilari(panel_yukle(), 2022, "nominal", "sag2023")


# --- DIŞ ÇIPA -------------------------------------------------------------


def test_ima_edilen_endeks_resmi_rakamla_uyusuyor(katsayilar):
    """Veriden çıkan endeks, TÜİK'in açıkladığı %64,77 ile uyuşmalı."""
    endeks = ima_edilen_endeks(katsayilar)
    sapma = abs(endeks.mean() - RESMI_ENDEKS_2022_2023) / RESMI_ENDEKS_2022_2023
    assert sapma < 0.005, (
        f"ima edilen {endeks.mean():.4f}, resmî {RESMI_ENDEKS_2022_2023}"
    )


def test_yedi_sirket_ayni_endeksi_veriyor(katsayilar):
    """Bağımsız yedi kaynak aynı sayıyı vermeli; vermiyorsa veri kusurlu."""
    endeks = ima_edilen_endeks(katsayilar)
    assert len(endeks) == 7
    assert endeks.std() / endeks.mean() < 0.01


# --- MEKANİZMA ------------------------------------------------------------


def test_parasal_olmayan_her_sirkette_daha_cok_yukseliyor(katsayilar):
    """Düzeltmenin tanımı bu. Tersi çıkarsa sınıflandırma yanlıştır."""
    t = parasal_ayrisim(katsayilar)
    assert len(t) == 7
    assert (t.makas > 1.0).all(), t[t.makas <= 1.0]


def test_odenmis_sermaye_duzeltilmiyor(katsayilar):
    """Nominal sermaye olduğu gibi kalır; düzeltme ayrı bir kaleme yazılır.

    Türkiye uygulamasında düzeltme farkı 'Sermaye Düzeltme Farkları'
    satırında birikir -- aşağıdaki test onu kontrol ediyor.
    """
    d = katsayilar[katsayilar.kalem == "odenmis_sermaye"]
    assert len(d) == 7
    assert (d.katsayi - 1.0).abs().max() < 1e-9


def test_sermaye_duzeltme_farki_duzeltmeyle_buyuyor():
    """Bu kalem düzeltmenin kendisidir ve düzeltilmiş sunumda patlar.

    İlk yazdığım hâli "nominal sunumda sıfır olmalı" diyordu ve test
    kırmızı döndü. Sebep veri hatası değil, tarih: Türkiye 2003-2004'te
    de enflasyon muhasebesi uygulamıştı (VUK mükerrer 298). O dönemin
    düzeltme farkı, o yıllarda faaliyette olan şirketlerin özkaynağında
    kalıcı bir bakiye olarak duruyor. ENJSA, ZOREN ve AKSEN'de var;
    sonradan halka açılanlarda (GWIND 2021, AYDEM 2020) yok.

    Doğru iddia şu: düzeltilmiş sunumda yedi şirkette de pozitif, ve
    nominal bakiyeden kat kat büyük.
    """
    panel = panel_yukle()
    n = panel[(panel.yil == 2022) & (panel.seviye == "nominal")].set_index("sirket")
    d = panel[(panel.yil == 2022) & (panel.seviye == "sag2023")].set_index("sirket")

    assert (d.sermaye_duzeltme_farklari > 0).all(), "düzeltilmiş sunumda hepsi pozitif"
    for s in d.index:
        eski = float(n.loc[s, "sermaye_duzeltme_farklari"] or 0)
        yeni = float(d.loc[s, "sermaye_duzeltme_farklari"])
        assert yeni > max(eski, 0), f"{s}: {eski:,.0f} -> {yeni:,.0f}"

    # Miras bakiyesi taşıyanlar, 2003-2004 döneminde faaliyetteki eski şirketler
    miras = set(n[n.sermaye_duzeltme_farklari.fillna(0) > 0].index)
    assert miras == {"AKSEN", "ENJSA", "ZOREN"}


# --- AYKIRILIK RAPORLAMA --------------------------------------------------


def test_aykiri_parasal_kalemler_yutulmuyor(katsayilar):
    """Endekse uymayan parasal kalem ortalamaya karışmamalı, raporlanmalı.

    Veride iki tane var (GWIND ve ZOREN ticari borçları). İkisi de iki
    sunum arasında yeniden sınıflandırılmış olabilir; kaynağa bakmadan
    karar verilemez, o yüzden düzeltilmiyor -- işaretleniyor.
    """
    a = parasal_aykiriliklar(katsayilar)
    assert set(a.kalem) <= {"ticari_borc"}
    assert "GWIND" in set(a.sirket)
    # aykırılar çıkarıldıktan sonra parasal medyan endekse oturmalı
    t = parasal_ayrisim(katsayilar)
    assert (t.parasal - ima_edilen_endeks(katsayilar).mean()).abs().max() < 0.01
