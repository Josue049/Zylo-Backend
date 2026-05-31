# Zylo Backend

Backend FastAPI listo para desarrollo con autenticación por sesión, catálogo de negocios, reservas, mensajes y notificaciones.

## Ejecutar

```bash
python3 -m pip install --break-system-packages fastapi sqlalchemy psycopg pydantic-settings python-multipart uvicorn
uvicorn app.main:app --reload
```

## Base de datos

La app lee la conexión desde `.env` o el entorno. Copia `.env.example` a `.env` y coloca ahí tus credenciales reales.

Ejemplo:

```env
DATABASE_URL=postgresql+psycopg://<usuario>:<contraseña>@<host>:<puerto>/<base_de_datos>
CLOUDINARY_CLOUD_NAME=<tu_cloud_name>
CLOUDINARY_API_KEY=<tu_api_key>
CLOUDINARY_API_SECRET=<tu_api_secret>
CLOUDINARY_UPLOAD_FOLDER=zylo/profile_photos
```

Si usas el endpoint de foto de perfil (`POST /users/me/photo`), la imagen se sube a Cloudinary por API y se guarda `secure_url` en `users.photo_url`.

## Credenciales demo

- Cliente: `client@zylo.test` / `Demo1234!`
- Negocio: `business@zylo.test` / `Demo1234!`

## Alcance

El proyecto incluye todos los endpoints solicitados con SQLAlchemy y creación automática de tablas al arrancar.
