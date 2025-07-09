import os
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials
from dotenv import load_dotenv

load_dotenv()  # Cargar variables de entorno desde .env

# Configurar el cliente de Azure
subscription_key = os.getenv("API_AZURE")
endpoint = os.getenv("ENDPOINT_AZURE")

client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(subscription_key))

# Palabras clave para clasificación
organico_keywords = [
    # Frutas
    "fruta",
    "manzana",
    "banana",
    "naranja",
    "pera",
    "uva",
    "limón",
    "sandía",
    "melón",
    "fresa",
    "arándano",
    "piña",
    "mango",
    "kiwi",
    "durazno",
    "ciruela",
    "cereza",
    "frambuesa",
    "mora",
    "granada",
    # Verduras
    "verdura",
    "lechuga",
    "tomate",
    "cebolla",
    "papa",
    "zanahoria",
    "maíz",
    "aguacate",
    "palta",
    "ajo",
    "cilantro",
    "apio",
    "espinaca",
    "brócoli",
    "coliflor",
    "calabaza",
    "pepino",
    "chile",
    "pimiento",
    "berenjena",
    "calabacín",
    "rábano",
    "remolacha",
    "alcachofa",
    # Otros alimentos
    "comida",
    "restos",
    "pan",
    "carne",
    "hueso",
    "pescado",
    "pollo",
    "arroz",
    "huevo",
    "lenteja",
    "garbanzo",
    "frijol",
    "soja",
    "tofu",
    "queso",
    "yogur",
    "leche",
    "mantequilla",
    "miel",
    "café",
    "té",
    # Materiales orgánicos
    "planta",
    "hoja",
    "cáscara",
    "pasto",
    "semilla",
    "flor",
    "tallo",
    "raíz",
    "madera",
    "corteza",
    "aserrín",
    "compost",
    "biodegradable",
    "papel",
    "cartón",  # Considerados orgánicos aunque sean procesados
]
inorganico_keywords = [
    # Plásticos
    "plástico",
    "botella",
    "envase",
    "bolsa",
    "film",
    "poliestireno",
    "PVC",
    "PET",
    "tupperware",
    "embalaje",
    "envoltorio",
    "tapón",
    # Metales
    "metal",
    "lata",
    "aluminio",
    "acero",
    "hierro",
    "cobre",
    "bronce",
    "llave",
    "candado",
    "cadena",
    "gancho",
    "clavo",
    "tornillo",
    # Vidrios
    "vidrio",
    "vaso",
    "botella",
    "frasco",
    "espejo",
    "ventana",
    "cristal",
    "lente",
    "gafas",
    "lentes",
    # Electrónicos
    "electrónico",
    "batería",
    "pilas",
    "celular",
    "computadora",
    "televisor",
    "pantalla",
    "ratón",
    "teclado",
    "impresora",
    "cargador",
    "auriculares",
    "disco",
    "usb",
    "cd",
    "dvd",
    "chip",
    # Varios
    "tela",
    "ropa",
    "zapato",
    "bolso",
    "mochila",
    "toalla",
    "sábana",
    "cojín",
    "alfombra",
    "cable",
    "alambre",
    "cerámica",
    "porcelana",
    "ladrillo",
    "cemento",
    "piedra",
    "arena",
    "grava",
    # Juguetes
    "juguete",
    "muñeca",
    "carro",
    "bicicleta",
    "pelota",
    "rompecabezas",
    "legos",
    "consola",
    "videojuego",
    # Utensilios
    "cuchara",
    "tenedor",
    "cuchillo",
    "plato",
    "olla",
    "sartén",
    "taza",
    "termo",
    "cafetera",
    "licuadora",
    "microondas",
    "refrigerador",
]


def obtener_objetos_detectados(image_path):
    try:
        with open(image_path, "rb") as image_stream:
            analysis = client.analyze_image_in_stream(
                image_stream,
                visual_features=[VisualFeatureTypes.objects],
                language="es",
            )
        if hasattr(analysis, "objects") and analysis.objects:
            nombres = [obj.object_property.lower() for obj in analysis.objects]
            return ", ".join(nombres)
        else:
            return "No detectado"
    except Exception as e:
        return f"Error: {e}"


def analizar_imagen(image_path):
    try:
        with open(image_path, "rb") as image_stream:
            analysis = client.analyze_image_in_stream(
                image_stream,
                visual_features=[
                    VisualFeatureTypes.tags,
                    VisualFeatureTypes.description,
                    VisualFeatureTypes.categories,
                ],
                language="es",
            )
        tags_detected = [tag.name.lower() for tag in analysis.tags]
        description_text = ""
        if analysis.description and analysis.description.captions:
            for caption in analysis.description.captions:
                description_text += caption.text.lower() + " "
        organico = any(
            word in tags_detected or word in description_text
            for word in organico_keywords
        )
        inorganico = any(
            word in tags_detected or word in description_text
            for word in inorganico_keywords
        )
        if organico and not inorganico:
            return "→ Residuo ORGÁNICO"
        elif inorganico and not organico:
            return "→ Residuo INORGÁNICO"
        elif organico and inorganico:
            return "→ Puede contener residuos ORGÁNICOS e INORGÁNICOS"
        else:
            return "→ No se pudo determinar el tipo de residuo."
    except Exception as e:
        return f"Error al analizar la imagen: {e}"
