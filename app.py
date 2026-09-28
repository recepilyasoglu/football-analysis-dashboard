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
        df_istatistik = pd.read_csv('otomatik_understat_veri.csv') 
        
        try:
            df_yas = pd.read_csv('oyuncu_dogum_tarihleri.csv', encoding='utf-8-sig')
        except UnicodeDecodeError:
            df_yas = pd.read_csv('oyuncu_dogum_tarihleri.csv', encoding='windows-1254')
        
        # HAYAT KURTARAN DOKUNUŞ: Sütun isimlerindeki büyük/küçük harf karmaşasını bitirmek için hepsini küçük harf yapıyoruz
        df_istatistik.columns = [col.strip().lower() for col in df_istatistik.columns]
        df_yas.columns = [col.strip().lower() for col in df_yas.columns]
        
        df_merge = pd.merge(df_istatistik, df_yas, on='player', how='inner')
        
        df_merge['birth_date'] = pd.to_datetime(df_merge['birth_date'], errors='coerce', dayfirst=True)
        bugun = pd.to_datetime("today")
        df_merge['Age'] = (bugun - df_merge['birth_date']).dt.days // 365
        
        # --- PER 90 HESAPLAMALARI ---
        sure_kolonlari = ['time', 'minutes', 'min', 'dakika', 'süre', 'mins']
        mevcut_sure = next((col for col in sure_kolonlari if col in df_merge.columns), None)
        
        # Artık kolonları 'xg', 'xa' diye küçük harfle arıyoruz
        metrikler_map = {
            'xg': 'xG_90',
            'xa': 'xA_90',
            'shots': 'shots_90',
            'key_passes': 'key_passes_90',
            'xgchain': 'xGChain_90',
            'xgbuildup': 'xGBuildup_90',
            'goals': 'goals_90',
            'assists': 'assists_90'
        }
        
        for ham_kolon, per90_adi in metrikler_map.items():
            if ham_kolon in df_merge.columns:
                if mevcut_sure:
                    # Süre 0 ise 1 yap (Sıfıra bölünme hatasını engellemek için)
                    sure_carpan = 90 / df_merge[mevcut_sure].replace(0, 1)
                    df_merge[per90_adi] = round(df_merge[ham_kolon] * sure_carpan, 2)
                else:
                    df_merge[per90_adi] = df_merge[ham_kolon]
            else:
                df_merge[per90_adi] = 0

        # Eğer takım kolonu 'team_title' diye geldiyse onu standart 'team' yapalım
        if 'team_title' in df_merge.columns:
            df_merge.rename(columns={'team_title': 'team'}, inplace=True)

        return df_merge
    except Exception as e:
        st.error(f"Veri yüklenirken hata oluştu: {e}")
        return pd.DataFrame()

df = verileri_hazirla()

if not df.empty:
    # --- 3. YAN MENÜ VE FİLTRELER ---
    st.sidebar.header("🔍 Filtreleme Seçenekleri")
    
    if 'league' in df.columns:
        secili_ligler = st.sidebar.multiselect("Lig Seçin", df['league'].unique(), default=df['league'].unique())
    else:
        secili_ligler = []
    
    u23_sart = st.sidebar.checkbox("Sadece U23 (23 Yaş ve Altı) Oyuncuları Göster", value=True)
    
    sure_kolonlari = ['time', 'minutes', 'min', 'dakika', 'süre', 'mins']
    mevcut_sure = next((col for col in sure_kolonlari if col in df.columns), None)
    
    min_dakika = 0
    if mevcut_sure:
        min_dakika = st.sidebar.slider("Minimum Oynama Süresi (Dakika)", 0, int(df[mevcut_sure].max()), 500)
    
    df_filtrelenmis = df.copy()
    if secili_ligler:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['league'].isin(secili_ligler)]
    if u23_sart:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['Age'] <= 23]
    if mevcut_sure:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis[mevcut_sure] >= min_dakika]

    takim_kolonu = 'team' if 'team' in df_filtrelenmis.columns else None
    hover_liste = [takim_kolonu, 'Age'] if takim_kolonu else ['Age']

    # --- 4. SEKME (TAB) YAPISI ---
    tab1, tab2, tab3, tab4 = st.tabs(["Keskin Nişancılar (Gol & xG)", "10 Numaralar & Kanatlar (Asist & xA)", "Gizli Kahramanlar (xGBuildup)", "🎯 Oyuncu Analiz Radarı"])

    with tab1:
        st.subheader("Gol vs xG (90 Dakika Başına)")
        if not df_filtrelenmis.empty:
            fig1 = px.scatter(df_filtrelenmis, x='xG_90', y='goals_90', hover_name='player',
                              hover_data=hover_liste, color=takim_kolonu,
                              labels={'xG_90': 'Beklenen Gol (xG) - 90dk', 'goals_90': 'Atılan Gol - 90dk'})
            fig1.add_shape(type='line', x0=0, y0=0, x1=df_filtrelenmis['xG_90'].max(), y1=df_filtrelenmis['xG_90'].max(),
                           line=dict(color='Red', dash='dash'))
            st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader("Asist vs xA (90 Dakika Başına)")
        if not df_filtrelenmis.empty:
            fig2 = px.scatter(df_filtrelenmis, x='xA_90', y='assists_90', hover_name='player',
                              hover_data=hover_liste, color=takim_kolonu,
                              labels={'xA_90': 'Beklenen Asist (xA) - 90dk', 'assists_90': 'Yapılan Asist - 90dk'})
            fig2.add_shape(type='line', x0=0, y0=0, x1=df_filtrelenmis['xA_90'].max(), y1=df_filtrelenmis['xA_90'].max(),
                           line=dict(color='Red', dash='dash'))
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("xGChain vs xGBuildup (90 Dakika Başına)")
        if not df_filtrelenmis.empty:
            fig3 = px.scatter(df_filtrelenmis, x='xGBuildup_90', y='xGChain_90', hover_name='player',
                              hover_data=hover_liste, color=takim_kolonu,
                              labels={'xGBuildup_90': 'Oyun Kurulumu (xGBuildup) - 90dk', 'xGChain_90': 'Hücum Katkısı (xGChain) - 90dk'})
            st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        st.subheader("Bireysel Profil Analizi")
        if not df_filtrelenmis.empty:
            secilen_oyuncu = st.selectbox("Detaylı radar analizi için listeden bir oyuncu seçin:", df_filtrelenmis['player'].unique())
            
            if secilen_oyuncu:
                oyuncu_verisi = df_filtrelenmis[df_filtrelenmis['player'] == secilen_oyuncu].iloc[0]
                
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
                    r=degerler, theta=kategoriler, fill='toself', fillcolor='rgba(0, 204, 150, 0.4)',
                    line=dict(color='#00cc96', width=2), name=secilen_oyuncu
                ))
                
                fig4.update_layout(
                    polar=dict(radialaxis=dict(visible=True, showline=False)),
                    showlegend=False,
                    title=dict(text=f"<b>{secilen_oyuncu}</b> - Profil Analizi", x=0.5, font=dict(size=20))
                )
                st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")
    st.subheader(f"📋 Seçili Filtrelere Göre Oyuncu Listesi ({len(df_filtrelenmis)} Oyuncu)")
    
    gosterilecek_kolonlar = ['player', takim_kolonu, 'league', 'Age', mevcut_sure, 'xG_90', 'xA_90', 'goals_90', 'assists_90']
    mevcut_kolonlar = [col for col in gosterilecek_kolonlar if col and col in df_filtrelenmis.columns]
    
    st.dataframe(df_filtrelenmis[mevcut_kolonlar].style.format({col: '{:.2f}' for col in ['xG_90', 'xA_90', 'goals_90', 'assists_90'] if col in mevcut_kolonlar}))
