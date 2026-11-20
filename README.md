# Pisos en Almería: alertas diarias

Busca cada día pisos de alquiler en Almería capital (Centro, Oliveros, Altamira, Zapillo y Vega de Acá; 500-700 €;
2 habitaciones, 1 baño, garaje y ascensor), publica una página con los vigentes y manda por correo los nuevos.

Diseño: `docs/superpowers/specs/2026-11-20-alertas-pisos-almeria-design.md`.

## Qué portal corre dónde

Medido el 20/11/2026 con `python scripts/sonda_portales.py`, desde casa y desde GitHub Actions (workflow
`sonda.yml`, ejecución 44790689034). Los resultados son idénticos en los dos sitios:

| Portal | Casa | GitHub | Dónde corre |
|---|---|---|---|
| Fotocasa (API) | 200 | 200 | GitHub |
| Habitaclia | 200 | 200 | GitHub |
| pisos.com | 200 | 200 | GitHub |
| Milanuncios (API) | 200 | 200 | GitHub |
| Idealista | 403 captcha | 403 captcha | PC (Edge visible) + alerta propia de Idealista |
| yaencontre | 403 captcha | 403 captcha | PC (Edge visible) |

Para volver a medirlo: `gh workflow run sonda.yml` y `gh run view --log`.
