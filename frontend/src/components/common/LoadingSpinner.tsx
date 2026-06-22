import React from 'react'
import { CircularProgress, Box, Typography } from '@mui/material'

export const LoadingSpinner: React.FC<{ message?: string }> = ({ 
  message = 'Loading...' 
}) => {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '400px',
        gap: 2,
      }}
    >
      <CircularProgress />
      <Typography variant="body1" color="textSecondary">
        {message}
      </Typography>
    </Box>
  )
}
