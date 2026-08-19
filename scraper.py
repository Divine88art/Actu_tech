import feedparser
import html
import ipaddress
import os
import re
import socket
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import monotonic
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from google import genai

API_KEY = os.getenv("GEMINI_API_KEY")
FLUX_RSS = [
    "https://www.lesnumeriques.com/rss.xml", "https://www.frandroid.com/feed",
    "https://www.01net.com/feed/", "https://www.clubic.com/feed/news",
    "https://www.lsa-conso.fr/rss/technologies", "https://www.futura-sciences.com/rss/actualites.xml",
    "https://techcrunch.com/feed/", "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss", "https://feeds.arstechnica.com/arstechnica/index",
    "https://m.tomshardware.com/feeds/all", "https://www.technologyreview.com/feed/",
    "https://news.mit.edu/rss/feed", "https://news.mit.edu/rss/topic/artificial-intelligence2",
    "https://spectrum.ieee.org/feeds/topic/robotics.rss", "https://robohub.org/feed/",
    "https://www.sciencedaily.com/rss/all.xml", "https://medicalxpress.com/rss-feed/",
    "https://www.inserm.fr/actualite/feed/", "https://www.dpreview.com/feeds/news.xml",
    "https://petapixel.com/feed/",
]

_tendances_cache = None
_tendances_cache_date = 0
_tendances_cache_lock = Lock()
TENDANCES_CACHE_TTL = 300


def _recuperer_flux(url_flux):
    try:
        reponse = requests.get(url_flux, headers={"User-Agent": "ActuTech/1.0 (+RSS reader)"}, timeout=(2, 4))
        reponse.raise_for_status()
        flux = feedparser.parse(reponse.content)
        if not flux.entries:
            return None
        entree = flux.entries[0]
        return {
            "titre": entree.get("title", "Article sans titre"),
            "lien": entree.get("link", ""),
            "source": flux.feed.get("title", "Tech Source"),
        }
    except Exception:
        return None


def recuperer_tendances(autoriser_collecte=True):
    global _tendances_cache, _tendances_cache_date
    with _tendances_cache_lock:
        if _tendances_cache is not None and monotonic() - _tendances_cache_date < TENDANCES_CACHE_TTL:
            return _tendances_cache
        if not autoriser_collecte:
            return []
    with ThreadPoolExecutor(max_workers=8) as executor:
        articles = [article for article in executor.map(_recuperer_flux, FLUX_RSS) if article]
    with _tendances_cache_lock:
        _tendances_cache, _tendances_cache_date = articles, monotonic()
    return articles


def _url_est_externe(url):
    adresse = urlparse(url)
    if adresse.scheme not in {"http", "https"} or not adresse.hostname:
        return False
    try:
        adresses = socket.getaddrinfo(adresse.hostname, None)
    except socket.gaierror:
        return False
    return all(not ipaddress.ip_address(info[4][0]).is_private for info in adresses)


def analyser_article(url):
    if not _url_est_externe(url):
        return {"erreur": "L'URL doit être une adresse http(s) publique valide."}
    try:
        reponse = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ActuTech/1.0)"}, timeout=(3, 8))
        reponse.raise_for_status()
        soup = BeautifulSoup(reponse.content, "html.parser")
        titre = soup.title.get_text(strip=True) if soup.title else "Titre introuvable"
        image = soup.find("meta", property="og:image")
        textes = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        resume = " ".join(texte for texte in textes if len(texte) > 30)[:6000]
        if not resume:
            return {"erreur": "Aucun contenu lisible n'a été trouvé dans cet article."}
        return {"titre": titre, "image": image.get("content") if image else None, "resume": resume}
    except requests.RequestException as erreur:
        return {"erreur": html.escape(f"Impossible de récupérer l'article : {erreur}")}
    except Exception as erreur:
        return {"erreur": html.escape(f"Impossible d'analyser l'article : {erreur}")}


def generer_post_facebook(titre, resume_texte):
    if not API_KEY:
        return "Impossible de générer le post : la variable GEMINI_API_KEY n'est pas configurée."
    try:
        client = genai.Client(api_key=API_KEY)
        prompt = f"""Tu es le CM principal de la page Facebook 'Actu Tech'.
Rédige un post Facebook percutant et professionnel d'après cet article.

Titre original : {titre}
Contenu : {resume_texte}

Traduis en français si nécessaire. Commence par une accroche en majuscules avec emojis,
ajoute 3 points clés, une question ouverte et exactement 4 à 5 hashtags. N'utilise jamais '---'."""
        response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
        texte = html.escape(response.text or "")
        return re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", texte).replace("---", "")
    except Exception as erreur:
        return html.escape(f"Impossible de générer le post : {erreur}")
