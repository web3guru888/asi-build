import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ChartContainer from './ChartContainer';
import { ChartData } from '../../types';

const mockChartData: ChartData = {
  labels: ['January', 'February', 'March'],
  datasets: [
    {
      label: 'Sales',
      data: [65, 59, 80],
      backgroundColor: '#4e73df',
      borderColor: '#4e73df',
      borderWidth: 1,
    },
  ],
};

describe('ChartContainer', () => {
  const defaultProps = {
    title: 'Test Chart',
    chartType: 'bar' as const,
    data: mockChartData,
    loading: false,
    error: null,
  };

  test('renders title correctly', () => {
    render(<ChartContainer {...defaultProps} />);
    expect(screen.getByText('Test Chart')).toBeInTheDocument();
  });

  test('displays loading spinner when loading is true', () => {
    render(<ChartContainer {...defaultProps} loading={true} />);
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveClass('animate-spin');
  });

  test('displays error message when error is present', () => {
    const errorMessage = 'Failed to load chart data';
    render(<ChartContainer {...defaultProps} error={errorMessage} />);
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
  });

  test('renders BarChart component when chartType is bar', () => {
    render(<ChartContainer {...defaultProps} chartType="bar" />);
    expect(screen.getByLabelText('Bar Chart')).toBeInTheDocument();
  });

  test('renders LineChart component when chartType is line', () => {
    render(<ChartContainer {...defaultProps} chartType="line" />);
    expect(screen.getByLabelText('Line Chart')).toBeInTheDocument();
  });

  test('renders PieChart component when chartType is pie', () => {
    render(<ChartContainer {...defaultProps} chartType="pie" />);
    expect(screen.getByLabelText('Pie Chart')).toBeInTheDocument();
  });

  test('passes chart data and options to the chart component', () => {
    const options = { responsive: true, maintainAspectRatio: false };
    render(
      <ChartContainer
        {...defaultProps}
        chartType="bar"
        options={options}
        data={mockChartData}
      />
    );
    // Since we can't directly inspect props, verify that chart rendered without errors
    expect(screen.getByLabelText('Bar Chart')).toBeInTheDocument();
  });

  test('handles empty data gracefully', () => {
    const emptyData: ChartData = {
      labels: [],
      datasets: [{ label: 'Empty', data: [] }],
    };
    render(<ChartContainer {...defaultProps} data={emptyData} />);
    expect(screen.getByLabelText('Bar Chart')).toBeInTheDocument();
  });

  test('applies custom className when provided', () => {
    render(<ChartContainer {...defaultProps} className="custom-chart-class" />);
    const container = screen.getByTestId('chart-container');
    expect(container).toHaveClass('custom-chart-class');
  });

  test('shows chart component when not loading and no error', () => {
    render(<ChartContainer {...defaultProps} />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.queryByText('Error')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Bar Chart')).toBeInTheDocument();
  });

  test('hides chart when loading', () => {
    render(<ChartContainer {...defaultProps} loading={true} />);
    expect(screen.queryByLabelText('Bar Chart')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  test('hides chart when there is an error', () => {
    render(<ChartContainer {...defaultProps} error="Data fetch failed" />);
    expect(screen.queryByLabelText('Bar Chart')).not.toBeInTheDocument();
    expect(screen.getByText('Data fetch failed')).toBeInTheDocument();
  });

  test('renders with height and width props', () => {
    render(
      <ChartContainer
        {...defaultProps}
        height="400px"
        width="600px"
      />
    );
    const container = screen.getByTestId('chart-container');
    expect(container).toHaveStyle({
      height: '400px',
      width: '600px',
    });
  });

  test('defaults to responsive container when no dimensions provided', () => {
    render(<ChartContainer {...defaultProps} />);
    const container = screen.getByTestId('chart-container');
    expect(container).toHaveStyle({
      height: '100%',
      width: '100%',
    });
  });
});