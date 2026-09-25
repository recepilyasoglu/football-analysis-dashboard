import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Avrupa Scout Panosu", layout="wide")
st.title("⚽ Avrupa Scout Analiz Panosu (2026/27)")

@st.cache_data
def veri_yukle():
    # 1. Understat Verisini Yükle
    try:
        df_stats = pd.read_csv('otomatik_understat_verileri.csv')
        df_stats.columns = [col.strip().lower() for col in df_stats.columns]
    except Exception:
        return pd.DataFrame(), False, "Ana veri okunamadı"

    oyuncu_kolonu = 'player' if 'player' in df_stats.columns else 'player_name'

    # 2. Yaş Verisini Yükle (Hataları gizlemeden)
    yas_dosyasi_bulundu = False
    hata_mesaji = ""
    try:
        
        df_dates = pd.read_csv('oyuncu_dogum_tarihleri.csv', sep=None, engine='python', encoding='windows-1254')
        df_dates.columns = ['player', 'birth_date']
        yas_dosyasi_bulundu = True
    except Exception as e:
        hata_mesaji = str(e)
        df_dates = pd.DataFrame(columns=['player', 'birth_date'])

    # 3. Kusursuz Eşleştirme
    df_stats['merge_key'] = df_stats[oyuncu_kolonu].astype(str).str.lower().str.strip()
    df_dates['merge_key'] = df_dates['player'].astype(str).str.lower().str.strip()

    if not df_dates.empty:
        df_merged = pd.merge(df_stats, df_dates[['merge_key', 'birth_date']], on='merge_key', how='left')
    else:
        df_merged = df_stats.copy()
        df_merged['birth_date'] = None

    df_merged = df_merged.drop(columns=['merge_key'])

    # 4. Dinamik Yaş Hesaplama (dayfirst=True ile Gün/Ay/Yıl formatı düzeltildi)
    df_merged['birth_date'] = pd.to_datetime(df_merged['birth_date'], dayfirst=True, errors='coerce')
    bugun = pd.to_datetime(datetime.today().strftime('%Y-%m-%d'))
    df_merged['age'] = (bugun - df_merged['birth_date']).dt.days / 365.25
    
    return df_merged, yas_dosyasi_bulundu, hata_mesaji

df, yas_dosyasi_bulundu, hata_mesaji = veri_yukle()

if df.empty:
    st.error("Ana veri dosyası ('otomatik_understat_verileri.csv') bulunamadı!")
else:
    st.sidebar.header("⚙️ Analiz Filtreleri")
    if not yas_dosyasi_bulundu:
        # Artık "dosya yok" demek yerine gerçek hatayı ekrana basacak
        st.sidebar.error(f"⚠️ Dosya okunurken hata oluştu! Hata detayı: {hata_mesaji}")
    else:
        eslesen_kisi_sayisi = df['age'].notnull().sum()
        st.sidebar.success(f"✅ Yaş dosyası bağlandı! {eslesen_kisi_sayisi} oyuncunun yaşı hesaplandı.")

    lig_sutunu = 'league' if 'league' in df.columns else df.columns[0]
    secilen_ligler = st.sidebar.multiselect("Lig Seç:", options=df[lig_sutunu].unique(), default=df[lig_sutunu].unique())
    
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
    
    olasi_sure_isimleri = ['time', 'min', 'mins', 'minutes']
    sure_kolonu = next((col for col in olasi_sure_isimleri if col in df.columns), None)

    if sure_kolonu:
        df[sure_kolonu] = pd.to_numeric(df[sure_kolonu], errors='coerce').fillna(0)
        min_sure = st.sidebar.slider("Minimum Oynama Süresi:", 0, 2500, 0, 100)
        df_filtre = df[(df[lig_sutunu].isin(secilen_ligler)) & (df[sure_kolonu] >= min_sure)].copy()
    else:
        df_filtre = df[df[lig_sutunu].isin(secilen_ligler)].copy()

    st.sidebar.subheader("🌟 U23 / Wonderkid Filtresi")
    u23_modu = st.sidebar.checkbox("Sadece 23 Yaş ve Altı Oyuncuları Göster")
    
    if u23_modu:
        df_filtre = df_filtre[(df_filtre['age'].notnull()) & (df_filtre['age'] <= 23.0)]

    sayisal_kolonlar = [gol_kolonu, xg_kolonu, sut_kolonu, asist_kolonu, xa_kolonu, kp_kolonu, xgchain_kolonu, xgbuildup_kolonu]
    for col in sayisal_kolonlar:
        df_filtre[col] = pd.to_numeric(df_filtre[col], errors='coerce').fillna(0)

    df_filtre['bitiricilik_deltasi'] = (df_filtre[gol_kolonu] - df_filtre[xg_kolonu]).round(2)
    df_filtre['asist_deltasi'] = (df_filtre[asist_kolonu] - df_filtre[xa_kolonu]).round(2)

    tab1, tab2, tab3 = st.tabs(["🎯 Keskin Nişancılar", "🧠 10 Numaralar & Kanatlar", "🛡️ Gizli Kahramanlar"])

    with tab1:
        fig_gol = px.scatter(
            df_filtre.sort_values(by='bitiricilik_deltasi', ascending=False), 
            x=sut_kolonu, y='bitiricilik_deltasi', color=lig_sutunu, size=gol_kolonu,
            hover_name=oyuncu_kolonu, hover_data={takim_kolonu: True, 'age': True},
            template='plotly_white'
        )
        st.plotly_chart(fig_gol, use_container_width=True)

    with tab2:
        fig_asist = px.scatter(
            df_filtre.sort_values(by='asist_deltasi', ascending=False), 
            x=kp_kolonu, y='asist_deltasi', color=lig_sutunu, size=asist_kolonu,
            hover_name=oyuncu_kolonu, hover_data={takim_kolonu: True, 'age': True},
            template='plotly_white'
        )
        st.plotly_chart(fig_asist, use_container_width=True)

    with tab3:
        fig_build = px.scatter(
            df_filtre.sort_values(by=xgbuildup_kolonu, ascending=False),
            x=xgbuildup_kolonu, y=xgchain_kolonu, color=lig_sutunu,
            hover_name=oyuncu_kolonu, hover_data={takim_kolonu: True, 'age': True},
            template='plotly_white'
        )
        st.plotly_chart(fig_build, use_container_width=True)

    st.subheader(f"📋 Scout Raporu Tablosu ({len(df_filtre)} Oyuncu)")
    gosterilecek_sutunlar = [oyuncu_kolonu, takim_kolonu, lig_sutunu]
    if sure_kolonu: gosterilecek_sutunlar.append(sure_kolonu)
    gosterilecek_sutunlar.append('age')
    gosterilecek_sutunlar.extend([xgbuildup_kolonu, xgchain_kolonu])
    
    gosterilecek_tablo = df_filtre[gosterilecek_sutunlar].copy()
    gosterilecek_tablo['age'] = gosterilecek_tablo['age'].apply(lambda x: f"{x:.1f}" if pd.notnull(x) else "Bilinmiyor")
    
    st.dataframe(gosterilecek_tablo.sort_values(by=xgbuildup_kolonu, ascending=False), use_container_width=True)
