# Importujeme potřebné knihovny
from flask import Flask, render_template_string, send_file, jsonify, Response, request, render_template
import pandas as pd
import json
from datetime import datetime
import subprocess
import threading
import time
import os
import crypto_analyzer
import logging

# Nastavení logování
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

def update_data():
    """Funkce pro pravidelnou aktualizaci dat"""
    while True:
        try:
            logging.info("Spouštím aktualizaci dat...")
            subprocess.run(['python3', 'crypto_analyzer.py'], check=True)
            time.sleep(60)  # Aktualizace každou minutu
        except Exception as e:
            logging.error(f"Chyba při aktualizaci dat: {e}")
            time.sleep(10)  # Při chybě počkáme 10 sekund před dalším pokusem

# Spustíme aktualizační vlákno
update_thread = threading.Thread(target=update_data, daemon=True)
update_thread.start()

@app.route('/')
def index():
    try:
        # Získáme seznam dostupných párů
        logging.info("Získávám seznam dostupných párů...")
        pairs = crypto_analyzer.get_usdt_pairs()
        
        # Získáme aktuálně vybraný symbol
        selected_symbol = request.args.get('symbol', 'BTCUSDT')
        logging.info(f"Vybraný symbol: {selected_symbol}")
        
        # Nastavíme vybraný symbol do prostředí
        os.environ['SELECTED_SYMBOL'] = selected_symbol
        
        try:
            # Spustíme analýzu pro vybraný symbol
            logging.info(f"Spouštím analýzu pro {selected_symbol}...")
            result = subprocess.run(['python3', 'crypto_analyzer.py'], 
                                  capture_output=True, text=True, check=True)
            output = result.stdout
            logging.info("Analýza dokončena")
        except subprocess.CalledProcessError as e:
            logging.error(f"Chyba při analýze: {e}\nOutput: {e.output}")
            output = f"Chyba při aktualizaci dat: {str(e)}\n{e.output}"

        # Načteme data ze souborů s ošetřením chyb
        df = pd.DataFrame()
        df_15m = pd.DataFrame()
        df_1d = pd.DataFrame()

        try:
            logging.info("Načítám hodinová data...")
            df = pd.read_csv(f'{selected_symbol}_1h_data.csv')
        except FileNotFoundError:
            logging.warning(f"Hodinová data pro {selected_symbol} nejsou k dispozici")
            df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                     'EMA9', 'EMA21', 'EMA50', 'RSI', 'BB_upper', 'BB_middle', 'BB_lower',
                                     'MACD', 'MACD_signal', 'MACD_hist', 'volatilita_10', 'zmena_5_svicek',
                                     'je_stagnace'])

        try:
            logging.info("Načítám 15minutová data...")
            df_15m = pd.read_csv(f'{selected_symbol}_15m_data.csv')
        except FileNotFoundError:
            logging.warning(f"15minutová data pro {selected_symbol} nejsou k dispozici")
            df_15m = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                         'EMA9', 'EMA21', 'EMA50', 'RSI', 'BB_upper', 'BB_middle', 'BB_lower',
                                         'MACD', 'MACD_signal', 'MACD_hist', 'volatilita_10', 'zmena_5_svicek',
                                         'je_stagnace'])

        try:
            logging.info("Načítám denní data...")
            df_1d = pd.read_csv(f'{selected_symbol}_1d_data.csv')
        except FileNotFoundError:
            logging.warning(f"Denní data pro {selected_symbol} nejsou k dispozici")
            df_1d = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                        'EMA9', 'EMA21', 'EMA50', 'RSI', 'BB_upper', 'BB_middle', 'BB_lower',
                                        'MACD', 'MACD_signal', 'MACD_hist', 'volatilita_10', 'zmena_5_svicek',
                                        'je_stagnace'])

        logging.info("Renderuji šablonu...")
        return render_template('index.html',
                             pairs=pairs,
                             selected_symbol=selected_symbol,
                             df=df.to_dict('records'),
                             df_15m=df_15m.to_dict('records'),
                             df_1d=df_1d.to_dict('records'))
    except Exception as e:
        logging.error(f"Neočekávaná chyba: {e}")
        return f"Došlo k chybě: {str(e)}"

@app.route('/download/csv')
def download_csv():
    try:
        selected_symbol = request.args.get('symbol', 'BTCUSDT')
        df = pd.read_csv(f'{selected_symbol}_1h_data.csv')
        csv_data = df.to_csv(index=False)
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Type': 'text/csv; charset=utf-8'}
        )
    except Exception as e:
        return f"Chyba při stahování CSV: {str(e)}"

@app.route('/download/json')
def download_json():
    try:
        selected_symbol = request.args.get('symbol', 'BTCUSDT')
        df = pd.read_csv(f'{selected_symbol}_1h_data.csv')
        json_data = df.to_json(orient='records', date_format='iso')
        return Response(
            json_data,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment;filename={selected_symbol}_1h_data.json'}
        )
    except Exception as e:
        return f"Chyba při stahování JSON: {str(e)}"

@app.route('/download/csv15m')
def download_csv_15m():
    try:
        selected_symbol = request.args.get('symbol', 'BTCUSDT')
        df = pd.read_csv(f'{selected_symbol}_15m_data.csv')
        csv_data = df.to_csv(index=False)
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Type': 'text/csv; charset=utf-8'}
        )
    except Exception as e:
        return f"Chyba při stahování CSV: {str(e)}"

@app.route('/download/json15m')
def download_json_15m():
    try:
        selected_symbol = request.args.get('symbol', 'BTCUSDT')
        df = pd.read_csv(f'{selected_symbol}_15m_data.csv')
        json_data = df.to_json(orient='records', date_format='iso')
        return Response(
            json_data,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment;filename={selected_symbol}_15m_data.json'}
        )
    except Exception as e:
        return f"Chyba při stahování JSON: {str(e)}"

@app.route('/download/csv1d')
def download_csv_1d():
    try:
        selected_symbol = request.args.get('symbol', 'BTCUSDT')
        df = pd.read_csv(f'{selected_symbol}_1d_data.csv')
        csv_data = df.to_csv(index=False)
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Type': 'text/csv; charset=utf-8'}
        )
    except Exception as e:
        return f"Chyba při stahování CSV: {str(e)}"

@app.route('/download/json1d')
def download_json_1d():
    try:
        selected_symbol = request.args.get('symbol', 'BTCUSDT')
        df = pd.read_csv(f'{selected_symbol}_1d_data.csv')
        json_data = df.to_json(orient='records', date_format='iso')
        return Response(
            json_data,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment;filename={selected_symbol}_1d_data.json'}
        )
    except Exception as e:
        return f"Chyba při stahování JSON: {str(e)}"

@app.route('/refresh_data')
def refresh_data():
    try:
        selected_symbol = request.args.get('symbol', 'BTCUSDT')
        os.environ['SELECTED_SYMBOL'] = selected_symbol
        # Spustíme crypto_analyzer.py pro aktualizaci dat
        subprocess.run(['python3', 'crypto_analyzer.py'], check=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, debug=True) 