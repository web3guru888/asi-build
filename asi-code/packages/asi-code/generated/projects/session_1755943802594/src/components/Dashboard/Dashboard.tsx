import React from 'react';
import { ChartData } from '../../types';
import Header from '../UI/Header';
import Sidebar from '../UI/Sidebar';
import Footer from '../UI/Footer';
import GridContainer from '../UI/GridContainer';
import Card from '../UI/Card';
import BarChart from '../Charts/BarChart';
import LineChart from '../Charts/LineChart';
import PieChart from '../Charts/PieChart';
import ChartContainer from '../Charts/ChartContainer';
import DataWidget from '../Widgets/DataWidget';
import StatWidget from '../Widgets/StatWidget';
import FilterBar from '../Widgets/FilterBar';
import LoadingSpinner from '../UI/LoadingSpinner';
import useFetchData from '../../hooks/useFetchData';

const Dashboard: React.FC = () => {
  // Mock data keys to simulate API endpoints
  const barDataKey = 'barChart';
  const lineDataKey = 'lineChart';
  const pieDataKey = 'pieChart';
  const tableDataKey = 'tableData';
  const statsKey = 'stats';

  // Custom hook for fetching multiple data sources
  const { data, loading, error, refetch } = useFetchData({
    barDataKey,
    lineDataKey,
    pieDataKey,
    tableDataKey,
    statsKey,
  });

  // Default fallback data
  const defaultBarData: ChartData = {
    labels: ['January', 'February', 'March', 'April', 'May', 'June'],
    datasets: [
      {
        label: 'Sales',
        data: [65, 59, 80, 81, 56, 55],
        backgroundColor: 'rgba(54, 162, 235, 0.6)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
      },
    ],
  };

  const defaultLineData: ChartData = {
    labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
    datasets: [
      {
        label: 'Revenue',
        data: [200, 450, 300, 600],
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.4,
        fill: true,
      },
    ],
  };

  const defaultPieData: ChartData = {
    labels: ['Direct', 'Referral', 'Social'],
    datasets: [
      {
        label: 'Traffic Source',
        data: [55, 30, 15],
        backgroundColor: [
          'rgba(255, 99, 132, 0.6)',
          'rgba(54, 162, 235, 0.6)',
          'rgba(255, 205, 86, 0.6)',
        ],
      },
    ],
  };

  const defaultStats = [
    { title: 'Total Users', value: '12,345', change: 12.5 },
    { title: 'Revenue', value: '$45,678', change: 8.3 },
    { title: 'Orders', value: '1,234', change: -2.1 },
    { title: 'Conversion Rate', value: '3.27%', change: 4.8 },
  ];

  const defaultTableData = [
    { id: 1, name: 'John Doe', email: 'john@example.com', status: 'Active', value: 2500 },
    { id: 2, name: 'Jane Smith', email: 'jane@example.com', status: 'Inactive', value: 1800 },
    { id: 3, name: 'Sam Wilson', email: 'sam@example.com', status: 'Active', value: 3100 },
  ];

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen flex-col items-center justify-center text-red-500 p-4">
        <h2 className="text-xl font-semibold">Error Loading Dashboard</h2>
        <p className="mt-2">An error occurred while fetching data: {error}</p>
        <button
          onClick={() => refetch()}
          className="mt-4 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Header */}
        <Header title="Dashboard" />

        {/* Dashboard Body */}
        <main className="flex-1 overflow-y-auto p-6">
          {/* Filters */}
          <FilterBar onFilterChange={refetch} />

          {/* Stats Widgets */}
          <GridContainer columns={4} className="mb-6">
            {data?.stats?.length
              ? data.stats.map((stat, index) => (
                  <StatWidget
                    key={index}
                    title={stat.title}
                    value={stat.value}
                    change={stat.change}
                  />
                ))
              : defaultStats.map((stat, index) => (
                  <StatWidget
                    key={index}
                    title={stat.title}
                    value={stat.value}
                    change={stat.change}
                  />
                ))}
          </GridContainer>

          {/* Charts */}
          <GridContainer columns={2} className="mb-6">
            <Card title="Sales Overview">
              <ChartContainer>
                <BarChart
                  data={data?.[barDataKey] || defaultBarData}
                  height={300}
                />
              </ChartContainer>
            </Card>

            <Card title="Revenue Trends">
              <ChartContainer>
                <LineChart
                  data={data?.[lineDataKey] || defaultLineData}
                  height={300}
                />
              </ChartContainer>
            </Card>

            <Card title="Traffic Sources">
              <ChartContainer>
                <PieChart
                  data={data?.[pieDataKey] || defaultPieData}
                  height={300}
                />
              </ChartContainer>
            </Card>

            <Card title="Recent Activity">
              <ChartContainer>
                <LineChart
                  data={data?.[lineDataKey] || defaultLineData}
                  height={300}
                />
              </ChartContainer>
            </Card>
          </GridContainer>

          {/* Data Table */}
          <Card title="Recent Orders" className="mb-6">
            <DataWidget
              data={data?.[tableDataKey] || defaultTableData}
              columns={['name', 'email', 'status', 'value']}
              onRowClick={(row) => console.log('Row clicked:', row)}
            />
          </Card>
        </main>

        {/* Footer */}
        <Footer />
      </div>
    </div>
  );
};

export default Dashboard;