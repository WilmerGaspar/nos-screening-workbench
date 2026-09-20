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
python3 tests/test_scoring.py

python3 cli.py --elements Ni,Al --process pvd --temp 150 \
  --application si_power_module --substrate Cu --die Si \
  --thickness-um 20 --power-w 50 --t-sink 45
```

API live (opcional):

```bash
export MP_API_KEY="..."     # https://next-gen.materialsproject.org/api
python3 cli.py --elements Ni,Al --process thermal_spray --temp 600 --live
```

## Qué hace el modo chip-cooling

NiAl estequiométrico: κ = 92.2 W/m·K. A 20 µm y 1 cm², \(R_{\mathrm{coat}} \approx 0.0022\) K/W.
FeAl (~12 W/m·K) no pasa la puerta de heat-spreader. Si no hay κ citable, el dictamen es `missing_thermal_data`.

## Posicionamiento

Correcto: screening layer *antes* de Thermo-Calc / ensayo.

Incorrecto: plataforma enterprise de cooling o “más precisa que Materials Project”.

Licencia CC BY-NC-SA 4.0. Uso comercial requiere permiso escrito.

## Autor

Wilmer Gaspar Espinoza Castillo  
ORCID: https://orcid.org/0009-0000-1388-9660
