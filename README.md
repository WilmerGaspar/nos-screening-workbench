# NOS Screening Workbench

Pre-filtro reproducible de fases intermetálicas para recubrimientos.

Repo: https://github.com/WilmerGaspar/nos-screening-workbench

Combina un **Natural Occurrence Score** (estabilidad + módulos + abundancia + evidencia) con:

- encaje de proceso (PVD / HVOF / electrodeposición)
- κ publicado (Terada 1995/2002) — no se inventa
- \(R_{\mathrm{coat}} = t/(\kappa A)\) y cota inferior de \(T_j\)

No sustituye CALPHAD, un TIM comercial ni un cupón de interfaz.

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

```bash
python3 tests/test_scoring.py && python3 tests/test_reliability.py

python3 cli.py --elements cited7 --process pvd --temp 150 \
  --application si_power_module --substrate Cu --die Si --site cold_plate \
  --thickness-um 20 --power-w 50 --tim-kappa 4 --tim-um 50
```

API live (opcional):

```bash
export MP_API_KEY="..."     # https://next-gen.materialsproject.org/api
python3 cli.py --elements Ni,Al --process thermal_spray --temp 600 --live
```

## Qué hace la v0.3 (interfaz primero)

En capas de 5–50 µm la κ del recubrimiento casi no mueve la temperatura: con 20 µm, 1 cm², 50 W
y un TIM de 50 µm a 4 W/m·K, NiAl aporta ~0.11 K frente a ~6.25 K del TIM. Por eso la v0.3:

- **κ deja de puntuar.** Se calcula qué fracción del ΔT (recubrimiento + TIM) toma la capa y qué κ
  necesita la película para quedarse bajo ese límite (por defecto 10 %). La κ bulk es cota superior.
- **El sitio de la capa decide el CTE.** El ΔCTE se mide contra los materiales que la capa toca
  (die, Cu del DBC, baseplate, wire de Al). Nuevo sitio: metalización del chip (bond pad).
- **Alertas de química** para el corte transversal (Ni/Fe hacia Cu, óxido de Al/Ti). No mueven el score.
- **Dictamen por fase:** `proceed_to_coupon`, `coupon_high_cte_risk`, `coupon_cte_unknown`,
  `kappa_significant`, `process_veto`.
- **Ranking de confiabilidad** 25 % NOS / 35 % proceso / 40 % interfaz, editable, con
  **estabilidad del ranking** sobre 120 combinaciones de pesos.
- **Ficha de cupón en dos etapas** (choque rápido comparativo + ciclado representativo con checkpoints).
- **Botón "Solicitar estudio"** que abre un correo con la configuración del usuario.

Correr pruebas: `python3 tests/test_scoring.py && python3 tests/test_reliability.py`

## Posicionamiento

Correcto: screening layer *antes* de Thermo-Calc / ensayo.

Incorrecto: plataforma enterprise de cooling o “más precisa que Materials Project”.

Licencia CC BY-NC-SA 4.0. Uso comercial requiere permiso escrito.

## Autor

Wilmer Gaspar Espinoza Castillo  
ORCID: https://orcid.org/0009-0000-1388-9660
