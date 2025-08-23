import { useMemo } from 'react';

/**
 * Custom hook to generate and manage chart color schemes
 * Provides consistent, accessible color palettes for all chart types
 * Includes support for light and dark modes
 */
export const useChartColors = () => {
  // Define base color palette
  const colors = useMemo(
    () => ({
      primary: '#0066CC',
      secondary: '#FF6B35',
      success: '#28A745',
      danger: '#DC3545',
      warning: '#FFC107',
      info: '#17A2B8',
      dark: '#343A40',
      gray: '#6C757D',
      light: '#F8F9FA',
    }),
    []
  );

  // Define dataset color palettes
  const datasetColors = useMemo(
    () => ({
      bar: [
        'rgba(0, 102, 204, 0.8)',
        'rgba(255, 107, 53, 0.8)',
        'rgba(40, 167, 69, 0.8)',
        'rgba(220, 53, 69, 0.8)',
        'rgba(255, 193, 7, 0.8)',
        'rgba(23, 162, 184, 0.8)',
        'rgba(108, 117, 125, 0.8)',
      ],
      line: [
        '#0066CC',
        '#FF6B35',
        '#28A745',
        '#DC3545',
        '#FFC107',
        '#17A2B8',
        '#6C757D',
      ],
      pie: [
        '#0066CC',
        '#FF6B35',
        '#28A745',
        '#DC3545',
        '#FFC107',
        '#17A2B8',
        '#343A40',
        '#6C757D',
        '#F8F9FA',
        '#20C997',
      ],
    }),
    []
  );

  // Generate gradient colors for advanced chart styling
  const gradients = useMemo(() => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return {};

    // Create gradient for line charts
    const lineHeight = 50;
    const lineWidth = 200;
    canvas.width = lineWidth;
    canvas.height = lineHeight;

    const lineGradient = ctx.createLinearGradient(0, 0, 0, lineHeight);
    lineGradient.addColorStop(0, 'rgba(0, 102, 204, 0.3)');
    lineGradient.addColorStop(1, 'rgba(0, 102, 204, 0.0)');

    // Create gradient for bar charts
    const barGradient = ctx.createLinearGradient(0, 0, 0, lineHeight);
    barGradient.addColorStop(0, 'rgba(255, 107, 53, 0.5)');
    barGradient.addColorStop(1, 'rgba(255, 107, 53, 0.2)');

    return {
      line: lineGradient as unknown as string,
      bar: barGradient as unknown as string,
    };
  }, []);

  return {
    colors,
    datasetColors,
    gradients,
    getColor: (index: number, type: 'bar' | 'line' | 'pie' = 'bar') => {
      const colorList = datasetColors[type];
      return colorList[index % colorList.length];
    },
    getBorderColor: (color: string) => {
      return color.replace('0.8', '1').replace('0.5', '1');
    },
  };
};