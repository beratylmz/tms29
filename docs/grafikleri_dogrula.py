"""Grafiklerin koddan kopmadığını doğrular.

Neden bayt karşılaştırması değil
--------------------------------
İlk hâli ``git diff --exit-code docs/`` idi: yeniden üretilen dosya
depodakiyle **birebir aynı** olsun isteniyordu. Yerel makinede geçti,
CI'da da geçti -- ama bu kırılgan bir kontrol. matplotlib veya freetype
sürümü değiştiği anda aynı kod farklı bayt üretir; hiçbir şey bozulmadığı
hâlde CI kırmızıya döner ve aylar sonra kimse sebebini hatırlamaz.

Buradaki kontrol asıl soruyu soruyor: **görseller hâlâ üretiliyor ve
depodakiyle aynı şeyi mi gösteriyor?**

- Beklenen dosya kümesi birebir eşleşmeli (eksik ya da fazla yok).
- Her dosya geçerli bir PNG olmalı ve boş olmamalı.
- Boyut, commit'teki hâlinden ``TOLERANS`` kadar sapabilir. Yeniden
  çizim gürültüsü birkaç yüzde; içeriği değişen bir grafik bunu aşar.

Yani sürüm oynamalarına dayanıyor, gerçek kopmayı yakalıyor.
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

#: Commit'teki boyuttan izin verilen bağıl sapma.
TOLERANS = 0.25

#: Geçerli bir PNG dosyasının ilk baytları.
PNG_IMZASI = b"\x89PNG\r\n\x1a\n"

EN_AZ_BAYT = 5_000


def _committeki_boyut(ad: str) -> int | None:
    """Dosyanın HEAD'deki boyutu; depo dışında çalışılıyorsa None."""
    try:
        cikti = subprocess.run(
            ["git", "cat-file", "-s", f"HEAD:docs/{ad}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return int(cikti.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None


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
        eski = _committeki_boyut(ad)
        if eski is None:
            print(f"  {ad}: {len(veri):,} bayt (commit'te karşılığı yok, atlandı)")
            continue
        sapma = abs(len(veri) - eski) / eski
        durum = "OK " if sapma <= TOLERANS else "SAPMA"
        print(f"  {durum} {ad}: {eski:,} -> {len(veri):,} bayt ({sapma:+.1%})")
        if sapma > TOLERANS:
            sorunlar.append(
                f"{ad}: boyut %{100 * sapma:.0f} değişti"
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
