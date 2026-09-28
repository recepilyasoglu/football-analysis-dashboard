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
        # Ana istatistik verisi
        df_istatistik = pd.read_csv('otomatik_understat_verileri.csv') 
        
        # Yaş verisi
        try:
            df_yas = pd.read_csv('oyuncu_dogum_tarihleri.csv', encoding='utf-8-sig')
        except UnicodeDecodeError:
            df_yas = pd.read_csv('oyuncu_dogum_tarihleri.csv', encoding='windows-1254')
        
        df_istatistik.columns = [col.strip().lower() for col in df_istatistik.columns]
        df_yas.columns = [col.strip().lower() for col in df_yas.columns]
        
        # 1. Birleştirme: Ana veri + Yaşlar
        df_merge = pd.merge(df_istatistik, df_yas, on='player', how='left')
        
        # --- YENİ: DIŞARIDAN KALECİ VERİSİ (FBref) ENTEGRASYONU ---
        try:
            df_kaleci = pd.read_csv('kaleci_verileri.csv')
            
            # FBref'in çoklu başlık (multi-index) yapısını veya özel karakterlerini temizleme
            # % işaretini kodun sorunsuz okuyabilmesi için _percent yapıyoruz
            df_kaleci.columns = [str(col).strip().lower().replace('%', '_percent') for col in df_kaleci.columns]
            
            # Kaleci dosyasından sadece işimize yarayacak değerli kolonları alıyoruz
            beklenen_kaleci_kolonlari = ['player', 'ga', 'ga90', 'saves', 'save_percent', 'cs']
            mevcut_kaleci_kolonlari = [col for col in beklenen_kaleci_kolonlari if col in df_kaleci.columns]
            
            if 'player' in mevcut_kaleci_kolonlari:
                df_kaleci_secili = df_kaleci[mevcut_kaleci_kolonlari]
                # 2. Birleştirme: Mevcut veri + Kaleci Metrikleri
                df_merge = pd.merge(df_merge, df_kaleci_secili, on='player', how='left')
        except FileNotFoundError:
            pass # Kaleci verisi henüz yoksa sessizce geç
        except Exception as e:
            st.warning(f"Kaleci verisi okunurken ufak bir pürüz çıktı: {e}")
            pass
        
        # Yaş Hesaplama
        df_merge['birth_date'] = pd.to_datetime(df_merge['birth_date'], errors='coerce', dayfirst=True)
        bugun = pd.to_datetime("today")
        df_merge['Age'] = (bugun - df_merge['birth_date']).dt.days // 365
        
        sure_kolonlari = ['time', 'minutes', 'min', 'dakika', 'süre', 'mins']
        mevcut_sure = next((col for col in sure_kolonlari if col in df_merge.columns), None)
        
        # Normal oyuncuların Per 90 hesaplamaları
        metrikler_map = {
            'xg': 'xG_90', 'xa': 'xA_90', 'shots': 'shots_90', 
            'key_passes': 'key_passes_90', 'xgchain': 'xGChain_90', 
            'xgbuildup': 'xGBuildup_90', 'goals': 'goals_90', 'assists': 'assists_90'
        }
        
        for ham_kolon, per90_adi in metrikler_map.items():
            if ham_kolon in df_merge.columns:
                if mevcut_sure:
                    sure_carpan = 90 / df_merge[mevcut_sure].replace(0, 1)
                    df_merge[per90_adi] = round(df_merge[ham_kolon] * sure_carpan, 2)
                else:
                    df_merge[per90_adi] = df_merge[ham_kolon]
            else:
                df_merge[per90_adi] = None

        if 'team_title' in df_merge.columns:
            df_merge.rename(columns={'team_title': 'team'}, inplace=True)

        return df_merge
    except Exception as e:
        st.error(f"Ana Veri yüklenirken hata oluştu: {e}")
        return pd.DataFrame()

df = verileri_hazirla()

if not df.empty:
    # --- 3. YAN MENÜ VE FİLTRELER ---
    st.sidebar.header("🔍 Filtreleme Seçenekleri")
    
    if 'league' in df.columns:
        secili_ligler = st.sidebar.multiselect("Lig Seçin", df['league'].unique(), default=df['league'].unique())
    else:
        secili_ligler = []
        
    if 'position' in df.columns:
        secili_mevkiler = st.sidebar.multiselect("Mevki Seçin", df['position'].dropna().unique(), default=df['position'].dropna().unique())
    
    u23_sart = st.sidebar.checkbox("Sadece U23 (23 Yaş ve Altı) Oyuncuları Göster", value=True)
    
    sure_kolonlari = ['time', 'minutes', 'min', 'dakika', 'süre', 'mins']
    mevcut_sure = next((col for col in sure_kolonlari if col in df.columns), None)
    
    min_dakika = 0
    if mevcut_sure:
        min_dakika = st.sidebar.slider("Minimum Oynama Süresi (Dakika)", 0, int(df[mevcut_sure].max()), 500)
    
    df_filtrelenmis = df.copy()
    if secili_ligler:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['league'].isin(secili_ligler)]
    if 'position' in df.columns and secili_mevkiler:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['position'].isin(secili_mevkiler)]
    if u23_sart:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['Age'] <= 23]
    if mevcut_sure:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis[mevcut_sure] >= min_dakika]

    takim_kolonu = 'team' if 'team' in df_filtrelenmis.columns else None
    hover_liste = [takim_kolonu, 'Age', 'position'] if takim_kolonu else ['Age', 'position']

    # --- 4. SEKME YAPISI ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Keskin Nişancılar (Gol & xG)", 
        "10 Numaralar & Kanatlar", 
        "Gizli Kahramanlar (xGBuildup)", 
        "🧤 Eldivenler (Kaleciler)", 
        "🎯 Oyuncu Analiz Radarı"
    ])

    df_filtrelenmis['size_tab1'] = pd.to_numeric(df_filtrelenmis['xG_90'], errors='coerce').fillna(0).clip(lower=0) + pd.to_numeric(df_filtrelenmis['goals_90'], errors='coerce').fillna(0).clip(lower=0) + 0.1
    df_filtrelenmis['size_tab2'] = pd.to_numeric(df_filtrelenmis['xA_90'], errors='coerce').fillna(0).clip(lower=0) + pd.to_numeric(df_filtrelenmis['assists_90'], errors='coerce').fillna(0).clip(lower=0) + 0.1
    df_filtrelenmis['size_tab3'] = pd.to_numeric(df_filtrelenmis['xGBuildup_90'], errors='coerce').fillna(0).clip(lower=0) + pd.to_numeric(df_filtrelenmis['xGChain_90'], errors='coerce').fillna(0).clip(lower=0) + 0.1

    max_baloncuk_boyutu = 12

    with tab1:
        st.subheader("Gol vs xG (90 Dakika Başına) - Sadece Hücumcular")
        if 'position' in df_filtrelenmis.columns:
            df_tab1 = df_filtrelenmis[df_filtrelenmis['position'].str.contains('F', na=False)]
        else:
            df_tab1 = df_filtrelenmis
            
        if not df_tab1.empty and df_tab1['xG_90'].notna().any():
            fig1 = px.scatter(df_tab1, x='xG_90', y='goals_90', hover_name='player',
                              hover_data=hover_liste, color=takim_kolonu,
                              size='size_tab1', size_max=max_baloncuk_boyutu, opacity=0.7,
                              labels={'xG_90': 'Beklenen Gol (xG) - 90dk', 'goals_90': 'Atılan Gol - 90dk'})
            st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader("Asist vs xA (90 Dakika Başına) - 10 Numara ve Kanatlar")
        if 'position' in df_filtrelenmis.columns:
            df_tab2 = df_filtrelenmis[df_filtrelenmis['position'].str.contains('M|F', na=False) & ~df_filtrelenmis['position'].str.contains('D|GK', na=False)]
        else:
            df_tab2 = df_filtrelenmis
            
        if not df_tab2.empty and df_tab2['xA_90'].notna().any():
            fig2 = px.scatter(df_tab2, x='xA_90', y='assists_90', hover_name='player',
                              hover_data=hover_liste, color=takim_kolonu,
                              size='size_tab2', size_max=max_baloncuk_boyutu, opacity=0.7,
                              labels={'xA_90': 'Beklenen Asist (xA) - 90dk', 'assists_90': 'Yapılan Asist - 90dk'})
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("xGChain vs xGBuildup (90 Dakika Başına)")
        if not df_filtrelenmis.empty and df_filtrelenmis['xGBuildup_90'].notna().any():
            fig3 = px.scatter(df_filtrelenmis, x='xGBuildup_90', y='xGChain_90', hover_name='player',
                              hover_data=hover_liste, color=takim_kolonu,
                              size='size_tab3', size_max=max_baloncuk_boyutu, opacity=0.7,
                              labels={'xGBuildup_90': 'Oyun Kurulumu (xGBuildup) - 90dk', 'xGChain_90': 'Hücum Katkısı (xGChain) - 90dk'})
            st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        st.subheader("Kurtarış Yüzdesi vs Yediği Gol (90dk) - Kaleci Analizi")
        if 'position' in df_filtrelenmis.columns:
            # Hem 'GK' yazanları bul
            df_gk = df_filtrelenmis[df_filtrelenmis['position'].str.contains('GK', na=False)]
            
            # Gerekli kaleci verileri yüklenmiş mi kontrol et
            if not df_gk.empty and 'save_percent' in df_gk.columns and df_gk['save_percent'].notna().any():
                
                # Baloncuk boyutunu toplam kurtarış (saves) sayısına bağlıyoruz
                df_gk['size_tab4'] = pd.to_numeric(df_gk['saves'], errors='coerce').fillna(0).clip(lower=0) + 0.1
                
                fig_gk = px.scatter(df_gk, x='save_percent', y='ga90', hover_name='player',
                                  hover_data=hover_liste + ['cs'], color=takim_kolonu,
                                  size='size_tab4', size_max=max_baloncuk_boyutu, opacity=0.7,
                                  labels={'save_percent': 'Kurtarış Yüzdesi (%)', 'ga90': 'Yediği Gol (GA) - 90dk', 'cs': 'Clean Sheet'})
                
                # Grafik tasarımını güncelle: X ekseninde sağa doğru gitmek (yüksek kurtarış yüzdesi) iyi
                # Y ekseninde aşağıda olmak (düşük yediği gol) iyidir.
                fig_gk.update_layout(xaxis=dict(autorange="reversed")) # Kurtarış yüzdesi yüksek olanları vurgulamak istersen bu değiştirilebilir
                
                st.plotly_chart(fig_gk, use_container_width=True)
            else:
                st.info("Bu grafiği görmek için 'kaleci_verileri.csv' dosyasının dizinde olduğundan ve isimlerin (Player) Understat verisiyle eşleştiğinden emin olun.")
        else:
            st.warning("Verinizde 'position' kolonu bulunmadığı için kaleciler filtrelenemedi.")

    with tab5:
        st.subheader("Bireysel Profil Analizi")
        if not df_filtrelenmis.empty:
            secilen_oyuncu = st.selectbox("Detaylı radar analizi için listeden bir oyuncu seçin:", df_filtrelenmis['player'].unique())
            
            if secilen_oyuncu:
                oyuncu_verisi = df_filtrelenmis[df_filtrelenmis['player'] == secilen_oyuncu].iloc[0]
                
                kategoriler = ['xG (90dk)', 'xA (90dk)', 'Şut (90dk)', 'Kilit Pas (90dk)', 'xGChain (90dk)', 'xGBuildup (90dk)']
                degerler = [
                    oyuncu_verisi.get('xG_90') or 0, oyuncu_verisi.get('xA_90') or 0, 
                    oyuncu_verisi.get('shots_90') or 0, oyuncu_verisi.get('key_passes_90') or 0, 
                    oyuncu_verisi.get('xGChain_90') or 0, oyuncu_verisi.get('xGBuildup_90') or 0
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
    
    # Tüm ihtimalleri gözeterek kolonları sıralıyoruz
    gosterilecek_kolonlar = ['player', takim_kolonu, 'league', 'Age', 'position', mevcut_sure, 'xG_90', 'xA_90', 'goals_90', 'assists_90', 'save_percent', 'ga90', 'cs']
    mevcut_kolonlar = [col for col in gosterilecek_kolonlar if col and col in df_filtrelenmis.columns]
    
    formatlanacak_kolonlar = [col for col in ['xG_90', 'xA_90', 'goals_90', 'assists_90', 'ga90'] if col in mevcut_kolonlar]
    st.dataframe(df_filtrelenmis[mevcut_kolonlar].style.format({col: '{:.2f}' for col in formatlanacak_kolonlar}))
