import React from 'react';
import { ChartData, ChartOptions } from '../../types';
import ChartContainer from '../Charts/ChartContainer';
import LoadingSpinner from '../UI/LoadingSpinner';
import Card from '../UI/Card';

interface DataWidgetProps {
  title: string;
  chartType: 'bar' | 'line' | 'pie';
  data: ChartData | null;
  options?: ChartOptions;
  isLoading?: boolean;
  error?: string | null;
  className?: string;
}

const DataWidget: React.FC<DataWidgetProps> = ({
  title,
  chartType,
  data,
  options = {},
  isLoading = false,
  error = null,
  className = '',
}) => {
  if (isLoading) {
    return (
      <Card className={className}>
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="text-red-500 text-center py-4">
          <p>Error loading data: {error}</p>
        </div>
      </Card>
    );
  }

  if (!data || !data.labels || !data.datasets || data.datasets.length === 0) {
    return (
      <Card className={className}>
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="text-gray-500 text-center py-4">
          <p>No data available</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <ChartContainer type={chartType} data={data} options={options} />
    </Card>
  );
};

export default DataWidget;