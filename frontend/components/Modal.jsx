"use client";

import { useEffect } from "react";

/**
 * Ventana modal simple y accesible.
 *
 * Se cierra con la tecla Escape o haciendo clic en el fondo. El atributo
 * `data-modal` lo usa la pantalla de caja para no robarle el foco al lector
 * mientras hay un modal abierto.
 *
 * @param {{
 *   titulo: string,
 *   onCerrar: () => void,
 *   children: React.ReactNode
 * }} props
 */
export default function Modal({ titulo, onCerrar, children }) {
  // Escape cierra el modal mientras esté montado.
  useEffect(() => {
    function alPresionar(evento) {
      if (evento.key === "Escape") onCerrar();
    }
    document.addEventListener("keydown", alPresionar);
    return () => document.removeEventListener("keydown", alPresionar);
  }, [onCerrar]);

  return (
    <div
      data-modal
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onMouseDown={(evento) => {
        if (evento.target === evento.currentTarget) onCerrar();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"
      >
        <div className="mb-4 flex items-center justify-between gap-4">
          <h2 className="text-lg font-semibold text-stone-800">{titulo}</h2>
          <button
            type="button"
            onClick={onCerrar}
            className="rounded-lg px-2 py-1 text-stone-500 hover:bg-stone-100 hover:text-stone-800"
            aria-label="Cerrar"
          >
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
