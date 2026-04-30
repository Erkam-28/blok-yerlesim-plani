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

# =============================================
# SABİTLER
# =============================================

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

TRANSFER_RULES = {
    "A3 Atölyesi": {"size": (24, 12), "rotate": True},
    "A4 Atölyesi": {"size": (24, 12), "rotate": True},
    "A3 Atölyesi(Jig)": None,
    "A6 Atölyesi": {"size": (12, 27), "rotate": False},
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

def snap(v):
    return round(round(v / STEP) * STEP, 10)

def rect_overlaps(ax1, ay1, ax2, ay2, bx1, by1, bx2, by2):
    if ax2 <= bx1 + 0.001: return False
    if ax1 >= bx2 - 0.001: return False
    if ay2 <= by1 + 0.001: return False
    if ay1 >= by2 - 0.001: return False
    return True

def istif_icinde_mi(x, y, w, h):
    for cx, cy in [(x, y), (x+w, y), (x, y+h), (x+w, y+h)]:
        if cx < 0 or cy < 0 or cy > ISTIF_Y_UST: return False
        if cx > ISTIF_X_ALT + ISTIF_EGIM * cy + 0.001: return False
    return True

st.info("👈 Lütfen Excel dosyasını yükleyin")
st.markdown("""
### 📋 Excel Dosyası Formatı:
- **Blok** - Blok adı
- **Baslangic** - Başlangıç tarihi
- **Bitis** - Bitiş tarihi  
- **Erection_Bas** - Erection başlangıç
- **En, Boy, Alan, Tonaj**
""")

st.caption("🏗️ Blok Yerleşim Planı")
