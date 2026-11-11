/**
 * Utilidades de formato para mostrar datos en la interfaz.
 * El backend manda números; acá se convierten a texto con formato argentino.
 */

const formatoMoneda = new Intl.NumberFormat("es-AR", {
  style: "currency",
  currency: "ARS",
  minimumFractionDigits: 2,
});

/**
 * Formatea un número como precio en pesos argentinos.
 * @param {number|string} valor
 * @returns {string} Por ejemplo "$ 3.200,00".
 */
export function formatearMoneda(valor) {
  return formatoMoneda.format(Number(valor) || 0);
}

/**
 * Formatea una cantidad según la unidad del producto.
 * Los productos por kg muestran 3 decimales; los que se venden por unidad, 0.
 *
 * @param {number|string} valor
 * @param {"kg"|"unidad"} unidad
 * @returns {string}
 */
export function formatearCantidad(valor, unidad) {
  const numero = Number(valor) || 0;
  if (unidad === "kg") {
    return numero.toLocaleString("es-AR", {
      minimumFractionDigits: 3,
      maximumFractionDigits: 3,
    });
  }
  return numero.toLocaleString("es-AR", { maximumFractionDigits: 0 });
}

const formatoHora = new Intl.DateTimeFormat("es-AR", {
  hour: "2-digit",
  minute: "2-digit",
});

/**
 * Extrae la hora de una fecha ISO que manda el backend.
 * El backend guarda hora local sin zona, así que `new Date` la interpreta
 * como hora local del navegador.
 *
 * @param {string} fechaHora
 * @returns {string} Por ejemplo "10:15".
 */
export function formatearHora(fechaHora) {
  return formatoHora.format(new Date(fechaHora));
}

/**
 * Devuelve la fecha local en formato YYYY-MM-DD, para el input de tipo date.
 * Se corrige el desfase de zona horaria para no mostrar el día anterior.
 *
 * @param {Date} [fecha]
 * @returns {string}
 */
export function fechaLocalISO(fecha = new Date()) {
  const local = new Date(fecha.getTime() - fecha.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

/**
 * Redondea a dos decimales para mostrar subtotales y totales.
 * El cálculo oficial lo hace el backend; esto es solo para la vista.
 *
 * @param {number} valor
 * @returns {number}
 */
export function redondearCentavos(valor) {
  return Math.round((Number(valor) + Number.EPSILON) * 100) / 100;
}
