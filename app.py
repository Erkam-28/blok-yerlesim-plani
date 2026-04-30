import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Polygon
from datetime import datetime
import warnings
from io import BytesIO

warnings.filterwarnings("ignore")

st.set_page_config(page_title="Blok Yerleşim Planı", layout="wide")
st.title("🏗️ BLOK YERLEŞİM PLANI - TAM VERSİYON")
st.markdown("---")

# ==================================================
# SABİTLER (SADECE TEMEL OLANLAR)
# ==================================================

ISKELE = 3
STEP = 0.5

def snap(v):
    return round(round(v / STEP) * STEP, 10)
# ==================================================
# SAHA TANIMLARI
# ==================================================

DARBOGAZ_PCT = 80
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
     "kisit": lambda b, t: (b["Tonaj"] <= 240 and b["Erection_Bas"] <= pd.Timestamp("2026-08-15")),
     "alan": lambda t: (99.35, 35.98) if t <= pd.Timestamp("2026-08-15") else (0.0, 0.0)},
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

# ==================================================
# ANA ARAYÜZ
# ==================================================

uploaded_file = st.file_uploader("📂 **Excel dosyasını yükle**", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Blok(MUGEM)")
        
        # Sütun adlarını düzenle
        df.columns = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "En", "Boy", "Alan", "Tonaj",
                      "Atanacak_Saha", "Kordinat_X", "Kordinat_Y", "Erection_X", "Erection_Y"]
        
        # Sayısal sütunları temizle
        for col in ["En", "Boy", "Alan", "Tonaj"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        
        # Tarih sütunlarını dönüştür
        for c in ["Baslangic", "Bitis", "Erection_Bas"]:
            df[c] = pd.to_datetime(df[c], dayfirst=True, errors="coerce")
        
        # Geçersiz satırları temizle
        df = df.dropna(subset=["Baslangic", "Bitis", "Erection_Bas"])
        
        st.success(f"✅ {len(df)} blok başarıyla yüklendi!")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📦 Toplam Blok", len(df))
        col2.metric("🏗️ Toplam Tonaj", f"{df['Tonaj'].sum():.0f} t")
        col3.metric("📅 İlk Başlangıç", df["Baslangic"].min().strftime("%d.%m.%Y"))
        
        st.markdown("---")
        
        # Tarih seçici
        min_date = df["Baslangic"].min()
        max_date = df["Erection_Bas"].max()
        secilen_tarih = st.date_input("📅 **Plan Görüntülenecek Tarih**", value=pd.Timestamp.now(), min_value=min_date, max_value=max_date)
        
        # Basit aktif blok listesi
        if st.button("🔄 **Aktif Blokları Göster**", type="primary"):
            tarih_ts = pd.Timestamp(secilen_tarih)
            aktif_bloklar = df[(df["Baslangic"] <= tarih_ts) & (df["Erection_Bas"] > tarih_ts)]
            
            st.subheader(f"📊 {secilen_tarih.strftime('%d.%m.%Y')} Tarihinde Aktif Bloklar")
            st.metric("Aktif Blok Sayısı", len(aktif_bloklar))
            st.dataframe(aktif_bloklar[["Blok", "Baslangic", "Bitis", "En", "Boy", "Tonaj"]])
            
            # Basit grafik
            fig, ax = plt.subplots(figsize=(10, 4))
            if len(aktif_bloklar) > 0:
                ax.bar(aktif_bloklar["Blok"].head(20), aktif_bloklar["Tonaj"].head(20))
                ax.set_xticklabels(aktif_bloklar["Blok"].head(20), rotation=45, ha="right", fontsize=8)
                ax.set_ylabel("Tonaj (t)")
                ax.set_title(f"Aktif Blokların Tonaj Dağılımı - {secilen_tarih.strftime('%d.%m.%Y')}")
                st.pyplot(fig)
                plt.close(fig)
            else:
                st.info("Bu tarihte aktif blok bulunmamaktadır.")
        
        # Veri önizleme
        with st.expander("📋 Tüm Bloklar (ilk 20 satır)"):
            st.dataframe(df[["Blok", "Baslangic", "Bitis", "En", "Boy", "Tonaj"]].head(20))
        
        # Excel indir
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Veriler")
        
        st.download_button(
            label="📥 **Excel Çıktısını İndir**",
            data=output.getvalue(),
            file_name="blok_verileri.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    except Exception as e:
        st.error(f"❌ Hata oluştu: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

else:
    st.info("👈 **Lütfen Excel dosyasını yükleyin**")
    st.markdown("""
    ### 📋 Gerekli Sütunlar:
    - Blok Adı
    - Başlangıç
    - Bitiş
    - Erection Başlangıç
    - En, Boy, Alan, Tonaj
    """)

st.caption("🏗️ Blok Yerleşim Planı")

# ==================================================
# SAHA MANAGER SINIFI (EN SONA EKLENDİ)
# ==================================================

class SahaManager:
    def __init__(self, ad):
        self.ad = ad
        self.bloklar = []

    def aktif_bloklar(self, tarih):
        t = pd.Timestamp(tarih)
        return [b for b in self.bloklar if pd.Timestamp(b["bas"]) <= t < pd.Timestamp(b["erc"])]

    def can_place(self, x, y, w, h, saha_u, saha_g, tarih, blok_erc=None):
        x, y, w, h = snap(x), snap(y), snap(w), snap(h)
        tarih_ts = pd.Timestamp(tarih)
        
        if x < 0 or y < 0:
            return False
        if x + w > saha_u + 0.01 or y + h > saha_g + 0.01:
            return False
        
        if blok_erc is not None:
            blok_erc_ts = pd.Timestamp(blok_erc)
            kontrol_bloklari = [b for b in self.bloklar if pd.Timestamp(b["bas"]) < blok_erc_ts and pd.Timestamp(b["erc"]) > tarih_ts]
        else:
            kontrol_bloklari = [b for b in self.bloklar if pd.Timestamp(b["bas"]) <= tarih_ts < pd.Timestamp(b["erc"])]
        
        for b in kontrol_bloklari:
            if (x < b["x"] + b["w"] and x + w > b["x"] and
                y < b["y"] + b["h"] and y + h > b["y"]):
                return False
        return True

    def find_spot_single(self, w, h, saha_u, saha_g, tarih, blok_erc=None):
        w, h = snap(w), snap(h)
        saha_u, saha_g = snap(saha_u), snap(saha_g)
        
        if w > saha_u or h > saha_g:
            return None
        
        y = 0.0
        while y + h <= saha_g + 0.01:
            x = 0.0
            while x + w <= saha_u + 0.01:
                if self.can_place(x, y, w, h, saha_u, saha_g, tarih, blok_erc):
                    return (x, y)
                x += STEP
            y += STEP
        return None

    def find_spot(self, w, h, saha_u, saha_g, tarih, mod="serbest", blok_erc=None):
        pos_n = self.find_spot_single(w, h, saha_u, saha_g, tarih, blok_erc)
        if pos_n:
            return pos_n[0], pos_n[1], False
        if abs(w - h) > 0.01:
            pos_r = self.find_spot_single(h, w, saha_u, saha_g, tarih, blok_erc)
            if pos_r:
                return pos_r[0], pos_r[1], True
        return None

    def add_block(self, idx, x, y, bas, erc, w_placed, h_placed):
        self.bloklar.append({
            "idx": idx, "x": snap(x), "y": snap(y),
            "w": snap(w_placed), "h": snap(h_placed),
            "bas": bas, "erc": erc,
        })

    def remove_block(self, idx):
        self.bloklar = [b for b in self.bloklar if b["idx"] != idx]


st.success("✅ SahaManager sınıfı başarıyla eklendi!")
