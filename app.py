import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

st.title("BLOK YERLEŞİM PLANI - TEST")

uploaded = st.file_uploader("Excel yükle", type=["xlsx"])

if uploaded:
    df = pd.read_excel(uploaded, sheet_name="Blok(MUGEM)")
    
    # Sütun adlarını düzenle
    df.columns = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "En", "Boy", "Alan", "Tonaj",
                  "Atanacak_Saha", "Kordinat_X", "Kordinat_Y", "Erection_X", "Erection_Y"]
    
    # Tarihleri dönüştür
    for c in ["Baslangic", "Bitis", "Erection_Bas"]:
        df[c] = pd.to_datetime(df[c], dayfirst=True, errors="coerce")
    
    st.success(f"{len(df)} blok yüklendi")
    
    # ========== SAHA TANIMINI EKLE ==========
    SAHALAR_TEST = [
        {"ad": "A3 Atölyesi", "alan": lambda t: (74.0, 32.0)},
        {"ad": "A29 Açık Saha", "alan": lambda t: (120.0, 21.0)},
    ]
    
    # SAHA TANIMINI TEST ET
    st.subheader("Saha Tanım Testi")
    for saha in SAHALAR_TEST:
        try:
            u, g = saha["alan"](datetime.now())
            st.write(f"✅ {saha['ad']}: {u} x {g}")
        except Exception as e:
            st.error(f"❌ {saha['ad']}: {e}")
    
    # ========== BASİT YERLEŞİM HESAPLA ==========
    st.subheader("Yerleşim Testi")
    
    try:
        tarih = pd.Timestamp.now()
        aktif = df[(df["Baslangic"] <= tarih) & (df["Erection_Bas"] > tarih)]
        st.write(f"Aktif blok sayısı: {len(aktif)}")
        st.dataframe(aktif[["Blok", "Baslangic", "Bitis", "Erection_Bas"]])
    except Exception as e:
        st.error(f"Yerleşim hatası: {e}")
