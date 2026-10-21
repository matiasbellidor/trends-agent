# trends-agent

Agente que junta tendencias de IA, data y actuaría y genera un digest diario en Markdown, filtrado por pilares de contenido. Corre gratis en GitHub Actions y deja el resultado en un vault de Obsidian.

Nació de un problema concreto: producir contenido de forma constante requiere saber qué se está discutiendo, y revisar siete fuentes a mano todos los días no escala. El agente hace la recolección y el filtrado; la decisión de qué contar sigue siendo humana.

## Qué hace

1. **Recolecta** de seis tipos de fuente: Hacker News, Reddit (RSS), GitHub (repos nuevos por topic), arXiv, YouTube (opcional) y feeds RSS genéricos.
2. **Filtra** por pilares definidos en `config.yaml`, con keywords y pesos.
3. **Puntúa** cada ítem y lo ordena.
4. **Deduplica** por URL normalizada y por similitud de título, y recuerda lo ya mostrado para no repetir días.
5. **Escribe** `AAAA-MM-DD.md` con frontmatter listo para Obsidian.

Si una fuente falla, el digest sale igual y la lista en "Fuentes con problemas". Si fallan todas, el job termina con error.

## Cómo puntúa

```
score = 100 * (0.5 * relevancia + 0.3 * engagement + 0.2 * recencia)
```

- **Relevancia:** por pilar, `peso * min(hits, 4) / 4`. Una keyword en el título cuenta 2 y en el resumen 1. Se suman los pilares y se topea en 1. Las keywords matchean como palabra completa (`sql` no matchea `MySQL`).
- **Engagement:** percentil dentro de su propia fuente, porque puntos de HN, estrellas de GitHub y vistas de YouTube no son comparables. Sin métrica (RSS, arXiv) vale 0.5. En Reddit el RSS no trae score, así que la posición en el top es la señal.
- **Recencia:** decaimiento exponencial con vida media de 36 horas.
- **Bonus multi-fuente:** +5 puntos por cada fuente adicional que trae lo mismo (máximo +10, score topeado en 100). Aparecer en dos lugares a la vez es una señal de tendencia real.

Todos los pesos, umbrales y keywords están en `config.yaml`.

## Instalación local

```bash
pip install -r requirements.txt && pip install -e .
python -m trends_agent run --config config.yaml --out-dir out --dry-run
```

Variables de entorno opcionales: `GITHUB_TOKEN` (sube el límite de búsqueda de 10 a 30 req/min) y `YOUTUBE_API_KEY`. Sin la clave de YouTube, esa fuente se saltea sola.

## Automatización con GitHub Actions

El workflow `.github/workflows/daily.yml` corre todos los días a las 07:17 (Buenos Aires). Configuración desde la web de GitHub, en `Settings > Secrets and variables > Actions`:

| Dónde | Nombre | Para qué |
|---|---|---|
| Variables | `VAULT_REPO` | `usuario/repo` privado donde se guarda el digest (carpeta `07-trends/`). Si está vacío, el digest se sube como artifact y no se commitea a ningún lado. |
| Secrets | `VAULT_TOKEN` | Token fine-grained con acceso **solo** al repo del vault, permiso Contents: read and write. |
| Secrets | `YOUTUBE_API_KEY` | Opcional. |

Para probarlo sin esperar al cron: pestaña `Actions > daily-digest > Run workflow`.

El código es público y los digests van a un repo privado, así el feed de ideas no queda expuesto.

## Tests

```bash
pytest
```

24 tests sin red: HTTP simulado con respuestas de ejemplo por fuente, y una corrida completa de punta a punta que cubre cruce de fuentes, fuente caída, segundo día sin repetidos y re-corrida idempotente.

## Decisiones y límites

- **No scrapea TikTok ni Instagram.** Viola sus términos, se rompe seguido y arriesga las cuentas. Solo usa APIs, RSS y feeds públicos.
- **El ranking final es manual.** No usa ninguna API paga: el digest se revisa después con un asistente que lee el archivo, y ahí se eligen las ideas.
- **Reddit puede bloquear IPs de GitHub Actions.** Es un riesgo conocido de los feeds públicos; si pasa, aparece en "Fuentes con problemas" y el resto sigue.
- **Las URLs de los feeds RSS de `config.yaml` no se verificaron contra la red real.** Se validan en la primera corrida.
- **Las keywords por palabra completa no cubren plurales ni variantes.** Hay que agregarlas explícitamente a `config.yaml`.

## Estructura

```
src/trends_agent/
  sources/     un módulo por fuente (hackernews, reddit, github, arxiv, youtube, rss)
  scoring.py   relevancia, percentiles, recencia
  dedupe.py    normalización de URL y similitud de títulos
  state.py     memoria de ítems ya mostrados
  digest.py    selección y render a Markdown
  pipeline.py  orquestación
  cli.py       punto de entrada
config.yaml    pilares, pesos y fuentes
tests/         pytest, sin red
```

## Licencia

MIT
