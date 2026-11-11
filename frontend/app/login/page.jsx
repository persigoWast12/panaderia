"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { RUTA_INICIO } from "@/lib/roles";

// En desarrollo se muestran los usuarios de prueba; en producción no.
const ES_DESARROLLO = process.env.NODE_ENV !== "production";

/**
 * Pantalla de login.
 * Valida contra `POST /api/login` y redirige según el rol que devuelve el
 * backend. El mensaje de error se muestra tal cual llega de la API.
 */
export default function Login() {
  const router = useRouter();
  const [usuario, setUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function entrar(evento) {
    evento.preventDefault();
    setError("");
    setEnviando(true);

    try {
      const datos = await api("/login", {
        method: "POST",
        body: JSON.stringify({ usuario, password }),
      });
      // Cada rol tiene su pantalla inicial (caja, productos o ventas).
      router.replace(RUTA_INICIO[datos.rol] ?? "/");
    } catch (fallo) {
      setError(fallo.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-amber-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="text-5xl">🥖</div>
          <h1 className="mt-2 text-2xl font-bold text-amber-900">Panadería</h1>
          <p className="text-sm text-stone-600">Ingresá con tu usuario</p>
        </div>

        <form
          onSubmit={entrar}
          className="space-y-4 rounded-2xl border border-stone-200 bg-white p-6 shadow-lg"
        >
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-stone-700">
              Usuario
            </span>
            <input
              type="text"
              autoComplete="username"
              autoCapitalize="none"
              autoFocus
              required
              value={usuario}
              onChange={(evento) => setUsuario(evento.target.value)}
              className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-stone-700">
              Contraseña
            </span>
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(evento) => setPassword(evento.target.value)}
              className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
            />
          </label>

          {error && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={enviando}
            className="w-full rounded-lg bg-amber-700 px-4 py-2.5 font-semibold text-white hover:bg-amber-800 disabled:opacity-60"
          >
            {enviando ? "Entrando…" : "Entrar"}
          </button>
        </form>

        {ES_DESARROLLO && (
          <details className="mt-4 rounded-xl border border-stone-200 bg-white/60 p-3 text-xs text-stone-600">
            <summary className="cursor-pointer font-medium">
              Usuarios de prueba
            </summary>
            <ul className="mt-2 space-y-1">
              <li>cajero1 / cajero123</li>
              <li>encargado1 / encargado123</li>
              <li>dueno1 / dueno123</li>
            </ul>
          </details>
        )}
      </div>
    </main>
  );
}
