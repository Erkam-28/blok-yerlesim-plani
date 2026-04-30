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
st.title("🏗️ BLOK YERLEŞİM PLANI - TAM VERSİYON")
st.markdown("---")

# ==================================================
# SABİTLER (SADECE TEMEL OLANLAR)
# ==================================================

ISKELE = 3
STEP = 0.5

def snap(v):
    return round(round(v / STEP) * STEP, 10)

# ==================================================
# ANA ARAYÜZ
# ==================================================

uploaded_file = st.file_uploader("📂 **Excel dosyasını yükle**", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file, sheet_name="Blok(MUGEM)")
        
        # Sütun adlarını düzenle
        df.columns = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "En", "Boy", "Alan", "Tonaj",
                      "Atanacak_Saha", "Kordinat_X", "Kordinat_Y", "Erection_X", "Erection_Y"]
        
        # Sayısal sütunları temizle
        for col in ["En", "Boy", "Alan", "Tonaj"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        
        # Tarih sütunlarını dönüştür
        for c in ["Baslangic", "Bitis", "Erection_Bas"]:
            df[c] = pd.to_datetime(df[c], dayfirst=True, errors="coerce")
        
        # Geçersiz satırları temizle
        df = df.dropna(subset=["Baslangic", "Bitis", "Erection_Bas"])
        
        st.success(f"✅ {len(df)} blok başarıyla yüklendi!")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📦 Toplam Blok", len(df))
        col2.metric("🏗️ Toplam Tonaj", f"{df['Tonaj'].sum():.0f} t")
        col3.metric("📅 İlk Başlangıç", df["Baslangic"].min().strftime("%d.%m.%Y"))
        
        st.markdown("---")
        
        # Tarih seçici
        min_date = df["Baslangic"].min()
        max_date = df["Erection_Bas"].max()
        secilen_tarih = st.date_input("📅 **Plan Görüntülenecek Tarih**", value=pd.Timestamp.now(), min_value=min_date, max_value=max_date)
        
        # Basit aktif blok listesi
        if st.button("🔄 **Aktif Blokları Göster**", type="primary"):
            tarih_ts = pd.Timestamp(secilen_tarih)
            aktif_bloklar = df[(df["Baslangic"] <= tarih_ts) & (df["Erection_Bas"] > tarih_ts)]
            
            st.subheader(f"📊 {secilen_tarih.strftime('%d.%m.%Y')} Tarihinde Aktif Bloklar")
            st.metric("Aktif Blok Sayısı", len(aktif_bloklar))
            st.dataframe(aktif_bloklar[["Blok", "Baslangic", "Bitis", "En", "Boy", "Tonaj"]])
            
            # Basit grafik
            fig, ax = plt.subplots(figsize=(10, 4))
            if len(aktif_bloklar) > 0:
                ax.bar(aktif_bloklar["Blok"].head(20), aktif_bloklar["Tonaj"].head(20))
                ax.set_xticklabels(aktif_bloklar["Blok"].head(20), rotation=45, ha="right", fontsize=8)
                ax.set_ylabel("Tonaj (t)")
                ax.set_title(f"Aktif Blokların Tonaj Dağılımı - {secilen_tarih.strftime('%d.%m.%Y')}")
                st.pyplot(fig)
                plt.close(fig)
            else:
                st.info("Bu tarihte aktif blok bulunmamaktadır.")
        
        # Veri önizleme
        with st.expander("📋 Tüm Bloklar (ilk 20 satır)"):
            st.dataframe(df[["Blok", "Baslangic", "Bitis", "En", "Boy", "Tonaj"]].head(20))
        
        # Excel indir
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Veriler")
        
        st.download_button(
            label="📥 **Excel Çıktısını İndir**",
            data=output.getvalue(),
            file_name="blok_verileri.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    except Exception as e:
        st.error(f"❌ Hata oluştu: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

else:
    st.info("👈 **Lütfen Excel dosyasını yükleyin**")
    st.markdown("""
    ### 📋 Gerekli Sütunlar:
    - Blok Adı
    - Başlangıç
    - Bitiş
    - Erection Başlangıç
    - En, Boy, Alan, Tonaj
    """)

st.caption("🏗️ Blok Yerleşim Planı")
