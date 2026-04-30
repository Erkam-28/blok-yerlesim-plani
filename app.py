import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Polygon
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
import warnings
from io import BytesIO

warnings.filterwarnings("ignore")

st.set_page_config(page_title="Blok Yerleşim Planı", layout="wide")
st.title("🏗️ BLOK YERLEŞİM PLANI")
st.markdown("---")

# ==================================================
# SABİTLER (ORİJİNAL)
# ==================================================

ISKELE = 3
DARBOGAZ_PCT = 80
STEP = 0.5
A31_SON_GUN = pd.Timestamp("2026-08-15")
DIKINE_ZORUNLU_BOY = 27

ISTIF_X_SOL = 0.0
ISTIF_Y_ALT = 0.0
ISTIF_Y_UST = 35.52
ISTIF_X_UST = 100.18
ISTIF_X_ALT = 72.4
ISTIF_EGIM = (ISTIF_X_UST - ISTIF_X_ALT) / ISTIF_Y_UST

DUZ_KIZAK_TOPLAM_U = 251.0
DUZ_KIZAK_TOPLAM_G = 59.56
DUZ_KIZAK_BLOK_U = 101.0
DUZ_KIZAK_MUGEM_U = 150.0
DUZ_KIZAK_MUGEM_X_BASLANGIC = 101.0

A6_TAM_U = 230.0
A6_G = 40.3
A6_BLOK_U = 111.0
A6_NB76_U = A6_TAM_U - A6_BLOK_U
A6_EYUL = datetime(2026, 9, 1)

TRANSFER_RULES = {
    "A3 Atölyesi": {"size": (24, 12), "rotate": True},
    "A4 Atölyesi": {"size": (24, 12), "rotate": True},
    "A3 Atölyesi(Jig)": None,
    "A6 Atölyesi": {"size": (12, 27), "rotate": False},
    "A31 Atölyesi": {"size": (12, 27), "rotate": False},
    "Düz Kızak": {"size": (12, 27), "rotate": False},
}

SAHALAR = [
    {"ad": "A3 Atölyesi", "oncelik": 1,
     "kisit": lambda b, t: b["Tonaj"] <= 55,
     "alan": lambda t: (74.0, 32.0)},
    {"ad": "A3 Atölyesi(Jig)", "oncelik": 1,
     "kisit": lambda b, t: (b["Tonaj"] <= 55 and b["En"] <= 12 and b["Boy"] <= 12),
     "alan": lambda t: (52.0, 32.0)},
    {"ad": "A4 Atölyesi", "oncelik": 1,
     "kisit": lambda b, t: b["Tonaj"] <= 55,
     "alan": lambda t: (53.0, 32.0)},
    {"ad": "A6 Atölyesi", "oncelik": 1,
     "kisit": lambda b, t: b["Tonaj"] <= 240,
     "alan": lambda t: (A6_TAM_U, A6_G) if t >= A6_EYUL else (A6_BLOK_U, A6_G)},
    {"ad": "A31 Atölyesi", "oncelik": 1,
     "kisit": lambda b, t: (b["Tonaj"] <= 240 and b["Erection_Bas"] <= A31_SON_GUN),
     "alan": lambda t: (99.35, 35.98) if t <= A31_SON_GUN else (0.0, 0.0)},
    {"ad": "A29 Açık Saha", "oncelik": 2,
     "kisit": lambda b, t: b["Tonaj"] <= 55,
     "alan": lambda t: (120.0, 21.0)},
    {"ad": "Düz Kızak", "oncelik": 2,
     "kisit": lambda b, t: b["Tonaj"] <= 400,
     "alan": lambda t: (DUZ_KIZAK_TOPLAM_U, DUZ_KIZAK_TOPLAM_G)},
    {"ad": "Açık Saha(İstif)", "oncelik": 3,
     "kisit": lambda b, t: b["Tonaj"] <= 400,
     "alan": lambda t: (ISTIF_X_UST, ISTIF_Y_UST)},
]
SAHALAR = sorted(SAHALAR, key=lambda x: x["oncelik"])

def snap(v):
    return round(round(v / STEP) * STEP, 10)

def rect_overlaps(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2):
    if ax2 <= bx1 + 0.001: return False
    if ax1 >= bx2 - 0.001: return False
    if ay2 <= by1 + 0.001: return False
    if ay1 >= by2 - 0.001: return False
    return True

def blok_rotasyon_modu(blok):
    en = float(blok["En"])
    boy = float(blok["Boy"])
    if abs(en - DIKINE_ZORUNLU_BOY) < 0.1 or abs(boy - DIKINE_ZORUNLU_BOY) < 0.1:
        return "dikine"
    return "serbest"

def istif_icinde_mi(x, y, w, h):
    koseler = [(x, y), (x+w, y), (x, y+h), (x+w, y+h)]
    for cx, cy in koseler:
        if cx < 0: return False
        if cy < 0: return False
        if cy > ISTIF_Y_UST: return False
        x_max = ISTIF_X_ALT + ISTIF_EGIM * cy
        if cx > x_max + 0.001: return False
    return True

def mugem_icinde_mi(x, y, w, h):
    if x < DUZ_KIZAK_MUGEM_X_BASLANGIC - 0.001: return False
    if y < -0.001: return False
    if x + w > DUZ_KIZAK_TOPLAM_U + 0.001: return False
    if y + h > DUZ_KIZAK_TOPLAM_G + 0.001: return False
    return True

def mugem_boyut(row):
    return float(row["Boy"]), float(row["En"])

# ==================================================
# SAHA MANAGER SINIFI
# ==================================================

class SahaManager:
    def __init__(self, ad):
        self.ad = ad
        self.bloklar = []
        self.mugem_isgal = []

    def aktif_bloklar(self, tarih):
        t = pd.Timestamp(tarih)
        return [b for b in self.bloklar if pd.Timestamp(b["bas"]) <= t < pd.Timestamp(b["erc"])]

    def transfer_rect(self):
        rule = TRANSFER_RULES.get(self.ad)
        if rule is None:
            return None
        tw, th = rule["size"]
        if rule.get("rotate", False):
            tw, th = th, tw
        return (0.0, 0.0, float(tw), float(th))

    def can_place(self, x, y, w, h, saha_u, saha_g, tarih, blok_erc=None):
        x, y, w, h = snap(x), snap(y), snap(w), snap(h)
        tarih_ts = pd.Timestamp(tarih)
        if x < 0 or y < 0:
            return False
        if self.ad == "Açık Saha(İstif)":
            if not istif_icinde_mi(x, y, w, h):
                return False
        else:
            if x + w > saha_u + 0.01 or y + h > saha_g + 0.01:
                return False
        tr = self.transfer_rect()
        if tr is not None:
            if rect_overlaps(x, y, x+w, y+h, tr[0], tr[1], tr[2], tr[3]):
                return False
        if blok_erc is not None:
            blok_erc_ts = pd.Timestamp(blok_erc)
            kontrol_bloklari = [b for b in self.bloklar if pd.Timestamp(b["bas"]) < blok_erc_ts and pd.Timestamp(b["erc"]) > tarih_ts]
        else:
            kontrol_bloklari = [b for b in self.bloklar if pd.Timestamp(b["bas"]) <= tarih_ts < pd.Timestamp(b["erc"])]
        for b in kontrol_bloklari:
            if rect_overlaps(x, y, x+w, y+h, b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]):
                return False
        return True

    def _aday_xs(self, tarih):
        tr = self.transfer_rect()
        xs = {0.0}
        if tr is not None:
            xs.add(snap(tr[2]))
        for b in self.bloklar:
            xs.add(snap(b["x"] + b["w"]))
            if b["x"] > 0:
                xs.add(snap(b["x"]))
        if self.ad == "Düz Kızak":
            for b in self.mugem_isgal:
                xs.add(snap(b["x"] + b["w"]))
                if b["x"] > 0:
                    xs.add(snap(b["x"]))
        return sorted(xs)

    def _aday_ys(self, tarih):
        tr = self.transfer_rect()
        ys = {0.0}
        if tr is not None:
            ys.add(snap(tr[3]))
        for b in self.bloklar:
            ys.add(snap(b["y"] + b["h"]))
            if b["y"] > 0:
                ys.add(snap(b["y"]))
        if self.ad == "Düz Kızak":
            for b in self.mugem_isgal:
                ys.add(snap(b["y"] + b["h"]))
                if b["y"] > 0:
                    ys.add(snap(b["y"]))
        return sorted(ys)

    def find_spot_single(self, w, h, saha_u, saha_g, tarih, blok_erc=None):
        w, h = snap(w), snap(h)
        saha_u, saha_g = snap(saha_u), snap(saha_g)
        if w > saha_u or h > saha_g:
            return None
        aday_ys = self._aday_ys(tarih)
        aday_xs = self._aday_xs(tarih)
        for y in aday_ys:
            y = snap(y)
            if y < 0 or y + h > saha_g + 0.01:
                continue
            for x in aday_xs:
                x = snap(x)
                if x < 0:
                    continue
                if self.ad != "Açık Saha(İstif)":
                    if x + w > saha_u + 0.01:
                        continue
                if self.can_place(x, y, w, h, saha_u, saha_g, tarih, blok_erc):
                    return (x, y)
        return None

    def find_spot(self, w, h, saha_u, saha_g, tarih, mod="serbest", blok_erc=None):
        if mod == "dikine":
            if h >= w:
                pos = self.find_spot_single(w, h, saha_u, saha_g, tarih, blok_erc)
                if pos:
                    return pos[0], pos[1], False
            else:
                pos = self.find_spot_single(h, w, saha_u, saha_g, tarih, blok_erc)
                if pos:
                    return pos[0], pos[1], True
            return None
        pos_n = self.find_spot_single(w, h, saha_u, saha_g, tarih, blok_erc)
        pos_r = None
        if abs(w - h) > 0.01:
            pos_r = self.find_spot_single(h, w, saha_u, saha_g, tarih, blok_erc)
        if pos_n is None and pos_r is None:
            return None
        if pos_n is None:
            return pos_r[0], pos_r[1], True
        if pos_r is None:
            return pos_n[0], pos_n[1], False
        if (pos_r[1], pos_r[0]) < (pos_n[1], pos_n[0]):
            return pos_r[0], pos_r[1], True
        return pos_n[0], pos_n[1], False

    def add_block(self, idx, x, y, bas, erc, w_placed, h_placed):
        self.bloklar.append({
            "idx": idx, "x": snap(x), "y": snap(y),
            "w": snap(w_placed), "h": snap(h_placed),
            "bas": bas, "erc": erc,
        })

    def add_mugem_isgal(self, idx, x, y, bas, w, h):
        self.mugem_isgal.append({
            "idx": idx, "x": snap(x), "y": snap(y),
            "w": snap(w), "h": snap(h), "bas": bas,
        })

    def remove_block(self, idx):
        self.bloklar = [b for b in self.bloklar if b["idx"] != idx]

    def cakisma_kontrol(self, tarih):
        aktif = self.aktif_bloklar(tarih)
        hatalar = []
        for i in range(len(aktif)):
            for j in range(i+1, len(aktif)):
                a, b = aktif[i], aktif[j]
                if rect_overlaps(a["x"], a["y"], a["x"]+a["w"], a["y"]+a["h"],
                                 b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]):
                    hatalar.append((a["idx"], b["idx"]))
        return hatalar

    def sinir_disi_kontrol(self, saha_u, saha_g, tarih):
        hatalar = []
        for b in self.aktif_bloklar(tarih):
            if self.ad == "Açık Saha(İstif)":
                if not istif_icinde_mi(b["x"], b["y"], b["w"], b["h"]):
                    hatalar.append(b["idx"])
            else:
                if (b["x"] < 0 or b["y"] < 0 or
                    b["x"] + b["w"] > saha_u + 0.01 or
                    b["y"] + b["h"] > saha_g + 0.01):
                    hatalar.append(b["idx"])
        return hatalar


class MugemManager:
    def __init__(self):
        self.bloklar = []

    def aktif_bloklar(self, tarih):
        return [b for b in self.bloklar if b["bas"] <= tarih]

    def can_place(self, x, y, w, h, tarih):
        if not mugem_icinde_mi(x, y, w, h):
            return False
        for b in self.aktif_bloklar(tarih):
            if rect_overlaps(x, y, x+w, y+h, b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]):
                return False
        return True

    def add_block(self, idx, x, y, bas, w_placed, h_placed):
        self.bloklar.append({
            "idx": idx, "x": snap(x), "y": snap(y),
            "w": snap(w_placed), "h": snap(h_placed), "bas": bas,
        })

    def remove_block(self, idx):
        self.bloklar = [b for b in self.bloklar if b["idx"] != idx]

# ==================================================
# YERLEŞTİRME FONKSİYONLARI
# ==================================================

def reset_df(target_df):
    target_df["Koord_X"] = np.nan
    target_df["Koord_Y"] = np.nan
    target_df["Normal_X"] = np.nan
    target_df["Normal_Y"] = np.nan
    target_df["Istif_X"] = np.nan
    target_df["Istif_Y"] = np.nan
    target_df["Mugem_Yerlesti"] = False
    target_df["Istife_Tasindi"] = False
    target_df["Donuk"] = False
    target_df["Sigmiyor"] = False
    target_df["Otelendi"] = False
    if "Orijinal_Bas" in target_df.columns:
        target_df["Baslangic"] = target_df["Orijinal_Bas"].copy()
        target_df["Bitis"] = target_df["Orijinal_Bitis"].copy()
    return {s["ad"]: SahaManager(s["ad"]) for s in SAHALAR}


def yerlesim_hesapla(hedef_tarih, target_df):
    managers = reset_df(target_df)
    return managers

# ==================================================
# PLAN GÖSTER (ORİJİNAL)
# ==================================================

def plan_goster(target_df, tarih_ts):
    import matplotlib.gridspec as gridspec
    t = pd.Timestamp(tarih_ts)
    aktif_sahalar = [s for s in SAHALAR if s["alan"](t.to_pydatetime())[0] > 0]
    
    cols = 3
    rows = max(1, (len(aktif_sahalar) + cols - 1) // cols)
    
    fig = plt.figure(figsize=(20, 12))
    gs = gridspec.GridSpec(rows, cols, figure=fig, hspace=0.3, wspace=0.2)
    
    for i, saha in enumerate(aktif_sahalar):
        ax = fig.add_subplot(gs[i])
        ax.text(0.5, 0.5, saha["ad"], ha="center", va="center", fontsize=12)
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 50)
    
    return fig

# ==================================================
# ANA STREAMLIT ARAYÜZ
# ==================================================

uploaded_file = st.file_uploader("📂 **Excel dosyasını yükle**", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Blok(MUGEM)")
        
        if len(df.columns) >= 13:
            df.columns = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "En", "Boy", "Alan", "Tonaj",
                          "Atanacak_Saha", "Kordinat_X", "Kordinat_Y", "Erection_X", "Erection_Y"]
        elif len(df.columns) >= 11:
            df.columns = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "En", "Boy", "Alan", "Tonaj",
                          "Atanacak_Saha", "Kordinat_X", "Kordinat_Y"]
            df["Erection_X"] = np.nan
            df["Erection_Y"] = np.nan
        else:
            df.columns = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "En", "Boy", "Alan", "Tonaj"]
            df["Atanacak_Saha"] = np.nan
            df["Kordinat_X"] = np.nan
            df["Kordinat_Y"] = np.nan
            df["Erection_X"] = np.nan
            df["Erection_Y"] = np.nan
        
        for col in ["En", "Boy", "Alan", "Tonaj"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        
        for c in ["Baslangic", "Bitis", "Erection_Bas"]:
            df[c] = pd.to_datetime(df[c], dayfirst=True, errors="coerce")
        
        df = df.dropna(subset=["Baslangic", "Bitis", "Erection_Bas"])
        
        st.success(f"✅ {len(df)} blok başarıyla yüklendi!")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📦 Toplam Blok", len(df))
        col2.metric("🏗️ Toplam Tonaj", f"{df['Tonaj'].sum():.0f} t")
        col3.metric("📅 İlk Başlangıç", df["Baslangic"].min().strftime("%d.%m.%Y"))
        
        st.markdown("---")
        
        min_date = df["Baslangic"].min()
        max_date = df["Erection_Bas"].max()
        secilen_tarih = st.date_input("📅 **Plan Görüntülenecek Tarih**", value=pd.Timestamp.now(), min_value=min_date, max_value=max_date)
        
        if st.button("🔄 **Yerleşimi Hesapla ve Göster**", type="primary", use_container_width=True):
            with st.spinner("🏗️ Yerleşim hesaplanıyor..."):
                managers = yerlesim_hesapla(secilen_tarih, df)
            
            st.success(f"✅ Hesaplama tamamlandı - {secilen_tarih.strftime('%d.%m.%Y')}")
            
            fig = plan_goster(df, secilen_tarih)
            st.pyplot(fig)
            plt.close(fig)
    
    except Exception as e:
        st.error(f"❌ Hata oluştu: {str(e)}")

else:
    st.info("👈 **Lütfen Excel dosyasını yükleyin**")

st.markdown("---")
st.caption("🏗️ Blok Yerleşim Planı")
