"""Test de intereses basado en el modelo RIASEC de John Holland.

Las preguntas son de redacción propia (no copian ningún test comercial).
Cada respuesta va de 1 (no me gusta nada) a 4 (me encanta).
"""
from ai.areas import AREAS

DIMENSIONES = {
    "R": ("Realista", "Te gusta trabajar con las manos, herramientas, máquinas, plantas o animales."),
    "I": ("Investigador", "Te gusta entender cómo funcionan las cosas, analizar y resolver problemas."),
    "A": ("Artístico", "Te gusta crear, expresarte y trabajar con ideas originales."),
    "S": ("Social", "Te gusta ayudar, enseñar y cuidar a otras personas."),
    "E": ("Emprendedor", "Te gusta liderar, convencer, vender y tomar decisiones."),
    "C": ("Convencional", "Te gusta el orden, los datos, los números y seguir procesos claros."),
}

PREGUNTAS = [
    ("R", "Reparar un aparato o una bicicleta que se malogró"),
    ("R", "Trabajar al aire libre: en el campo, una obra o con animales"),
    ("R", "Armar, construir o fabricar algo con mis propias manos"),
    ("R", "Manejar máquinas, herramientas o vehículos"),
    ("I", "Hacer experimentos para descubrir por qué pasa algo"),
    ("I", "Resolver problemas de matemáticas o acertijos de lógica"),
    ("I", "Leer o ver videos sobre ciencia, el cuerpo humano o la tecnología"),
    ("I", "Investigar un tema a fondo hasta entenderlo bien"),
    ("A", "Dibujar, pintar, diseñar o tomar fotos"),
    ("A", "Escribir historias, poemas o contenido para redes"),
    ("A", "Tocar un instrumento, cantar, bailar o actuar"),
    ("A", "Decorar espacios o darle tu propio estilo a tu ropa"),
    ("S", "Explicarle una tarea a un compañero que no la entiende"),
    ("S", "Cuidar a alguien que está enfermo o necesita ayuda"),
    ("S", "Participar en voluntariados o ayudar en mi comunidad"),
    ("S", "Escuchar a mis amigos cuando tienen un problema"),
    ("E", "Organizar un evento, una actividad o un negocio pequeño"),
    ("E", "Convencer a otros de una idea o vender un producto"),
    ("E", "Ser delegado, líder de grupo o representante"),
    ("E", "Negociar y tomar decisiones aunque haya riesgo"),
    ("C", "Llevar las cuentas o el control de gastos"),
    ("C", "Ordenar información en tablas, listas o archivos"),
    ("C", "Seguir instrucciones paso a paso con mucho cuidado"),
    ("C", "Usar Excel o programas para organizar datos"),
]

OPCIONES = {1: "No me gusta", 2: "Me da igual", 3: "Me gusta", 4: "Me encanta"}

# Respuestas de ejemplo para la demo (estudiante con perfil Social-Investigador)
EJEMPLO = [2, 1, 2, 1, 4, 3, 4, 3, 2, 2, 1, 2, 4, 4, 3, 4, 2, 2, 3, 1, 2, 3, 3, 2]


def puntajes(respuestas: list[int]) -> dict[str, float]:
    """Promedio por dimensión, escalado a 0-100."""
    suma = {d: 0 for d in DIMENSIONES}
    cuenta = {d: 0 for d in DIMENSIONES}
    for (dim, _), r in zip(PREGUNTAS, respuestas):
        suma[dim] += r
        cuenta[dim] += 1
    return {d: round((suma[d] / cuenta[d] - 1) / 3 * 100, 1) for d in DIMENSIONES}


def codigo_holland(p: dict[str, float]) -> str:
    """Las tres dimensiones más altas, p. ej. 'SIC'."""
    return "".join(sorted(p, key=p.get, reverse=True)[:3])


def ranking_areas(p: dict[str, float]) -> list[tuple[str, float]]:
    """Afinidad de 0 a 100 con cada área: promedio de los puntajes ponderado por el perfil del área."""
    res = []
    for area_id, area in AREAS.items():
        pesos = area["riasec"]
        afinidad = sum(p[d] * w for d, w in pesos.items()) / sum(pesos.values())
        res.append((area_id, round(afinidad, 1)))
    return sorted(res, key=lambda x: x[1], reverse=True)
