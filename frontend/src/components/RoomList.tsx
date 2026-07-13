import type { ChatRoom } from '../types'

interface RoomListProps {
  rooms: ChatRoom[]
  onEnter: (roomId: number) => void
  loading?: boolean
}

export function RoomList({ rooms, onEnter, loading = false }: RoomListProps) {
  if (loading) {
    return <p className="text-sm text-gray-500">Cargando salas...</p>
  }

  if (rooms.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-gray-300 bg-white p-6 text-center text-sm text-gray-500">
        No hay salas todavía. Crea la primera.
      </div>
    )
  }

  return (
    <ul className="space-y-2">
      {rooms.map((room) => (
        <li
          key={room.id}
          className="flex items-center justify-between rounded-md border border-gray-200 bg-white px-4 py-3"
        >
          <div>
            <p className="font-medium text-gray-900">{room.name}</p>
            <p className="text-xs text-gray-500">
              Creada el {new Date(room.created_at).toLocaleString()}
            </p>
          </div>
          <button
            type="button"
            onClick={() => onEnter(room.id)}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
          >
            Entrar
          </button>
        </li>
      ))}
    </ul>
  )
}
