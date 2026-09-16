"""Rapor grafikleri.

Neden pakette, docs betiğinde değil
-----------------------------------
Bir grafik sessizce yalan söyleyebilir: yanlış yere çizilen bir referans
çizgisi hatasız çalışır ve yanlış anlatır. Fonksiyonlar burada olduğu
için çizilen sayının hesaplanan sayıyla aynı olduğu test edilebiliyor
(bkz. tests/test_grafik.py).

Palet
-----
Teal (#00846C) ve kiremit (#A3392A). Renk körlüğü ayrımı doğrulandı
(deutan ΔE 8,9; normal görüş ΔE 24,1). Ayrıca hiçbir grafikte renk tek
başına bilgi taşımıyor -- her yerde doğrudan etiket var.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ACCENT = "#00846C"
TAIL = "#A3392A"
MUTED = "#5F6E6E"
LINE = "#D9E0DD"
ZEMIN = "#FFFFFF"


def _duzen(ax: plt.Axes) -> plt.Axes:
    ax.spines[["top", "right"]].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(LINE)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(True, color=LINE, linewidth=0.7, alpha=0.6)
    ax.set_axisbelow(True)
    return ax


def endeks_geri_cikarim(
    endeks: pd.Series, resmi: float, ax: plt.Axes | None = None, pay: float = 0.02
) -> plt.Axes:
    """Yedi şirketten geri çıkarılan enflasyon endeksi, resmî rakama karşı.

    Projenin dış çıpası: parasal kalemlerin katsayısı tanım gereği resmî
    endekse eşit olmalı ve yedi bağımsız kaynak aynı sayıyı vermeli.

    Eksen ölçeği hakkında
    ---------------------
    Eksen, verinin kendi aralığına değil resmî endeksin ``±pay`` kadar
    çevresine sabitleniyor. Sebebi dürüstlük: gözlenen sapmalar binde
    birler mertebesinde, eksen onlara göre daraltılsaydı noktalar
    dağılmış görünürdü ve grafik kendi mesajının tersini anlatırdı.
    Şimdiki hâlinde referans çizgisinden görülebilir bir uzaklık,
    gerçekten anlamlı bir sapma demek.
    """
    ax = _duzen(ax or plt.subplots(figsize=(8, 3.2))[1])
    s = endeks.sort_values()
    y = np.arange(len(s))
    ax.axvspan(
        resmi * (1 - 0.005), resmi * (1 + 0.005), color=ACCENT, alpha=0.10, zorder=0
    )
    ax.axvline(resmi, color=TAIL, lw=1.8, zorder=1)
    ax.scatter(
        s.values, y, s=80, color=ACCENT, zorder=3, edgecolor=ZEMIN, linewidth=1.5
    )
    for i, (_ad, v) in enumerate(s.items()):
        ax.annotate(
            f"{v:.4f}",
            xy=(v, i),
            xytext=(11, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=MUTED,
            family="monospace",
        )
    ax.set_yticks(y, s.index, fontsize=9)
    ax.set_xlim(resmi * (1 - pay), resmi * (1 + pay))
    ax.set_ylim(-0.8, len(s) - 0.2)
    ax.annotate(
        f"resmî TÜFE endeksi {resmi:.4f}\n(gölgeli bant: ±%0,5)",
        xy=(resmi, -0.62),
        xytext=(8, 0),
        textcoords="offset points",
        va="center",
        fontsize=8.5,
        color=TAIL,
    )
    en_buyuk = 100 * (s - resmi).abs().max() / resmi
    ax.set_xlabel(
        f"parasal kalemlerden geri çıkarılan endeks  ·  en büyük sapma %{en_buyuk:.2f}",
        color=MUTED,
        fontsize=9,
    )
    ax.set_title(
        "Veri, resmî enflasyon endeksini yeniden üretiyor", fontsize=11, loc="left"
    )
    return ax


#: Bu grafiğe giren kalemler ve sınıfları. Açık liste, çünkü:
#:
#: - Gelir tablosu kalemleri (hasılat, FAVÖK, net kâr) dışarıda:
#:   onlar tek bir bilanço tarihinden değil, kazanıldıkları aydan
#:   itibaren endeksleniyor. Aynı grafikte göstermek iki farklı
#:   mekanizmayı tek hikâye sanmak olurdu.
#: - "Sermaye düzeltme farkları" dışarıda: nominalde sıfıra yakın
#:   olduğu için katsayısı patlıyor ve ekseni eziyor. Kendi başına
#:   anlamlı, ama bu grafiğin sorusu o değil.
#: - Ödenmiş sermaye dışarıda: katsayısı tam 1,0 (düzeltme ayrı bir
#:   kaleme yazılıyor); "parasal olmayan endeksi aşar" kuralının
#:   istisnası ve ayrı anlatılması gerekiyor.
GRAFIK_KALEMLERI: tuple[tuple[str, str], ...] = (
    ("nakit", "parasal"),
    ("ticari_borc", "parasal"),
    ("kv_yukumluluk", "parasal"),
    ("donen_varlik", "parasal"),
    ("toplam_yukumluluk", "karma"),
    ("toplam_varlik", "karma"),
    ("duran_varlik", "parasal olmayan"),
    ("ozkaynak", "parasal olmayan"),
    ("maddi_duran_varlik", "parasal olmayan"),
    ("maddi_olmayan_duran_varlik", "parasal olmayan"),
)


def kalem_katsayilari(
    katsayi_df: pd.DataFrame, endeks: float, ax: plt.Axes | None = None
) -> plt.Axes:
    """Kalem bazında yükseltme katsayıları, parasal/parasal olmayan ayrımıyla.

    Grafiğin tek iddiası var: parasal kalemler endeksin üstünde durur,
    parasal olmayanlar onu aşar. Hangi kalemlerin girdiği
    `GRAFIK_KALEMLERI`'nde açıkça yazılı -- gerekçeleriyle.
    """
    ax = _duzen(ax or plt.subplots(figsize=(8.5, 4.2))[1])
    sinif = dict(GRAFIK_KALEMLERI)
    sira = [k for k, _ in GRAFIK_KALEMLERI]
    konum = {k: i for i, k in enumerate(reversed(sira))}
    d = katsayi_df[katsayi_df.kalem.isin(sira)]

    ax.axvline(endeks, color=MUTED, lw=1.2, ls="--", zorder=1)
    ax.annotate(
        f"endeks {endeks:.4f}",
        xy=(endeks, len(sira) - 1.1),
        xytext=(6, 0),
        textcoords="offset points",
        fontsize=8.5,
        color=MUTED,
    )
    for ad, renk, isaret in (
        ("parasal", ACCENT, "o"),
        ("karma", MUTED, "D"),
        ("parasal olmayan", TAIL, "s"),
    ):
        alt = d[d.kalem.map(sinif) == ad]
        ax.scatter(
            alt.katsayi,
            [konum[k] for k in alt.kalem],
            s=46,
            marker=isaret,
            color=renk,
            alpha=0.82,
            label=ad,
            zorder=3,
            edgecolor=ZEMIN,
            linewidth=0.9,
        )
    ax.set_yticks(
        range(len(sira)),
        [k.replace("_", " ") for k in reversed(sira)],
        fontsize=8.5,
    )
    ax.set_xscale("log")
    ax.set_xticks([1, 1.6477, 3, 5, 8], ["1", "1,65", "3", "5", "8"])
    ax.set_xlim(0.9, 10)
    ax.legend(fontsize=8.5, frameon=False, loc="upper right")
    ax.set_xlabel("düzeltilmiş / nominal (log ölçek)", color=MUTED, fontsize=9)
    ax.set_title(
        "Parasal kalemler endekste durur, parasal olmayanlar aşar",
        fontsize=11,
        loc="left",
    )
    return ax


def esik_taramasi(araliklar: pd.DataFrame, oran_adi: str) -> plt.Figure:
    """Her şirketin kırılma aralığı ve eşik başına etkilenen karar sayısı."""
    fig, (ust, alt) = plt.subplots(
        2,
        1,
        figsize=(9, 5.2),
        sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1], "hspace": 0.12},
    )
    a = araliklar.sort_values("alt")
    for i, r in enumerate(a.itertuples()):
        ust.plot(
            [r.alt, r.ust],
            [i, i],
            color=TAIL,
            lw=5,
            solid_capstyle="round",
            alpha=0.75,
            zorder=2,
        )
        ust.annotate(
            f"{r.alt:.2f} – {r.ust:.2f}",
            xy=(r.ust, i),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=8,
            color=MUTED,
            family="monospace",
        )
    ust.set_yticks(range(len(a)), a.sirket, fontsize=9)
    genislik = a.ust.max() - a.alt.min()
    ust.set_xlim(a.alt.min() - 0.04 * genislik, a.ust.max() + 0.22 * genislik)
    _duzen(ust)
    ust.set_title(
        f"{oran_adi}: muhasebe tercihinin kararı çevirdiği eşik aralıkları",
        fontsize=11,
        loc="left",
    )

    izgara = np.linspace(a.alt.min(), a.ust.max(), 2000)
    sayi = np.zeros_like(izgara)
    for r in a.itertuples():
        sayi += ((izgara > r.alt) & (izgara < r.ust)).astype(float)
    alt.fill_between(izgara, sayi, color=ACCENT, alpha=0.3, step="mid")
    alt.plot(izgara, sayi, color=ACCENT, lw=1.8, drawstyle="steps-mid")
    _duzen(alt)
    alt.set_ylabel("etkilenen\nşirket", color=MUTED, fontsize=8.5)
    alt.set_xlabel(f"{oran_adi} eşiği", color=MUTED, fontsize=9)
    alt.set_yticks(range(0, int(sayi.max()) + 1))
    fig.subplots_adjust(left=0.12, right=0.97, top=0.90, bottom=0.12)
    return fig


def siralama_egimi(
    karsilastirma: pd.DataFrame,
    oranlar: tuple[str, str],
    basliklar: tuple[str, str],
) -> plt.Figure:
    """İki oranın sıralamasının nominal -> düzeltilmiş geçişi.

    Sıra değiştiren şirketler kiremit rengiyle ve kalın çiziliyor; renk
    tek başına bilgi taşımasın diye her çizginin iki ucunda da isim var.
    """
    fig, eksenler = plt.subplots(1, 2, figsize=(10, 4.8))
    for ax, oran, baslik in zip(eksenler, oranlar, basliklar, strict=True):
        d = karsilastirma[karsilastirma.oran == oran].copy()
        d["sira_a"] = d.a.rank()
        d["sira_b"] = d.b.rank()
        for r in d.itertuples():
            degisti = r.sira_a != r.sira_b
            ax.plot(
                [0, 1],
                [r.sira_a, r.sira_b],
                color=TAIL if degisti else MUTED,
                lw=2.2 if degisti else 1.2,
                alpha=0.95 if degisti else 0.45,
                zorder=3 if degisti else 2,
            )
            ax.annotate(
                r.sirket,
                xy=(0, r.sira_a),
                xytext=(-6, 0),
                textcoords="offset points",
                ha="right",
                va="center",
                fontsize=8.5,
                color=MUTED,
            )
            ax.annotate(
                r.sirket,
                xy=(1, r.sira_b),
                xytext=(6, 0),
                textcoords="offset points",
                ha="left",
                va="center",
                fontsize=8.5,
                color=TAIL if degisti else MUTED,
            )
        ax.set_xlim(-0.42, 1.42)
        ax.invert_yaxis()
        ax.set_xticks([0, 1], ["nominal", "düzeltilmiş"], fontsize=9)
        ax.set_yticks([])
        ax.spines[:].set_visible(False)
        ax.tick_params(colors=MUTED, length=0)
        ax.set_title(baslik, fontsize=10.5, loc="left")
    fig.suptitle(
        "Sıralama: bilanço oranı ayakta kalıyor, kârlılık kalmıyor",
        fontsize=11,
        x=0.02,
        ha="left",
    )
    # tight_layout, çerçevesi kapalı eksenlerde uyarı veriyor; boşluk elle.
    fig.subplots_adjust(left=0.10, right=0.92, top=0.82, bottom=0.10, wspace=0.42)
    return fig
