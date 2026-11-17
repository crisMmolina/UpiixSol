# Seguridad de dependencias

Registro breve de avisos de seguridad en dependencias y cómo se resolvieron.

## 2026-11-17 · picomatch · GHSA-fc5q-39xc-vjpf (UPS-082)

- **Aviso:** https://github.com/advisories/GHSA-fc5q-39xc-vjpf · severidad alta · ReDoS con extglobs repetidos de una sola rama.
- **Versiones afectadas:** `picomatch <= 4.0.7`. **Versión corregida:** ninguna publicada a la fecha (`first_patched_version: null`).
- **Ruta:** `@tailwindcss/vite` → `vite@8` → `tinyglobby` → `fdir` → `picomatch@4.0.7`. Hacía fallar `npm --prefix web audit --omit=dev --audit-level=high` en el job `web` de CI.
- **Arreglo:** `@tailwindcss/vite` y `tailwindcss` pasan de `dependencies` a `devDependencies` en `web/package.json`. Solo se usan al compilar (`vite.config.ts`, `src/index.css`); nada en tiempo de ejecución los importa. El árbol de producción ya no contiene vite ni picomatch, y la auditoría pasa sin debilitarse.
- **Por qué así:** era la opción (a) de la tarea. Fijar picomatch con `overrides` (opción b) no era posible porque no existe versión corregida. Se descartó `npm audit fix --force`: baja vite a 6.2.7 (cambio incompatible). Vite sigue en `^8`.
- **Riesgo residual:** picomatch vulnerable sigue en el árbol de desarrollo (build local, CI y la etapa `web-build` del Dockerfile, que ejecuta `npm ci` con devDependencies). Solo procesa globs del propio repositorio, no entradas de usuarios. Revisar cuando picomatch publique una versión corregida.
