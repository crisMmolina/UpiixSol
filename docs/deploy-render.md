# Despliegue gratis en internet · Render + Neon (UPS-030)

UpiixSol corre en un solo contenedor en Render, con el plan free, y usa Postgres en Neon, también con el plan free. La guía usa solo los planes gratuitos de los dos. Las imágenes que suben los usuarios se guardan en el mismo Postgres (`MEDIA_STORAGE=database`), porque Render borra el disco del plan free en cada reinicio.

El stack de Docker Compose con nginx (`docs/runbook.md`) sigue igual para un servidor propio. Esta guía cubre solo la opción gratuita.

## 1. Base de datos en Neon (≈5 min)
1. Crea una cuenta en <https://neon.com> (con GitHub o con correo).
2. **New project**: ponle de nombre `upiixsol` y elige la región **AWS US East 2 (Ohio)**, la misma que `render.yaml`.
3. **Connect**: deja **Connection pooling** apagado y copia la cadena de conexión directa (el host no lleva `-pooler`). Se ve así:
   `postgresql://usuario:clave@ep-….us-east-2.aws.neon.tech/neondb?sslmode=require`
   La app ya mantiene su propio pool de conexiones, y la conexión directa evita sorpresas del pooler con las migraciones.
   Es un secreto: no la pegues en chats, issues ni en el repo.

## 2. Servicio web en Render (≈10 min, casi todo es el primer build)
1. Crea una cuenta en <https://render.com> con GitHub.
2. Ve a **New → Blueprint**, elige el repositorio `crisMmolina/UpiixSol` en la rama `main` y Render lee `render.yaml`. Si el repo no aparece, dale acceso a Render desde GitHub (*Configure GitHub App*). Así, además, cada merge a `main` se despliega solo.
3. Render te pide una sola variable, `DATABASE_URL`: pega la cadena de Neon. No necesitas cambiar `postgresql://`, porque el contenedor agrega el driver. Render genera solo `JWT_SECRET` y `SEED_DEFAULT_PASSWORD`.
4. Da clic en **Apply**. El primer build tarda varios minutos. Al arrancar, el contenedor:
   - aplica las migraciones;
   - siembra las 6 cuentas y el contenido de demostración;
   - escribe `SEED_OK … accounts=6` en **Logs**.

## 3. Verifica
Reemplaza `<servicio>` por la URL que te dio Render, p. ej. `upiixsol.onrender.com`.
- `https://<servicio>/api/health` → `{"status":"ok"}`
- `https://<servicio>/api/ready` → `{"status":"ready"}` (la base responde)
- `https://<servicio>/api/docs` → 404 (en producción la documentación está apagada)
- Entra con `superadmin1@upiixsol.dev`. Su contraseña es el valor de `SEED_DEFAULT_PASSWORD` (Render → servicio → **Environment** → ojo para verlo). La app te lleva directo a cambiarla, y la API no deja hacer nada más hasta que lo hagas.

## 4. Después del primer arranque
1. En **Environment** pon `SEED_ON_START=false` y guarda; Render vuelve a desplegar. Si lo dejas en `true`, cada arranque vuelve a crear el contenido de demostración que hayas borrado.
2. Reparte o desactiva las otras cuentas sembradas, como en `docs/runbook.md` §6:
   - `superadmin2`, `superadmin3` y `superadmin4`;
   - `admin.ia`;
   - `alumno.demo`.
3. Cambia también `SEED_DEFAULT_PASSWORD` a un valor nuevo. Las cuentas que ya existen no cambian con esto: solo evita que un seed accidental use el valor que ya se compartió. Cada cuenta cambia su contraseña desde la app.

## 5. Actualizar y respaldar
- Con el repo conectado, cada merge a `main` redepliega solo. Si no, usa **Manual Deploy → Deploy latest commit**. Las migraciones nuevas se aplican al arrancar.
- **Respaldo:** usa `pg_dump` con la cadena directa de Neon, p. ej. `pg_dump "<cadena directa>" -Fc -f upiixsol-$(date +%F).dump`. Las imágenes viajan dentro del dump, en `media_objects`.

## Lo que implica el plan gratis
| Tema | Qué esperar |
|---|---|
| **Render se duerme** | Tras 15 min sin visitas el servicio se apaga, y la siguiente visita tarda cerca de un minuto en abrir. Render Starter (USD 7/mes) quita esto. |
| **Horas de Render** | 750 h al mes por workspace: alcanzan para un servicio encendido todo el mes, no para dos. |
| **Recursos de Render** | 512 MB de RAM y 0.1 CPU. Sirve para una demo o un club pequeño; Render no recomienda el plan free para producción. |
| **Tamaño de Neon** | 0.5 GB por proyecto; algunos reportes de 2026 dicen 1 GB, revisa tu panel. Las imágenes cuentan: ya llegan redimensionadas y en WebP, de decenas a pocos cientos de KB cada una. |
| **Neon en reposo** | El cómputo se suspende tras 5 min sin consultas, y la primera consulta después tarda un poco más. |
| **Cuotas de Neon** | El plan free también limita las horas de cómputo y la transferencia al mes. Servir imágenes desde la base cuenta para las dos; revisa el consumo en el panel de Neon. |
| **Límite por IP** | Detrás del proxy de Render alguien puede falsear su IP para el límite por IP (`FORWARDED_ALLOW_IPS="*"`). El límite por correo del login sigue funcionando. |

Los límites de los planes cambian seguido: confírmalos en las páginas de precios de Render y Neon antes de depender de ellos.
