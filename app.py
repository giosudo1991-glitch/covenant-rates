"""
Covenant Kursi — საქართველოს ვალუტის კურსების აგრეგატორი
"""

from flask import Flask, jsonify, send_file, Response
import requests
from bs4 import BeautifulSoup
import re, time, threading, os
from datetime import datetime

app = Flask(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/html, */*',
    'Accept-Language': 'ka,en-US;q=0.9,en;q=0.8',
}

CURRENCIES = ['USD', 'EUR', 'GBP', 'RUB', 'TRY', 'CHF', 'UAH', 'AED']
CACHE_TTL = 300
cache = {'data': None, 'ts': 0}

BANK_IDS = {
    'tbc':       'TBC ბანკი',
    'bog':       'საქ. ბანკი',
    'liberty':   'Liberty ბანკი',
    'procredit': 'ProCredit',
    'credo':     'Credo ბანკი',
    'basis':     'BasisBank',
    'vtb':       'VTB ბანკი',
    'space':     'Space ბანკი',
}

EXCHANGE_IDS = {
    'rico':     'Rico',
    'valuto':   'Valuto',
    'tbcpay':   'TBC Pay',
}

def clean(s):
    try:
        return round(float(re.sub(r'[^\d.]', '', str(s))), 4)
    except:
        return None


# ══════════════════════════════════════════
#  NBG — ეროვნული ბანკი (პირდაპირი API)
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


# ══════════════════════════════════════════
#  MYRATE.GE — ყველა ბანკი და გამცვლელი
# ══════════════════════════════════════════

def fetch_myrate():
    try:
        r = requests.get('https://myrate.ge/api/v1/rates', headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    try:
        r = requests.get('https://myrate.ge/', headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        import json
        for script in soup.find_all('script'):
            text = script.get_text()
            if 'rates' in text and 'USD' in text:
                match = re.search(r'(\{.*"rates".*\})', text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(1))
                    except:
                        pass
    except Exception as e:
        print(f'myrate.ge error: {e}')
    return None


def fetch_kurs():
    """kurs.ge - ალტერნატიული წყარო"""
    try:
        r = requests.get('https://kurs.ge/api/rates', headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    try:
        r = requests.get('https://kurs.ge/', headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        results = {}
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 3:
                    bank_name = cells[0].get_text(strip=True)
                    for i, cell in enumerate(cells):
                        text = cell.get_text(strip=True).upper()
                        code = re.sub(r'[^A-Z]', '', text)
                        if code in CURRENCIES and i + 2 < len(cells):
                            b = clean(cells[i+1].get_text())
                            s = clean(cells[i+2].get_text())
                            if b and s and 0.1 < b < 100:
                                if bank_name not in results:
                                    results[bank_name] = {}
                                results[bank_name][code] = {'buy': b, 'sell': s}
        return results
    except Exception as e:
        print(f'kurs.ge error: {e}')
    return None


def fetch_rico():
    try:
        r = requests.get('https://rico.ge/', headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        rates = {}
        for row in soup.select('table tr, .rate-row, .exchange-row'):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:
                code = re.sub(r'[^A-Z]', '', cells[0].get_text(strip=True).upper())
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
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:
                code = re.sub(r'[^A-Z]', '', cells[0].get_text(strip=True).upper())
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
        soup = BeautifulSoup(r.text, 'html.parser')
        rates = {}
        for row in soup.select('table tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:
                code = re.sub(r'[^A-Z]', '', cells[0].get_text(strip=True).upper())
                if code in CURRENCIES:
                    b = clean(cells[1].get_text())
                    s = clean(cells[2].get_text())
                    if b and s and 0.5 < b < 50:
                        rates[code] = {'buy': b, 'sell': s}
        return rates
    except Exception as e:
        print(f'Lazika error: {e}')
        return {}

def fetch_mbs():
    try:
        r = requests.get('https://mbs.ge/', headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        rates = {}
        for row in soup.select('table tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:
                code = re.sub(r'[^A-Z]', '', cells[0].get_text(strip=True).upper())
                if code in CURRENCIES:
                    b = clean(cells[1].get_text())
                    s = clean(cells[2].get_text())
                    if b and s and 0.5 < b < 50:
                        rates[code] = {'buy': b, 'sell': s}
        return rates
    except Exception as e:
        print(f'MBS error: {e}')
        return {}

def fetch_kapitali():
    try:
        r = requests.get('https://www.kapitali.ge/', headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        rates = {}
        for row in soup.select('table tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 3:
                code = re.sub(r'[^A-Z]', '', cells[0].get_text(strip=True).upper())
                if code in CURRENCIES:
                    b = clean(cells[1].get_text())
                    s = clean(cells[2].get_text())
                    if b and s and 0.5 < b < 50:
                        rates[code] = {'buy': b, 'sell': s}
        return rates
    except Exception as e:
        print(f'Kapitali error: {e}')
        return {}


# ══════════════════════════════════════════
#  FETCH ALL
# ══════════════════════════════════════════

SOURCES_DIRECT = [
    ('nbg',      'ეროვნული ბანკი',  'official', fetch_nbg),
    ('rico',     'Rico',              'exchange', fetch_rico),
    ('valuto',   'Valuto',            'exchange', fetch_valuto),
    ('lazika',   'ლაზიკა',           'exchange', fetch_lazika),
    ('mbs',      'MBS',               'exchange', fetch_mbs),
    ('kapitali', 'კაპიტალი',        'exchange', fetch_kapitali),
]

BANK_SOURCES = [
    ('tbc',       'TBC ბანკი',        'bank'),
    ('bog',       'საქ. ბანკი',       'bank'),
    ('liberty',   'Liberty ბანკი',    'bank'),
    ('procredit', 'ProCredit',         'bank'),
    ('credo',     'Credo ბანკი',      'bank'),
    ('basis',     'BasisBank',         'bank'),
    ('vtb',       'VTB ბანკი',        'bank'),
    ('space',     'Space ბანკი',      'bank'),
    ('tbcpay',    'TBC Pay',           'exchange'),
]

def fetch_all():
    print(f'\n[{datetime.now().strftime("%H:%M:%S")}] კურსი იტვირთება...')
    result = {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'sources': {}
    }

    # პირდაპირი წყაროები
    for sid, name, category, fn in SOURCES_DIRECT:
        try:
            rates = fn()
            result['sources'][sid] = {
                'name': name, 'category': category,
                'rates': rates, 'ok': len(rates) > 0
            }
            print(f'  {name}: {"✓" if rates else "✗"} {len(rates)} ვალუტა')
        except Exception as e:
            result['sources'][sid] = {'name': name, 'category': category, 'rates': {}, 'ok': False}
            print(f'  {name}: ✗ {e}')

    # ბანკები myrate.ge-დან
    print('  myrate.ge-დან ვტვირთავ...')
    myrate_data = fetch_myrate()

    if myrate_data:
        print('  ✓ myrate.ge მუშაობს')
        # myrate.ge-ს სტრუქტურა: {bank_id: {currency: {buy, sell}}}
        for sid, name, category in BANK_SOURCES:
            bank_data = myrate_data.get(sid, myrate_data.get(name, {}))
            rates = {}
            if isinstance(bank_data, dict):
                for cur, vals in bank_data.items():
                    code = cur.upper()
                    if code in CURRENCIES and isinstance(vals, dict):
                        b = clean(vals.get('buy', vals.get('rate')))
                        s = clean(vals.get('sell'))
                        if b and s:
                            rates[code] = {'buy': b, 'sell': s}
            result['sources'][sid] = {
                'name': name, 'category': category,
                'rates': rates, 'ok': len(rates) > 0
            }
            print(f'  {name}: {"✓" if rates else "✗"} {len(rates)} ვალუტა')
    else:
        print('  ✗ myrate.ge ვერ ჩაიტვირთა, kurs.ge ვცდი...')
        kurs_data = fetch_kurs()

        for sid, name, category in BANK_SOURCES:
            rates = {}
            if kurs_data and isinstance(kurs_data, dict):
                for key, vals in kurs_data.items():
                    if name.lower() in key.lower() or sid.lower() in key.lower():
                        rates = vals if isinstance(vals, dict) else {}
                        break
            result['sources'][sid] = {
                'name': name, 'category': category,
                'rates': rates, 'ok': len(rates) > 0
            }
            print(f'  {name}: {"✓" if rates else "✗"} {len(rates)} ვალუტა')

    print(f'  → დასრულდა')
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
    return send_file(os.path.join(os.path.dirname(__file__), 'index.html'))

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
        "name": "Covenant Kursi",
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
const CACHE = 'kursi-v2';
const ASSETS = ['/'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
});
self.addEventListener('fetch', e => {
  if (e.request.url.includes('/api/')) return;
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
"""
    return Response(sw, mimetype='application/javascript')


if __name__ == '__main__':
    print('=' * 50)
    print('🇬🇪  Covenant Kursi — ვალუტის კურსი')
    print('=' * 50)
    get_cached()
    t = threading.Thread(target=background_refresh, daemon=True)
    t.start()
    print('\n✅ სერვერი გაშვებულია!')
    print('🌐 http://localhost:5000')
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
