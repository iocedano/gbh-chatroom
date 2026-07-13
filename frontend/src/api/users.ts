import { api } from './client'
import type { User } from '../types'

export function getCurrentUser() {
  return api<User>('/users/me')
}
