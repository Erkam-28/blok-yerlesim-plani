import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Blok Yerleşim Planı", layout="wide")

st.title("🏗️ BLOK YERLEŞİM PLANI")

uploaded_file = st.file_uploader("📂 Excel dosyasını yükle", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, sheet_name="Blok(MUGEM)")
    st.success(f"✅ {len(df)} blok yüklendi!")
    st.dataframe(df.head(10))
else:
    st.info("👈 Lütfen Excel dosyasını yükleyin")
