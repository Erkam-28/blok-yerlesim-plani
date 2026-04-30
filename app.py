import streamlit as st
import pandas as pd
import numpy as np

st.title("HATA AYIKLAMA")

uploaded = st.file_uploader("Excel yükle", type=["xlsx"])

if uploaded:
    df = pd.read_excel(uploaded, sheet_name="Blok(MUGEM)")
    
    # Tüm sütunları ve ilk satırdaki değerleri göster
    st.write("### SÜTUNLAR VE İLK SATIR:")
    for col in df.columns:
        val = df[col].iloc[0]
        st.write(f"**{col}**: {val} (tip: {type(val).__name__})")
    
    # Sayısal olması gereken sütunları kontrol et
    st.write("### SAYISAL SÜTUN KONTROLÜ:")
    for col in ["En", "Boy", "Alan", "Tonaj"]:
        if col in df.columns:
            degerler = df[col].head(10).tolist()
            st.write(f"{col}: {degerler}")
            
            # Metin var mı?
            for i, val in enumerate(degerler):
                if isinstance(val, str):
                    st.error(f"❌ {col} sütununda {i}. satırda METİN: '{val}'")
