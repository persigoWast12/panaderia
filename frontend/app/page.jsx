"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { RUTA_INICIO } from "@/lib/roles";

/**
 * Página de entrada.
 * Consulta la sesión y redirige a la pantalla inicial del rol; si no hay
 * sesión, `api` manda a /login.
 */
export default function Inicio() {
  const router = useRouter();

  useEffect(() => {
    api("/me")
      .then((empleado) => {
        router.replace(RUTA_INICIO[empleado.rol] ?? "/login");
      })
      .catch(() => {
        // Sin sesión o sesión vencida: siempre al login.
        router.replace("/login");
      });
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center text-stone-600">
      Cargando…
    </main>
  );
}
