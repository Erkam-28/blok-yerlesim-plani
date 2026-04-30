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
st.title("🏗️ BLOK YERLEŞİM PLANI")
st.markdown("---")

# ==================================================
# SABİTLER
# ==================================================

ISKELE = 3
DARBOGAZ_PCT = 80
STEP = 0.5
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
DUZ_KIZAK_MUGEM_X_BASLANGIC = 101.0

A6_TAM_U = 230.0
A6_G = 40.3
A6_BLOK_U = 111.0
A6_EYUL = datetime(2026, 9, 1)

def snap(v):
    return round(round(v / STEP) * STEP, 10)

# ==================================================
# ARAYÜZ
# ==================================================

uploaded_file = st.file_uploader("📂 **Excel dosyasını yükle**", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Blok(MUGEM)")
        
        # Sütun adlarını düzenle
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
        
        # Sayısal sütunları temizle
        for col in ["En", "Boy", "Alan", "Tonaj"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(",", ".").str.strip()
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        
        # Tarih sütunlarını dönüştür
        for c in ["Baslangic", "Bitis", "Erection_Bas"]:
            df[c] = pd.to_datetime(df[c], dayfirst=True, errors="coerce")
        
        st.success(f"✅ {len(df)} blok başarıyla yüklendi!")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📦 Toplam Blok", len(df))
        col2.metric("🏗️ Toplam Tonaj", f"{df['Tonaj'].sum():.0f} t")
        col3.metric("📅 İlk Başlangıç", df["Baslangic"].min().strftime("%d.%m.%Y"))
        
        st.dataframe(df.head(10))
        
    except Exception as e:
        st.error(f"Hata: {str(e)}")

else:
    st.info("👈 Lütfen Excel dosyasını yükleyin")
    st.markdown("""
    ### 📋 Gerekli Sütunlar:
    - Blok
    - Başlangıç
    - Bitiş
    - Erection Başlangıç
    - En, Boy, Alan, Tonaj
    """)

st.caption("🏗️ Blok Yerleşim Planı")
