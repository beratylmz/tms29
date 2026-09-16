"""Terminoloji ve sabitler. Bu projenin "karar dosyası".

Neden ayrı bir dosya
--------------------
Bu analizde karıştırılması kolay üç ayrım var ve üçü de sessizce yanlış
sonuç üretir. Hepsi burada bir kez tanımlanıyor.

1. FİYAT SEVİYESİ (price level)
   Bir rakamın hangi tarihin satın alma gücüyle ifade edildiği.
   "2022 (Nominal)" ile "2022 (2023 SAG)" *aynı yılın* bilançosudur ama
   farklı fiyat seviyelerindedir. Bu proje tam olarak ikisi arasındaki
   farkı ölçtüğü için, fiyat seviyesi veri setinde birinci sınıf bir
   boyuttur -- asla yıl ile birleştirilmez.

   SAG = "Satın Alma Gücü". TMS 29 uyarınca düzeltilmiş rakam.

2. PARASAL / PARASAL OLMAYAN KALEM
   TMS 29'un çekirdeği. Parasal kalemler (nakit, ticari alacak, borç)
   zaten bilanço tarihinin satın alma gücündedir; düzeltilmezler.
   Parasal olmayan kalemler (maddi duran varlık, stok, özkaynak) edinme
   tarihinden itibaren endekslenir.

   Sonuç: düzeltme bilançoyu düzgün bir katsayıyla büyütmez, **bileşimini
   değiştirir.** Oranların değişmesinin sebebi budur. Eğer düzeltme
   düzgün bir çarpma olsaydı hiçbir oran değişmezdi -- bu, projenin
   kontrol testidir (bkz. tests/test_dogrula.py).

3. MUTLAK TUTAR / DİKEY YÜZDE
   Kaynak çalışma kitabında her tablo iki blok hâlinde duruyor: önce bin
   TL cinsinden mutlak tutarlar, sonra aynı kalemlerin toplama oranı
   (common-size). İki bloğun **başlık satırı birebir aynı** olduğu için
   ayırt edilemezler; ayrım değerlerin büyüklüğünden yapılıyor.

   Bu tuzağa düşmek sessiz bir hata olurdu: yüzdeleri TL sanmak hiçbir
   yerde hata vermez, sadece sonucu saçmalaştırır.
"""

from __future__ import annotations

#: Kaynak dosyadaki tutarların birimi.
BIRIM = "bin TL"

#: Bir kolonun dikey-yüzde bloğuna ait sayılması için üst sınır.
#: Gerçek bir finansal tablo kolonunda mutlaka milyonlar mertebesinde en
#: az bir değer bulunur; yüzde bloğunda hiçbir değer 100'ü aşmaz.
#: Aradaki üç mertebelik boşluk, eşiğin keyfî olmamasını sağlıyor.
DIKEY_YUZDE_TAVANI = 1_000.0

#: Enflasyon muhasebesinin ilk uygulandığı yıl. 2022 bilançoları hem
#: nominal hem düzeltilmiş hâlde mevcut -- projenin ölçüm penceresi bu.
ILK_DUZELTME_YILI = 2022

#: TMS 29 kapsamında parasal sayılan kalemler (düzeltilmez).
PARASAL = frozenset(
    {
        "nakit",
        "ticari_alacak",
        "diger_alacak",
        "finansal_yatirim_kv",
        "ticari_borc",
        "diger_borc",
        "finansal_borc_kv",
        "finansal_borc_uv",
        "ertelenmis_vergi_yukumlulugu",
    }
)

#: Parasal olmayan kalemler (endekslenir).
PARASAL_OLMAYAN = frozenset(
    {
        "maddi_duran_varlik",
        "maddi_olmayan_duran_varlik",
        "stoklar",
        "ozkaynak",
        "odenmis_sermaye",
        "sermaye_duzeltme_farklari",
    }
)


def fiyat_seviyesi_ayristir(baslik: str) -> tuple[int, str]:
    """Kolon başlığından (yıl, fiyat seviyesi) çıkarır.

    Beklenen biçimler::

        "31.12.2022 (Nominal TL)"   -> (2022, "nominal")
        "31.12.2023 (2024 TL SAG)"  -> (2023, "sag2024")
        "31.12.2025 (2025 SAG)"     -> (2025, "sag2025")

    Fiyat seviyesi normalize ediliyor çünkü şirketler aynı şeyi iki
    farklı yazıyor ("2024 SAG" ve "2024 TL SAG"). Normalize edilmezse
    aynı kolon iki ayrı seviye sanılır ve eşleştirme sessizce boş kalır.
    """
    import re

    m = re.search(r"(\d{4})", baslik)
    if not m:
        raise ValueError(f"Başlıkta yıl bulunamadı: {baslik!r}")
    yil = int(m.group(1))

    ic = re.search(r"\((.*?)\)", baslik)
    if not ic:
        raise ValueError(f"Başlıkta fiyat seviyesi parantezi yok: {baslik!r}")
    ifade = ic.group(1).upper().replace("TL", "").strip()

    if "NOM" in ifade:
        return yil, "nominal"
    m2 = re.search(r"(\d{4})", ifade)
    if m2 and "SAG" in ifade:
        return yil, f"sag{m2.group(1)}"
    raise ValueError(f"Fiyat seviyesi tanınmadı: {baslik!r} -> {ifade!r}")
