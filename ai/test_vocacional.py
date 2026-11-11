"""Test de intereses basado en el modelo RIASEC de John Holland.

36 preguntas, 6 por cada tipo de interés (Realista, Investigativa, Artística, Social, Emprendedora
y Convencional), redactadas por la founder. Se responden con una escala de 1 (no me interesa) a 5
(me interesa mucho).

Se presentan en 6 partes, una por tipo de interés, con nombres amigables (Construir y explorar,
Investigar y descubrir, Crear e imaginar, Ayudar y conectar, Liderar y emprender, Organizar y planificar).
"""
from ai.areas import AREAS

INSTRUCCIONES = ("Lee cada afirmación y señala qué tanto te interesaría realizar esa actividad, "
                 "independientemente de si consideras que tienes habilidad para hacerla.")

DIMENSIONES = {
    "R": ("Realista", "Te interesan las actividades prácticas, técnicas y de construcción."),
    "I": ("Investigativa", "Te interesa investigar, analizar y resolver problemas."),
    "A": ("Artística", "Te interesa crear, diseñar y expresar ideas."),
    "S": ("Social", "Te interesa ayudar, enseñar y trabajar con personas."),
    "E": ("Emprendedora", "Te interesa liderar, organizar iniciativas y desarrollar proyectos."),
    "C": ("Convencional", "Te interesa organizar, registrar y administrar información."),
}

# Afirmaciones por dimensión, en el orden del instrumento original (1-36)
AFIRMACIONES = {
    "R": ["Me gustaría construir o ensamblar objetos utilizando herramientas y materiales.",
          "Disfrutaría realizar actividades que impliquen reparar máquinas o equipos.",
          "Me interesaría participar en proyectos de construcción de viviendas o espacios.",
          "Me gustaría aprender a manejar equipos tecnológicos o maquinaria especializada.",
          "Disfrutaría realizar experimentos prácticos para comprobar cómo funciona un objeto.",
          "Me interesaría trabajar en actividades que requieran manipular materiales y obtener resultados concretos."],
    "I": ["Me gustaría investigar por qué ocurren determinados fenómenos naturales.",
          "Disfrutaría resolver problemas matemáticos o científicos que representen un desafío.",
          "Me interesaría analizar información para encontrar explicaciones o conclusiones.",
          "Me gustaría realizar investigaciones sobre el funcionamiento del cuerpo humano.",
          "Disfrutaría utilizar datos y evidencias para comprobar si una idea es correcta.",
          "Me interesaría aprender cómo se desarrollan nuevos conocimientos científicos o tecnológicos."],
    "A": ["Me gustaría diseñar espacios, edificios u objetos que tengan una apariencia original.",
          "Disfrutaría crear ilustraciones, fotografías, videos u otras producciones visuales.",
          "Me interesaría desarrollar propuestas creativas para solucionar problemas cotidianos.",
          "Me gustaría participar en proyectos relacionados con la música, el teatro o las artes visuales.",
          "Disfrutaría combinar colores, formas y materiales para crear composiciones.",
          "Me interesaría desarrollar ideas propias y transformarlas en proyectos creativos."],
    "S": ["Me gustaría orientar a otras personas cuando tengan dificultades para aprender.",
          "Disfrutaría participar en actividades que contribuyan al bienestar de mi comunidad.",
          "Me interesaría escuchar y ayudar a personas que atraviesan situaciones difíciles.",
          "Me gustaría explicar temas que conozco para facilitar el aprendizaje de otros.",
          "Disfrutaría trabajar en equipo para alcanzar objetivos compartidos.",
          "Me interesaría participar en proyectos relacionados con la salud y el bienestar de las personas."],
    "E": ["Me gustaría dirigir un equipo para desarrollar un proyecto.",
          "Disfrutaría presentar mis ideas y convencer a otras personas sobre su importancia.",
          "Me interesaría crear un negocio o desarrollar un emprendimiento propio.",
          "Me gustaría organizar actividades y coordinar responsabilidades entre varias personas.",
          "Disfrutaría negociar y buscar acuerdos para resolver diferentes situaciones.",
          "Me interesaría asumir responsabilidades en proyectos donde sea necesario tomar decisiones."],
    "C": ["Me gustaría organizar documentos y mantener información clasificada.",
          "Disfrutaría trabajar con tablas, registros y bases de datos.",
          "Me interesaría revisar información para detectar errores o inconsistencias.",
          "Me gustaría llevar el control de presupuestos, gastos o recursos de un proyecto.",
          "Disfrutaría planificar actividades siguiendo procedimientos y pasos establecidos.",
          "Me interesaría utilizar herramientas digitales para organizar información y realizar tareas administrativas."],
}

ORDEN = ["R", "I", "A", "S", "E", "C"]

# 6 partes, una por dimensión, en el orden del instrumento original (preguntas 1-6, 7-12, ..., 31-36)
NOMBRES_PARTE = {"R": "Construir y explorar", "I": "Investigar y descubrir", "A": "Crear e imaginar",
                 "S": "Ayudar y conectar", "E": "Liderar y emprender", "C": "Organizar y planificar"}
ICONOS_PARTE = {"R": "🛠️", "I": "🔬", "A": "🎨", "S": "🤝", "E": "🚀", "C": "📋"}  # respaldo en texto
ICONOS_3D_PARTE = {"R": "parte_construir", "I": "parte_investigar", "A": "parte_crear",
                   "S": "parte_ayudar", "E": "parte_liderar", "C": "parte_organizar"}  # app/iconos/*.png
SECCIONES_TEST = [(NOMBRES_PARTE[d], ICONOS_PARTE[d], [(d, texto, "") for texto in AFIRMACIONES[d]]) for d in ORDEN]
ICONOS_3D = [ICONOS_3D_PARTE[d] for d in ORDEN]

# Lista plana de preguntas en el orden en que se muestran (6 por parte)
PREGUNTAS = [(dim, texto) for _, _, items in SECCIONES_TEST for dim, texto, _ in items]
AYUDAS = [ayuda for _, _, items in SECCIONES_TEST for _, _, ayuda in items]
POR_SECCION = 6

OPCIONES = {1: "1 · No me interesa", 2: "2 · Me interesa poco", 3: "3 · Me interesa moderadamente",
            4: "4 · Me interesa bastante", 5: "5 · Me interesa mucho"}
ESCALA_MAX = max(OPCIONES)

# Respuestas de ejemplo para la demo: estudiante con perfil Social-Investigativo (6 por dimensión, orden R I A S E C)
EJEMPLO = ([2, 1, 2, 2, 1, 2] + [5, 4, 5, 5, 4, 5] + [2, 2, 1, 2, 1, 2] +
           [5, 5, 4, 5, 5, 4] + [2, 3, 2, 2, 3, 2] + [3, 3, 4, 3, 3, 4])


def puntajes(respuestas: list[int]) -> dict[str, float]:
    """Promedio por dimensión, escalado a 0-100 (1 = 0 y 5 = 100)."""
    suma = {d: 0 for d in DIMENSIONES}
    cuenta = {d: 0 for d in DIMENSIONES}
    for (dim, _), r in zip(PREGUNTAS, respuestas):
        suma[dim] += r
        cuenta[dim] += 1
    return {d: round((suma[d] / cuenta[d] - 1) / (ESCALA_MAX - 1) * 100, 1) for d in DIMENSIONES}


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
