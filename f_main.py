import streamlit as st
import pandas as pd
import os

# --- Configuration de la page Streamlit ---
st.set_page_config(layout="wide")

# --- SECTION POUR LE LOGO ---
# Il est dans le même repertoire que le script f_main.py
logo_path = "dit_logo.png" 
if os.path.exists(logo_path):
    st.image(logo_path, width=300)
else:
    st.warning(f"Le fichier logo '{logo_path}' n'a pas été trouvé. Veuillez le placer au bon endroit.")
# --- FIN SECTION LOGO ---

st.title("🏡 Examen Data Collection : Analyse et Feedback")
st.markdown("Cette application présente des données immobilières locales et intègre un formulaire de feedback.")



## Aperçu des Données Immobilières Collectées (via Web Scraper) :
data_folder = "data"

# Dictionnaire des fichiers CSV à afficher
csv_files_to_display = {
    "Villas": "villas.csv",
    "Appartements": "appartements.csv",
    "Terrains": "terrains.csv"
}

# Vérification si le dossier 'data' existe avant de tenter de charger les fichiers
if not os.path.exists(data_folder):
    st.error(f"Le dossier '{data_folder}' est introuvable. Créez-le et placez-y vos fichiers CSV.")
else:
    # Utilisation des onglets pour une meilleure présentation si nous avons plusieurs fichiers
    tabs = st.tabs(list(csv_files_to_display.keys()))

    for i, (tab_name, filename) in enumerate(csv_files_to_display.items()):
        with tabs[i]:
            st.subheader(f"Données : {tab_name}")
            file_path = os.path.join(data_folder, filename)
            
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)
                    st.write(f"Fichier **`{filename}`** chargé avec succès.")
                    st.write(f"**Taille :** {len(df)} lignes, {len(df.columns)} colonnes.")
                    st.dataframe(df.head(10)) # Affiche les 10 premières lignes
                    
                    # Bouton de téléchargement du fichier original
                    csv_download_data = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label=f"Télécharger {filename}",
                        data=csv_download_data,
                        file_name=filename,
                        mime="text/csv",
                        key=f"download_{filename}"
                    )
                except pd.errors.EmptyDataError:
                    st.warning(f"Le fichier '{filename}' est vide. Il n'y a pas de données à afficher.")
                except Exception as e:
                    st.error(f"Une erreur s'est produite lors du chargement de '{filename}' : {e}")
            else:
                st.info(f"Le fichier **`{filename}`** n'a pas été trouvé dans le dossier `{data_folder}`. Veuillez le placer là.")


## Collecte de Feedback via KoboToolbox

st.header("Donnez votre avis sur l'application !")
st.markdown("""
    Vos retours sont importants pour améliorer cette application.
    Veuillez utiliser le formulaire ci-dessous pour laisser votre notation et vos commentaires.
""")

# NOTRE URL PUBLIQUE DE DÉPLOIEMENT DU FORMULAIRE KOBOTOOLBOX
kobo_form_url = "https://ee.kobotoolbox.org/x/ZSbOXWh3"


# Utilisation d'un iframe pour intégrer le formulaire Kobotoolbox
st.components.v1.iframe(kobo_form_url, height=700, scrolling=True)

st.markdown("---")
st.info("Ceci est l'application Streamlit pour notre examen de Data Collection.")
st.info("Le temps impartie ne nous a pas permit d'insérer notre script, le scraping avec sélénium.")