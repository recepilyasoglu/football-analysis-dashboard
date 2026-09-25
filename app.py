import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Sayfa Ayarları
st.set_page_config(page_title="Avrupa Scout Panosu", layout="wide")
st.title("⚽ Avrupa Scout Analiz Panosu (2026/27)")
st.markdown("Understat istatistikleri ve dinamik yaş hesaplamasıyla entegre scout panosu.")

# 2. Veri Yükleme ve Birleştirme (Join İşlemi)
@st.cache_data
def veri_yukle():
    # Ana Fact Tablosu (Understat İstatistikleri)
    try:
        df_stats = pd.read_csv('otomatik_understat_verileri.csv')
        df_stats.columns = [col.strip().lower() for col in df_stats.columns]
    except Exception:
        return pd.DataFrame()

    # Boyut Tablosu (Doğum Tarihleri)
    try:
        df_dates = pd.read_csv('oyuncu_dogum_tarihleri.csv')
        df_dates.columns = ['player', 'birth_date']
    except Exception:
        df_dates = pd.DataFrame(columns=['player', 'birth_date'])

    # İki veriyi oyuncu ismine göre birleştiriyoruz (Left Join)
    oyuncu_kolonu = 'player' if 'player' in df_stats.columns else 'player_name'
    if not df_dates.empty and oyuncu_kolonu in df_stats.columns:
        df_merged = pd.merge(df_stats, df_dates, left_on=oyuncu_kolonu, right_on='player', how='left')
        if 'player_y' in df_merged.columns:
            df_merged = df_merged.drop(columns=['player_y']).rename(columns={'player_x': 'player'})
    else:
        df_merged = df_stats.copy()
        df_merged['birth_date'] = None

    # Güvenli Dinamik Yaş Hesaplama
    # Tüm tarihleri datetime formatına çevir, bozuk olanları NaT (Not a Time) yap
    df_merged['birth_date'] = pd.to_datetime(df_merged['birth_date'], errors='coerce')
    bugun = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
    
    # Hata fırlatmaması için, dt.days ile gün farkını bulup 365.25'e bölüyoruz
    df_merged['age'] = (bugun - df_merged['birth_date']).dt.days / 365.25
    
    return df_merged

df = veri_yukle()

if df.empty:
    st.error("Veri dosyası bulunamadı! Lütfen 'otomatik_understat_verileri.csv' dosyasının var olduğundan emin ol.")
else:
    st.sidebar.header("⚙️ Analiz Filtreleri")
    lig_sutunu = 'league' if 'league' in df.columns else df.columns[0]
    secilen_ligler = st.sidebar.multiselect("Lig Seç:", options=df[lig_sutunu].unique(), default=df[lig_sutunu].unique())
    
    # Temel Kolonlar
    sut_kolonu = 'shots' if 'shots' in df.columns else 'sh'
    gol_kolonu = 'goals' if 'goals' in df.columns else 'gls'
    xg_kolonu = 'xg'
    asist_kolonu = 'assists'
    xa_kolonu = 'xa'
    kp_kolonu = 'key_passes'
    xgchain_kolonu = 'xgchain' if 'xgchain' in df.columns else 'xg_chain'
    xgbuildup_kolonu = 'xgbuildup' if 'xgbuildup' in df.columns else 'xg_buildup'
    oyuncu_kolonu = 'player' if 'player' in df.columns else 'player_name'
    takim_kolonu = 'team' if 'team' in df.columns else 'team_title'
    
    olasi_sure_isimleri = ['time', 'min', 'mins', 'minutes', 'oynama_suresi']
    sure_kolonu = next((col for col in olasi_sure_isimleri if col in df.columns), None)

    # Süre Filtresi
    if sure_kolonu:
        df[sure_kolonu] = pd.to_numeric(df[sure_kolonu], errors='coerce').fillna(0)
        min_sure = st.sidebar.slider("Minimum Oynama Süresi (Dakika):", 0, 2500, 300, 100)
        df_filtre = df[(df[lig_sutunu].isin(secilen_ligler)) & (df[sure_kolonu] >= min_sure)].copy()
    else:
        df_filtre = df[df[lig_sutunu].isin(secilen_ligler)].copy()

    # --- DİNAMİK YAŞ FİLTRESİ ---
    st.sidebar.subheader("🌟 U23 / Wonderkid Filtresi")
    u23_modu = st.sidebar.checkbox("Sadece 23 Yaş ve Altı Oyuncuları Göster")
    
    if u23_modu:
        # Sadece yaşı hesaplanabilen (null olmayan) ve 23'e eşit/küçük olanları tut
        df_filtre = df_filtre[(df_filtre['age'].notnull()) & (df_filtre['age'] <= 23.0)]
        st.sidebar.success("U23 filtresi aktif. Statik referans dosyasından eşleşen gençler listeleniyor.")

    # Sayısal dönüşümler
    sayisal_kolonlar = [gol_kolonu, xg_kolonu, sut_kolonu, asist_kolonu, xa_kolonu, kp_kolonu, xgchain_kolonu, xgbuildup_kolonu]
    for col in sayisal_kolonlar:
        if col in df_filtre.columns:
            df_filtre[col] = pd.to_numeric(df_filtre[col], errors='coerce').fillna(0)
        else:
            df_filtre[col] = 0

    df_filtre['bitiricilik_deltasi'] = (df_filtre[gol_kolonu] - df_filtre[xg_kolonu]).round(2)
    df_filtre['asist_deltasi'] = (df_filtre[asist_kolonu] - df_filtre[xa_kolonu]).round(2)

    # --- 3 SEKME (TABS) YAPISI ---
    tab1, tab2, tab3 = st.tabs(["🎯 Keskin Nişancılar", "🧠 10 Numaralar & Kanatlar", "🛡️ Gizli Kahramanlar (Stoper & 6 Numara)"])

    with tab1:
        st.subheader("Şut Hacmi vs Bitiricilik Deltası")
        fig_gol = px.scatter(
            df_filtre.sort_values(by='bitiricilik_deltasi', ascending=False), 
            x=sut_kolonu, y='bitiricilik_deltasi', color=lig_sutunu, size=gol_kolonu,
            hover_name=oyuncu_kolonu, hover_data={takim_kolonu: True, gol_kolonu: True, xg_kolonu: True, 'age': True},
            size_max=20, template='plotly_white'
        )
        st.plotly_chart(fig_gol, use_container_width=True)

    with tab2:
        st.subheader("Kilit Pas vs Asist Deltası")
        fig_asist = px.scatter(
            df_filtre.sort_values(by='asist_deltasi', ascending=False), 
            x=kp_kolonu, y='asist_deltasi', color=lig_sutunu, size=asist_kolonu,
            hover_name=oyuncu_kolonu, hover_data={takim_kolonu: True, asist_kolonu: True, xa_kolonu: True, 'age': True},
            size_max=20, template='plotly_white'
        )
        st.plotly_chart(fig_asist, use_container_width=True)

    with tab3:
        st.subheader("Geriden Oyun Kurma (xGBuildup)")
        fig_build = px.scatter(
            df_filtre.sort_values(by=xgbuildup_kolonu, ascending=False),
            x=xgbuildup_kolonu, y=xgchain_kolonu, color=lig_sutunu,
            hover_name=oyuncu_kolonu, hover_data={takim_kolonu: True, 'age': True},
            template='plotly_white'
        )
        st.plotly_chart(fig_build, use_container_width=True)

    # Alt Kısım: Genel Tablo
    st.subheader(f"📋 Scout Raporu Tablosu ({len(df_filtre)} Oyuncu)")
    gosterilecek_sutunlar = [oyuncu_kolonu, takim_kolonu, lig_sutunu]
    if sure_kolonu: gosterilecek_sutunlar.append(sure_kolonu)
    gosterilecek_sutunlar.append('age')
    gosterilecek_sutunlar.extend([xgbuildup_kolonu, xgchain_kolonu, gol_kolonu, xg_kolonu, kp_kolonu, xa_kolonu])
    
    gosterilecek_tablo = df_filtre[gosterilecek_sutunlar].copy()
    
    # Tabloda yaşı daha düzgün göstermek için yuvarlama (NaN olanlar kalabilir)
    gosterilecek_tablo['age'] = gosterilecek_tablo['age'].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "Bilinmiyor")
    
    st.dataframe(gosterilecek_tablo.sort_values(by=xgbuildup_kolonu, ascending=False), use_container_width=True)
