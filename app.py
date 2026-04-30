import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
from io import BytesIO

warnings.filterwarnings("ignore")

st.set_page_config(page_title="Blok Yerleşim Planı", layout="wide")

st.title("🏗️ BLOK YERLEŞİM PLANI")
st.markdown("---")

uploaded_file = st.file_uploader("📂 **Excel dosyasını yükle**", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, sheet_name="Blok(MUGEM)")
    
    # SÜTUN ADLARINI DÜZENLE (senin Excel'ine göre)
    df.columns = [
        "Blok", "Baslangic", "Bitis", "Erection_Bas",
        "En", "Boy", "Alan", "Tonaj",
        "Atanacak_Saha", "Kordinat_X", "Kordinat_Y",
        "Erection_X", "Erection_Y"
    ]
    
    # Tarih sütunlarını dönüştür
    for c in ["Baslangic", "Bitis", "Erection_Bas"]:
        df[c] = pd.to_datetime(df[c], dayfirst=True, errors="coerce")
    
    st.success(f"✅ {len(df)} blok başarıyla yüklendi!")
    
    # Temel bilgiler
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Toplam Blok", len(df))
    col2.metric("🏗️ Toplam Tonaj", f"{df['Tonaj'].sum():.0f} t")
    col3.metric("📅 İlk Başlangıç", df["Baslangic"].min().strftime("%d.%m.%Y"))
    
    # Veriyi göster
    with st.expander("📋 Yüklenen Veri (ilk 10 satır)"):
        st.dataframe(df.head(10))
    
    # Manuel atama yapılan bloklar
    manuel_atama = df[df["Atanacak_Saha"].notna()]
    if len(manuel_atama) > 0:
        st.info(f"📌 **Manuel atama yapılan blok:** {len(manuel_atama)} adet")
        st.dataframe(manuel_atama[["Blok", "Atanacak_Saha", "Kordinat_X", "Kordinat_Y"]])
    
else:
    st.info("👈 **Lütfen Excel dosyasını yükleyin**")
    st.markdown("""
    ### 📋 Excel Dosyası Formatı:
    
    | Sütun | Açıklama |
    |-------|----------|
    | Blok Adı | Blok kimliği |
    | Başlangıç | Üretim başlangıç tarihi |
    | Bitiş | Üretim bitiş tarihi |
    | Erection Başlangıç | Montaj başlangıç tarihi |
    | En, Boy, Alan, Tonaj | Blok ölçüleri |
    | Atanacağı Saha | (Opsiyonel) Manuel saha ataması |
    | Kordinatlar(x/y) | (Opsiyonel) Manuel koordinat |
    | Erection(x/y) | (Opsiyonel) MUGEM koordinatları |
    """)

st.markdown("---")
st.caption("🏗️ Blok Yerleşim Planı | Excel'inizdeki sütun adları otomatik düzenlendi")
