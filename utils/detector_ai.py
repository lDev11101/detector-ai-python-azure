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
    "fruta",
    "verdura",
    "comida",
    "restos",
    "planta",
    "hoja",
    "pan",
    "cáscara",
    "pasto",
    "carne",
    "hueso",
    "pescado",
    "pollo",
    "arroz",
    "semilla",
    "limón",
    "rostro",
    "persona",
]
inorganico_keywords = [
    "plástico",
    "botella",
    "metal",
    "lata",
    "vidrio",
    "papel",
    "cartón",
    "tela",
    "aluminio",
    "batería",
    "pilas",
    "envase",
    "bolsa",
    "lata",
    "electrónico",
    "cuaderno",
    "lentes",
    "gafas",
]


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
