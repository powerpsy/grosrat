#!/usr/bin/env python3
"""
GROSRAT - Price Tracker pour Toppreise.ch
Suivi automatique de prix avec alertes Discord
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime
import json
import os
import sys
import threading

# Pour la detection de touche
try:
    import msvcrt  # Windows
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False
    import select  # Unix

# =============================================================================
# CONFIGURATION
# =============================================================================

CHECK_INTERVAL_HOURS = 6
CONFIG_FILE = "tracked_products.json"
VERSION = "2.1"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'fr-CH,fr;q=0.9,de;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}


# =============================================================================
# UTILITAIRES
# =============================================================================

def wait_with_keycheck(seconds):
    """
    Attend pendant 'seconds' secondes, mais verifie regulierement 
    si la touche M est pressee pour retourner au menu.
    Retourne True si M est presse, False sinon.
    """
    end_time = time.time() + seconds
    
    while time.time() < end_time:
        # Verifier si une touche est pressee
        if HAS_MSVCRT:
            # Windows
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                if key == 'm':
                    return True
        else:
            # Unix - utilise select pour verifier stdin
            if select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1).lower()
                if key == 'm':
                    return True
        
        # Petite pause pour ne pas surcharger le CPU
        time.sleep(0.5)
    
    return False


# =============================================================================
# COULEURS ANSI
# =============================================================================

class C:
    """Codes couleurs ANSI"""
    RST = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    BLK = '\033[30m'
    RED = '\033[31m'
    GRN = '\033[32m'
    YLW = '\033[33m'
    BLU = '\033[34m'
    MAG = '\033[35m'
    CYN = '\033[36m'
    WHT = '\033[37m'
    
    BRED = '\033[91m'
    BGRN = '\033[92m'
    BYLW = '\033[93m'
    BBLU = '\033[94m'
    BMAG = '\033[95m'
    BCYN = '\033[96m'
    BWHT = '\033[97m'

# =============================================================================
# INTERFACE TERMINAL
# =============================================================================

class UI:
    """Gestion de l'interface terminal"""
    
    W = 78  # Largeur
    
    @staticmethod
    def clear():
        os.system('cls' if os.name == 'nt' else 'clear')
    
    @staticmethod
    def title(t):
        if os.name == 'nt':
            os.system(f'title {t}')
    
    @classmethod
    def line(cls, char='-'):
        return char * cls.W
    
    @classmethod
    def box_top(cls):
        return '+' + '-' * (cls.W - 2) + '+'
    
    @classmethod
    def box_bot(cls):
        return '+' + '-' * (cls.W - 2) + '+'
    
    @classmethod
    def box_mid(cls):
        return '+' + '-' * (cls.W - 2) + '+'
    
    @classmethod
    def box_row(cls, text, align='left', color=''):
        inner = cls.W - 4
        if len(text) > inner:
            text = text[:inner-3] + '...'
        
        if align == 'center':
            content = text.center(inner)
        elif align == 'right':
            content = text.rjust(inner)
        else:
            content = text.ljust(inner)
        
        rst = C.RST if color else ''
        return f"| {color}{content}{rst} |"
    
    @classmethod
    def header(cls):
        cls.clear()
        cls.title("GROSRAT - Price Tracker")
        
        print(C.CYN + cls.box_top() + C.RST)
        print(C.CYN + cls.box_row("") + C.RST)
        print(C.CYN + cls.box_row(f"GROSRAT v{VERSION} - Price Tracker", 'center', C.BWHT + C.BOLD) + C.RST)
        print(C.CYN + cls.box_row("Suivi de prix Toppreise.ch avec alertes Discord", 'center', C.WHT) + C.RST)
        print(C.CYN + cls.box_row("") + C.RST)
        print(C.CYN + cls.box_bot() + C.RST)
    
    @classmethod
    def section(cls, title, color=C.YLW):
        print()
        print(color + cls.box_top() + C.RST)
        print(color + cls.box_row(title.upper(), 'center', C.BOLD) + C.RST)
        print(color + cls.box_bot() + C.RST)
    
    @classmethod
    def info(cls, label, value, lcolor=C.CYN, vcolor=C.WHT):
        print(f"  {lcolor}{label}:{C.RST} {vcolor}{value}{C.RST}")
    
    @classmethod
    def ok(cls, msg):
        print(f"  {C.BGRN}[OK]{C.RST} {msg}")
    
    @classmethod
    def err(cls, msg):
        print(f"  {C.BRED}[ERREUR]{C.RST} {msg}")
    
    @classmethod
    def warn(cls, msg):
        print(f"  {C.BYLW}[!]{C.RST} {msg}")
    
    @classmethod
    def status(cls, msg):
        print(f"  {C.BBLU}[*]{C.RST} {msg}")
    
    @classmethod
    def prompt(cls, msg, color=C.BGRN):
        print()
        return input(f"  {color}>{C.RST} {msg}: ").strip()
    
    @classmethod
    def confirm(cls, msg):
        r = cls.prompt(f"{msg} (o/n)").lower()
        return r in ['o', 'oui', 'y', 'yes']
    
    @classmethod
    def table(cls, headers, rows, widths=None):
        """Affiche un tableau ASCII"""
        if not widths:
            widths = []
            for i, h in enumerate(headers):
                mx = len(h)
                for row in rows:
                    if i < len(row):
                        mx = max(mx, len(str(row[i])))
                widths.append(min(mx + 2, 35))
        
        # Ligne superieure
        print()
        print(C.CYN + '+' + '+'.join(['-' * w for w in widths]) + '+' + C.RST)
        
        # En-tete
        hline = C.CYN + '|' + C.RST
        for i, h in enumerate(headers):
            hline += C.BOLD + C.WHT + h.center(widths[i]) + C.RST + C.CYN + '|' + C.RST
        print(hline)
        
        # Separateur
        print(C.CYN + '+' + '+'.join(['=' * w for w in widths]) + '+' + C.RST)
        
        # Lignes de donnees
        for idx, row in enumerate(rows):
            rcolor = C.BGRN if idx == 0 else C.WHT
            rline = C.CYN + '|' + C.RST
            for i, cell in enumerate(row):
                cell_str = str(cell)
                if len(cell_str) > widths[i] - 2:
                    cell_str = cell_str[:widths[i]-5] + '...'
                rline += rcolor + cell_str.center(widths[i]) + C.RST + C.CYN + '|' + C.RST
            print(rline)
        
        # Ligne inferieure
        print(C.CYN + '+' + '+'.join(['-' * w for w in widths]) + '+' + C.RST)
    
    @classmethod
    def product_card(cls, product):
        """Affiche les details d'un produit"""
        print()
        print(C.BCYN + cls.box_top() + C.RST)
        print(C.BCYN + cls.box_row("DETAILS DU PRODUIT", 'center', C.BOLD + C.WHT) + C.RST)
        print(C.BCYN + cls.box_mid() + C.RST)
        print(C.BCYN + cls.box_row("") + C.RST)
        print(C.BCYN + cls.box_row(f"Modele    : {product.get('title', 'N/A')}", color=C.WHT) + C.RST)
        print(C.BCYN + cls.box_row(f"Reference : {product.get('reference', 'N/A')}", color=C.YLW) + C.RST)
        print(C.BCYN + cls.box_row("") + C.RST)
        
        if product.get('best_price'):
            price_str = f">>> MEILLEUR PRIX: CHF {product['best_price']:.2f} <<<"
            print(C.BCYN + cls.box_row(price_str, 'center', C.BGRN + C.BOLD) + C.RST)
        
        print(C.BCYN + cls.box_row("") + C.RST)
        print(C.BCYN + cls.box_bot() + C.RST)
        
        # Tableau des offres
        if product.get('offers'):
            headers = ['Rang', 'Vendeur', 'Prix']
            rows = []
            for i, offer in enumerate(product['offers'], 1):
                rows.append([f"#{i}", offer['shop'], f"CHF {offer['price']:.2f}"])
            
            cls.table(headers, rows, [8, 40, 18])
            print(f"  {C.DIM}Total: {product.get('total_offers', len(rows))} offres{C.RST}")
    
    @classmethod
    def offers_box(cls, offers):
        """Affiche le cadre des meilleures offres"""
        print()
        print(C.CYN + cls.box_top() + C.RST)
        print(C.CYN + cls.box_row("MEILLEURES OFFRES", 'center', C.BOLD) + C.RST)
        print(C.CYN + cls.box_mid() + C.RST)
        
        if offers:
            for i, offer in enumerate(offers[:5], 1):
                shop = offer['shop']
                if len(shop) > 35:
                    shop = shop[:32] + '...'
                price_str = f"CHF {offer['price']:.2f}"
                line = f"#{i}  {shop:<38} {price_str:>12}"
                color = C.BGRN if i == 1 else C.WHT
                print(C.CYN + cls.box_row(line, color=color) + C.RST)
        else:
            print(C.CYN + cls.box_row("Aucune offre disponible", color=C.DIM) + C.RST)
        
        print(C.CYN + cls.box_bot() + C.RST)
    
    @classmethod
    def tracking_box(cls, product, threshold, check_num, price=None, next_check=None):
        """Affiche le statut du suivi"""
        print()
        print(C.YLW + cls.box_top() + C.RST)
        print(C.YLW + cls.box_row("SUIVI EN COURS", 'center', C.BOLD) + C.RST)
        print(C.YLW + cls.box_mid() + C.RST)
        
        title = product.get('title', 'N/A')
        if len(title) > 55:
            title = title[:52] + '...'
        
        print(C.YLW + cls.box_row(f"Produit   : {title}") + C.RST)
        print(C.YLW + cls.box_row(f"Reference : {product.get('reference', 'N/A')}") + C.RST)
        print(C.YLW + cls.box_mid() + C.RST)
        
        if price:
            pcolor = C.BGRN if price <= threshold else C.BRED
            print(C.YLW + cls.box_row(f"Prix actuel : CHF {price:.2f}", color=pcolor) + C.RST)
        
        print(C.YLW + cls.box_row(f"Seuil alerte: CHF {threshold:.2f}", color=C.CYN) + C.RST)
        
        if price:
            diff = price - threshold
            if diff > 0:
                print(C.YLW + cls.box_row(f"Ecart       : +CHF {diff:.2f} au-dessus", color=C.DIM) + C.RST)
            else:
                print(C.YLW + cls.box_row(f"OBJECTIF ATTEINT! CHF {abs(diff):.2f} sous le seuil", color=C.BGRN) + C.RST)
        
        print(C.YLW + cls.box_mid() + C.RST)
        ts = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        print(C.YLW + cls.box_row(f"Verification #{check_num} - {ts}") + C.RST)
        if next_check:
            print(C.YLW + cls.box_row(f"Prochaine   : {next_check}", color=C.DIM) + C.RST)
        print(C.YLW + cls.box_bot() + C.RST)


# =============================================================================
# FONCTIONS SCRAPING
# =============================================================================

def search_product(query):
    """Recherche un produit sur Toppreise.ch"""
    url = f"https://www.toppreise.ch/produktsuche?q={requests.utils.quote(query)}"
    
    UI.status(f"Recherche de '{query}' sur Toppreise.ch...")
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        text = resp.text
        
        products = []
        seen = set()
        
        # Pattern pour extraire les produits depuis les URLs
        # Format: /preisvergleich/Category/Product-Name-p123456
        pattern = r'/preisvergleich/[^/]+/([^"\?]+)-p(\d+)'
        matches = re.findall(pattern, text)
        
        for name_raw, pid in matches:
            if pid not in seen:
                seen.add(pid)
                
                # Nettoyer le nom (remplacer - par espace)
                name = name_raw.replace('-', ' ')
                
                # Filtrer les noms trop courts ou invalides
                if len(name) > 10 and 'CHF' not in name:
                    # Reconstruire l'URL
                    href = f"/preisvergleich/Grafikkarten/{name_raw}-p{pid}"
                    # Chercher la vraie URL dans le texte
                    url_match = re.search(rf'/preisvergleich/[^"\s]+{pid}[^"\s]*', text)
                    if url_match:
                        href = url_match.group(0).split('"')[0].split(')')[0]
                    
                    products.append({
                        'id': pid,
                        'name': name[:100],
                        'url': f"https://www.toppreise.ch{href}" if href.startswith('/') else href,
                    })
                    
                    if len(products) >= 10:
                        break
        
        return products
        
    except Exception as e:
        UI.err(f"Erreur de recherche: {e}")
        return []


def get_product_details(url, silent=False):
    """Recupere les details d'un produit"""
    if not silent:
        UI.status("Chargement des details...")
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        text = resp.text
        soup = BeautifulSoup(text, 'html.parser')
        
        # Titre depuis h1
        title = ""
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
        
        # Reference (entre parentheses a la fin)
        reference = ""
        ref_m = re.search(r'\(([^)]+)\)\s*$', title)
        if ref_m:
            reference = ref_m.group(1)
        
        # Extraction des offres avec BeautifulSoup
        offers = []
        seen = set()
        
        # Trouver tous les logos de shops
        shop_logos = soup.select('.Plugin_ShopLogo')
        
        for logo in shop_logos:
            # Trouver le nom du shop depuis l'image
            img = logo.find('img')
            if not img:
                continue
            shop_name = img.get('alt') or img.get('title') or ''
            shop_name = shop_name.strip()
            
            if not shop_name or shop_name in seen:
                continue
            
            # Remonter pour trouver le conteneur de l'offre
            # Le prix est dans un frere/parent avec class priceContainer
            parent = logo
            price_found = None
            
            # Chercher dans les parents/freres
            for _ in range(10):
                parent = parent.parent
                if not parent:
                    break
                
                # Chercher le prix dans ce conteneur
                price_div = parent.select_one('.Plugin_Price')
                if price_div:
                    price_text = price_div.get_text(strip=True)
                    price_clean = price_text.replace("'", "").replace(",", ".").strip()
                    try:
                        price_found = float(price_clean)
                        break
                    except ValueError:
                        pass
            
            if price_found and shop_name not in seen:
                seen.add(shop_name)
                offers.append({
                    'shop': shop_name,
                    'price': price_found,
                })
        
        # Trier par prix
        offers.sort(key=lambda x: x['price'])
        
        # Meilleur prix depuis "X Angebote ab CHF Y"
        best = None
        m = re.search(r'(\d+)\s*Angebote?\s*ab\s*CHF\s*([\d\'\.,]+)', text)
        if m:
            try:
                best = float(m.group(2).replace("'", "").replace(",", "."))
            except:
                pass
        
        # Fallback sur la premiere offre
        if not best and offers:
            best = offers[0]['price']
        
        return {
            'title': title,
            'reference': reference,
            'url': url,
            'best_price': best,
            'offers': offers[:5],
            'total_offers': len(offers)
        }
        
    except Exception as e:
        UI.err(f"Erreur de chargement: {e}")
        return None


# =============================================================================
# DISCORD
# =============================================================================

def send_discord(webhook, product, price, threshold):
    """Envoie une notification Discord"""
    embed = {
        "title": "ALERTE PRIX - GROSRAT",
        "description": "Le prix est passe sous votre seuil!",
        "color": 3066993,
        "fields": [
            {"name": "Produit", "value": product['title'][:256], "inline": False},
            {"name": "Reference", "value": product.get('reference') or "N/A", "inline": True},
            {"name": "Prix actuel", "value": f"**CHF {price:.2f}**", "inline": True},
            {"name": "Seuil", "value": f"CHF {threshold:.2f}", "inline": True},
            {"name": "Economie", "value": f"CHF {threshold - price:.2f}", "inline": True},
            {"name": "Lien", "value": f"[Toppreise]({product['url']})", "inline": False},
        ],
        "footer": {"text": f"GROSRAT - {datetime.now().strftime('%d.%m.%Y %H:%M')}"},
    }
    
    try:
        resp = requests.post(webhook, json={"username": "GROSRAT", "embeds": [embed]}, timeout=10)
        resp.raise_for_status()
        UI.ok("Notification Discord envoyee!")
        return True
    except Exception as e:
        UI.err(f"Erreur Discord: {e}")
        return False


# =============================================================================
# SUIVI
# =============================================================================

def check_price(product, threshold, webhook):
    """Verifie le prix actuel, retourne (price, offers)"""
    details = get_product_details(product['url'], silent=True)
    
    if details and details['best_price']:
        price = details['best_price']
        offers = details.get('offers', [])
        
        if price <= threshold:
            if webhook:
                send_discord(webhook, product, price, threshold)
        
        return price, offers
    return None, []


def save_config(product, threshold, webhook):
    """Sauvegarde la configuration (ancien format - legacy)"""
    config = {
        'product': product,
        'threshold': threshold,
        'webhook': webhook,
        'created': datetime.now().isoformat()
    }
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    UI.ok(f"Config sauvegardee: {CONFIG_FILE}")


def load_tracked_products():
    """Charge la liste des produits suivis"""
    if not os.path.exists(CONFIG_FILE):
        return {'products': [], 'webhook': ''}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Migration ancien format
            if 'product' in data and 'products' not in data:
                return {
                    'products': [{
                        'id': 1,
                        'product': data['product'],
                        'threshold': data['threshold'],
                        'active': True,
                        'created': data.get('created', datetime.now().isoformat())
                    }],
                    'webhook': data.get('webhook', '')
                }
            return data
    except:
        return {'products': [], 'webhook': ''}


def save_tracked_products(data):
    """Sauvegarde la liste des produits suivis"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_tracked_product(data, product, threshold):
    """Ajoute un produit a la liste de suivi"""
    # Generer un nouvel ID
    max_id = 0
    for p in data['products']:
        if p.get('id', 0) > max_id:
            max_id = p['id']
    
    new_entry = {
        'id': max_id + 1,
        'product': product,
        'threshold': threshold,
        'active': True,
        'created': datetime.now().isoformat()
    }
    data['products'].append(new_entry)
    save_tracked_products(data)
    return new_entry['id']


def remove_tracked_product(data, product_id):
    """Supprime un produit de la liste"""
    data['products'] = [p for p in data['products'] if p.get('id') != product_id]
    save_tracked_products(data)


def start_tracking(product, threshold, webhook):
    """Demarre le suivi automatique d'un seul produit (mode legacy)"""
    UI.header()
    UI.section("DEMARRAGE DU SUIVI", C.GRN)
    
    UI.info("Produit", product['title'][:55])
    UI.info("Reference", product['reference'])
    UI.info("Seuil", f"CHF {threshold:.2f}")
    UI.info("Intervalle", f"{CHECK_INTERVAL_HOURS}h (4x/jour)")
    UI.info("Discord", "Actif" if webhook else "Inactif")
    
    print()
    print(f"  {C.DIM}Ctrl+C pour arreter{C.RST}")
    
    save_config(product, threshold, webhook)
    
    count = 0
    
    try:
        while True:
            count += 1
            UI.header()
            
            price, offers = check_price(product, threshold, webhook)
            
            # Afficher les offres
            UI.offers_box(offers)
            
            # Calculer prochaine verification
            next_t = datetime.now().timestamp() + (CHECK_INTERVAL_HOURS * 3600)
            next_str = datetime.fromtimestamp(next_t).strftime('%d.%m.%Y %H:%M')
            
            # Afficher le statut du suivi
            UI.tracking_box(product, threshold, count, price, next_str)
            
            print()
            print(f"  {C.DIM}Ctrl+C pour arreter{C.RST}")
            
            time.sleep(CHECK_INTERVAL_HOURS * 3600)
            
    except KeyboardInterrupt:
        print()
        UI.warn("Suivi arrete")
        UI.status("Relancez pour reprendre")


def start_multi_tracking(data):
    """Demarre le suivi automatique de plusieurs produits"""
    webhook = data.get('webhook', '')
    products = [p for p in data['products'] if p.get('active', True)]
    
    if not products:
        UI.err("Aucun produit actif a suivre")
        return
    
    UI.header()
    UI.section("DEMARRAGE DU SUIVI MULTI-ARTICLES", C.GRN)
    
    UI.info("Articles", f"{len(products)} produit(s)")
    UI.info("Intervalle", f"{CHECK_INTERVAL_HOURS}h (4x/jour)")
    UI.info("Discord", "Actif" if webhook else "Inactif")
    
    print()
    for p in products:
        title = p['product']['title'][:45]
        print(f"  {C.CYN}[{p['id']}]{C.RST} {title} - Seuil: CHF {p['threshold']:.2f}")
    
    print()
    print(f"  {C.DIM}Ctrl+C pour arreter{C.RST}")
    time.sleep(2)
    
    count = 0
    
    try:
        while True:
            count += 1
            UI.header()
            
            # Recharger les produits (au cas ou modifies)
            data = load_tracked_products()
            products = [p for p in data['products'] if p.get('active', True)]
            webhook = data.get('webhook', '')
            
            print()
            print(C.YLW + UI.box_top() + C.RST)
            print(C.YLW + UI.box_row(f"SUIVI MULTI-ARTICLES - Verification #{count}", 'center', C.BOLD) + C.RST)
            print(C.YLW + UI.box_row(datetime.now().strftime('%d.%m.%Y %H:%M:%S'), 'center', C.DIM) + C.RST)
            print(C.YLW + UI.box_bot() + C.RST)
            
            # Verifier chaque produit
            for entry in products:
                product = entry['product']
                threshold = entry['threshold']
                
                print()
                title = product['title']
                if len(title) > 50:
                    title = title[:47] + '...'
                
                print(f"  {C.BCYN}[{entry['id']}]{C.RST} {C.WHT}{title}{C.RST}")
                
                price, offers = check_price(product, threshold, webhook)
                
                if price:
                    if price <= threshold:
                        status = f"{C.BGRN}CHF {price:.2f} <= {threshold:.2f} [ALERTE!]{C.RST}"
                    else:
                        diff = price - threshold
                        status = f"{C.YLW}CHF {price:.2f}{C.RST} (seuil: {threshold:.2f}, ecart: +{diff:.2f})"
                    print(f"      {status}")
                    
                    if offers:
                        best = offers[0]
                        print(f"      {C.DIM}Meilleur: {best['shop']} a CHF {best['price']:.2f}{C.RST}")
                else:
                    print(f"      {C.BRED}Erreur de chargement{C.RST}")
                
                time.sleep(1)  # Pause entre requetes
            
            # Prochaine verification
            next_t = datetime.now().timestamp() + (CHECK_INTERVAL_HOURS * 3600)
            next_str = datetime.fromtimestamp(next_t).strftime('%d.%m.%Y %H:%M')
            
            print()
            print(C.CYN + UI.box_top() + C.RST)
            print(C.CYN + UI.box_row(f"Prochaine verification: {next_str}", 'center') + C.RST)
            print(C.CYN + UI.box_row("[M] Menu  |  Ctrl+C Quitter", 'center', C.DIM) + C.RST)
            print(C.CYN + UI.box_bot() + C.RST)
            
            # Attente interruptible
            if wait_with_keycheck(CHECK_INTERVAL_HOURS * 3600):
                # Retour au menu demande
                print()
                UI.status("Retour au menu...")
                time.sleep(1)
                return  # Retour au menu principal
            
    except KeyboardInterrupt:
        print()
        UI.warn("Suivi arrete")
        UI.status("Retour au menu...")
        time.sleep(1)


# =============================================================================
# ECRANS MULTI-ARTICLES
# =============================================================================

def screen_main_menu():
    """Menu principal"""
    data = load_tracked_products()
    nb_products = len(data['products'])
    nb_active = len([p for p in data['products'] if p.get('active', True)])
    
    UI.header()
    
    print()
    print(C.YLW + UI.box_top() + C.RST)
    print(C.YLW + UI.box_row("MENU PRINCIPAL", 'center', C.BOLD) + C.RST)
    print(C.YLW + UI.box_mid() + C.RST)
    print(C.YLW + UI.box_row("") + C.RST)
    print(C.YLW + UI.box_row(f"  [1]  Ajouter un article a suivre", color=C.WHT) + C.RST)
    print(C.YLW + UI.box_row(f"  [2]  Voir les articles suivis ({nb_products})", color=C.WHT) + C.RST)
    print(C.YLW + UI.box_row(f"  [3]  Supprimer un article", color=C.WHT) + C.RST)
    print(C.YLW + UI.box_row(f"  [4]  Configurer Discord", color=C.WHT) + C.RST)
    print(C.YLW + UI.box_row("") + C.RST)
    print(C.YLW + UI.box_mid() + C.RST)
    
    if nb_active > 0:
        print(C.YLW + UI.box_row(f"  [S]  DEMARRER LE SUIVI ({nb_active} actifs)", color=C.BGRN) + C.RST)
    else:
        print(C.YLW + UI.box_row(f"  [S]  Demarrer le suivi (aucun article)", color=C.DIM) + C.RST)
    
    print(C.YLW + UI.box_row(f"  [Q]  Quitter", color=C.DIM) + C.RST)
    print(C.YLW + UI.box_row("") + C.RST)
    print(C.YLW + UI.box_bot() + C.RST)
    
    choice = UI.prompt("Choix").lower()
    return choice


def screen_list_products():
    """Affiche la liste des produits suivis"""
    data = load_tracked_products()
    
    UI.header()
    UI.section(f"ARTICLES SUIVIS ({len(data['products'])})", C.CYN)
    
    if not data['products']:
        print()
        print(f"  {C.DIM}Aucun article suivi pour le moment.{C.RST}")
        print(f"  {C.DIM}Utilisez [1] pour ajouter un article.{C.RST}")
    else:
        print()
        for entry in data['products']:
            product = entry['product']
            threshold = entry['threshold']
            active = entry.get('active', True)
            
            status_icon = C.BGRN + "[ON] " if active else C.BRED + "[OFF]"
            title = product['title']
            if len(title) > 45:
                title = title[:42] + '...'
            
            print(f"  {C.YLW}[{entry['id']}]{C.RST} {status_icon}{C.RST} {C.WHT}{title}{C.RST}")
            print(f"       {C.DIM}Ref: {product.get('reference', 'N/A')} | Seuil: CHF {threshold:.2f}{C.RST}")
            print()
    
    # Webhook status
    print()
    webhook = data.get('webhook', '')
    if webhook:
        print(f"  {C.MAG}Discord:{C.RST} {C.BGRN}Configure{C.RST}")
    else:
        print(f"  {C.MAG}Discord:{C.RST} {C.DIM}Non configure{C.RST}")
    
    print()
    input(f"  {C.DIM}Appuyez sur Entree pour continuer...{C.RST}")


def screen_remove_product():
    """Supprime un produit"""
    data = load_tracked_products()
    
    UI.header()
    UI.section("SUPPRIMER UN ARTICLE", C.RED)
    
    if not data['products']:
        print()
        UI.warn("Aucun article a supprimer")
        time.sleep(1)
        return
    
    print()
    for entry in data['products']:
        product = entry['product']
        title = product['title'][:50]
        print(f"  {C.YLW}[{entry['id']}]{C.RST} {title}")
    
    print()
    print(f"  {C.DIM}0 = annuler{C.RST}")
    
    try:
        choice = int(UI.prompt("ID a supprimer"))
        if choice == 0:
            return
        
        # Trouver le produit
        found = None
        for entry in data['products']:
            if entry['id'] == choice:
                found = entry
                break
        
        if found:
            if UI.confirm(f"Supprimer '{found['product']['title'][:40]}...'?"):
                remove_tracked_product(data, choice)
                UI.ok("Article supprime")
                time.sleep(1)
        else:
            UI.err("ID non trouve")
            time.sleep(1)
    except ValueError:
        UI.err("ID invalide")
        time.sleep(1)


def screen_config_discord():
    """Configure le webhook Discord global"""
    data = load_tracked_products()
    
    UI.header()
    UI.section("CONFIGURATION DISCORD", C.MAG)
    
    current = data.get('webhook', '')
    
    print()
    if current:
        print(f"  {C.WHT}Webhook actuel:{C.RST}")
        print(f"  {C.DIM}{current[:50]}...{C.RST}")
    else:
        print(f"  {C.DIM}Aucun webhook configure{C.RST}")
    
    print()
    print(f"  {C.CYN}Creation webhook:{C.RST}")
    print(f"  {C.DIM}Discord > Serveur > Parametres > Integrations > Webhooks{C.RST}")
    
    print()
    print(f"  {C.DIM}Laissez vide pour supprimer le webhook actuel.{C.RST}")
    
    webhook = UI.prompt("Nouveau webhook")
    
    if webhook:
        if not webhook.startswith("https://discord.com/api/webhooks/"):
            UI.warn("URL non standard")
            if not UI.confirm("Continuer quand meme?"):
                return
    
    data['webhook'] = webhook
    save_tracked_products(data)
    
    if webhook:
        UI.ok("Webhook configure")
    else:
        UI.ok("Webhook supprime")
    time.sleep(1)


def add_product_flow():
    """Flux d'ajout d'un produit"""
    # Recherche
    selected = screen_search()
    if not selected:
        return False
    
    # Details
    details = screen_details(selected['url'])
    if not details:
        return False
    
    # Seuil
    threshold = screen_threshold(details.get('best_price'))
    if not threshold:
        return False
    
    # Produit a suivre
    product = {
        'title': details['title'],
        'reference': details['reference'],
        'url': details['url'],
        'best_price': details.get('best_price')
    }
    
    # Ajouter a la liste
    data = load_tracked_products()
    new_id = add_tracked_product(data, product, threshold)
    
    UI.header()
    UI.section("ARTICLE AJOUTE", C.GRN)
    
    print()
    UI.info("ID", f"#{new_id}")
    UI.info("Produit", product['title'][:50])
    UI.info("Seuil", f"CHF {threshold:.2f}")
    
    print()
    UI.ok("L'article a ete ajoute a la liste de suivi!")
    
    print()
    if UI.confirm("Ajouter un autre article?"):
        return True  # Continuer
    return False


# =============================================================================
# ECRANS
# =============================================================================

def screen_search():
    """Ecran de recherche"""
    UI.header()
    UI.section("RECHERCHE", C.CYN)
    
    print()
    print(f"  {C.WHT}Entrez le nom du produit a rechercher.{C.RST}")
    print(f"  {C.DIM}Exemple: Garmin Fenix 8 Pro 51mm{C.RST}")
    
    query = UI.prompt("Recherche")
    if not query:
        UI.err("Recherche vide")
        return None
    
    products = search_product(query)
    if not products:
        UI.err("Aucun resultat")
        return None
    
    return screen_select(products)


def screen_select(products):
    """Ecran de selection"""
    UI.header()
    UI.section(f"RESULTATS ({len(products)})", C.CYN)
    
    print()
    for i, p in enumerate(products, 1):
        c = C.WHT if i % 2 == 0 else C.BWHT
        print(f"  {C.YLW}[{i}]{C.RST} {c}{p['name']}{C.RST}")
    
    print()
    print(f"  {C.DIM}0 = annuler{C.RST}")
    
    try:
        choice = int(UI.prompt("Choix"))
        if choice == 0:
            return None
        if 1 <= choice <= len(products):
            return products[choice - 1]
        UI.err("Numero invalide")
        return None
    except ValueError:
        UI.err("Entrez un numero")
        return None


def screen_details(url):
    """Ecran des details"""
    details = get_product_details(url)
    if not details:
        UI.err("Impossible de charger le produit")
        return None
    
    UI.header()
    UI.product_card(details)
    
    print()
    if not UI.confirm("Est-ce le bon produit?"):
        return None
    
    return details


def screen_threshold(current_price):
    """Ecran du seuil"""
    UI.header()
    UI.section("SEUIL D'ALERTE", C.YLW)
    
    print()
    if current_price:
        print(f"  {C.WHT}Prix actuel: {C.BGRN}CHF {current_price:.2f}{C.RST}")
    print(f"  {C.WHT}Alerte quand le prix passe SOUS ce seuil.{C.RST}")
    
    try:
        val = UI.prompt("Seuil (CHF)")
        threshold = float(val.replace(",", ".").replace("CHF", "").strip())
        if threshold <= 0:
            UI.err("Le seuil doit etre positif")
            return None
        return threshold
    except ValueError:
        UI.err("Valeur invalide")
        return None


def screen_discord():
    """Ecran Discord"""
    UI.header()
    UI.section("NOTIFICATIONS DISCORD", C.MAG)
    
    print()
    print(f"  {C.WHT}Webhook Discord pour les alertes (optionnel).{C.RST}")
    print(f"  {C.DIM}Laissez vide pour desactiver.{C.RST}")
    print()
    print(f"  {C.CYN}Creation webhook:{C.RST}")
    print(f"  {C.DIM}Serveur > Parametres > Integrations > Webhooks{C.RST}")
    
    webhook = UI.prompt("Webhook (ou vide)")
    
    if webhook and not webhook.startswith("https://discord.com/api/webhooks/"):
        UI.warn("URL non standard")
        if not UI.confirm("Continuer?"):
            webhook = ""
    
    return webhook


def screen_summary(product, threshold, webhook):
    """Ecran resume"""
    UI.header()
    UI.section("RESUME", C.GRN)
    
    print()
    title = product['title']
    if len(title) > 50:
        title = title[:47] + '...'
    
    UI.info("Produit", title)
    UI.info("Reference", product['reference'])
    
    if product.get('best_price'):
        UI.info("Prix actuel", f"CHF {product['best_price']:.2f}")
    
    UI.info("Seuil", f"CHF {threshold:.2f}", vcolor=C.BYLW)
    UI.info("Discord", "Actif" if webhook else "Inactif", 
            vcolor=C.BGRN if webhook else C.BRED)
    UI.info("Frequence", f"4x/jour ({CHECK_INTERVAL_HOURS}h)")
    
    print()
    return UI.confirm("Lancer le suivi?")


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Activer couleurs Windows
    if os.name == 'nt':
        os.system('color')
    
    while True:
        choice = screen_main_menu()
        
        if choice == '1':
            # Ajouter un article
            while add_product_flow():
                pass  # Continue tant que l'utilisateur veut ajouter
        
        elif choice == '2':
            # Voir les articles
            screen_list_products()
        
        elif choice == '3':
            # Supprimer un article
            screen_remove_product()
        
        elif choice == '4':
            # Configurer Discord
            screen_config_discord()
        
        elif choice == 's':
            # Demarrer le suivi
            data = load_tracked_products()
            active = [p for p in data['products'] if p.get('active', True)]
            
            if not active:
                UI.header()
                UI.err("Aucun article actif a suivre!")
                UI.status("Ajoutez des articles avec [1]")
                time.sleep(2)
            else:
                start_multi_tracking(data)
        
        elif choice == 'q':
            UI.header()
            print()
            print(f"  {C.CYN}A bientot!{C.RST}")
            print()
            break
        
        else:
            # Choix invalide
            pass


if __name__ == "__main__":
    main()
