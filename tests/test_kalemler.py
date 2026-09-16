"""Kanonik eşleme testleri.

En kritik test, birbirine çok benzeyen iki kalemin karışmadığını
doğrulayan olan: "TOPLAM YÜKÜMLÜLÜKLER" ile "TOPLAM YÜKÜMLÜLÜKLER VE
ÖZKAYNAKLAR" bir harf farkıyla yazılıyor ama tamamen farklı iki
büyüklük. Bulanık eşleştirme kullansaydık bunlar karışırdı ve bilanço
dengesi bozulurdu -- üstelik hiçbir yerde hata vermeden.
"""

import pandas as pd

from tms29.kalemler import ZORUNLU, esle, genis, normalize
from tms29.veri import ham_yukle


def test_normalize_turkce_buyuk_harf_tuzagi():
    """'İ' ve 'I' karışırsa TİCARİ ile TICARI eşleşmez."""
    assert normalize("Ticari Borçlar") == normalize("TİCARİ BORÇLAR")
    assert normalize("Nakit ve Nakit Benzerleri (Cash & equivalents)") == normalize(
        "NAKİT VE NAKİT BENZERLERİ"
    )


def test_normalize_ingilizce_karsiligi_atiyor():
    assert normalize("Hasılat (Net Revenue)") == "HASILAT"
    assert normalize("VARLIKLAR / ASSETS") == "VARLIKLAR"


def test_benzer_iki_kalem_karismiyor():
    """Projenin en tehlikeli eşleme hatası."""
    df = pd.DataFrame(
        {
            "ham_etiket": [
                "TOPLAM YÜKÜMLÜLÜKLER",
                "TOPLAM YÜKÜMLÜLÜKLER VE ÖZKAYNAKLAR",
            ],
            "blok": ["mutlak"] * 2,
            "sirket": ["X"] * 2,
            "tablo": ["bilanco"] * 2,
            "yil": [2022] * 2,
            "seviye": ["nominal"] * 2,
            "deger": [100.0, 180.0],
        }
    )
    eslenen, _ = esle(df)
    kalemler = set(eslenen.kalem)
    assert kalemler == {"toplam_yukumluluk", "toplam_kaynak"}
    assert len(kalemler) == 2  # ikisi tek bir kaleme çökmedi


def test_taninmayan_etiket_sessizce_dusmuyor():
    df = pd.DataFrame(
        {
            "ham_etiket": ["Uydurma Kalem"],
            "blok": ["mutlak"],
            "sirket": ["X"],
            "tablo": ["bilanco"],
            "yil": [2022],
            "seviye": ["nominal"],
            "deger": [1.0],
        }
    )
    eslenen, eslenmeyen = esle(df)
    assert len(eslenen) == 0
    assert "Uydurma Kalem" in eslenmeyen.index


def test_zorunlu_kalemler_her_sirkette_var():
    """Bir şirkette eksik kalem, o şirketin analizden sessizce düşmesi demek."""
    panel = genis(esle(ham_yukle())[0])
    eksikler = {}
    for sirket in panel.sirket.unique():
        d = panel[panel.sirket == sirket]
        yok = [k for k in dict.fromkeys(ZORUNLU) if d[k].notna().sum() == 0]
        if yok:
            eksikler[sirket] = yok
    assert not eksikler, f"eksik kalemler: {eksikler}"
