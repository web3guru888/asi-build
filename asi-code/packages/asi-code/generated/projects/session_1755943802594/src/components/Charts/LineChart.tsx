import React from 'react';
import { ChartData, ChartOptions } from '../../types';

interface LineChartProps {
  data: ChartData;
  options?: ChartOptions;
  loading?: boolean;
  error?: string | null;
  height?: string;
  width?: string;
}

const defaultOptions: ChartOptions = {
  responsive: true,
  plugins: {
    legend: {
      position: 'top' as const,
    },
    title: {
      display: true,
      text: 'Line Chart',
    },
  },
  scales: {
    x: {
      display: true,
    },
    y: {
      display: true,
      beginAtZero: true,
    },
  },
};

const LineChart: React.FC<LineChartProps> = ({
  data,
  options = defaultOptions,
  loading = false,
  error = null,
  height = '400px',
  width = '100%',
}) => {
  // Fallback data for error state
  const errorData = {
    labels: ['Error'],
    datasets: [
      {
        label: 'No data available',
        data: [0],
        borderColor: 'rgba(255, 99, 132, 1)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
      },
    ],
  };

  if (loading) {
    return (
      <div
        style={{
          height,
          width,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <p>Loading chart...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div
        style={{
          height,
          width,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          padding: '20px',
          color: '#d32f2f',
          backgroundColor: '#ffebee',
          border: '1px solid #ffcdd2',
          borderRadius: '8px',
        }}
      >
        <p>
          <strong>Error loading chart:</strong> {error}
        </p>
      </div>
    );
  }

  // Ensure we have valid data
  if (!data || !data.labels || !data.datasets || data.labels.length === 0) {
    return (
      <div
        style={{
          height,
          width,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          padding: '20px',
          color: '#ff9800',
          backgroundColor: '#fff3e0',
          border: '1px solid #ffe0b2',
          borderRadius: '8px',
        }}
      >
        <p>No data available to display chart.</p>
      </div>
    );
  }

  // Since we can't use charting libraries directly, render a basic SVG line chart
  const canvasWidth = 600;
  const canvasHeight = 300;
  const padding = 50;
  const chartWidth = canvasWidth - padding * 2;
  const chartHeight = canvasHeight - padding * 2;

  // Find global min/max across all datasets
  const allDataValues = data.datasets.flatMap((dataset) => dataset.data);
  const minValue = Math.min(0, ...allDataValues);
  const maxValue = Math.max(...allDataValues);
  const valueRange = maxValue - minValue || 1; // Avoid division by zero

  // Helper function to scale Y value to pixel position
  const scaleY = (value: number): number => {
    const normalized = (value - minValue) / valueRange;
    return canvasHeight - padding - normalized * chartHeight;
  };

  // Helper function to get X position for a label index
  const scaleX = (index: number): number => {
    const step = chartWidth / (data.labels.length - 1 || 1);
    return padding + index * step;
  };

  return (
    <div style={{ width, height, position: 'relative' }}>
      <svg width="100%" height="100%" viewBox={`0 0 ${canvasWidth} ${canvasHeight}`} style={{ maxWidth: '100%', maxHeight: '100%' }}>
        {/* X and Y axes */}
        <line
          x1={padding}
          y1={padding}
          x2={padding}
          y2={canvasHeight - padding}
          stroke="#ccc"
          strokeWidth="2"
        />
        <line
          x1={padding}
          y1={canvasHeight - padding}
          x2={canvasWidth - padding}
          y2={canvasHeight - padding}
          stroke="#ccc"
          strokeWidth="2"
        />

        {/* Y-axis labels */}
        {[0, 1, 2, 3, 4, 5].map((step) => {
          const yValue = minValue + (valueRange * step) / 5;
          const y = scaleY(yValue);
          return (
            <g key={step}>
              <line x1={padding - 5} y1={y} x2={padding} y2={y} stroke="#ccc" />
              <text x={padding - 10} y={y} fontSize="12" textAnchor="end" dominantBaseline="middle">
                {yValue.toFixed(2)}
              </text>
            </g>
          );
        })}

        {/* X-axis labels */}
        {data.labels.map((label, index) => {
          const x = scaleX(index);
          return (
            <text
              key={index}
              x={x}
              y={canvasHeight - padding + 20}
              fontSize="12"
              textAnchor="middle"
              dominantBaseline="hanging"
            >
              {label}
            </text>
          );
        })}

        {/* Data lines and points */}
        {data.datasets.map((dataset, datasetIndex) => {
          const color = dataset.borderColor
            ? Array.isArray(dataset.borderColor)
              ? dataset.borderColor[0]
              : dataset.borderColor
            : `hsl(${(datasetIndex * 137) % 360}, 70%, 50%)`;

          const points = dataset.data.map((value, pointIndex) => ({
            x: scaleX(pointIndex),
            y: scaleY(value),
          }));

          return (
            <g key={dataset.label}>
              {/* Line path */}
              <polyline
                fill="none"
                stroke={color}
                strokeWidth="3"
                points={points.map((p) => `${p.x},${p.y}`).join(' ')}
              />

              {/* Data points */}
              {points.map((point, idx) => (
                <circle
                  key={idx}
                  cx={point.x}
                  cy={point.y}
                  r="4"
                  fill={color}
                  stroke="white"
                  strokeWidth="2"
                />
              ))}

              {/* Dataset label near first point */}
              {points.length > 0 && (
                <text
                  x={points[0].x + 10}
                  y={points[0].y - 10}
                  fontSize="14"
                  fill={color}
                  fontWeight="bold"
                >
                  {dataset.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Chart title */}
      {options?.plugins?.title?.display && options.plugins.title.text && (
        <div
          style={{
            textAlign: 'center',
            marginTop: '10px',
            fontWeight: 'bold',
            fontSize: '16px',
          }}
        >
          {options.plugins.title.text}
        </div>
      )}
    </div>
  );
};

export default LineChart;