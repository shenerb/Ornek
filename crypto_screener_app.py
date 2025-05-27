import streamlit as st
import pandas as pd
import time
import ccxt
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="Kripto Dip & Hacim Tarayıcı", layout="centered")
st.title("📉 Binance Kripto Dip & Hacim Taraması")

# Binance API tanımı
exchange = ccxt.binance({
    'enableRateLimit': True
})

def fetch_symbols():
    try:
        markets = exchange.load_markets()
        return sorted([symbol for symbol in markets if symbol.endswith('/USDT') and 'spot' in markets[symbol]['type']])
    except Exception as e:
        st.error(f"Binance API bağlantı hatası: {e}")
        return []

# (Diğer fonksiyonlar aynen kalacak...)

# Ana arayüz

st.sidebar.header("🔧 Filtre Ayarları")
ma_tolerance = st.sidebar.slider("MA Yakınlık Toleransı (%)", 1, 10, 5) / 100
volume_threshold = st.sidebar.slider("Hacim Artış Eşiği (kat)", 1.0, 5.0, 1.5)
use_ma = st.sidebar.checkbox("MA Dip Filtresi Kullan", value=True)
use_rsi = st.sidebar.checkbox("RSI Dip Filtresi Kullan", value=False)
rsi_threshold = st.sidebar.slider("RSI Eşiği", 10, 50, 30)

# Binance API bağlantı testi butonu
if st.button("Test Binance Bağlantısı"):
    try:
        markets = exchange.load_markets()
        st.success(f"{len(markets)} piyasa yüklendi.")
    except Exception as e:
        st.error(f"Bağlantı hatası: {e}")

# Kripto tarama butonu ve işlemi
if st.button("🔍 Kripto Tarama Başlat"):
    with st.spinner("Binance üzerindeki kriptolar taranıyor..."):
        symbols = fetch_symbols()
        if not symbols:
            st.warning("Binance API'den veri alınamadı. Lütfen bağlantınızı veya API erişimini kontrol edin.")
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

                    # Grafik
                    data_plot = fetch_ohlcv(row['Sembol'], since_days=90)
                    data_plot['MA20'] = data_plot['close'].rolling(20).mean()
                    data_plot['MA50'] = data_plot['close'].rolling(50).mean()
                    data_plot['MA200'] = data_plot['close'].rolling(200).mean()
                    plot_crypto_chart(data_plot, row['Sembol'])
