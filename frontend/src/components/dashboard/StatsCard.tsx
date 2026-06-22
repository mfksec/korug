import React from 'react'
import {
  Card,
  CardContent,
  Typography,
  Box,
  CircularProgress,
} from '@mui/material'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'

interface StatsCardProps {
  title: string
  value: string | number
  icon?: React.ReactNode
  trend?: number
  isLoading?: boolean
}

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  icon,
  trend,
  isLoading = false,
}) => {
  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography color="textSecondary" gutterBottom>
              {title}
            </Typography>
            <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
              {isLoading ? <CircularProgress size={24} /> : value}
            </Typography>
            {trend !== undefined && (
              <Box sx={{ display: 'flex', alignItems: 'center', mt: 1, color: 'success.main' }}>
                <TrendingUpIcon sx={{ fontSize: 18, mr: 0.5 }} />
                <Typography variant="caption">+{trend}% this week</Typography>
              </Box>
            )}
          </Box>
          {icon && (
            <Box sx={{ color: 'primary.main', fontSize: '2rem' }}>
              {icon}
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  )
}
