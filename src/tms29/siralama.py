"""Düzeltmenin sıralama ve eşik kararlarına etkisi.

İki ayrı soru, iki ayrı cevap
-----------------------------
1. **Göreli karşılaştırma** (sıralama) düzeltmeden etkileniyor mu?
   Spearman sıra korelasyonu ve yer değiştiren çiftlerle ölçülüyor.

2. **Mutlak eşik kararları** etkileniyor mu? Kredi politikaları
   "Borç/Özkaynak 1,5'i geçerse reddet" gibi eşiklerle çalışır.

İkincisinde eşik seçimi tuzaktır
--------------------------------
Tek bir eşik seçip "bak, burada kırılıyor" demek, sonucu veren eşiği
seçmek olur -- yol haritasında senaryo seçiciliği diye işaretlediğimiz
hatanın aynısı. Bunun yerine **bütün eşik uzayı** taranıyor.

Mekanik basit: bir şirketin nominal değeri a, düzeltilmiş değeri b ise,
(min(a,b), max(a,b)) aralığındaki **her** eşik o şirketin kararını
çevirir. Bu aralıkların birleşimi, muhasebe tercihinin en az bir kararı
değiştirdiği bölgedir. Seçim yok, tarama var.
"""

from __future__ import annotations

import itertools

import pandas as pd
from scipy import stats


def siralama_kaymasi(karsilastirma: pd.DataFrame) -> pd.DataFrame:
    """Her oran için sıra korelasyonu ve yer değiştiren çift sayısı.

    Parameters
    ----------
    karsilastirma
        `oranlar.seviye_karsilastir` çıktısı: sirket, oran, a, b, degisim.
    """
    satirlar = []
    for oran, d in karsilastirma.groupby("oran"):
        d = d.sort_values("sirket")
        if len(d) < 3:
            continue
        rho = stats.spearmanr(d.a, d.b).statistic
        ters = [
            (x.sirket, y.sirket)
            for x, y in itertools.combinations(d.itertuples(), 2)
            if (x.a - y.a) * (x.b - y.b) < 0
        ]
        satirlar.append(
            dict(
                oran=oran,
                spearman=float(rho),
                yer_degistiren_cift=len(ters),
                toplam_cift=len(d) * (len(d) - 1) // 2,
                ciftler="; ".join(f"{a}<->{b}" for a, b in ters),
                en_buyuk_degisim=float(d.degisim.abs().max()),
                ortalama_degisim=float(d.degisim.mean()),
            )
        )
    return pd.DataFrame(satirlar).sort_values("spearman")


def esik_kirilma_araliklari(karsilastirma: pd.DataFrame, oran: str) -> pd.DataFrame:
    """Her şirket için kararı çeviren eşik aralığı.

    Bu aralıktaki herhangi bir eşik, aynı şirket ve aynı yıl için
    nominal ve düzeltilmiş rakamlara göre **farklı** karar üretir.
    """
    d = karsilastirma[karsilastirma.oran == oran]
    return pd.DataFrame(
        [
            dict(
                sirket=r.sirket,
                alt=min(r.a, r.b),
                ust=max(r.a, r.b),
                genislik=abs(r.b - r.a),
                yon="düzeltme iyileştiriyor"
                if r.b < r.a
                else "düzeltme kötüleştiriyor",
            )
            for r in d.itertuples()
        ]
    ).sort_values("alt")


def esik_tarama(karsilastirma: pd.DataFrame, oran: str, adim: int = 2000) -> dict:
    """Eşik uzayının ne kadarında karar değişiyor.

    Gözlenen değer aralığı `adim` noktaya bölünüyor ve her noktada kaç
    şirketin kararının çevrildiği sayılıyor. Böylece tek bir eşik
    seçmeden, "muhasebe tercihi kararı ne sıklıkla değiştirir" sorusuna
    seçimden bağımsız bir cevap veriliyor.
    """
    import numpy as np

    araliklar = esik_kirilma_araliklari(karsilastirma, oran)
    if araliklar.empty:
        return {}
    lo = float(min(araliklar.alt))
    hi = float(max(araliklar.ust))
    izgara = np.linspace(lo, hi, adim)
    etkilenen = np.zeros(adim, dtype=int)
    for r in araliklar.itertuples():
        etkilenen += ((izgara > r.alt) & (izgara < r.ust)).astype(int)

    return {
        "oran": oran,
        "taranan_alt": lo,
        "taranan_ust": hi,
        "en_az_bir_karar_degisiyor": float((etkilenen >= 1).mean()),
        "azami_etkilenen_sirket": int(etkilenen.max()),
        "ortalama_etkilenen_sirket": float(etkilenen.mean()),
    }


def makas_aciklayici_mi(
    karsilastirma: pd.DataFrame, ayrisim: pd.DataFrame, oran: str
) -> dict:
    """Parasal/parasal olmayan makası, oran değişimini açıklıyor mu?

    Mekanizma doğruysa, makası açık olan şirkette oran daha çok
    değişmeli. n = 7 olduğu için bu bir hipotez testi değil, tutarlılık
    kontrolüdür -- p-değeri raporlanıyor ama üzerine karar kurulmuyor.
    """
    d = (
        karsilastirma[karsilastirma.oran == oran]
        .merge(ayrisim[["sirket", "makas"]], on="sirket")
        .dropna(subset=["makas", "degisim"])
    )
    if len(d) < 4:
        return {}
    r = stats.spearmanr(d.makas, d.degisim.abs())
    return {
        "oran": oran,
        "n": len(d),
        "spearman": float(r.statistic),
        "p": float(r.pvalue),
        "not": "n=7; yön göstergesi, hipotez testi değil",
    }
