# ⚽ Dinamik Oyuncu Scout Panosu (Football Analytics Dashboard)

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3f4f75?logo=plotly&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)

Avrupa'nın 5 Büyük Ligi'ndeki oyuncuların detaylı hücum, pas ve savunma metriklerini analiz etmek, yeni yetenekleri (U23) keşfetmek ve oyuncu performanslarını görselleştirmek için geliştirilmiş veri bilimi destekli **Scout (Yetenek Avcısı) Panosu**.

## 🚀 Proje Hakkında

Bu proje, futbol veri analitiğini kolaylaştırmak amacıyla tasarlanmıştır. **Understat** üzerinden çekilen güncel performans verileri (xG, xA, xGChain, xGBuildup vb.) ile **FBref** kaynaklı oyuncu doğum tarihleri, özel geliştirilmiş bir **Yapay Zeka Destekli Bulanık Eşleştirme (Fuzzy Matching)** algoritması ile birleştirilmektedir. 

Böylece isimler farklı formatlarda yazılmış olsa bile (örn. *Kylian Mbappé* ile *Kylian Mbappe-Lottin*), sistem oyuncuları otomatik tanır ve yaş, mevki, dakika filtrelerinin kusursuz çalışmasını sağlar.

## ✨ Öne Çıkan Özellikler

- 🤖 **Akıllı Veri Eşleştirme:** Özel `super_temizle` fonksiyonu ve `difflib` algoritması sayesinde farklı veri setlerindeki özel karakterli ve uyumsuz isimler %80 benzerlik eşiğiyle otomatik eşleşir.
- 🔄 **Bağımsız ve Dinamik Veri Çekme:** Dış kütüphanelere bağlı kalmadan saf Python kullanılarak Understat'ın JSON yapısı çözümlenir ve veriler otomatik güncellenir.
- 🎯 **Mevkiye Özel Sekmeler ve Tablolar:**
  - **Keskin Nişancılar:** Forvetler için Gol vs xG analizi.
  - **10 Numaralar & Kanatlar:** Playmaker'lar için Asist vs xA analizi.
  - **Gizli Kahramanlar:** Orta saha ve defanslar için xGChain vs xGBuildup (Oyun Kurulumu) analizi.
  - **Eldivenler:** Kaleciler için Kurtarış Yüzdesi analizi.
- 🕸️ **Bireysel Profil Radarı:** Seçilen oyuncunun tüm metriklerini tek bir radar grafiğinde (Plotly) rakipleriyle kıyaslanabilir formatta sunar.
- 👦 **U23 Akıllı Filtreleme:** Sadece 23 yaş ve altı oyuncuları filtreleyerek "Wonderkid" avına çıkmanızı sağlar. Yaşı bulunamayan verileri (manipülasyondan kaçınarak) filtre dışında tutar.

## 📂 Veri Kaynakları

1. **İstatistikler:** [Understat](https://understat.com/) (xG, xA, Dakika, Gol vb.)
2. **Yaş ve Profil:** [FBref](https://fbref.com/) (Oyuncu Doğum Yılları)
3. **Kaleci Verileri:** Manuel/Dışa Aktarılmış Kaleci CSV veri seti.

## 🛠️ Kurulum ve Çalıştırma

Projeyi kendi bilgisayarınızda çalıştırmak için aşağıdaki adımları izleyebilirsiniz:

1. Repoyu bilgisayarınıza klonlayın:
   ```bash
   git clone https://github.com/KULLANICI_ADIN/REPO_ADIN.git
   cd REPO_ADIN
   ```

2. Gerekli kütüphaneleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
   *(Not: `requirements.txt` dosyanızda pandas, streamlit, plotly, requests gibi kütüphanelerin bulunduğundan emin olun.)*

3. Uygulamayı başlatın:
   ```bash
   streamlit run app.py
   ```

## 📜 Dosya Yapısı

- `app.py`: Streamlit arayüzünü, görselleştirmeleri ve Fuzzy Matching algoritmalarını içeren ana uygulama dosyası.
- `otomatik_veri_cek.py`: Understat üzerinden güncel sezon verilerini kazıyan bağımsız Python scripti.
- `otomatik_understat_verileri.csv`: Bot tarafından çekilen güncel ana istatistik dosyası.
- `oyuncu_dogum_tarihleri.csv`: FBref tabanlı, akıllı okuyucu ile işlenen yaş dosyası.
- `kaleci_verileri.csv`: Kalecilere özel (Save%, GA90 vb.) istatistikleri barındıran dosya.

---
*Bu proje açık kaynaklıdır ve futbol veri analizine ilgi duyan herkesin katkısına açıktır.*