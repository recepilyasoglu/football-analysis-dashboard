import requests
import re
import json
import pandas as pd
import codecs
from datetime import datetime

def verileri_cek():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Veri çekme işlemi başlatılıyor...")
    
    # Understat'ın 5 büyük lig kodları
    leagues = {
        'EPL': 'ENG-Premier League',
        'La_liga': 'ESP-La Liga',
        'Bundesliga': 'GER-Bundesliga',
        'Serie_A': 'ITA-Serie A',
        'Ligue_1': 'FRA-Ligue 1'
    }
    
    # 2026-2027 sezonu için 2026 kullanıyoruz. (Gerekirse bu yılı değiştirebilirsin)
    season = '2026'
    all_players = []
    
    # Bot olduğumuzu gizlemek için standart bir tarayıcı kimliği
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    for league_code, league_name in leagues.items():
        url = f"https://understat.com/league/{league_code}/{season}"
        print(f"--> {league_name} verileri indiriliyor...")
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            # Understat verileri HTML içindeki bir JavaScript değişkenine gömer. O değişkeni Regex ile avlıyoruz.
            match = re.search(r"var playersData\s*=\s*JSON\.parse\('([^']+)'\);", response.text)
            if match:
                encoded_data = match.group(1)
                # Şifreli (hex) metni Python sözlüğüne çeviriyoruz
                decoded_data = codecs.decode(encoded_data, 'unicode_escape')
                players = json.loads(decoded_data)
                
                # İsimleri ve ligleri formatla
                for p in players:
                    p['player'] = p.pop('player_name', None) # player_name'i player yap
                    p['league'] = league_name
                    
                all_players.extend(players)
                print(f"    {len(players)} oyuncu başarıyla çekildi.")
            else:
                print(f"    HATA: {league_name} için veriler HTML içinde bulunamadı.")
                
        except Exception as e:
            print(f"    KRİTİK HATA ({league_name}): {e}")
            
    if all_players:
        df = pd.DataFrame(all_players)
        
        # Scout panosunda ihtiyacımız olan sütunları seçelim
        cols_to_keep = ['player', 'team_title', 'league', 'position', 'time', 'goals', 'xG', 'assists', 'xA', 'shots', 'key_passes', 'xGChain', 'xGBuildup']
        
        # Eksik kolon varsa çökmeyi engellemek için 0 ile doldur
        for col in cols_to_keep:
            if col not in df.columns:
                df[col] = 0
                
        df = df[cols_to_keep]
        
        # Dosyaya kaydet
        df.to_csv('otomatik_understat_verileri.csv', index=False, encoding='utf-8-sig')
        print(f"\n[BAŞARILI] Toplam {len(df)} oyuncunun verisi 'otomatik_understat_verileri.csv' dosyasına kaydedildi!")
    else:
        print("\n[BAŞARISIZ] Hiçbir veri çekilemedi. Lütfen bağlantınızı kontrol edin.")

if __name__ == "__main__":
    verileri_cek()
