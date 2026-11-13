import "./globals.css";

/** Metadatos que Next usa para el título y la descripción de la pestaña. */
export const metadata = {
  title: "El Molino",
  description: "Sistema de gestión de la panadería El Molino",
};

/**
 * Layout raíz de la aplicación.
 * Define el idioma y el contenedor base de todas las páginas.
 */
export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
