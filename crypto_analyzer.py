# Importujeme potřebné knihovny
from binance.client import Client
import pandas as pd
import ta
import numpy as np
from datetime import datetime, timezone
import config  # Zde budou API klíče
import os

# Vytvoříme připojení k Binance
client = Client(config.API_KEY, config.API_SECRET)

def get_historical_data(symbol, interval, lookback):
    """
    Získá historická data z Binance API.
    
    Args:
        symbol (str): Trading pár (např. 'BTCUSDT')
        interval (str): Časový interval ('1h', '15m', '1w', '1M')
        lookback (int): Počet svíček k získání
        
    Returns:
        pd.DataFrame: DataFrame s historickými daty nebo None při chybě
    """
    try:
        print(f"Získávám data pro {symbol} s intervalem {interval}...")
        
        # Získáme data z Binance
        klines = client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            limit=lookback
        )
        
        if not klines:
            print(f"Žádná data nebyla nalezena pro {symbol} s intervalem {interval}")
            return None
            
        # Vytvoříme DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Převedeme timestamp na datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Převedeme sloupce na správné datové typy
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Kontrola chybějících hodnot
        if df[numeric_columns].isnull().any().any():
            print(f"Varování: Nalezeny chybějící hodnoty v datech pro {symbol}")
            df = df.dropna(subset=numeric_columns)
            
        if df.empty:
            print(f"Po vyčištění dat nezbyly žádné platné záznamy pro {symbol}")
            return None
            
        # Ponecháme jen potřebné sloupce
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        # Převedeme čas na lokální časovou zónu
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Europe/Prague')
        
        print(f"Úspěšně získáno {len(df)} záznamů pro {symbol}")
        return df
        
    except Exception as e:
        print(f"Chyba při získávání dat pro {symbol}: {str(e)}")
        return None

def add_indicators(df):
    """
    Přidá technické indikátory do DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame s historickými daty
        
    Returns:
        pd.DataFrame: DataFrame s přidanými indikátory
    """
    if df is None or df.empty:
        print("Prázdný DataFrame - nelze vypočítat indikátory")
        return None

    try:
        # Vytvoříme kopii DataFrame
        df = df.copy()
        
        # Převedeme sloupce na float
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            df[col] = df[col].astype(float)
        
        # Zkontrolujeme NaN hodnoty v close cenách
        if df['close'].isnull().any():
            print("Varování: Nalezeny NaN hodnoty v close cenách")
            # Vyplníme NaN hodnoty metodou forward fill a pak backward fill
            df['close'] = df['close'].ffill().bfill()
        
        # Přidáme EMA indikátory
        df['EMA9'] = ta.trend.ema_indicator(close=df['close'], window=9)
        df['EMA21'] = ta.trend.ema_indicator(close=df['close'], window=21)
        df['EMA50'] = ta.trend.ema_indicator(close=df['close'], window=50)
        
        # Přidáme RSI
        df['RSI'] = ta.momentum.rsi(close=df['close'], window=14)
        
        # Přidáme Bollinger Bands
        bb_indicator = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
        df['BB_horni'] = bb_indicator.bollinger_hband()
        df['BB_dolni'] = bb_indicator.bollinger_lband()
        
        # Přidáme změnu za posledních 5 svíček v procentech
        df['zmena_5_svicek'] = df['close'].pct_change(periods=5) * 100
        
        # Přidáme volatilitu (10denní směrodatná odchylka zavíracích cen)
        df['volatilita_10'] = df['close'].rolling(window=10).std()
        
        # Přidáme sloupec je_stagnace
        df['je_stagnace'] = False
        
        # Vyplníme NaN hodnoty v indikátorech metodou forward fill a pak backward fill
        indicator_columns = ['EMA9', 'EMA21', 'EMA50', 'RSI', 'BB_horni', 'BB_dolni', 
                           'zmena_5_svicek', 'volatilita_10']
        for col in indicator_columns:
            df[col] = df[col].ffill().bfill()
        
        return df
        
    except Exception as e:
        print(f"Chyba při výpočtu indikátorů: {str(e)}")
        return None

def analyze_stagnation(df):
    """
    Analyzuje stagnaci ceny v DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame s historickými daty
        
    Returns:
        pd.DataFrame: DataFrame s přidaným sloupcem je_stagnace
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                   'EMA20', 'EMA50', 'EMA200', 'RSI', 'BB_horni', 'BB_dolni', 'zmena_5_svicek',
                                   'EMA9', 'EMA21', 'volatilita_10', 'je_stagnace'])
    
    # Vypočítáme procentuální změnu ceny
    df['zmena_ceny'] = df['close'].pct_change()
    
    # Definujeme práh pro stagnaci (0.1% = 0.001)
    prah_stagnace = 0.001
    
    # Označíme periody, kde je změna ceny menší než práh
    df['je_stagnace'] = (abs(df['zmena_ceny']) < prah_stagnace).astype(int)
    
    # Odstraníme pomocný sloupec
    df = df.drop('zmena_ceny', axis=1)
    
    return df

def get_usdt_pairs():
    """
    Získá seznam všech dostupných párů s USDT z Binance.
    
    Returns:
        list: Seznam symbolů párů s USDT
    """
    try:
        # Získáme informace o všech symbolech
        exchange_info = client.get_exchange_info()
        
        # Vyfiltrujeme pouze USDT páry
        usdt_pairs = [symbol['symbol'] for symbol in exchange_info['symbols'] 
                     if symbol['symbol'].endswith('USDT') and symbol['status'] == 'TRADING']
        
        # Seřadíme abecedně
        usdt_pairs.sort()
        return usdt_pairs
    except Exception as e:
        print(f"Chyba při získávání seznamu párů: {str(e)}")
        return []

# Hlavní část programu
if __name__ == "__main__":
    try:
        # Pokud není specifikován symbol, použijeme výchozí BTCUSDT
        symbol = os.environ.get('SELECTED_SYMBOL', 'BTCUSDT')
        interval = '1h'     # Časový interval
        lookback = 100      # Počet svíček
        
        # Získáme hodinová data
        df = get_historical_data(symbol, interval, lookback)
        if df is not None:
            df = add_indicators(df)
            df = analyze_stagnation(df)
            
            # Vypíšeme statistiky pro hodinová data
            print("\nStatistiky hodinových dat (posledních 24 hodin):")
            last_24h = df.tail(24)
            print(f"Průměrný objem: {last_24h['volume'].mean():.2f}")
            print(f"Průměrná volatilita: {last_24h['volatilita_10'].mean():.2f}")
            print(f"Počet stagnujících period: {last_24h['je_stagnace'].sum()}")
            print(f"EMA9: {last_24h['EMA9'].iloc[-1]:.2f}")
            print(f"EMA21: {last_24h['EMA21'].iloc[-1]:.2f}")
            print(f"EMA50: {last_24h['EMA50'].iloc[-1]:.2f}")
            print(f"RSI: {last_24h['RSI'].iloc[-1]:.2f}")
            
            # Uložíme hodinová data
            df.to_csv(f'{symbol}_{interval}_data.csv', index=False)

        # Nastavení parametrů pro 15minutové svíčky
        interval_15m = '15m'
        lookback_15m = 100
        
        # Získáme 15minutová data
        df_15m = get_historical_data(symbol, interval_15m, lookback_15m)
        if df_15m is not None:
            df_15m = add_indicators(df_15m)
            df_15m = analyze_stagnation(df_15m)
            
            # Vypíšeme statistiky pro 15minutová data
            print("\nStatistiky 15minutových dat (posledních 24 hodin):")
            last_24h_15m = df_15m.tail(96)  # 96 15minutových svíček = 24 hodin
            print(f"Průměrný objem: {last_24h_15m['volume'].mean():.2f}")
            print(f"Průměrná volatilita: {last_24h_15m['volatilita_10'].mean():.2f}")
            print(f"Počet stagnujících period: {last_24h_15m['je_stagnace'].sum()}")
            print(f"EMA9: {last_24h_15m['EMA9'].iloc[-1]:.2f}")
            print(f"EMA21: {last_24h_15m['EMA21'].iloc[-1]:.2f}")
            print(f"EMA50: {last_24h_15m['EMA50'].iloc[-1]:.2f}")
            print(f"RSI: {last_24h_15m['RSI'].iloc[-1]:.2f}")
            
            # Uložíme 15minutová data
            df_15m.to_csv(f'{symbol}_{interval_15m}_data.csv', index=False)

        # Nastavení parametrů pro týdenní svíčky
        interval_1w = '1w'
        lookback_1w = 100  # Změněno na 100 týdenních svíček
        
        # Získáme týdenní data
        df_1w = get_historical_data(symbol, interval_1w, lookback_1w)
        if df_1w is not None:
            df_1w = add_indicators(df_1w)
            df_1w = analyze_stagnation(df_1w)
            
            # Vypíšeme statistiky pro týdenní data
            print("\nStatistiky týdenních dat:")
            print(f"Průměrný objem: {df_1w['volume'].mean():.2f}")
            print(f"Průměrná volatilita: {df_1w['volatilita_10'].mean():.2f}")
            print(f"Počet stagnujících period: {df_1w['je_stagnace'].sum()}")
            print(f"EMA9: {df_1w['EMA9'].iloc[-1]:.2f}")
            print(f"EMA21: {df_1w['EMA21'].iloc[-1]:.2f}")
            print(f"EMA50: {df_1w['EMA50'].iloc[-1]:.2f}")
            print(f"RSI: {df_1w['RSI'].iloc[-1]:.2f}")
            
            # Uložíme týdenní data
            df_1w.to_csv(f'{symbol}_{interval_1w}_data.csv', index=False)
            
    except Exception as e:
        print(f"\nChyba při zpracování dat: {str(e)}") 