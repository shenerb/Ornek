import streamlit as st
import pandas as pd
import time
import ccxt
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="Kripto Dip & Hacim Tarayıcı", layout="centered")
st.title("📉 Gate.io Kripto Dip & Hacim Taraması")

# Gate.io API tanımı
exchange = ccxt.gateio({
    'enableRateLimit': True
})

def fetch_symbols():
    try:
        markets = exchange.load_markets()
        # Gate.io sembollerinde alt çizgi var, USDT ile biten spot pariteleri seçiyoruz
        return sorted([symbol for symbol in markets if symbol.endswith('_USDT') and markets[symbol]['spot']])
    except Exception as e:
        st.error(f"Gate.io API bağlantı hatası: {e}")
        return []

def fetch_ohlcv(symbol, timeframe='1d', since_days=90):
    since = exchange.milliseconds() - since_days * 24 * 60 * 60 * 1000
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def plot_crypto_chart(data, symbol):
    plt.figure(figsize=(10, 4))
    plt.plot(data.index, data['close'], label="Kapanış", color="blue")
    plt.plot(data.index, data["MA20"], label="MA20", color="orange")
    plt.plot(data.index, data["MA50"], label="MA50", color="green")
    plt.plot(data.index, data["MA200"], label="MA200", color="red")
    plt.title(f"{symbol} - Son 90 Gün")
    plt.legend()

    plt.text(
        0.5, 0.5, "Bay-P",
        fontsize=40,
        color="gray",
        alpha=0.15,
        ha="center",
        va="center",
        transform=plt.gca().transAxes,
        weight="bold"
    )
    plt.tight_layout()
    st.pyplot(plt)
    plt.clf()

def scan_cryptos(symbols, ma_tolerance, volume_threshold, use_ma, use_rsi, rsi_threshold):
    results = []
    for symbol in symbols:
        try:
            data = fetch_ohlcv(symbol)
            if len(data) < 30:
                continue

            data['MA20'] = data['close'].rolling(20).mean()
            data['MA50'] = data['close'].rolling(50).mean()
            data['MA200'] = data['close'].rolling(200).mean()
            data['AvgVolume20'] = data['volume'].rolling(20).mean()
            data['RSI'] = calculate_rsi(data['close'])

            close = data['close'].iloc[-1]
            prev_close = data['close'].iloc[-2]
            change_pct = ((close - prev_close) / prev_close) * 100

            ma20 = data['MA20'].iloc[-1]
            ma50 = data['MA50'].iloc[-1]
            ma200 = data['MA200'].iloc[-1]
            rsi = data['RSI'].iloc[-1]
            volume = data['volume'].iloc[-1]
            avg_volume = data['AvgVolume20'].iloc[-1]
            volume_ratio = volume / avg_volume if avg_volume else 0

            is_near_ma = close < ma20 * (1 + ma_tolerance) or close < ma50 * (1 + ma_tolerance) or close < ma200 * (1 + ma_tolerance)
            passes_ma = is_near_ma if use_ma else True
            passes_volume = volume_ratio >= volume_threshold
            passes_rsi = rsi <= rsi_threshold if use_rsi else True

            if passes_ma and passes_volume and passes_rsi:
                results.append({
                    'Sembol': symbol,
                    'Kapanış': round(close, 4),
                    'Değişim %': round(change_pct, 2),
                    'MA20': round(ma20, 4),
                    'MA50': round(ma50, 4),
                    'RSI': round(rsi, 2),
                    'Hacim Katsayısı': round(volume_ratio, 2)
                })
        except Exception:
            continue
        time.sleep(0.1)
    return pd.DataFrame(results)

# Arayüz
st.sidebar.header("🔧 Filtre Ayarları")
ma_tolerance = st.sidebar.slider("MA Yakınlık Toleransı (%)", 1, 10, 5) / 100
volume_threshold = st.sidebar.slider("Hacim Artış Eşiği (kat)", 1.0, 5.0, 1.5)
use_ma = st.sidebar.checkbox("MA Dip Filtresi Kullan", value=True)
use_rsi = st.sidebar.checkbox("RSI Dip Filtresi Kullan", value=False)
rsi_threshold = st.sidebar.slider("RSI Eşiği", 10, 50, 30)

# Gate.io API bağlantı testi butonu
if st.button("Test Gate.io Bağlantısı"):
    try:
        markets = exchange.load_markets()
        st.success(f"{len(markets)} piyasa yüklendi.")
    except Exception as e:
        st.error(f"Bağlantı hatası: {e}")

if st.button("🔍 Kripto Tarama Başlat"):
    with st.spinner("Gate.io üzerindeki kriptolar taranıyor..."):
        symbols = fetch_symbols()
        if not symbols:
            st.warning("Gate.io API'den veri alınamadı. Lütfen bağlantınızı veya API erişimini kontrol edin.")
        else:
            df = scan_cryptos(symbols, ma_tolerance, volume_threshold, use_ma, use_rsi, rsi_threshold)

            if df.empty:
                st.warning("Kriterlere uyan kripto bulunamadı.")
            else:
                st.success(f"{len(df)} kripto bulundu.")
                for _, row in df.iterrows():
                    color = "green" if row['Değişim %'] >= 0 else "red"
                    icon = "▲" if row['Değişim %'] >= 0 else "▼"

                    st.markdown(f"""
                        <div style="border:1px solid #ccc; border-radius:10px; padding:10px; margin:10px 0;">
                            <strong>{row['Sembol']}</strong><br>
                            Kapanış: <span style="color:{color}; font-weight:bold;">
                                {row['Kapanış']} ({icon} {abs(row['Değişim %'])}%)
                            </span><br>
                            MA20: {row['MA20']} | MA50: {row['MA50']}<br>
                            RSI: <b>{row['RSI']}</b> | Hacim/Ort.: <b>{row['Hacim Katsayısı']}</b><br>
                        </div>
                    """, unsafe_allow_html=True)

                    data_plot = fetch_ohlcv(row['Sembol'], since_days=90)
                    data_plot['MA20'] = data_plot['close'].rolling(20).mean()
                    data_plot['MA50'] = data_plot['close'].rolling(50).mean()
                    data_plot['MA200'] = data_plot['close'].rolling(200).mean()
                    plot_crypto_chart(data_plot, row['Sembol'])
