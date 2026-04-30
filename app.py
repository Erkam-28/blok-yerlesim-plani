import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("BLOK YERLEŞİM PLANI")

uploaded = st.file_uploader("Excel yükle", type=["xlsx"])

if uploaded:
    df = pd.read_excel(uploaded, sheet_name="Blok(MUGEM)")
    
    # Sütun adlarını düzenle
    df.columns = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "En", "Boy", "Alan", "Tonaj",
                  "Atanacak_Saha", "Kordinat_X", "Kordinat_Y", "Erection_X", "Erection_Y"]
    
    st.success(f"{len(df)} blok yüklendi")
    st.dataframe(df)
    
    # Basit bir grafik
    fig, ax = plt.subplots()
    ax.bar(df["Blok"].head(10), df["Tonaj"].head(10))
    ax.set_xticklabels(df["Blok"].head(10), rotation=45)
    st.pyplot(fig)
