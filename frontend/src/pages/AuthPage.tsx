import { useState } from 'react'
import { LoginForm } from '../components/LoginForm'
import { RegisterForm } from '../components/RegisterForm'

type AuthTab = 'login' | 'register'

export function AuthPage() {
  const [tab, setTab] = useState<AuthTab>('login')

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold text-gray-900">GBH Chat</h1>
          <p className="mt-1 text-sm text-gray-500">Log in or create an account to continue</p>
        </div>

        <div className="mb-6 grid grid-cols-2 rounded-md bg-gray-100 p-1">
          <button
            type="button"
            onClick={() => setTab('login')}
            className={`rounded-md px-3 py-2 text-sm font-medium ${
              tab === 'login' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
            }`}
          >
            Log in
          </button>
          <button
            type="button"
            onClick={() => setTab('register')}
            className={`rounded-md px-3 py-2 text-sm font-medium ${
              tab === 'register' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600'
            }`}
          >
            Sign up
          </button>
        </div>

        {tab === 'login' ? <LoginForm /> : <RegisterForm />}
      </div>
    </div>
  )
}
