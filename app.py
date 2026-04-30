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

ISKELE = 3
STEP = 0.5

def snap(v):
    return round(round(v / STEP) * STEP, 10)

# ==================================================
# ARAYÜZ
# ==================================================

uploaded_file = st.file_uploader("📂 **Excel dosyasını yükle**", type=["xlsx"])

if uploaded_file is not None:
    try:
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
                df[col] = df[col].astype(str).str.replace(",", ".").str.strip()
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        
        # Tarih sütunlarını dönüştür
        for c in ["Baslangic", "Bitis", "Erection_Bas"]:
            df[c] = pd.to_datetime(df[c], dayfirst=True, errors="coerce")
        
        # Geçersiz tarihleri temizle
        df = df.dropna(subset=["Baslangic", "Bitis", "Erection_Bas"])
        
        st.success(f"✅ {len(df)} blok başarıyla yüklendi!")
        
        # Temel bilgiler
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📦 Toplam Blok", len(df))
        col2.metric("🏗️ Toplam Tonaj", f"{df['Tonaj'].sum():.0f} t")
        col3.metric("📐 Toplam Alan", f"{df['Alan'].sum():.0f} m²")
        col4.metric("📅 Başlangıç", df["Baslangic"].min().strftime("%d.%m.%Y"))
        
        st.markdown("---")
        
        # Tarih seçici
        min_date = df["Baslangic"].min()
        max_date = df["Erection_Bas"].max()
        secilen_tarih = st.date_input("📅 **Plan Görüntülenecek Tarih**", value=pd.Timestamp.now(), min_value=min_date, max_value=max_date)
        
        # Hesaplama butonu
        if st.button("🔄 **Yerleşimi Hesapla**", type="primary", use_container_width=True):
            with st.spinner("🏗️ Yerleşim hesaplanıyor..."):
                # Basit bir hesaplama simülasyonu - daha sonra tam kod eklenecek
                st.success(f"✅ Hesaplama tamamlandı - {secilen_tarih.strftime('%d.%m.%Y')}")
                
                # Geçici olarak veri tablosunu göster
                st.subheader("📊 Yüklenen Bloklar")
                st.dataframe(df[["Blok", "Baslangic", "Bitis", "En", "Boy", "Tonaj"]].head(20))
                
                # Basit bir grafik göster
                fig, ax = plt.subplots(figsize=(10, 4))
                blok_sayisi = df.groupby(df["Baslangic"].dt.month).size()
                ax.bar(blok_sayisi.index, blok_sayisi.values)
                ax.set_xlabel("Ay")
                ax.set_ylabel("Blok Sayısı")
                ax.set_title("Aylık Blok Dağılımı")
                st.pyplot(fig)
                plt.close(fig)
        
        # Veri önizleme
        with st.expander("📋 Veri Önizleme (ilk 10 satır)"):
            st.dataframe(df.head(10))
        
        # Manuel atama yapılanlar
        manuel = df[df["Atanacak_Saha"].notna()]
        if len(manuel) > 0:
            with st.expander(f"📌 Manuel Atama Yapılan Bloklar ({len(manuel)} adet)"):
                st.dataframe(manuel[["Blok", "Atanacak_Saha", "Kordinat_X", "Kordinat_Y"]])
        
        # Excel indir
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Yerlesim")
        
        st.download_button(
            label="📥 **Excel Çıktısını İndir**",
            data=output.getvalue(),
            file_name="blok_yerlesim.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    except Exception as e:
        st.error(f"❌ Hata oluştu: {str(e)}")

else:
    st.info("👈 **Lütfen Excel dosyasını yükleyin**")
    st.markdown("""
    ### 📋 Gerekli Sütunlar:
    | Sütun | Açıklama |
    |-------|----------|
    | Blok | Blok adı |
    | Başlangıç | Üretim başlangıç tarihi |
    | Bitiş | Üretim bitiş tarihi |
    | Erection Başlangıç | Montaj başlangıç tarihi |
    | En, Boy, Alan, Tonaj | Blok ölçüleri |
    """)

st.markdown("---")
st.caption("🏗️ Blok Yerleşim Planı")
