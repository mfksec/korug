import React from 'react'
import { Card, CardContent, Typography, Box, CircularProgress, alpha } from '@mui/material'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'

interface StatsCardProps {
  title: string
  value: string | number
  icon?: React.ReactNode
  trend?: number
  isLoading?: boolean
  /** Accent colour for the top bar / selected ring (any CSS colour or theme token). */
  accent?: string
  /** Renders the card as a button and applies hover affordance. */
  onClick?: () => void
  /** Highlights the card as the active selection. */
  selected?: boolean
}

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  icon,
  trend,
  isLoading = false,
  accent = 'primary.main',
  onClick,
  selected = false,
}) => {
  const clickable = Boolean(onClick)
  return (
    <Card
      onClick={onClick}
      sx={{
        position: 'relative',
        overflow: 'hidden',
        height: '100%',
        cursor: clickable ? 'pointer' : 'default',
        transition: 'transform .15s ease, box-shadow .15s ease, border-color .15s ease',
        borderColor: selected ? accent : undefined,
        ...(selected && { boxShadow: (t) => `0 0 0 1px ${t.palette.mode === 'dark' ? alpha('#fff', 0.04) : 'transparent'}` }),
        '&::before': {
          content: '""',
          position: 'absolute',
          insetInline: 0,
          top: 0,
          height: 3,
          bgcolor: accent,
          opacity: selected ? 1 : 0.55,
        },
        ...(clickable && {
          '&:hover': { transform: 'translateY(-2px)', boxShadow: 4 },
        }),
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography color="textSecondary" gutterBottom sx={{ fontSize: 13, fontWeight: 600 }}>
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
          {icon && <Box sx={{ color: accent, fontSize: '2rem' }}>{icon}</Box>}
        </Box>
      </CardContent>
    </Card>
  )
}
