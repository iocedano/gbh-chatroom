import { useState, type FormEvent } from 'react'
import { ErrorBanner } from './ErrorBanner'

interface CreateRoomFormProps {
  onCreate: (name: string) => Promise<void>
}

export function CreateRoomForm({ onCreate }: CreateRoomFormProps) {
  const [name, setName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      await onCreate(name.trim())
      setName('')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'No se pudo crear la sala'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3 rounded-md border border-gray-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-gray-900">Crear sala</h2>
      <ErrorBanner message={error} />
      <div className="flex gap-2">
        <input
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Nombre de la sala"
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
          maxLength={150}
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Creando...' : 'Crear'}
        </button>
      </div>
    </form>
  )
}
