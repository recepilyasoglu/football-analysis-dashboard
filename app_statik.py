import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import unicodedata
import re
import os
import difflib
import numpy as np # BENZERLİK MOTORU İÇİN EKLENDİ

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Scout Pano", layout="wide")
st.title("⚽ Dinamik Oyuncu Scout Panosu")

# --- AGRESIF İSİM TEMİZLEYİCİ ---
def super_temizle(isim):
    if pd.isna(isim): return ""
    t = str(isim).lower()
    t = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
    t = t.replace('ı', 'i').replace('ö', 'o').replace('ü', 'u').replace('ş', 's').replace('ğ', 'g').replace('ç', 'c')
    t = re.sub(r'[^a-z]', '', t)
    return t

# --- 2. VERİ YÜKLEME VE İŞLEME ---
@st.cache_data
def verileri_hazirla():
    try:
        # 1. UNDERSTAT İSTATİSTİKLERİ
        df_istatistik = pd.read_csv('otomatik_understat_verileri.csv') 
        df_istatistik.columns = [col.strip().lower() for col in df_istatistik.columns]
        df_istatistik['merge_key'] = df_istatistik['player'].apply(super_temizle)
        
        if 'goals' in df_istatistik.columns:
            df_istatistik['goals'] = pd.to_numeric(df_istatistik['goals'], errors='coerce').fillna(0).astype(int)
        if 'assists' in df_istatistik.columns:
            df_istatistik['assists'] = pd.to_numeric(df_istatistik['assists'], errors='coerce').fillna(0).astype(int)
        
        # 2. AKILLI YAŞ OKUYUCU
        df_yas = pd.DataFrame()
        yas_dosyasi = None
        
        for file in os.listdir():
            if file.lower().endswith('oyuncu_dogum_tarihleri.csv'):
                yas_dosyasi = file
                break
                
        yas_sozlugu = {}
        if yas_dosyasi:
            for enc in ['utf-8', 'utf-8-sig', 'windows-1254', 'latin1']:
                try:
                    df_yas = pd.read_csv(yas_dosyasi, encoding=enc, sep=None, engine='python', on_bad_lines='skip')
                    if not df_yas.empty:
                        break
                except:
                    continue
            
            if not df_yas.empty:
                if isinstance(df_yas.columns, pd.MultiIndex):
                    df_yas.columns = ['_'.join(map(str, col)).strip() for col in df_yas.columns]
                    
                df_yas.columns = [str(col).strip().lower() for col in df_yas.columns]
                
                player_col = None
                for col in df_yas.columns:
                    if col in ['player', 'oyuncu', 'isim', 'name', 'player_name', 'futbolcu']:
                        player_col = col; break
                if not player_col:
                    for col in df_yas.columns:
                        if 'player' in col or 'oyuncu' in col or 'isim' in col or 'name' in col:
                            player_col = col; break
                            
                age_col = None
                for col in df_yas.columns:
                    if col in ['age', 'born', 'yas', 'yaş', 'birth_date', 'dogum_tarihi', 'dob']:
                        age_col = col; break
                if not age_col:
                    for col in df_yas.columns:
                        if 'age' in col or 'born' in col or 'yas' in col or 'yaş' in col:
                            age_col = col; break
                            
                if player_col and age_col:
                    df_yas['merge_key'] = df_yas[player_col].apply(super_temizle)
                    
                    bugun = pd.to_datetime("today")
                    if 'born' in age_col or 'doğum' in age_col:
                        df_yas['hesaplanan_yas'] = bugun.year - pd.to_numeric(df_yas[age_col], errors='coerce')
                    elif 'date' in age_col or 'tarih' in age_col or 'dob' in age_col:
                        df_yas[age_col] = pd.to_datetime(df_yas[age_col], errors='coerce')
                        df_yas['hesaplanan_yas'] = (bugun - df_yas[age_col]).dt.days // 365
                    else:
                        df_yas['hesaplanan_yas'] = df_yas[age_col].astype(str).str.split('-').str[0]
                        df_yas['hesaplanan_yas'] = pd.to_numeric(df_yas['hesaplanan_yas'], errors='coerce')
                        
                    yas_sozlugu = dict(zip(df_yas['merge_key'], df_yas['hesaplanan_yas']))

        vip_yaslar = {
            'kylianmbappelottin': 27, 'lautaromartinez': 29, 'donyellmalen': 27,
            'yassirzabiri': 21, 'sergiocamello': 25, 'gustavovarela': 21,
            'philliptietz': 29, 'lamineyamal': 19, 'erlinghaaland': 26,
            'raphinha': 29, 'mariano': 30, 'martinsatriano': 23, 
            'eduexposito': 28, 'lukasucic': 22, 'davidhancko': 26, 'orelmangala': 26,
            'ximonavarro': 36, 'djenedakonam': 34, 'papealassanegueye': 27,
            'giacomoquagliata': 26, 'loriskarius': 33, 'lorenzopalmisani': 22
        }
        
        yeni_yaslar = []
        yas_keys = list(yas_sozlugu.keys())
        
        for p in df_istatistik['merge_key']:
            if p in vip_yaslar:
                yeni_yaslar.append(vip_yaslar[p])
            elif p in yas_sozlugu and pd.notna(yas_sozlugu[p]):
                yeni_yaslar.append(yas_sozlugu[p])
            else:
                bulundu = False
                for y_p, y_age in yas_sozlugu.items():
                    if pd.notna(y_age) and len(y_p) > 3 and len(p) > 3:
                        if y_p in p or p in y_p:
                            yeni_yaslar.append(y_age)
                            bulundu = True
                            break
                            
                if not bulundu:
                    en_iyi_eslesme = difflib.get_close_matches(p, yas_keys, n=1, cutoff=0.80)
                    if en_iyi_eslesme and pd.notna(yas_sozlugu[en_iyi_eslesme[0]]):
                        yeni_yaslar.append(yas_sozlugu[en_iyi_eslesme[0]])
                    else:
                        yeni_yaslar.append(pd.NA)
                    
        df_istatistik['Age'] = yeni_yaslar
        
        # 3. KALECİ VERİSİ
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
                        
            df_kaleci['merge_key'] = df_kaleci['player'].apply(super_temizle)
            beklenen = ['merge_key', 'ga', 'ga90', 'saves', 'save_percent', 'cs', 'age']
            mevcut = [c for c in beklenen if c in df_kaleci.columns]
            df_k = df_kaleci[mevcut].copy()
            
            if 'age' in df_k.columns:
                df_k['age_gk'] = pd.to_numeric(df_k['age'].astype(str).str.split('-').str[0], errors='coerce')
                df_k.drop(columns=['age'], inplace=True)
                
            df_k['is_gk'] = True
            df_istatistik = pd.merge(df_istatistik, df_k, on='merge_key', how='left')
            
            if 'is_gk' in df_istatistik.columns:
                df_istatistik.loc[df_istatistik['is_gk'] == True, 'position'] = 'GK'
            
            if 'age_gk' in df_istatistik.columns:
                df_istatistik['Age'] = df_istatistik.apply(
                    lambda row: row['age_gk'] if pd.notna(row.get('age_gk')) else row['Age'], axis=1
                )
        except:
            pass
            
        df_istatistik.drop(columns=['merge_key', 'is_gk', 'age_gk'], inplace=True, errors='ignore')
        df_istatistik['Age'] = pd.to_numeric(df_istatistik['Age'], errors='coerce').astype('Int64')

        def sade_pozisyon_bul(poz_metni):
            if pd.isna(poz_metni): return 'Bilinmiyor'
            p = str(poz_metni).upper()
            if 'GK' in p: return 'GK'
            elif 'M R' in p or 'M L' in p or 'AMR' in p or 'AML' in p or 'W' in p: return 'W' 
            elif 'F' in p: return 'FW' 
            elif 'M' in p: return 'MF' 
            elif 'D' in p: return 'DF' 
            return 'Diğer'

        if 'position' in df_istatistik.columns:
             df_istatistik['sade_pozisyon'] = df_istatistik['position'].apply(sade_pozisyon_bul)
             
        sure_kolonlari = ['time', 'minutes', 'min', 'dakika', 'süre', 'mins']
        mevcut_sure = next((col for col in sure_kolonlari if col in df_istatistik.columns), None)
        
        metrikler_map = {
            'xg': 'xG_90', 'xa': 'xA_90', 'shots': 'shots_90', 
            'key_passes': 'key_passes_90', 'xgchain': 'xGChain_90', 
            'xgbuildup': 'xGBuildup_90', 'goals': 'goals_90', 'assists': 'assists_90'
        }
        
        for ham, p90 in metrikler_map.items():
            if ham in df_istatistik.columns:
                if mevcut_sure:
                    carpan = 90 / df_istatistik[mevcut_sure].replace(0, 1)
                    df_istatistik[p90] = round(df_istatistik[ham] * carpan, 2)
                else:
                    df_istatistik[p90] = df_istatistik[ham]
            else:
                df_istatistik[p90] = None

        if 'team_title' in df_istatistik.columns:
            df_istatistik.rename(columns={'team_title': 'team'}, inplace=True)

        return df_istatistik
    except Exception as e:
        st.error(f"Kritik Hata: {e}")
        return pd.DataFrame()

df = verileri_hazirla()

# --- TABLOLAR İÇİN DİNAMİK RENKLENDİRME (Koşullu Biçimlendirme) ---
def dinamik_renklendir(row):
    styles = [''] * len(row)
    # Bitiricilik Performansı (Attığı Gol vs Beklenen Gol)
    if 'goals_90' in row.index and 'xG_90' in row.index:
        try:
            fark_g = float(row['goals_90']) - float(row['xG_90'])
            idx_g = row.index.get_loc('goals_90')
            if fark_g > 0.15: # Beklenenden çok atıyorsa YEŞİL
                styles[idx_g] = 'background-color: rgba(39, 174, 96, 0.4)'
            elif fark_g < -0.15: # Pozisyonları harcıyorsa KIRMIZI
                styles[idx_g] = 'background-color: rgba(231, 76, 60, 0.4)'
        except: pass
        
    # Yaratıcılık Performansı (Yaptığı Asist vs Beklenen Asist)
    if 'assists_90' in row.index and 'xA_90' in row.index:
        try:
            fark_a = float(row['assists_90']) - float(row['xA_90'])
            idx_a = row.index.get_loc('assists_90')
            if fark_a > 0.10: # Beklenenden çok asist yapıyorsa YEŞİL
                styles[idx_a] = 'background-color: rgba(39, 174, 96, 0.4)'
            elif fark_a < -0.10: # Arkadaşları paslarını atamıyorsa veya kötü pas atıyorsa KIRMIZI
                styles[idx_a] = 'background-color: rgba(231, 76, 60, 0.4)'
        except: pass
    return styles

# --- SEKME İÇİ DİNAMİK TABLO ÇİZDİRİCİ ---
def sekme_tablosu_ciz(df_tab, kolonlar, sort_cols):
    if df_tab.empty:
        return
    mevcut_kolonlar = [c for c in kolonlar if c and c in df_tab.columns]
    df_gosterim = df_tab[mevcut_kolonlar].copy()
    mevcut_sort = [c for c in sort_cols if c in df_gosterim.columns]
    
    if mevcut_sort:
        df_gosterim = df_gosterim.sort_values(by=mevcut_sort, ascending=[False]*len(mevcut_sort))
        
    if 'Age' in df_gosterim.columns:
        df_gosterim['Age'] = df_gosterim['Age'].apply(lambda x: '-' if pd.isna(x) else int(x))
        
    format_dict = {col: '{:.2f}' for col in ['xG_90', 'xA_90', 'goals_90', 'assists_90', 'ga90', 'xGBuildup_90', 'xGChain_90', 'save_percent'] if col in df_gosterim.columns}
    
    st.markdown("---")
    st.markdown(f"**📋 İlgili Mevki Tablosu ({len(df_gosterim)} Oyuncu)** - *Beklenenden iyi performans gösterenler <span style='color:green'>YEŞİL</span>, kötü performans gösterenler <span style='color:red'>KIRMIZI</span> ile işaretlenmiştir.*", unsafe_allow_html=True)
    st.dataframe(df_gosterim.style.format(format_dict).apply(dinamik_renklendir, axis=1))

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
    
    u23_sart = st.sidebar.checkbox("Sadece U23 (23 Yaş ve Altı) Oyuncuları Göster", value=False)
    
    sure_kolonlari = ['time', 'minutes', 'min', 'dakika', 'süre', 'mins']
    mevcut_sure = next((col for col in sure_kolonlari if col in df.columns), None)
    
    min_dakika = 0
    if mevcut_sure:
        min_dakika = st.sidebar.slider("Minimum Oynama Süresi (Dakika)", 0, int(df[mevcut_sure].max()), 300)
    
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
    temel_hover = {'Age': True, 'sade_pozisyon': True}
    if takim_kolonu:
        temel_hover[takim_kolonu] = True

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Keskin Nişancılar (Gol & xG)", 
        "10 Numaralar & Kanatlar", 
        "Gizli Kahramanlar (xGBuildup)", 
        "🧤 Eldivenler (Kaleciler)", 
        "🎯 Profil Analizi & Benzerlik"
    ])

    df_filtrelenmis['xG_90'] = pd.to_numeric(df_filtrelenmis['xG_90'], errors='coerce').fillna(0)
    df_filtrelenmis['goals_90'] = pd.to_numeric(df_filtrelenmis['goals_90'], errors='coerce').fillna(0)
    df_filtrelenmis['xA_90'] = pd.to_numeric(df_filtrelenmis['xA_90'], errors='coerce').fillna(0)
    df_filtrelenmis['assists_90'] = pd.to_numeric(df_filtrelenmis['assists_90'], errors='coerce').fillna(0)
    df_filtrelenmis['xGBuildup_90'] = pd.to_numeric(df_filtrelenmis['xGBuildup_90'], errors='coerce').fillna(0)
    df_filtrelenmis['xGChain_90'] = pd.to_numeric(df_filtrelenmis['xGChain_90'], errors='coerce').fillna(0)

    df_filtrelenmis['size_tab1'] = df_filtrelenmis['xG_90'] + df_filtrelenmis['goals_90'] + 0.1
    df_filtrelenmis['size_tab2'] = df_filtrelenmis['xA_90'] + df_filtrelenmis['assists_90'] + 0.1
    df_filtrelenmis['size_tab3'] = df_filtrelenmis['xGBuildup_90'] + df_filtrelenmis['xGChain_90'] + 0.1
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

        if not df_tab1.empty:
            hover_dict = temel_hover.copy()
            hover_dict['size_tab1'] = False 
            if 'goals' in df_tab1.columns: hover_dict['goals'] = True
                
            fig1 = px.scatter(df_tab1, x='xG_90', y='goals_90', hover_name='player',
                              hover_data=hover_dict, color=takim_kolonu,
                              size='size_tab1', size_max=max_baloncuk_boyutu, opacity=0.7,
                              text='goals' if 'goals' in df_tab1.columns else None,
                              labels={'xG_90': 'Beklenen Gol (xG) - 90dk', 'goals_90': 'Atılan Gol - 90dk', 'goals': 'Toplam Gol'})
            
            fig1.update_traces(textposition='top center', textfont=dict(color='white', size=11))
            st.plotly_chart(fig1, use_container_width=True)
            
            kolonlar_tab1 = ['player', takim_kolonu, 'league', 'Age', 'sade_pozisyon', mevcut_sure, 'goals', 'goals_90', 'xG_90']
            siralama_tab1 = ['goals', 'goals_90', 'xG_90']
            sekme_tablosu_ciz(df_tab1, kolonlar_tab1, siralama_tab1)

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
            
        if not df_tab2.empty:
            hover_dict = temel_hover.copy()
            hover_dict['size_tab2'] = False
            if 'assists' in df_tab2.columns: hover_dict['assists'] = True
                
            fig2 = px.scatter(df_tab2, x='xA_90', y='assists_90', hover_name='player',
                              hover_data=hover_dict, color=takim_kolonu,
                              size='size_tab2', size_max=max_baloncuk_boyutu, opacity=0.7,
                              text='assists' if 'assists' in df_tab2.columns else None,
                              labels={'xA_90': 'Beklenen Asist (xA) - 90dk', 'assists_90': 'Yapılan Asist - 90dk', 'assists': 'Toplam Asist'})
                              
            fig2.update_traces(textposition='top center', textfont=dict(color='white', size=11))
            st.plotly_chart(fig2, use_container_width=True)
            
            kolonlar_tab2 = ['player', takim_kolonu, 'league', 'Age', 'sade_pozisyon', mevcut_sure, 'assists', 'assists_90', 'xA_90']
            siralama_tab2 = ['assists', 'assists_90', 'xA_90']
            sekme_tablosu_ciz(df_tab2, kolonlar_tab2, siralama_tab2)

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

        if not df_tab3.empty:
            hover_dict = temel_hover.copy()
            hover_dict['size_tab3'] = False
            fig3 = px.scatter(df_tab3, x='xGBuildup_90', y='xGChain_90', hover_name='player',
                              hover_data=hover_dict, color=takim_kolonu,
                              size='size_tab3', size_max=max_baloncuk_boyutu, opacity=0.7,
                              labels={'xGBuildup_90': 'Oyun Kurulumu (xGBuildup) - 90dk', 'xGChain_90': 'Hücum Katkısı (xGChain) - 90dk'})
            st.plotly_chart(fig3, use_container_width=True)
            
            kolonlar_tab3 = ['player', takim_kolonu, 'league', 'Age', 'sade_pozisyon', mevcut_sure, 'xGBuildup_90', 'xGChain_90']
            siralama_tab3 = ['xGBuildup_90', 'xGChain_90']
            sekme_tablosu_ciz(df_tab3, kolonlar_tab3, siralama_tab3)

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
                
                kolonlar_tab4 = ['player', takim_kolonu, 'league', 'Age', 'sade_pozisyon', mevcut_sure, 'saves', 'save_percent', 'ga90', 'cs']
                siralama_tab4 = ['save_percent', 'saves']
                sekme_tablosu_ciz(df_gk, kolonlar_tab4, siralama_tab4)
            elif secili_mevki == 'GK':
                st.info("Kaleci verileri bulunamadı veya oyuncu eşleşmedi.")
        else:
            st.warning("Verinizde pozisyon kolonu bulunamadı.")

    with tab5:
        st.subheader("Bireysel Profil Analizi ve Benzerlik Motoru")
        if not df_filtrelenmis.empty:
            secilen_oyuncu = st.selectbox("Detaylı analiz için listeden bir oyuncu seçin:", df_filtrelenmis['player'].unique())
            
            if secilen_oyuncu:
                oyuncu_verisi = df_filtrelenmis[df_filtrelenmis['player'] == secilen_oyuncu].iloc[0]
                kategoriler = ['xG (90dk)', 'xA (90dk)', 'Şut (90dk)', 'Kilit Pas (90dk)', 'xGChain (90dk)', 'xGBuildup (90dk)']
                degerler = [
                    oyuncu_verisi.get('xG_90') or 0, oyuncu_verisi.get('xA_90') or 0, 
                    oyuncu_verisi.get('shots_90') or 0, oyuncu_verisi.get('key_passes_90') or 0, 
                    oyuncu_verisi.get('xGChain_90') or 0, oyuncu_verisi.get('xGBuildup_90') or 0
                ]
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    fig4 = go.Figure()
                    fig4.add_trace(go.Scatterpolar(
                        r=degerler, theta=kategoriler, fill='toself', fillcolor='rgba(0, 204, 150, 0.4)',
                        line=dict(color='#00cc96', width=2), name=secilen_oyuncu
                    ))
                    fig4.update_layout(
                        polar=dict(radialaxis=dict(visible=True, showline=False)),
                        showlegend=False,
                        title=dict(text=f"<b>{secilen_oyuncu}</b> - Profil Radarı", x=0.5, font=dict(size=18))
                    )
                    st.plotly_chart(fig4, use_container_width=True)
                
                # --- YENİ EKLENTİ: YAPAY ZEKA OYUNCU BENZERLİK MOTORU ---
                with col2:
                    st.markdown(f"### 🤖 Benzerlik Motoru")
                    st.write(f"Oyun stili ve ana istatistikleri **{secilen_oyuncu}** ile en çok eşleşen oyuncular (Aynı mevkide):")
                    
                    benzerlik_metrikleri = ['xG_90', 'xA_90', 'shots_90', 'key_passes_90', 'xGChain_90', 'xGBuildup_90']
                    hedef_mevki = oyuncu_verisi.get('sade_pozisyon')
                    
                    df_havuz = df_filtrelenmis[df_filtrelenmis['sade_pozisyon'] == hedef_mevki].copy()
                    df_havuz = df_havuz.dropna(subset=benzerlik_metrikleri)
                    
                    if len(df_havuz) > 1:
                        # Vektörel Uzay Kurulumu (Min-Max Normalizasyonu)
                        X = df_havuz[benzerlik_metrikleri].values
                        X_min = X.min(axis=0)
                        X_max = X.max(axis=0)
                        X_norm = (X - X_min) / (X_max - X_min + 1e-9) # Sıfıra bölmeyi engelle
                        
                        # Hedef Oyuncu Vektörü
                        hedef_idx = df_havuz.index.get_loc(oyuncu_verisi.name)
                        hedef_vektor = X_norm[hedef_idx]
                        
                        # Öklid Mesafesi ile Benzerlik Hesabı
                        mesafeler = np.linalg.norm(X_norm - hedef_vektor, axis=1)
                        # Maksimum mesafe sqrt(6) civarıdır, bunu 100 üzerinden skora çeviriyoruz
                        df_havuz['Benzerlik_Skoru'] = 100 - (mesafeler / np.sqrt(len(benzerlik_metrikleri)) * 100)
                        
                        # Kendisini listeden çıkar ve en yüksek skorlu 3 kişiyi al
                        en_benzerler = df_havuz[df_havuz['player'] != secilen_oyuncu].nlargest(3, 'Benzerlik_Skoru')
                        
                        for idx, row in en_benzerler.iterrows():
                            st.success(f"⭐ **{row['player']}** ({row['team']})\n\nSkor: **%{row['Benzerlik_Skoru']:.1f}**")
                    else:
                        st.info("Benzerlik motorunu çalıştırmak için bu mevkide yeterli oyuncu verisi bulunamadı.")
