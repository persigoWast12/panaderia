# Panadería — MVP

Sistema de gestión para una panadería de barrio: login por roles, productos con stock y registro de ventas en el mostrador. Reemplaza el cuaderno de ventas y stock.

El proyecto se construye por etapas. Estado actual:

| Etapa | Estado |
|---|---|
| 1. Estructura del backend | ✅ |
| 2. Modelos, tablas y seed | ✅ |
| 3. Login y sesiones | ✅ |
| 4. Productos y stock | ✅ |
| 5. Ventas | ⏳ |
| 6. Frontend | ⏳ |
| 7. Pruebas del flujo completo | ⏳ |

Hoy el backend ya crea las tablas, carga los datos de ejemplo, tiene login con sesiones y roles, y permite consultar y administrar productos y stock. Todavía no registra ventas.

## Requisitos

- **Python 3.13**
- **PostgreSQL 17** (la base se administra con pgAdmin 4)
- **Node.js 24** (se usa recién en la etapa 6, para el frontend)

## Base de datos

La aplicación **no crea la base**, solo las tablas. La base `panaderia` tiene que existir antes de arrancar.

Si todavía no existe, se puede crear desde pgAdmin o con `psql`:

```powershell
$env:PGPASSWORD='TU_CLAVE'
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost `
  -c "CREATE DATABASE panaderia ENCODING 'UTF8'"
```

La conexión se configura con la variable `DATABASE_URL`, por ejemplo:

```
postgresql+psycopg://postgres:TU_CLAVE@localhost:5432/panaderia
```

## Backend

### Instalación

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

`requirements-dev.txt` incluye también `pytest` y `httpx`, que se usan en la etapa 7. Para correr solo la aplicación alcanza con `requirements.txt`.

### Variables de entorno

```powershell
Copy-Item .env.example .env
```

Después editar `backend/.env`:

```
DATABASE_URL=postgresql+psycopg://postgres:TU_CLAVE@localhost:5432/panaderia
COOKIE_SECURE=false
SESSION_HOURS=12
```

- `COOKIE_SECURE` controla el flag `Secure` de la cookie de sesión. En la red local (HTTP) va en `false`.
- `SESSION_HOURS` define cuántas horas dura una sesión (por defecto 12).
- El archivo `.env` real está ignorado por git; nunca se sube.

### Arranque

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Al iniciar, la aplicación:

1. Crea las tablas si no existen (`create_all`).
2. Carga el seed **solo si la base está vacía** (si no hay ningún empleado).
3. Borra las sesiones vencidas.
4. Queda escuchando en `http://127.0.0.1:8000`.

Hay que correr **un solo worker**. Con dos procesos, los dos podrían intentar cargar el seed a la vez.

### Usuarios de prueba

| Usuario | Contraseña | Rol |
|---|---|---|
| `cajero1` | `cajero123` | cajero |
| `encargado1` | `encargado123` | encargado |

Las contraseñas se guardan con hash bcrypt; las de la tabla son solo para desarrollo.

El seed también carga 2 proveedores y 10 productos de panadería con stock inicial.

### Login y sesiones

El login se hace con `POST /login`:

```powershell
# Guarda la cookie de sesión en $sesion
$sesion = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Uri http://127.0.0.1:8000/login -Method Post `
  -WebSession $sesion -ContentType "application/json" `
  -Body '{"usuario":"cajero1","password":"cajero123"}'
```

Si las credenciales son correctas, devuelve un objeto con `nombre` y `rol`, y setea la cookie `session`. La cookie es `HttpOnly`, `SameSite=Lax`, `Path=/` y dura `SESSION_HOURS` horas.

En la tabla `sesion` se guarda **solo el hash SHA-256 del token**, nunca el token en claro. `POST /logout` borra la fila de la sesión actual y la cookie, y las sesiones vencidas se limpian al arrancar el servidor.

Los roles son `cajero` y `encargado`. Los endpoints protegidos usan la dependencia `require_rol(...)` y responden `403` si el rol no coincide.

### Endpoints disponibles

| Método y ruta | Qué hace |
|---|---|
| `GET /test` | Endpoint de prueba: responde `{"status":"ok"}` |
| `POST /login` | Inicia sesión: devuelve rol y nombre, y setea la cookie `session` |
| `POST /logout` | Cierra la sesión actual y borra la cookie |
| `GET /me` | Devuelve nombre y rol del empleado autenticado |
| `GET /productos?q=` | Lista productos activos con su stock; `q` busca por nombre |
| `GET /productos/codigo/{codigo}` | Busca un producto por código de barras (incluye inactivos) |
| `POST /productos` | Crea un producto y su stock (solo encargado) |
| `PUT /productos/{id}` | Modifica nombre, precio, unidad, código o estado (solo encargado) |
| `GET /stock` | Lista el stock de todos los productos, incluidos los inactivos |
| `PUT /stock/{producto_id}` | Fija la cantidad disponible (solo encargado) |
| `GET /docs` | Documentación automática de FastAPI |

Los endpoints de ventas se agregan en la etapa 5.

### Probar que está vivo

```powershell
Invoke-RestMethod http://127.0.0.1:8000/test
```

### Probar el login

```powershell
# /me con la sesión guardada por el login
Invoke-RestMethod -Uri http://127.0.0.1:8000/me -WebSession $sesion

# Logout y reintento: el último comando debe fallar con 401
Invoke-RestMethod -Uri http://127.0.0.1:8000/logout -Method Post -WebSession $sesion
Invoke-RestMethod -Uri http://127.0.0.1:8000/me -WebSession $sesion
```

### Productos y stock

El cajero puede consultar productos y stock, pero no modificarlos. El encargado puede crear y editar productos y ajustar el stock; si el cajero intenta modificar, recibe `403`. Para las operaciones de escritura, iniciá sesión con `encargado1` y guardá la cookie en `$sesion`.

```powershell
# Listar y buscar (cajero o encargado)
Invoke-RestMethod -Uri "http://127.0.0.1:8000/productos?q=pan" -WebSession $sesion
Invoke-RestMethod -Uri http://127.0.0.1:8000/productos/codigo/2000000000015 -WebSession $sesion

# Crear un producto (encargado)
Invoke-RestMethod -Uri http://127.0.0.1:8000/productos -Method Post `
  -WebSession $sesion -ContentType "application/json" `
  -Body '{"nombre":"Pan de nuez","codigo_barras":"2000000000114","unidad":"unidad","precio":1200,"cantidad_inicial":20}'

# Ajustar stock (usá el id que devolvió la creación)
Invoke-RestMethod -Uri http://127.0.0.1:8000/stock/11 -Method Put `
  -WebSession $sesion -ContentType "application/json" `
  -Body '{"cantidad_disponible":35.5}'
```

- `GET /productos` solo muestra productos activos.
- `GET /stock` muestra todos, con `activo` incluido.
- `GET /productos/codigo/{codigo}` devuelve también productos inactivos.
- El código de barras no se puede repetir.
- La unidad solo se puede corregir si el producto todavía no tiene ventas.

## Frontend

Pendiente (etapa 6). Será un proyecto Next.js con TypeScript y Tailwind, que llamará a `/api/...` y Next reenviará al backend.

## Pruebas

Pendientes (etapa 7). Se van a correr con `pytest` contra una base aparte, `panaderia_test`.

## Estructura

```
panaderia/
├── backend/
│   ├── main.py            # app FastAPI y arranque (tablas + seed)
│   ├── database.py        # conexión y sesión de SQLAlchemy
│   ├── models.py          # las 7 tablas
│   ├── security.py        # hash de contraseñas, tokens y dependencias de rol
│   ├── schemas.py         # esquemas de entrada y salida (Pydantic)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py        # /login, /logout, /me
│   │   ├── productos.py   # /productos
│   │   └── stock.py       # /stock
│   ├── seed.py            # datos de ejemplo
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
├── docs/                  # documentación personal (ignorada por git)
├── .gitignore
└── README.md
```

## Notas

- **No se usa Alembic.** Si cambia el modelo de datos, hay que borrar las tablas y dejar que `create_all` las vuelva a crear.
- Las fechas de venta se guardan en **hora local**, sin zona horaria, porque el sistema corre en una sola sucursal.
- Los productos y empleados no se borran: se desactivan con `activo = false`.
- La carpeta `docs/` es de uso personal y está excluida del repositorio.
