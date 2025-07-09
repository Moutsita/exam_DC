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
CATEGORY_PATH = '/categorie/appartements'
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
    # CORRECTION ICI : Utiliser 'page' au lieu de 'p'
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
        # La limite max du site est 119 (page=119), donc 120 est une bonne limite pour l'utilisateur
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
        # Attendre que les liens des appartements soient présents
        WebDriverWait(driver, 15).until( # 15 secondes pour plus de robustesse
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.card-image"))
        )
        print(f"  Liens des appartements apparus sur la page {page_num}.")
    except Exception as e:
        print(f"  Erreur: Les liens des appartements n'ont pas été trouvés sur la page {page_num}. Fin de la collecte des pages. Message: {e}")
        break # Si les liens ne sont pas trouvés, cela peut indiquer la fin des pages
    
    links_elements = driver.find_elements(By.CSS_SELECTOR, "a.card-image")
    
    # Si aucune annonce n'est trouvée sur la page actuelle, on arrête
    if not links_elements:
        print(f"  Aucun appartement trouvé sur la page {page_num}. Fin de la collecte des pages.")
        break

    for link_element in links_elements:
        relative_url = link_element.get_attribute('href')
        if relative_url:
            full_url = urljoin(BASE_URL, relative_url)
            if "/appartements/" in full_url: # S'assurer que c'est bien un lien d'appartements
                all_ad_urls.add(full_url)
    
    print(f"  Total d'URLs collectées jusqu'à présent : {len(all_ad_urls)}")
    page_num += 1

urls_to_scrape = list(all_ad_urls) # Convertir le set en liste pour le scraping séquentiel
print(f"\nCollecte des URLs terminée. {len(urls_to_scrape)} URLs uniques d'annonces à scraper en détail.")

if not urls_to_scrape:
    print("ATTENTION : Aucune URL d'appartement valide trouvée. Vérifiez les sélecteurs de liens ou la pagination.")
    driver.quit()
    exit()

# --- Scraping des données de chaque appartement individuel ---
all_appartements_data = []

for i, url_detail_appartement in enumerate(urls_to_scrape):
    print(f"\n --- Scraping de la villa {i+1}/{len(urls_to_scrape)} : {url_detail_appartement} ---")
    driver.get(url_detail_appartement)
    
    time.sleep(5) # Pause pour un chargement initial plus stable de la page de détail
    
    # Dictionnaire des données pour cette villa spécifique (initialisation pour garantir toutes les clés)
    # NOTE: 'description' est retirée ici
    appartement_data = {
        'url': url_detail_appartement,
        'price': 'N/A',
        'nombre_de_pieces': 'N/A',
        'adresse': 'N/A',
        'nombre_de_salles_de_bain': 'N/A',
        'image_lien': 'N/A'
    }
    
    try:
        # Le titre comme condition d'attente
        WebDriverWait(driver, 15).until( 
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1.title")) 
        )
        print("  Le titre de l'appartement est apparu sur la page de détail.")
    except Exception as e:
        print(f"  Erreur: La page de détail ne semble pas avoir chargé correctement ou le titre n'est pas présent pour {url_detail_appartement}. Message: {e}")
        all_appartements_data.append(appartement_data) # Ajouter les données partielles avant de continuer
        continue 

    # --- Extraction des données dans la page de détail ---
    
    # Prix
    try:
        price_element = driver.find_element(By.CSS_SELECTOR, 'p.price')
        appartement_data['price'] = price_element.text.strip()
    except Exception as e:
        print(f"  Erreur lors de la récupération du prix : {e}")
    print(f"  Prix trouvé : {appartement_data['price']}")
    
    # Nombre de pièces (Stratégie de fallback améliorée)
    try:
        nbre_pieces_element = driver.find_element(By.CSS_SELECTOR, ".hide-on-med-and-down li:nth-of-type(1) span.qt") 
        appartement_data['nombre_de_pieces'] = nbre_pieces_element.text.strip()
        print(f"  Nombre de pièces trouvé : {appartement_data['nombre_de_pieces']}")
    except Exception as e:
        print(f"  Erreur lors de la récupération du nombre de pièces avec le sélecteur principal : {e}. Tentative de recherche alternative.")
        try:
            nbre_pieces_element_alt = driver.find_element(By.CSS_SELECTOR, "div.ad-details span.qt")
            appartement_data['nombre_de_pieces'] = nbre_pieces_element_alt.text.strip()
            print(f"  Nombre de pièces trouvé (alternative) : {appartement_data['nombre_de_pieces']}")
        except Exception as e_alt:
            try:
                list_items = driver.find_elements(By.CSS_SELECTOR, "div.ad-details ul li")
                found_rooms = False
                for item in list_items:
                    text_content = item.text.strip()
                    if "pièce" in text_content.lower() or "chambre" in text_content.lower():
                        match = re.search(r'(\d+)\s*(pièce|chambre)', text_content.lower())
                        if match:
                            appartement_data['nombre_de_pieces'] = match.group(1) + " pièces" 
                            found_rooms = True
                            print(f"  Nombre de pièces trouvé (alternative 2 par texte) : {appartement_data['nombre_de_pieces']}")
                            break
                if not found_rooms:
                     print(f"  Aucune alternative pour le nombre de pièces trouvée par texte.")
            except Exception as e_alt2:
                print(f"  Erreur lors de la dernière tentative pour le nombre de pièces : {e_alt2}")

    # Adresse
    try:
        adresse_element = driver.find_element(By.CSS_SELECTOR, "div.extra-info-ad-detail")
        adresse_text = adresse_element.text.strip()
        
        parts = [p.strip() for p in adresse_text.split('\n') if p.strip()]
        if len(parts) > 1:
            appartement_data['adresse'] = parts[1] 
        else:
            match = re.search(r'([A-Za-zÀ-ÿ\s-]+,\s*[A-Za-zÀ-ÿ\s-]+)(?:\s+Villas)?$', adresse_text)
            if match:
                appartement_data['adresse'] = match.group(1).strip()
            else:
                appartement_data['adresse'] = adresse_text.strip() 
        print(f"  Adresse trouvée : {appartement_data['adresse']}")
    except Exception as e:
        print(f"  Erreur lors de la récupération de l'adresse : {e}")
        
    # Le nombre de salles de bain
    try:
        nbre_salle_element = driver.find_element(By.CSS_SELECTOR, ".hide-on-med-and-down li:nth-of-type(2) span.qt") 
        appartement_data['nombre_de_salles_de_bain'] = nbre_salle_element.text.strip()
        print(f"  Nombre de salles de bains trouvé : {appartement_data['nombre_de_salles_de_bain']}")
    except Exception as e:
        print(f"  Erreur lors de la récupération du nombre de salles de bain avec le sélecteur principal : {e}. Tentative de recherche alternative.")
        try:
            nbre_salle_element_alt = driver.find_element(By.CSS_SELECTOR, "div.ad-details span.qt")
            appartement_data['nombre_de_salles_de_bain'] = nbre_pieces_element_alt.text.strip()
            print(f"  Nombre de salles de bain trouvé (alternative) : {appartement_data['nombre_de_salles_de_bain']}")
        except Exception as e_alt:
            try:
                list_items = driver.find_elements(By.CSS_SELECTOR, "div.ad-details ul li")
                found_rooms = False
                for item in list_items:
                    text_content = item.text.strip()
                    if "pièce" in text_content.lower() or "chambre" in text_content.lower():
                        match = re.search(r'(\d+)\s*(pièce|chambre)', text_content.lower())
                        if match:
                            appartement_data['nombre_de_salles_de_bain'] = match.group(1) + " pièces" 
                            found_rooms = True
                            print(f"  Nombre de salles de bain trouvé (alternative 2 par texte) : {appartement_data['nombre_de_salles_de_bain']}")
                            break
                if not found_rooms:
                     print(f"  Aucune alternative pour le nombre de salles de bains trouvée par texte.")
            except Exception as e_alt2:
                print(f"  Erreur lors de la dernière tentative pour le nombre de salles de bains : {e_alt2}")

    
    # Lien de l'image principale
    try:
        image_slide_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.swiper-slide-active"))
        )
        style_attribute = image_slide_element.get_attribute('style')
        match = re.search(r'url\((["\']?)(.*?)\1\)', style_attribute)
        if match:
            image_lien = match.group(2)
            appartement_data['image_lien'] = image_lien
            print(f"  Lien image trouvé (depuis style) : {appartement_data['image_lien']}")
        else:
            print(f"  Erreur: URL de l'image non trouvée dans l'attribut style pour {url_detail_appartement}")
    except Exception as e:
        print(f"  Erreur lors de la récupération du lien de l'image (élément non trouvé) : {e}")

    all_appartements_data.append(appartement_data)
    
# --- Création et affichage du DataFrame ---
print("\n--- Scraping terminé ! Création du DataFrame... ---")
df = pd.DataFrame(all_appartements_data)

print("\n--- Aperçu des données ---")
print(df.head())
print(f"\nDataFrame complet ({len(df)} lignes) :")
print(df)

# Sauvegarder les données dans un fichier CSV
try:
    df.to_csv("appartements_coinafrique.csv", index=False, encoding='utf-8')
    print("\nDonnées sauvegardées dans appartements_coinafrique.csv")
except Exception as e:
    print(f"Erreur lors de la sauvegarde du CSV : {e}")

# --- Fermeture du navigateur ---
print("\nFermeture du navigateur.")
driver.quit()