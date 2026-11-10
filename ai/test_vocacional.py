"""Test de intereses basado en el modelo RIASEC de John Holland.

Las preguntas son de redacción propia. Siguen el formato de los marcadores RIASEC de dominio público
(AFPD; Armstrong y otros, 2008), validados en español por Cupani y otros (2019):
  - una sola actividad concreta por pregunta (sin "o" que mezcle actividades distintas),
  - cada pregunta mide un solo tipo de interés,
  - actividades posibles en la costa, la sierra y la selva (sin suponer computadora ni redes sociales),
  - 4 preguntas por tipo y respuesta de agrado de 1 (no me gusta) a 4 (me encanta).
No son una traducción del instrumento AFPD: para medir con un test validado, usar sus ítems en español.
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
    ("R", "Reparar cosas que se malogran en casa"),
    ("R", "Trabajar en el campo con plantas o animales"),
    ("R", "Construir algo con tus manos, como un mueble o una maqueta"),
    ("R", "Usar herramientas o máquinas para hacer un trabajo"),
    ("I", "Hacer experimentos para descubrir por qué pasa algo"),
    ("I", "Resolver problemas difíciles de matemática"),
    ("I", "Aprender cómo funciona el cuerpo humano"),
    ("I", "Investigar un tema a fondo hasta entenderlo"),
    ("A", "Dibujar o pintar"),
    ("A", "Escribir cuentos, poemas o historias"),
    ("A", "Presentarte en un escenario: actuar, bailar o tocar música"),
    ("A", "Diseñar cómo se ve algo: un afiche, una prenda o un ambiente"),
    ("S", "Explicarle un tema a un compañero que no lo entiende"),
    ("S", "Cuidar a una persona enferma o mayor"),
    ("S", "Participar en actividades para ayudar a tu comunidad"),
    ("S", "Escuchar y aconsejar a alguien que tiene un problema"),
    ("E", "Vender un producto o un servicio"),
    ("E", "Convencer a un grupo de que apoye tu idea"),
    ("E", "Dirigir un grupo como delegado o líder"),
    ("E", "Iniciar tu propio negocio"),
    ("C", "Llevar las cuentas del dinero de un negocio o de tu casa"),
    ("C", "Llevar un registro ordenado de algo, como notas, ventas o inventario"),
    ("C", "Revisar un trabajo con cuidado para encontrar errores"),
    ("C", "Ordenar documentos para que todo esté en su lugar"),
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
