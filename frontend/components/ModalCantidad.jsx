"use client";

import { useState } from "react";

import Modal from "@/components/Modal";
import { formatearCantidad, formatearMoneda } from "@/lib/formato";
import { CANTIDAD_MAX } from "@/lib/limites";

/**
 * Pide los kilos cuando el producto se vende por peso.
 *
 * Valida que la cantidad sea mayor a cero y que no supere el stock disponible
 * que se conoce en pantalla. El backend vuelve a validar al cobrar.
 *
 * @param {{
 *   producto: {
 *     nombre: string,
 *     precio: number,
 *     cantidad_disponible: number
 *   },
 *   onConfirmar: (cantidad: number) => void,
 *   onCancelar: () => void
 * }} props
 */
export default function ModalCantidad({ producto, onConfirmar, onCancelar }) {
  const [cantidad, setCantidad] = useState("");
  const [error, setError] = useState("");

  function confirmar(evento) {
    evento.preventDefault();
    // Acepta coma o punto como separador decimal.
    const numero = Number(String(cantidad).replace(",", "."));

    if (!Number.isFinite(numero) || numero <= 0) {
      setError("Ingresá una cantidad mayor a cero.");
      return;
    }

    if (numero > CANTIDAD_MAX) {
      setError(
        `La cantidad máxima permitida es ${formatearCantidad(
          CANTIDAD_MAX,
          "kg"
        )} kg.`
      );
      return;
    }

    if (numero > Number(producto.cantidad_disponible)) {
      setError(
        `Solo hay ${formatearCantidad(
          producto.cantidad_disponible,
          "kg"
        )} kg disponibles.`
      );
      return;
    }

    // Se redondea a 3 decimales, que es la precisión que guarda la base.
    onConfirmar(Math.round(numero * 1000) / 1000);
  }

  return (
    <Modal titulo={`¿Cuántos kg de ${producto.nombre}?`} onCerrar={onCancelar}>
      <form onSubmit={confirmar} className="space-y-4">
        <p className="text-sm text-stone-600">
          Precio por kg: <strong>{formatearMoneda(producto.precio)}</strong> ·
          Disponible: {formatearCantidad(producto.cantidad_disponible, "kg")} kg
        </p>

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-stone-700">
            Kilos
          </span>
          <input
            type="number"
            inputMode="decimal"
            step="0.001"
            min="0.001"
            max={Math.min(
              Number(producto.cantidad_disponible),
              CANTIDAD_MAX
            )}
            autoFocus
            value={cantidad}
            onChange={(evento) => {
              setCantidad(evento.target.value);
              setError("");
            }}
            className="w-full rounded-lg border border-stone-300 px-3 py-2 text-lg focus:border-amber-600 focus:outline-none"
            placeholder="0,000"
          />
        </label>

        {error && <p className="text-sm text-red-700">{error}</p>}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancelar}
            className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-100"
          >
            Cancelar
          </button>
          <button
            type="submit"
            className="rounded-lg bg-amber-700 px-4 py-2 text-sm font-medium text-white hover:bg-amber-800"
          >
            Agregar
          </button>
        </div>
      </form>
    </Modal>
  );
}
