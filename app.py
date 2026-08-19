from flask import Flask, render_template, request
from scraper import analyser_article, generer_post_facebook, recuperer_tendances

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    resultat = None
    post_ia = None
    url_saisie = ""
    tendances = []

    if request.method == "POST":
        url_saisie = request.form.get("url", "").strip()
        if url_saisie:
            resultat = analyser_article(url_saisie)
            if resultat and resultat.get("resume"):
                post_ia = generer_post_facebook(resultat["titre"], resultat["resume"])
        tendances = recuperer_tendances(autoriser_collecte=False)
    else:
        tendances = recuperer_tendances()

    return render_template(
        "index.html", 
        resultat=resultat, 
        post_ia=post_ia, 
        url=url_saisie,
        tendances=tendances
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000)
