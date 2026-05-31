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
```

## Credenciales demo

- Cliente: `client@zylo.test` / `Demo1234!`
- Negocio: `business@zylo.test` / `Demo1234!`

## Alcance

El proyecto incluye todos los endpoints solicitados con SQLAlchemy y creación automática de tablas al arrancar.
