/**
 * Roles del sistema y su presentación en la interfaz.
 *
 * Los valores de las claves deben coincidir con el CHECK de la tabla
 * `empleado` del backend y con lo que devuelve `/me`.
 */
export const ETIQUETAS_ROL = {
  cajero: "Cajero",
  encargado: "Encargado",
  contador: "Contador",
  dueno: "Dueño",
};

/** Pantalla a la que se redirige a cada rol después del login. */
export const RUTA_INICIO = {
  cajero: "/caja",
  encargado: "/productos",
  contador: "/ventas",
  dueno: "/productos",
};

/**
 * Enlaces del header. Cada uno declara qué roles pueden verlo; el filtrado se
 * hace en `Header.jsx` para no mostrar secciones sin permiso.
 */
export const NAVEGACION = [
  { href: "/caja", texto: "Caja", roles: ["cajero"] },
  {
    href: "/productos",
    texto: "Productos",
    roles: ["encargado", "dueno"],
  },
  { href: "/ventas", texto: "Ventas", roles: ["contador", "dueno"] },
  { href: "/empleados", texto: "Empleados", roles: ["dueno"] },
];

/** Nombres visibles de las formas de pago aceptadas por el backend. */
export const ETIQUETAS_FORMA_PAGO = {
  efectivo: "Efectivo",
  billetera_virtual: "Billetera virtual",
  tarjeta: "Tarjeta",
};
