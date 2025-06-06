from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from utils.detector_ai import analizar_imagen

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analizar", methods=["POST"])
def analizar():
    if "imagen" not in request.files:
        return jsonify({"error": "No se envió ninguna imagen"}), 400
    file = request.files["imagen"]
    if file.filename == "":
        return jsonify({"error": "Nombre de archivo vacío"}), 400
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    resultado = analizar_imagen(filepath)
    os.remove(filepath)
    return jsonify({"resultado": resultado})


if __name__ == "__main__":
    app.run()
