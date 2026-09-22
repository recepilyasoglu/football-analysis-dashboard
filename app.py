import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Sayfa Ayarları
st.set_page_config(page_title="Avrupa Scout Panosu", layout="wide")
st.title("⚽ Avrupa Scout Analiz Panosu (2026/27)")
st.markdown("Understat verileriyle güncellenen Forvet ve Oyun Kurucu (Playmaker) analizleri.")

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
    # Sütun isimlerini standartlaştırma
    df.columns = [col.strip().lower() for col in df.columns]

    st.sidebar.header("⚙️ Analiz Filtreleri")
    
    lig_sutunu = 'league' if 'league' in df.columns else df.columns[0]
    secilen_ligler = st.sidebar.multiselect("Lig Seç:", options=df[lig_sutunu].unique(), default=df[lig_sutunu].unique())
    
    # Tüm gerekli kolonların varlığını kontrol etme ve dönüştürme
    sut_kolonu = 'shots' if 'shots' in df.columns else 'sh'
    gol_kolonu = 'goals' if 'goals' in df.columns else 'gls'
    xg_kolonu = 'xg'
    asist_kolonu = 'assists'
    xa_kolonu = 'xa'
    kp_kolonu = 'key_passes'
    
    min_aksiyon = st.sidebar.slider("Minimum Şut / Kilit Pas Hacmi:", 1, 50, 10, 1)

    # Veriyi filtrele (şut veya kilit pası min değerden büyük olanlar)
    df_filtre = df[(df[lig_sutunu].isin(secilen_ligler))].copy()
    
    for col in [gol_kolonu, xg_kolonu, sut_kolonu, asist_kolonu, xa_kolonu, kp_kolonu]:
        df_filtre[col] = pd.to_numeric(df_filtre.get(col, 0), errors='coerce').fillna(0)

    # Hesaplanmış Metrikler
    df_filtre['bitiricilik_deltasi'] = (df_filtre[gol_kolonu] - df_filtre[xg_kolonu]).round(2)
    df_filtre['asist_deltasi'] = (df_filtre[asist_kolonu] - df_filtre[xa_kolonu]).round(2)
    
    oyuncu_kolonu = 'player' if 'player' in df.columns else 'player_name'
    takim_kolonu = 'team' if 'team' in df.columns else 'team_title'

    # SADECE SEÇİLEN HACİMDEKİLER (Şut veya Kilit Pas)
    df_filtre = df_filtre[(df_filtre[sut_kolonu] >= min_aksiyon) | (df_filtre[kp_kolonu] >= min_aksiyon)]

    # --- SEKME YARATMA (TABS) ---
    tab1, tab2 = st.tabs(["🎯 Keskin Nişancılar (Gol & xG)", "🧠 Oyun Kurucular (Asist & xA)"])

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
        st.markdown("*Asist Deltası yüksek olanlar, zor pasları gole çeviren kaliteli bitiricilere sahip olan veya ekstrem yaratıcılığa sahip oyunculardır.*")
        fig_asist = px.scatter(
            df_filtre.sort_values(by='asist_deltasi', ascending=False), 
            x=kp_kolonu, y='asist_deltasi', color=lig_sutunu, size=asist_kolonu,
            hover_name=oyuncu_kolonu, hover_data={takim_kolonu: True, asist_kolonu: True, xa_kolonu: True},
            labels={kp_kolonu: 'Kilit Pas (Key Passes)', 'asist_deltasi': 'Asist Deltası (Gerçekleşen Asist - xA)'},
            size_max=20, template='plotly_white'
        )
        st.plotly_chart(fig_asist, use_container_width=True)

    # Alt Kısım: Genel Tablo
    st.subheader(f"📋 Veri Tablosu ({len(df_filtre)} Oyuncu)")
    gosterilecek_tablo = df_filtre[[oyuncu_kolonu, takim_kolonu, lig_sutunu, sut_kolonu, gol_kolonu, xg_kolonu, 'bitiricilik_deltasi', kp_kolonu, asist_kolonu, xa_kolonu, 'asist_deltasi']]
    st.dataframe(gosterilecek_tablo, use_container_width=True)
