import requests
import re
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'fr-CH,fr;q=0.9,de;q=0.8',
}

# Test page produit pour parser les offres
url = "https://www.toppreise.ch/preisvergleich/Grafikkarten/GAINWARD-GeForce-RTX-5070-Ti-Phoenix-S-5547-NE7507T019T2-GB2031K-p809595"
print(f"Fetching: {url}")

r = requests.get(url, headers=HEADERS, timeout=15)
print(f"Status: {r.status_code}, Length: {len(r.text)}")

# Chercher les patterns de prix et vendeurs
text = r.text

# Pattern: CHF XXX inkl. Versand ... /shops/SHOP-sXXX
print("\n--- Recherche des offres ---")

# Methode 1: liens /shops/ avec prix avant
shop_links = re.findall(r'CHF\s*([\d\'\.,]+)[^<]{0,200}/shops/([\w\-]+)-s\d+', text)
print(f"Methode shops: {len(shop_links)} resultats")
for price, shop in shop_links[:10]:
    print(f"  {shop}: CHF {price}")

# Methode 2: chercher les blocs avec inkl. Versand
print("\n--- Methode inkl. Versand ---")
versand = re.findall(r'CHF\s*([\d\'\.,]+)\s*inkl\.\s*Versand[:\s]*([\d\.,]*)[^<]{0,100}', text)
print(f"Resultats: {len(versand)}")
for v in versand[:5]:
    print(f"  {v}")

# Methode 3: chercher dans la structure HTML
print("\n--- Structure HTML autour des prix ---")
soup = BeautifulSoup(text, 'html.parser')
# Chercher les elements contenant "inkl. Versand"
for elem in soup.find_all(string=re.compile(r'inkl\.\s*Versand'))[:3]:
    parent = elem.parent
    print(f"Parent: {parent.name}")
    print(f"  Text: {parent.get_text(strip=True)[:100]}")
    # Chercher le lien shop proche
    container = parent.find_parent(['div', 'tr', 'li'])
    if container:
        shop_link = container.find('a', href=re.compile(r'/shops/'))
        if shop_link:
            print(f"  Shop: {shop_link.get_text(strip=True)}")
