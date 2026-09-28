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
        df_istatistik = pd.read_csv('otomatik_understat_verileri.csv') 
        
        try:
            df_yas = pd.read_csv('oyuncu_dogum_tarihleri.csv', encoding='utf-8-sig')
        except UnicodeDecodeError:
            df_yas = pd.read_csv('oyuncu_dogum_tarihleri.csv', encoding='windows-1254')
        
        df_istatistik.columns = [col.strip().lower() for col in df_istatistik.columns]
        df_yas.columns = [col.strip().lower() for col in df_yas.columns]
        
        # --- KUSURSUZ EŞLEŞTİRME (İsimlerdeki boşluk ve harf hatalarını engellemek için) ---
        df_istatistik['merge_key'] = df_istatistik['player'].astype(str).str.lower().str.replace(' ', '')
        df_yas['merge_key'] = df_yas['player'].astype(str).str.lower().str.replace(' ', '')
        
        # Player kolonunu df_yas'tan düşüyoruz ki birleştirince player_x, player_y karmaşası olmasın
        df_merge = pd.merge(df_istatistik, df_yas.drop(columns=['player']), on='merge_key', how='left')
        
        # --- KALECİ VERİSİ ---
        try:
            for enc in ['utf-8-sig', 'windows-1254', 'latin1']:
                try:
                    df_kaleci = pd.read_csv('kaleci_verileri.csv', encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            
            df_kaleci.columns = [str(col).strip().lower().replace('%', '_percent') for col in df_kaleci.columns]
            
            if 'player' not in df_kaleci.columns:
                for col in df_kaleci.columns:
                    if 'player' in col or 'oyuncu' in col:
                        df_kaleci.rename(columns={col: 'player'}, inplace=True)
                        break
            
            if 'player' in df_kaleci.columns:
                beklenen_kaleci_kolonlari = ['player', 'ga', 'ga90', 'saves', 'save_percent', 'cs', 'age']
                mevcut_kaleci_kolonlari = [col for col in beklenen_kaleci_kolonlari if col in df_kaleci.columns]
                
                df_kaleci_secili = df_kaleci[mevcut_kaleci_kolonlari].copy()
                
                if 'age' in df_kaleci_secili.columns:
                    df_kaleci_secili['age_gk'] = df_kaleci_secili['age'].astype(str).str.split('-').str[0]
                    df_kaleci_secili['age_gk'] = pd.to_numeric(df_kaleci_secili['age_gk'], errors='coerce')
                    df_kaleci_secili.drop(columns=['age'], inplace=True)
                
                df_kaleci_secili['position_gk'] = 'GK' 
                df_kaleci_secili['merge_key'] = df_kaleci_secili['player'].astype(str).str.lower().str.replace(' ', '')
                
                df_merge = pd.merge(df_merge, df_kaleci_secili.drop(columns=['player']), on='merge_key', how='left')
                
                if 'position_gk' in df_merge.columns:
                    df_merge['position'] = df_merge['position'].fillna(df_merge['position_gk'])
                    df_merge.drop(columns=['position_gk'], inplace=True)

        except Exception as e:
            pass
        
        # Merge key işini bitirdi, silebiliriz
        df_merge.drop(columns=['merge_key'], inplace=True)
        
        # --- POZİSYON SADELEŞTİRME ---
        def sade_pozisyon_bul(poz_metni):
            if pd.isna(poz_metni):
                return 'Bilinmiyor'
            p = str(poz_metni).upper()
            if 'GK' in p:
                return 'GK'
            elif 'M R' in p or 'M L' in p or 'AMR' in p or 'AML' in p or 'W' in p:
                return 'W' 
            elif 'F' in p:
                return 'FW' 
            elif 'M' in p:
                return 'MF' 
            elif 'D' in p:
                return 'DF' 
            return 'Diğer'

        if 'position' in df_merge.columns:
             df_merge['sade_pozisyon'] = df_merge['position'].apply(sade_pozisyon_bul)
        
        # --- GENEL YAŞ HESAPLAMA ---
        df_merge['birth_date'] = pd.to_datetime(df_merge['birth_date'], errors='coerce', dayfirst=True)
        bugun = pd.to_datetime("today")
        df_merge['Age'] = (bugun - df_merge['birth_date']).dt.days // 365
        
        if 'age_gk' in df_merge.columns:
            df_merge['Age'] = df_merge['Age'].fillna(df_merge['age_gk'])
            
        df_merge['Age'] = df_merge['Age'].astype('Int64')
        
        sure_kolonlari = ['time', 'minutes', 'min', 'dakika', 'süre', 'mins']
        mevcut_sure = next((col for col in sure_kolonlari if col in df_merge.columns), None)
        
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
        st.error(f"Veri yüklenirken hata oluştu: {e}")
        return pd.DataFrame()

df = verileri_hazirla()

if not df.empty:
    st.sidebar.header("🔍 Filtreleme Seçenekleri")
    
    if 'league' in df.columns:
        secili_ligler = st.sidebar.multiselect("Lig Seçin", df['league'].unique(), default=df['league'].unique())
    else:
        secili_ligler = []
        
    if 'sade_pozisyon' in df.columns:
        mevcut_sade_mevkiler = df['sade_pozisyon'].dropna().unique()
        secili_mevki = st.sidebar.selectbox("Mevki Seçin", ['Tümü'] + list(mevcut_sade_mevkiler))
    else:
        secili_mevki = 'Tümü'
    
    u23_sart = st.sidebar.checkbox("Sadece U23 (23 Yaş ve Altı) Oyuncuları Göster", value=True)
    
    sure_kolonlari = ['time', 'minutes', 'min', 'dakika', 'süre', 'mins']
    mevcut_sure = next((col for col in sure_kolonlari if col in df.columns), None)
    
    min_dakika = 0
    if mevcut_sure:
        min_dakika = st.sidebar.slider("Minimum Oynama Süresi (Dakika)", 0, int(df[mevcut_sure].max()), 500)
    
    df_filtrelenmis = df.copy()
    if secili_ligler:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['league'].isin(secili_ligler)]
    
    if secili_mevki != 'Tümü' and 'sade_pozisyon' in df.columns:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['sade_pozisyon'] == secili_mevki]
    
    if u23_sart:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['Age'] <= 23]
        
    if azot := mevcut_sure:
        df_filtrelenmis = df_filtrelenmis[df_filtrelenmis[azot] >= min_dakika]

    takim_kolonu = 'team' if 'team' in df_filtrelenmis.columns else None

    # Hover (Bilgi Kutucuğu) sözlüklerini temiz gösterim için ayarlıyoruz.
    # False olanlar arka planda çalışır ama ekranda o çirkin yazıyla görünmez.
    temel_hover = {'Age': True, 'sade_pozisyon': True}
    if takim_kolonu:
        temel_hover[takim_kolonu] = True

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
    
    def sekme_uyarisi(beklenen_mevkiler, aktif_sekme_adi):
        if secili_mevki != 'Tümü' and secili_mevki not in beklenen_mevkiler:
             st.warning(f"Şu an **{aktif_sekme_adi}** sekmesindesiniz. Ancak soldan **{secili_mevki}** mevkisini seçtiniz. İlgili oyuncuları görmek için uygun sekmeye geçin veya mevki filtresini 'Tümü' yapın.")

    with tab1:
        st.subheader("Gol vs xG (90 Dakika Başına) - Sadece Hücumcular (FW)")
        sekme_uyarisi(['FW', 'W'], "Keskin Nişancılar")
        
        if 'sade_pozisyon' in df_filtrelenmis.columns:
             if secili_mevki == 'Tümü':
                 df_tab1 = df_filtrelenmis[df_filtrelenmis['sade_pozisyon'].isin(['FW', 'W'])]
             else:
                 df_tab1 = df_filtrelenmis
        else:
             df_tab1 = df_filtrelenmis

        if not df_tab1.empty and df_tab1['xG_90'].notna().any():
            hover_dict = temel_hover.copy()
            hover_dict['size_tab1'] = False # Ekranda o çirkin ondalıklı sayıyı gizle
            
            fig1 = px.scatter(df_tab1, x='xG_90', y='goals_90', hover_name='player',
                              hover_data=hover_dict, color=takim_kolonu,
                              size='size_tab1', size_max=max_baloncuk_boyutu, opacity=0.7,
                              labels={'xG_90': 'Beklenen Gol (xG) - 90dk', 'goals_90': 'Atılan Gol - 90dk'})
            st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        st.subheader("Asist vs xA (90 Dakika Başına) - Kanatlar ve 10 Numaralar (W, MF)")
        sekme_uyarisi(['W', 'MF', 'FW'], "10 Numaralar & Kanatlar")
        
        if 'sade_pozisyon' in df_filtrelenmis.columns:
            if secili_mevki == 'Tümü':
                 df_tab2 = df_filtrelenmis[df_filtrelenmis['sade_pozisyon'].isin(['W', 'MF', 'FW'])]
            else:
                 df_tab2 = df_filtrelenmis
        else:
            df_tab2 = df_filtrelenmis
            
        if not df_tab2.empty and df_tab2['xA_90'].notna().any():
            hover_dict = temel_hover.copy()
            hover_dict['size_tab2'] = False
            
            fig2 = px.scatter(df_tab2, x='xA_90', y='assists_90', hover_name='player',
                              hover_data=hover_dict, color=takim_kolonu,
                              size='size_tab2', size_max=max_baloncuk_boyutu, opacity=0.7,
                              labels={'xA_90': 'Beklenen Asist (xA) - 90dk', 'assists_90': 'Yapılan Asist - 90dk'})
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("xGChain vs xGBuildup (90 Dakika Başına) - Orta Saha ve Defans (MF, DF)")
        sekme_uyarisi(['MF', 'DF', 'W'], "Gizli Kahramanlar")
        
        if 'sade_pozisyon' in df_filtrelenmis.columns:
             if secili_mevki == 'Tümü':
                  df_tab3 = df_filtrelenmis[df_filtrelenmis['sade_pozisyon'].isin(['MF', 'DF', 'W'])]
             else:
                  df_tab3 = df_filtrelenmis
        else:
             df_tab3 = df_filtrelenmis

        if not df_tab3.empty and df_tab3['xGBuildup_90'].notna().any():
            hover_dict = temel_hover.copy()
            hover_dict['size_tab3'] = False
            
            fig3 = px.scatter(df_tab3, x='xGBuildup_90', y='xGChain_90', hover_name='player',
                              hover_data=hover_dict, color=takim_kolonu,
                              size='size_tab3', size_max=max_baloncuk_boyutu, opacity=0.7,
                              labels={'xGBuildup_90': 'Oyun Kurulumu (xGBuildup) - 90dk', 'xGChain_90': 'Hücum Katkısı (xGChain) - 90dk'})
            st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        st.subheader("Kurtarış Yüzdesi vs Yediği Gol (90dk) - Sadece Kaleciler (GK)")
        sekme_uyarisi(['GK'], "Eldivenler (Kaleciler)")
        
        if 'sade_pozisyon' in df_filtrelenmis.columns:
            if secili_mevki == 'Tümü':
                df_gk = df_filtrelenmis[df_filtrelenmis['sade_pozisyon'] == 'GK']
            else:
                 df_gk = df_filtrelenmis 
            
            if not df_gk.empty and 'save_percent' in df_gk.columns and df_gk['save_percent'].notna().any():
                df_gk['size_tab4'] = pd.to_numeric(df_gk['saves'], errors='coerce').fillna(0).clip(lower=0) + 0.1
                
                hover_dict = temel_hover.copy()
                hover_dict['cs'] = True
                hover_dict['size_tab4'] = False
                
                fig_gk = px.scatter(df_gk, x='save_percent', y='ga90', hover_name='player',
                                  hover_data=hover_dict, color=takim_kolonu,
                                  size='size_tab4', size_max=max_baloncuk_boyutu, opacity=0.7,
                                  labels={'save_percent': 'Kurtarış Yüzdesi (%)', 'ga90': 'Yediği Gol (GA) - 90dk', 'cs': 'Clean Sheet'})
                
                st.plotly_chart(fig_gk, use_container_width=True)
            elif secili_mevki == 'GK':
                st.info("Kaleci verileri bulunamadı veya oyuncu eşleşmedi.")
        else:
            st.warning("Verinizde pozisyon kolonu bulunamadı.")

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

    # --- AKILLI TABLO SIRALAMA ---
    st.markdown("---")
    st.subheader(f"📋 Seçili Filtrelere Göre Oyuncu Listesi ({len(df_filtrelenmis)} Oyuncu)")
    
    if secili_mevki == 'GK' and 'save_percent' in df_filtrelenmis.columns:
        df_filtrelenmis = df_filtrelenmis.sort_values(by='save_percent', ascending=False)
    elif secili_mevki == 'FW' and 'goals_90' in df_filtrelenmis.columns:
        df_filtrelenmis = df_filtrelenmis.sort_values(by=['goals_90', 'xG_90'], ascending=[False, False])
    elif secili_mevki == 'W' and 'assists_90' in df_filtrelenmis.columns:
        df_filtrelenmis = df_filtrelenmis.sort_values(by=['assists_90', 'xA_90'], ascending=[False, False])
    elif secili_mevki in ['MF', 'DF'] and 'xGBuildup_90' in df_filtrelenmis.columns:
        df_filtrelenmis = df_filtrelenmis.sort_values(by=['xGBuildup_90', 'xGChain_90'], ascending=[False, False])
    else:
        if mevcut_sure and mevcut_sure in df_filtrelenmis.columns:
            df_filtrelenmis = df_filtrelenmis.sort_values(by=mevcut_sure, ascending=False)
            
    gosterilecek_kolonlar = ['player', takim_kolonu, 'league', 'Age', 'sade_pozisyon', mevcut_sure, 'xG_90', 'xA_90', 'goals_90', 'assists_90', 'save_percent', 'ga90', 'cs']
    mevcut_kolonlar = [col for col in gosterilecek_kolonlar if col and col in df_filtrelenmis.columns]
    
    formatlanacak_kolonlar = [col for col in ['xG_90', 'xA_90', 'goals_90', 'assists_90', 'ga90'] if col in mevcut_kolonlar]
    st.dataframe(df_filtrelenmis[mevcut_kolonlar].style.format({col: '{:.2f}' for col in formatlanacak_kolonlar}))
