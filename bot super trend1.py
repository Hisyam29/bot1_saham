import yfinance as yf
import pandas as pd
import requests
import time
import os

# =========================
# CONFIG
# =========================
TOKEN = "8265694791:AAHElCfxfPoB40pZe5yv9tvVcQEIFIAQUAw"
CHAT_IDS = [
    "1280847575",  # kamu
    
]

INTERVAL = "4h"
PERIOD = "30d"

ATR_PERIOD = 2
MULTIPLIER = 1

CHECK_INTERVAL = 1800  # 30 menit

# =========================
# TELEGRAM
# =========================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    for chat_id in CHAT_IDS:
        data = {
            "chat_id": chat_id,
            "text": message
        }
        try:
            res = requests.post(url, data=data)
            print(f"Telegram ke {chat_id}:", res.text)
        except:
            print(f"Gagal kirim ke {chat_id}")

# =========================
# LOAD SAHAM DARI EXCEL
# =========================
def load_symbols():
    df = pd.read_excel(r"C:\Users\Hisyam\OneDrive\Documents\Coding\saham.xlsx")

    print("KOLOM TERDETEKSI:", df.columns)

    # ambil kolom "Kode"
    symbols = df["Kode"].tolist()

    # bersihkan
    symbols = [str(s).strip().upper() for s in symbols if str(s) != 'nan']

    # tambah .JK
    symbols = [s + ".JK" for s in symbols]

    print("TOTAL SAHAM:", len(symbols))
    print(symbols[:10])

    return symbols

# =========================
# GET DATA
# =========================
def get_data(symbol):
    df = yf.download(symbol, period=PERIOD, interval=INTERVAL)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.dropna(inplace=True)
    return df

# =========================
# SUPER TREND (2,1)
# =========================
def compute_supertrend(df):
    df = df.copy()

    df['H-L'] = df['High'] - df['Low']
    df['H-C'] = (df['High'] - df['Close'].shift()).abs()
    df['L-C'] = (df['Low'] - df['Close'].shift()).abs()

    df['TR'] = df[['H-L','H-C','L-C']].max(axis=1)
    df['ATR'] = df['TR'].rolling(ATR_PERIOD).mean()

    hl2 = (df['High'] + df['Low']) / 2

    df['upperband'] = hl2 + MULTIPLIER * df['ATR']
    df['lowerband'] = hl2 - MULTIPLIER * df['ATR']

    df['in_uptrend'] = True

    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['upperband'].iloc[i-1]:
            df.loc[df.index[i], 'in_uptrend'] = True
        elif df['Close'].iloc[i] < df['lowerband'].iloc[i-1]:
            df.loc[df.index[i], 'in_uptrend'] = False
        else:
            df.loc[df.index[i], 'in_uptrend'] = df['in_uptrend'].iloc[i-1]

    return df

# =========================
# MAIN BOT
# =========================
def run_bot():
    symbols = load_symbols()

    send_telegram("🚀 BOT 1 AKTIF - SUPER TREND 4H (VOL SPIKE)")

    while True:
        print("Scanning market...")

        results = []

        for symbol in symbols:
            try:
                df = get_data(symbol)

                if len(df) < 20:
                    continue

                last_price = df['Close'].iloc[-1]
                volume_now = df['Volume'].iloc[-1]
                volume_avg = df['Volume'].rolling(20).mean().iloc[-1]

                # =========================
                # FILTER AWAL
                # =========================
                if volume_avg < 1_000_000:
                    continue

                if last_price < 100:
                    continue

                # =========================
                # FILTER VOLUME (WAJIB SPIKE)
                # =========================
                if volume_now < volume_avg * 1.5:
                    continue

                df = compute_supertrend(df)

                current_trend = df['in_uptrend'].iloc[-1]

                # =========================
                # HANYA AMBIL BULLISH
                # =========================
                if current_trend:
                    results.append((symbol, last_price, volume_now, volume_avg))

                # DEBUG
                print(symbol, "| Trend:", current_trend)

            except Exception as e:
                print("Error:", symbol, e)

        # =========================
        # OUTPUT
        # =========================
        if results:
            message = "🔥 SAHAM POTENSIAL (SUPER TREND + VOL SPIKE)\n\n"

            for r in results[:10]:
                message += f"{r[0]} | {int(r[1])}\n"

            send_telegram(message)

        else:
            send_telegram("❌ Tidak ada saham sesuai kriteria")

        print("Sleep...\n")
        time.sleep(CHECK_INTERVAL)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    run_bot()