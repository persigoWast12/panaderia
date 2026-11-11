"use client";

import { useEffect, useRef, useState } from "react";

import Header from "@/components/Header";
import ModalCantidad from "@/components/ModalCantidad";
import { api } from "@/lib/api";
import {
  formatearCantidad,
  formatearMoneda,
  redondearCentavos,
} from "@/lib/formato";
import { ETIQUETAS_FORMA_PAGO } from "@/lib/roles";
import { useSesion } from "@/lib/sesion";

const FORMAS_PAGO = ["efectivo", "billetera_virtual", "tarjeta"];

/**
 * Pantalla de caja para el rol cajero.
 *
 * Flujo principal:
 * - el campo del lector mantiene el foco;
 * - Enter busca el código y agrega el producto;
 * - los productos por kg abren un modal para ingresar kilos;
 * - el carrito valida stock y se envía a `POST /api/ventas` sin total.
 *
 * El total que se muestra es solo de referencia: el backend lo recalcula con
 * los precios de la base al registrar la venta.
 */
export default function Caja() {
  const { empleado, cargando, error: errorSesion, permitido } = useSesion([
    "cajero",
  ]);

  const codigoRef = useRef(null);
  // Carrito, búsqueda, modal de kilos y mensajes de la pantalla.
  const [carrito, setCarrito] = useState([]);
  const [formaPago, setFormaPago] = useState("efectivo");
  const [busqueda, setBusqueda] = useState("");
  const [resultados, setResultados] = useState([]);
  const [productoPesable, setProductoPesable] = useState(null);
  const [mensaje, setMensaje] = useState("");
  const [error, setError] = useState("");
  const [cobrando, setCobrando] = useState(false);

  // Foco permanente en el lector. Se devuelve el foco al campo salvo que el
  // clic sea en un input, un botón, un enlace o un modal.
  useEffect(() => {
    if (!permitido) return;

    codigoRef.current?.focus();

    function alHacerClic(evento) {
      if (
        evento.target.closest("input, button, select, textarea, a, [data-modal]")
      ) {
        return;
      }
      codigoRef.current?.focus();
    }

    document.addEventListener("click", alHacerClic);
    return () => document.removeEventListener("click", alHacerClic);
  }, [permitido]);

  // Buscador por nombre con retardo de 300 ms para no llamar en cada tecla.
  useEffect(() => {
    if (!permitido) return;

    const texto = busqueda.trim();
    if (!texto) {
      setResultados([]);
      return;
    }

    let vigente = true;
    const temporizador = setTimeout(() => {
      api(`/productos?q=${encodeURIComponent(texto)}`)
        .then((datos) => {
          if (vigente) setResultados(datos);
        })
        .catch(() => {
          if (vigente) setResultados([]);
        });
    }, 300);

    return () => {
      vigente = false;
      clearTimeout(temporizador);
    };
  }, [busqueda, permitido]);

  /** Suma lo que ya hay en el carrito para un producto. */
  function cantidadEnCarrito(productoId) {
    return carrito
      .filter((item) => item.producto.id === productoId)
      .reduce((total, item) => total + item.cantidad, 0);
  }

  /**
   * Agrega un producto al carrito o suma la cantidad si ya estaba.
   * Valida el stock conocido en pantalla; el backend vuelve a validar al
   * cobrar, por si otra caja vendió mientras tanto.
   */
  function agregar(producto, cantidad) {
    setError("");
    setMensaje("");

    if (Number(producto.cantidad_disponible) <= 0) {
      setError(`No hay stock de '${producto.nombre}'.`);
      return;
    }

    const yaEnCarrito = cantidadEnCarrito(producto.id);
    if (yaEnCarrito + cantidad > Number(producto.cantidad_disponible)) {
      setError(`No hay stock suficiente de '${producto.nombre}'.`);
      return;
    }

    setCarrito((anterior) => {
      const indice = anterior.findIndex(
        (item) => item.producto.id === producto.id
      );

      if (indice === -1) {
        return [...anterior, { producto, cantidad }];
      }

      const copia = [...anterior];
      copia[indice] = {
        ...copia[indice],
        cantidad: copia[indice].cantidad + cantidad,
      };
      return copia;
    });

    setProductoPesable(null);
    setBusqueda("");
    setResultados([]);
    setTimeout(() => codigoRef.current?.focus(), 0);
  }

  function quitar(productoId) {
    setCarrito((anterior) =>
      anterior.filter((item) => item.producto.id !== productoId)
    );
    setTimeout(() => codigoRef.current?.focus(), 0);
  }

  /**
   * Maneja el Enter del lector de códigos.
   * Busca el producto por código, rechaza inactivos y, si es por kg, abre el
   * modal de cantidad. El campo se limpia siempre.
   */
  async function escanear(evento) {
    if (evento.key !== "Enter") return;
    evento.preventDefault();

    const codigo = evento.currentTarget.value.trim();
    evento.currentTarget.value = "";
    if (!codigo) return;

    setError("");
    setMensaje("");
    let abriendoModal = false;

    try {
      const producto = await api(
        `/productos/codigo/${encodeURIComponent(codigo)}`
      );

      if (!producto.activo) {
        setError(`'${producto.nombre}' está inactivo.`);
        return;
      }

      if (producto.unidad === "kg") {
        abriendoModal = true;
        setProductoPesable(producto);
        return;
      }

      agregar(producto, 1);
    } catch (fallo) {
      setError(
        fallo.message === "Producto no encontrado."
          ? `No existe un producto con el código ${codigo}.`
          : fallo.message
      );
    } finally {
      if (!abriendoModal) codigoRef.current?.focus();
    }
  }

  function elegirResultado(producto) {
    if (producto.unidad === "kg") {
      setProductoPesable(producto);
      return;
    }
    agregar(producto, 1);
  }

  /**
   * Envía el carrito a `POST /api/ventas`.
   * No manda total: el backend lo calcula. Si falla (por ejemplo, stock
   * insuficiente), muestra el error y conserva el carrito.
   */
  async function cobrar() {
    if (carrito.length === 0) {
      setError("El carrito está vacío.");
      return;
    }

    setCobrando(true);
    setError("");
    setMensaje("");

    try {
      const venta = await api("/ventas", {
        method: "POST",
        body: JSON.stringify({
          forma_pago: formaPago,
          items: carrito.map((item) => ({
            producto_id: item.producto.id,
            cantidad:
              item.producto.unidad === "kg"
                ? Math.round(item.cantidad * 1000) / 1000
                : Math.trunc(item.cantidad),
          })),
        }),
      });

      setMensaje(
        `Venta #${venta.id} registrada. Total: ${formatearMoneda(venta.total)}.`
      );
      setCarrito([]);
    } catch (fallo) {
      setError(fallo.message);
    } finally {
      setCobrando(false);
      codigoRef.current?.focus();
    }
  }

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
            No tenés permiso para entrar a la caja.
          </p>
        </main>
      </>
    );
  }

  // Total de referencia: suma de subtotales redondeados, igual que el backend.
  const total = redondearCentavos(
    carrito.reduce(
      (acumulado, item) =>
        acumulado +
        redondearCentavos(item.cantidad * Number(item.producto.precio)),
      0
    )
  );

  return (
    <>
      <Header empleado={empleado} />

      <main className="mx-auto max-w-6xl px-4 py-6">
        <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
          <section className="space-y-4">
            <div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-stone-700">
                  Código de barras
                </span>
                <input
                  ref={codigoRef}
                  type="text"
                  autoComplete="off"
                  enterKeyHint="done"
                  onKeyDown={escanear}
                  placeholder="Escaneá o escribí el código y presioná Enter"
                  className="w-full rounded-lg border-2 border-amber-500 px-3 py-3 text-lg focus:border-amber-700 focus:outline-none"
                />
              </label>
            </div>

            <div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-stone-700">
                  Buscar por nombre
                </span>
                <input
                  type="text"
                  autoComplete="off"
                  value={busqueda}
                  onChange={(evento) => setBusqueda(evento.target.value)}
                  placeholder="Ej. pan, medialunas…"
                  className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
                />
              </label>

              {busqueda.trim() && (
                <ul className="mt-3 divide-y divide-stone-100">
                  {resultados.length === 0 && (
                    <li className="py-2 text-sm text-stone-500">
                      No se encontraron productos activos.
                    </li>
                  )}
                  {resultados.map((producto) => (
                    <li
                      key={producto.id}
                      className="flex items-center gap-3 py-2"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium text-stone-800">
                          {producto.nombre}
                        </p>
                        <p className="text-xs text-stone-500">
                          {formatearMoneda(producto.precio)}
                          {producto.unidad === "kg" ? " / kg" : " c/u"} · stock{" "}
                          {formatearCantidad(
                            producto.cantidad_disponible,
                            producto.unidad
                          )}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => elegirResultado(producto)}
                        disabled={Number(producto.cantidad_disponible) <= 0}
                        className="rounded-lg bg-amber-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-800 disabled:opacity-40"
                      >
                        Agregar
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {error && (
              <p className="rounded-xl bg-red-50 px-4 py-3 text-red-700">
                {error}
              </p>
            )}
            {mensaje && (
              <p className="rounded-xl bg-green-50 px-4 py-3 text-green-700">
                {mensaje}
              </p>
            )}
          </section>

          <aside className="space-y-4">
            <div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-stone-800">
                Carrito
              </h2>

              {carrito.length === 0 ? (
                <p className="py-6 text-center text-sm text-stone-500">
                  Todavía no agregaste productos.
                </p>
              ) : (
                <ul className="divide-y divide-stone-100">
                  {carrito.map((item) => {
                    const subtotal = redondearCentavos(
                      item.cantidad * Number(item.producto.precio)
                    );
                    return (
                      <li key={item.producto.id} className="py-3">
                        <div className="flex items-start gap-2">
                          <div className="min-w-0 flex-1">
                            <p className="font-medium text-stone-800">
                              {item.producto.nombre}
                            </p>
                            <p className="text-xs text-stone-500">
                              {formatearCantidad(
                                item.cantidad,
                                item.producto.unidad
                              )}{" "}
                              {item.producto.unidad === "kg" ? "kg" : "u."} ×{" "}
                              {formatearMoneda(item.producto.precio)}
                              {item.producto.unidad === "kg" ? "/kg" : ""}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="font-semibold text-stone-800">
                              {formatearMoneda(subtotal)}
                            </p>
                            <button
                              type="button"
                              onClick={() => quitar(item.producto.id)}
                              className="text-xs font-medium text-red-700 hover:underline"
                            >
                              Quitar
                            </button>
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}

              <div className="mt-4 border-t border-stone-200 pt-4">
                <p className="text-sm text-stone-500">Total</p>
                <p className="text-4xl font-bold tracking-tight text-amber-900">
                  {formatearMoneda(total)}
                </p>
              </div>
            </div>

            <div className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-stone-700">
                  Forma de pago
                </span>
                <select
                  value={formaPago}
                  onChange={(evento) => setFormaPago(evento.target.value)}
                  className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
                >
                  {FORMAS_PAGO.map((forma) => (
                    <option key={forma} value={forma}>
                      {ETIQUETAS_FORMA_PAGO[forma]}
                    </option>
                  ))}
                </select>
              </label>

              <button
                type="button"
                onClick={cobrar}
                disabled={cobrando || carrito.length === 0}
                className="mt-4 w-full rounded-xl bg-green-700 px-4 py-3 text-lg font-bold text-white hover:bg-green-800 disabled:opacity-40"
              >
                {cobrando ? "Cobrando…" : "Cobrar"}
              </button>
            </div>
          </aside>
        </div>
      </main>

      {productoPesable && (
        <ModalCantidad
          producto={productoPesable}
          onConfirmar={(cantidad) => agregar(productoPesable, cantidad)}
          onCancelar={() => {
            setProductoPesable(null);
            setTimeout(() => codigoRef.current?.focus(), 0);
          }}
        />
      )}
    </>
  );
}
