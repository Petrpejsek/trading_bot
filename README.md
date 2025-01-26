# Trading Bot

Tento projekt je trading bot pro sledování a analýzu kryptoměnových trhů. Bot sbírá data z Binance API a poskytuje statistiky o obchodování.

## Funkce

- Sběr historických dat z Binance API
- Analýza volatility a objemu obchodů
- Webové rozhraní pro zobrazení statistik
- Podpora různých časových rámců (15m, 1h, 1w)

## Instalace

1. Naklonujte repozitář:
```bash
git clone [URL repozitáře]
```

2. Nainstalujte potřebné závislosti:
```bash
pip install -r requirements.txt
```

3. Vytvořte soubor `config.py` s vašimi API klíči:
```python
API_KEY = 'váš_binance_api_klíč'
API_SECRET = 'váš_binance_api_secret'
```

## Použití

1. Spusťte analyzátor dat:
```bash
python crypto_analyzer.py
```

2. Spusťte webové rozhraní:
```bash
python web_viewer.py
```

Webové rozhraní bude dostupné na `http://localhost:8081`

## Struktura projektu

- `crypto_analyzer.py` - Hlavní skript pro analýzu dat
- `web_viewer.py` - Flask aplikace pro webové rozhraní
- `config.py` - Konfigurační soubor s API klíči
- `templates/` - Adresář s HTML šablonami pro webové rozhraní 