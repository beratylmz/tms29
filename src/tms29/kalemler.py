"""Ham etiketleri kanonik kalem adlarına çevirir.

Neden açık tablo, neden bulanık eşleştirme değil
------------------------------------------------
Yedi şirket aynı kalemi farklı yazıyor: "KV YÜKÜMLÜLÜKLER TOPLAM" ve
"KISA VADELİ YÜKÜMLÜLÜKLER TOPLAM" aynı şey. Bunu benzerlik skoruyla
çözmek cazip ama tehlikeli: "TOPLAM YÜKÜMLÜLÜKLER" ile "TOPLAM
YÜKÜMLÜLÜKLER VE ÖZKAYNAKLAR" birbirine çok benzer ve **tamamen farklı**
iki büyüklüktür. Bulanık eşleştirme bunları karıştırdığında hiçbir yerde
hata vermez, sadece bilanço dengesi bozulur -- ve bozulduğunu görmek
için doğrulama katmanına ihtiyaç duyarsın.

Bu yüzden eşleme elle yazılmış, tam eşleşen bir tablo. Tanınmayan etiket
sessizce düşürülmüyor; `esle()` onları ayrıca döndürüyor.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd


def normalize(etiket: str) -> str:
    """Etiketi karşılaştırılabilir hâle getirir.

    - Parantez içi İngilizce karşılık atılır: "Hasılat (Net Revenue)" -> "HASILAT"
    - "/" sonrası atılır: "VARLIKLAR / ASSETS" -> "VARLIKLAR"
    - Türkçe büyük harf tuzağı: "İ" ve "ı" ayrı ayrı ele alınır, yoksa
      "TİCARİ" ile "TICARI" eşleşmez.
    """
    s = etiket.split("(")[0].split("/")[0]
    s = s.replace("İ", "I").replace("ı", "i").replace("Î", "I")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Za-z0-9ÇĞÖŞÜçğöşü ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip().upper()


#: kanonik ad -> hangi tabloda aranacağı. Tablo kısıtı olmayan kalem yok:
#: aynı kelime farklı tablolarda farklı şey demek olabiliyor. Örnek:
#: "Parasal Pozisyon" gelir tablosunda TMS 29 kazanç/kaybı, nakit akış
#: tablosunda o kazancın nakit dışı olduğu için geri çevrilmesi. İkisini
#: karıştırmak sessiz bir hata olurdu.
TABLO: dict[str, str] = {}

#: kanonik ad -> kabul edilen ham etiketler (normalize edilmiş hâlleriyle)
ESLEME: dict[str, tuple[str, ...]] = {
    # --- bilanço: toplamlar ---
    "donen_varlik": ("DONEN VARLIKLAR TOPLAM",),
    "duran_varlik": ("DURAN VARLIKLAR TOPLAM",),
    "toplam_varlik": ("TOPLAM VARLIKLAR",),
    "kv_yukumluluk": ("KV YUKUMLULUKLER TOPLAM", "KISA VADELI YUKUMLULUKLER TOPLAM"),
    "uv_yukumluluk": ("UV YUKUMLULUKLER TOPLAM", "UZUN VADELI YUKUMLULUKLER TOPLAM"),
    "toplam_yukumluluk": ("TOPLAM YUKUMLULUKLER",),
    "ozkaynak": ("OZKAYNAKLAR TOPLAM",),
    "toplam_kaynak": ("TOPLAM KAYNAKLAR", "TOPLAM YUKUMLULUKLER VE OZKAYNAKLAR"),
    # --- bilanço: parasal / parasal olmayan ayrımı için ---
    "nakit": ("NAKIT VE NAKIT BENZERLERI",),
    "ticari_borc": ("TICARI BORCLAR",),
    "maddi_duran_varlik": ("MADDI DURAN VARLIKLAR",),
    "maddi_olmayan_duran_varlik": ("MADDI OLMAYAN DURAN VARLIKLAR",),
    "odenmis_sermaye": ("ODENMIS SERMAYE",),
    "sermaye_duzeltme_farklari": ("SERMAYE DUZELTME FARKLARI",),
    # --- gelir tablosu ---
    "hasilat": ("HASILAT",),
    "brut_kar": ("BRUT KAR",),
    "favok": ("FAVOK",),
    "net_kar": ("NET DONEM KARI",),
    # TMS 29'un gelir tablosuna soktuğu kalem. Nominal muhasebede yok --
    # sıfırdan bir büyüklük olarak beliriyor. Yedi şirket yedi farklı
    # biçimde yazmış; hepsi burada, çünkü bulanık eşleştirme yok.
    "net_parasal_pozisyon": (
        "NET PARASAL POZISYON KAZANCI",
        "NET PARASAL POZISYON KAYBI",
        "NET PARASAL POZISYON KAYIPLARI",
        "PARASAL KAZANC",
    ),
}

#: Bilanço kalemi bilançoda, gelir kalemi gelir tablosunda aranır.
TABLO.update(
    {
        k: "bilanco"
        for k in (
            "donen_varlik",
            "duran_varlik",
            "toplam_varlik",
            "kv_yukumluluk",
            "uv_yukumluluk",
            "toplam_yukumluluk",
            "ozkaynak",
            "toplam_kaynak",
            "nakit",
            "ticari_borc",
            "maddi_duran_varlik",
            "maddi_olmayan_duran_varlik",
            "odenmis_sermaye",
            "sermaye_duzeltme_farklari",
        )
    }
)
TABLO.update(
    {
        k: "gelir"
        for k in ("hasilat", "brut_kar", "favok", "net_kar", "net_parasal_pozisyon")
    }
)

#: Her şirkette bulunması zorunlu kalemler. Eksikse veri seti kusurludur.
ZORUNLU = (
    "net_parasal_pozisyon",
    "donen_varlik",
    "duran_varlik",
    "toplam_varlik",
    "kv_yukumluluk",
    "uv_yukumluluk",
    "toplam_yukumluluk",
    "ozkaynak",
    "toplam_kaynak",
    "nakit",
    "maddi_duran_varlik",
    "ozkaynak",
    "hasilat",
    "favok",
    "net_kar",
)

_TERS = {ham: kanon for kanon, hamlar in ESLEME.items() for ham in hamlar}


def esle(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Ham çıkarıma `kalem` kolonu ekler.

    Returns
    -------
    (eslenen, eslenmeyen)
        `eslenen`: kanonik adı bulunan satırlar, `kalem` kolonu eklenmiş.
        `eslenmeyen`: tanınmayan ham etiketler ve kaç kez geçtikleri.
            Sessizce yutulmasınlar diye ayrıca döndürülüyor.
    """
    n = df.ham_etiket.map(normalize)
    kalem = n.map(_TERS)

    # Tablo kısıtı: kalem yanlış tabloda bulunduysa eşleşme geçersiz.
    if "tablo" in df.columns:
        beklenen = kalem.map(TABLO)
        yanlis_tablo = beklenen.notna() & (beklenen != df.tablo)
        kalem = kalem.where(~yanlis_tablo)

    eslenen = df.assign(kalem=kalem)[kalem.notna()].copy()
    eslenmeyen = df.loc[kalem.isna(), "ham_etiket"].value_counts()
    return eslenen, eslenmeyen


def genis(df: pd.DataFrame, blok: str = "mutlak") -> pd.DataFrame:
    """Eşlenmiş veriyi (şirket, yıl, seviye) x kalem matrisine çevirir.

    Analiz burada başlıyor; bu noktaya kadar hiçbir yorum yapılmadı.
    """
    d = df[df.blok == blok]
    return d.pivot_table(
        index=["sirket", "yil", "seviye"],
        columns="kalem",
        values="deger",
        aggfunc="first",
    ).reset_index()
