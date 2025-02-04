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

app = Flask(__name__)

def update_data():
    """Funkce pro pravidelnou aktualizaci dat"""
    while True:
        try:
            # Místo spuštění jako subprocess voláme funkci přímo
            crypto_analyzer.main()
            time.sleep(60)  # Aktualizace každou minutu
        except Exception as e:
            print(f"Chyba při aktualizaci dat: {e}")

# Spustíme aktualizační vlákno
update_thread = threading.Thread(target=update_data, daemon=True)
update_thread.start()

@app.route('/')
def index():
    # Získáme seznam dostupných párů
    pairs = crypto_analyzer.get_usdt_pairs()
    
    # Získáme aktuálně vybraný symbol
    selected_symbol = request.args.get('symbol', 'BTCUSDT')
    
    # Nastavíme vybraný symbol do prostředí
    os.environ['SELECTED_SYMBOL'] = selected_symbol
    
    try:
        # Místo spuštění jako subprocess voláme funkci přímo
        crypto_analyzer.main()
    except Exception as e:
        output = f"Chyba při aktualizaci dat: {str(e)}"

    try:
        # Načteme data ze souborů
        df = pd.read_csv(f'{selected_symbol}_1h_data.csv')
        df_15m = pd.read_csv(f'{selected_symbol}_15m_data.csv')
        df_1w = pd.read_csv(f'{selected_symbol}_1w_data.csv')
    except Exception as e:
        # Pokud soubory neexistují, vytvoříme prázdné DataFrames
        columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                  'EMA9', 'EMA21', 'EMA50', 'RSI', 'BB_upper', 'BB_middle', 'BB_lower',
                  'MACD', 'MACD_signal', 'MACD_hist', 'volatilita_10', 'je_stagnace']
        df = pd.DataFrame(columns=columns)
        df_15m = pd.DataFrame(columns=columns)
        df_1w = pd.DataFrame(columns=columns)

    return render_template('index.html',
                         pairs=pairs,
                         selected_symbol=selected_symbol,
                         df=df.to_dict('records'),
                         df_15m=df_15m.to_dict('records'),
                         df_1w=df_1w.to_dict('records'))

@app.route('/download/csv')
def download_csv():
    try:
        selected_symbol = request.args.get('symbol', 'BTCUSDT')
        return send_file(f'{selected_symbol}_1h_data.csv',
                        mimetype='text/csv',
                        as_attachment=True,
                        download_name=f'{selected_symbol}_1h_data.csv')
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
        return send_file(f'{selected_symbol}_15m_data.csv',
                        mimetype='text/csv',
                        as_attachment=True,
                        download_name=f'{selected_symbol}_15m_data.csv')
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

@app.route('/download/csv1w')
def download_csv_1w():
    try:
        selected_symbol = request.args.get('symbol', 'BTCUSDT')
        return send_file(f'{selected_symbol}_1w_data.csv',
                        mimetype='text/csv',
                        as_attachment=True,
                        download_name=f'{selected_symbol}_1w_data.csv')
    except Exception as e:
        return f"Chyba při stahování CSV: {str(e)}"

@app.route('/download/json1w')
def download_json_1w():
    try:
        selected_symbol = request.args.get('symbol', 'BTCUSDT')
        df = pd.read_csv(f'{selected_symbol}_1w_data.csv')
        json_data = df.to_json(orient='records', date_format='iso')
        return Response(
            json_data,
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment;filename={selected_symbol}_1w_data.json'}
        )
    except Exception as e:
        return f"Chyba při stahování JSON: {str(e)}"

@app.route('/refresh_data')
def refresh_data():
    try:
        selected_symbol = request.args.get('symbol', 'BTCUSDT')
        os.environ['SELECTED_SYMBOL'] = selected_symbol
        # Spustíme crypto_analyzer.py pro aktualizaci dat
        crypto_analyzer.main()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False) 