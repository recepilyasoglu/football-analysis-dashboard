import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Scout Pano", layout="wide")
st.title("⚽ Dinamik Oyuncu Scout Panosu")

# --- 2. VERİ YÜKLEME VE İŞLEME ---
@st.cache_data
def verileri_hazirla():
    try:
        # Ana istatistik verisini oku
        df_istatistik = pd.read_csv('otomatik_understat_verileri.csv') 
        
        # Karakter sorununu çözdüğümüz format
        try:
            df_yas = pd.read_csv('oyuncu_dogum_tarihleri.csv', encoding='utf-8-sig')
        except UnicodeDecodeError:
            df_yas = pd.read_csv('oyuncu_dogum_tarihleri.csv', encoding='windows-1254')
        
        # İki veriyi birleştir
        df_merge = pd.merge(df_istatistik, df_yas, on='player', how='inner')
        
        # Yaş hesaplama
        df_merge['birth_date'] = pd.to_datetime(df_merge['birth_date'], errors='coerce', dayfirst=True)
        bugun = pd.to_datetime("today")
        df_merge['Age'] = (bugun - df_merge['birth_date']).dt.days // 365
        
        # --- PER 90 HESAPLAMALARI (90 Dakika Standardizasyonu) ---
        # time kolonu sıfır olanlarda hata almamak için ufak bir kontrol
        if 'time' in df_merge.columns:
            sure_carpan = 90 / df_merge['time']
            df_merge['xG_90'] = round(df_merge['xG'] * sure_carpan, 2)
            df_merge['xA_90'] = round(df_merge['xA'] * sure_carpan, 2)
            df_merge['shots_90'] = round(df_merge['shots'] * sure_carpan, 2)
            df_merge['key_passes_90'] = round(df_merge['key_passes'] * sure_carpan, 2)
            df_merge['xGChain_90'] = round(df_merge['xGChain'] * sure_carpan, 2)
            df_merge['xGBuildup_90'] = round(df_merge['xGBuildup'] * sure_carpan, 2)
            df_merge['goals_90'] = round(df_merge['goals'] * sure_carpan, 2)
            df_merge['assists_90'] = round(df_merge['assists'] * sure_carpan, 2)

        return df_merge
    except Exception as e:
        st.error(f"Veri yüklenirken hata oluştu: {e}")
        return pd.DataFrame()

df = verileri_hazirla()

if not df.empty:
    # --- 3. YAN MENÜ VE FİLTRELER ---
    st.sidebar.header("🔍 Filtreleme Seçenekleri")
    
    # Lig Filtresi
    if 'league' in df.columns:
        secili_ligler = st.sidebar.multiselect("Lig Seçin", df['league'].unique(), default=df['league'].unique())
    else:
        secili_ligler = []
    
    # U23 Filtresi
    u23_sart = st.sidebar.checkbox("Sadece U23 (23 Yaş ve Altı) Oyuncuları Göster", value=True)
    
    # Süre Filtresi
    min_dakika = 0
    if 'time' in df.columns:
        min_dakika = st.sidebar.slider("Minimum Oynama Süresi (Dakika)", 0, int(df['time'].max()), 500)
    
    # Filtreleri Uygulama
    df_filtrelenmis = df.copy()
    if secili_ligler:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['league'].isin(secili_ligler)]
    if u23_sart:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['Age'] <= 23]
    if 'time' in df.columns:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['time'] >= min_dakika]

    # --- 4. SEKME (TAB) YAPISI ---
    tab1, tab2, tab3, tab4 = st.tabs(["Keskin Nişancılar (Gol & xG)", "10 Numaralar & Kanatlar (Asist & xA)", "Gizli Kahramanlar (xGBuildup)", "🎯 Oyuncu Analiz Radarı"])

    # TAB 1: Keskin Nişancılar
    with tab1:
        st.subheader("Gol vs xG (90 Dakika Başına)")
        fig1 = px.scatter(df_filtrelenmis, x='xG_90', y='goals_90', hover_name='player',
                          hover_data=['team', 'Age'], color='team',
                          labels={'xG_90': 'Beklenen Gol (xG) - 90dk', 'goals_90': 'Atılan Gol - 90dk'})
        fig1.add_shape(type='line', x0=0, y0=0, x1=df_filtrelenmis['xG_90'].max(), y1=df_filtrelenmis['xG_90'].max(),
                       line=dict(color='Red', dash='dash'))
        st.plotly_chart(fig1, use_container_width=True)

    # TAB 2: 10 Numaralar & Kanatlar
    with tab2:
        st.subheader("Asist vs xA (90 Dakika Başına)")
        fig2 = px.scatter(df_filtrelenmis, x='xA_90', y='assists_90', hover_name='player',
                          hover_data=['team', 'Age'], color='team',
                          labels={'xA_90': 'Beklenen Asist (xA) - 90dk', 'assists_90': 'Yapılan Asist - 90dk'})
        fig2.add_shape(type='line', x0=0, y0=0, x1=df_filtrelenmis['xA_90'].max(), y1=df_filtrelenmis['xA_90'].max(),
                       line=dict(color='Red', dash='dash'))
        st.plotly_chart(fig2, use_container_width=True)

    # TAB 3: Gizli Kahramanlar
    with tab3:
        st.subheader("xGChain vs xGBuildup (90 Dakika Başına)")
        fig3 = px.scatter(df_filtrelenmis, x='xGBuildup_90', y='xGChain_90', hover_name='player',
                          hover_data=['team', 'Age'], color='team',
                          labels={'xGBuildup_90': 'Oyun Kurulumu Katkısı (xGBuildup) - 90dk', 'xGChain_90': 'Hücum Katkısı (xGChain) - 90dk'})
        st.plotly_chart(fig3, use_container_width=True)

    # TAB 4: Radar Grafiği
    with tab4:
        st.subheader("Bireysel Profil Analizi")
        if not df_filtrelenmis.empty:
            secilen_oyuncu = st.selectbox(
                "Detaylı radar analizi için listeden bir oyuncu seçin:", 
                df_filtrelenmis['player'].unique()
            )
            
            if secilen_oyuncu:
                oyuncu_verisi = df_filtrelenmis[df_filtrelenmis['player'] == secilen_oyuncu].iloc[0]
                
                # Radar metrikleri (Artık Per 90 verileri kullanılıyor)
                kategoriler = ['xG (90dk)', 'xA (90dk)', 'Şut (90dk)', 'Kilit Pas (90dk)', 'xGChain (90dk)', 'xGBuildup (90dk)']
                degerler = [
                    oyuncu_verisi.get('xG_90', 0), 
                    oyuncu_verisi.get('xA_90', 0), 
                    oyuncu_verisi.get('shots_90', 0), 
                    oyuncu_verisi.get('key_passes_90', 0), 
                    oyuncu_verisi.get('xGChain_90', 0), 
                    oyuncu_verisi.get('xGBuildup_90', 0)
                ]
                
                fig4 = go.Figure()
                fig4.add_trace(go.Scatterpolar(
                    r=degerler,
                    theta=kategoriler,
                    fill='toself',
                    fillcolor='rgba(0, 204, 150, 0.4)',
                    line=dict(color='#00cc96', width=2),
                    name=secilen_oyuncu
                ))
                
                fig4.update_layout(
                    polar=dict(radialaxis=dict(visible=True, showline=False)),
                    showlegend=False,
                    title=dict(text=f"<b>{secilen_oyuncu}</b> - Profil Analizi (90 Dk Başına)", x=0.5, font=dict(size=20))
                )
                
                st.plotly_chart(fig4, use_container_width=True)

    # Filtrelenmiş Tabloyu Sayfanın Altında Göster
    st.markdown("---")
    st.subheader(f"📋 Seçili Filtrelere Göre Oyuncu Listesi ({len(df_filtrelenmis)} Oyuncu)")
    
    # Tabloyu daha okunaklı göstermek için formatlama
    gosterilecek_kolonlar = ['player', 'team', 'league', 'Age', 'time', 'xG_90', 'xA_90', 'goals_90', 'assists_90']
    mevcut_kolonlar = [col for col in gosterilecek_kolonlar if col in df_filtrelenmis.columns]
    
    st.dataframe(df_filtrelenmis[mevcut_kolonlar].style.format({'xG_90': '{:.2f}', 'xA_90': '{:.2f}'}))
