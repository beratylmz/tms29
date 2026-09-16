"""Oran motoru.

Tasarım kararı: oranlar fiyat seviyesinden habersiz
--------------------------------------------------
Her oran yalnızca bir bilanço satırı alıyor ve o satırın hangi fiyat
seviyesinde olduğunu bilmiyor. Böylece aynı fonksiyon nominal ve
düzeltilmiş rakamlarda çalışıyor -- karşılaştırma "elmayla elma" oluyor.

mcvar'daki `metrics.py` ile aynı ilke: ölçüm, senaryonun kaynağından
bağımsız olmalı. Oran hesabına "eğer düzeltilmişse şunu yap" gibi bir
dal koysaydık, ölçtüğümüz fark kısmen kendi kodumuzdan gelirdi.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

#: oran adı -> (hesap, açıklama)
ORANLAR: dict[str, tuple[Callable[[pd.Series], float], str]] = {
    "borc_ozkaynak": (
        lambda r: r.toplam_yukumluluk / r.ozkaynak,
        "Kaldıraç. Kredi kararlarında eşik olarak en sık kullanılan oran.",
    ),
    "cari": (
        lambda r: r.donen_varlik / r.kv_yukumluluk,
        "Kısa vadeli likidite. Payda da paydaki da ağırlıklı parasal.",
    ),
    "ozkaynak_varlik": (
        lambda r: r.ozkaynak / r.toplam_varlik,
        "Sermaye yeterliliği. Parasal olmayan ağırlığına duyarlı.",
    ),
    "duran_varlik_yogunlugu": (
        lambda r: r.duran_varlik / r.toplam_varlik,
        "Varlık yoğunluğu. Düzeltmenin etkisini belirleyen asıl değişken.",
    ),
    "net_kar_marji": (
        lambda r: r.net_kar / r.hasilat,
        "Kârlılık. Gelir tablosu kalemleri farklı endekslenir.",
    ),
    "ozkaynak_karliligi": (
        lambda r: r.net_kar / r.ozkaynak,
        "ROE. Payda düzeltmeden en çok etkilenen büyüklük.",
    ),
}


def oranlari_hesapla(panel: pd.DataFrame) -> pd.DataFrame:
    """Panelin her satırı için bütün oranları hesaplar.

    Gerekli kalemi eksik olan satırda o oran NaN kalır; satır düşürülmez,
    çünkü diğer oranlar hâlâ geçerlidir.
    """
    cikti = panel[["sirket", "yil", "seviye"]].copy()
    for ad, (hesap, _) in ORANLAR.items():
        degerler = []
        for _, r in panel.iterrows():
            try:
                v = float(hesap(r))
                degerler.append(v if pd.notna(v) else None)
            except (TypeError, ZeroDivisionError, AttributeError):
                degerler.append(None)
        cikti[ad] = degerler
    return cikti


def seviye_karsilastir(oran_df: pd.DataFrame, yil: int, a: str, b: str) -> pd.DataFrame:
    """Aynı yılın iki fiyat seviyesindeki oranlarını yan yana koyar.

    Returns
    -------
    DataFrame
        sirket, oran, `a` seviyesindeki değer, `b` seviyesindeki değer,
        ve bağıl değişim.
    """
    x = oran_df[(oran_df.yil == yil) & (oran_df.seviye == a)].set_index("sirket")
    y = oran_df[(oran_df.yil == yil) & (oran_df.seviye == b)].set_index("sirket")
    ortak = sorted(set(x.index) & set(y.index))
    satirlar = []
    for oran in ORANLAR:
        for s in ortak:
            ilk, son = x.loc[s, oran], y.loc[s, oran]
            if pd.isna(ilk) or pd.isna(son) or ilk == 0:
                continue
            satirlar.append(
                dict(
                    sirket=s,
                    oran=oran,
                    a=float(ilk),
                    b=float(son),
                    degisim=float((son - ilk) / abs(ilk)),
                )
            )
    return pd.DataFrame(satirlar)
