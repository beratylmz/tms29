"""TMS 29 etki analizi — enflasyon muhasebesi oranları ne kadar değiştiriyor?"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

from tms29.cikar import calisma_kitabini_cikar
from tms29.dogrula import Ihlal, kapsama_raporu, kimlikleri_dogrula
from tms29.kalemler import ESLEME, ZORUNLU, esle, genis, normalize
from tms29.kavramlar import (
    ILK_DUZELTME_YILI,
    PARASAL,
    PARASAL_OLMAYAN,
    fiyat_seviyesi_ayristir,
)

try:
    __version__ = _version("tms29")
except PackageNotFoundError:  # depo içinden, kurulmadan
    __version__ = "0.0.0+local"

__all__ = [
    "ESLEME",
    "ILK_DUZELTME_YILI",
    "PARASAL",
    "PARASAL_OLMAYAN",
    "ZORUNLU",
    "Ihlal",
    "__version__",
    "calisma_kitabini_cikar",
    "esle",
    "fiyat_seviyesi_ayristir",
    "genis",
    "kapsama_raporu",
    "kimlikleri_dogrula",
    "normalize",
]
