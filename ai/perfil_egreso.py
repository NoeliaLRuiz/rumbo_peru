"""Perfil de egreso REFERENCIAL de una carrera según su nivel (universitario, técnico o técnico-productivo).

No describe a una institución en particular: cada una publica su perfil oficial en su web.
Usa Claude con salida estructurada; sin API key, usa una plantilla por nivel y área.
"""
import json
import os

from ai.areas import nombre_area
from ai.perfiles_carreras import buscar_carrera

MODELO = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")

ESQUEMA = {
    "type": "object",
    "properties": {
        "resumen": {"type": "string", "description": "1-2 oraciones: quién es el egresado"},
        "sabras_hacer": {"type": "array", "items": {"type": "string"}, "description": "4 competencias concretas"},
        "donde_trabajar": {"type": "array", "items": {"type": "string"}, "description": "3 lugares de trabajo en el Perú"},
        "enfoque": {"type": "string", "description": "Una frase: más práctico/operativo o más analítico/de gestión"},
    },
    "required": ["resumen", "sabras_hacer", "donde_trabajar", "enfoque"],
    "additionalProperties": False,
}

SISTEMA = """Eres un orientador vocacional peruano. Describe el perfil de egreso TÍPICO de una carrera
en el Perú para el nivel indicado, en español claro para un estudiante de secundaria.
Sé concreto y realista; no menciones instituciones, sueldos ni cifras."""

_PLANTILLA = {
    "universitaria": {
        "enfoque": "Formación amplia: teoría, investigación y gestión.",
        "sabras": ["Analizar problemas complejos de tu campo con base científica",
                   "Diseñar, planificar y evaluar proyectos", "Liderar equipos y tomar decisiones",
                   "Investigar y seguir estudiando un posgrado"],
        "donde": ["Empresas privadas e instituciones del Estado", "Consultoras y ONG", "Tu propio emprendimiento"],
    },
    "pedagógica": {
        "enfoque": "Formación docente: pedagogía, didáctica y práctica en aulas reales.",
        "sabras": ["Planificar y conducir sesiones de aprendizaje", "Evaluar el progreso de tus estudiantes",
                   "Atender la diversidad e inclusión en el aula", "Trabajar con las familias y la comunidad"],
        "donde": ["Colegios públicos y privados", "Programas educativos del Estado y ONG", "Proyectos de educación comunitaria"],
    },
    "técnica": {
        "enfoque": "Formación práctica: sales a trabajar más rápido, haciendo.",
        "sabras": ["Ejecutar procesos técnicos de tu especialidad", "Usar equipos, herramientas y software del sector",
                   "Resolver problemas del día a día en el trabajo", "Apoyar la supervisión de operaciones"],
        "donde": ["Empresas medianas y grandes del sector", "Instituciones públicas", "Tu propio negocio o taller"],
    },
    "técnico-productiva": {
        "enfoque": "Formación corta y aplicada a un oficio.",
        "sabras": ["Realizar las tareas de un oficio con seguridad", "Usar las herramientas del oficio",
                   "Atender clientes y cumplir encargos", "Empezar un emprendimiento pequeño"],
        "donde": ["Talleres y negocios locales", "Empresas que contratan personal operativo", "Trabajo independiente"],
    },
}


def _reglas(programa: str, nivel: str, area_id: str) -> dict:
    """Sin IA: perfil de la carrera desde el catálogo (ai/perfiles_carreras.py);
    si la carrera no está en el catálogo, una plantilla general por nivel."""
    p = _PLANTILLA.get(nivel, _PLANTILLA["técnica"])
    carrera = buscar_carrera(programa)
    if carrera:
        nivel_alto = nivel in ("universitaria", "pedagógica")
        sabras = carrera.get("uni" if nivel_alto else "tec") or carrera.get("tec" if nivel_alto else "uni")
        return {"resumen": carrera["resumen"], "sabras_hacer": sabras, "donde_trabajar": carrera["donde"],
                "enfoque": p["enfoque"], "fuente": "catálogo", "carrera": carrera["nombre"]}
    return {
        "resumen": f"Quien egresa de {programa.title()} ({nivel}) trabaja en el campo de "
                   f"{nombre_area(area_id).lower()}.",
        "sabras_hacer": p["sabras"], "donde_trabajar": p["donde"], "enfoque": p["enfoque"], "fuente": "plantilla",
    }


def perfil_egreso(programa: str, nivel: str, area_id: str) -> dict:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return _reglas(programa, nivel, area_id)
    try:
        import anthropic

        resp = anthropic.Anthropic().beta.messages.create(
            model=MODELO,
            max_tokens=2000,
            system=SISTEMA,
            messages=[{"role": "user", "content": json.dumps(
                {"carrera": programa, "nivel": nivel, "area": nombre_area(area_id),
                 # el catálogo sirve de referencia para que la IA no se aleje de la profesión real
                 "referencia": _reglas(programa, nivel, area_id)}, ensure_ascii=False)}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": ESQUEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if resp.stop_reason != "end_turn":
            raise RuntimeError(f"stop_reason={resp.stop_reason}")
        data = json.loads(next(b.text for b in resp.content if b.type == "text"))
        data["fuente"] = "ia"
        return data
    except Exception:
        return _reglas(programa, nivel, area_id)
