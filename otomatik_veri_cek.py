import soccerdata as sd
import pandas as pd

def verileri_cek():
    print("Understat verileri çekiliyor...")
    
    # 5 Büyük Lig için Understat bağlantısı
    understat = sd.Understat(
        leagues=['ENG-Premier League', 'ESP-La Liga', 'ITA-Serie A', 'GER-Bundesliga', 'FRA-Ligue 1'], 
        seasons=2026
    )
    
    # Oyuncu sezon istatistiklerini çek
    df = understat.read_player_season_stats()
    df.reset_index(inplace=True)
    
    # CSV olarak kaydet
    df.to_csv('otomatik_understat_verileri.csv', index=False)
    print("İşlem Başarılı! 'otomatik_understat_verileri.csv' güncellendi.")

if __name__ == "__main__":
    verileri_cek()
