from flask import Flask, request, jsonify
import subprocess
import shlex

app = Flask(__name__)

# Clé secrète simple pour éviter que n'importe qui spamme ton service.
# Change cette valeur et mets la MÊME valeur côté PHP.
API_KEY = "pouetpouet123"


@app.route("/transcribe", methods=["POST"])
def transcribe():
    data = request.get_json(silent=True) or {}

    # --- Sécurité simple par clé ---
    if data.get("key") != API_KEY:
        return jsonify({"error": "unauthorized"}), 401

    text = data.get("text", "").strip()
    lang = data.get("lang", "fr").strip()

    if not text:
        return jsonify({"error": "missing 'text' field"}), 400

    if len(text) > 2000:
        return jsonify({"error": "text too long (max 2000 characters)"}), 400

    try:
        # -q : pas de sortie audio, --ipa : sortie en API, -v : langue
        result = subprocess.run(
            ["espeak-ng", "-v", lang, "-q", "--ipa"],
            input=text,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"error": "transcription timed out"}), 504
    except FileNotFoundError:
        return jsonify({"error": "espeak-ng not found on server"}), 500

    if result.returncode != 0:
        return jsonify({"error": "espeak-ng failed", "details": result.stderr.strip()}), 500

    ipa = result.stdout.strip()

    return jsonify({
        "text": text,
        "lang": lang,
        "ipa": ipa,
    })


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Service de transcription API opérationnel"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
