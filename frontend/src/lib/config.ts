export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ||
  (process.env.NODE_ENV === 'development'
    ? 'http://localhost:8000'
    : 'https://erp-web-backend-i5zv.onrender.com')

if (!API_BASE_URL && typeof window !== 'undefined') {
  throw new Error('Falta NEXT_PUBLIC_API_URL para conectar el frontend con la API.')
}
