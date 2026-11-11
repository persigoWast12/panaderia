"use client";

import { useEffect, useState } from "react";

import Header from "@/components/Header";
import Modal from "@/components/Modal";
import { api } from "@/lib/api";
import { ETIQUETAS_ROL } from "@/lib/roles";
import { useSesion } from "@/lib/sesion";

const ROLES = ["cajero", "encargado", "contador", "dueno"];

const FORMULARIO_VACIO = {
  nombre: "",
  usuario: "",
  rol: "cajero",
  password: "",
};

/**
 * Administración de empleados, solo para el dueño.
 *
 * Un mismo modal cambia de modo según la acción:
 * - `crear`: nombre, usuario, rol y contraseña inicial;
 * - `editar`: nombre, usuario y rol (el rol propio no se puede cambiar);
 * - `password`: solo la contraseña nueva.
 *
 * El backend aplica las mismas reglas; la interfaz las refleja para evitar
 * errores evitables (por ejemplo, deshabilitar la baja de uno mismo).
 */
export default function Empleados() {
  const { empleado, cargando, error: errorSesion, permitido } = useSesion([
    "dueno",
  ]);

  const [empleados, setEmpleados] = useState([]);
  const [cargandoLista, setCargandoLista] = useState(true);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");

  const [modo, setModo] = useState(null);
  const [seleccionado, setSeleccionado] = useState(null);
  const [formulario, setFormulario] = useState(FORMULARIO_VACIO);
  const [errorModal, setErrorModal] = useState("");
  const [guardando, setGuardando] = useState(false);

  /** Trae todos los empleados, incluidos los inactivos. */
  async function cargar() {
    setCargandoLista(true);
    try {
      const datos = await api("/empleados");
      setEmpleados(datos);
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

  function abrirCrear() {
    setModo("crear");
    setSeleccionado(null);
    setFormulario(FORMULARIO_VACIO);
    setErrorModal("");
  }

  function abrirEditar(persona) {
    setModo("editar");
    setSeleccionado(persona);
    setFormulario({
      nombre: persona.nombre,
      usuario: persona.usuario,
      rol: persona.rol,
      password: "",
    });
    setErrorModal("");
  }

  function abrirPassword(persona) {
    setModo("password");
    setSeleccionado(persona);
    setFormulario({ ...FORMULARIO_VACIO, password: "" });
    setErrorModal("");
  }

  function cerrarModal() {
    setModo(null);
    setSeleccionado(null);
    setErrorModal("");
  }

  /**
   * Guarda según el modo del modal. Para crear y resetear exige al menos 8
   * caracteres; para editar no toca la contraseña.
   */
  async function guardar(evento) {
    evento.preventDefault();
    setErrorModal("");

    if (!formulario.nombre.trim() || !formulario.usuario.trim()) {
      setErrorModal("Completá el nombre y el usuario.");
      return;
    }

    if (modo !== "editar" && formulario.password.length < 8) {
      setErrorModal("La contraseña tiene que tener al menos 8 caracteres.");
      return;
    }

    setGuardando(true);
    try {
      if (modo === "crear") {
        await api("/empleados", {
          method: "POST",
          body: JSON.stringify({
            nombre: formulario.nombre.trim(),
            usuario: formulario.usuario.trim(),
            rol: formulario.rol,
            password: formulario.password,
          }),
        });
        setMensaje("Empleado creado.");
      } else if (modo === "editar") {
        await api(`/empleados/${seleccionado.id}`, {
          method: "PUT",
          body: JSON.stringify({
            nombre: formulario.nombre.trim(),
            usuario: formulario.usuario.trim(),
            rol: formulario.rol,
          }),
        });
        setMensaje("Empleado actualizado.");
      } else if (modo === "password") {
        await api(`/empleados/${seleccionado.id}/password`, {
          method: "PUT",
          body: JSON.stringify({ password: formulario.password }),
        });
        setMensaje(
          seleccionado.id === empleado.id
            ? "Contraseña actualizada. Volvé a iniciar sesión."
            : "Contraseña actualizada. Se cerraron las sesiones del empleado."
        );
      }

      cerrarModal();

      // Si el dueño cambió su propia clave, el backend cerró su sesión:
      // directamente se lo manda al login.
      if (modo === "password" && seleccionado.id === empleado.id) {
        window.location.href = "/login";
        return;
      }

      await cargar();
    } catch (fallo) {
      setErrorModal(fallo.message);
    } finally {
      setGuardando(false);
    }
  }

  /** Activa o desactiva a otro empleado (nunca a uno mismo). */
  async function alternarActivo(persona) {
    setError("");
    setMensaje("");

    if (persona.id === empleado.id) {
      setError("No podés desactivar tu propio usuario.");
      return;
    }

    // Desactivar es una acción importante: se pide confirmación.
    const accion = persona.activo ? "desactivar" : "activar";
    if (!window.confirm(`¿Querés ${accion} a ${persona.nombre}?`)) return;

    try {
      await api(`/empleados/${persona.id}`, {
        method: "PUT",
        body: JSON.stringify({ activo: !persona.activo }),
      });
      setMensaje(
        persona.activo ? "Empleado desactivado." : "Empleado activado."
      );
      await cargar();
    } catch (fallo) {
      setError(fallo.message);
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
            No tenés permiso para administrar empleados.
          </p>
        </main>
      </>
    );
  }

  const tituloModal =
    modo === "crear"
      ? "Nuevo empleado"
      : modo === "editar"
        ? `Editar ${seleccionado?.nombre ?? ""}`
        : `Cambiar contraseña de ${seleccionado?.nombre ?? ""}`;

  return (
    <>
      <Header empleado={empleado} />

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-amber-900">Empleados</h1>
            <p className="text-sm text-stone-600">
              Altas, bajas y cambios de contraseña.
            </p>
          </div>
          <button
            type="button"
            onClick={abrirCrear}
            className="rounded-lg bg-amber-700 px-4 py-2 font-medium text-white hover:bg-amber-800"
          >
            Nuevo empleado
          </button>
        </div>

        {error && (
          <p className="rounded-xl bg-red-50 px-4 py-3 text-red-700">{error}</p>
        )}
        {mensaje && (
          <p className="rounded-xl bg-green-50 px-4 py-3 text-green-700">
            {mensaje}
          </p>
        )}

        <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-stone-200 text-sm">
              <thead className="bg-stone-50 text-left text-stone-600">
                <tr>
                  <th className="px-4 py-3 font-medium">Nombre</th>
                  <th className="px-4 py-3 font-medium">Usuario</th>
                  <th className="px-4 py-3 font-medium">Rol</th>
                  <th className="px-4 py-3 font-medium">Estado</th>
                  <th className="px-4 py-3 font-medium">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100">
                {cargandoLista && (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center">
                      Cargando…
                    </td>
                  </tr>
                )}

                {!cargandoLista &&
                  empleados.map((persona) => {
                    const esUnoMismo = persona.id === empleado.id;
                    return (
                      <tr key={persona.id}>
                        <td className="px-4 py-3 font-medium text-stone-800">
                          {persona.nombre}
                          {esUnoMismo && (
                            <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
                              Vos
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-stone-600">
                          {persona.usuario}
                        </td>
                        <td className="px-4 py-3 text-stone-600">
                          {ETIQUETAS_ROL[persona.rol] ?? persona.rol}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                              persona.activo
                                ? "bg-green-100 text-green-800"
                                : "bg-stone-200 text-stone-600"
                            }`}
                          >
                            {persona.activo ? "Activo" : "Inactivo"}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() => abrirEditar(persona)}
                              className="rounded-lg border border-stone-300 px-2 py-1 text-xs font-medium text-stone-700 hover:bg-stone-100"
                            >
                              Editar
                            </button>
                            <button
                              type="button"
                              onClick={() => abrirPassword(persona)}
                              className="rounded-lg border border-stone-300 px-2 py-1 text-xs font-medium text-stone-700 hover:bg-stone-100"
                            >
                              Clave
                            </button>
                            <button
                              type="button"
                              onClick={() => alternarActivo(persona)}
                              disabled={esUnoMismo}
                              className={`rounded-lg px-2 py-1 text-xs font-medium disabled:cursor-not-allowed disabled:opacity-40 ${
                                persona.activo
                                  ? "border border-red-200 text-red-700 hover:bg-red-50"
                                  : "border border-green-200 text-green-700 hover:bg-green-50"
                              }`}
                            >
                              {persona.activo ? "Desactivar" : "Activar"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {modo && (
        <Modal titulo={tituloModal} onCerrar={cerrarModal}>
          <form onSubmit={guardar} className="space-y-3">
            {modo !== "password" && (
              <>
                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-stone-700">
                    Nombre
                  </span>
                  <input
                    type="text"
                    required
                    autoFocus
                    value={formulario.nombre}
                    onChange={(evento) =>
                      setFormulario({
                        ...formulario,
                        nombre: evento.target.value,
                      })
                    }
                    className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
                  />
                </label>

                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-stone-700">
                    Usuario
                  </span>
                  <input
                    type="text"
                    required
                    autoCapitalize="none"
                    value={formulario.usuario}
                    onChange={(evento) =>
                      setFormulario({
                        ...formulario,
                        usuario: evento.target.value,
                      })
                    }
                    className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
                  />
                </label>

                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-stone-700">
                    Rol
                  </span>
                  <select
                    value={formulario.rol}
                    disabled={
                      modo === "editar" && seleccionado.id === empleado.id
                    }
                    onChange={(evento) =>
                      setFormulario({
                        ...formulario,
                        rol: evento.target.value,
                      })
                    }
                    className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none disabled:bg-stone-100"
                  >
                    {ROLES.map((rol) => (
                      <option key={rol} value={rol}>
                        {ETIQUETAS_ROL[rol]}
                      </option>
                    ))}
                  </select>
                </label>
              </>
            )}

            {(modo === "crear" || modo === "password") && (
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-stone-700">
                  {modo === "crear" ? "Contraseña inicial" : "Contraseña nueva"}
                </span>
                <input
                  type="password"
                  required
                  minLength={8}
                  autoFocus={modo === "password"}
                  autoComplete="new-password"
                  value={formulario.password}
                  onChange={(evento) =>
                    setFormulario({
                      ...formulario,
                      password: evento.target.value,
                    })
                  }
                  className="w-full rounded-lg border border-stone-300 px-3 py-2 focus:border-amber-600 focus:outline-none"
                />
                <span className="mt-1 block text-xs text-stone-500">
                  Mínimo 8 caracteres.
                </span>
              </label>
            )}

            {modo === "password" && seleccionado.id === empleado.id && (
              <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900">
                Al cambiar tu propia contraseña se cierran tus sesiones y
                tenés que volver a entrar.
              </p>
            )}

            {errorModal && <p className="text-sm text-red-700">{errorModal}</p>}

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={cerrarModal}
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
    </>
  );
}
