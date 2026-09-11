from flask import Flask, request, jsonify
import subprocess
from langdetect import detect, DetectorFactory, LangDetectException

# Rend la détection déterministe (résultats reproductibles)
DetectorFactory.seed = 0

app = Flask(__name__)

# Clé secrète simple pour éviter que n'importe qui spamme ton service.
API_KEY = "pouetpouet123"

# --- Mapping code détecté (ISO 639-1) -> code de voix eSpeak-NG ---
# La plupart correspondent directement ; quelques exceptions notables
# (mandarin, hébreu...) sont explicitées ci-dessous.
LANG_MAP = {
    "af": "af", "sq": "sq", "am": "am", "ar": "ar", "hy": "hy",
    "az": "az", "eu": "eu", "be": "be", "bn": "bn", "bs": "bs",
    "bg": "bg", "ca": "ca", "zh-cn": "cmn", "zh-tw": "cmn",
    "hr": "hr", "cs": "cs", "da": "da", "nl": "nl", "en": "en",
    "et": "et", "fi": "fi", "fr": "fr", "de": "de", "el": "el",
    "he": "he", "hi": "hi", "hu": "hu", "is": "is", "id": "id",
    "it": "it", "ja": "ja", "kn": "kn", "kk": "kk", "ko": "ko",
    "lv": "lv", "lt": "lt", "mk": "mk", "ms": "ms", "ml": "ml",
    "mr": "mr", "ne": "ne", "no": "nb", "fa": "fa", "pl": "pl",
    "pt": "pt", "pa": "pa", "ro": "ro", "ru": "ru", "sr": "sr",
    "sk": "sk", "sl": "sl", "es": "es", "sw": "sw", "sv": "sv",
    "ta": "ta", "te": "te", "th": "th", "tr": "tr", "uk": "uk",
    "ur": "ur", "vi": "vi", "cy": "cy",
}

# --- Liste affichée côté frontend (code eSpeak -> nom lisible) ---
SUPPORTED_LANGUAGES = {
    "auto": "Détection automatique",
    "fr": "Français", "en": "Anglais", "es": "Espagnol", "de": "Allemand",
    "it": "Italien", "pt": "Portugais", "nl": "Néerlandais", "pl": "Polonais",
    "ru": "Russe", "uk": "Ukrainien", "el": "Grec", "tr": "Turc",
    "sv": "Suédois", "da": "Danois", "nb": "Norvégien", "fi": "Finnois",
    "cs": "Tchèque", "sk": "Slovaque", "ro": "Roumain", "hu": "Hongrois",
    "bg": "Bulgare", "hr": "Croate", "sr": "Serbe", "he": "Hébreu",
    "ar": "Arabe", "fa": "Persan", "hi": "Hindi", "bn": "Bengali",
    "ta": "Tamoul", "te": "Télougou", "ml": "Malayalam", "mr": "Marathi",
    "th": "Thaï", "vi": "Vietnamien", "id": "Indonésien", "ms": "Malais",
    "cmn": "Chinois (mandarin)", "ja": "Japonais", "ko": "Coréen",
    "sw": "Swahili", "am": "Amharique", "cy": "Gallois", "is": "Islandais",
}


def detect_language(text):
    """Détecte la langue du texte et renvoie un code compatible eSpeak-NG.
    Retombe sur 'fr' si la détection échoue (texte trop court, etc.)."""
    try:
        detected = detect(text)
    except LangDetectException:
        return "fr", "fr"
    espeak_code = LANG_MAP.get(detected, detected)
    return detected, espeak_code


@app.route("/transcribe", methods=["POST"])
def transcribe():
    data = request.get_json(silent=True) or {}

    if data.get("key") != API_KEY:
        return jsonify({"error": "unauthorized"}), 401

    text = data.get("text", "").strip()
    lang = data.get("lang", "fr").strip()

    if not text:
        return jsonify({"error": "missing 'text' field"}), 400

    if len(text) > 2000:
        return jsonify({"error": "text too long (max 2000 characters)"}), 400

    detected_iso = None
    if lang == "auto" or not lang:
        detected_iso, lang = detect_language(text)

    try:
        lines = text.split("\n")
        ipa_lines = []
        for line in lines:
            if line.strip() == "":
                ipa_lines.append("")
                continue
            result = subprocess.run(
                ["espeak-ng", "-v", lang, "-q", "--ipa"],
                input=line,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return jsonify({"error": "espeak-ng failed", "details": result.stderr.strip()}), 500
            # eSpeak-NG insère ses propres retours à la ligne à chaque pause
            # (virgule, point...). On les remplace par un espace pour ne
            # garder que les retours à la ligne voulus par l'utilisateur.
            clause_output = result.stdout.strip().replace("\n", " ")
            clause_output = " ".join(clause_output.split())
            ipa_lines.append(clause_output)
        ipa = "\n".join(ipa_lines)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "transcription timed out"}), 504
    except FileNotFoundError:
        return jsonify({"error": "espeak-ng not found on server"}), 500

    response = {
        "text": text,
        "lang": lang,
        "ipa": ipa,
    }
    if detected_iso:
        response["detected_lang"] = detected_iso

    return jsonify(response)


@app.route("/languages", methods=["GET"])
def languages():
    """Renvoie la liste des langues supportées, pour construire le menu déroulant."""
    return jsonify(SUPPORTED_LANGUAGES)


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Service de transcription API opérationnel"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
