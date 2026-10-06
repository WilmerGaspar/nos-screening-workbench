# NOS Screening Workbench v0.3 — interfaz primero

## Por qué cambió

Varias fuentes independientes apuntan a lo mismo: a 5–50 µm la κ del recubrimiento casi no mueve la
temperatura; lo que decide es la interfaz (desajuste de CTE, adherencia, solidez de la capa).
Fuentes: revisión de Wang, Lu y Bai (J Mater Sci: Mater Electron, 2026), preprint de Scarpa
et al. con datos de Infineon (arXiv:2608.08363) e ingenieros de materiales consultados en
octubre de 2026 (aporte práctico, no publicado).

## Qué cambió

| Antes (v0.2) | Ahora (v0.3) |
|---|---|
| κ valía 40 % del score | κ no puntúa: se calcula qué fracción del ΔT toma la capa y qué κ necesita la película |
| Umbral fijo de 25 W/m·K | κ necesaria según TIM y espesor reales (editables) |
| "Sitio de la capa" era solo texto | El sitio define contra qué materiales se mide el ΔCTE |
| Sin metalización del chip | Nuevo sitio: metalización del pad (Scarpa et al.) |
| Sin alertas de química | Alertas para el corte: Ni/Fe hacia Cu, óxido de Al/Ti |
| Pesos 30/30/40 fijos | 25/35/40 editables + estabilidad del ranking (120 combinaciones) |
| Ficha de cupón térmica | Ficha en dos etapas: choque rápido + ciclado con checkpoints |
| Sin forma de contactarte | Botón "Solicitar estudio o cupón" (abre un correo con la configuración) |
| Sin coincidencia → todo el catálogo | Sin coincidencia → aviso y nada más |

Demo por defecto (7 fases citadas, cold plate, 20 µm, 50 W, TIM 50 µm a 4 W/m·K):
NiAl primero (`proceed_to_coupon`), 0.11 K de la capa contra 6.25 K del TIM, primero en el
92 % de las combinaciones de pesos. FeAl queda último en el camino de calor, pero en
bond-coat pasa a `proceed_to_coupon`.

## Datos que hay que completar (no se inventaron)

- Los valores de CTE de NiAl, CoAl, FeAl y Ni3Al en `thermal.py` no tienen DOI en el repo.
  La app los marca como `cte_uncited`. Conviene buscar la fuente y agregar `cte_source`.
- FeTi, NiGa y Ni3Ga no tienen CTE: su dictamen es `coupon_cte_unknown`.
- El TIM por defecto (50 µm, 4 W/m·K) es un supuesto editable.

## Cómo subirlo a GitHub (sin terminal)

1. Abre https://github.com/WilmerGaspar/nos-screening-workbench
2. **Add file → Upload files**.
3. Arrastra todos los archivos de este paquete. La carpeta `tests` arrástrala como carpeta
   para que `tests/test_reliability.py` quede en su lugar.
4. Mensaje del commit: `v0.3 interface-first`. **Commit changes**.
5. Streamlit Cloud debería redesplegar solo en unos minutos. Si no, en share.streamlit.io
   abre la app → **Reboot**.
6. Prueba la demo: Ejecutar screening → revisa la tabla, la estabilidad y la ficha de cupón.

Pruebas: `python3 tests/test_scoring.py && python3 tests/test_reliability.py`
