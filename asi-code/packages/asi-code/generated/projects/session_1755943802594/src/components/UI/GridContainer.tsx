import React from 'react';
import { Box, Container, Grid, Paper, Theme, useMediaQuery, useTheme } from '@mui/material';

interface GridContainerProps {
  /**
   * Children elements to be rendered inside the grid
   */
  children: React.ReactNode;
  /**
   * Optional className to apply custom styles
   */
  className?: string;
  /**
   * Number of columns in the grid layout (default: 12)
   * @default 12
   */
  columns?: number;
  /**
   * Spacing between grid items (default: 3)
   * @default 3
   */
  spacing?: number;
  /**
   * Max width of the container (default: 'xl')
   * @default 'xl'
   */
  maxWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | false;
  /**
   * Whether to include a paper elevation around the grid (default: false)
   * @default false
   */
  withPaper?: boolean;
  /**
   * Elevation level for Paper component if withPaper is true (default: 2)
   * @default 2
   */
  elevation?: number;
  /**
   * Optional padding for the container (default: 3)
   * @default 3
   */
  padding?: number;
}

/**
 * Responsive grid container component for organizing dashboard content
 * Provides a consistent layout structure using Material UI's Grid system
 * Automatically adjusts column layout based on screen size
 */
const GridContainer: React.FC<GridContainerProps> = ({
  children,
  className,
  columns = 12,
  spacing = 3,
  maxWidth = 'xl',
  withPaper = false,
  elevation = 2,
  padding = 3,
}) => {
  const theme: Theme = useTheme();
  const isXs = useMediaQuery(theme.breakpoints.down('sm'));
  const isSm = useMediaQuery(theme.breakpoints.between('sm', 'md'));
  const isMd = useMediaQuery(theme.breakpoints.between('md', 'lg'));

  // Determine number of columns per item based on screen size
  const getColumnsPerItem = (): number => {
    if (isXs) return 12; // 1 column on extra small screens
    if (isSm) return 6; // 2 columns on small screens
    if (isMd) return 4; // 3 columns on medium screens
    return Math.floor(columns / 4); // 4+ columns on large screens
  };

  const gridSpacing = spacing;
  const gridColumn = getColumnsPerItem();

  const content = (
    <Grid container spacing={gridSpacing}>
      {React.Children.map(children, (child) => (
        <Grid item xs={12} sm={6} md={4} lg={3} key={React.isValidElement(child) ? React.elementKey(child) : undefined}>
          {child}
        </Grid>
      ))}
    </Grid>
  );

  return (
    <Container maxWidth={maxWidth} className={className} sx={{ py: padding }}>
      {withPaper ? (
        <Paper elevation={elevation} sx={{ p: 2, height: '100%' }}>
          {content}
        </Paper>
      ) : (
        content
      )}
    </Container>
  );
};

export default GridContainer;