import React from 'react';
import { ChartData, ChartOptions } from '../../types';

interface PieChartProps {
  data: ChartData;
  options?: ChartOptions;
  loading?: boolean;
  error?: string | null;
  width?: string;
  height?: string;
}

/**
 * PieChart component for displaying pie chart visualizations
 * using Canvas-based rendering. Handles loading and error states.
 */
const PieChart: React.FC<PieChartProps> = ({
  data,
  options = {},
  loading = false,
  error = null,
  width = '100%',
  height = '300px',
}) => {
  if (loading) {
    return (
      <div style={{ width, height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p>Loading chart...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ width, height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'red' }}>
        <p>Error: {error}</p>
      </div>
    );
  }

  // Validate data
  if (!data || !data.labels || !data.datasets || data.datasets.length === 0) {
    return (
      <div style={{ width, height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'orange' }}>
        <p>No valid data provided</p>
      </div>
    );
  }

  const totalDataPoints = data.datasets[0].data.reduce((sum, value) => sum + value, 0);
  if (totalDataPoints === 0) {
    return (
      <div style={{ width, height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <p>No data to display</p>
      </div>
    );
  }

  // Default pie chart colors if not provided
  const defaultColors = [
    '#FF6384',
    '#36A2EB',
    '#FFCE56',
    '#4BC0C0',
    '#9966FF',
    '#FF9F40',
    '#FF6384',
    '#C9CBCF',
  ];

  const chartRef = React.useRef<HTMLCanvasElement>(null);

  React.useEffect(() => {
    const canvas = chartRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) * 0.8;
    const dataset = data.datasets[0];
    const values = dataset.data;
    const colors = (dataset.backgroundColor as string[] | undefined) ||
      values.map((_, index) => defaultColors[index % defaultColors.length]);

    let startAngle = 0;

    // Draw each slice
    values.forEach((value, index) => {
      const sliceAngle = (2 * Math.PI * value) / totalDataPoints;
      const endAngle = startAngle + sliceAngle;

      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, startAngle, endAngle);
      ctx.closePath();
      ctx.fillStyle = colors[index];
      ctx.fill();

      // Draw border if specified
      if (dataset.borderColor) {
        const borderColor = Array.isArray(dataset.borderColor)
          ? dataset.borderColor[index]
          : dataset.borderColor;
        ctx.strokeStyle = borderColor;
        ctx.lineWidth = dataset.borderWidth || 1;
        ctx.stroke();
      }

      startAngle = endAngle;
    });

    // Draw labels if enabled
    if (options.plugins?.legend?.display !== false) {
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'left';
      const legendX = centerX + radius + 20;
      const legendY = centerY - (values.length * 15) / 2;

      data.labels.forEach((label, index) => {
        ctx.fillStyle = colors[index];
        ctx.fillRect(legendX, legendY + index * 15, 10, 10);
        ctx.fillStyle = '#000';
        ctx.fillText(label, legendX + 15, legendY + index * 15 + 10);
      });
    }
  }, [data, options, totalDataPoints]);

  return (
    <div style={{ width, height, position: 'relative' }}>
      <canvas
        ref={chartRef}
        width={400}
        height={300}
        style={{ width: '100%', height: '100%' }}
        aria-label="Pie chart visualization"
        role="img"
      />
    </div>
  );
};

export default PieChart;