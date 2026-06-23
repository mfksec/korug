// Auth state is provided application-wide via AuthContext so that the navbar,
// route guards, and pages all share a single source of truth (including the
// user's role). This module re-exports the context hook for backward
// compatibility with existing `@/hooks/useAuth` imports.
export { useAuth } from '@/contexts/AuthContext'
