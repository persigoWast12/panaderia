/**
 * Configuración de Next.js.
 *
 * El navegador nunca llama directo al backend: pide `/api/...` al mismo
 * servidor de Next, y Next reenvía a FastAPI. Así la cookie de sesión queda en
 * el mismo origen y no hace falta configurar CORS.
 *
 * @type {import('next').NextConfig}
 */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL ?? "http://127.0.0.1:8000"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
