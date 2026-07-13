import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthProvider'
import { useAuth } from './hooks/useAuth'
import { AuthPage } from './pages/AuthPage'
import { ChatPage } from './pages/ChatPage'
import { RoomsPage } from './pages/RoomsPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isCheckingSession } = useAuth()
  if (isCheckingSession) {
    return <SessionLoading />
  }
  if (!isAuthenticated) {
    return <Navigate to="/" replace />
  }
  return children
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isCheckingSession } = useAuth()
  if (isCheckingSession) {
    return <SessionLoading />
  }
  if (isAuthenticated) {
    return <Navigate to="/rooms" replace />
  }
  return children
}

function SessionLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 text-sm text-gray-500">
      Cargando sesión...
    </div>
  )
}

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <PublicRoute>
            <AuthPage />
          </PublicRoute>
        }
      />
      <Route
        path="/rooms"
        element={
          <ProtectedRoute>
            <RoomsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/rooms/:roomId"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
