# CLAUDE.md — NOS Screening Workbench

## Cómo trabajar con el usuario

- Responder siempre en español.
- El usuario está estudiando programación: explicar en palabras simples qué se hizo y por qué.
- Revisar el código de terceros (skills, plugins, paquetes) antes de instalarlo.

## El proyecto

App de Streamlit y CLI que hace un pre-filtro reproducible de fases intermetálicas para
recubrimientos: Natural Occurrence Score + encaje de proceso + κ publicada (no se inventa) +
riesgo de interfaz por CTE. Es una capa de screening antes de CALPHAD o de un cupón de ensayo,
no un sustituto. Ver `README.md` y `METHODOLOGY.md`. Licencia CC BY-NC-SA 4.0.

## Comandos

```bash
pip install -r requirements.txt   # el contenedor de la nube no las trae instaladas
streamlit run app.py
for t in tests/test_*.py; do python3 "$t" || break; done   # 4 scripts, sin pytest
```

`MP_API_KEY` (Materials Project) solo hace falta para `cli.py --live`; ver `.env.example`.

## Convenciones

- Mensajes de commit en inglés.
- Cada cambio de comportamiento lleva pruebas en `tests/`; si cambia el método, actualizar
  `METHODOLOGY.md`. Los textos de la interfaz viven en `i18n.py`.

## Memoria entre sesiones

Al terminar una sesión con algo que valga la pena recordar, agregar aquí una entrada corta
(fecha, qué se hizo, qué quedó pendiente) y subirla con el resto de los cambios.

- **2026-11-25** — Se instalaron los skills de `academic-research-skills` (deep-research,
  academic-paper, academic-paper-reviewer, academic-pipeline, sr-screener). Quedan permanentes
  gracias al script de configuración del entorno «Default», fijado al commit `18749d8` del repo
  Imbad0202/academic-research-skills. No se instaló `claude-mem`: en la nube su memoria se borra
  con el contenedor y envía toda la actividad a un modelo observador. Este archivo hace de memoria.
