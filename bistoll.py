import os
import yfinance as yf
import feedparser
from tradingview_ta import TA_Handler, Interval
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markup import escape
import time

console = Console()

def get_comprehensive_news(symbol):
    rss_urls = [
        "https://tr.investing.com/rss/news_25.rss",        
        "https://tr.investing.com/rss/news_285.rss",       
        "https://tr.investing.com/rss/stock_market_news.rss"
    ]
    news_results = []
    seen_titles = set()
    kritik_kelimeler = [symbol, "BORSA", "BIST", "KAP", "SAVAŞ", "FED", "FAİZ", "KRİZ", "ABD", "İHALE", "BİLANÇO"]

    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title_upper = entry.title.upper()
                if any(k in title_upper for k in kritik_kelimeler):
                    if entry.title not in seen_titles:
                        # Rich etiketlerini bozmaması için başlığı temizliyoruz
                        news_results.append(f"• {escape(entry.title)}")
                        seen_titles.add(entry.title)
        except: continue
    
    if len(news_results) < 3:
        try:
            feed_gen = feedparser.parse(rss_urls[0])
            for entry in feed_gen.entries[:4]:
                if entry.title not in seen_titles:
                    news_results.append(f"• [Genel] {escape(entry.title)}")
        except: pass
    return news_results[:8]

# --- 3. ANA ANALİZ MOTORU ---
def analyze_stock(symbol):
    console.print(f"\n[bold cyan]📡 {symbol} Analiz Ediliyor (5sn Periyot Koruması Aktif)...[/bold cyan]")
    
    periyotlar = {
        "5 Dakika": Interval.INTERVAL_5_MINUTES, 
        "15 Dakika": Interval.INTERVAL_15_MINUTES, 
        "Günlük": Interval.INTERVAL_1_DAY, 
        "Haftalık": Interval.INTERVAL_1_WEEK
    }
    
    time_results = []
    for label, inter in periyotlar.items():
        try:
            console.print(f"[dim]>> {label} verisi çekiliyor...[/dim]")
            time.sleep(5) # 429 Hatası almamak için 5 saniye bekleme
            handler = TA_Handler(symbol=symbol, exchange="BIST", screener="turkey", interval=inter)
            res = handler.get_analysis().summary['RECOMMENDATION']
            time_results.append((label, res))
        except Exception as e:
            msg = "SINIR AŞILDI" if "429" in str(e) else "HATA"
            time_results.append((label, msg))

    # Teknik Detaylar (Günlük)
    try:
        ticker = yf.Ticker(f"{symbol}.IS")
        handler_main = TA_Handler(symbol=symbol, exchange="BIST", screener="turkey", interval=Interval.INTERVAL_1_DAY)
        ta_main = handler_main.get_analysis()
        hist = ticker.history(period="10d")
        
        last_p = ta_main.indicators['close']
        h, l = ta_main.indicators['high'], ta_main.indicators['low']
        pivot = (h + l + last_p) / 3
        r1, s1 = (2 * pivot) - l, (2 * pivot) - h
        
        vol_avg = hist['Volume'].mean()
        vol_now = ta_main.indicators['volume']
        vol_ratio = vol_now / vol_avg
        vol_status = f"[bold green]PATLAMA (%{vol_ratio*100:.0f})[/bold green]" if vol_ratio > 1.4 else "Normal"
        
        # Mum Formasyonu
        o_p, c_p = ta_main.indicators['open'], last_p
        body = abs(c_p - o_p)
        pattern = "Belirsiz"
        if body < (h - l) * 0.1: pattern = "DOJİ (Kararsızlık)"
        elif (c_p - l) > body * 2: pattern = "ÇEKİÇ (Boğa)"
        elif (h - max(o_p, c_p)) > body * 2: pattern = "MEZAR TAŞI"

    except Exception as e:
        console.print(f"[red]Teknik veri hatası: {e}[/red]")
        return

    console.clear()

    # Vade Tablosu (Markup hatası düzeltildi)
    v_table = Table(title=f"\n[bold yellow]{symbol} Stratejik Analiz[/bold yellow]")
    v_table.add_column("Periyot", style="cyan")
    v_table.add_column("Sinyal", style="bold")
    for lab, res in time_results:
        color = "white"
        if "BUY" in res: color = "green"
        elif "SELL" in res: color = "red"
        elif "SINIR" in res or "HATA" in res: color = "yellow"
        v_table.add_row(lab, f"[{color}]{res}[/{color}]")
    console.print(v_table)

    # Teknik Radar
    radar = Table(title="Teknik Radar")
    radar.add_column("Özellik", style="magenta")
    radar.add_column("Değer", style="yellow")
    radar.add_row("Pivot / Fiyat", f"{pivot:.2f} / {last_p:.2f}")
    radar.add_row("Direnç (R1)", f"[red]{r1:.2f}[/red]")
    radar.add_row("Destek (S1)", f"[green]{s1:.2f}[/green]")
    radar.add_row("Hacim / Mum", f"{vol_status} / {pattern}")
    console.print(radar)

    news = get_comprehensive_news(symbol)
    console.print(Panel("\n".join(news), title="🔥 Haber Akışı & Jeopolitik", border_style="red"))

# --- ANA MENÜ ---
def main():
    try:
        txt_files = [f for f in os.listdir('.') if f.endswith('.txt')]
        if not txt_files:
            console.print("[red]Hata: Sektör dosyaları bulunamadı![/red]")
            return
        
        for i, f in enumerate(txt_files, 1):
            console.print(f"{i}. {f.upper().replace('.TXT', '')}")
        
        s_idx = int(console.input("\nSektör No: ")) - 1
        with open(txt_files[s_idx], 'r', encoding='utf-8') as f:
            hisseler = [l.strip().upper() for l in f if l.strip()]
        
        for i, h in enumerate(hisseler, 1):
            console.print(f"{i}. {h}")
        
        h_idx = int(console.input("\nHisse No: ")) - 1
        analyze_stock(hisseler[h_idx])
    except (ValueError, IndexError):
        console.print("[red]Geçersiz seçim![/red]")
    except Exception as e:
        console.print(f"[red]Beklenmedik hata: {e}[/red]")

if __name__ == "__main__":
    main()
