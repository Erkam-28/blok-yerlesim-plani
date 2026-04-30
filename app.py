import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Test", layout="wide")

uploaded = st.file_uploader("Excel yükle", type=["xlsx"])

if uploaded:
    df = pd.read_excel(uploaded, sheet_name="Blok(MUGEM)")
    
    # HANGİ SÜTUNLAR VAR?
    st.write("📋 SÜTUNLAR:", list(df.columns))
    
    # İLK SATIRDAKİ DEĞERLER
    st.write("📋 İLK SATIR:")
    for col in df.columns:
        st.write(f"  {col}: {df[col].iloc[0]} (tip: {type(df[col].iloc[0])})")
