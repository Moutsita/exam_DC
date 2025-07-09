from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
import time
import pandas as pd
import re # Pour l'extraction de l'URL de l'image

# --- Configuration initiale de Selenium ---
BASE_URL = 'https://sn.coinafrique.com'
CATEGORY_PATH = '/categorie/terrains' # Cible les terrains
START_URL = urljoin(BASE_URL, CATEGORY_PATH)

path = r'C:\chrome-win64\chromedriver-win64\chromedriver.exe'

chrome_options = Options()
# Décommenter pour un mode sans affichage une fois que tout fonctionne bien
# chrome_options.add_argument("--headless") 
# chrome_options.add_argument("--disable-gpu")
# chrome_options.add_argument("--window-size=1920,1080")

service = Service(executable_path=path)
driver = webdriver.Chrome(service=service, options=chrome_options)

# --- Fonction pour construire l'URL de la page ---
def get_page_url(base_url, page_number):
    parsed_url = urlparse(base_url)
    query_params = parse_qs(parsed_url.query)
    query_params['page'] = [str(page_number)] 
    new_query = urlencode(query_params, doseq=True)
    return parsed_url._replace(query=new_query).geturl()

# --- Collecte des URLs de toutes les annonces sur plusieurs pages ---
all_ad_urls = set() # Utiliser un set pour garantir l'unicité
page_num = 1
max_pages_to_scrape = 0

while True:
    try:
        user_input = input("Entrez le nombre maximal de pages à scraper (max 119, 0 pour quitter) : ")
        max_pages_to_scrape = int(user_input)
        if 0 <= max_pages_to_scrape <= 119: 
            if max_pages_to_scrape == 0:
                print("Scraping annulé par l'utilisateur.")
                driver.quit()
                exit()
            break
        else:
            print("Veuillez entrer un nombre entre 0 et 119.")
    except ValueError:
        print("Entrée invalide. Veuillez entrer un nombre entier.")


print(f"Début de la collecte des URLs des annonces, jusqu'à {max_pages_to_scrape} pages.")

while page_num <= max_pages_to_scrape:
    current_page_url = get_page_url(START_URL, page_num)
    print(f"\n --- Navigation vers la page {page_num}/{max_pages_to_scrape} : {current_page_url} ---")
    driver.get(current_page_url)
    
    time.sleep(3) # Un petit délai pour le chargement de la page de liste

    try:
        # Attendre que les liens des annonces soient présents
        WebDriverWait(driver, 15).until( # 15 secondes pour plus de robustesse
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.card-image"))
        )
        print(f"  Liens des terrains apparus sur la page {page_num}.")
    except Exception as e:
        print(f"  Erreur: Les liens des terrains n'ont pas été trouvés sur la page {page_num}. Fin de la collecte des pages. Message: {e}")
        break # Si les liens ne sont pas trouvés, cela peut indiquer la fin des pages
    
    links_elements = driver.find_elements(By.CSS_SELECTOR, "a.card-image")
    
    # Si aucun terrain n'est trouvé sur la page actuelle, on arrête
    if not links_elements:
        print(f"  Aucun terrain trouvé sur la page {page_num}. Fin de la collecte des pages.")
        break

    for link_element in links_elements:
        relative_url = link_element.get_attribute('href')
        if relative_url:
            full_url = urljoin(BASE_URL, relative_url)
            # S'assurer que c'est bien un lien de terrains ET qu'il contient "/annonce/"
            if "/annonce/" in full_url and "/terrains/" in full_url: 
                all_ad_urls.add(full_url)
    
    print(f"  Total d'URLs collectées jusqu'à présent : {len(all_ad_urls)}")
    page_num += 1

urls_to_scrape = list(all_ad_urls) # Convertir le set en liste pour le scraping séquentiel
print(f"\nCollecte des URLs terminée. {len(urls_to_scrape)} URLs uniques d'annonces à scraper en détail.")

if not urls_to_scrape:
    print("ATTENTION : Aucune URL de terrain valide trouvée. Vérifiez les sélecteurs de liens ou la pagination.")
    driver.quit()
    exit()

# --- Scraping des données de chaque annonce individuelle ---
all_terrains_data = []

for i, url_detail_terrain in enumerate(urls_to_scrape):
    print(f"\n --- Scraping du terrain {i+1}/{len(urls_to_scrape)} : {url_detail_terrain} ---") # Message modifié
    driver.get(url_detail_terrain)
    
    time.sleep(5) # Pause pour un chargement initial plus stable de la page de détail
    
    # Dictionnaire des données pour ce terrain spécifique (initialisation pour garantir toutes les clés)
    terrain_data = {
        'url': url_detail_terrain,
        'price': 'N/A',
        'superficie': 'N/A', # Nom de la clé est correct
        'adresse': 'N/A',
        'image_lien': 'N/A'
    }
    
    try:
        # Le titre comme condition d'attente
        WebDriverWait(driver, 15).until( 
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.title")) 
        )
        print("  Le titre du terrain est apparu sur la page de détail.") # Message modifié
    except Exception as e:
        print(f"  Erreur: La page de détail ne semble pas avoir chargé correctement ou le titre n'est pas présent pour {url_detail_terrain}. Message: {e}")
        all_terrains_data.append(terrain_data)
        continue 

    # --- Extraction des données dans la page de détail ---

    # Prix
    try:
        price_element = driver.find_element(By.CSS_SELECTOR, 'p.price')
        terrain_data['price'] = price_element.text.strip()
    except Exception as e:
        print(f"  Erreur lors de la récupération du prix : {e}")
    print(f"  Prix trouvé : {terrain_data['price']}")
    
    # Superficie en m2 (basé sur la logique originale, corrigé l'assignation de la clé)
    try:
        superficie_element = driver.find_element(By.CSS_SELECTOR, ".hide-on-med-and-down li:nth-of-type(1) span.qt") 
        terrain_data['superficie'] = superficie_element.text.strip() # CORRECT : Assigne à 'superficie'
        print(f"  Superficie trouvée : {terrain_data['superficie']}")
    except Exception as e:
        print(f"  Erreur lors de la récupération de la superficie avec le sélecteur principal : {e}. Tentative de recherche alternative.")
        try:
            superficie_element_alt = driver.find_element(By.CSS_SELECTOR, "div.ad-details span.qt")
            terrain_data['superficie'] = superficie_element_alt.text.strip() # CORRECT : Assigne à 'superficie'
            print(f"  Superficie trouvée (alternative) : {terrain_data['superficie']}")
        except Exception as e_alt:
            try:
                list_items = driver.find_elements(By.CSS_SELECTOR, "div.ad-details ul li")
                found_superficie_via_text_fallback = False # Variable renommée pour éviter confusion
                for item in list_items:
                    text_content = item.text.strip()
                    # Conserver la logique de recherche originale, qui cherchait "pièce" ou "chambre"
                    # car vous avez indiqué que "l'ancien script marchait" et "ne prends pas comme critère m2".
                    if "pièce" in text_content.lower() or "chambre" in text_content.lower(): 
                        match = re.search(r'(\d+)\s*(pièce|chambre)', text_content.lower()) 
                        if match:
                            # Assigner à 'superficie' mais avec le texte "pièces" comme dans l'original
                            terrain_data['superficie'] = match.group(1) + " pièces" 
                            found_superficie_via_text_fallback = True
                            print(f"  Superficie trouvée (alternative 2 par texte) : {terrain_data['superficie']}")
                            break
                if not found_superficie_via_text_fallback:
                     print(f"  Aucune alternative pour la superficie trouvée par texte.")
            except Exception as e_alt2:
                print(f"  Erreur lors de la dernière tentative pour la superficie : {e_alt2}")

    # Adresse
    try:
        adresse_element = driver.find_element(By.CSS_SELECTOR, "div.extra-info-ad-detail")
        adresse_text = adresse_element.text.strip()
        
        parts = [p.strip() for p in adresse_text.split('\n') if p.strip()]
        if len(parts) > 1:
            terrain_data['adresse'] = parts[1] 
        else:
            # Ajusté le regex pour "Terrains" si nécessaire dans le texte de l'adresse
            match = re.search(r'([A-Za-zÀ-ÿ\s-]+,\s*[A-Za-zÀ-ÿ\s-]+)(?:\s+Terrains)?$', adresse_text)
            if match:
                terrain_data['adresse'] = match.group(1).strip()
            else:
                terrain_data['adresse'] = adresse_text.strip() 
        print(f"  Adresse trouvée : {terrain_data['adresse']}")
    except Exception as e:
        print(f"  Erreur lors de la récupération de l'adresse : {e}")
    
    # Lien de l'image principale
    try:
        image_slide_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.swiper-slide-active"))
        )
        style_attribute = image_slide_element.get_attribute('style')
        match = re.search(r'url\((["\']?)(.*?)\1\)', style_attribute)
        if match:
            image_lien = match.group(2)
            terrain_data['image_lien'] = image_lien
            print(f"  Lien image trouvé (depuis style) : {terrain_data['image_lien']}")
        else:
            print(f"  Erreur: URL de l'image non trouvée dans l'attribut style pour {url_detail_terrain}")
    except Exception as e:
        print(f"  Erreur lors de la récupération du lien de l'image (élément non trouvé) : {e}")

    all_terrains_data.append(terrain_data)
    
# --- Création et affichage du DataFrame ---
print("\n--- Scraping terminé ! Création du DataFrame... ---")
df = pd.DataFrame(all_terrains_data)

print("\n--- Aperçu des données ---")
print(df.head())
print(f"\nDataFrame complet ({len(df)} lignes) :")
print(df)

# Sauvegarder les données dans un fichier CSV
try:
    df.to_csv("terrains_coinafrique.csv", index=False, encoding='utf-8')
    print("\nDonnées sauvegardées dans terrains_coinafrique.csv") # Corrigé le nom du fichier ici
except Exception as e:
    print(f"Erreur lors de la sauvegarde du CSV : {e}")

# --- Fermeture du navigateur ---
print("\nFermeture du navigateur.")
driver.quit()