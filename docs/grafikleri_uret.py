"""README'deki dört grafiği üretir.

    python docs/grafikleri_uret.py

Zemin bilerek beyaz: GitHub hem açık hem koyu temada gösteriyor, saydam
zemin koyu temada eksen yazılarını görünmez yapardı.
"""

from __future__ import annotations

import matplotlib

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

ZEMIN = "#FFFFFF"


def kaydet(fig: plt.Figure, ad: str) -> None:
    fig.patch.set_facecolor(ZEMIN)
    for ax in fig.axes:
        ax.set_facecolor(ZEMIN)
    fig.savefig(f"docs/{ad}.png", dpi=160, bbox_inches="tight", facecolor=ZEMIN)
    plt.close(fig)
    print(f"docs/{ad}.png")


def main() -> None:
    panel = panel_yukle()
    katsayilar = yukseltme_katsayilari(panel, 2022, "nominal", "sag2023")
    karsilastirma = seviye_karsilastir(
        oranlari_hesapla(panel), 2022, "nominal", "sag2023"
    )

    fig, ax = plt.subplots(figsize=(8, 3.2))
    grafik.endeks_geri_cikarim(
        ima_edilen_endeks(katsayilar), RESMI_ENDEKS_2022_2023, ax=ax
    )
    kaydet(fig, "endeks-cipasi")

    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    grafik.kalem_katsayilari(katsayilar, RESMI_ENDEKS_2022_2023, ax=ax)
    kaydet(fig, "kalem-katsayilari")

    kaydet(
        grafik.esik_taramasi(
            esik_kirilma_araliklari(karsilastirma, "borc_ozkaynak"), "Borç / Özkaynak"
        ),
        "esik-taramasi",
    )

    kaydet(
        grafik.siralama_egimi(
            karsilastirma,
            ("borc_ozkaynak", "ozkaynak_karliligi"),
            ("Borç / Özkaynak", "Özkaynak kârlılığı (ROE)"),
        ),
        "siralama-egimi",
    )


if __name__ == "__main__":
    main()
