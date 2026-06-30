import { type ReactElement } from 'react'
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ThemeProvider, createTheme } from '@mui/material'
import { EmptyState } from './Widgets'

const renderWithTheme = (ui: ReactElement) =>
  render(<ThemeProvider theme={createTheme()}>{ui}</ThemeProvider>)

describe('EmptyState', () => {
  it('renders the title and description', () => {
    renderWithTheme(<EmptyState title="No domains yet" description="Add your first domain." />)
    expect(screen.getByText('No domains yet')).toBeInTheDocument()
    expect(screen.getByText('Add your first domain.')).toBeInTheDocument()
  })

  it('exposes a status role so screen readers announce it', () => {
    renderWithTheme(<EmptyState title="Nothing here" />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('renders an action when provided', () => {
    renderWithTheme(<EmptyState title="x" action={<button>Add domain</button>} />)
    expect(screen.getByRole('button', { name: 'Add domain' })).toBeInTheDocument()
  })
})
