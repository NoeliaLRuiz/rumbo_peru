"""Test de intereses basado en el modelo RIASEC de John Holland.

24 preguntas en 4 secciones temáticas (actividades, lugares de trabajo, temas y otras actividades).
Cada sección tiene 6 preguntas, una por tipo de interés, así el puntaje queda balanceado.

Las preguntas son de redacción propia. Siguen el formato de los marcadores RIASEC de dominio público
(AFPD; Armstrong y otros, 2008), validados en español por Cupani y otros (2019):
  - una sola actividad, lugar o tema concreto por pregunta,
  - cada pregunta mide un solo tipo de interés,
  - posibles en la costa, la sierra y la selva (sin suponer computadora ni redes sociales),
  - respuesta de agrado de 1 (no me gusta) a 4 (me encanta).
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

# (título de la sección, ícono, [(tipo, pregunta, ayuda para palabras poco conocidas)])
SECCIONES_TEST = [
    ("¿Te gustaría hacer estas actividades?", "🛠️", [
        ("R", "Reparar cosas que se malogran en casa", ""),
        ("I", "Hacer experimentos para descubrir por qué pasa algo", ""),
        ("A", "Dibujar o pintar", ""),
        ("S", "Explicarle un tema a un compañero que no lo entiende", ""),
        ("E", "Vender un producto o un servicio", ""),
        ("C", "Llevar las cuentas del dinero de un negocio o de tu casa", ""),
    ]),
    ("¿Te gustaría trabajar en estos lugares?", "🏢", [
        ("R", "Un taller de mecánica o de carpintería", "Lugar donde se reparan o fabrican objetos, vehículos o muebles."),
        ("I", "Un laboratorio de investigación", "Lugar donde se hacen pruebas y análisis para descubrir cosas nuevas."),
        ("A", "Un estudio de diseño o de grabación", "Lugar donde se crean afiches, videos, música o diseños."),
        ("S", "Un centro de salud o una escuela", ""),
        ("E", "Tu propia empresa", "Un negocio que tú diriges y en el que tomas las decisiones."),
        ("C", "Una oficina de contabilidad o un banco", "Lugares donde se registra y controla el dinero."),
    ]),
    ("¿Te gustaría aprender sobre estos temas?", "📚", [
        ("R", "Cómo funcionan los motores y las máquinas", ""),
        ("I", "Cómo funciona el cuerpo humano", ""),
        ("A", "El arte, la música o el teatro", ""),
        ("S", "Cómo aprenden y se sienten las personas", "Es lo que estudian la psicología y la educación."),
        ("E", "Cómo crear y hacer crecer un negocio", ""),
        ("C", "Cómo organizar información de forma ordenada", "Por ejemplo, archivos, registros o bases de datos."),
    ]),
    ("¿Te gustaría hacer estas otras actividades?", "✨", [
        ("R", "Trabajar en el campo con plantas o animales", ""),
        ("I", "Resolver problemas difíciles de matemática", ""),
        ("A", "Presentarte en un escenario: actuar, bailar o tocar música", ""),
        ("S", "Cuidar a una persona enferma o mayor", ""),
        ("E", "Dirigir un grupo como delegado o líder", ""),
        ("C", "Revisar un trabajo con cuidado para encontrar errores", ""),
    ]),
]

# Lista plana de preguntas en orden: sección 1, sección 2, ... (6 por sección)
PREGUNTAS = [(dim, texto) for _, _, items in SECCIONES_TEST for dim, texto, _ in items]
AYUDAS = [ayuda for _, _, items in SECCIONES_TEST for _, _, ayuda in items]
POR_SECCION = 6

OPCIONES = {1: "No me gusta", 2: "Me da igual", 3: "Me gusta", 4: "Me encanta"}

# Respuestas de ejemplo para la demo: estudiante con perfil Social-Investigador (orden R, I, A, S, E, C)
EJEMPLO = [2, 4, 2, 4, 2, 3,
           1, 4, 2, 4, 2, 3,
           2, 4, 1, 4, 2, 3,
           1, 3, 1, 4, 3, 2]


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
