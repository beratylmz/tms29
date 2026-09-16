"""Düzeltmenin mekanizmasını ölçer.

Çekirdek fikir
--------------
TMS 29 bilançoyu düzgün bir katsayıyla büyütmez. Parasal kalemler
(nakit, alacak, borç) yalnızca bilanço tarihinden itibaren endekslenir;
parasal olmayan kalemler (maddi duran varlık, özkaynak) **edinme
tarihinden** itibaren. Aradaki fark bilançonun bileşimini değiştirir --
oranların değişme sebebi budur.

Bu modül o farkı doğrudan ölçüyor: her kalemin "yükseltme katsayısı",
düzeltilmiş değerin nominal değere oranı.

Dış çıpa
--------
Parasal kalemlerin katsayısı, tanım gereği resmî TÜFE endeks oranına
eşit olmalıdır. Yani veriden **enflasyon endeksi geri çıkarılabilir** --
ve resmî rakamla karşılaştırılabilir. Yedi şirketin denetim raporundan
elle çıkarılmış veri, bağımsız olarak aynı endeksi veriyorsa, hem veri
hem kavrayış doğrulanmış olur.

Bu, mcvar'daki analitik VaR çıpasının karşılığı: cevabı dışarıdan
bilinen bir büyüklüğü ölçüp tutturmak.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: TÜİK, 2023 yıllık TÜFE enflasyonu %64,77 -> Ara.2022 / Ara.2023 endeks oranı.
#: Kaynak: TÜİK Tüketici Fiyat Endeksi, Aralık 2023 bülteni.
RESMI_ENDEKS_2022_2023 = 1.6477

#: Katsayısı endekse eşit çıkması beklenen kalemler (saf parasal).
CIPA_KALEMLERI = ("nakit", "kv_yukumluluk")


def yukseltme_katsayilari(
    panel: pd.DataFrame, yil: int, nominal: str, duzeltilmis: str
) -> pd.DataFrame:
    """Her şirket ve kalem için düzeltilmiş / nominal oranı.

    1,0'a yakın katsayı "düzeltilmedi", endekse yakın katsayı "yalnızca
    bilanço tarihinden endekslendi", endeksten büyük katsayı "edinme
    tarihinden endekslendi" demektir.
    """
    sayisal = [c for c in panel.columns if c not in ("sirket", "yil", "seviye")]
    satirlar = []
    for s in sorted(panel.sirket.unique()):
        n = panel[(panel.sirket == s) & (panel.yil == yil) & (panel.seviye == nominal)]
        d = panel[
            (panel.sirket == s) & (panel.yil == yil) & (panel.seviye == duzeltilmis)
        ]
        if n.empty or d.empty:
            continue
        n, d = n.iloc[0], d.iloc[0]
        for k in sayisal:
            if pd.isna(n[k]) or pd.isna(d[k]) or n[k] == 0:
                continue
            satirlar.append(
                dict(
                    sirket=s,
                    kalem=k,
                    nominal=float(n[k]),
                    duzeltilmis=float(d[k]),
                    katsayi=float(d[k]) / float(n[k]),
                )
            )
    return pd.DataFrame(satirlar)


def ima_edilen_endeks(katsayi_df: pd.DataFrame) -> pd.Series:
    """Parasal kalemlerden enflasyon endeksini geri çıkarır.

    Her şirket için ayrı bir tahmin üretiyor. Yedi tahmin birbirine
    yakın değilse ya veri hatalıdır ya da bir kalem yanlış
    sınıflandırılmıştır.
    """
    d = katsayi_df[katsayi_df.kalem.isin(CIPA_KALEMLERI)]
    return d.groupby("sirket")["katsayi"].median()


#: Parasal bir kalemin endeksten sapabileceği azami oran. Bunun üstü,
#: kalem sınıflandırmasının ya da çıkarımın sorgulanması gerektiğini söyler.
PARASAL_SAPMA_TAVANI = 0.02


def parasal_aykiriliklar(katsayi_df: pd.DataFrame) -> pd.DataFrame:
    """Endekse uyması beklenirken uymayan parasal kalemleri bulur.

    Parasal bir kalemin katsayısı tanım gereği endekse eşit olmalı.
    Değilse üç ihtimal var: kalem aslında parasal değil, iki sunum
    arasında yeniden sınıflandırılmış, ya da çıkarımda hata var.

    Bunları ortalamanın içinde eritmek yerine ayrıca döndürüyoruz --
    aykırılık, bulgudur; gürültü değil.
    """
    from tms29.kavramlar import PARASAL

    endeks = ima_edilen_endeks(katsayi_df)
    d = katsayi_df[katsayi_df.kalem.isin(PARASAL)].copy()
    d["beklenen"] = d.sirket.map(endeks)
    d["sapma"] = (d.katsayi - d.beklenen) / d.beklenen
    return (
        d[d.sapma.abs() > PARASAL_SAPMA_TAVANI]
        .sort_values("sapma", key=abs, ascending=False)
        .reset_index(drop=True)
    )


def parasal_ayrisim(katsayi_df: pd.DataFrame) -> pd.DataFrame:
    """Şirket başına parasal ve parasal olmayan katsayı ortalamaları.

    Aradaki makas, o şirkette düzeltmenin ne kadar ısırdığını gösterir:
    varlıkları ne kadar eskiyse makas o kadar açık.
    """
    from tms29.kavramlar import PARASAL, PARASAL_OLMAYAN

    # Aykırı parasal kalemler ortalamaya girmiyor; ayrıca raporlanıyorlar.
    aykiri = parasal_aykiriliklar(katsayi_df)
    aykiri_anahtar = set(zip(aykiri.sirket, aykiri.kalem, strict=True))
    d = katsayi_df[
        ~katsayi_df.apply(lambda r: (r.sirket, r.kalem) in aykiri_anahtar, axis=1)
    ].copy()
    d["sinif"] = np.where(
        d.kalem.isin(PARASAL),
        "parasal",
        np.where(d.kalem.isin(PARASAL_OLMAYAN), "parasal_olmayan", "karma"),
    )
    t = (
        d[d.sinif != "karma"]
        .pivot_table(
            index="sirket", columns="sinif", values="katsayi", aggfunc="median"
        )
        .reset_index()
    )
    t["makas"] = t.parasal_olmayan / t.parasal
    return t.sort_values("makas", ascending=False)


def parasal_kazanc_etkisi(
    panel: pd.DataFrame, yil: int, nominal: str, duzeltilmis: str
) -> pd.DataFrame:
    """TMS 29'un gelir tablosuna kattığı kalemin kâra etkisi.

    Nominal muhasebede böyle bir satır yoktur; düzeltmeyle birlikte
    sıfırdan belirir. İşareti şirketin **net parasal pozisyonuna**
    bağlıdır: net parasal borçlu enflasyondan kazanır (borcu reel olarak
    erir), net parasal alacaklı kaybeder.

    Kaldıraç tek başına yeterli gösterge değildir -- bu veride ENJSA
    yüksek kaldıraçlı olduğu hâlde kayıp yazıyor, çünkü imtiyaz
    sözleşmesi finansal varlıkları (TFRS Yorum 12) onu net parasal
    alacaklı yapıyor. Karşı örnek `tests/test_siralama.py`'de kilitli.
    """
    n = panel[(panel.yil == yil) & (panel.seviye == nominal)].set_index("sirket")
    d = panel[(panel.yil == yil) & (panel.seviye == duzeltilmis)].set_index("sirket")
    ortak = sorted(set(n.index) & set(d.index))
    return pd.DataFrame(
        {
            "sirket": ortak,
            "kaldirac_nominal": [
                n.loc[s, "toplam_yukumluluk"] / n.loc[s, "ozkaynak"] for s in ortak
            ],
            "parasal_kazanc": [d.loc[s, "net_parasal_pozisyon"] for s in ortak],
            "kazanc_ozkaynaga": [
                d.loc[s, "net_parasal_pozisyon"] / d.loc[s, "ozkaynak"] for s in ortak
            ],
            "kar_katsayisi": [d.loc[s, "net_kar"] / n.loc[s, "net_kar"] for s in ortak],
        }
    ).sort_values("kazanc_ozkaynaga")
