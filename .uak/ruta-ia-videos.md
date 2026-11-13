# Brief · Ruta UpiixIA "De cero a LLMs" con videos secuenciales

> Entrada para el kit (modo **marathon**): correr `/uak-spec ruta-ia-videos` con este archivo como fuente.
> El planner debe convertirlo en `docs/specs/002-ruta-ia-videos/{spec,plan}.md` y en tareas `UPS-042+` de `.uak/TASKS.md`.
> Las tareas sugeridas al final ya siguen el formato de `TASKS.md`; el planner puede ajustarlas (IDs, Paths, Estimate).
> UI en español (México). Commits sin líneas de coautoría de IA (PROJECT principio 5).
> **Ya planeado (2026-11-11):** las tareas reales son **UPS-045..048** en `.uak/TASKS.md`; la §8 queda solo como historial. Donde este brief y `docs/specs/002-ruta-ia-videos/spec.md` difieran (p. ej. publicación de la ruta en §4), manda la spec. La §5 sigue siendo el catálogo de partida para UPS-046.

## 1. Problema

La academia **UpiixIA** solo tiene la ruta de demostración "Fundamentos de IA con Python" (`app/fixtures/demo.json`): 2 módulos y 4 videos sueltos de freeCodeCamp que **se repiten entre sí** y no forman una secuencia. El club necesita una ruta real, **desde cero hasta construir y usar un LLM**, donde cada clase continúe exactamente donde terminó la anterior y no haya videos de 10 horas.

## 2. Qué se quiere

- Una ruta nueva **"De cero a LLMs"** en la academia UpiixIA con **9 módulos** (las 9 etapas de la §5) y ~45 clases.
- Cada clase es **un video de YouTube** (o un **tramo** de un video largo, con inicio y fin) más enlaces de apoyo.
- Se mezcla español e inglés: se usó el mejor curso de cada tema. Cada clase indica su idioma.
- La ruta debe poder cargarse **sin redeploy de código de contenido** (fixture idempotente) y editarse después desde el panel del admin de academia.

## 3. Cambio técnico obligatorio: tramos de video (inicio/fin)

Hoy el reproductor **descarta la marca de tiempo**:
- `app/services/youtube.py` → `extract_video_id()` solo devuelve el ID; `embed_url()` genera `https://www.youtube-nocookie.com/embed/<id>` sin `start`/`end`.
- `app/models/learning.py` → `Lesson` tiene `youtube_url`, `youtube_video_id`, `duration_min`, pero **no** `start_s`/`end_s`.
- `web/src/features/learning/youtube.ts` y `Player.tsx` arman el embed sin tiempos.

Se necesita:
1. Columnas `start_s` y `end_s` (`Integer`, nullable) en `lessons`, con migración `0007_lesson_segments.py` reversible.
2. `extract_video_id` sigue igual; una función nueva `parse_start(url)` lee `t=`/`start=` (`?t=850`, `?t=14m10s`, `&start=850`) para prellenar `start_s` si el admin pega un enlace con tiempo.
3. `embed_url(video_id, start_s=None, end_s=None)` agrega `?start=<s>&end=<s>` solo con enteros válidos (`0 ≤ start < end`). Nada de la URL del usuario llega crudo al embed.
4. Schemas de entrada/salida (`app/schemas/learning.py`), servicio (`app/services/learning.py`) y tipos web (`web/src/lib/types.ts`) exponen `start_s`/`end_s`.
5. El formulario de clase del admin de academia permite inicio/fin en `mm:ss` o `h:mm:ss`.
6. `duration_min` se calcula como `ceil((end_s - start_s)/60)` cuando ambos existen.
7. Validación: `end_s > start_s`; si hay error, el mensaje va en el `FormMessage` reservado.

## 4. Carga de contenido

- Archivo nuevo `app/fixtures/ruta-ia.json`, mismo esquema que `route` en `demo.json` más `start_s`, `end_s`, `lang` (`es`/`en`) y `status` (`ok`/`verificar`).
- `app/seed.py` gana un paso idempotente que crea o actualiza la ruta por título (sin duplicar clases al correr dos veces) y la deja **publicada solo si todas sus clases tienen `status: ok`**; las clases `verificar` quedan como borrador (`is_published = false`).
- La ruta de demostración vieja se conserva marcada `demo_data`; decidir con el humano si se oculta (**decisión humana**, `uak decision`).
- La descripción de cada clase termina con el idioma: `*Video en español.*` o `*Video en inglés (activa subtítulos en español).*`

## 5. Catálogo de contenido (fuente de verdad)

**Leyenda de estado:**
- `ok` = enlace confirmado en una fuente oficial (repo de GitHub del autor o búsqueda con el título exacto).
- `verificar` = ID tomado de memoria o canal no confirmado: **abrirlo y comprobar título, canal y que no esté borrado** antes de publicar.
- `buscar` = no hay URL todavía; la tarea de verificación debe encontrarla o proponer sustituto.

Fuentes de donde salen los enlaces:
- MoureDev: README de https://github.com/mouredev/Hello-Python (marcas de tiempo por lección).
- Data School: README de https://github.com/justmarkham/scikit-learn-videos
- Karpathy: README de https://github.com/karpathy/nn-zero-to-hero y https://karpathy.ai/zero-to-hero.html
- 3Blue1Brown: https://www.3blue1brown.com/topics/neural-networks , https://www.3blue1brown.com/topics/linear-algebra , https://www.3blue1brown.com/topics/calculus · canal doblado: buscar "3Blue1Brown Español" en YouTube.
- GPT desde cero: https://github.com/maximiranda/gpt-desde-cero · canal https://www.youtube.com/@ai.explicada
- Hugging Face: https://huggingface.co/learn/llm-course
- Jetson: https://www.jetson-ai-lab.com/tutorials/ y https://www.jetson-ai-lab.com/tutorials/ollama

### Módulo 1 · Python desde cero (MoureDev · es)
Un solo video (`Kp4Mvapo5kc`, ~10 h) partido en tramos. `end_s` = inicio de la lección siguiente (README de Hello-Python).

| # | Clase | URL | start_s | end_s | Estado |
|---|---|---|---|---|---|
| 1.1 | Configuración y Hola Mundo | https://youtu.be/Kp4Mvapo5kc | 850 | 2938 | ok |
| 1.2 | Variables | https://youtu.be/Kp4Mvapo5kc | 2938 | 5665 | ok |
| 1.3 | Operadores | https://youtu.be/Kp4Mvapo5kc | 5665 | 8643 | ok |
| 1.4 | Strings | https://youtu.be/Kp4Mvapo5kc | 8643 | 10872 | ok |
| 1.5 | Listas | https://youtu.be/Kp4Mvapo5kc | 10872 | 14711 | ok |
| 1.6 | Diccionarios | https://youtu.be/Kp4Mvapo5kc | 18506 | 21442 | ok |
| 1.7 | Condicionales | https://youtu.be/Kp4Mvapo5kc | 21442 | 23822 | ok |
| 1.8 | Bucles | https://youtu.be/Kp4Mvapo5kc | 23822 | 26619 | ok |
| 1.9 | Funciones | https://youtu.be/Kp4Mvapo5kc | 26619 | 29327 | ok |
| 1.10 | Clases y objetos | https://youtu.be/Kp4Mvapo5kc | 29327 | 32030 | ok |

Enlaces extra (LessonLink, no clases): Tuplas `?t=14711`, Sets `?t=16335`, Excepciones `?t=32030`, Módulos `?t=34583`; tutorial oficial https://docs.python.org/es/3/tutorial/

### Módulo 2 · Matemáticas con intuición (3Blue1Brown · en, preferir doblaje es)
Si existe la versión de "3Blue1Brown Español", usar esa URL y `lang: es`.

| # | Clase | URL | Estado |
|---|---|---|---|
| 2.1 | Vectores, ¿qué son? | https://www.youtube.com/watch?v=fNk_zzaMoSs | verificar |
| 2.2 | Combinaciones lineales y base | https://www.youtube.com/watch?v=k7RM-ot2NWY | verificar |
| 2.3 | Matrices como transformaciones | https://www.youtube.com/watch?v=kYB8IZa5AuE | verificar |
| 2.4 | Multiplicación de matrices | https://www.youtube.com/watch?v=XkY2DOUCWMU | verificar |
| 2.5 | La esencia del cálculo | https://www.youtube.com/watch?v=WUvTyaaNkzM | verificar |
| 2.6 | Qué es una derivada | https://www.youtube.com/watch?v=9vKqVkMQHKk | verificar |
| 2.7 | Derivadas con geometría | https://www.youtube.com/watch?v=S0_qX4VJhMQ | verificar |
| 2.8 | Regla de la cadena | https://www.youtube.com/watch?v=YG15m2VwSjA | verificar |

Listas: álgebra lineal https://www.youtube.com/playlist?list=PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab · cálculo https://www.youtube.com/playlist?list=PLZHQObOWTQDMsr9K-rj53DwVRMYO3t5Yr (verificar).

### Módulo 3 · Datos y Machine Learning práctico
| # | Clase | URL | Idioma | Estado |
|---|---|---|---|---|
| 3.1 | NumPy | Lección #07, "Curso Python Data Science en Español" (Rafa González Gouveia) · ficha https://classcentral.com/course/youtube-curso-python-data-science-2021-en-espanol-54807 | es | buscar |
| 3.2 | pandas | Lección #08 del mismo curso | es | buscar |
| 3.3 | ¿Qué es el Machine Learning? | https://www.youtube.com/watch?v=elojMnjn4kk | en | ok |
| 3.4 | Preparar Python: scikit-learn y Jupyter | https://www.youtube.com/watch?v=IsXXlYVBt1M | en | ok |
| 3.5 | Primeros pasos con el dataset iris | https://www.youtube.com/watch?v=hd1W4CyPX58 | en | ok |
| 3.6 | Entrenar un modelo | https://www.youtube.com/watch?v=RlQuVL6-qe8 | en | ok |
| 3.7 | Comparar modelos | https://www.youtube.com/watch?v=0pP4EwWJgIU | en | ok |
| 3.8 | pandas, seaborn y scikit-learn | https://www.youtube.com/watch?v=3ZWuPVWq7p4 | en | ok |
| 3.9 | Validación cruzada | https://www.youtube.com/watch?v=6dbrR-WymjI | en | ok |
| 3.10 | Buscar los mejores parámetros | https://www.youtube.com/watch?v=Gol_qOgRqfA | en | ok |
| 3.11 | Evaluar un clasificador | https://www.youtube.com/watch?v=85dtiMz9tSo | en | ok |
| 3.12 | Flujo de trabajo completo | https://www.youtube.com/watch?v=irHhDMbw3xo | en | ok |

Lista Data School: https://www.youtube.com/playlist?list=PL5-da3qGB5ICeMbQuqbbCOQWcS6OYBr5A (2015: avisar en la descripción que algunas funciones cambiaron de nombre). Notebooks: https://github.com/justmarkham/scikit-learn-videos
Extra (LessonLink): StatQuest "A Gentle Introduction to Machine Learning" https://www.youtube.com/watch?v=Gv9_4yMHFhI (ok).

### Módulo 4 · Redes neuronales (3Blue1Brown, Deep Learning caps. 1–4 · en)
| # | Clase | URL | Estado |
|---|---|---|---|
| 4.1 | ¿Qué es una red neuronal? | https://www.youtube.com/watch?v=aircAruvnKk | verificar |
| 4.2 | Descenso del gradiente | https://www.youtube.com/watch?v=IHZwWFHWa-w | verificar |
| 4.3 | Backpropagation: la idea | https://www.youtube.com/watch?v=Ilg3gGewQ5U | verificar |
| 4.4 | Backpropagation: el cálculo | https://www.youtube.com/watch?v=tIeHLnjs5U8 | verificar |

Lista: https://www.youtube.com/playlist?list=PLZHQObOWTQDNU6R1_67000Dx_ZCJB-3pi (verificar). Alternativa en español como enlace extra: DotCSV "¿Qué es una red neuronal?" parte 1 https://www.youtube.com/watch?v=MRIv2IwFTPg y parte 2 https://www.youtube.com/watch?v=uwbHOpp9xkc (ok).

### Módulo 5 · Construirlo en código (Karpathy, Zero to Hero · en)
Videos de 1–2 h: partir cada uno en 2–3 clases usando los **capítulos de la descripción de YouTube** (tarea de verificación: copiar los tiempos de ahí). Mientras no existan tramos, cada video es una clase completa.

| # | Clase | URL | Estado |
|---|---|---|---|
| 5.1 | micrograd: backpropagation desde cero | https://www.youtube.com/watch?v=VMj-3S1tku0 | ok |
| 5.2 | makemore: tu primer modelo de lenguaje | https://www.youtube.com/watch?v=PaCmpygFfXo | ok |
| 5.3 | makemore 2: MLP | https://youtu.be/TCH_1BHY58I | ok |
| 5.4 | makemore 3: activaciones, gradientes y BatchNorm | https://youtu.be/P6sfmUTpUmc | ok |
| 5.5 | makemore 4: backprop a mano (opcional) | https://youtu.be/q8SA3rM6ckI | ok |
| 5.6 | makemore 5: WaveNet | https://youtu.be/t3YJ5hKiMQ0 | ok |

Código: https://github.com/karpathy/nn-zero-to-hero

### Módulo 6 · Transformers: entender y construir un GPT
| # | Clase | URL | Idioma | Estado |
|---|---|---|---|---|
| 6.1 | Transformers, la tecnología detrás de los LLMs | https://www.youtube.com/watch?v=wjZofJX0v4M | en | verificar |
| 6.2 | La atención en los transformers | https://www.youtube.com/watch?v=eMlx5fFNoYc | en | ok |
| 6.3 | Construyamos GPT desde cero | https://www.youtube.com/watch?v=kCc8FmEb1nY | en | ok |
| 6.4 | Construir el tokenizador de GPT | https://www.youtube.com/watch?v=zduSFxRajkE | en | ok |
| 6.5 | Cómo guardan datos los LLMs | https://www.youtube.com/watch?v=9-Jl0dxWQs8 | en | verificar |

Repaso en español (LessonLink): serie "GPT desde cero", eps. 1–3, https://www.youtube.com/@ai.explicada · notebooks https://github.com/maximiranda/gpt-desde-cero (el ep. 4 aún no se publica).

### Módulo 7 · De GPT a ChatGPT (Karpathy · en)
| # | Clase | URL | Estado |
|---|---|---|---|
| 7.1–7.4 | Deep Dive into LLMs like ChatGPT (3.5 h): preentrenamiento, fine-tuning, RLHF, alucinaciones | https://www.youtube.com/watch?v=7xTGNNLPyMI | ok |

Partir en 4 tramos usando los capítulos de la descripción del video.

### Módulo 8 · Usar LLMs: Hugging Face, RAG y modelos locales
| # | Clase | URL | Idioma | Estado |
|---|---|---|---|---|
| 8.1 | Curso de LLMs de Hugging Face: videos de los caps. 1–3 | Extraer las URLs de YouTube incrustadas en https://huggingface.co/learn/llm-course | en | buscar |
| 8.2 | RAG de punta a punta, parte 1 | "RAG: E2E App, habla con tu data no estructurada, parte 1" (The Machine Learning Engineer) · ficha https://classcentral.com/course/youtube-rag-e2e-app-habla-con-tu-data-no-estructurada-parte-1-espanol-machinelearning-datascience-381866 | es | buscar |
| 8.3 | RAG de punta a punta, parte 2 | ficha https://classcentral.com/course/youtube-rag-e2e-app-habla-con-tu-data-no-estructurada-parte-2-espanol-machinelearning-datascience-381864 | es | buscar |
| 8.4 | Ollama: LLMs locales | "Aprende Ollama en 15 minutos" · resumen https://lilys.ai/es/notes/local-llm-20251213/learn-ollama-llm-locally | es | buscar |
| 8.5 | LM Studio en español | https://www.youtube.com/watch?v=X95qSmkigco | es | verificar |

### Módulo 9 · LLMs en la Jetson
Sin serie de video confiable. Clases que se pueden cargar ya como **enlaces** (LessonLink) dentro de una clase introductoria; el club grabará sus propios videos después.
- Tutoriales oficiales: https://www.jetson-ai-lab.com/tutorials/
- Ollama en Jetson: https://www.jetson-ai-lab.com/tutorials/ollama
- Guía en español de NVIDIA: https://la.blogs.nvidia.com/?p=6761
- Paul McWhorter (toptechboy), LLMs locales en Orin Nano: https://toptechboy.com/tag/llm/ (verificar)
- ⚠️ El curso gratis de NVIDIA DLI "Getting Started with AI on Jetson Nano" **no es compatible con la Orin Nano**; no prometer certificado sin confirmar el modelo de kit.

### Huecos conocidos (fuera de alcance del contenido de video v1)
- Ética, sesgos y seguridad → sesión en vivo del club (evento, no clase).
- Videos propios de Jetson → se agregan cuando el club los grabe.
- Proyecto final → trabajo por equipos con mentor; no lleva video.

## 6. Criterios de aceptación (EARS)

- **Cuando** un miembro abre la clase 1.2, **el sistema** reproduce el video desde 2938 s y se detiene en 5665 s.
- **Cuando** un admin pega `https://youtu.be/Kp4Mvapo5kc?t=850` en el formulario, **el sistema** prellena inicio = 14:10.
- **Si** `end_s ≤ start_s`, **entonces el sistema** rechaza la clase con 422 y mensaje en español.
- **Cuando** se corre el seed dos veces, **el sistema** no duplica módulos ni clases.
- **Mientras** una clase tenga `status: verificar` o `buscar`, **el sistema** la deja como borrador.
- **El sistema** muestra el idioma de cada clase en su descripción.
- Las clases nuevas aparecen en el reproductor, cuentan para el progreso y "Continuar donde te quedaste" funciona igual que hoy.

## 7. Seguridad

- El servidor sigue **sin hacer fetch** de las URLs (ver `docs/spikes/youtube.md`); `start_s`/`end_s` son enteros validados, nunca texto concatenado al embed.
- Mismos permisos que hoy: solo superadmin y el admin de su academia editan clases (`docs/permissions-matrix.md` sin filas nuevas, solo verificar que los campos nuevos respeten el alcance).

---

## 8. Tareas sugeridas (formato `.uak/TASKS.md`)

## UPS-042 · Lesson video segments: start/end seconds in model, API and player

- **Type:** feature
- **Priority:** P0
- **Estimate:** 150 min
- **Rubric / Spec:** human request 2026-11-11: long videos split into classes · `docs/specs/002-ruta-ia-videos/spec.md` §3
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-043, UPS-044
- **Paths:** app/models/learning.py, app/migrations/versions/0007_lesson_segments.py, app/services/youtube.py, app/services/learning.py, app/schemas/learning.py, app/tests/test_youtube.py, app/tests/test_learning.py, web/src/lib/types.ts, web/src/features/learning/youtube.ts, web/src/features/learning/Player.tsx, web/src/features/academy-admin/
- **Freeze-Allowed:** no
- **Acceptance:**
  - Nullable `start_s`/`end_s` on `lessons` (migration 0007, reversible); API reads and writes them; `end_s > start_s` enforced (422, Spanish message).
  - `parse_start()` understands `t=850`, `t=14m10s`, `start=850`; the admin form prefills start from a pasted URL and accepts `mm:ss`/`h:mm:ss`.
  - `embed_url()` adds `start`/`end` only from validated integers; the player starts and stops at them; `duration_min` derives from the segment.
  - Tests cover parsing, validation, embed URL and the permissions scope; coverage stays at 100 %.
- **Verify:** `uv run pytest -q app/tests/test_youtube.py app/tests/test_learning.py && npm --prefix web run lint && npm --prefix web run build`
- **Next step:** migration + model + youtube helpers with tests, then API, then player and admin form.

## UPS-043 · Verify and complete the UpiixIA video catalog

- **Type:** spike
- **Priority:** P0
- **Estimate:** 120 min
- **Rubric / Spec:** `docs/specs/002-ruta-ia-videos/spec.md` §5
- **Depends on:** None
- **Uses contract:** None
- **Related:** UPS-044
- **Paths:** docs/spikes/ruta-ia-catalog.md, app/fixtures/ruta-ia.json
- **Freeze-Allowed:** no
- **Acceptance:**
  - Every row marked `verificar` is opened: title, channel and availability confirmed, or replaced and noted.
  - Every row marked `buscar` gets a real YouTube URL (NumPy/pandas ES, Hugging Face videos, RAG ES, Ollama ES) or a documented substitute.
  - Chapter timestamps copied from the YouTube descriptions for the Karpathy videos (module 5) and the Deep Dive (module 7) to split them into 2–4 segments.
  - Prefer the "3Blue1Brown Español" dubbed URL when it exists.
  - Results recorded in `docs/spikes/ruta-ia-catalog.md` and `app/fixtures/ruta-ia.json` with `status: ok`.
- **Verify:** human review of `docs/spikes/ruta-ia-catalog.md` (every link opened at least once)
- **Next step:** walk module by module, starting with modules 2, 4 and 8.

## UPS-044 · Seed the "De cero a LLMs" route for UpiixIA

- **Type:** feature
- **Priority:** P0
- **Estimate:** 120 min
- **Rubric / Spec:** `docs/specs/002-ruta-ia-videos/spec.md` §4
- **Depends on:** UPS-042
- **Uses contract:** UPS-043
- **Related:** None
- **Paths:** app/fixtures/ruta-ia.json, app/seed.py, app/tests/test_seed_ruta_ia.py, e2e/test_ruta_ia.py
- **Freeze-Allowed:** no
- **Acceptance:**
  - `app/fixtures/ruta-ia.json` holds the 9 modules and their lessons from spec §5, with `start_s`, `end_s`, `lang`, `status` and links.
  - The seed creates or updates the route idempotently (two runs → same counts); lessons not `ok` stay unpublished.
  - Each description ends with the language note; long videos appear as segments.
  - The old demo route's fate follows the human `uak decision`.
  - e2e: a member opens lesson 1.2, the embed carries `start=2938&end=5665`, marking it complete moves the progress bar.
- **Verify:** `uv run pytest -q app/tests/test_seed_ruta_ia.py && uv run pytest -q e2e/test_ruta_ia.py`
- **Next step:** write the fixture from the spike output, then the idempotent seed step.
