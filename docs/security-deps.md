# Seguridad de dependencias

Registro breve de avisos de seguridad en dependencias y cómo se resolvieron.

## 2026-11-17 · picomatch · GHSA-fc5q-39xc-vjpf (UPS-082)

- **Aviso:** https://github.com/advisories/GHSA-fc5q-39xc-vjpf · severidad alta · ReDoS con extglobs repetidos de una sola rama.
- **Versiones afectadas:** `picomatch <= 4.0.7`. **Versión corregida:** ninguna publicada a la fecha (`first_patched_version: null`).
- **Ruta:** `@tailwindcss/vite` → `vite@8` → `tinyglobby` → `fdir` → `picomatch@4.0.7`. Hacía fallar `npm --prefix web audit --omit=dev --audit-level=high` en el job `web` de CI.
- **Arreglo:** `@tailwindcss/vite` y `tailwindcss` pasan de `dependencies` a `devDependencies` en `web/package.json`. Solo se usan al compilar (`vite.config.ts`, `src/index.css`); nada en tiempo de ejecución los importa. El árbol de producción ya no contiene vite ni picomatch, y la auditoría pasa sin debilitarse.
- **Por qué así:** era la opción (a) de la tarea. Fijar picomatch con `overrides` (opción b) no era posible porque no existe versión corregida. Se descartó `npm audit fix --force`: baja vite a 6.2.7 (cambio incompatible). Vite sigue en `^8`.
- **Riesgo residual:** picomatch vulnerable sigue en el árbol de desarrollo (build local, CI y la etapa `web-build` del Dockerfile, que ejecuta `npm ci` con devDependencies). Solo procesa globs del propio repositorio, no entradas de usuarios. Revisar cuando picomatch publique una versión corregida.

## 2026-11-18 · resvg-py 0.5.0 · dependencia nueva (UPS-099)

- **Paquete:** `resvg-py` 0.5.0 (PyPI), enlace Python del renderizador Rust `resvg`. **Licencia:** MIT. **Fuente:** https://github.com/baseplate-admin/resvg-py (proyecto pequeño, ~30 estrellas, último push 2026-11-10). Ruedas precompiladas para manylinux x86_64 y macOS arm64, Python ≥ 3.10.
- **Por qué:** ningún cliente de correo muestra SVG y el logo del sitio es SVG. El servidor rasteriza una copia PNG solo para los correos (`app/services/mail_images.py`); el sitio sigue sirviendo el SVG.
- **Mitigaciones:** solo se renderizan SVG que pasan `media._svg_is_safe` (sin `href` externos, sin scripts), con tope de 512 KB, sin fuentes del sistema ni `resources_dir`; cualquier fallo devuelve `None` y el correo muestra el nombre en texto.
- **Despliegue:** `uv sync --locked` en el Dockerfile (python:3.12-slim, glibc) instala la rueda manylinux; no hay paso de compilación.
- **Riesgo residual:** dependencia con pocos mantenedores; el código nativo parsea SVG de superadmin ya validado. Revisar avisos de seguridad de `resvg` al actualizar.
