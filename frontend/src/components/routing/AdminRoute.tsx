import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'

interface AdminRouteProps {
  children: React.ReactNode
}

/** Route guard for admin-only pages (Users, Audit logs). Non-admins are
 * redirected to the dashboard. Backend endpoints enforce this too; this just
 * keeps the UI honest. */
export const AdminRoute: React.FC<AdminRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading, isAdmin } = useAuth()

  if (isLoading) {
    return <LoadingSpinner message="Loading..." />
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />
  }
  return <>{children}</>
}
