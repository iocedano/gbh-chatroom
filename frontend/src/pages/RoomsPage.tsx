import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { createRoom, joinRoom, listRooms } from '../api/rooms'
import { CreateRoomForm } from '../components/CreateRoomForm'
import { ErrorBanner } from '../components/ErrorBanner'
import { RoomList } from '../components/RoomList'
import { useAuth } from '../hooks/useAuth'
import type { ChatRoom } from '../types'

export function RoomsPage() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [rooms, setRooms] = useState<ChatRoom[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadRooms = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const data = await listRooms()
      setRooms(data)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout()
        navigate('/', { replace: true })
        return
      }
      const message = err instanceof ApiError ? err.message : 'Could not load rooms'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [logout, navigate])

  useEffect(() => {
    void loadRooms()
  }, [loadRooms])

  async function handleCreate(name: string) {
    await createRoom(name)
    await loadRooms()
  }

  async function handleEnter(roomId: number) {
    setError(null)

    try {
      await joinRoom(roomId)
      navigate(`/rooms/${roomId}`)
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Could not enter room'
      setError(message)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Chat rooms</h1>
            <p className="text-sm text-gray-500">Hi, {user?.username}</p>
          </div>
          <button
            type="button"
            onClick={logout}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          >
            Log out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-4 px-4 py-6">
        <ErrorBanner message={error} />
        <CreateRoomForm onCreate={handleCreate} />
        <RoomList rooms={rooms} onEnter={handleEnter} loading={loading} />
      </main>
    </div>
  )
}
