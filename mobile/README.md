# TechCare Pruebas — App Android (APK beta)

Envoltorio **WebView** nativo (Java, sin dependencias externas) que abre la web de
**pruebas** de TechCare. Es el equivalente móvil del `.exe` de la carpeta `desktop/`:
**solo abre la URL**, toda la lógica vive en el sitio web.

- **A dónde se conecta:** `http://192.168.10.6:451/` (servidor de pruebas, en la LAN).
  → **Solo funciona dentro del WiFi de ANA.** Fuera de la red muestra un aviso.
- **Firma:** APK de *depuración* (debug). Se instala por *sideload* (no Google Play).
- **Versión:** `app/build.gradle` → `versionName` / `versionCode` (hoy `7.9.98-beta`).

## Cómo se compila (no en el servidor: no tiene Android SDK)
Igual que el `.exe`: lo compila **GitHub Actions**.

1. Haz push de cambios en `mobile/**` a `main` **o** entra a la pestaña **Actions** del
   repo → *Build Mobile (Android APK)* → **Run workflow**.
2. Al terminar, el APK queda en el **Release** `mobile-v<versión>` y como artefacto
   *TechCare-Pruebas-Android*.

## Cómo se instala en el teléfono
1. Descarga el `.apk` del Release.
2. Ábrelo; Android pedirá permitir **"Instalar apps desconocidas"** para ese navegador
   o gestor de archivos (es normal sin Google Play). Acéptalo.
3. Instala y abre. Concede **cámara** y **fotos** cuando lo pida (para subir imágenes).

> **Nota sobre actualizar:** como es APK de depuración, al instalar una versión nueva
> puede pedir **desinstalar la anterior** primero. Si quieren actualizaciones "encima"
> sin desinstalar (como el `.exe`), hay que firmar con una llave estable (release
> keystore) — se puede agregar después.

## Cambiar la URL
Edita `app/src/main/res/values/strings.xml` → `app_url`.
Si apuntas a otra IP/host por HTTP, agrégalo también en
`app/src/main/res/xml/network_security_config.xml` (Android bloquea HTTP por defecto).
Para HTTPS (p. ej. producción) no hace falta tocar ese archivo.
