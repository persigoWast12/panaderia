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
export async function api(path, init) {
  const respuesta = await fetch(`/api${path}`, {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

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
    throw new Error(datos?.detail ?? "Error inesperado");
  }

  return datos;
}
