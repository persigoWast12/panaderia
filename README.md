# Panadería — MVP

Sistema de gestión para una panadería de barrio: login por roles, productos con stock, registro de ventas en el mostrador, consulta de ventas y administración de empleados. Reemplaza el cuaderno de ventas y stock.

El proyecto se construye por etapas. Estado actual:

| Etapa | Estado |
|---|---|
| 1. Estructura del backend | ✅ |
| 2. Modelos, tablas y seed | ✅ |
| 3. Login y sesiones | ✅ |
| 4. Productos y stock | ✅ |
| 5. Ventas | ✅ |
| 6. Frontend | ✅ |
| 7. Pruebas del flujo completo | ✅ |

La aplicación ya crea las tablas, carga los datos de ejemplo, tiene login con sesiones y cuatro roles, administra productos y stock, registra ventas y cuenta con el frontend completo: caja, productos, consulta de ventas y empleados.

## Requisitos

- **Python 3.13**
- **PostgreSQL 17** (la base se administra con pgAdmin 4)
- **Node.js 24** (para el frontend)

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

`requirements-dev.txt` incluye también `pytest` y `httpx`, que se usan en las pruebas. Para correr solo la aplicación alcanza con `requirements.txt`.

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
| `dueno1` | `dueno123` | dueño |

Las contraseñas se guardan con hash bcrypt; las de la tabla son solo para desarrollo.

El seed también carga 2 proveedores y 10 productos de panadería con stock inicial.

Al desplegar, entrar con `dueno1`, cambiar esa contraseña desde **Empleados**, crear las cuentas reales y desactivar los usuarios de prueba. Los empleados no se borran: se desactivan para conservar sus ventas.

### Login y sesiones

El login se hace con `POST /login`:

```powershell
# Guarda la cookie de sesión en $sesion
$sesion = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Uri http://127.0.0.1:8000/login -Method Post `
  -WebSession $sesion -ContentType "application/json" `
  -Body '{"usuario":"cajero1","password":"cajero123"}'
```

Si las credenciales son correctas, devuelve un objeto con `id`, `nombre`, `usuario` y `rol`, y setea la cookie `session`. La cookie es `HttpOnly`, `SameSite=Lax`, `Path=/` y dura `SESSION_HOURS` horas.

En la tabla `sesion` se guarda **solo el hash SHA-256 del token**, nunca el token en claro. `POST /logout` borra la fila de la sesión actual y la cookie, y las sesiones vencidas se limpian al arrancar el servidor.

Los roles son:

| Rol | Qué puede hacer |
|---|---|
| `cajero` | Vender, consultar productos y stock. |
| `encargado` | Administrar productos y stock. No vende. |
| `contador` | Solo consultar ventas. |
| `dueno` | Todo lo del encargado, más consultar ventas y administrar empleados. No vende. |

Los endpoints protegidos usan la dependencia `require_rol(...)` y responden `403` si el rol no coincide.

### Endpoints disponibles

| Método y ruta | Qué hace |
|---|---|
| `GET /test` | Confirma que el servidor y la base de datos responden |
| `POST /login` | Inicia sesión: devuelve id, nombre, usuario y rol, y setea la cookie `session` |
| `POST /logout` | Cierra la sesión actual y borra la cookie |
| `GET /me` | Devuelve id, nombre, usuario y rol del empleado autenticado |
| `GET /productos?q=` | Lista productos activos con su stock; `q` busca por nombre (cajero, encargado y dueño) |
| `GET /productos/codigo/{codigo}` | Busca un producto por código de barras, incluidos los inactivos (cajero, encargado y dueño) |
| `POST /productos` | Crea un producto y su stock (encargado y dueño) |
| `PUT /productos/{id}` | Modifica nombre, precio, unidad, código o estado (encargado y dueño) |
| `GET /stock` | Lista todos los productos con precio, stock y si tienen ventas (cajero, encargado y dueño) |
| `PUT /stock/{producto_id}` | Fija la cantidad disponible (encargado y dueño) |
| `POST /ventas` | Registra una venta y descuenta stock (solo cajero) |
| `GET /ventas?fecha=` | Lista las ventas del día o de la fecha indicada (contador y dueño) |
| `GET /empleados` | Lista todos los empleados (solo dueño) |
| `POST /empleados` | Crea un empleado (solo dueño) |
| `PUT /empleados/{id}` | Edita nombre, usuario, rol o estado (solo dueño) |
| `PUT /empleados/{id}/password` | Resetea la contraseña y cierra las sesiones de ese empleado (solo dueño) |
| `GET /docs` | Documentación automática de FastAPI |

El frontend está en `frontend/`; las instrucciones están más abajo.

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

El cajero puede consultar productos y stock, pero no modificarlos. El encargado y el dueño pueden crear y editar productos y ajustar el stock; si el cajero intenta modificar, recibe `403`. Para las operaciones de escritura, iniciá sesión con `encargado1` o `dueno1` y guardá la cookie en `$sesion`.

```powershell
# Listar y buscar (cajero, encargado o dueño)
Invoke-RestMethod -Uri "http://127.0.0.1:8000/productos?q=pan" -WebSession $sesion
Invoke-RestMethod -Uri http://127.0.0.1:8000/productos/codigo/2000000000015 -WebSession $sesion

# Crear un producto (encargado o dueño)
Invoke-RestMethod -Uri http://127.0.0.1:8000/productos -Method Post `
  -WebSession $sesion -ContentType "application/json" `
  -Body '{"nombre":"Pan de nuez","codigo_barras":"2000000000114","unidad":"unidad","precio":1200,"cantidad_inicial":20}'

# Ajustar stock (usá el id que devolvió la creación)
Invoke-RestMethod -Uri http://127.0.0.1:8000/stock/11 -Method Put `
  -WebSession $sesion -ContentType "application/json" `
  -Body '{"cantidad_disponible":35.5}'
```

- `GET /productos` solo muestra productos activos.
- `GET /stock` muestra todos, con `activo`, `precio` y `tiene_ventas`.
- `GET /productos/codigo/{codigo}` devuelve también productos inactivos.
- El código de barras no se puede repetir.
- La unidad solo se puede corregir si el producto todavía no tiene ventas.

### Ventas

Solo el cajero registra ventas; el contador y el dueño pueden consultarlas. El backend calcula el total y descuenta el stock en una sola transacción: si falta stock, no se guarda nada.

```powershell
# Login como cajero (guardando la cookie en $sesion)
$sesion = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Uri http://127.0.0.1:8000/login -Method Post `
  -WebSession $sesion -ContentType "application/json" `
  -Body '{"usuario":"cajero1","password":"cajero123"}'

# Registrar una venta (no se manda el total)
Invoke-RestMethod -Uri http://127.0.0.1:8000/ventas -Method Post `
  -WebSession $sesion -ContentType "application/json" `
  -Body '{"forma_pago":"efectivo","items":[{"producto_id":1,"cantidad":1.250},{"producto_id":4,"cantidad":2}]}'

# Para consultar, iniciar sesión como contador o dueño
$consulta = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Uri http://127.0.0.1:8000/login -Method Post `
  -WebSession $consulta -ContentType "application/json" `
  -Body '{"usuario":"dueno1","password":"dueno123"}'

# Ventas de hoy o de una fecha
Invoke-RestMethod -Uri http://127.0.0.1:8000/ventas -WebSession $consulta
Invoke-RestMethod -Uri "http://127.0.0.1:8000/ventas?fecha=2026-10-31" -WebSession $consulta
```

- `forma_pago`: `efectivo`, `billetera_virtual` o `tarjeta`.
- Las cantidades de productos por `kg` aceptan decimales; las de `unidad` deben ser enteras.
- Si se manda un `total` en el cuerpo, se ignora.
- El precio unitario se copia del producto al momento de la venta.

### Empleados

Solo el dueño administra empleados. Las contraseñas se guardan con bcrypt y nunca se devuelven.

```powershell
# Login como dueño
$sesion = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Uri http://127.0.0.1:8000/login -Method Post `
  -WebSession $sesion -ContentType "application/json" `
  -Body '{"usuario":"dueno1","password":"dueno123"}'

# Listar empleados
Invoke-RestMethod -Uri http://127.0.0.1:8000/empleados -WebSession $sesion

# Crear un contador
Invoke-RestMethod -Uri http://127.0.0.1:8000/empleados -Method Post `
  -WebSession $sesion -ContentType "application/json" `
  -Body '{"nombre":"Contador","usuario":"contador1","rol":"contador","password":"contador123"}'

# Resetear una contraseña (usá el id que devolvió la lista o la creación)
Invoke-RestMethod -Uri http://127.0.0.1:8000/empleados/4/password -Method Put `
  -WebSession $sesion -ContentType "application/json" `
  -Body '{"password":"nueva123"}'
```

- Roles válidos: `cajero`, `encargado`, `contador` y `dueno`.
- Al desactivar a un empleado o resetear su contraseña, se cierran sus sesiones abiertas.
- El dueño no puede desactivarse a sí mismo ni cambiarse el rol.
- Los empleados no se borran: se desactivan para conservar sus ventas.

## Frontend

Está en `frontend/` y usa **Next.js 16** (App Router), **JavaScript (JSX)** y **Tailwind 4**. El navegador solo habla con `/api/...`; Next reenvía al backend usando `BACKEND_URL` (por defecto `http://127.0.0.1:8000`).

### Instalación y arranque

```powershell
cd frontend
npm install
npm run dev
```

Abrir `http://localhost:3000/login`.

Para usarlo en la red local conviene compilar y arrancar en modo producción:

```powershell
npm run build
npm start
```

Next muestra la dirección de red (por ejemplo `http://192.168.0.245:3000`). Las otras PC entran con esa URL. El backend puede seguir escuchando solo en `127.0.0.1:8000` porque Next lo llama desde la misma máquina.

Si desde la otra PC no carga, permitir Node.js en el Firewall de Windows para el puerto 3000.

Para cambiar el destino del backend, copiar `frontend/.env.local.example` a `frontend/.env.local` y editar `BACKEND_URL`.

### Pantallas

| Ruta | Quién entra | Qué hace |
|---|---|---|
| `/login` | Todos | Inicia sesión y redirige según el rol. |
| `/caja` | Cajero | Lector de códigos, búsqueda por nombre, carrito, kilos, total y cobro. |
| `/productos` | Encargado y dueño | Alta, edición, activación y ajuste de stock. |
| `/ventas` | Contador y dueño | Ventas por fecha, total del día y por forma de pago. |
| `/empleados` | Dueño | Alta, edición, activación, baja y reseteo de contraseña. |

El header muestra el nombre y el rol, y solo ofrece las secciones permitidas.

## Pruebas

Las pruebas usan PostgreSQL, igual que la aplicación, contra una base aparte (`panaderia_test`) para no tocar los datos de desarrollo.

Crear la base una sola vez:

```powershell
$env:PGPASSWORD='TU_CLAVE'
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost `
  -c "CREATE DATABASE panaderia_test"
```

Correr las pruebas:

```powershell
cd backend
$env:TEST_DATABASE_URL="postgresql+psycopg://postgres:TU_CLAVE@localhost:5432/panaderia_test"
.\.venv\Scripts\python.exe -m pytest -q
```

Son **42 pruebas** y cubren login y sesiones, los cuatro roles, productos y stock, ventas (incluida una prueba de dos ventas simultáneas) y administración de empleados.

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
│   │   ├── stock.py       # /stock
│   │   ├── ventas.py      # /ventas
│   │   └── empleados.py   # /empleados
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_productos.py
│   │   ├── test_ventas.py
│   │   └── test_empleados.py
│   ├── seed.py            # datos de ejemplo
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.jsx       # redirige según el rol
│   │   ├── login/
│   │   ├── caja/
│   │   ├── productos/
│   │   ├── ventas/
│   │   └── empleados/
│   ├── components/        # Header y modales
│   ├── lib/               # cliente HTTP, formato, roles y sesión
│   ├── next.config.mjs    # rewrite de /api
│   ├── package.json
│   └── .env.local.example
├── docs/                  # documentación personal (ignorada por git)
├── .gitignore
└── README.md
```

## Notas

- **No se usa Alembic.** Si cambia el modelo de datos, hay que borrar las tablas y dejar que `create_all` las vuelva a crear.
- Las fechas de venta se guardan en **hora local**, sin zona horaria, porque el sistema corre en una sola sucursal.
- Los productos y empleados no se borran: se desactivan con `activo = false`.
- Los roles se agregaron recreando las tablas, porque todavía no había datos reales. Si más adelante cambia el modelo y hay ventas que conservar, hay que migrar a mano o incorporar Alembic.
- El backend y el frontend tienen que correr en la misma PC: el navegador habla con Next y Next reenvía a `127.0.0.1:8000`.
- Para el uso real, cambiar la contraseña de `dueno1` y desactivar `cajero1` y `encargado1` desde la pantalla de empleados.
- **Backup recomendado**: programar un `pg_dump` diario de la base `panaderia` (por ejemplo, con el Programador de tareas de Windows). El MVP no incluye respaldos automáticos.
- La carpeta `docs/` es de uso personal y está excluida del repositorio.
