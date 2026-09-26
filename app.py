import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Sayfa Ayarları
st.set_page_config(page_title="Scout Pano", layout="wide")
st.title("⚽ Dinamik Oyuncu Scout Panosu")

# 1. VERİ YÜKLEME VE BİRLEŞTİRME
@st.cache_data
def verileri_hazirla():
    try:
        # Ana istatistik verisini oku (Kendi dosya adını yazmayı unutma)
        # Eğer bu dosyada da karakter sorunu oluyorsa buraya da encoding='windows-1254' ekleyebilirsin
        df_istatistik = pd.read_csv('otomatik_understat_verileri.csv') 
        
        # Karakter sorununu çözdüğümüz format (Eğer windows-1254 ile kaydettiysen bunu, yoksa utf-8-sig kullan)
        # Önceki denemelerimizde windows-1254'ün işe yaradığını görmüştük
        try:
            df_yas = pd.read_csv('oyuncu_dogum_tarihleri.csv', encoding='utf-8-sig')
        except UnicodeDecodeError:
            df_yas = pd.read_csv('oyuncu_dogum_tarihleri.csv', encoding='windows-1254')
        
        # İki veriyi 'player' kolonu üzerinden birleştir
        df_merge = pd.merge(df_istatistik, df_yas, on='player', how='inner')
        
        # Doğum tarihinden otomatik yaş hesaplama (Tarih formatı sorunlarını önlemek için dayfirst=True)
        df_merge['birth_date'] = pd.to_datetime(df_merge['birth_date'], errors='coerce', dayfirst=True)
        bugun = pd.to_datetime("today")
        df_merge['Age'] = (bugun - df_merge['birth_date']).dt.days // 365
        
        return df_merge
    except Exception as e:
        st.error(f"Veri yüklenirken hata oluştu: {e}")
        return pd.DataFrame()

# Ana veriyi çağır
df = verileri_hazirla()

if not df.empty:
    # 2. YAN MENÜ VE FİLTRELER
    st.sidebar.header("🔍 Filtreleme Seçenekleri")
    
    # U23 Filtresi
    u23_sart = st.sidebar.checkbox("Sadece U23 (23 Yaş ve Altı) Oyuncuları Göster", value=True)
    
    # Süre Filtresi (Eğer verinde 'time' kolonu varsa)
    min_dakika = 0
    if 'time' in df.columns:
        min_dakika = st.sidebar.slider("Minimum Oynama Süresi (Dakika)", 0, int(df['time'].max()), 500)
    
    # Filtreleri Uygulama
    df_filtrelenmis = df.copy()
    if u23_sart:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['Age'] <= 23]
    if 'time' in df.columns:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['time'] >= min_dakika]
        
    # Filtrelenmiş Tabloyu Göster
    st.subheader(f"📋 Oyuncu Listesi ({len(df_filtrelenmis)} Oyuncu)")
    st.dataframe(df_filtrelenmis)

    # 3. RADAR GRAFİĞİ BÖLÜMÜ
    st.markdown("---")
    st.subheader("🎯 Oyuncu Analiz Radarı")
    
    if not df_filtrelenmis.empty:
        # Oyuncu seçimi
        secilen_oyuncu = st.selectbox(
            "Detaylı radar analizi için listeden bir oyuncu seçin:", 
            df_filtrelenmis['player'].unique()
        )
        
        if secilen_oyuncu:
            # Seçili oyuncunun verisini çek
            oyuncu_verisi = df_filtrelenmis[df_filtrelenmis['player'] == secilen_oyuncu].iloc[0]
            
            # Radar metrikleri
            kategoriler = ['Gol Beklentisi (xG)', 'Asist Beklentisi (xA)', 'Şut', 'Kilit Pas', 'xGChain', 'xGBuildup']
            degerler = [
                oyuncu_verisi.get('xG', 0), 
                oyuncu_verisi.get('xA', 0), 
                oyuncu_verisi.get('shots', 0), 
                oyuncu_verisi.get('key_passes', 0), 
                oyuncu_verisi.get('xGChain', 0), 
                oyuncu_verisi.get('xGBuildup', 0)
            ]
            
            # Grafiği Çizdir
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=degerler,
                theta=kategoriler,
                fill='toself',
                fillcolor='rgba(0, 204, 150, 0.4)',
                line=dict(color='#00cc96', width=2),
                name=secilen_oyuncu
            ))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, showline=False)),
                showlegend=False,
                title=dict(text=f"<b>{secilen_oyuncu}</b> - Profil Analizi", x=0.5, font=dict(size=20))
            )
            
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Mevcut filtrelere uygun oyuncu bulunamadı.")
