import requests
import re
from bs4 import BeautifulSoup

url = 'https://www.toppreise.ch/preisvergleich/Activity-Tracker-Smartwatches/GARMIN-fenix-8-Pro-AMOLED-Sapphire-Graphit-Schwarz-010-03199-11-p818374'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'fr-CH,fr;q=0.9,de;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

resp = requests.get(url, headers=headers, timeout=15)
text = resp.text
soup = BeautifulSoup(text, 'html.parser')

print(f"Longueur reponse: {len(text)} caracteres")
print("="*60)

# Verifier presence de mots cles
print("Presence mots cles:")
print(f"  'Galaxus': {'Galaxus' in text}")
print(f"  'wamo24': {'wamo24' in text}")
print(f"  '/shops/': {'/shops/' in text}")
print(f"  'inkl. Versand': {'inkl. Versand' in text}")

# Utiliser BeautifulSoup pour trouver les liens de shops
print("\nLiens vers shops:")
shop_links = soup.find_all('a', href=re.compile(r'/shops/'))
for link in shop_links[:10]:
    href = link.get('href', '')
    name = link.get_text(strip=True)
    print(f"  {name} -> {href}")

# Chercher les elements de prix
print("\nElements avec 'price' dans la classe:")
price_elements = soup.find_all(class_=re.compile(r'price'))
for elem in price_elements[:10]:
    print(f"  {elem.name}: {elem.get_text(strip=True)[:50]}")

# Chercher le prix principal
print("\nRecherche prix 998:")
if '998' in text:
    idx = text.find('998')
    print(f"  Contexte: ...{text[max(0,idx-100):idx+100]}...")
