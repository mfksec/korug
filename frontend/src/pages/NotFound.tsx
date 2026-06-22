import React from 'react'
import { Container, Typography, Box } from '@mui/material'

export const NotFound: React.FC = () => {
  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          textAlign: 'center',
        }}
      >
        <Typography variant="h1" sx={{ fontSize: '4rem', fontWeight: 'bold', mb: 2 }}>
          404
        </Typography>
        <Typography variant="h5" sx={{ mb: 2 }}>
          Page Not Found
        </Typography>
        <Typography variant="body1" color="textSecondary" sx={{ mb: 3 }}>
          The page you're looking for doesn't exist.
        </Typography>
        <a href="/dashboard" style={{ textDecoration: 'none', color: '#1976d2' }}>
          ← Back to Dashboard
        </a>
      </Box>
    </Container>
  )
}
