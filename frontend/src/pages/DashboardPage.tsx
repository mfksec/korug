import React from 'react'
import { Box, Container } from '@mui/material'
import { Navbar } from '@/components/common/Navbar'
import { DashboardHome } from '@/components/dashboard/DashboardHome'

interface DashboardPageProps {
  onLogout: () => void
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onLogout }) => {
  return (
    <Box>
      <Navbar onLogout={onLogout} />
      <Container maxWidth="lg">
        <DashboardHome />
      </Container>
    </Box>
  )
}
