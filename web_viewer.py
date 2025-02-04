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

# Globální proměnné pro ukládání dat
data = {
    'hourly': None,
    'minute15': None,
    'weekly': None,
    'last_update': None
}

def update_data():
    """Funkce pro aktualizaci dat v samostatném vlákně"""
    while True:
        try:
            # Získání dat pro různé časové intervaly
            hourly_data = crypto_analyzer.get_historical_data('BTCUSDT', '1h', 100)
            minute15_data = crypto_analyzer.get_historical_data('BTCUSDT', '15m', 100)
            weekly_data = crypto_analyzer.get_historical_data('BTCUSDT', '1w', 100)
            
            if hourly_data is not None and minute15_data is not None and weekly_data is not None:
                # Aktualizace globálních dat
                data['hourly'] = crypto_analyzer.analyze_data(hourly_data, '24 hodin')
                data['minute15'] = crypto_analyzer.analyze_data(minute15_data, '24 hodin')
                data['weekly'] = crypto_analyzer.analyze_data(weekly_data, None)
                data['last_update'] = time.strftime('%H:%M:%S')
        except Exception as e:
            print(f"Chyba při aktualizaci dat: {str(e)}")
            
        # Počkáme 60 sekund před další aktualizací
        time.sleep(60)

@app.route('/')
def index():
    """Hlavní stránka s daty"""
    return render_template('index.html', 
                         hourly_data=data['hourly'],
                         minute15_data=data['minute15'],
                         weekly_data=data['weekly'],
                         last_update=data['last_update'])

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
    # Spustíme aktualizační vlákno
    update_thread = threading.Thread(target=update_data, daemon=True)
    update_thread.start()
    
    # Spustíme Flask aplikaci
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port) 