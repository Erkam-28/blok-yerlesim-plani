import streamlit as st
import pandas as pd
from datetime import datetime

st.title("SAHA TANIMI TESTİ")

# SAHALAR tanımını buraya kopyala (kısa versiyon)
SAHALAR = [
    {"ad": "A3 Atölyesi", "oncelik": 1,
     "kisit": lambda b, t: True,  # Geçici
     "alan": lambda t: (74.0, 32.0)},
    {"ad": "A29 Açık Saha", "oncelik": 2,
     "kisit": lambda b, t: True,
     "alan": lambda t: (120.0, 21.0)},
]

for saha in SAHALAR:
    try:
        u, g = saha["alan"](datetime.now())
        st.success(f"✅ {saha['ad']}: {u} x {g}")
    except Exception as e:
        st.error(f"❌ {saha['ad']} HATALI: {e}")
