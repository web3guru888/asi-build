import React from 'react';
import { Card as MuiCard, CardProps as MuiCardProps, CardContent, CardHeader, Typography, Box, Theme, useTheme } from '@mui/material';

/**
 * Props interface for the Card component
 */
export interface CardProps extends Omit<MuiCardProps, 'title'> {
  /**
   * Optional title for the card header
   */
  title?: string;
  /**
   * Optional subtitle for the card header
   */
  subtitle?: string;
  /**
   * Content to display in the card action area (e.g. buttons)
   */
  actions?: React.ReactNode;
  /**
   * Children elements to be rendered inside the card content
   */
  children: React.ReactNode;
  /**
   * Optional header actions (e.g. menu, buttons in header)
   */
  headerActions?: React.ReactNode;
  /**
   * Whether the card should have elevated styling
   * @default true
   */
  elevation?: boolean;
  /**
   * Optional background color for the card header
   */
  headerBackgroundColor?: string;
}

/**
 * A reusable Card component with support for header, content, and actions.
 * Built on top of Material-UI Card with extended styling and props.
 *
 * @example
 * <Card title="Revenue Overview" subtitle="Last 30 days">
 *   <BarChart data={chartData} />
 * </Card>
 */
const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  actions,
  children,
  headerActions,
  elevation = true,
  headerBackgroundColor,
  sx,
  ...otherProps
}) => {
  const theme: Theme = useTheme();
  const hasHeader = !!(title || subtitle || headerActions);

  return (
    <MuiCard
      raised={elevation}
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        ...sx,
      }}
      {...otherProps}
    >
      {hasHeader && (
        <CardHeader
          title={
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Box>
                {title && (
                  <Typography variant="h6" component="div">
                    {title}
                  </Typography>
                )}
                {subtitle && (
                  <Typography variant="body2" color="text.secondary" component="div">
                    {subtitle}
                  </Typography>
                )}
              </Box>
              {headerActions && <Box>{headerActions}</Box>}
            </Box>
          }
          sx={{
            pb: 0,
            backgroundColor: headerBackgroundColor || 'background.paper',
            borderBottom: title ? `1px solid ${theme.palette.divider}` : 'none',
            '.MuiCardHeader-action': { alignSelf: 'center' },
          }}
        />
      )}
      <CardContent
        sx={{
          px: 2,
          pt: hasHeader ? 1 : 2,
          pb: '16px !important',
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {children}
      </CardContent>
      {actions && (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'flex-end',
            p: 1,
            pt: 0,
            gap: 1,
          }}
        >
          {actions}
        </Box>
      )}
    </MuiCard>
  );
};

export default Card;