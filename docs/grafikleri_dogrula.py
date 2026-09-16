"""Grafiklerin koddan kopmadığını doğrular.

Neden bayt ya da dosya boyutu karşılaştırması değil
---------------------------------------------------
İlk hâli ``git diff --exit-code docs/`` idi: yeniden üretilen dosya
depodakiyle **birebir aynı** olsun isteniyordu. Yerel makinede geçti,
CI'da düştü -- çünkü GitHub'ın Ubuntu makinesindeki freetype sürümü
yazıları biraz farklı çiziyor, bu da PNG sıkıştırmasını değiştiriyor.
Hiçbir şey bozulmamıştı; kontrol yanlış soruyu soruyordu.

İkinci denemem dosya **boyutunu** karşılaştırmaktı. Daha iyi ama hâlâ
yanlış eksende: sıkıştırılmış boyut, yazı kenarlarındaki bir piksellik
farktan bile etkilenir ve sürümden sürüme oynar.

Burada bakılan şey **görüntü boyutları**: genişlik ve yükseklik.
``figsize × dpi``den geliyorlar, yani kodun kendisinden. ``bbox_inches
="tight"`` kırpması yazı ölçülerine az da olsa bağlı olduğu için küçük
bir tolerans bırakılıyor -- ama içeriği gerçekten değişen bir grafik
(panel eklenmiş, eksen büyümüş) bu toleransı fersah fersah aşar.

Kontrol edilen dört şey:

- Beklenen dosya kümesi birebir eşleşmeli (eksik ya da fazla yok).
- Her dosya geçerli bir PNG olmalı ve boş olmamalı.
- Genişlik ve yükseklik, commit'teki hâlinden ``TOLERANS`` kadar sapabilir.

Sürüm oynamalarına dayanır, gerçek kopmayı yakalar.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

#: docs/grafikleri_uret.py'nin üretmesi gereken dosyalar.
BEKLENEN = {
    "endeks-cipasi.png",
    "kalem-katsayilari.png",
    "esik-taramasi.png",
    "siralama-egimi.png",
}

#: Commit'teki görüntü boyutlarından izin verilen bağıl sapma.
#: Yazı ölçüsü farkları birkaç piksel oynatır; içerik değişikliği
#: onlarca yüzde oynatır. Aradaki boşluk geniş.
TOLERANS = 0.10

#: Geçerli bir PNG dosyasının ilk baytları.
PNG_IMZASI = b"\x89PNG\r\n\x1a\n"

EN_AZ_BAYT = 5_000


def png_olculeri(veri: bytes) -> tuple[int, int]:
    """PNG başlığından (genişlik, yükseklik). Kütüphane gerekmiyor.

    IHDR yığını dosyanın başında sabit yerde duruyor: 16-20. baytlar
    genişlik, 20-24. baytlar yükseklik, ikisi de big-endian uint32.
    """
    return (
        int.from_bytes(veri[16:20], "big"),
        int.from_bytes(veri[20:24], "big"),
    )


def _committeki_olculer(ad: str) -> tuple[int, int] | None:
    """Dosyanın HEAD'deki görüntü boyutları; çözülemezse None."""
    try:
        cikti = subprocess.run(
            ["git", "cat-file", "blob", f"HEAD:docs/{ad}"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    veri = cikti.stdout
    if len(veri) < 24 or not veri.startswith(PNG_IMZASI):
        return None
    return png_olculeri(veri)


def main() -> int:
    klasor = Path("docs")
    mevcut = {p.name for p in klasor.glob("*.png")}
    sorunlar: list[str] = []

    eksik = BEKLENEN - mevcut
    fazla = mevcut - BEKLENEN
    if eksik:
        sorunlar.append(f"üretilmeyen grafik: {sorted(eksik)}")
    if fazla:
        sorunlar.append(
            f"beklenmeyen grafik: {sorted(fazla)} "
            "(BEKLENEN kümesini güncelle ya da dosyayı kaldır)"
        )

    for ad in sorted(BEKLENEN & mevcut):
        yol = klasor / ad
        veri = yol.read_bytes()
        if not veri.startswith(PNG_IMZASI):
            sorunlar.append(f"{ad}: geçerli bir PNG değil")
            continue
        if len(veri) < EN_AZ_BAYT:
            sorunlar.append(f"{ad}: şüpheli derecede küçük ({len(veri)} bayt)")
            continue
        yeni = png_olculeri(veri)
        eski = _committeki_olculer(ad)
        if eski is None:
            print(f"  {ad}: {yeni[0]}x{yeni[1]} px (commit'te karşılığı yok, atlandı)")
            continue
        sapma = max(abs(y - e) / e for y, e in zip(yeni, eski, strict=True))
        durum = "OK " if sapma <= TOLERANS else "SAPMA"
        print(
            f"  {durum} {ad}: {eski[0]}x{eski[1]} -> {yeni[0]}x{yeni[1]} px "
            f"({sapma:.1%})"
        )
        if sapma > TOLERANS:
            sorunlar.append(
                f"{ad}: görüntü boyutu %{100 * sapma:.0f} değişti"
                " — grafik güncellenmemiş olabilir"
            )

    if sorunlar:
        print("\nDOĞRULAMA BAŞARISIZ:")
        for s in sorunlar:
            print(f"  - {s}")
        return 1
    print(f"\n{len(BEKLENEN)} grafik doğrulandı.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
