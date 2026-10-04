import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import unicodedata
import re
import os
import difflib
import numpy as np
import json
import requests # Standart kütüphane yeterli!

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
    
# --- 2. CANLI API VERİ YÜKLEME ---
@st.cache_data(ttl=43200) # Veriyi 12 saatte bir otomatik canlı çeker
def verileri_hazirla():
    try:
        ligler = {'EPL': 'ENG-Premier League', 'La_liga': 'ESP-La Liga', 'Bundesliga': 'GER-Bundesliga', 'Serie_A': 'ITA-Serie A', 'Ligue_1': 'FRA-Ligue 1'}
        sezon = '2026' # Canlı 2026 verisi
        tum_oyuncular = []

        SCRAPER_API_KEY = "66e0963124cda017fecac0bbba2da732" 

        for lig_kodu, lig_adi in ligler.items():
            hedef_url = f"https://understat.com/league/{lig_kodu}/{sezon}"
            payload = {'api_key': SCRAPER_API_KEY, 'url': hedef_url}
            
            try:
                response = requests.get('http://api.scraperapi.com', params=payload, timeout=45)
                
                if response.status_code == 200:
                    html = response.text
                    
                    # 🔥 1. AŞAMA: Zırhlı Buldozer (Boşluk, tab veya isim değişimlerine karşı korumalı)
                    match = re.search(r"playersData\s*=\s*JSON\.parse\(\s*['\"](.*?)['\"]\s*\)", html)
                    raw_data = None
                    
                    if match:
                        raw_data = match.group(1)
                    else:
                        # 🔥 2. AŞAMA (B planı): Eğer playersData ismini bile silmişlerse, sayfadaki 
                        # tüm JSON bloklarını bul ve 2.sini (Oyuncu listesini) zorla al!
                        json_blocks = re.findall(r"JSON\.parse\(\s*['\"](.*?)['\"]\s*\)", html)
                        if len(json_blocks) >= 2:
                            raw_data = json_blocks[1] 

                    if raw_data:
                        try:
                            decoded_data = bytes(raw_data, 'utf-8').decode('unicode_escape')
                            oyuncu_verisi = json.loads(decoded_data)

                            for oyuncu in oyuncu_verisi:
                                oyuncu['league'] = lig_adi
                                oyuncu['player'] = oyuncu.pop('player_name', None)
                            tum_oyuncular.extend(oyuncu_verisi)
                        except Exception as e:
                            st.warning(f"⚠️ {lig_adi} verisi çözülemedi: {e}")
                    else:
                        st.warning(f"⚠️ {lig_adi} için HTML geldi ama JSON tablosu bulunamadı!")
                else:
                    st.warning(f"❌ ScraperAPI Hata {response.status_code} ({lig_adi})")
                    
            except Exception as e:
                st.warning(f"🔌 {lig_adi} bağlantı zaman aşımı: {e}")

        if not tum_oyuncular:
            st.error("🚨 Hiçbir veri çekilemedi. Lütfen sayfayı yenileyin (Clear Cache yapmayı unutmayın).")
            return pd.DataFrame()

        # --- Veri İşleme Adımları ---
        df_istatistik = pd.DataFrame(tum_oyuncular)
        df_istatistik = df_istatistik.rename(columns={'team_title': 'team', 'time': 'minutes'})
        
        sayisal_kolonlar = ['goals', 'assists', 'shots', 'key_passes', 'xG', 'xA', 'xGChain', 'xGBuildup', 'minutes']
        for col in sayisal_kolonlar:
            if col in df_istatistik.columns:
                df_istatistik[col] = pd.to_numeric(df_istatistik[col], errors='coerce').fillna(0)
                
        df_istatistik.columns = [col.strip().lower() for col in df_istatistik.columns]
        df_istatistik['merge_key'] = df_istatistik['player'].apply(super_temizle)
        
        if 'goals' in df_istatistik.columns:
            df_istatistik['goals'] = pd.to_numeric(df_istatistik['goals'], errors='coerce').fillna(0).astype(int)
        if 'assists' in df_istatistik.columns:
            df_istatistik['assists'] = pd.to_numeric(df_istatistik['assists'], errors='coerce').fillna(0).astype(int)
        
        # --- Yaş ve Kaleci İşlemleri ---
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
                    if not df_yas.empty: break
                except: continue
            
            if not df_yas.empty:
                df_yas.columns = [str(col).strip().lower() for col in df_yas.columns]
                player_col = next((col for col in df_yas.columns if col in ['player', 'oyuncu', 'isim', 'name']), None)
                age_col = next((col for col in df_yas.columns if col in ['age', 'born', 'yas', 'yaş']), None)
                            
                if player_col and age_col:
                    df_yas['merge_key'] = df_yas[player_col].apply(super_temizle)
                    df_yas['hesaplanan_yas'] = pd.to_datetime('today').year - pd.to_numeric(df_yas[age_col], errors='coerce')
                    yas_sozlugu = dict(zip(df_yas['merge_key'], df_yas['hesaplanan_yas']))

        vip_yaslar = {
            'kylianmbappelottin': 27, 'lautaromartinez': 29, 'donyellmalen': 27, 'erlinghaaland': 26,
            'lamineyamal': 19, 'raphinha': 29, 'giacomoquagliata': 26, 'loriskarius': 33, 'lorenzopalmisani': 22
        }
        yeni_yaslar = []
        yas_keys = list(yas_sozlugu.keys())
        
        for p in df_istatistik['merge_key']:
            if p in vip_yaslar: yeni_yaslar.append(vip_yaslar[p])
            elif p in yas_sozlugu and pd.notna(yas_sozlugu[p]): yeni_yaslar.append(yas_sozlugu[p])
            else:
                eslesme = difflib.get_close_matches(p, yas_keys, n=1, cutoff=0.80)
                if eslesme and pd.notna(yas_sozlugu[eslesme[0]]): yeni_yaslar.append(yas_sozlugu[eslesme[0]])
                else: yeni_yaslar.append(pd.NA)
        df_istatistik['Age'] = yeni_yaslar
        
        try:
            df_kaleci = pd.read_csv('kaleci_verileri.csv')
            df_kaleci.columns = [str(col).strip().lower().replace('%', '_percent') for col in df_kaleci.columns]
            player_col_gk = next((col for col in df_kaleci.columns if 'player' in col or 'oyuncu' in col), None)
            if player_col_gk: df_kaleci.rename(columns={player_col_gk: 'player'}, inplace=True)
                        
            df_kaleci['merge_key'] = df_kaleci['player'].apply(super_temizle)
            mevcut_k = [c for c in ['merge_key', 'ga', 'ga90', 'saves', 'save_percent', 'cs', 'age'] if c in df_kaleci.columns]
            df_k = df_kaleci[mevcut_k].copy()
            df_k['is_gk'] = True
            if 'age' in df_k.columns:
                df_k['age_gk'] = pd.to_numeric(df_k['age'], errors='coerce')
                df_k.drop(columns=['age'], inplace=True)
                
            df_istatistik = pd.merge(df_istatistik, df_k, on='merge_key', how='left')
            if 'is_gk' in df_istatistik.columns: df_istatistik.loc[df_istatistik['is_gk'] == True, 'position'] = 'GK'
            if 'age_gk' in df_istatistik.columns: df_istatistik['Age'] = df_istatistik.apply(lambda row: row['age_gk'] if pd.notna(row.get('age_gk')) else row['Age'], axis=1)
        except: pass
            
        df_istatistik.drop(columns=['merge_key', 'is_gk', 'age_gk'], inplace=True, errors='ignore')
        df_istatistik['Age'] = pd.to_numeric(df_istatistik['Age'], errors='coerce').astype('Int64')

        def sade_pozisyon_bul(poz_metni):
            if pd.isna(poz_metni): return 'Bilinmiyor'
            p = str(poz_metni).upper()
            if 'GK' in p: return 'GK'
            elif any(x in p for x in ['M R', 'M L', 'AMR', 'AML', 'W']): return 'W' 
            elif 'F' in p: return 'FW' 
            elif 'M' in p: return 'MF' 
            elif 'D' in p: return 'DF' 
            return 'Diğer'

        if 'position' in df_istatistik.columns: df_istatistik['sade_pozisyon'] = df_istatistik['position'].apply(sade_pozisyon_bul)
             
        mevcut_sure = next((col for col in ['time', 'minutes', 'min', 'dakika', 'süre', 'mins'] if col in df_istatistik.columns), None)
        metrikler_map = {'xg': 'xG_90', 'xa': 'xA_90', 'shots': 'shots_90', 'key_passes': 'key_passes_90', 'xgchain': 'xGChain_90', 'xgbuildup': 'xGBuildup_90', 'goals': 'goals_90', 'assists': 'assists_90'}
        
        for ham, p90 in metrikler_map.items():
            if ham in df_istatistik.columns:
                if mevcut_sure: df_istatistik[p90] = round(df_istatistik[ham] * (90 / df_istatistik[mevcut_sure].replace(0, 1)), 2)
                else: df_istatistik[p90] = df_istatistik[ham]
            else: df_istatistik[p90] = None

        return df_istatistik
    except Exception as e:
        st.error(f"Kritik Hata: {e}")
        return pd.DataFrame()

df = verileri_hazirla()

# --- TABLOLAR İÇİN DİNAMİK RENKLENDİRME ---
def dinamik_renklendir(row):
    styles = [''] * len(row)
    if 'goals_90' in row.index and 'xG_90' in row.index:
        try:
            fark_g = float(row['goals_90']) - float(row['xG_90'])
            idx_g = row.index.get_loc('goals_90')
            if fark_g > 0.15: styles[idx_g] = 'background-color: rgba(39, 174, 96, 0.4)'
            elif fark_g < -0.15: styles[idx_g] = 'background-color: rgba(231, 76, 60, 0.4)'
        except: pass
    if 'assists_90' in row.index and 'xA_90' in row.index:
        try:
            fark_a = float(row['assists_90']) - float(row['xA_90'])
            idx_a = row.index.get_loc('assists_90')
            if fark_a > 0.10: styles[idx_a] = 'background-color: rgba(39, 174, 96, 0.4)'
            elif fark_a < -0.10: styles[idx_a] = 'background-color: rgba(231, 76, 60, 0.4)'
        except: pass
    return styles

def sekme_tablosu_ciz(df_tab, kolonlar, sort_cols):
    if df_tab.empty: return
    mevcut_kolonlar = [c for c in kolonlar if c and c in df_tab.columns]
    df_gosterim = df_tab[mevcut_kolonlar].copy()
    mevcut_sort = [c for c in sort_cols if c in df_gosterim.columns]
    if mevcut_sort: df_gosterim = df_gosterim.sort_values(by=mevcut_sort, ascending=[False]*len(mevcut_sort))
    if 'Age' in df_gosterim.columns: df_gosterim['Age'] = df_gosterim['Age'].apply(lambda x: '-' if pd.isna(x) else int(x))
    format_dict = {col: '{:.2f}' for col in ['xG_90', 'xA_90', 'goals_90', 'assists_90', 'ga90', 'xGBuildup_90', 'xGChain_90', 'save_percent'] if col in df_gosterim.columns}
    st.markdown("---")
    st.dataframe(df_gosterim.style.format(format_dict).apply(dinamik_renklendir, axis=1))

if not df.empty:
    st.sidebar.header("🔍 Filtreleme Seçenekleri")
    secili_ligler = st.sidebar.multiselect("Lig Seçin", df['league'].unique(), default=df['league'].unique()) if 'league' in df.columns else []
    mevcut_sade_mevkiler = df['sade_pozisyon'].dropna().unique() if 'sade_pozisyon' in df.columns else []
    secili_mevki = st.sidebar.selectbox("Mevki Seçin", ['Tümü'] + list(mevcut_sade_mevkiler))
    u23_sart = st.sidebar.checkbox("Sadece U23 Oyuncuları Göster", value=False)
    
    mevcut_sure = next((col for col in ['time', 'minutes', 'min', 'dakika', 'süre', 'mins'] if col in df.columns), None)
    min_dakika = st.sidebar.slider("Minimum Oynama Süresi", 0, int(df[mevcut_sure].max()), 300) if mevcut_sure else 0
    
    df_filtrelenmis = df.copy()
    if secili_ligler: df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['league'].isin(secili_ligler)]
    if secili_mevki != 'Tümü': df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['sade_pozisyon'] == secili_mevki]
    if u23_sart: df_filtrelenmis = df_filtrelenmis[df_filtrelenmis['Age'] <= 23]
    if mevcut_sure: df_filtrelenmis = df_filtrelenmis[df_filtrelenmis[mevcut_sure] >= min_dakika]

    takim_kolonu = 'team' if 'team' in df_filtrelenmis.columns else None
    temel_hover = {'Age': True, 'sade_pozisyon': True}
    if takim_kolonu: temel_hover[takim_kolonu] = True

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Keskin Nişancılar", "10 Numaralar & Kanatlar", "Gizli Kahramanlar", "Eldivenler (Kaleciler)", "Profil & Benzerlik"])

    df_filtrelenmis[['xG_90', 'goals_90', 'xA_90', 'assists_90', 'xGBuildup_90', 'xGChain_90']] = df_filtrelenmis[['xG_90', 'goals_90', 'xA_90', 'assists_90', 'xGBuildup_90', 'xGChain_90']].fillna(0)
    df_filtrelenmis['size_tab1'] = df_filtrelenmis['xG_90'] + df_filtrelenmis['goals_90'] + 0.1
    df_filtrelenmis['size_tab2'] = df_filtrelenmis['xA_90'] + df_filtrelenmis['assists_90'] + 0.1
    df_filtrelenmis['size_tab3'] = df_filtrelenmis['xGBuildup_90'] + df_filtrelenmis['xGChain_90'] + 0.1
    max_b = 12

    with tab1:
        st.subheader("Gol vs xG (90dk)")
        df_tab1 = df_filtrelenmis[df_filtrelenmis['sade_pozisyon'].isin(['FW', 'W'])] if secili_mevki == 'Tümü' else df_filtrelenmis
        if not df_tab1.empty:
            hover = temel_hover.copy()
            hover['size_tab1'] = False
            if 'goals' in df_tab1.columns: hover['goals'] = True
            fig1 = px.scatter(df_tab1, x='xG_90', y='goals_90', hover_name='player', hover_data=hover, color=takim_kolonu, size='size_tab1', size_max=max_b, text='goals' if 'goals' in df_tab1.columns else None)
            fig1.update_traces(textposition='top center')
            st.plotly_chart(fig1, use_container_width=True)
            sekme_tablosu_ciz(df_tab1, ['player', takim_kolonu, 'league', 'Age', 'sade_pozisyon', mevcut_sure, 'goals', 'goals_90', 'xG_90'], ['goals', 'goals_90', 'xG_90'])

    with tab2:
        st.subheader("Asist vs xA (90dk)")
        df_tab2 = df_filtrelenmis[df_filtrelenmis['sade_pozisyon'].isin(['W', 'MF', 'FW'])] if secili_mevki == 'Tümü' else df_filtrelenmis
        if not df_tab2.empty:
            hover = temel_hover.copy()
            hover['size_tab2'] = False
            if 'assists' in df_tab2.columns: hover['assists'] = True
            fig2 = px.scatter(df_tab2, x='xA_90', y='assists_90', hover_name='player', hover_data=hover, color=takim_kolonu, size='size_tab2', size_max=max_b, text='assists' if 'assists' in df_tab2.columns else None)
            fig2.update_traces(textposition='top center')
            st.plotly_chart(fig2, use_container_width=True)
            sekme_tablosu_ciz(df_tab2, ['player', takim_kolonu, 'league', 'Age', 'sade_pozisyon', mevcut_sure, 'assists', 'assists_90', 'xA_90'], ['assists', 'assists_90', 'xA_90'])

    with tab3:
        st.subheader("xGChain vs xGBuildup (90dk)")
        df_tab3 = df_filtrelenmis[df_filtrelenmis['sade_pozisyon'].isin(['MF', 'DF', 'W'])] if secili_mevki == 'Tümü' else df_filtrelenmis
        if not df_tab3.empty:
            hover = temel_hover.copy()
            hover['size_tab3'] = False
            fig3 = px.scatter(df_tab3, x='xGBuildup_90', y='xGChain_90', hover_name='player', hover_data=hover, color=takim_kolonu, size='size_tab3', size_max=max_b)
            st.plotly_chart(fig3, use_container_width=True)
            sekme_tablosu_ciz(df_tab3, ['player', takim_kolonu, 'league', 'Age', 'sade_pozisyon', mevcut_sure, 'xGBuildup_90', 'xGChain_90'], ['xGBuildup_90', 'xGChain_90'])

    with tab4:
        st.subheader("Kurtarış Yüzdesi vs Yediği Gol")
        df_gk = df_filtrelenmis[df_filtrelenmis['sade_pozisyon'] == 'GK'] if secili_mevki == 'Tümü' else df_filtrelenmis
        if not df_gk.empty and 'save_percent' in df_gk.columns:
            df_gk['size_tab4'] = pd.to_numeric(df_gk['saves'], errors='coerce').fillna(0).clip(lower=0) + 0.1
            hover = temel_hover.copy()
            hover['size_tab4'] = False
            fig_gk = px.scatter(df_gk, x='save_percent', y='ga90', hover_name='player', hover_data=hover, color=takim_kolonu, size='size_tab4', size_max=max_b)
            st.plotly_chart(fig_gk, use_container_width=True)
            sekme_tablosu_ciz(df_gk, ['player', takim_kolonu, 'league', 'Age', 'sade_pozisyon', mevcut_sure, 'saves', 'save_percent', 'ga90', 'cs'], ['save_percent', 'saves'])

    with tab5:
        st.subheader("Bireysel Profil Analizi ve Benzerlik Motoru")
        if not df_filtrelenmis.empty:
            secilen = st.selectbox("Oyuncu seçin:", df_filtrelenmis['player'].unique())
            if secilen:
                veri = df_filtrelenmis[df_filtrelenmis['player'] == secilen].iloc[0]
                kat = ['xG_90', 'xA_90', 'shots_90', 'key_passes_90', 'xGChain_90', 'xGBuildup_90']
                deg = [veri.get(k) or 0 for k in kat]
                
                c1, c2 = st.columns([2, 1])
                with c1:
                    fig4 = go.Figure()
                    fig4.add_trace(go.Scatterpolar(r=deg, theta=['xG', 'xA', 'Şut', 'K.Pas', 'xGChain', 'xGBuildup'], fill='toself', line=dict(color='#00cc96')))
                    fig4.update_layout(polar=dict(radialaxis=dict(visible=True, showline=False)), title=dict(text=f"<b>{secilen}</b>", x=0.5))
                    st.plotly_chart(fig4, use_container_width=True)
                
                with c2:
                    st.markdown("### 🤖 Benzerlik")
                    hedef_mevki = veri.get('sade_pozisyon')
                    df_havuz = df_filtrelenmis[df_filtrelenmis['sade_pozisyon'] == hedef_mevki].dropna(subset=kat)
                    if len(df_havuz) > 1:
                        X = df_havuz[kat].values
                        X_norm = (X - X.min(axis=0)) / (X.max(axis=0) - X.min(axis=0) + 1e-9)
                        hedef_vektor = X_norm[df_havuz.index.get_loc(veri.name)]
                        df_havuz['Skor'] = 100 - (np.linalg.norm(X_norm - hedef_vektor, axis=1) / np.sqrt(len(kat)) * 100)
                        en_benzer = df_havuz[df_havuz['player'] != secilen].nlargest(3, 'Skor')
                        for idx, r in en_benzer.iterrows(): st.success(f"⭐ {r['player']}\n\nSkor: **%{r['Skor']:.1f}**")
