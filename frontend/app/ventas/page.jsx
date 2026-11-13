"use client";

import { useEffect, useState } from "react";

import Header from "@/components/Header";
import { api } from "@/lib/api";
import {
  fechaLocalISO,
  formatearCantidad,
  formatearHora,
  formatearMoneda,
  redondearCentavos,
} from "@/lib/formato";
import { ETIQUETAS_FORMA_PAGO } from "@/lib/roles";
import { useSesion } from "@/lib/sesion";

const FORMAS = ["efectivo", "billetera_virtual", "tarjeta"];

/**
 * Consulta de ventas para contador y dueño.
 *
 * Pide `GET /api/ventas?fecha=...`, que devuelve las ventas del día con sus
 * renglones. Los totales del día y por forma de pago se calculan en el
 * cliente a partir de esos datos; no hay un endpoint de reportes aparte.
 */
export default function Ventas() {
  const { empleado, cargando, error: errorSesion, permitido } = useSesion([
    "cajero",
    "encargado",
    "contador",
    "dueno",
  ]);

  const [fecha, setFecha] = useState(fechaLocalISO());
  const [ventas, setVentas] = useState([]);
  const [cargandoLista, setCargandoLista] = useState(true);
  const [error, setError] = useState("");

  /** Trae las ventas de la fecha seleccionada. */
  async function cargar() {
    setCargandoLista(true);
    try {
      const datos = await api(`/ventas?fecha=${encodeURIComponent(fecha)}`);
      setVentas(datos);
      setError("");
    } catch (fallo) {
      setError(fallo.message);
    } finally {
      setCargandoLista(false);
    }
  }

  useEffect(() => {
    if (permitido) cargar();
  }, [permitido, fecha]);

  if (cargando) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        Cargando…
      </main>
    );
  }

  if (!empleado) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4 text-center text-red-700">
        {errorSesion || "No se pudo iniciar la sesión."}
      </main>
    );
  }

  if (!permitido) {
    return (
      <>
        <Header empleado={empleado} />
        <main className="mx-auto max-w-3xl px-4 py-10">
          <p className="rounded-xl bg-red-50 p-4 text-red-700">
            No tenés permiso para consultar ventas.
          </p>
        </main>
      </>
    );
  }

  // Total del día: se redondea solo para mostrar, el dato oficial es cada venta.
  const totalDia = redondearCentavos(
    ventas.reduce((total, venta) => total + Number(venta.total), 0)
  );

  // Desglose para el cierre de caja: efectivo, billetera virtual y tarjeta.
  const totalesPorForma = ventas.reduce((acumulado, venta) => {
    acumulado[venta.forma_pago] =
      (acumulado[venta.forma_pago] ?? 0) + Number(venta.total);
    return acumulado;
  }, {});

  return (
    <>
      <Header empleado={empleado} />

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-amber-900">
              Consulta de ventas
            </h1>
            <p className="text-sm text-stone-600">
              Ventas registradas en el día seleccionado.
            </p>
          </div>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-stone-700">
              Fecha
            </span>
            <input
              type="date"
              value={fecha}
              onChange={(evento) => setFecha(evento.target.value)}
              className="rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
            />
          </label>
        </div>

        {error && (
          <p className="rounded-xl bg-red-50 px-4 py-3 text-red-700">{error}</p>
        )}

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-amber-200 bg-amber-100 p-4">
            <p className="text-sm font-medium text-amber-900">Total del día</p>
            <p className="text-2xl font-bold text-amber-950">
              {formatearMoneda(totalDia)}
            </p>
          </div>

          {FORMAS.map((forma) => (
            <div
              key={forma}
              className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm"
            >
              <p className="text-sm font-medium text-stone-600">
                {ETIQUETAS_FORMA_PAGO[forma]}
              </p>
              <p className="text-2xl font-bold text-stone-800">
                {formatearMoneda(totalesPorForma[forma] ?? 0)}
              </p>
            </div>
          ))}
        </section>

        {cargandoLista && (
          <p className="rounded-xl bg-white p-6 text-center text-stone-500">
            Cargando ventas…
          </p>
        )}

        {!cargandoLista && ventas.length === 0 && (
          <p className="rounded-xl bg-white p-6 text-center text-stone-500">
            No hay ventas registradas para esa fecha.
          </p>
        )}

        <section className="space-y-3">
          {ventas.map((venta) => (
            <article
              key={venta.id}
              className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm"
            >
              <header className="flex flex-wrap items-center gap-3 border-b border-stone-100 bg-stone-50 px-4 py-3">
                <h2 className="font-semibold text-stone-800">
                  Venta #{venta.id}
                </h2>
                <span className="text-sm text-stone-600">
                  {formatearHora(venta.fecha_hora)}
                </span>
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
                  {ETIQUETAS_FORMA_PAGO[venta.forma_pago] ?? venta.forma_pago}
                </span>
                <span className="ml-auto text-lg font-bold text-stone-800">
                  {formatearMoneda(venta.total)}
                </span>
              </header>

              <ul className="divide-y divide-stone-100 px-4 text-sm">
                {venta.items.map((item) => (
                  <li
                    key={item.producto_id}
                    className="flex flex-wrap items-center gap-2 py-2"
                  >
                    <span className="min-w-0 flex-1 truncate text-stone-700">
                      {item.nombre}
                    </span>
                    <span className="text-stone-500">
                      {formatearCantidad(item.cantidad, item.unidad)}{" "}
                      {item.unidad === "kg" ? "kg" : "u."} ×{" "}
                      {formatearMoneda(item.precio_unitario)}
                    </span>
                    <span className="w-24 text-right font-medium text-stone-700">
                      {formatearMoneda(item.subtotal)}
                    </span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </section>
      </main>
    </>
  );
}
