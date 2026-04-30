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

# ==================================================
# SABİTLER
# ==================================================

STEP = 0.5

def snap(v):
    return round(round(v / STEP) * STEP, 10)

# ==================================================
# YARDIMCI FONKSİYONLAR
# ==================================================

def aktif_blok_say(df, tarih):
    """Verilen tarihte aktif olan blokları sayar"""
    t = pd.Timestamp(tarih)
    aktif = df[(df["Baslangic"] <= t) & (df["Erection_Bas"] > t)]
    return len(aktif)

# ==================================================
# ANA ARAYÜZ
# ==================================================

uploaded_file = st.file_uploader("📂 **Excel dosyasını yükle**", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Excel'i oku
        df = pd.read_excel(uploaded_file, sheet_name="Blok(MUGEM)")
        
        # Sütun adlarını düzenle
        if len(df.columns) >= 13:
            df.columns = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "En", "Boy", "Alan", "Tonaj",
                          "Atanacak_Saha", "Kordinat_X", "Kordinat_Y", "Erection_X", "Erection_Y"]
        elif len(df.columns) >= 11:
            df.columns = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "En", "Boy", "Alan", "Tonaj",
                          "Atanacak_Saha", "Kordinat_X", "Kordinat_Y"]
            df["Erection_X"] = np.nan
            df["Erection_Y"] = np.nan
        else:
            df.columns = ["Blok", "Baslangic", "Bitis", "Erection_Bas", "En", "Boy", "Alan", "Tonaj"]
            df["Atanacak_Saha"] = np.nan
            df["Kordinat_X"] = np.nan
            df["Kordinat_Y"] = np.nan
            df["Erection_X"] = np.nan
            df["Erection_Y"] = np.nan
        
        # Sayısal sütunları temizle
        for col in ["En", "Boy", "Alan", "Tonaj"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        
        # Tarih sütunlarını dönüştür
        for c in ["Baslangic", "Bitis", "Erection_Bas"]:
            df[c] = pd.to_datetime(df[c], dayfirst=True, errors="coerce")
        
        # Geçersiz satırları temizle
        df = df.dropna(subset=["Baslangic", "Bitis", "Erection_Bas"])
        
        # Başarı mesajı
        st.success(f"✅ {len(df)} blok başarıyla yüklendi!")
        
        # Özet bilgiler
        col1, col2, col3 = st.columns(3)
        col1.metric("📦 Toplam Blok", len(df))
        col2.metric("🏗️ Toplam Tonaj", f"{df['Tonaj'].sum():.0f} t")
        col3.metric("📅 İlk Başlangıç", df["Baslangic"].min().strftime("%d.%m.%Y") if len(df) > 0 else "-")
        
        st.markdown("---")
        
        # Tarih seçici
        min_date = df["Baslangic"].min()
        max_date = df["Erection_Bas"].max()
        secilen_tarih = st.date_input("📅 **Plan Görüntülenecek Tarih**", value=pd.Timestamp.now(), min_value=min_date, max_value=max_date)
        
        # Hesaplama butonu
        if st.button("🔄 **Yerleşimi Hesapla**", type="primary", use_container_width=True):
            tarih_ts = pd.Timestamp(secilen_tarih)
            
            # Aktif blokları bul
            aktif = df[(df["Baslangic"] <= tarih_ts) & (df["Erection_Bas"] > tarih_ts)]
            
            st.subheader(f"📊 {secilen_tarih.strftime('%d.%m.%Y')} Tarihinde Aktif Bloklar")
            st.metric("Aktif Blok Sayısı", len(aktif))
            
            if len(aktif) > 0:
                st.dataframe(aktif[["Blok", "Baslangic", "Bitis", "En", "Boy", "Tonaj"]])
                
                # Basit grafik
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.bar(aktif["Blok"].head(20), aktif["Tonaj"].head(20))
                ax.set_xticklabels(aktif["Blok"].head(20), rotation=45, ha="right", fontsize=8)
                ax.set_ylabel("Tonaj (t)")
                ax.set_title("Aktif Blokların Tonaj Dağılımı")
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

st.markdown("---")
st.caption("🏗️ Blok Yerleşim Planı")
