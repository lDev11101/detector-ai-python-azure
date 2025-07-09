from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
from dotenv import load_dotenv
import mysql.connector
import os
import base64

# Cargar variables de entorno
load_dotenv()

# Configuración de la app
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Función para conectarse a la base de datos
def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )


# Función para guardar el historial en la base de datos
def guardar_historial(tipo_residuo, ip, imagen_path, objetos_detectados):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    fecha = now.date()
    hora = now.time()
    with open(imagen_path, "rb") as f:
        imagen = f.read()
    sql = """
        INSERT INTO historial_residuos 
        (tipo_residuo, fecha, hora, ip, imagen, objetos_detectados) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (tipo_residuo, fecha, hora, ip, imagen, objetos_detectados))
    conn.commit()
    cursor.close()
    conn.close()


# Ruta principal
@app.route("/")
def index():
    return render_template("index.html")


# Ruta para analizar imagen
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

    # Importar funciones de análisis
    from utils.detector_ai import analizar_imagen, obtener_objetos_detectados

    resultado = analizar_imagen(filepath)
    objetos_detectados = obtener_objetos_detectados(filepath)

    tipos_map = {
        "→ Residuo ORGÁNICO": "ORGÁNICOS",
        "→ Residuo INORGÁNICO": "INORGÁNICOS",
        "→ Puede contener residuos ORGÁNICOS e INORGÁNICOS": "ORGÁNICOS e INORGÁNICOS",
    }
    tipo = tipos_map.get(resultado)

    if tipo:
        ip = request.remote_addr
        guardar_historial(tipo, ip, filepath, objetos_detectados)

    os.remove(filepath)
    return jsonify({"resultado": resultado})


# Ruta para mostrar historial
@app.route("/historial")
def historial():
    try:
        page = int(request.args.get("page", 1))
        per_page = 8
        offset = (page - 1) * per_page

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM historial_residuos")
        total = cursor.fetchone()[0]
        total_pages = (total + per_page - 1) // per_page

        cursor.execute(
            """
            SELECT tipo_residuo, fecha, hora, ip, imagen, objetos_detectados 
            FROM historial_residuos 
            ORDER BY id DESC 
            LIMIT %s OFFSET %s
        """,
            (per_page, offset),
        )
        rows = cursor.fetchall()

        historial = []
        for tipo, fecha, hora, ip, imagen, objetos in rows:
            img_b64 = base64.b64encode(imagen).decode("utf-8") if imagen else ""
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

        cursor.close()
        conn.close()

        return render_template(
            "historial.html", historial=historial, page=page, total_pages=total_pages
        )

    except Exception as e:
        print("Error en /historial:", e)
        return "Error interno en el servidor: " + str(e), 500


# Ejecutar la app
if __name__ == "__main__":
    app.run()
