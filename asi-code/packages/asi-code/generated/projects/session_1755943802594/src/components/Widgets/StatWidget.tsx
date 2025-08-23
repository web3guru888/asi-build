import React from 'react';
import { Card } from '../UI/Card';
import { ChartData } from '../../types';
import BarChart from '../Charts/BarChart';
import LineChart from '../Charts/LineChart';
import PieChart from '../Charts/PieChart';
import ChartContainer from '../Charts/ChartContainer';
import LoadingSpinner from '../UI/LoadingSpinner';
import { useFetchData } from '../../hooks/useFetchData';

interface StatWidgetProps {
  title: string;
  type: 'bar' | 'line' | 'pie';
  endpoint: string;
  className?: string;
}

/**
 * StatWidget displays a chart with a title and loading/error states.
 * It fetches data from the provided endpoint and renders the appropriate chart type.
 */
const StatWidget: React.FC<StatWidgetProps> = ({ title, type, endpoint, className = '' }) => {
  const { data, loading, error } = useFetchData<ChartData>(endpoint);

  // Render loading state
  if (loading) {
    return (
      <Card className={className}>
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="flex justify-center items-center h-64">
          <LoadingSpinner />
        </div>
      </Card>
    );
  }

  // Render error state
  if (error) {
    return (
      <Card className={className}>
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <div className="text-red-500 text-sm p-4">Error loading data: {error.message}</div>
      </Card>
    );
  }

  // Render chart when data is available
  if (data) {
    return (
      <Card className={className}>
        <h3 className="text-lg font-semibold mb-4">{title}</h3>
        <ChartContainer>
          {type === 'bar' && <BarChart data={data} />}
          {type === 'line' && <LineChart data={data} />}
          {type === 'pie' && <PieChart data={data} />}
        </ChartContainer>
      </Card>
    );
  }

  // Fallback if no data, loading, or error (should not happen due to state handling above)
  return null;
};

export default StatWidget;