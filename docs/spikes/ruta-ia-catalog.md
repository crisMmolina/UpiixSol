# Catálogo verificado · Ruta UpiixIA "De cero a LLMs" (UPS-046)

Fuente de verdad de los enlaces para `app/fixtures/ruta-ia.json` (UPS-047). Parte del §5 del brief humano (`.uak/ruta-ia-videos.md`, que sube el PR 91) y lo corrige con lo que se comprobó el **2026-11-12**.

## Cómo se verificó

- **Disponibilidad, título y canal:** `https://www.youtube.com/oembed?url=<URL>&format=json` devuelve 200 con título y canal si el video existe y es público; 404 si no. No usa la API de datos de YouTube ni requiere cuenta.
- **Capítulos y duración:** campos `shortDescription` y `lengthSeconds` de la página del video (los capítulos que el autor escribió en la descripción).
- **Tiempos de MoureDev:** comparados contra el README de `mouredev/Hello-Python`.
- **Enlaces que no son de YouTube:** `curl` con código HTTP final.
- Nadie vio los videos completos: `ok` significa título, canal y disponibilidad confirmados, no que el contenido se revisó clase por clase. Un humano abre cada enlace en el PR (criterio de aceptación).

## Estados

| Estado | Significado | Efecto en el seed (UPS-047) |
|---|---|---|
| `ok` | Video abierto y confirmado por oembed (título, canal, disponible), o tiempos copiados del autor | Clase publicada |
| `sustituto` | El video del brief no existe con ese título; se propone otro que un humano debe ver antes de publicar | Clase en borrador |

No queda ninguna fila sin URL: las que el brief marcaba `buscar` o `verificar` se resolvieron abajo. Fecha de verificación de toda fila: **2026-11-12** (columna `fecha`).

## Cambios frente al brief (léelos primero)

1. **Módulos 2 y 4: sí existe el doblaje "3Blue1Brown Español"** para los 7 capítulos de álgebra lineal/cálculo y los 4 de Deep Learning. Se usó esa URL con `lang: es`. Excepción: 2.8 (regla de la cadena) no tiene doblaje; queda en inglés.
2. **3.12 "Flujo de trabajo completo"** (`irHhDMbw3xo`): el ID coincide con el video 10 del README de Data School ("Building a Machine Learning workflow"), pero el título vivo en YouTube es "How do I encode categorical features using scikit-learn?". Mismo video, título renombrado; el contenido (Pipeline + OneHotEncoder + ColumnTransformer) es el que pide la clase.
3. **8.4 Ollama:** "Aprende Ollama en 15 minutos" no se encontró con ese título. Se propone un sustituto (estado `sustituto`).
4. **Hugging Face (8.1):** la página del curso no incrusta videos, solo enlaza una lista de YouTube del canal oficial (80 videos del curso original, 2021–22, con variantes PyTorch y TensorFlow). Se eligieron 4 en PyTorch.
5. **Karpathy (módulo 5) y "Deep Dive into LLMs" (módulo 7):** partidos en tramos con los capítulos de la descripción de cada video.
6. **Módulo 9:** hay video oficial de NVIDIA en español para la clase introductoria.
7. **Enlace extra no verificable:** `https://la.blogs.nvidia.com/?p=6761` devuelve 403 a `curl` (bloqueo de bots, no se pudo abrir sin navegador). Un humano debe abrirlo antes de publicarlo como `LessonLink`.

## Módulo 1 · Python desde cero (MoureDev · es)

Un solo video, `Kp4Mvapo5kc`, "Curso COMPLETO de PYTHON desde CERO para PRINCIPIANTES" (MoureDev by Brais Moure), 36 454 s. Los tiempos coinciden con el README de Hello-Python. `end_s` = inicio de la lección siguiente. 1.1 junta las lecciones 1 (Configuración) y 2 (Hola Mundo) del README. Tuplas y Sets (14711–18506) quedan como enlaces extra.

| # | Clase | URL | start_s | end_s | lang | status | fecha |
|---|---|---|---|---|---|---|---|
| 1.1 | Configuración y Hola Mundo | https://youtu.be/Kp4Mvapo5kc | 850 | 2938 | es | ok | 2026-11-12 |
| 1.2 | Variables | https://youtu.be/Kp4Mvapo5kc | 2938 | 5665 | es | ok | 2026-11-12 |
| 1.3 | Operadores | https://youtu.be/Kp4Mvapo5kc | 5665 | 8643 | es | ok | 2026-11-12 |
| 1.4 | Strings | https://youtu.be/Kp4Mvapo5kc | 8643 | 10872 | es | ok | 2026-11-12 |
| 1.5 | Listas | https://youtu.be/Kp4Mvapo5kc | 10872 | 14711 | es | ok | 2026-11-12 |
| 1.6 | Diccionarios | https://youtu.be/Kp4Mvapo5kc | 18506 | 21442 | es | ok | 2026-11-12 |
| 1.7 | Condicionales | https://youtu.be/Kp4Mvapo5kc | 21442 | 23822 | es | ok | 2026-11-12 |
| 1.8 | Bucles | https://youtu.be/Kp4Mvapo5kc | 23822 | 26619 | es | ok | 2026-11-12 |
| 1.9 | Funciones | https://youtu.be/Kp4Mvapo5kc | 26619 | 29327 | es | ok | 2026-11-12 |
| 1.10 | Clases y objetos | https://youtu.be/Kp4Mvapo5kc | 29327 | 32030 | es | ok | 2026-11-12 |

Enlaces extra (LessonLink): Tuplas https://youtu.be/Kp4Mvapo5kc?t=14711 · Sets https://youtu.be/Kp4Mvapo5kc?t=16335 · Excepciones https://youtu.be/Kp4Mvapo5kc?t=32030 · Módulos https://youtu.be/Kp4Mvapo5kc?t=34583 · tutorial oficial https://docs.python.org/es/3/tutorial/ (200) · código https://github.com/mouredev/Hello-Python (200).

## Módulo 2 · Matemáticas con intuición (3Blue1Brown Español · es)

Canal "3Blue1Brown Español" confirmado por oembed. El original en inglés queda como enlace extra de cada clase.

| # | Clase | URL | start_s | end_s | lang | status | fecha |
|---|---|---|---|---|---|---|---|
| 2.1 | Vectores, ¿qué son? | https://www.youtube.com/watch?v=wiuEEkP_XuM | - | - | es | ok | 2026-11-12 |
| 2.2 | Combinaciones lineales y base | https://www.youtube.com/watch?v=RqQqFx4xUjk | - | - | es | ok | 2026-11-12 |
| 2.3 | Matrices como transformaciones | https://www.youtube.com/watch?v=YJfS4_m_0Z8 | - | - | es | ok | 2026-11-12 |
| 2.4 | Multiplicación de matrices | https://www.youtube.com/watch?v=8f7UUnbLqp0 | - | - | es | ok | 2026-11-12 |
| 2.5 | La esencia del cálculo | https://www.youtube.com/watch?v=ykwjb-OGimE | - | - | es | ok | 2026-11-12 |
| 2.6 | Qué es una derivada | https://www.youtube.com/watch?v=byYkHqabnKM | - | - | es | ok | 2026-11-12 |
| 2.7 | Derivadas con geometría | https://www.youtube.com/watch?v=nQruR83shIA | - | - | es | ok | 2026-11-12 |
| 2.8 | Regla de la cadena | https://www.youtube.com/watch?v=YG15m2VwSjA | - | - | en | ok | 2026-11-12 |

Originales en inglés (extra, todos 200 en oembed): `fNk_zzaMoSs`, `k7RM-ot2NWY`, `kYB8IZa5AuE`, `XkY2DOUCWMU`, `WUvTyaaNkzM`, `9vKqVkMQHKk`, `S0_qX4VJhMQ`. 2.8 solo existe en inglés ("Visualizing the chain rule and product rule", 3Blue1Brown); no se halló doblaje.
Listas (200): álgebra lineal https://www.youtube.com/playlist?list=PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab · cálculo https://www.youtube.com/playlist?list=PLZHQObOWTQDMsr9K-rj53DwVRMYO3t5Yr.

## Módulo 3 · Datos y Machine Learning práctico

3.1 y 3.2 son del "Curso Python Data Science en Español" del canal Rafa Gonzalez Gouveia; el título del video no trae el número de lección (#07, #08), pero tema, canal y serie coinciden y la lección #06 del mismo curso se ve en la búsqueda justo antes.

| # | Clase | URL | start_s | end_s | lang | status | fecha |
|---|---|---|---|---|---|---|---|
| 3.1 | NumPy | https://www.youtube.com/watch?v=fczpaVSwGCA | - | - | es | ok | 2026-11-12 |
| 3.2 | pandas | https://www.youtube.com/watch?v=GpdPvpV7MkA | - | - | es | ok | 2026-11-12 |
| 3.3 | ¿Qué es el Machine Learning? | https://www.youtube.com/watch?v=elojMnjn4kk | - | - | en | ok | 2026-11-12 |
| 3.4 | Preparar Python: scikit-learn y Jupyter | https://www.youtube.com/watch?v=IsXXlYVBt1M | - | - | en | ok | 2026-11-12 |
| 3.5 | Primeros pasos con el dataset iris | https://www.youtube.com/watch?v=hd1W4CyPX58 | - | - | en | ok | 2026-11-12 |
| 3.6 | Entrenar un modelo | https://www.youtube.com/watch?v=RlQuVL6-qe8 | - | - | en | ok | 2026-11-12 |
| 3.7 | Comparar modelos | https://www.youtube.com/watch?v=0pP4EwWJgIU | - | - | en | ok | 2026-11-12 |
| 3.8 | pandas, seaborn y scikit-learn | https://www.youtube.com/watch?v=3ZWuPVWq7p4 | - | - | en | ok | 2026-11-12 |
| 3.9 | Validación cruzada | https://www.youtube.com/watch?v=6dbrR-WymjI | - | - | en | ok | 2026-11-12 |
| 3.10 | Buscar los mejores parámetros | https://www.youtube.com/watch?v=Gol_qOgRqfA | - | - | en | ok | 2026-11-12 |
| 3.11 | Evaluar un clasificador | https://www.youtube.com/watch?v=85dtiMz9tSo | - | - | en | ok | 2026-11-12 |
| 3.12 | Flujo de trabajo completo | https://www.youtube.com/watch?v=irHhDMbw3xo | - | - | en | ok | 2026-11-12 |

Notas: los videos de Data School son de 2015; la descripción de cada clase debe avisar que algunas funciones cambiaron de nombre (p. ej. `sklearn.cross_validation` → `sklearn.model_selection`). 3.12: ver "Cambios frente al brief" punto 2. Los tres hermanos de la serie Rafa Gonzalez Gouveia también existen: Python para Data Science `fYZsuJb5VqE` (#01), Jupyter `CwbMaSkKDZg`, funciones y paquetes `1DOSQuEwYwg` (#06).
Extra (LessonLink): StatQuest "A Gentle Introduction to Machine Learning" https://www.youtube.com/watch?v=Gv9_4yMHFhI (200). Lista Data School https://www.youtube.com/playlist?list=PL5-da3qGB5ICeMbQuqbbCOQWcS6OYBr5A (200) · notebooks https://github.com/justmarkham/scikit-learn-videos (200).

## Módulo 4 · Redes neuronales (3Blue1Brown Español, Aprendizaje Profundo caps. 1–4 · es)

| # | Clase | URL | start_s | end_s | lang | status | fecha |
|---|---|---|---|---|---|---|---|
| 4.1 | ¿Qué es una red neuronal? | https://www.youtube.com/watch?v=jKCQsndqEGQ | - | - | es | ok | 2026-11-12 |
| 4.2 | Descenso del gradiente | https://www.youtube.com/watch?v=mwHiaTrQOiI | - | - | es | ok | 2026-11-12 |
| 4.3 | Backpropagation: la idea | https://www.youtube.com/watch?v=ScVpPS_CFYc | - | - | es | ok | 2026-11-12 |
| 4.4 | Backpropagation: el cálculo | https://www.youtube.com/watch?v=CyPjDPKtycM | - | - | es | ok | 2026-11-12 |

Originales en inglés (extra, 200): `aircAruvnKk`, `IHZwWFHWa-w`, `Ilg3gGewQ5U`, `tIeHLnjs5U8`. Lista https://www.youtube.com/playlist?list=PLZHQObOWTQDNU6R1_67000Dx_ZCJB-3pi (200). Alternativa en español (extra, 200): DotCSV "¿Qué es una Red Neuronal?" parte 1 https://www.youtube.com/watch?v=MRIv2IwFTPg · parte 2 https://www.youtube.com/watch?v=uwbHOpp9xkc.

## Módulo 5 · Construirlo en código (Karpathy, Zero to Hero · en)

Cada video se parte en 2–3 clases en los capítulos de su descripción de YouTube; `end_s` es el inicio del capítulo siguiente y el último tramo termina en la duración real (`lengthSeconds`). Todos en inglés ("Andrej Karpathy").

| # | Clase | URL | start_s | end_s | lang | status | fecha |
|---|---|---|---|---|---|---|---|
| 5.1a | micrograd: derivadas y el objeto Value | https://www.youtube.com/watch?v=VMj-3S1tku0 | 0 | 3172 | en | ok | 2026-11-12 |
| 5.1b | micrograd: backpropagation de una neurona | https://www.youtube.com/watch?v=VMj-3S1tku0 | 3172 | 5971 | en | ok | 2026-11-12 |
| 5.1c | micrograd: PyTorch y una red multicapa | https://www.youtube.com/watch?v=VMj-3S1tku0 | 5971 | 8752 | en | ok | 2026-11-12 |
| 5.2a | makemore: bigramas contando | https://www.youtube.com/watch?v=PaCmpygFfXo | 0 | 3777 | en | ok | 2026-11-12 |
| 5.2b | makemore: bigramas con una red neuronal | https://www.youtube.com/watch?v=PaCmpygFfXo | 3777 | 7065 | en | ok | 2026-11-12 |
| 5.3a | makemore 2: MLP, el modelo | https://www.youtube.com/watch?v=TCH_1BHY58I | 0 | 1937 | en | ok | 2026-11-12 |
| 5.3b | makemore 2: MLP, entrenamiento y experimentos | https://www.youtube.com/watch?v=TCH_1BHY58I | 1937 | 4539 | en | ok | 2026-11-12 |
| 5.4a | makemore 3: pérdida inicial y activaciones | https://www.youtube.com/watch?v=P6sfmUTpUmc | 0 | 2440 | en | ok | 2026-11-12 |
| 5.4b | makemore 3: BatchNorm | https://www.youtube.com/watch?v=P6sfmUTpUmc | 2440 | 4715 | en | ok | 2026-11-12 |
| 5.4c | makemore 3: visualizar activaciones y gradientes | https://www.youtube.com/watch?v=P6sfmUTpUmc | 4715 | 6957 | en | ok | 2026-11-12 |
| 5.5a | makemore 4: backprop a mano, parte 1 (opcional) | https://www.youtube.com/watch?v=q8SA3rM6ckI | 0 | 3917 | en | ok | 2026-11-12 |
| 5.5b | makemore 4: backprop a mano, parte 2 (opcional) | https://www.youtube.com/watch?v=q8SA3rM6ckI | 3917 | 6924 | en | ok | 2026-11-12 |
| 5.6 | makemore 5: WaveNet | https://www.youtube.com/watch?v=t3YJ5hKiMQ0 | - | - | en | ok | 2026-11-12 |

Capítulos usados (de la descripción): 5.1 `00:52:52` neurona · `01:39:31` comparación con PyTorch · 5.2 `01:02:57` PART 2 · 5.3 `00:32:17` resumen de la red · 5.4 `00:40:40` batch normalization · `01:18:35` PyTorch-ificar el código · 5.5 `01:05:17` digresión de Bessel · 5.6 dura 3381 s (56 min), se deja entera. Código: https://github.com/karpathy/nn-zero-to-hero (200) · https://karpathy.ai/zero-to-hero.html (200).

## Módulo 6 · Transformers: entender y construir un GPT (en)

| # | Clase | URL | start_s | end_s | lang | status | fecha |
|---|---|---|---|---|---|---|---|
| 6.1 | Transformers, la tecnología detrás de los LLMs | https://www.youtube.com/watch?v=wjZofJX0v4M | - | - | en | ok | 2026-11-12 |
| 6.2 | La atención en los transformers | https://www.youtube.com/watch?v=eMlx5fFNoYc | - | - | en | ok | 2026-11-12 |
| 6.3 | Construyamos GPT desde cero | https://www.youtube.com/watch?v=kCc8FmEb1nY | - | - | en | ok | 2026-11-12 |
| 6.4 | Construir el tokenizador de GPT | https://www.youtube.com/watch?v=zduSFxRajkE | - | - | en | ok | 2026-11-12 |
| 6.5 | Cómo guardan datos los LLMs | https://www.youtube.com/watch?v=9-Jl0dxWQs8 | - | - | en | ok | 2026-11-12 |

6.1, 6.2 y 6.5 son 3Blue1Brown, caps. 5–7 de Deep Learning; no hay doblaje en español de esos tres. Repaso en español (LessonLink): serie "GPT desde cero" del canal AI Explicada https://www.youtube.com/@ai.explicada (200) · notebooks https://github.com/maximiranda/gpt-desde-cero (200). Se vio la parte 3 ("LA ATENCIÓN", `HUbdN5XAyZI`); el brief dice eps. 1–3, el canal confirma al menos la 3.

## Módulo 7 · De GPT a ChatGPT (Karpathy · en)

"Deep Dive into LLMs like ChatGPT" (`7xTGNNLPyMI`, Andrej Karpathy), 12 683 s. 4 tramos con sus capítulos.

| # | Clase | URL | start_s | end_s | lang | status | fecha |
|---|---|---|---|---|---|---|---|
| 7.1 | Preentrenamiento: datos, tokens y red neuronal | https://www.youtube.com/watch?v=7xTGNNLPyMI | 0 | 3563 | en | ok | 2026-11-12 |
| 7.2 | Post-entrenamiento y alucinaciones | https://www.youtube.com/watch?v=7xTGNNLPyMI | 3563 | 7648 | en | ok | 2026-11-12 |
| 7.3 | Aprendizaje por refuerzo: DeepSeek-R1 y AlphaGo | https://www.youtube.com/watch?v=7xTGNNLPyMI | 7648 | 10106 | en | ok | 2026-11-12 |
| 7.4 | RLHF y qué esperar | https://www.youtube.com/watch?v=7xTGNNLPyMI | 10106 | 12683 | en | ok | 2026-11-12 |

Capítulos: `00:59:23` pretraining to post-training · `02:07:28` supervised finetuning to reinforcement learning · `02:48:26` reinforcement learning from human feedback (RLHF).

## Módulo 8 · Usar LLMs: Hugging Face, RAG y modelos locales

| # | Clase | URL | start_s | end_s | lang | status | fecha |
|---|---|---|---|---|---|---|---|
| 8.1a | Hugging Face: la función pipeline | https://www.youtube.com/watch?v=tiZFewofSLM | - | - | en | ok | 2026-11-12 |
| 8.1b | Hugging Face: la arquitectura Transformer | https://www.youtube.com/watch?v=H39Z_720T5s | - | - | en | ok | 2026-11-12 |
| 8.1c | Hugging Face: tokenizadores, visión general | https://www.youtube.com/watch?v=VFp38yj8h3A | - | - | en | ok | 2026-11-12 |
| 8.1d | Hugging Face: la API Trainer | https://www.youtube.com/watch?v=nvBXf7s7vTI | - | - | en | ok | 2026-11-12 |
| 8.2 | RAG de punta a punta, parte 1 | https://www.youtube.com/watch?v=qjgQUs4eJ34 | - | - | es | ok | 2026-11-12 |
| 8.3 | RAG de punta a punta, parte 2 | https://www.youtube.com/watch?v=cIf-ITLsYBk | - | - | es | ok | 2026-11-12 |
| 8.4 | Ollama: LLMs locales | https://www.youtube.com/watch?v=xE_msdWg3Pg | - | - | es | sustituto | 2026-11-12 |
| 8.5 | LM Studio en español | https://www.youtube.com/watch?v=X95qSmkigco | - | - | es | ok | 2026-11-12 |

- **8.1a–d:** canal oficial Hugging Face. Salen de la lista que enlaza la página del curso (https://youtube.com/playlist?list=PLo2EIpI_JMQvWfQndUesu0nPBAtZ9gP1o, 200). Son del curso original (2021–22): sirven para pipeline, arquitectura, tokenización y fine-tuning, pero no cubren los capítulos nuevos de LLMs. Se usaron las variantes de PyTorch; las de TensorFlow se omiten. Extras: `1pedAIvTWXk` (qué pasa dentro de pipeline), `00GKzGyWFEs` (bienvenida), https://huggingface.co/learn/llm-course (200).
- **8.2 y 8.3:** canal "The Machine Learning Engineer", título exacto "RAG: E2E App. Habla con tu data no estructurada Parte 1/2 (Español)", 59:35 y 1:18:38. Existe una parte 3 de 31:22 (`J2vQapnbFGU`) como enlace extra.
- **8.4 sustituto:** el video de "Aprende Ollama en 15 minutos" no apareció. Sustituto: "Aprende Ollama en menos de 8 minutos!" de CodelyTV (7:57, publicado hace unos 2 años: puede estar desactualizado, Ollama cambia rápido). Alternativas vigentes que un humano puede preferir: Nichonauta "IA Local con Ollama" `uGQ5aJt7RZU` (17:03, reciente) y Apasoft Training "Curso de OLLAMA 2026" `FFjvZV05vxM` (54:29). Hasta que alguien lo vea queda en borrador.
- **8.5:** canal "LLM Master", título "LM Studio Tutorial en Español…". Disponible.

## Módulo 9 · LLMs en la Jetson

Video oficial de NVIDIA para la clase introductoria (decisión humana, pregunta abierta 4); el resto, como enlaces.

| # | Clase | URL | start_s | end_s | lang | status | fecha |
|---|---|---|---|---|---|---|---|
| 9.1 | Primeros pasos con el kit de desarrollo Jetson Orin Nano | https://www.youtube.com/watch?v=VWdJ4BCtam8 | - | - | es | ok | 2026-11-12 |

- **9.1:** canal "NVIDIA Developer", 4:54, en español. Es introducción al kit, no un tutorial de LLMs; los LLMs van en los enlaces. Un humano debe verlo antes de publicar.
- Extra oficial: NVIDIA "Presentamos NVIDIA Jetson Orin Nano Super" https://www.youtube.com/watch?v=S9L2WGf1KrM (2:05, es).
- Enlaces (LessonLink): tutoriales oficiales https://www.jetson-ai-lab.com/tutorials/ (200) · Ollama en Jetson https://www.jetson-ai-lab.com/tutorials/ollama (200) · Paul McWhorter https://toptechboy.com/tag/llm/ (200, contenido no revisado).
- No verificado: https://la.blogs.nvidia.com/?p=6761 (403 a `curl`).
- Advertencia del brief que se mantiene: el curso gratis de NVIDIA DLI "Getting Started with AI on Jetson Nano" **no** es compatible con la Orin Nano; no prometer certificado sin confirmar el modelo del kit.

## Totales

- Clases en el catálogo: **M1** 10 · **M2** 8 · **M3** 12 · **M4** 4 · **M5** 13 · **M6** 5 · **M7** 4 · **M8** 8 · **M9** 1 = **65 clases**, 64 `ok` y 1 `sustituto` (8.4).
- Las 65 filas tienen URL; no queda ninguna sin resolver.
- Los 46 IDs de YouTube distintos usados como clase devuelven 200 en oembed.

## Huecos conocidos (fuera del alcance de video v1)

Ética, sesgos y seguridad → sesión en vivo del club (evento, no clase). Videos propios de Jetson → cuando el club los grabe.
