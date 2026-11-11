"use client";

import { useEffect, useState } from "react";

import Header from "@/components/Header";
import Modal from "@/components/Modal";
import { api } from "@/lib/api";
import { formatearCantidad, formatearMoneda } from "@/lib/formato";
import { useSesion } from "@/lib/sesion";

const FORMULARIO_VACIO = {
  nombre: "",
  codigo_barras: "",
  unidad: "unidad",
  precio: "",
  cantidad_inicial: "0",
};

/**
 * Pantalla de productos y stock para encargado y dueño.
 *
 * La tabla se alimenta de `GET /api/stock`, que incluye también los productos
 * inactivos y el campo `tiene_ventas`. Ese dato se usa para bloquear el cambio
 * de unidad cuando el producto ya tiene ventas.
 *
 * Tiene tres operaciones: crear, editar y ajustar stock. Las tres refrescan la
 * tabla al terminar.
 */
export default function Productos() {
  const { empleado, cargando, error: errorSesion, permitido } = useSesion([
    "encargado",
    "dueno",
  ]);

  const [productos, setProductos] = useState([]);
  const [cargandoLista, setCargandoLista] = useState(true);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");

  const [formulario, setFormulario] = useState(FORMULARIO_VACIO);
  const [creando, setCreando] = useState(false);

  const [productoEditando, setProductoEditando] = useState(null);
  const [formEdicion, setFormEdicion] = useState(null);
  const [errorModal, setErrorModal] = useState("");
  const [guardando, setGuardando] = useState(false);

  const [productoStock, setProductoStock] = useState(null);
  const [cantidadStock, setCantidadStock] = useState("");

  /** Trae todos los productos (activos e inactivos) con su stock y precio. */
  async function cargar() {
    setCargandoLista(true);
    try {
      const datos = await api("/stock");
      setProductos(datos);
      setError("");
    } catch (fallo) {
      setError(fallo.message);
    } finally {
      setCargandoLista(false);
    }
  }

  useEffect(() => {
    if (permitido) cargar();
  }, [permitido]);

  function actualizarCampo(campo, valor) {
    setFormulario((anterior) => ({ ...anterior, [campo]: valor }));
  }

  /** Crea un producto con su stock inicial desde el formulario de arriba. */
  async function crear(evento) {
    evento.preventDefault();
    setError("");
    setMensaje("");

    if (!formulario.nombre.trim() || !formulario.codigo_barras.trim()) {
      setError("Completá el nombre y el código de barras.");
      return;
    }

    if (!(Number(formulario.precio) > 0)) {
      setError("El precio tiene que ser mayor a cero.");
      return;
    }

    setCreando(true);
    try {
      await api("/productos", {
        method: "POST",
        body: JSON.stringify({
          nombre: formulario.nombre.trim(),
          codigo_barras: formulario.codigo_barras.trim(),
          unidad: formulario.unidad,
          precio: Number(formulario.precio),
          cantidad_inicial: Number(formulario.cantidad_inicial) || 0,
        }),
      });
      setFormulario(FORMULARIO_VACIO);
      setMensaje("Producto creado.");
      await cargar();
    } catch (fallo) {
      setError(fallo.message);
    } finally {
      setCreando(false);
    }
  }

  function abrirEdicion(producto) {
    setProductoEditando(producto);
    setFormEdicion({
      nombre: producto.nombre,
      codigo_barras: producto.codigo_barras,
      unidad: producto.unidad,
      precio: String(producto.precio),
      activo: producto.activo,
    });
    setErrorModal("");
  }

  /**
   * Guarda los cambios del modal de edición.
   * Si el producto tiene ventas, el select de unidad queda deshabilitado; el
   * backend igual rechaza el cambio si se intenta por API.
   */
  async function guardarEdicion(evento) {
    evento.preventDefault();
    setErrorModal("");

    if (!formEdicion.nombre.trim() || !formEdicion.codigo_barras.trim()) {
      setErrorModal("Completá el nombre y el código de barras.");
      return;
    }

    if (!(Number(formEdicion.precio) > 0)) {
      setErrorModal("El precio tiene que ser mayor a cero.");
      return;
    }

    setGuardando(true);
    try {
      await api(`/productos/${productoEditando.producto_id}`, {
        method: "PUT",
        body: JSON.stringify({
          nombre: formEdicion.nombre.trim(),
          codigo_barras: formEdicion.codigo_barras.trim(),
          unidad: formEdicion.unidad,
          precio: Number(formEdicion.precio),
          activo: formEdicion.activo,
        }),
      });
      setProductoEditando(null);
      setMensaje("Producto actualizado.");
      await cargar();
    } catch (fallo) {
      setErrorModal(fallo.message);
    } finally {
      setGuardando(false);
    }
  }

  /** Activa o desactiva un producto sin borrarlo. */
  async function alternarActivo(producto) {
    setError("");
    setMensaje("");
    try {
      await api(`/productos/${producto.producto_id}`, {
        method: "PUT",
        body: JSON.stringify({ activo: !producto.activo }),
      });
      setMensaje(
        producto.activo ? "Producto desactivado." : "Producto activado."
      );
      await cargar();
    } catch (fallo) {
      setError(fallo.message);
    }
  }

  /** Abre el modal de ajuste de stock con la cantidad actual. */
  function abrirStock(producto) {
    setProductoStock(producto);
    setCantidadStock(String(producto.cantidad_disponible));
    setErrorModal("");
  }

  /** Fija la cantidad disponible del producto (valor absoluto, no suma). */
  async function guardarStock(evento) {
    evento.preventDefault();
    setErrorModal("");

    const cantidad = Number(cantidadStock);
    if (!Number.isFinite(cantidad) || cantidad < 0) {
      setErrorModal("La cantidad tiene que ser cero o mayor.");
      return;
    }

    setGuardando(true);
    try {
      await api(`/stock/${productoStock.producto_id}`, {
        method: "PUT",
        body: JSON.stringify({ cantidad_disponible: cantidad }),
      });
      setProductoStock(null);
      setMensaje("Stock actualizado.");
      await cargar();
    } catch (fallo) {
      setErrorModal(fallo.message);
    } finally {
      setGuardando(false);
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
            No tenés permiso para administrar productos.
          </p>
        </main>
      </>
    );
  }

  return (
    <>
      <Header empleado={empleado} />

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6">
        <h1 className="text-2xl font-bold text-amber-900">
          Productos y stock
        </h1>

        {error && (
          <p className="rounded-xl bg-red-50 px-4 py-3 text-red-700">{error}</p>
        )}
        {mensaje && (
          <p className="rounded-xl bg-green-50 px-4 py-3 text-green-700">
            {mensaje}
          </p>
        )}

        <form
          onSubmit={crear}
          className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm"
        >
          <h2 className="mb-3 text-lg font-semibold text-stone-800">
            Nuevo producto
          </h2>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <label className="block lg:col-span-2">
              <span className="mb-1 block text-sm font-medium text-stone-700">
                Nombre
              </span>
              <input
                type="text"
                required
                value={formulario.nombre}
                onChange={(evento) =>
                  actualizarCampo("nombre", evento.target.value)
                }
                className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-sm font-medium text-stone-700">
                Código de barras
              </span>
              <input
                type="text"
                required
                value={formulario.codigo_barras}
                onChange={(evento) =>
                  actualizarCampo("codigo_barras", evento.target.value)
                }
                className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-sm font-medium text-stone-700">
                Unidad
              </span>
              <select
                value={formulario.unidad}
                onChange={(evento) =>
                  actualizarCampo("unidad", evento.target.value)
                }
                className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
              >
                <option value="unidad">Por unidad</option>
                <option value="kg">Por peso (kg)</option>
              </select>
            </label>

            <label className="block">
              <span className="mb-1 block text-sm font-medium text-stone-700">
                Precio
              </span>
              <input
                type="number"
                min="0.01"
                step="0.01"
                required
                value={formulario.precio}
                onChange={(evento) =>
                  actualizarCampo("precio", evento.target.value)
                }
                className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-sm font-medium text-stone-700">
                Stock inicial
              </span>
              <input
                type="number"
                min="0"
                step={formulario.unidad === "kg" ? "0.001" : "1"}
                value={formulario.cantidad_inicial}
                onChange={(evento) =>
                  actualizarCampo("cantidad_inicial", evento.target.value)
                }
                className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
              />
            </label>
          </div>

          <div className="mt-4 flex justify-end">
            <button
              type="submit"
              disabled={creando}
              className="rounded-lg bg-amber-700 px-4 py-2 font-medium text-white hover:bg-amber-800 disabled:opacity-60"
            >
              {creando ? "Creando…" : "Crear producto"}
            </button>
          </div>
        </form>

        <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-stone-200 text-sm">
              <thead className="bg-stone-50 text-left text-stone-600">
                <tr>
                  <th className="px-4 py-3 font-medium">Nombre</th>
                  <th className="px-4 py-3 font-medium">Código</th>
                  <th className="px-4 py-3 font-medium">Unidad</th>
                  <th className="px-4 py-3 font-medium">Precio</th>
                  <th className="px-4 py-3 font-medium">Stock</th>
                  <th className="px-4 py-3 font-medium">Estado</th>
                  <th className="px-4 py-3 font-medium">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {cargandoLista && (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 text-center">
                      Cargando…
                    </td>
                  </tr>
                )}

                {!cargandoLista && productos.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 text-center">
                      No hay productos cargados.
                    </td>
                  </tr>
                )}

                {productos.map((producto) => (
                  <tr key={producto.producto_id}>
                    <td className="px-4 py-3 font-medium text-stone-800">
                      {producto.nombre}
                    </td>
                    <td className="px-4 py-3 text-stone-600">
                      {producto.codigo_barras}
                    </td>
                    <td className="px-4 py-3 text-stone-600">
                      {producto.unidad === "kg" ? "kg" : "unidad"}
                    </td>
                    <td className="px-4 py-3 text-stone-600">
                      {formatearMoneda(producto.precio)}
                    </td>
                    <td className="px-4 py-3 text-stone-600">
                      {formatearCantidad(
                        producto.cantidad_disponible,
                        producto.unidad
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          producto.activo
                            ? "bg-green-100 text-green-800"
                            : "bg-stone-200 text-stone-600"
                        }`}
                      >
                        {producto.activo ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => abrirEdicion(producto)}
                          className="rounded-lg border border-stone-300 px-2 py-1 text-xs font-medium text-stone-700 hover:bg-stone-100"
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          onClick={() => abrirStock(producto)}
                          className="rounded-lg border border-stone-300 px-2 py-1 text-xs font-medium text-stone-700 hover:bg-stone-100"
                        >
                          Stock
                        </button>
                        <button
                          type="button"
                          onClick={() => alternarActivo(producto)}
                          className={`rounded-lg px-2 py-1 text-xs font-medium ${
                            producto.activo
                              ? "border border-red-200 text-red-700 hover:bg-red-50"
                              : "border border-green-200 text-green-700 hover:bg-green-50"
                          }`}
                        >
                          {producto.activo ? "Desactivar" : "Activar"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {productoEditando && formEdicion && (
        <Modal
          titulo={`Editar ${productoEditando.nombre}`}
          onCerrar={() => setProductoEditando(null)}
        >
          <form onSubmit={guardarEdicion} className="space-y-3">
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-stone-700">
                Nombre
              </span>
              <input
                type="text"
                required
                value={formEdicion.nombre}
                onChange={(evento) =>
                  setFormEdicion({ ...formEdicion, nombre: evento.target.value })
                }
                className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-sm font-medium text-stone-700">
                Código de barras
              </span>
              <input
                type="text"
                required
                value={formEdicion.codigo_barras}
                onChange={(evento) =>
                  setFormEdicion({
                    ...formEdicion,
                    codigo_barras: evento.target.value,
                  })
                }
                className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
              />
            </label>

            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-stone-700">
                  Unidad
                </span>
                <select
                  value={formEdicion.unidad}
                  disabled={productoEditando.tiene_ventas}
                  onChange={(evento) =>
                    setFormEdicion({
                      ...formEdicion,
                      unidad: evento.target.value,
                    })
                  }
                  className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none disabled:bg-stone-100"
                >
                  <option value="unidad">Por unidad</option>
                  <option value="kg">Por peso (kg)</option>
                </select>
              </label>

              <label className="block">
                <span className="mb-1 block text-sm font-medium text-stone-700">
                  Precio
                </span>
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  required
                  value={formEdicion.precio}
                  onChange={(evento) =>
                    setFormEdicion({
                      ...formEdicion,
                      precio: evento.target.value,
                    })
                  }
                  className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
                />
              </label>
            </div>

            {productoEditando.tiene_ventas && (
              <p className="text-xs text-stone-500">
                La unidad no se puede cambiar porque el producto ya tiene
                ventas.
              </p>
            )}

            <label className="flex items-center gap-2 text-sm text-stone-700">
              <input
                type="checkbox"
                checked={formEdicion.activo}
                onChange={(evento) =>
                  setFormEdicion({
                    ...formEdicion,
                    activo: evento.target.checked,
                  })
                }
                className="h-4 w-4 rounded border-stone-300"
              />
              Producto activo
            </label>

            {errorModal && <p className="text-sm text-red-700">{errorModal}</p>}

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setProductoEditando(null)}
                className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-100"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={guardando}
                className="rounded-lg bg-amber-700 px-4 py-2 text-sm font-medium text-white hover:bg-amber-800 disabled:opacity-60"
              >
                {guardando ? "Guardando…" : "Guardar"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {productoStock && (
        <Modal
          titulo={`Stock de ${productoStock.nombre}`}
          onCerrar={() => setProductoStock(null)}
        >
          <form onSubmit={guardarStock} className="space-y-3">
            <p className="text-sm text-stone-600">
              Unidad: {productoStock.unidad === "kg" ? "kilogramos" : "unidades"}
            </p>

            <label className="block">
              <span className="mb-1 block text-sm font-medium text-stone-700">
                Cantidad disponible
              </span>
              <input
                type="number"
                min="0"
                step={productoStock.unidad === "kg" ? "0.001" : "1"}
                required
                autoFocus
                value={cantidadStock}
                onChange={(evento) => setCantidadStock(evento.target.value)}
                className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
              />
            </label>

            {errorModal && <p className="text-sm text-red-700">{errorModal}</p>}

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setProductoStock(null)}
                className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-100"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={guardando}
                className="rounded-lg bg-amber-700 px-4 py-2 text-sm font-medium text-white hover:bg-amber-800 disabled:opacity-60"
              >
                {guardando ? "Guardando…" : "Guardar stock"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
