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
    
    # Sütun adlarını temizle (başındaki/sonundaki boşlukları kaldır)
    df.columns = df.columns.str.strip()
    
    st.success(f"✅ {len(df)} blok başarıyla yüklendi!")
    
    # Veriyi göster
    st.subheader("📋 Yüklenen Veri")
    st.dataframe(df.head(10))
    
    # Temel bilgiler
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Toplam Blok", len(df))
    col2.metric("🏗️ Toplam Tonaj", f"{df['Tonaj'].sum():.0f} t" if 'Tonaj' in df.columns else "?")
    
    # Baslangic sütunu varsa göster
    if 'Baslangic' in df.columns:
        col3.metric("📅 Başlangıç", df["Baslangic"].min().strftime("%d.%m.%Y"))
    else:
        col3.metric("📅 Sütunlar", f"Bulunan: {', '.join(df.columns[:5])}...")
    
    # Hangi sütunların olduğunu göster
    with st.expander("🔍 Excel'deki sütunlar"):
        st.write(list(df.columns))
    
else:
    st.info("👈 **Lütfen Excel dosyasını yükleyin**")
    st.markdown("""
    ### 📋 Excel Dosyası Formatı:
    - **Blok** - Blok adı
    - **Baslangic** - Başlangıç tarihi
    - **Bitis** - Bitiş tarihi  
    - **Erection_Bas** - Erection başlangıç
    - **En, Boy, Alan, Tonaj**
    """)

st.markdown("---")
st.caption("🏗️ Blok Yerleşim Planı")
