// Aset di public/ dimuat relatif terhadap base Vite: dashboard disajikan di /dashboard/,
// preview frontend di /. URL absolut "/assets/..." akan salah alamat di bawah /dashboard/.
export const assetUrl = (path: string) => `${import.meta.env?.BASE_URL ?? '/'}${path.replace(/^\/+/, '')}`
