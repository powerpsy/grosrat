# 🐀 GROSRAT - Price Tracker

Suivi automatique de prix sur Toppreise.ch avec alertes Discord.

## Fonctionnalités

- 🔍 Recherche de produits sur Toppreise.ch
- 📊 Affichage des meilleurs prix et vendeurs
- 🎯 Définition d'un seuil de prix personnalisé
- ⏰ Suivi automatique 4x/jour (toutes les 6 heures)
- 🔔 Notifications Discord quand le prix atteint le seuil

## Installation

```bash
pip install -r requirements.txt
```

## Utilisation

```bash
python price_tracker.py
```

Le programme vous guidera pour :
1. Rechercher un produit
2. Sélectionner le bon modèle
3. Définir votre prix seuil
4. Configurer les notifications Discord (optionnel)
5. Lancer le suivi automatique

## Configuration Discord

Pour recevoir des notifications Discord :
1. Ouvrez les paramètres de votre serveur Discord
2. Allez dans **Intégrations** > **Webhooks**
3. Créez un nouveau webhook
4. Copiez l'URL du webhook et collez-la dans le programme

## Fichiers

- `price_tracker.py` - Programme principal
- `requirements.txt` - Dépendances Python
- `tracked_products.json` - Configuration du suivi (créé automatiquement)

## Exemple

```
🐀 GROSRAT - Price Tracker pour Toppreise.ch
================================================================================

📝 Quel article souhaitez-vous suivre ?
🔍 Recherche: Garmin Fenix 8 Pro 51mm

📋 5 produit(s) trouvé(s):
  [1] GARMIN fenix 8 Pro - AMOLED, Sapphire, Graphit / Schwarz, 51 mm

================================================================================
📱 INFORMATIONS DU PRODUIT
================================================================================
📌 Modèle: GARMIN fenix 8 Pro - AMOLED, Sapphire, Graphit / Schwarz, 51 mm
🔖 Référence: 010-03199-11
💰 MEILLEUR PRIX: CHF 998.00

Rang   Vendeur                        Prix
--------------------------------------------------------------------------------
🥇     vendeur1.ch                    CHF 998.00
🥈     vendeur2.ch                    CHF 1039.00
🥉     vendeur3.ch                    CHF 1057.80
================================================================================
```

## Licence

MIT - Utilisation libre
