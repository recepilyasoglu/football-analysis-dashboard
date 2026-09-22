import soccerdata as sd
import pandas as pd

def verileri_guncelle():
    print("Understat üzerinden veri çekme işlemi başlatılıyor...")
    
    try:
        # FBref yerine veri kaynağı olarak Understat'ı seçiyoruz
        # Understat, doğrudan xG, Şut, Gol verilerine odaklıdır ve botlara çok daha ılımlı yaklaşır
        understat = sd.Understat(
            leagues=[
                "ENG-Premier League", 
                "ESP-La Liga", 
                "ITA-Serie A", 
                "GER-Bundesliga", 
                "FRA-Ligue 1"
            ], 
            seasons="2026"  # Understat sezonu genellikle başlangıç yılıyla (2026) alır
        )
        
        # Oyuncuların sezonluk istatistiklerini (şut, gol, xG vs. hepsi içindedir) çekiyoruz
        print("İstatistikler indiriliyor, lütfen bekleyin...")
        df_stats = understat.read_player_season_stats()
        
        # Veriyi düzleştirip CSV'ye kaydediyoruz
        df_stats.reset_index(inplace=True)
        df_stats.to_csv('otomatik_understat_verileri.csv', index=False)
        
        print("İşlem BAŞARILI! Veriler 'otomatik_understat_verileri.csv' dosyasına kaydedildi.")
        
    except Exception as e:
        print(f"Veri çekilirken bir hata oluştu: {e}")

if __name__ == "__main__":
    verileri_guncelle()