"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api";
import { ETIQUETAS_ROL, NAVEGACION, RUTA_INICIO } from "@/lib/roles";

/**
 * Barra superior de las pantallas autenticadas.
 *
 * Muestra el nombre y el rol, los enlaces permitidos para ese rol y el botón
 * de cerrar sesión.
 *
 * @param {{empleado: {nombre: string, rol: string}}} props
 */
export default function Header({ empleado }) {
  const ruta = usePathname();
  const router = useRouter();
  const [saliendo, setSaliendo] = useState(false);

  // Cada enlace declara sus roles; acá se ocultan los que no corresponden.
  const enlaces = NAVEGACION.filter((item) =>
    item.roles.includes(empleado.rol)
  );

  async function cerrarSesion() {
    setSaliendo(true);
    try {
      await api("/logout", { method: "POST" });
    } catch {
      // Aunque el backend falle (por ejemplo, sesión ya vencida), igual
      // volvemos al login: la cookie deja de servir.
    }
    router.replace("/login");
  }

  return (
    <header className="bg-amber-900 text-amber-50 shadow-md">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-4 py-3">
        <Link
          href={RUTA_INICIO[empleado.rol]}
          className="text-lg font-bold tracking-tight"
        >
          🥖 Panadería
        </Link>

        <nav className="flex flex-wrap gap-1">
          {enlaces.map((enlace) => {
            const activo = ruta === enlace.href;
            return (
              <Link
                key={enlace.href}
                href={enlace.href}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  activo
                    ? "bg-amber-50 text-amber-900"
                    : "text-amber-100 hover:bg-amber-800"
                }`}
              >
                {enlace.texto}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-3 text-sm">
          <span className="text-amber-100">
            {empleado.nombre} · {ETIQUETAS_ROL[empleado.rol] ?? empleado.rol}
          </span>
          <button
            type="button"
            onClick={cerrarSesion}
            disabled={saliendo}
            className="rounded-lg border border-amber-200/40 px-3 py-1.5 font-medium text-amber-50 hover:bg-amber-800 disabled:opacity-60"
          >
            {saliendo ? "Saliendo…" : "Cerrar sesión"}
          </button>
        </div>
      </div>
    </header>
  );
}
