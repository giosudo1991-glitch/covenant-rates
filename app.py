from flask import Flask, jsonify, send_file
import requests
from bs4 import BeautifulSoup
import json
import os

app = Flask(__name__)

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/rates')
def get_rates():
    rates = []
    
    # NBG Official Rate
    try:
        r = requests.get('https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json', timeout=5)
        data = r.json()
        for item in data[0]['currencies']:
            if item['code'] in ['USD', 'EUR', 'GBP', 'RUB', 'TRY', 'CHF', 'UAH']:
                rates.append({
                    'bank': 'NBG ოფიციალური',
                    'currency': item['code'],
                    'buy': round(item['rate'] * 0.99, 4),
                    'sell': round(item['rate'] * 1.01, 4),
                    'official': item['rate']
                })
    except Exception as e:
        print(f"NBG error: {e}")

    # TBC Bank
    try:
        r = requests.get('https://www.tbcbank.ge/web/ka/web-currency-calculator', timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.select('table.currency-table tr')
        for row in rows:
            cols = row.select('td')
            if len(cols) >= 3:
                currency = cols[0].text.strip()
                buy = cols[1].text.strip()
                sell = cols[2].text.strip()
                if currency in ['USD', 'EUR', 'GBP', 'RUB', 'TRY']:
                    try:
                        rates.append({
                            'bank': 'TBC Bank',
                            'currency': currency,
                            'buy': float(buy),
                            'sell': float(sell)
                        })
                    except:
                        pass
    except Exception as e:
        print(f"TBC error: {e}")

    # BOG Bank
    try:
        r = requests.get('https://bankofgeorgia.ge/en/individual/currency-exchange', timeout=5)
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.select('table tr')
        for row in rows:
            cols = row.select('td')
            if len(cols) >= 3:
                currency = cols[0].text.strip()
                buy = cols[1].text.strip()
                sell = cols[2].text.strip()
                if currency in ['USD', 'EUR', 'GBP', 'RUB', 'TRY']:
                    try:
                        rates.append({
                            'bank': 'Bank of Georgia',
                            'currency': currency,
                            'buy': float(buy),
                            'sell': float(sell)
                        })
                    except:
                        pass
    except Exception as e:
        print(f"BOG error: {e}")

    return jsonify(rates)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
