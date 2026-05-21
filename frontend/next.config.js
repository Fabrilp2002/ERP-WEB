/** @type {import('next').NextConfig} */
const nextConfig = {
  // Nota: 'output: standalone' se removió el 2026-05-15 porque era residual
  // del build de Electron viejo. En Vercel rompe la auto-detección del output.
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*.supabase.co',
      },
    ],
  },

  // v7.2 — Redirects de las rutas viejas /cuentas/* a sus reemplazos.
  // Cualquier bookmark, link compartido o referencia externa sigue funcionando.
  async redirects() {
    return [
      { source: '/cuentas', destination: '/comprobantes', permanent: true },
      { source: '/cuentas/cliente/:id', destination: '/clientes/:id', permanent: true },
      { source: '/cuentas/proveedor/:id', destination: '/proveedores/:id', permanent: true },
    ]
  },
}

module.exports = nextConfig
