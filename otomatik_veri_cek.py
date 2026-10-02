import cloudscraper
import re
import json
import codecs
import pandas as pd
from datetime import datetime

def understat_verilerini_cek():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Veri çekme işlemi başlatılıyor...")
    
    ligler = {
        'EPL': 'ENG-Premier League', 
        'La_liga': 'ESP-La Liga', 
        'Bundesliga': 'GER-Bundesliga', 
        'Serie_A': 'ITA-Serie A', 
        'Ligue_1': 'FRA-Ligue 1'
    }
    sezon = '2026' 
    tum_oyuncular = []
    
    # Gerçek tarayıcı kimliği
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    
    for lig_kodu, lig_adi in ligler.items():
        print(f"📡 {lig_adi} verileri çekiliyor...")
        url = f"https://understat.com/league/{lig_kodu}/{sezon}"
        
        try:
            response = scraper.get(url)
            
            if response.status_code == 200:
                html = response.text
                oyuncu_verisi = None
                
                # Sadece <script> etiketlerinin içini alıyoruz (Sayfanın geri kalanıyla ilgilenmiyoruz)
                script_blocks = re.findall(r"<script.*?>(.*?)</script>", html, re.DOTALL | re.IGNORECASE)
                
                for script in script_blocks:
                    if "var playersData" in script:
                        try:
                            # 1. EN GÜÇLÜ YÖNTEM: Makasla Kesme (Regex Yok!)
                            if "JSON.parse('" in script:
                                raw_data = script.split("JSON.parse('")[1].split("')")[0]
                                decoded_data = bytes(raw_data, 'utf-8').decode('unicode_escape')
                                oyuncu_verisi = json.loads(decoded_data)
                                break
                            
                            elif 'JSON.parse("' in script:
                                raw_data = script.split('JSON.parse("')[1].split('")')[0]
                                decoded_data = bytes(raw_data, 'utf-8').decode('unicode_escape')
                                oyuncu_verisi = json.loads(decoded_data)
                                break
                                
                            else:
                                # DEDEKTİF MODU: Site yapısı değiştiyse bize o satırı göster!
                                print(f"🔍 DEDEKTİF: Format değişmiş! İşte veri satırı: {script.strip()[:200]}")
                        except Exception as parse_err:
                            print(f"❌ {lig_adi} Şifre Çözme Hatası: {parse_err}")
                
                if oyuncu_verisi:
                    for oyuncu in oyuncu_verisi:
                        oyuncu['league'] = lig_adi
                        oyuncu['player'] = oyuncu.pop('player_name', None)
                    tum_oyuncular.extend(oyuncu_verisi)
                    print(f"✅ {lig_adi} BAŞARIYLA ÇEKİLDİ! ({len(oyuncu_verisi)} oyuncu)")
                elif not oyuncu_verisi and "DEDEKTİF" not in locals():
                    print(f"❌ {lig_adi} için HTML'de 'playersData' etiketi hiç bulunamadı!")
            else:
                print(f"❌ HTTP Hata kodu: {response.status_code}")
                
        except Exception as e:
            print(f"⚠ {lig_adi} Bağlantı hatası: {e}")
            
    # GÜVENLİK SİGORTASI
    if not tum_oyuncular:
        print("🚨 HİÇBİR VERİ ÇEKİLEMEDİ! İşlem iptal ediliyor, eski dosya korunacak.")
        return

    df = pd.DataFrame(tum_oyuncular)
    df = df.rename(columns={'team_title': 'team', 'time': 'minutes'})
    
    sayisal_kolonlar = ['goals', 'assists', 'shots', 'key_passes', 'xG', 'xA', 'xGChain', 'xGBuildup', 'minutes']
    for col in sayisal_kolonlar:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    dosya_adi = 'otomatik_understat_verileri.csv'
    df.to_csv(dosya_adi, index=False, encoding='utf-8-sig')
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 İŞLEM TAMAM! Toplam {len(df)} oyuncunun güncel verisi '{dosya_adi}' olarak kaydedildi.")

if __name__ == "__main__":
    understat_verilerini_cek()
