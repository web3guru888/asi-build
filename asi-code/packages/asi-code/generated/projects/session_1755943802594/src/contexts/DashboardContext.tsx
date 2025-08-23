import React, { createContext, useContext, useState, useCallback, useMemo, ReactNode } from 'react';
import { ChartData, ChartType } from '../types';

interface DashboardContextType {
  chartData: ChartData | null;
  chartType: ChartType;
  loading: boolean;
  error: string | null;
  setChartData: (data: ChartData) => void;
  setChartType: (type: ChartType) => void;
  fetchData: () => Promise<void>;
  refreshData: () => void;
}

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

interface DashboardProviderProps {
  children: ReactNode;
  initialChartType?: ChartType;
}

export const DashboardProvider: React.FC<DashboardProviderProps> = ({
  children,
  initialChartType = 'bar',
}) => {
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [chartType, setChartType] = useState<ChartType>(initialChartType);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Simulate data fetching - in real app this would call an API
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Simulate API delay
      await new Promise((resolve) => setTimeout(resolve, 800));

      // Generate sample data
      const labels = ['January', 'February', 'March', 'April', 'May', 'June', 'July'];
      const data = labels.map(() => Math.floor(Math.random() * 100));

      const sampleData: ChartData = {
        labels,
        datasets: [
          {
            label: 'Sales',
            data,
            backgroundColor: [
              'rgba(255, 99, 132, 0.6)',
              'rgba(54, 162, 235, 0.6)',
              'rgba(255, 206, 86, 0.6)',
              'rgba(75, 192, 192, 0.6)',
              'rgba(153, 102, 255, 0.6)',
              'rgba(255, 159, 64, 0.6)',
              'rgba(199, 199, 199, 0.6)',
            ],
            borderColor: [
              'rgba(255, 99, 132, 1)',
              'rgba(54, 162, 235, 1)',
              'rgba(255, 206, 86, 1)',
              'rgba(75, 192, 192, 1)',
              'rgba(153, 102, 255, 1)',
              'rgba(255, 159, 64, 1)',
              'rgba(199, 199, 199, 1)',
            ],
            borderWidth: 1,
          },
        ],
      };

      setChartData(sampleData);
    } catch (err) {
      setError('Failed to fetch chart data. Please try again later.');
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshData = useCallback(() => {
    void fetchData();
  }, [fetchData]);

  // Handle setting chart data with validation
  const handleSetChartData = useCallback((data: ChartData) => {
    if (!data.labels || !data.datasets || data.labels.length === 0 || data.datasets.length === 0) {
      throw new Error('Invalid chart data: labels and datasets are required');
    }
    setChartData(data);
  }, []);

  // Handle setting chart type with validation
  const handleSetChartType = useCallback((type: ChartType) => {
    const validTypes: ChartType[] = ['bar', 'line', 'pie'];
    if (!validTypes.includes(type)) {
      throw new Error(`Invalid chart type: ${type}. Must be one of: ${validTypes.join(', ')}`);
    }
    setChartType(type);
  }, []);

  const value = useMemo(
    () => ({
      chartData,
      chartType,
      loading,
      error,
      setChartData: handleSetChartData,
      setChartType: handleSetChartType,
      fetchData,
      refreshData,
    }),
    [chartData, chartType, loading, error, handleSetChartData, handleSetChartType, fetchData, refreshData]
  );

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
};

// Custom hook to use the dashboard context
export const useDashboard = (): DashboardContextType => {
  const context = useContext(DashboardContext);
  if (context === undefined) {
    throw new Error('useDashboard must be used within a DashboardProvider');
  }
  return context;
};