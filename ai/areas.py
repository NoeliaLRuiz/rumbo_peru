"""Áreas vocacionales y clasificación de programas de estudio.

Cada área tiene un perfil RIASEC (modelo de intereses de Holland):
R = Realista, I = Investigador, A = Artístico, S = Social, E = Emprendedor, C = Convencional.
Los pesos (0-3) dicen cuánto se parece el área a cada tipo de interés.
"""
import re
import unicodedata

AREAS = {
    "tecnologia": {
        "nombre": "Tecnología e informática",
        "riasec": {"R": 1, "I": 3, "A": 0, "S": 0, "E": 0, "C": 2},
        "claves": ["INFORMATIC", "SISTEMAS", "SOFTWARE", "COMPUTACION", "COMPUTO", "DATOS",
                   "REDES", "TECNOLOGIAS DE LA INFORMACION", "TECNOLOGIAS DE INFORMACION",
                   "PROGRAMACION", "CIBER", "TELECOMUNICA", "INTELIGENCIA ARTIFICIAL", "ROBOTIC",
                   "COMPUTADORA", "OFIMATICA", "DIGITACION", "DIGITADOR"],
    },
    "salud": {
        "nombre": "Salud",
        "riasec": {"R": 1, "I": 3, "A": 0, "S": 3, "E": 0, "C": 1},
        "claves": ["ENFERMERI", "MEDICINA", "MEDICO", "OBSTETRI", "FARMAC", "ODONTO", "ESTOMATOL",
                   "NUTRICION", "PSICOLOG", "LABORATORIO CLINICO", "TECNOLOGIA MEDICA", "FISIOTERAPIA",
                   "TERAPIA", "PROTESIS DENTAL", "OPTOMETR", "RADIOLOG", "SALUD"],
    },
    "educacion": {
        "nombre": "Educación y docencia",
        "riasec": {"R": 0, "I": 1, "A": 2, "S": 3, "E": 1, "C": 0},
        "claves": ["EDUCACION", "PEDAGOG", "DOCENTE", "DOCENCIA", "FORMACION DOCENTE"],
    },
    "agro_ambiente": {
        "nombre": "Agro, ambiente y recursos naturales",
        "riasec": {"R": 3, "I": 2, "A": 0, "S": 0, "E": 1, "C": 0},
        "claves": ["AGRO", "AGRICOL", "AGRONOM", "PECUARI", "ZOOTECN", "VETERINAR", "FOREST",
                   "AMBIENT", "ACUICULT", "PESQUER", "PESCA", "BIOLOG", "ECOLOG", "RECURSOS NATURALES",
                   "CULTIVO", "CRIANZA", "COSECHA", "AGRARIA", "AGRICULTURA", "GANADER"],
    },
    "construccion": {
        "nombre": "Arquitectura y construcción",
        "riasec": {"R": 3, "I": 1, "A": 2, "S": 0, "E": 0, "C": 1},
        "claves": ["ARQUITECTURA", "CIVIL", "CONSTRUCCION", "EDIFICACION", "TOPOGRAF", "URBANIS",
                   "INTERIORES", "SANITARI", "ALBANIL"],
    },
    "comunicacion": {
        "nombre": "Comunicación, idiomas y medios",
        "riasec": {"R": 0, "I": 0, "A": 3, "S": 2, "E": 2, "C": 0},
        "claves": ["COMUNICACION", "PERIODIS", "PUBLICIDAD", "PUBLICITARI", "AUDIOVISUAL", "TRADUCC",
                   "IDIOMA", "LINGU", "LITERATURA", "RELACIONES PUBLICAS", "INGLES"],
    },
    "arte_diseno": {
        "nombre": "Arte y diseño",
        "riasec": {"R": 1, "I": 0, "A": 3, "S": 0, "E": 1, "C": 0},
        "claves": ["ARTE", "ARTES", "ARTISTIC", "DISENO", "MUSICA", "DANZA", "TEATRO", "ACTUACION",
                   "PINTURA", "ESCULTURA", "FOTOGRAF", "MODAS", "ANIMACION", "CINE", "CERAMICA",
                   "MANUALIDADES", "JOYERIA", "DECORACION", "RESTAURACION", "ESTAMPADO", "VIDRIERIA"],
    },
    "derecho_sociales": {
        "nombre": "Derecho, ciencias sociales y humanidades",
        "riasec": {"R": 0, "I": 2, "A": 1, "S": 3, "E": 2, "C": 0},
        "claves": ["DERECHO", "CIENCIAS? POLITICA", "JURIDIC", "SOCIOLOG", "ANTROPOLOG", "TRABAJO SOCIAL",
                   "RELACIONES INTERNACIONALES", "HISTORIA", "FILOSOF", "GEOGRAF", "ARQUEOLOG",
                   "TEOLOG", "POLICIA", "CIENCIAS SOCIALES", "SERVICIOS SOCIALES", "SERVICIO SOCIALES",
                   "CUIDADO DE NINOS", "ADULTO MAYOR", "ASISTENTE DE NINOS"],
    },
    "servicios": {
        "nombre": "Turismo, gastronomía y servicios",
        "riasec": {"R": 2, "I": 0, "A": 1, "S": 2, "E": 2, "C": 0},
        "claves": ["TURISMO", "HOTEL", "HOSTELER", "GASTRONOM", "COCINA", "CULINARI", "PANADER",
                   "PASTELER", "RESTAURANT", "GUIA", "PELUQU", "ESTILISMO", "COSMET", "BARBER",
                   "COSTURA", "CONFECCION", "PRENDAS", "BELLEZA", "DEPORT", "BORDADO", "TEJEDUR",
                   "CORTE Y ENSAMBLAJE", "PATRONAJE", "ESTETIC", "COSMIATR", "BAR", "BARMAN",
                   "COCTEL", "SERVICIO DE MESA", "REPOSTER", "TEJIDO", "SASTRER", "CORTE DE CABELLO",
                   "CALZADO", "CUERO", "TRANSPORTE"],
    },
    "negocios": {
        "nombre": "Administración, negocios y finanzas",
        "riasec": {"R": 0, "I": 1, "A": 0, "S": 1, "E": 3, "C": 3},
        "claves": ["ADMINISTRA", "CONTAB", "ECONOM", "FINANZ", "BANCA", "BANCARI", "MARKETING",
                   "NEGOCIOS", "COMERCI", "GESTION", "SECRETARI", "LOGISTIC", "RECURSOS HUMANOS",
                   "EMPRESA", "AUDITOR", "SEGUROS", "ADUANA", "ALMACEN", "VENTA", "CAJERO",
                   "ASISTENCIA DE DIRECCION"],
    },
    "ingenieria": {
        "nombre": "Ingeniería, industria y oficios técnicos",
        "riasec": {"R": 3, "I": 2, "A": 0, "S": 0, "E": 0, "C": 1},
        "claves": ["INGENIERIA", "MECANIC", "ELECTRIC", "ELECTRON", "ELECTROTECN", "MECATRON",
                   "INDUSTRIA", "MINA", "MINER", "METALUR", "QUIMIC", "PETROL", "MAQUINARIA",
                   "SOLDADURA", "AUTOMOTRIZ", "PRODUCCION", "ALIMENTARIA", "ALIMENTOS", "TEXTIL",
                   "CARPINTER", "MANTENIMIENTO", "REFRIGERACION", "ENERGI", "MECANCIA", "MOTOS",
                   "EQUIPOS PESADOS", "EBANISTER", "PROCESAMIENTO DE PRODUCTOS", "LACTEOS"],
    },
    "ciencias": {
        "nombre": "Ciencias básicas",
        "riasec": {"R": 1, "I": 3, "A": 0, "S": 0, "E": 0, "C": 2},
        "claves": ["MATEMAT", "FISICA", "ESTADIST", "CIENCIAS", "ASTRONOM"],
    },
}

# Respaldo: familia de programa de SUNEDU -> área (cuando ninguna palabra clave coincide)
FAMILIA_SUNEDU = {
    "SALUD": "salud", "INFORMATICA": "tecnologia", "ADMINISTRACION Y COMERCIO": "negocios",
    "ARQUITECTURA Y CONSTRUCCION": "construccion", "INDUSTRIA Y PRODUCCION": "ingenieria",
    "INGENIERIA Y PROFESIONES AFINES": "ingenieria", "DERECHO": "derecho_sociales",
    "CIENCIAS SOCIALES Y DEL COMPORTAMIENTO": "derecho_sociales", "HUMANIDADES": "derecho_sociales",
    "PERIODISMO E INFORMACION": "comunicacion", "IDIOMAS": "comunicacion", "ARTE": "arte_diseno",
    "AGRICULTURA": "agro_ambiente", "MEDIO AMBIENTE": "agro_ambiente", "VETERINARIA": "agro_ambiente",
    "PESCA": "agro_ambiente", "SILVICULTURA": "agro_ambiente", "CIENCIAS BIOLOGICAS Y AFINES": "agro_ambiente",
    "CIENCIAS FISICAS Y QUIMICAS": "ciencias", "MATEMATICAS Y ESTADISTICA": "ciencias",
    "SERVICIOS PERSONALES": "servicios", "SERVICIOS DE TRANSPORTE": "servicios",
    "SERVICIOS DE HIGIENE Y SALUD OCUPACIONAL": "salud", "BIENESTAR": "derecho_sociales",
}

_PATRONES = {a: re.compile(r"\b(" + "|".join(v["claves"]) + r")") for a, v in AREAS.items()}


def normalizar(texto: str) -> str:
    """Mayúsculas y sin tildes: 'Diseño Gráfico' -> 'DISENO GRAFICO'."""
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto.upper()).strip()


def clasificar(programa: str, familia: str = "") -> str:
    """Devuelve el id del área de un programa. El orden de AREAS importa:
    'ARQUITECTURA DE PLATAFORMAS TI' cae en tecnología antes que en construcción."""
    nombre = normalizar(programa)
    for area, patron in _PATRONES.items():
        if patron.search(nombre):
            return area
    return FAMILIA_SUNEDU.get(normalizar(familia), "otros")


ICONOS = {
    "tecnologia": "💻", "salud": "🩺", "educacion": "📚", "agro_ambiente": "🌱", "construccion": "🏗️",
    "comunicacion": "🎙️", "arte_diseno": "🎨", "derecho_sociales": "⚖️", "servicios": "🍳",
    "negocios": "📈", "ingenieria": "⚙️", "ciencias": "🔬",
}


def nombre_area(area_id: str) -> str:
    return AREAS.get(area_id, {}).get("nombre", "Otros")


def icono_area(area_id: str) -> str:
    return ICONOS.get(area_id, "🎓")
