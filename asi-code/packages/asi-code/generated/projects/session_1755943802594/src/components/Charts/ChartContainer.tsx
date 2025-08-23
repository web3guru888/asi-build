import React from 'react';
import { ChartData, ChartOptions } from '../../types';
import BarChart from './BarChart';
import LineChart from './LineChart';
import PieChart from './PieChart';
import LoadingSpinner from '../UI/LoadingSpinner';
import Card from '../UI/Card';

interface ChartContainerProps {
  title: string;
  chartType: 'bar' | 'line' | 'pie';
  data: ChartData;
  options?: ChartOptions;
  loading?: boolean;
  error?: string | null;
  height?: string;
  width?: string;
}

const ChartContainer: React.FC<ChartContainerProps> = ({
  title,
  chartType,
  data,
  options = {},
  loading = false,
  error = null,
  height = '400px',
  width = '100%',
}) => {
  // Render loading state
  if (loading) {
    return (
      <Card style={{ width, height, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
        <h3>{title}</h3>
        <LoadingSpinner />
      </Card>
    );
  }

  // Render error state
  if (error) {
    return (
      <Card style={{ width, height, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', color: '#d32f2f' }}>
        <h3>{title}</h3>
        <p>Error loading chart: {error}</p>
      </Card>
    );
  }

  // Validate data
  if (!data || !data.labels || !data.datasets || data.datasets.length === 0) {
    return (
      <Card style={{ width, height, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', color: '#f57c00' }}>
        <h3>{title}</h3>
        <p>No data available for the chart.</p>
      </Card>
    );
  }

  // Render the appropriate chart based on type
  const renderChart = () => {
    switch (chartType) {
      case 'bar':
        return <BarChart data={data} options={options} />;
      case 'line':
        return <LineChart data={data} options={options} />;
      case 'pie':
        return <PieChart data={data} options={options} />;
      default:
        return (
          <div style={{ color: '#f57c00', textAlign: 'center' }}>
            Unsupported chart type: {chartType}
          </div>
        );
    }
  };

  return (
    <Card style={{ width, height, display: 'flex', flexDirection: 'column' }}>
      <h3>{title}</h3>
      <div style={{ flex: 1, position: 'relative' }}>
        {renderChart()}
      </div>
    </Card>
  );
};

export default ChartContainer;