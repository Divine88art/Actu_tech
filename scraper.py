import feedparser
import html
import os
import re
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import monotonic

import requests
from bs4 import BeautifulSoup
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY", "TA_CLE_API_ICI")

# --- 21 FLUX RSS STRUCTURES ---
FLUX_RSS = [
    "https://www.lesnumeriques.com/rss.xml",
    "https://www.frandroid.com/feed",
    "https://www.01net.com/feed/",
    "https://www.clubic.com/feed/news",
    "https://www.lsa-conso.fr/rss/technologies",
    "https://www.futura-sciences.com/rss/actualites.xml",
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://m.tomshardware.com/feeds/all",
    "https://www.technologyreview.com/feed/",
    "https://news.mit.edu/rss/feed",
    "https://news.mit.edu/rss/topic/artificial-intelligence2",
    "https://spectrum.ieee.org/feeds/topic/robotics.rss",
    "https://robohub.org/feed/",
    "https://www.sciencedaily.com/rss/all.xml",
    "https://medicalxpress.com/rss-feed/",
    "https://www.inserm.fr/actualite/feed/",
    "https://www.dpreview.com/feeds/news.xml",
    "https://petapixel.com/feed/",
]

_tendances_cache = None
_tendances_cache_date = 0
_tendances_cache_lock = Lock()
TENDANCES_CACHE_TTL = 300


def _recuperer_flux(url_flux):
    try:
        reponse = requests.get(
            url_flux,
            headers={"User-Agent": "ActuTech/1.0 (+RSS reader)"},
            timeout=(2, 4),
        )
        reponse.raise_for_status()
        flux = feedparser.parse(reponse.content)
        if not flux.entries:
            return None
        entry = flux.entries[0]
        return {
            "titre": entry.get("title", "Article sans titre"),
            "lien": entry.get("link", ""),
            "source": flux.feed.get("title", "Tech Source"),
        }
    except (requests.RequestException, Exception):
        return None


def recuperer_tendances(autoriser_collecte=True):
    global _tendances_cache, _tendances_cache_date

    with _tendances_cache_lock:
        if _tendances_cache is not None and monotonic() - _tendances_cache_date < TENDANCES_CACHE_TTL:
            return _tendances_cache
        if not autoriser_collecte:
            return []

    # Les flux lents ou indisponibles ne bloquent plus les autres sources.
    with ThreadPoolExecutor(max_workers=8) as executor:
        resultats = executor.map(_recuperer_flux, FLUX_RSS)
    articles_tendances = [article for article in resultats if article]

    with _tendances_cache_lock:
        _tendances_cache = articles_tendances
        _tendances_cache_date = monotonic()
    return articles_tendances


def analyser_article(url):
    if not url.startswith(("http://", "https://")):
        return {"erreur": "L'URL doit commencer par http:// ou https://."}

    try:
        reponse = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ActuTech/1.0)"},
            timeout=(3, 8),
        )
        reponse.raise_for_status()
        soup = BeautifulSoup(reponse.content, "html.parser")

        titre = soup.title.get_text(strip=True) if soup.title else "Titre introuvable"
        og_image = soup.find("meta", property="og:image")
        image_url = og_image.get("content") if og_image else None
        textes = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        textes = [texte for texte in textes if len(texte) > 30]
        contenu_complet = " ".join(textes[:6])

        if not contenu_complet:
            return {"erreur": "Aucun contenu lisible n'a été trouvé dans cet article."}
        return {"titre": titre, "image": image_url, "resume": contenu_complet}
    except requests.RequestException as e:
        return {"erreur": f"Impossible de récupérer l'article : {e}"}
    except Exception as e:
        return {"erreur": f"Impossible d'analyser l'article : {e}"}


def generer_post_facebook(titre, resume_texte):
    try:
        client = genai.Client(api_key=API_KEY)
        prompt = f"""
        Tu es le CM principal de la page Facebook 'Actu Tech'.
        Rédige un post Facebook percutant, engageant et professionnel d'après cet article.

        Titre original : {titre}
        Contenu de l'article : {resume_texte}

        CONSIGNES OBLIGATOIRES :
        1. TRADUCTION : Si l'article est en anglais, traduis et vulgarise le sujet dans un FRANÇAIS impeccable.
        2. ACCROCHE : Une première ligne choc/captivante en MAJUSCULES avec emojis.
        3. CORPS : 3 points clés clairs et aérés sous forme de puces.
        4. ENGAGEMENT : Termine par une question ouverte stimulante pour inviter au débat en commentaire.
        5. HASHTAGS : Ajoute exactement 4 à 5 hashtags stratégiques à la fin.
        6. FORMAT : N'utilise jamais de séparateurs '---'.
        """
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        texte = html.escape(response.text or "")
        texte = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", texte)
        return texte.replace("---", "")
    except Exception as e:
        return f"Impossible de générer le post : {e}"
import feedparser
import requests
import re
from bs4 import BeautifulSoup
from google import genai

API_KEY = "TA_CLE_API_ICI"  # Conserve ta vraie clé API ici !

# --- 21 FLUX RSS STRUCTURÉS ---
FLUX_RSS = [
    # Médias Tech (FR)
    "https://www.lesnumeriques.com/rss.xml",
    "https://www.frandroid.com/feed",
    "https://www.01net.com/feed/",
    "https://www.clubic.com/feed/news",
    "https://www.lsa-conso.fr/rss/technologies",
    "https://www.futura-sciences.com/rss/actualites.xml",
    
    # Tech & Innovation (EN)
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://m.tomshardware.com/feeds/all",
    "https://www.technologyreview.com/feed/",             # MIT Tech Review
    "https://news.mit.edu/rss/feed",                        # MIT News Global
    
    # Robotique & IA
    "https://news.mit.edu/rss/topic/artificial-intelligence2",
    "https://spectrum.ieee.org/feeds/topic/robotics.rss", # IEEE Spectrum
    "https://robohub.org/feed/",                          # Robohub
    
    # Sciences
    "https://www.sciencedaily.com/rss/all.xml",
    
    # Santé & Biotech
    "https://medicalxpress.com/rss-feed/",
    "https://www.inserm.fr/actualite/feed/",               # Inserm France
    
    # Photo & Imagerie
    "https://www.dpreview.com/feeds/news.xml",
    "https://petapixel.com/feed/"
]

def recuperer_tendances():
    articles_tendances = []
    
    for url_flux in FLUX_RSS:
        try:
            # Timeout rapide de 3s pour ne pas bloquer si un site rame
            flux = feedparser.parse(url_flux)
            if flux.entries:
                entry = flux.entries[0] # On prend le tout dernier article de chaque source
                articles_tendances.append({
                    'titre': entry.title,
                    'lien': entry.link,
                    'source': flux.feed.title if 'title' in flux.feed else 'Tech Source'
                })
        except Exception:
            continue
            
    return articles_tendances

def analyser_article(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        reponse = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(reponse.text, 'html.parser')

        titre = soup.title.string if soup.title else "Titre introuvable"
        
        # Image Meta (og:image)
        og_image = soup.find("meta", property="og:image")
        image_url = og_image["content"] if og_image else None

        # Paragraphes principaux
        paragraphes = soup.find_all("p")
        textes = [p.text.strip() for p in paragraphes if len(p.text.strip()) > 30]
        contenu_complet = " ".join(textes[:6])

        return {
            "titre": titre,
            "image": image_url,
            "resume": contenu_complet
        }
    except Exception as e:
        return {"erreur": f"Impossible d'analyser l'article : {e}"}

def generer_post_facebook(titre, resume_texte):
    try:
        client = genai.Client(api_key=API_KEY)
        
        prompt = f"""
        Tu es le CM principal de la page Facebook 'Actu Tech'.
        Rédige un post Facebook percutant, engageant et professionnel d'après cet article.

        Titre original : {titre}
        Contenu de l'article : {resume_texte}

        CONSIGNES OBLIGATOIRES :
        1. TRADUCTION : Si l'article est en anglais (ex: MIT, TechCrunch, IEEE), traduis et vulgarise le sujet dans un FRANÇAIS impeccable.
        2. ACCROCHE : Une première ligne choc/captivante en MAJUSCULES avec emojis.
        3. CORPS : 3 points clés clairs et aérés sous forme de puces.
        4. ENGAGEMENT : Termine par une question ouverte stimulante pour inviter au débat en commentaire.
        5. HASHTAGS : Ajoute exactement 4 à 5 hashtags stratégiques à la fin (mélange généraliste et niche, ex: #ActuTech #Innovation #IA #MIT).
        6. FORMAT : N'utilise jamais de séparateurs '---'.
        """
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        
        texte = response.text
        # Transformation du Markdown pour affichage HTML propre
        texte = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', texte)
        texte = texte.replace('---', '')
        return texte
        
    except Exception as e:
        return f"Impossible de générer le post : {e}"
