/**
 * Cola offline con IndexedDB (Dexie).
 * Cuando la App Principal pierde internet, las mutaciones se guardan aquí.
 * Al recuperar la conexión, se envían al backend en orden FIFO.
 */
import Dexie, { type Table } from 'dexie'
import type { SyncItem } from './types'
import { api } from './api'

class OfflineDB extends Dexie {
  syncQueue!: Table<SyncItem, number>

  constructor() {
    super('erp_offline')
    this.version(1).stores({
      syncQueue: '++id, estado, fecha_creacion',
    })
  }
}

const db = new OfflineDB()

export const offlineQueue = {
  encolar: (item: Omit<SyncItem, 'id'>) => db.syncQueue.add(item),

  pendientes: () => db.syncQueue.where('estado').equals('pendiente').toArray(),

  /**
   * Intenta sincronizar todos los items pendientes.
   * Llamar cuando se detecta reconexión a internet.
   */
  sincronizar: async () => {
    if (!navigator.onLine) return
    const items = await offlineQueue.pendientes()
    if (!items.length) return

    console.log(`[Sync] Enviando ${items.length} operaciones pendientes...`)

    for (const item of items) {
      try {
        await api.request({
          method: item.method,
          url: item.endpoint,
          data: item.payload,
          _retry: true,
        } as never)
        await db.syncQueue.update(item.id!, { estado: 'sincronizado' })
      } catch {
        await db.syncQueue.update(item.id!, {
          estado: 'error',
          intentos: item.intentos + 1,
        })
      }
    }
    console.log('[Sync] Sincronización completada')
  },

  contarPendientes: () => db.syncQueue.where('estado').equals('pendiente').count(),
}

// Escuchar reconexión y sincronizar automáticamente
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => offlineQueue.sincronizar())
}
