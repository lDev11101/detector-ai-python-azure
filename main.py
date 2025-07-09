from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
from dotenv import load_dotenv
import mysql.connector
import os
import base64
import logging
from functools import wraps

# Configuración inicial de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Configuración de la aplicación Flask
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB límite
app.config["ALLOWED_EXTENSIONS"] = {"png", "jpg", "jpeg", "gif"}

# Crear directorio de uploads si no existe
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# Decorador para manejar errores de la base de datos
def handle_db_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except mysql.connector.Error as err:
            logger.error(f"Database error: {err}")
            return jsonify({"error": "Database operation failed"}), 500
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return jsonify({"error": "Internal server error"}), 500

    return wrapper


# Decorador para manejar errores en rutas
def handle_route_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Route error: {e}")
            return jsonify({"error": str(e)}), 500

    return wrapper


def get_db_connection():
    """Establece y retorna una conexión a la base de datos MySQL.

    Returns:
        mysql.connector.connection: Conexión a la base de datos

    Raises:
        mysql.connector.Error: Si hay un error al conectar a la base de datos
    """
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
    except mysql.connector.Error as err:
        logger.error(f"Database connection error: {err}")
        raise


def allowed_file(filename):
    """Verifica si la extensión del archivo está permitida.

    Args:
        filename (str): Nombre del archivo a verificar

    Returns:
        bool: True si la extensión es permitida, False en caso contrario
    """
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )


@handle_db_errors
def save_history(tipo_residuo, ip, imagen_path, objetos_detectados):
    """Guarda un registro en el historial de residuos.

    Args:
        tipo_residuo (str): Tipo de residuo detectado
        ip (str): Dirección IP del cliente
        imagen_path (str): Ruta al archivo de imagen
        objetos_detectados (str): Lista de objetos detectados

    Raises:
        IOError: Si hay un problema al leer el archivo de imagen
        mysql.connector.Error: Si hay un error en la operación de base de datos
    """
    conn = None
    cursor = None
    try:
        now = datetime.now()
        fecha = now.date()
        hora = now.time()

        with open(imagen_path, "rb") as f:
            imagen = f.read()

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            INSERT INTO historial_residuos 
            (tipo_residuo, fecha, hora, ip, imagen, objetos_detectados) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (tipo_residuo, fecha, hora, ip, imagen, objetos_detectados))
        conn.commit()

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/")
@handle_route_errors
def index():
    """Ruta principal que muestra la página de inicio.

    Returns:
        str: HTML renderizado de la página index.html
    """
    return render_template("index.html")


@app.route("/analizar", methods=["POST"])
@handle_route_errors
def analyze_image():
    """Ruta para analizar una imagen enviada por el usuario.

    Returns:
        JSON: Resultado del análisis o mensaje de error

    Errors:
        400: Si no se envía imagen o el archivo no es válido
        500: Si ocurre un error durante el análisis
    """
    if "imagen" not in request.files:
        logger.warning("No image file in request")
        return jsonify({"error": "No se envió ninguna imagen"}), 400

    file = request.files["imagen"]
    if file.filename == "":
        logger.warning("Empty filename in request")
        return jsonify({"error": "Nombre de archivo vacío"}), 400

    if not allowed_file(file.filename):
        logger.warning(f"Invalid file type: {file.filename}")
        return jsonify({"error": "Tipo de archivo no permitido"}), 400

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Importar funciones de análisis (import diferido para mejor performance)
        from utils.detector_ai import analizar_imagen, obtener_objetos_detectados

        resultado = analizar_imagen(filepath)
        objetos_detectados = obtener_objetos_detectados(filepath)

        tipos_map = {
            "→ Residuo ORGÁNICO": "ORGÁNICOS",
            "→ Residuo INORGÁNICO": "INORGÁNICOS",
            "→ Puede contener residuos ORGÁNICOS e INORGÁNICOS": "ORGÁNICOS e INORGÁNICOS",
        }
        tipo = tipos_map.get(resultado, "DESCONOCIDO")

        if tipo != "DESCONOCIDO":
            ip = request.remote_addr
            save_history(tipo, ip, filepath, objetos_detectados)

        return jsonify(
            {"resultado": resultado, "objetos_detectados": objetos_detectados}
        )

    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        return jsonify({"error": "Error al analizar la imagen"}), 500

    finally:
        if "filepath" in locals() and os.path.exists(filepath):
            os.remove(filepath)


@app.route("/historial")
@handle_route_errors
def historial():
    """Ruta para mostrar el historial de análisis.

    Returns:
        str: HTML renderizado de la página historial.html con los datos

    Errors:
        500: Si ocurre un error al acceder a la base de datos
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = 8
        offset = (page - 1) * per_page

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Obtener conteo total de registros
        cursor.execute("SELECT COUNT(*) AS total FROM historial_residuos")
        total = cursor.fetchone()["total"]
        total_pages = (total + per_page - 1) // per_page

        # Obtener registros paginados
        cursor.execute(
            """
            SELECT tipo_residuo, fecha, hora, ip, imagen, objetos_detectados 
            FROM historial_residuos 
            ORDER BY id DESC 
            LIMIT %s OFFSET %s
        """,
            (per_page, offset),
        )

        historial = []
        for row in cursor.fetchall():
            img_b64 = (
                base64.b64encode(row["imagen"]).decode("utf-8") if row["imagen"] else ""
            )
            historial.append(
                {
                    "tipo": row["tipo_residuo"],
                    "objetos": row["objetos_detectados"],
                    "fecha": row["fecha"].strftime("%Y-%m-%d"),
                    "hora": str(row["hora"]),
                    "ip": row["ip"],
                    "imagen": img_b64,
                }
            )

        return render_template(
            "historial.html", historial=historial, page=page, total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error showing history: {e}")
        return jsonify({"error": "Error al obtener el historial"}), 500

    finally:
        if "cursor" in locals():
            cursor.close()
        if "conn" in locals():
            conn.close()


@app.errorhandler(404)
def not_found_error(error):
    """Manejador de errores para páginas no encontradas (404)."""
    logger.warning(f"404 error: {error}")
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    """Manejador de errores internos del servidor (500)."""
    logger.error(f"500 error: {error}")
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run()
