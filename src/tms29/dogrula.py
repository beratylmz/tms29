"""Muhasebe kimliklerini doğrular.

Neden gerekli
-------------
Bu veri, denetim raporlarından **elle** çıkarıldı. Elle çıkarımın tipik
hatası bir satırı atlamak ya da yanlış kolona yazmaktır; ikisi de
sessizdir. Bilanço kimliği bunları yakalar: alt toplamlar tutmuyorsa
bir yerde bir kalem kayıp demektir.

Tolerans neden sıfır değil
--------------------------
Kaynak tutarlar bin TL'ye yuvarlanmış; alt toplamlar bu yuvarlanmış
rakamlardan üretildiği için birkaç birimlik sapma normaldir. Mutlak
eşiğin (bin TL) yanında **oransal** bir eşik de kullanılıyor, çünkü
233 milyar ₺'lik bir bilançoda 5 birimlik sapma ile 5 milyonluk sapma
aynı şey değil.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: Bir kimliğin tuttuğu kabul edilmesi için izin verilen bağıl sapma.
TOLERANS = 0.005  # %0,5

#: Bağıl sapmanın anlamsızlaştığı küçük tutarlar için mutlak taban (bin TL).
MUTLAK_TABAN = 50.0

KIMLIKLER = {
    "varlık toplamı": (["donen_varlik", "duran_varlik"], "toplam_varlik"),
    "yükümlülük toplamı": (["kv_yukumluluk", "uv_yukumluluk"], "toplam_yukumluluk"),
    "kaynak toplamı": (["toplam_yukumluluk", "ozkaynak"], "toplam_kaynak"),
    "bilanço dengesi": (["toplam_varlik"], "toplam_kaynak"),
}


@dataclass(frozen=True)
class Ihlal:
    """Tutmayan tek bir kimlik."""

    sirket: str
    yil: int
    seviye: str
    kimlik: str
    beklenen: float
    bulunan: float

    @property
    def bagil(self) -> float:
        return abs(self.bulunan - self.beklenen) / max(abs(self.beklenen), 1.0)

    def __str__(self) -> str:
        return (
            f"{self.sirket} {self.yil} {self.seviye}: {self.kimlik} — "
            f"beklenen {self.beklenen:,.0f}, bulunan {self.bulunan:,.0f} "
            f"({self.bagil:.2%})"
        )


def kimlikleri_dogrula(genis_df: pd.DataFrame) -> list[Ihlal]:
    """Her satırda her kimliği sınar, tutmayanları döndürür."""
    ihlaller: list[Ihlal] = []
    for _, r in genis_df.iterrows():
        for ad, (parcalar, toplam) in KIMLIKLER.items():
            if any(pd.isna(r.get(p)) for p in parcalar) or pd.isna(r.get(toplam)):
                continue
            beklenen = sum(float(r[p]) for p in parcalar)
            bulunan = float(r[toplam])
            fark = abs(bulunan - beklenen)
            if fark <= MUTLAK_TABAN:
                continue
            if fark / max(abs(beklenen), 1.0) <= TOLERANS:
                continue
            ihlaller.append(
                Ihlal(r.sirket, int(r.yil), r.seviye, ad, beklenen, bulunan)
            )
    return ihlaller


def kapsama_raporu(genis_df: pd.DataFrame) -> pd.DataFrame:
    """Hangi şirket-yıl için hangi fiyat seviyeleri mevcut.

    Projenin ölçümü aynı yılın iki seviyede bulunmasına dayandığı için
    bu tablo, neyin ölçülebilir olduğunu doğrudan söylüyor.
    """
    t = (
        genis_df.groupby(["sirket", "yil"])["seviye"]
        .apply(lambda s: sorted(set(s)))
        .reset_index(name="seviyeler")
    )
    t["seviye_sayisi"] = t.seviyeler.map(len)
    t["olculebilir"] = t.seviye_sayisi >= 2
    return t
