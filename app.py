"""
kursi.ge — საქართველოს ვალუტის კურსების აგრეგატორი
"""

from flask import Flask, jsonify, send_from_directory
import requests
from bs4 import BeautifulSoup
import json, re, time, threading, os
from datetime import datetime

app = Flask(__name__, static_folder='.')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ka,en-US;q=0.9,en;q=0.8',
}

CURRENCIES = ['USD', 'EUR', 'GBP', 'RUB', 'TRY', 'CHF', 'UAH', 'AED']
CACHE_TTL = 300  # 5 წუთი
cache = {'data': None, 'ts': 0}

# ══════════════════════════════════════════
#  HELPER
# ══════════════════════════════════════════
def clean(s):
    try:
        return round(float(re.sub(r'[^\d.]', '', str(s))), 4)
    except:
        return None

def parse_table(html, cur_col=0, buy_col=1, sell_col=2, selector='table tr'):
    soup = BeautifulSoup(html, 'html.parser')
    rates = {}
    for row in soup.select(selector):
        cells = row.find_all(['td','th'])
        if len(cells) > max(cur_col, buy_col, sell_col):
            code = cells[cur_col].get_text(strip=True).upper()
            # strip flag emoji or extra chars
            code = re.sub(r'[^A-Z]', '', code)
            if code in CURRENCIES:
                b = clean(cells[buy_col].get_text())
                s = clean(cells[sell_col].get_text())
                if b and s:
                    rates[code] = {'buy': b, 'sell': s}
    return rates

# ══════════════════════════════════════════
#  BANKS
# ══════════════════════════════════════════

def fetch_nbg():
    try:
        r = requests.get(
            'https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/ka/json',
            headers=HEADERS, timeout=10)
        data = r.json()
        rates = {}
        for item in data[0]['currencies']:
            code = item['code']
            if code in CURRENCIES:
                rate = round(item['rate'] / item['quantity'], 4)
                rates[code] = {'buy': rate, 'sell': rate, 'official': True}
        return rates
    except Exception as e:
        print(f'NBG error: {e}')
        return {}

def fetch_tbc():
    try:
        r = requests.get('https://api.tbcbank.ge/v1/currency/exchange-rate',
                         headers=HEADERS, timeout=10)
        data = r.json()
        rates = {}
        for item in data.get('currencies', []):
            code = item.get('currency','').upper()
            if code in CURRENCIES:
                b = clean(item.get('buy'))
                s = clean(item.get('sell'))
                if b and s:
                    rates[code] = {'buy': b, 'sell': s}
        if rates: return rates
    except: pass
    try:
        r = requests.get('https://www.tbcbank.ge/web/en/web/guest/exchange-rates',
                         headers=HEADERS, timeout=10)
        return parse_table(r.text)
    except Exception as e:
        print(f'TBC error: {e}')
        return {}

def fetch_bog():
    try:
        r = requests.get('https://bankofgeorgia.ge/mob/en/ExchangeRates',
                         headers=HEADERS, timeout=10)
        data = r.json()
        rates = {}
        for item in data.get('Data', []):
            code = item.get('RateName','').upper()
            if code in CURRENCIES:
                b = clean(item.get('BuyRate'))
                s = clean(item.get('SellRate'))
                if b and s:
                    rates[code] = {'buy': b, 'sell': s}
        if rates: return rates
    except: pass
    try:
        r = requests.get('https://bankofgeorgia.ge/en/personal/exchange-rates',
                         headers=HEADERS, timeout=10)
        return parse_table(r.text)
    except Exception as e:
        print(f'BOG error: {e}')
        return {}

def fetch_liberty():
    try:
        r = requests.get('https://libertybank.ge/en/individuals/exchange-rates/',
                         headers=HEADERS, timeout=10)
        return parse_table(r.text)
    except Exception as e:
        print(f'Liberty error: {e}')
        return {}

def fetch_procredit():
    try:
        r = requests.get('https://www.procreditbank.ge/en/exchange-rates',
                         headers=HEADERS, timeout=10)
        return parse_table(r.text)
    except Exception as e:
        print(f'ProCredit error: {e}')
        return {}

def fetch_credo():
    try:
        r = requests.get('https://credobank.ge/en/exchange-rates',
                         headers=HEADERS, timeout=10)
        return parse_table(r.text)
    except Exception as e:
        print(f'Credo error: {e}')
        return {}

def fetch_basis():
    try:
        r = requests.get('https://basisbank.ge/en/exchange-rates',
                         headers=HEADERS, timeout=10)
        return parse_table(r.text)
    except Exception as e:
        print(f'BasisBank error: {e}')
        return {}

def fetch_vtb():
    try:
        r = requests.get('https://vtb.com.ge/en/individuals/exchange-rates/',
                         headers=HEADERS, timeout=10)
        return parse_table(r.text)
    except Exception as e:
        print(f'VTB error: {e}')
        return {}

def fetch_space():
    try:
        r = requests.get('https://www.spacebank.ge/en/exchange-rate',
                         headers=HEADERS, timeout=10)
        return parse_table(r.text)
    except Exception as e:
        print(f'Space error: {e}')
        return {}

def fetch_tbcpay():
    try:
        r = requests.get('https://tbcpay.ge/exchange-rates',
                         headers=HEADERS, timeout=10)
        return parse_table(r.text)
    except Exception as e:
        print(f'TBCPay error: {e}')
        return {}

# ══════════════════════════════════════════
#  CURRENCY EXCHANGES (გამცვლელები)
# ══════════════════════════════════════════

def fetch_rico():
    try:
        r = requests.get('https://rico.ge/', headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        rates = {}
        for row in soup.select('table tr, .rate-row, .exchange-row, tr'):
            cells = row.find_all(['td','th'])
            if len(cells) >= 3:
                code = re.sub(r'[^A-Z]','', cells[0].get_text(strip=True).upper())
                if code in CURRENCIES:
                    b = clean(cells[1].get_text())
                    s = clean(cells[2].get_text())
                    if b and s and 0.5 < b < 50:
                        rates[code] = {'buy': b, 'sell': s}
        return rates
    except Exception as e:
        print(f'Rico error: {e}')
        return {}

def fetch_valuto():
    try:
        r = requests.get('https://valuto.ge/', headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        rates = {}
        for row in soup.select('table tr, .currency-row'):
            cells = row.find_all(['td','th'])
            if len(cells) >= 3:
                code = re.sub(r'[^A-Z]','', cells[0].get_text(strip=True).upper())
                if code in CURRENCIES:
                    b = clean(cells[1].get_text())
                    s = clean(cells[2].get_text())
                    if b and s and 0.5 < b < 50:
                        rates[code] = {'buy': b, 'sell': s}
        return rates
    except Exception as e:
        print(f'Valuto error: {e}')
        return {}

def fetch_lazika():
    try:
        r = requests.get('https://lazika.ge/', headers=HEADERS, timeout=10)
        return parse_table(r.text)
    except Exception as e:
        print(f'Lazika error: {e}')
        return {}

def fetch_kapitali():
    try:
        r = requests.get('https://www.kapitali.ge/', headers=HEADERS, timeout=10)
        return parse_table(r.text)
    except Exception as e:
        print(f'Kapitali error: {e}')
        return {}

def fetch_mbs():
    try:
        r = requests.get('https://mbs.ge/', headers=HEADERS, timeout=10)
        return parse_table(r.text)
    except Exception as e:
        print(f'MBS error: {e}')
        return {}

# ══════════════════════════════════════════
#  FETCH ALL
# ══════════════════════════════════════════

SOURCES = [
    # id, ქართული სახელი, კატეგორია, ფუნქცია
    ('nbg',       'ეროვნული ბანკი',    'official',  fetch_nbg),
    ('tbc',       'TBC ბანკი',          'bank',      fetch_tbc),
    ('bog',       'საქ. ბანკი',         'bank',      fetch_bog),
    ('liberty',   'Liberty ბანკი',      'bank',      fetch_liberty),
    ('procredit', 'ProCredit',           'bank',      fetch_procredit),
    ('credo',     'Credo ბანკი',        'bank',      fetch_credo),
    ('basis',     'BasisBank',           'bank',      fetch_basis),
    ('vtb',       'VTB ბანკი',          'bank',      fetch_vtb),
    ('space',     'Space ბანკი',        'bank',      fetch_space),
    ('tbcpay',    'TBC Pay',             'exchange',  fetch_tbcpay),
    ('rico',      'Rico',                'exchange',  fetch_rico),
    ('valuto',    'Valuto',              'exchange',  fetch_valuto),
    ('lazika',    'ლაზიკა',             'exchange',  fetch_lazika),
    ('kapitali',  'კაპიტალი',          'exchange',  fetch_kapitali),
    ('mbs',       'MBS',                 'exchange',  fetch_mbs),
]

def fetch_all():
    print(f'\n[{datetime.now().strftime("%H:%M:%S")}] კურსი იტვირთება...')
    result = {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'sources': {}
    }
    for sid, name, category, fn in SOURCES:
        try:
            rates = fn()
            result['sources'][sid] = {
                'name': name,
                'category': category,
                'rates': rates,
                'ok': len(rates) > 0
            }
            status = f'✓ {len(rates)} ვალუტა' if rates else '✗ ვერ ჩაიტვირთა'
            print(f'  {name}: {status}')
        except Exception as e:
            result['sources'][sid] = {'name': name, 'category': category, 'rates': {}, 'ok': False}
            print(f'  {name}: ✗ {e}')
    print(f'  → დასრულდა {datetime.now().strftime("%H:%M:%S")}')
    return result

def get_cached():
    now = time.time()
    if cache['data'] is None or (now - cache['ts']) > CACHE_TTL:
        cache['data'] = fetch_all()
        cache['ts'] = now
    return cache['data']

def background_refresh():
    while True:
        time.sleep(CACHE_TTL)
        cache['data'] = fetch_all()
        cache['ts'] = time.time()

# ══════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/rates')
def api_rates():
    return jsonify(get_cached())

@app.route('/api/refresh')
def api_refresh():
    cache['ts'] = 0
    return jsonify(get_cached())

@app.route('/manifest.json')
def manifest():
    return jsonify({
        "name": "კურსი.ge",
        "short_name": "კურსი",
        "description": "საქართველოს ბანკების ვალუტის კურსი",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0d1117",
        "theme_color": "#c9a84c",
        "lang": "ka",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    })

@app.route('/sw.js')
def service_worker():
    sw = """
const CACHE = 'kursi-v1';
const ASSETS = ['/', '/static/index.html'];
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS))));
self.addEventListener('fetch', e => {
  if (e.request.url.includes('/api/')) return;
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
"""
    from flask import Response
    return Response(sw, mimetype='application/javascript')

if __name__ == '__main__':
    print('='*50)
    print('🇬🇪  კურსი.ge — ვალუტის კურსი')
    print('='*50)
    get_cached()
    t = threading.Thread(target=background_refresh, daemon=True)
    t.start()
    print('\n✅ სერვერი გაშვებულია!')
    print('🌐 http://localhost:5000')
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
