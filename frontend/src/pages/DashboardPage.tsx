import React from 'react'
import { Box, Container } from '@mui/material'
import { Navbar } from '@/components/common/Navbar'
import { DashboardHome } from '@/components/dashboard/DashboardHome'

export const DashboardPage: React.FC = () => {
  return (
    <Box>
      <Navbar />
      <Container maxWidth="lg">
        <DashboardHome />
      </Container>
    </Box>
  )
}
