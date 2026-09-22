import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Sayfa Ayarları
st.set_page_config(page_title="Avrupa Keskin Nişancıları", layout="wide")
st.title("⚽ Avrupa'nın En Keskin Forvetleri (Otomatik Veri Hattı)")
st.markdown("Understat verileriyle beslenen, Avrupa'nın 5 büyük ligindeki forvetlerin bitiricilik ve xG analizi.")

# 2. Otomatik İndirilen Veriyi Yükleme
@st.cache_data
def veri_yukle():
    try:
        # Otomatik çektiğimiz birleşik dosyayı okuyoruz
        df = pd.read_csv('otomatik_understat_verileri.csv')
        return df
    except Exception as e:
        st.error(f"Veri dosyası okunamadı: {e}")
        return pd.DataFrame()

df = veri_yukle()

if df.empty:
    st.error("`otomatik_avrupa_sut_verileri.csv` dosyası bulunamadı! Lütfen önce veri çekme scriptini çalıştır.")
else:
    # Understat sütun isimleri soccerdata formatına göre düzenlenir (örn: league, player, team, goals, shots, xG)
    # Sütun isimlerindeki olası boşluk veya büyük/küçük harf farklarını standartlaştıralım
    df.columns = [col.strip().lower() for col in df.columns]

    # 3. Sol Menü (Sidebar) - İnteraktif Filtreler
    st.sidebar.header("⚙️ Analiz Filtreleri")
    
    # Lig sütununun adını kontrol edelim (genelde 'league' veya 'comp')
    lig_sutunu = 'league' if 'league' in df.columns else df.columns[0]
    
    secilen_ligler = st.sidebar.multiselect("Lig Seç:", options=df[lig_sutunu].unique(), default=df[lig_sutunu].unique())
    
    # Süre veya şut filtreleri (Understat'ta süre 'time' veya 'min', şut 'shots' olarak geçer)
    sut_kolonu = 'shots' if 'shots' in df.columns else 'sh'
    gol_kolonu = 'goals' if 'goals' in df.columns else 'gls'
    xg_kolonu = 'xg' if 'xg' in df.columns else 'x ممکن'
    
    min_sut = st.sidebar.slider("Minimum Şut Sayısı:", 1, 50, 10, 1)

    # 4. Veriyi Filtreleme ve Bitiricilik Deltası Hesaplama
    # Understat verisinde doğrudan xG ve Gol (goals) yer alır.
    # Saf Bitiricilik Deltası = Gerçekleşen Gol - Beklenen Gol (Goals - xG)
    df_filtre = df[(df[lig_sutunu].isin(secilen_ligler)) & (df[sut_kolonu] >= min_sut)].copy()
                   
    # Sayısal dönüşümler
    df_filtre[gol_kolonu] = pd.to_numeric(df_filtre[gol_kolonu], errors='coerce').fillna(0)
    df_filtre[xg_kolonu] = pd.to_numeric(df_filtre[xg_kolonu], errors='coerce').fillna(0)
    df_filtre[sut_kolonu] = pd.to_numeric(df_filtre[sut_kolonu], errors='coerce').fillna(0)

    # Bitiricilik Deltası (Gol - xG) ve Şut Başına xG hesaplama
    df_filtre['bitiricilik_deltasi'] = (df_filtre[gol_kolonu] - df_filtre[xg_kolonu]).round(2)
    
    # Oyuncu adı ve takım sütunları
    oyuncu_kolonu = 'player' if 'player' in df.columns else 'player_name'
    takim_kolonu = 'team' if 'team' in df.columns else 'team_title'

    sonuc_df = df_filtre[[oyuncu_kolonu, takim_kolonu, lig_sutunu, sut_kolonu, gol_kolonu, xg_kolonu, 'bitiricilik_deltasi']]
    sonuc_df = sonuc_df.sort_values(by='bitiricilik_deltasi', ascending=False)

    # 5. İnteraktif Grafik (Plotly)
    st.subheader("📊 Şut Hacmi vs Bitiricilik Deltası (Gol - xG)")
    
    fig = px.scatter(
        sonuc_df, 
        x=sut_kolonu, 
        y='bitiricilik_deltasi', 
        color=lig_sutunu, 
        size=gol_kolonu,
        hover_name=oyuncu_kolonu,
        hover_data={takim_kolonu: True, gol_kolonu: True, xg_kolonu: True},
        labels={sut_kolonu: 'Toplam Şut Sayısı', 'bitiricilik_deltasi': 'Bitiricilik Deltası (Gol - xG)'},
        size_max=25, 
        template='plotly_white'
    )
    st.plotly_chart(fig, use_container_width=True)

    # 6. Tablo Görünümü
    st.subheader(f"🏆 Seçilen Kriterlere Uyan Toplam Oyuncu: {len(sonuc_df)}")
    st.dataframe(sonuc_df, use_container_width=True)