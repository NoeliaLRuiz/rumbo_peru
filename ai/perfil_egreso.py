"""Perfil de egreso REFERENCIAL de una carrera según su nivel (universitario, técnico o técnico-productivo).

No describe a una institución en particular: cada una publica su perfil oficial en su web.
Usa Claude con salida estructurada; sin API key, usa una plantilla por nivel y área.
"""
import json
import os

from ai.areas import nombre_area

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
    p = _PLANTILLA.get(nivel, _PLANTILLA["técnica"])
    return {
        "resumen": f"Quien egresa de {programa.title()} ({nivel}) trabaja en el campo de "
                   f"{nombre_area(area_id).lower()}.",
        "sabras_hacer": p["sabras"], "donde_trabajar": p["donde"], "enfoque": p["enfoque"], "fuente": "reglas",
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
                {"carrera": programa, "nivel": nivel, "area": nombre_area(area_id)}, ensure_ascii=False)}],
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
