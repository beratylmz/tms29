"""Dondurulmuş veri setini yükler. Ağ ve Excel gerektirmez."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_KOK = Path(__file__).resolve().parents[2]
HAM_YOL = _KOK / "veri" / "ham_cikarim.csv.gz"
KAYNAK_YOL = _KOK / "veri" / "kaynak_fsa.xlsx"


def ham_yukle() -> pd.DataFrame:
    """Kayıpsız çıkarımın dondurulmuş hâli (uzun biçim)."""
    if not HAM_YOL.exists():  # pragma: no cover
        raise FileNotFoundError(
            f"Veri bulunamadı: {HAM_YOL}\n"
            'Depo kökünden pip install -e "." ile kurulduğundan emin ol.'
        )
    return pd.read_csv(HAM_YOL)


def panel_yukle():
    """Eşlenmiş, geniş biçimli panel: (şirket, yıl, seviye) x kalem."""
    from tms29.kalemler import esle, genis

    eslenen, _ = esle(ham_yukle())
    return genis(eslenen)
