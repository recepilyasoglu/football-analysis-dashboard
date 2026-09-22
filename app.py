import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Sayfa Ayarları
st.set_page_config(page_title="Avrupa Scout Panosu", layout="wide")
st.title("⚽ Avrupa Scout Analiz Panosu (2026/27)")
st.markdown("Understat verileriyle güncellenen Forvet, 10 Numara ve Geriden Oyun Kurucu analizleri.")

# 2. Veri Yükleme
@st.cache_data
def veri_yukle():
    try:
        df = pd.read_csv('otomatik_understat_verileri.csv')
        return df
    except Exception as e:
        return pd.DataFrame()

df = veri_yukle()

if df.empty:
    st.error("Veri dosyası bulunamadı!")
else:
    df.columns = [col.strip().lower() for col in df.columns]

    st.sidebar.header("⚙️ Analiz Filtreleri")
    lig_sutunu = 'league' if 'league' in df.columns else df.columns[0]
    secilen_ligler = st.sidebar.multiselect("Lig Seç:", options=df[lig_sutunu].unique(), default=df[lig_sutunu].unique())
    
    # Tüm gerekli kolonlar
    sut_kolonu = 'shots' if 'shots' in df.columns else 'sh'
    gol_kolonu = 'goals' if 'goals' in df.columns else 'gls'
    xg_kolonu = 'xg'
    asist_kolonu = 'assists'
    xa_kolonu = 'xa'
    kp_kolonu = 'key_passes'
    
    # Yeni Savunma/Oyun Kurulumu Kolonları
    xgchain_kolonu = 'xgchain' if 'xgchain' in df.columns else 'xg_chain'
    xgbuildup_kolonu = 'xgbuildup' if 'xgbuildup' in df.columns else 'xg_buildup'
    sure_kolonu = 'time' if 'time' in df.columns else 'min'

    min_sure = st.sidebar.slider("Minimum Oynama Süresi (Dakika):", 0, 3000, 300, 50)

    # Veriyi süreye ve lige göre filtrele
    df_filtre = df[(df[lig_sutunu].isin(secilen_ligler))].copy()
    
    # Sayısal dönüşümler
    sayisal_kolonlar = [gol_kolonu, xg_kolonu, sut_kolonu, asist_kolonu, xa_kolonu, kp_kolonu, xgchain_kolonu, xgbuildup_kolonu, sure_kolonu]
    for col in sayisal_kolonlar:
        if col in df_filtre.columns:
            df_filtre[col] = pd.to_numeric(df_filtre[col], errors='coerce').fillna(0)
        else:
            df_filtre[col] = 0

    df_filtre = df_filtre[df_filtre[sure_kolonu] >= min_sure]

    df_filtre['bitiricilik_deltasi'] = (df_filtre[gol_kolonu] - df_filtre[xg_kolonu]).round(2)
    df_filtre['asist_deltasi'] = (df_filtre[asist_kolonu] - df_filtre[xa_kolonu]).round(2)
    
    oyuncu_kolonu = 'player' if 'player' in df.columns else 'player_name'
    takim_kolonu = 'team' if 'team' in df.columns else 'team_title'

    # --- YENİ 3 SEKME (TABS) YAPISI ---
    tab1, tab2, tab3 = st.tabs(["🎯 Keskin Nişancılar", "🧠 10 Numaralar & Kanatlar", "🛡️ Gizli Kahramanlar (Stoper & 6 Numara)"])

    # SEKME 1: BİTİRİCİLİK
    with tab1:
        st.subheader("Şut Hacmi vs Bitiricilik Deltası (Gol - xG)")
        fig_gol = px.scatter(
            df_filtre.sort_values(by='bitiricilik_deltasi', ascending=False), 
            x=sut_kolonu, y='bitiricilik_deltasi', color=lig_sutunu, size=gol_kolonu,
            hover_name=oyuncu_kolonu, hover_data={takim_kolonu: True, gol_kolonu: True, xg_kolonu: True},
            labels={sut_kolonu: 'Toplam Şut', 'bitiricilik_deltasi': 'Bitiricilik Deltası'},
            size_max=20, template='plotly_white'
        )
        st.plotly_chart(fig_gol, use_container_width=True)

    # SEKME 2: YARATICILIK
    with tab2:
        st.subheader("Kilit Pas vs Asist Deltası (Asist - xA)")
        fig_asist = px.scatter(
            df_filtre.sort_values(by='asist_deltasi', ascending=False), 
            x=kp_kolonu, y='asist_deltasi', color=lig_sutunu, size=asist_kolonu,
            hover_name=oyuncu_kolonu, hover_data={takim_kolonu: True, asist_kolonu: True, xa_kolonu: True},
            labels={kp_kolonu: 'Kilit Pas', 'asist_deltasi': 'Asist Deltası'},
            size_max=20, template='plotly_white'
        )
        st.plotly_chart(fig_asist, use_container_width=True)

    # SEKME 3: GERİDEN OYUN KURMA (YENİ!)
    with tab3:
        st.subheader("Oyun Kurulumuna Katkı: xGBuildup vs xGChain")
        st.markdown("""
        **🔍 Nasıl Okunmalı?**
        - **xGChain (Y Dikey Ekseni):** Oyuncunun dahil olduğu *tüm* atakların toplam şut kalitesi.
        - **xGBuildup (X Yatay Ekseni):** Oyuncunun *şut çekmeden ve son pası vermeden* başlattığı atakların kalitesi.  
        👉 *X ekseninde en sağda olan oyuncular, takımlarını geriden kusursuz çıkaran elit Stoperler ve 6 Numaralardır!*
        """)
        fig_build = px.scatter(
            df_filtre.sort_values(by=xgbuildup_kolonu, ascending=False),
            x=xgbuildup_kolonu, y=xgchain_kolonu, color=lig_sutunu,
            hover_name=oyuncu_kolonu, hover_data={takim_kolonu: True, sure_kolonu: True},
            labels={xgbuildup_kolonu: 'xGBuildup (Geriden Oyun Kurma)', xgchain_kolonu: 'xGChain (Toplam Atak Katkısı)'},
            template='plotly_white'
        )
        st.plotly_chart(fig_build, use_container_width=True)

    # Alt Kısım: Genel Tablo
    st.subheader(f"📋 Kapsamlı Veri Tablosu ({len(df_filtre)} Oyuncu)")
    gosterilecek_tablo = df_filtre[[oyuncu_kolonu, takim_kolonu, lig_sutunu, sure_kolonu, xgbuildup_kolonu, xgchain_kolonu, gol_kolonu, xg_kolonu, kp_kolonu, xa_kolonu]]
    # Tabloyu varsayılan olarak Oyun Kurma (xGBuildup) gücüne göre sıralayalım
    st.dataframe(gosterilecek_tablo.sort_values(by=xgbuildup_kolonu, ascending=False), use_container_width=True)
