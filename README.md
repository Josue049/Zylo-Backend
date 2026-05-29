# Zylo Backend

Backend FastAPI listo para desarrollo con autenticación por sesión, catálogo de negocios, reservas, mensajes y notificaciones.

## Ejecutar

```bash
python3 -m pip install --break-system-packages fastapi sqlalchemy psycopg pydantic-settings python-multipart uvicorn
uvicorn app.main:app --reload
```

## Base de datos

Por defecto la app usa SQLite local para desarrollo, pero puedes conectarla a PostgreSQL definiendo `DATABASE_URL` en `.env` o en el entorno.

Ejemplo:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/zylo
```

## Credenciales demo

- Cliente: `client@zylo.test` / `Demo1234!`
- Negocio: `business@zylo.test` / `Demo1234!`

## Alcance

El proyecto incluye todos los endpoints solicitados con SQLAlchemy y creación automática de tablas al arrancar.