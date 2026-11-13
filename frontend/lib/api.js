/**
 * Cliente HTTP único del frontend.
 *
 * Todas las llamadas pasan por `/api` para que Next las reenvíe al backend.
 * La cookie de sesión viaja sola (`credentials: "same-origin"`).
 *
 * Si el backend responde 401 fuera de la pantalla de login, se redirige a
 * `/login`. El mensaje de error se toma del campo `detail` de FastAPI para
 * mostrarlo tal cual en pantalla.
 *
 * @param {string} path Ruta relativa sin `/api`, por ejemplo `/productos?q=pan`.
 * @param {RequestInit} [init] Opciones de `fetch` (method, body, etc.).
 * @returns {Promise<any>} Cuerpo JSON de la respuesta.
 * @throws {Error} Con el mensaje del backend o "Error inesperado".
 */
function mensajeDeError(detalle) {
  // En los 422 de FastAPI, detail es una lista de errores de validación.
  if (Array.isArray(detalle)) {
    return "Datos inválidos. Revisá los campos.";
  }
  if (typeof detalle === "string" && detalle.trim()) {
    return detalle;
  }
  return "Error inesperado";
}

export async function api(path, init) {
  let respuesta;

  try {
    respuesta = await fetch(`/api${path}`, {
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      ...init,
    });
  } catch {
    throw new Error(
      "No se pudo conectar con el servidor. Revisá la conexión e intentá de nuevo."
    );
  }

  const datos = await respuesta.json().catch(() => null);

  if (
    respuesta.status === 401 &&
    typeof window !== "undefined" &&
    !window.location.pathname.startsWith("/login")
  ) {
    window.location.href = "/login";
    throw new Error("Sesión vencida");
  }

  if (!respuesta.ok) {
    if (respuesta.status >= 500 && !datos?.detail) {
      throw new Error(
        "Error del servidor. Intentá de nuevo en unos minutos."
      );
    }
    throw new Error(mensajeDeError(datos?.detail));
  }

  return datos;
}
