import React from 'react';
import { ChartData, ChartOptions } from '../../types';

interface BarChartProps {
  data: ChartData;
  options?: ChartOptions;
  loading?: boolean;
  error?: string | null;
}

const defaultOptions: ChartOptions = {
  responsive: true,
  plugins: {
    legend: {
      position: 'top' as const,
    },
    tooltip: {
      enabled: true,
    },
  },
  scales: {
    x: {
      beginAtZero: true,
    },
    y: {
      beginAtZero: true,
    },
  },
};

const BarChart: React.FC<BarChartProps> = ({
  data,
  options = defaultOptions,
  loading = false,
  error = null,
}) => {
  if (loading) {
    return <div>Loading chart...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (!data || !data.labels || !data.datasets || data.labels.length === 0) {
    return <div>No data available</div>;
  }

  const chartStyle: React.CSSProperties = {
    width: '100%',
    height: '400px',
    position: 'relative',
  };

  const maxValue = Math.max(...data.datasets.flatMap((d) => d.data));
  const barThickness = 40;

  return (
    <div style={chartStyle} aria-label="Bar chart">
      <svg width="100%" height="100%" viewBox={`0 0 ${data.labels.length * 80 + 100} 500`}>
        {/* Y-axis line */}
        <line x1="60" y1="20" x2="60" y2="460" stroke="#ccc" strokeWidth="1" />

        {/* X-axis line */}
        <line x1="60" y1="460" x2={data.labels.length * 80 + 60} y2="460" stroke="#ccc" strokeWidth="1" />

        {/* Y-axis ticks and labels */}
        {Array.from({ length: 6 }).map((_, i) => {
          const y = 460 - (i * 440) / 5;
          const value = ((maxValue / 5) * i).toFixed(0);
          return (
            <g key={`y-tick-${i}`}>
              <line x1="55" y1={y} x2="60" y2={y} stroke="#ccc" strokeWidth="1" />
              <text x="50" y={y + 4} textAnchor="end" fontSize="12" fill="#666">
                {value}
              </text>
            </g>
          );
        })}

        {/* Bars */}
        {data.labels.map((label, i) => {
          const x = 80 + i * 80;
          const dataset = data.datasets[0];
          const value = dataset.data[i];
          const height = (value / maxValue) * 440;
          const y = 460 - height;

          return (
            <g key={`bar-${i}`}>
              {/* Bar */}
              <rect
                x={x}
                y={y}
                width={barThickness}
                height={height}
                fill={dataset.backgroundColor ? (Array.isArray(dataset.backgroundColor) ? dataset.backgroundColor[i] : dataset.backgroundColor) : '#3f51b5'}
                rx="4"
                ry="4"
              />
              {/* Value label on top */}
              <text x={x + barThickness / 2} y={y - 10} textAnchor="middle" fontSize="12" fill="#333">
                {value}
              </text>
              {/* X-axis label */}
              <text x={x + barThickness / 2} y="480" textAnchor="middle" fontSize="12" fill="#333">
                {label}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'center', gap: '16px' }}>
        {data.datasets.map((dataset, i) => (
          <div key={`legend-${i}`} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <div
              style={{
                width: '16px',
                height: '16px',
                backgroundColor: dataset.backgroundColor ? (Array.isArray(dataset.backgroundColor) ? dataset.backgroundColor[0] : dataset.backgroundColor) : '#3f51b5',
                borderRadius: '3px',
              }}
            />
            <span style={{ fontSize: '14px', color: '#333' }}>{dataset.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default BarChart;