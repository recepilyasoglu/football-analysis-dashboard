import soccerdata as sd
import pandas as pd

print("Understat verileri çekiliyor...")

# Understat nesnesini başlatıyoruz
u = sd.Understat(leagues=['ENG-Premier League', 'ESP-La Liga', 'ITA-Serie A', 'GER-Bundesliga', 'FRA-Ligue 1'], seasons=2026)

# Doğru metod argümansız veya standart çağrılır
df_shots = u.read_player_season_stats()
df_shots.reset_index(inplace=True)

# Kolon isimlerini kontrol edip kaydedelim
df_shots.to_csv('otomatik_veri_cek.csv', index=False)
print("BAŞARILI! 'otomatik_veri_cek.csv' dosyası güncellendi.")