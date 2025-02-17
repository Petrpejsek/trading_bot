# Importujeme potřebné knihovny
from flask import Flask, render_template_string, send_file, jsonify, Response, request, render_template
import pandas as pd
import json
from datetime import datetime
import subprocess
import os
import crypto_analyzer
import logging

# Nastavení logování
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

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
        
        # Spustíme analýzu pro vybraný symbol
        logging.info(f"Spouštím analýzu pro {selected_symbol}...")
        subprocess.run(['python3', 'crypto_analyzer.py'], check=True)
        
        # Načteme data ze souborů
        df = pd.read_csv(f'{selected_symbol}_1h_data.csv')
        df_15m = pd.read_csv(f'{selected_symbol}_15m_data.csv')
        df_1d = pd.read_csv(f'{selected_symbol}_1d_data.csv')
        
        return render_template('index.html',
                             pairs=pairs,
                             selected_symbol=selected_symbol,
                             df=df.to_dict('records'),
                             df_15m=df_15m.to_dict('records'),
                             df_1d=df_1d.to_dict('records'))
    except Exception as e:
        logging.error(f"Chyba: {str(e)}")
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
            headers={
                'Content-Type': 'text/csv; charset=utf-8',
                'Content-Disposition': f'inline; filename={selected_symbol}_1h_data.csv'
            }
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
            headers={
                'Content-Type': 'text/csv; charset=utf-8',
                'Content-Disposition': f'inline; filename={selected_symbol}_15m_data.csv'
            }
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
            headers={
                'Content-Type': 'text/csv; charset=utf-8',
                'Content-Disposition': f'inline; filename={selected_symbol}_1d_data.csv'
            }
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
        subprocess.run(['python3', 'crypto_analyzer.py'], check=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 