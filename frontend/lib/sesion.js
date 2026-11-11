"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";

/**
 * Hook que obtiene la sesión actual y dice si el rol puede entrar a la página.
 *
 * Se llama una sola vez por pantalla. `api("/me")` devuelve 401 si no hay
 * sesión; en ese caso el cliente HTTP redirige a `/login`. Si el usuario está
 * autenticado pero su rol no está en `rolesPermitidos`, la página muestra el
 * mensaje de acceso denegado.
 *
 * @param {string[]} [rolesPermitidos] Roles que pueden ver la pantalla.
 * @returns {{
 *   empleado: {id: number, nombre: string, usuario: string, rol: string}|null,
 *   cargando: boolean,
 *   error: string,
 *   permitido: boolean
 * }}
 */
export function useSesion(rolesPermitidos) {
  const [empleado, setEmpleado] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let activo = true;

    api("/me")
      .then((datos) => {
        if (activo) setEmpleado(datos);
      })
      .catch((fallo) => {
        // El 401 ya redirige a /login desde `api`; no hace falta mostrarlo.
        if (activo && fallo.message !== "Sesión vencida") {
          setError(fallo.message);
        }
      })
      .finally(() => {
        if (activo) setCargando(false);
      });

    // Evita actualizar estado si el componente se desmontó antes de responder.
    return () => {
      activo = false;
    };
  }, []);

  const permitido =
    empleado !== null &&
    (!rolesPermitidos || rolesPermitidos.includes(empleado.rol));

  return { empleado, cargando, error, permitido };
}
