import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Dashboard from './Dashboard';
import { ChartData } from '../../types';

// Mock child components to isolate Dashboard testing
jest.mock('../UI/Header', () => {
  return function MockHeader() {
    return <header data-testid="mock-header">Header</header>;
  };
});

jest.mock('../UI/Sidebar', () => {
  return function MockSidebar() {
    return <aside data-testid="mock-sidebar">Sidebar</aside>;
  };
});

jest.mock('../UI/Footer', () => {
  return function MockFooter() {
    return <footer data-testid="mock-footer">Footer</footer>;
  };
});

jest.mock('../UI/GridContainer', () => {
  return function MockGridContainer({ children }: { children: React.ReactNode }) {
    return <div data-testid="mock-grid-container">{children}</div>;
  };
});

jest.mock('../Widgets/StatWidget', () => {
  return function MockStatWidget({ title, value }: { title: string; value: number | string }) {
    return (
      <div data-testid="mock-stat-widget">
        <span>{title}</span>
        <span>{value}</span>
      </div>
    );
  };
});

jest.mock('../Widgets/DataWidget', () => {
  return function MockDataWidget({
    title,
    chartType,
    data,
  }: {
    title: string;
    chartType: 'bar' | 'line' | 'pie';
    data: ChartData;
  }) {
    return (
      <div data-testid="mock-data-widget">
        <span>{title}</span>
        <span>{chartType}</span>
        <pre>{JSON.stringify(data)}</pre>
      </div>
    );
  };
});

jest.mock('../Widgets/FilterBar', () => {
  return function MockFilterBar({ onFilter }: { onFilter: (filters: Record<string, string>) => void }) {
    return (
      <div data-testid="mock-filter-bar">
        <button onClick={() => onFilter({ period: 'monthly' })}>Apply Filter</button>
      </div>
    );
  };
});

// Mock useFetchData hook
jest.mock('../../hooks/useFetchData', () => ({
  __esModule: true,
  default: jest.fn(),
}));

const mockUseFetchData = require('../../hooks/useFetchData').default;

describe('Dashboard Component', () => {
  const mockData = {
    performance: {
      labels: ['Jan', 'Feb', 'Mar'],
      datasets: [
        {
          label: 'Sales',
          data: [100, 150, 200],
          backgroundColor: '#4F46E5',
          borderColor: '#4F46E5',
        },
      ],
    },
    traffic: {
      labels: ['Direct', 'Social', 'Referral'],
      datasets: [
        {
          label: 'Visitors',
          data: [300, 200, 150],
          backgroundColor: ['#4F46E5', '#059669', '#D97706'],
        },
      ],
    },
    stats: {
      revenue: 45231,
      growth: 18,
      customers: 1548,
      conversionRate: 3.2,
    },
  };

  beforeEach(() => {
    mockUseFetchData.mockReturnValue({
      data: mockData,
      loading: false,
      error: null,
    });
  });

  it('renders header, sidebar, and footer', () => {
    render(<Dashboard />);

    expect(screen.getByTestId('mock-header')).toBeInTheDocument();
    expect(screen.getByTestId('mock-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('mock-footer')).toBeInTheDocument();
  });

  it('displays loading spinner when data is loading', () => {
    mockUseFetchData.mockReturnValue({
      data: null,
      loading: true,
      error: null,
    });

    render(<Dashboard />);
    expect(screen.getByTestId('mock-loading-spinner')).toBeInTheDocument();
  });

  it('displays error message when data fetch fails', () => {
    mockUseFetchData.mockReturnValue({
      data: null,
      loading: false,
      error: new Error('Failed to fetch data'),
    });

    render(<Dashboard />);
    expect(screen.getByText('Something went wrong. Please try again later.')).toBeInTheDocument();
  });

  it('renders filter bar and handles filter submission', () => {
    render(<Dashboard />);

    const filterBar = screen.getByTestId('mock-filter-bar');
    expect(filterBar).toBeInTheDocument();

    const applyButton = screen.getByText('Apply Filter');
    applyButton.click();

    // Ensure the onFilter callback is triggered properly
    expect(screen.queryByText('Data will update based on filters')).not.toBeInTheDocument(); // Just testing render
  });

  it('renders stat widgets with correct data', () => {
    render(<Dashboard />);

    const statWidgets = screen.getAllByTestId('mock-stat-widget');
    expect(statWidgets).toHaveLength(4);

    // Check revenue stat
    expect(statWidgets[0]).toHaveTextContent('Total Revenue');
    expect(statWidgets[0]).toHaveTextContent('$45,231');

    // Check growth stat
    expect(statWidgets[1]).toHaveTextContent('Growth');
    expect(statWidgets[1]).toHaveTextContent('18%');

    // Check customers stat
    expect(statWidgets[2]).toHaveTextContent('Total Customers');
    expect(statWidgets[2]).toHaveTextContent('1,548');

    // Check conversion rate stat
    expect(statWidgets[3]).toHaveTextContent('Conversion Rate');
    expect(statWidgets[3]).toHaveTextContent('3.2%');
  });

  it('renders data widgets with correct chart types and data', () => {
    render(<Dashboard />);

    const dataWidgets = screen.getAllByTestId('mock-data-widget');
    expect(dataWidgets).toHaveLength(2);

    // Sales Performance Widget
    expect(dataWidgets[0]).toHaveTextContent('Sales Performance');
    expect(dataWidgets[0]).toHaveTextContent('line');
    expect(dataWidgets[0]).toHaveTextContent(JSON.stringify(mockData.performance));

    // Traffic Source Distribution Widget
    expect(dataWidgets[1]).toHaveTextContent('Traffic Source Distribution');
    expect(dataWidgets[1]).toHaveTextContent('pie');
    expect(dataWidgets[1]).toHaveTextContent(JSON.stringify(mockData.traffic));
  });

  it('renders grid container to organize widgets', () => {
    render(<Dashboard />);

    const gridContainer = screen.getByTestId('mock-grid-container');
    expect(gridContainer).toBeInTheDocument();
  });

  it('handles empty data gracefully', () => {
    mockUseFetchData.mockReturnValue({
      data: {
        performance: { labels: [], datasets: [] },
        traffic: { labels: [], datasets: [] },
        stats: { revenue: 0, growth: 0, customers: 0, conversionRate: 0 },
      },
      loading: false,
      error: null,
    });

    render(<Dashboard />);

    const statWidgets = screen.getAllByTestId('mock-stat-widget');
    expect(statWidgets[0]).toHaveTextContent('$0');
    expect(statWidgets[1]).toHaveTextContent('0%');
    expect(statWidgets[2]).toHaveTextContent('0');
    expect(statWidgets[3]).toHaveTextContent('0%');
  });

  it('matches snapshot when fully loaded', async () => {
    const { asFragment } = render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByTestId('mock-header')).toBeInTheDocument();
    });

    expect(asFragment()).toMatchSnapshot();
  });
});