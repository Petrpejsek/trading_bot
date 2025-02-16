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
        
        # Pro denní data zkusíme získat více historických dat
        if interval == '1d':
            try:
                # Nejprve zkusíme získat 200 denních svíček
                klines = client.get_historical_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=200  # Maximálně 200 denních svíček
                )
            except:
                try:
                    # Pokud se nepodaří 200, zkusíme získat tolik, kolik je dostupných
                    klines = client.get_historical_klines(
                        symbol=symbol,
                        interval=interval,
                        limit=lookback
                    )
                except:
                    print(f"Nepodařilo se získat denní data pro {symbol}")
                    return None
        else:
            # Pro ostatní časové rámce použijeme standardní počet
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
        
        # Kontrola minimálního počtu svíček - snížíme na 20 pro novější páry
        if len(df) < 20:  # Minimálně 20 svíček pro základní indikátory
            print(f"Nedostatek dat pro výpočet indikátorů (nalezeno {len(df)} svíček, potřeba alespoň 20)")
            # Vytvoříme prázdný DataFrame se stejnými sloupci
            empty_df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                           'EMA9', 'EMA21', 'EMA50', 'RSI', 'BB_upper', 'BB_middle', 'BB_lower',
                                           'MACD', 'MACD_signal', 'MACD_hist', 'volatilita_10', 'zmena_5_svicek'])
            return empty_df
        
        # Převedeme sloupce na float a vyčistíme NaN hodnoty
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].ffill().bfill()  # Vyplníme chybějící hodnoty
        
        # EMA indikátory
        df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['EMA50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # První průměr - klasický SMA pro prvních 14 period
        first_avg_gain = gain.rolling(window=14, min_periods=14).mean()
        first_avg_loss = loss.rolling(window=14, min_periods=14).mean()
        
        # Inicializujeme průměry
        avg_gain = pd.Series(index=df.index, dtype=float)
        avg_loss = pd.Series(index=df.index, dtype=float)
        
        # Nastavíme první hodnoty
        avg_gain.iloc[13] = first_avg_gain.iloc[13]  # 14. perioda (index 13)
        avg_loss.iloc[13] = first_avg_loss.iloc[13]
        
        # Wilderův způsob průměrování: ((předchozí avg * 13) + aktuální hodnota) / 14
        for i in range(14, len(df)):
            avg_gain.iloc[i] = (avg_gain.iloc[i-1] * 13 + gain.iloc[i]) / 14
            avg_loss.iloc[i] = (avg_loss.iloc[i-1] * 13 + loss.iloc[i]) / 14
        
        # Výpočet RS a RSI
        rs = avg_gain / avg_loss.where(avg_loss != 0, float('inf'))
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Speciální případy
        df.loc[avg_loss == 0, 'RSI'] = 100  # Když není žádná ztráta, RSI = 100
        df.loc[avg_gain == 0, 'RSI'] = 0    # Když není žádný zisk, RSI = 0
        
        # Prvních 14 period nemá platné hodnoty
        df.loc[:13, 'RSI'] = None
        
        # Ošetření NaN hodnot
        df['RSI'] = df['RSI'].fillna(50)
        df['RSI'] = df['RSI'].clip(0, 100)
        
        # Bollinger Bands (20 period SMA s 2 směrodatnými odchylkami)
        df['BB_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
        df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
        
        # MACD (12,26,9)
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        
        # Volatilita (10denní směrodatná odchylka zavíracích cen)
        df['volatilita_10'] = df['close'].rolling(window=10).std()
        
        # Změna za posledních 5 svíček v procentech
        df['zmena_5_svicek'] = df['close'].pct_change(periods=5) * 100
        
        # Vyplníme NaN hodnoty v indikátorech
        indicator_columns = ['EMA9', 'EMA21', 'EMA50', 'RSI', 'BB_upper', 'BB_lower', 'BB_middle',
                           'MACD', 'MACD_signal', 'MACD_hist', 'volatilita_10', 'zmena_5_svicek']
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
    if df is None or df.empty or len(df) < 2:  # Kontrola minimálního počtu svíček pro výpočet změny
        empty_df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                       'EMA9', 'EMA21', 'EMA50', 'RSI', 'BB_upper', 'BB_middle', 'BB_lower',
                                       'MACD', 'MACD_signal', 'MACD_hist', 'volatilita_10', 'zmena_5_svicek',
                                       'je_stagnace'])
        return empty_df
    
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

        # Nastavení parametrů pro denní svíčky
        interval_1d = '1d'
        lookback_1d = 100  # Posledních 100 denních svíček
        
        # Získáme denní data
        df_1d = get_historical_data(symbol, interval_1d, lookback_1d)
        if df_1d is not None:
            df_1d = add_indicators(df_1d)
            df_1d = analyze_stagnation(df_1d)
            
            # Vypíšeme statistiky pro denní data
            print("\nStatistiky denních dat:")
            print(f"Průměrný objem: {df_1d['volume'].mean():.2f}")
            print(f"Průměrná volatilita: {df_1d['volatilita_10'].mean():.2f}")
            print(f"Počet stagnujících period: {df_1d['je_stagnace'].sum()}")
            print(f"EMA9: {df_1d['EMA9'].iloc[-1]:.2f}")
            print(f"EMA21: {df_1d['EMA21'].iloc[-1]:.2f}")
            print(f"EMA50: {df_1d['EMA50'].iloc[-1]:.2f}")
            print(f"RSI: {df_1d['RSI'].iloc[-1]:.2f}")
            
            # Uložíme denní data
            df_1d.to_csv(f'{symbol}_{interval_1d}_data.csv', index=False)
            
    except Exception as e:
        print(f"\nChyba při zpracování dat: {str(e)}") 