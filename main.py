from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename
from utils.detector_ai import analizar_imagen
import mysql.connector
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def guardar_historial(tipo_residuo, ip, imagen_path, objetos_detectados):
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="1230",
        database="detectorIA",
    )
    cursor = conn.cursor()
    now = datetime.now()
    fecha = now.date()
    hora = now.time()
    with open(imagen_path, "rb") as f:
        imagen = f.read()
    sql = "INSERT INTO historial_residuos (tipo_residuo, fecha, hora, ip, imagen, objetos_detectados) VALUES (%s, %s, %s, %s, %s, %s)"
    cursor.execute(sql, (tipo_residuo, fecha, hora, ip, imagen, objetos_detectados))
    conn.commit()
    cursor.close()
    conn.close()


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

    # Extraer nombres de objetos detectados usando la función de Azure
    from utils.detector_ai import obtener_objetos_detectados

    objetos_detectados = obtener_objetos_detectados(filepath)

    if resultado == "→ Residuo ORGÁNICO":
        tipo = "ORGÁNICOS"
    elif resultado == "→ Residuo INORGÁNICO":
        tipo = "INORGÁNICOS"
    elif resultado == "→ Puede contener residuos ORGÁNICOS e INORGÁNICOS":
        tipo = "ORGÁNICOS e INORGÁNICOS"
    else:
        tipo = None

    if tipo:
        ip = request.remote_addr
        guardar_historial(tipo, ip, filepath, objetos_detectados)
    os.remove(filepath)
    return jsonify({"resultado": resultado})


@app.route("/historial")
def historial():
    try:
        conn = mysql.connector.connect(
            host="localhost", user="root", password="1230", database="detectorIA"
        )
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tipo_residuo, fecha, hora, ip, imagen, objetos_detectados FROM historial_residuos ORDER BY id DESC"
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        import base64

        historial = []
        for tipo, fecha, hora, ip, imagen, objetos in rows:
            if imagen is not None:
                img_b64 = base64.b64encode(imagen).decode("utf-8")
            else:
                img_b64 = ""
            historial.append(
                {
                    "tipo": tipo,
                    "objetos": objetos,
                    "fecha": fecha.strftime("%Y-%m-%d"),
                    "hora": str(hora),
                    "ip": ip,
                    "imagen": img_b64,
                }
            )
        return render_template("historial.html", historial=historial)
    except Exception as e:
        print("Error en /historial:", e)
        return "Error interno en el servidor: " + str(e), 500


if __name__ == "__main__":
    app.run(debug=True)
