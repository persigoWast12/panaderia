# Manual de uso — Sistema de Panadería

**Versión:** 1.0  
**Fecha:** 13/11/2026  
**Tipo de sistema:** aplicación web de gestión de panadería

---

## Índice

**Parte 1 — Uso del sistema**

1. Introducción
2. Acceso al sistema
3. Roles y permisos
4. Caja
5. Productos y stock
6. Ventas
7. Empleados
8. Contador
9. Preguntas frecuentes
10. Glosario

**Parte 2 — Administración técnica**

11. Arquitectura general
12. Requisitos
13. Instalación desde cero
14. Arranque diario
15. Reiniciar la base
16. Backup y restore
17. Solución de problemas
18. Usuarios de prueba y límites
19. Referencia técnica

---

# Parte 1 — Uso del sistema

## 1. Introducción

El Sistema de Panadería permite reemplazar el cuaderno de ventas y stock por una aplicación web.

Sirve para:

- registrar ventas en el mostrador,
- consultar productos y stock,
- administrar productos,
- consultar las ventas del día,
- administrar empleados y contraseñas.

El sistema admite lector de códigos de barras y también ingreso manual. El código se puede escribir a mano y confirmar con Enter.

El sistema tiene cuatro roles:

- **Cajero:** vende y consulta productos/stock.
- **Encargado:** administra productos y stock.
- **Contador:** solo consulta ventas.
- **Dueño:** administra todo y además consulta ventas.

---

## 2. Acceso al sistema

Abrir en el navegador:

```text
http://localhost:3000/login
```

![Pantalla de inicio de sesión](img/01-login.png)

1. Escribir el **usuario**.
2. Escribir la **contraseña**.
3. Tocar **Entrar**.

El sistema redirige automáticamente según el rol:

- cajero → Caja,
- encargado → Productos,
- contador → Ventas,
- dueño → Productos.

Para cerrar sesión, usar el botón **Cerrar sesión** del encabezado.

> **Importante:** si la sesión vence o se cierra desde otro lado, la próxima acción redirige al inicio de sesión.

### Usuarios de prueba

| Usuario | Contraseña | Rol |
|---|---|---|
| `cajero1` | `cajero123` | Cajero |
| `encargado1` | `encargado123` | Encargado |
| `contador1` | `contador123` | Contador |
| `dueno1` | `dueno123` | Dueño |

---

## 3. Roles y permisos

| Acción | Cajero | Encargado | Contador | Dueño |
|---|:---:|:---:|:---:|:---:|
| Iniciar sesión | Sí | Sí | Sí | Sí |
| Vender en caja | Sí | No | No | No |
| Consultar productos y stock | Sí | Sí | No | Sí |
| Crear/editar productos | No | Sí | No | Sí |
| Ajustar stock | No | Sí | No | Sí |
| Consultar ventas | No | No | Sí | Sí |
| Administrar empleados | No | No | No | Sí |
| Resetear contraseñas | No | No | No | Sí |

El encabezado muestra solamente las secciones permitidas para el rol.

---

## 4. Caja

La pantalla de caja está disponible para el rol **cajero**.

![Caja vacía](img/02-caja-vacia.png)

### 4.1 Vender por código de barras

1. El cursor queda en el campo **Código de barras**.
2. Escanear o escribir el código.
3. Presionar **Enter**.

El producto se agrega al carrito.

### 4.2 Vender por nombre

1. Escribir parte del nombre en **Buscar por nombre**.
2. Esperar los resultados.
3. Tocar **Agregar** en el producto correcto.

### 4.3 Vender por kilo

Cuando el producto se vende por peso, se abre un modal para ingresar los kilos.

![Modal de kilos](img/03-modal-kg.png)

1. Escribir la cantidad en kilos. Se acepta coma o punto.
2. Tocar **Agregar**.

Ejemplo: `0,5` agrega medio kilo.

### 4.4 Carrito y total

![Carrito con productos](img/04-caja-carrito.png)

El carrito muestra:

- producto,
- cantidad,
- precio unitario,
- subtotal,
- total general.

Para quitar un producto, usar **Quitar**.

### 4.5 Cobrar

1. Elegir la **forma de pago**:
   - Efectivo,
   - Billetera virtual,
   - Tarjeta.
2. Tocar **Cobrar**.

El sistema calcula el total y descuenta el stock. Si no hay stock suficiente, no se registra la venta.

![Venta confirmada](img/05-venta-confirmada.png)

El mensaje muestra el número de venta y el total registrado.

> **Importante:** el total que muestra la pantalla es de referencia. El total oficial lo calcula el sistema al cobrar, con los precios cargados.

### 4.6 Errores comunes en caja

| Mensaje | Qué significa |
|---|---|
| “No existe un producto con el código…” | El código no está cargado. |
| “’Producto’ está inactivo.” | El producto existe pero fue desactivado. |
| “No hay stock suficiente…” | La cantidad pedida supera el stock. |
| “No se pudo conectar con el servidor…” | El sistema no está disponible en ese momento. |
| “Sesión vencida” | Hay que volver a iniciar sesión. |

---

## 5. Productos y stock

Disponible para **encargado** y **dueño**.

![Productos y stock](img/06-productos.png)

### 5.1 Crear un producto

1. Completar **Nombre**.
2. Completar **Código de barras**.
3. Elegir **Unidad**:
   - Por unidad,
   - Por peso (kg).
4. Completar **Precio**.
5. Completar **Stock inicial**.
6. Tocar **Crear producto**.

El código de barras no se puede repetir.

### 5.2 Editar un producto

1. Buscar el producto en la tabla.
2. Tocar **Editar**.

![Editar producto](img/07-editar-producto.png)

Se pueden cambiar:

- nombre,
- código,
- unidad,
- precio,
- estado activo/inactivo.

La unidad no se puede cambiar si el producto ya tiene ventas.

### 5.3 Activar o desactivar

- **Desactivar** oculta el producto de la caja y de la lista de productos activos.
- **Activar** lo vuelve a habilitar.

Los productos no se borran: se desactivan para conservar el historial de ventas.

### 5.4 Ajustar stock

1. Tocar **Stock** en la fila del producto.

![Ajustar stock](img/08-ajustar-stock.png)

2. Escribir la cantidad disponible.
3. Tocar **Guardar stock**.

El ajuste es absoluto: “hay 30”, no “sumar 30”.

### 5.5 Límites

| Campo | Mínimo | Máximo |
|---|---:|---:|
| Precio unitario | `0,01` | `1.000.000,00` |
| Stock por producto | `0` | `100.000,000` |
| Cantidad por ítem | `0,001` kg / `1` unidad | `10.000,000` |
| Total de una venta | `0` | `10.000.000,00` |

Los productos por unidad no pueden tener stock fraccionario.

---

## 6. Ventas

Disponible para **contador** y **dueño**.

![Consulta de ventas](img/09-ventas.png)

La pantalla muestra:

- **Total del día**.
- Totales por forma de pago:
  - Efectivo,
  - Billetera virtual,
  - Tarjeta.
- Lista de ventas con:
  - número,
  - hora,
  - forma de pago,
  - total,
  - detalle de productos.

Para cambiar de día, usar el selector **Fecha**.

Si no hay ventas, aparece “No hay ventas registradas para esa fecha”.

---

## 7. Empleados

Disponible solo para el **dueño**.

![Empleados](img/10-empleados.png)

### 7.1 Crear empleado

1. Tocar **Nuevo empleado**.
2. Completar nombre, usuario, rol y contraseña inicial.
3. Tocar **Guardar**.

La contraseña debe tener al menos 8 caracteres.

### 7.2 Editar empleado

1. Tocar **Editar** en la fila.
2. Cambiar nombre, usuario o rol.
3. Tocar **Guardar**.

El dueño no puede cambiarse su propio rol.

### 7.3 Cambiar contraseña

1. Tocar **Clave** en la fila.

![Cambiar contraseña](img/11-cambiar-password.png)

2. Escribir la contraseña nueva.
3. Tocar **Guardar**.

Se cierran las sesiones abiertas de ese empleado.

Si el dueño cambia su propia contraseña, el sistema lo redirige al inicio de sesión.

### 7.4 Activar o desactivar

- **Desactivar** impide que ese empleado inicie sesión y cierra sus sesiones.
- **Activar** lo habilita nuevamente.

Los empleados no se borran: se desactivan para conservar sus ventas.

El dueño no puede desactivarse a sí mismo.

---

## 8. Contador

El contador solo puede consultar ventas.

![Vista del contador](img/12-contador.png)

En el encabezado solo aparece **Ventas**. No puede entrar a caja, productos, stock ni empleados.

---

## 9. Preguntas frecuentes

### No puedo iniciar sesión

- Verificar usuario y contraseña.
- Recordar que el usuario no distingue mayúsculas.
- Si el empleado está inactivo, el dueño debe activarlo.
- Si se olvidó la contraseña, el dueño debe resetearla.

### No aparece un producto en la caja

- Puede estar inactivo.
- Puede no tener stock.
- Verificar el código exacto.

### No me deja cobrar

- Revisar que el carrito no esté vacío.
- Verificar stock.
- Verificar que la aplicación esté funcionando.
- Si la sesión venció, volver a entrar.

### El total no coincide con lo que calculé

El total oficial lo calcula el sistema al cobrar. Si hay diferencias, revisar precios y cantidades cargadas.

### La pantalla quedó cargando

- Recargar la página.
- Verificar que la aplicación esté disponible.
- Revisar la conexión.

### ¿Puedo borrar un producto o empleado?

No. Se desactivan para conservar las ventas históricas.

---

## 10. Glosario

| Término | Significado |
|---|---|
| Producto | Artículo que se vende. |
| Stock | Cantidad disponible. |
| Venta | Operación de cobro con uno o más productos. |
| Detalle | Renglón de una venta. |
| Precio unitario | Precio por unidad o por kilo al momento de la venta. |
| Rol | Permisos del empleado. |
| Sesión | Acceso abierto después de iniciar sesión. |

---

# Parte 2 — Administración técnica

## 11. Arquitectura general

```text
Navegador
   │  http://localhost:3000
   ▼
Next.js (frontend)
   │  /api/* → BACKEND_URL
   ▼
FastAPI (backend)
   │
   ▼
PostgreSQL (base "panaderia")
```

El navegador no llama directo al backend: Next reenvía `/api/*` a `http://127.0.0.1:8000`.

---

## 12. Requisitos

- Python 3.13
- PostgreSQL 17
- Node.js 24
- Windows, PowerShell

---

## 13. Instalación desde cero

### 13.1 Crear la base

La aplicación no crea la base, solo las tablas.

```powershell
$env:PGPASSWORD='TU_CLAVE'
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -h localhost `
  -c "CREATE DATABASE panaderia ENCODING 'UTF8'"
```

### 13.2 Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Editar `backend/.env`:

```text
DATABASE_URL=postgresql+psycopg://postgres:TU_CLAVE@localhost:5432/panaderia
COOKIE_SECURE=false
SESSION_HOURS=12
```

### 13.3 Frontend

```powershell
cd frontend
npm install
```

Opcional: copiar `frontend/.env.local.example` a `frontend/.env.local` y ajustar `BACKEND_URL`.

### 13.4 Arrancar

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Frontend, en otra terminal:

```powershell
cd frontend
npm run dev
```

Abrir `http://localhost:3000/login`.

> **Nota:** usar un solo worker del backend. El seed no está preparado para dos procesos arrancando a la vez.

---

## 14. Arranque diario

1. Verificar que PostgreSQL esté corriendo.
2. Arrancar el backend.
3. Arrancar el frontend.
4. Abrir `http://localhost:3000/login`.

Para la red local conviene compilar el frontend:

```powershell
cd frontend
npm run build
npm start
```

Next muestra la dirección de red, por ejemplo `http://192.168.0.245:3000`.

---

## 15. Reiniciar la base

El script `reset_db.py` borra las tablas, las vuelve a crear y carga el seed.

```powershell
cd backend
.\.venv\Scripts\python.exe reset_db.py
```

Pide confirmación. Para una demo o script:

```powershell
.\.venv\Scripts\python.exe reset_db.py --yes
```

Resultado esperado:

```text
Resumen: 4 empleados, 10 productos, 0 ventas.
```

> **Cuidado:** borra todas las ventas y datos cargados. Usarlo solo en entornos de prueba.

---

## 16. Backup y restore

### Backup manual

```powershell
$env:PGPASSWORD='TU_CLAVE'
& "C:\Program Files\PostgreSQL\17\bin\pg_dump.exe" -U postgres -h localhost `
  -Fc -f "C:\backup\panaderia_2026-11-13.dump" panaderia
```

### Restore

```powershell
$env:PGPASSWORD='TU_CLAVE'
& "C:\Program Files\PostgreSQL\17\bin\pg_restore.exe" -U postgres -h localhost `
  -d panaderia --clean --if-exists "C:\backup\panaderia_2026-11-13.dump"
```

Para el volumen de una panadería de barrio, un backup manual antes de cada jornada importante es suficiente.

---

## 17. Solución de problemas

| Problema | Causa probable | Solución |
|---|---|---|
| El backend no arranca | PostgreSQL apagado o `DATABASE_URL` mal | Revisar `.env` y el servicio de PostgreSQL. |
| “No se pudo conectar con el servidor” | Backend apagado | Arrancar uvicorn. |
| El frontend no carga | `npm install` incompleto | Ejecutar `npm install`. |
| Puerto ocupado | Otro proceso en 3000 u 8000 | Cerrar el proceso o cambiar el puerto. |
| No aparece la extensión `unaccent` | Usuario sin permisos | Usar el usuario `postgres` o crear la extensión a mano. |
| La sesión se cierra | Venció `SESSION_HOURS` | Volver a iniciar sesión. |
| No se puede cambiar la unidad | El producto ya tiene ventas | Es una regla del sistema. |

---

## 18. Usuarios de prueba y límites

### Usuarios

| Usuario | Contraseña | Rol |
|---|---|---|
| `cajero1` | `cajero123` | Cajero |
| `encargado1` | `encargado123` | Encargado |
| `contador1` | `contador123` | Contador |
| `dueno1` | `dueno123` | Dueño |

### Límites

| Campo | Máximo |
|---|---:|
| Precio | `$1.000.000,00` |
| Stock | `100.000,000` |
| Cantidad por ítem | `10.000,000` |
| Total de venta | `$10.000.000,00` |

---

## 19. Referencia técnica

| Método y ruta | Rol | Función |
|---|---|---|
| `GET /test` | público | Verifica backend y base. |
| `POST /login` | público | Inicia sesión. |
| `POST /logout` | autenticado | Cierra sesión. |
| `GET /me` | autenticado | Datos del usuario actual. |
| `GET /productos?q=` | cajero, encargado, dueño | Lista productos activos. |
| `GET /productos/codigo/{codigo}` | cajero, encargado, dueño | Busca por código. |
| `POST /productos` | encargado, dueño | Crea producto. |
| `PUT /productos/{id}` | encargado, dueño | Edita producto. |
| `GET /stock` | cajero, encargado, dueño | Lista stock. |
| `PUT /stock/{id}` | encargado, dueño | Ajusta stock. |
| `POST /ventas` | cajero | Registra venta. |
| `GET /ventas?fecha=` | contador, dueño | Consulta ventas. |
| `GET /empleados` | dueño | Lista empleados. |
| `POST /empleados` | dueño | Crea empleado. |
| `PUT /empleados/{id}` | dueño | Edita empleado. |
| `PUT /empleados/{id}/password` | dueño | Resetea contraseña. |
| `GET /docs` | público | Documentación automática. |

---

**Fin del manual.**
