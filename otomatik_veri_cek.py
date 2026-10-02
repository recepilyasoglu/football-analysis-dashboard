import requests
import json
import re
import codecs
import pandas as pd
from datetime import datetime

def understat_verilerini_cek():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Veri çekme işlemi başlatılıyor...")
    
    # 5 Büyük Lig ve Güncel Sezon (2026/2027 sezonu için '2026' kullanıyoruz)
    ligler = {
        'EPL': 'ENG-Premier League', 
        'La_liga': 'ESP-La Liga', 
        'Bundesliga': 'GER-Bundesliga', 
        'Serie_A': 'ITA-Serie A', 
        'Ligue_1': 'FRA-Ligue 1'
    }
    sezon = '2026' 
    
    tum_oyuncular = []
    
    # Her bir lig için Understat sunucularına bağlanıyoruz
    for lig_kodu, lig_adi in ligler.items():
        print(f"📡 {lig_adi} verileri çekiliyor...")
        url = f"https://understat.com/league/{lig_kodu}/{sezon}"
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Understat veriyi sayfanın içine şifreli bir JSON olarak gizler, onu Regex ile buluyoruz
            match = re.search(r"playersData\s*=\s*JSON\.parse\('(.*?)'\)", response.text)
            
            if match:
                # Şifreli JSON metnini çöz (Decode)
                encoded_json = match.group(1)
                decoded_json = codecs.escape_decode(encoded_json.encode('utf-8'))[0].decode('utf-8')
                oyuncu_verisi = json.loads(decoded_json)
                
                # Hangi ligden geldiğini ekleyelim (app.py'deki lig filtresi için)
                for oyuncu in oyuncu_verisi:
                    oyuncu['league'] = lig_adi
                    
                tum_oyuncular.extend(oyuncu_verisi)
                print(f"✅ {lig_adi} başarıyla çekildi. ({len(oyuncu_verisi)} oyuncu)")
            else:
                print(f"❌ {lig_adi} için JSON verisi bulunamadı!")
                
        except Exception as e:
            print(f"⚠️ {lig_adi} çekilirken hata oluştu: {e}")
            
    # Verileri bir Pandas DataFrame'ine çevir
    df = pd.DataFrame(tum_oyuncular)
    
    # Sütun isimlerini bizim app.py'nin beklediği formata göre ayarlayalım
    df = df.rename(columns={
        'player_name': 'player',
        'team_title': 'team',
        'time': 'minutes'
    })
    
    # Sayısal verileri doğru formata çevir
    sayisal_kolonlar = ['goals', 'assists', 'shots', 'key_passes', 'xG', 'xA', 'xGChain', 'xGBuildup', 'minutes']
    for col in sayisal_kolonlar:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # Dosyayı app.py'nin okuduğu isimle tam üstüne kaydediyoruz!
    dosya_adi = 'otomatik_understat_verileri.csv'
    df.to_csv(dosya_adi, index=False, encoding='utf-8')
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 İŞLEM TAMAM! Toplam {len(df)} oyuncunun güncel verisi '{dosya_adi}' olarak kaydedildi.")

if __name__ == "__main__":
    understat_verilerini_cek()
