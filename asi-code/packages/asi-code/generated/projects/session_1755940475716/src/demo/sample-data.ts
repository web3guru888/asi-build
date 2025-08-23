import { Point, Dimensions } from '../lib/types/index';

/**
 * Sample dataset for demonstrating SVG graph visualizations
 * Contains multiple series with timestamps and numeric values
 */
export const timeSeriesData = [
  {
    label: 'User Growth',
    color: '#3b82f6',
    data: [
      { x: new Date('2025-01-01').getTime(), y: 120 },
      { x: new Date('2025-02-01').getTime(), y: 165 },
      { x: new Date('2025-03-01').getTime(), y: 140 },
      { x: new Date('2025-04-01').getTime(), y: 210 },
      { x: new Date('2025-05-01').getTime(), y: 250 },
      { x: new Date('2025-06-01').getTime(), y: 320 },
      { x: new Date('2025-07-01').getTime(), y: 290 },
      { x: new Date('2025-08-01').getTime(), y: 350 }
    ] as Point[]
  },
  {
    label: 'Revenue',
    color: '#10b981',
    data: [
      { x: new Date('2025-01-01').getTime(), y: 80 },
      { x: new Date('2025-02-01').getTime(), y: 110 },
      { x: new Date('2025-03-01').getTime(), y: 95 },
      { x: new Date('2025-04-01').getTime(), y: 145 },
      { x: new Date('2025-05-01').getTime(), y: 180 },
      { x: new Date('2025-06-01').getTime(), y: 225 },
      { x: new Date('2025-07-01').getTime(), y: 200 },
      { x: new Date('2025-08-01').getTime(), y: 260 }
    ] as Point[]
  },
  {
    label: 'Engagement Rate',
    color: '#f59e0b',
    data: [
      { x: new Date('2025-01-01').getTime(), y: 45 },
      { x: new Date('2025-02-01').getTime(), y: 52 },
      { x: new Date('2025-03-01').getTime(), y: 48 },
      { x: new Date('2025-04-01').getTime(), y: 62 },
      { x: new Date('2025-05-01').getTime(), y: 70 },
      { x: new Date('2025-06-01').getTime(), y: 85 },
      { x: new Date('2025-07-01').getTime(), y: 78 },
      { x: new Date('2025-08-01').getTime(), y: 92 }
    ] as Point[]
  }
];

/**
 * Sample dataset for bar chart visualization
 */
export const barChartData = {
  labels: ['Q1', 'Q2', 'Q3', 'Q4'],
  series: [
    {
      label: 'Sales',
      color: '#8b5cf6',
      data: [150, 220, 180, 260] as number[]
    },
    {
      label: 'Targets',
      color: '#6366f1',
      data: [130, 200, 200, 240] as number[]
    }
  ]
};

/**
 * Sample dataset for pie chart visualization
 */
export const pieChartData = [
  { label: 'Desktop', value: 62, color: '#06b6d4' },
  { label: 'Mobile', value: 28, color: '#f97316' },
  { label: 'Tablet', value: 10, color: '#84cc16' }
];

/**
 * Configuration for graph dimensions and margins
 */
export const graphDimensions: Dimensions = {
  width: 800,
  height: 400
};

export const defaultMargins = {
  top: 20,
  right: 30,
  bottom: 40,
  left: 60
};

/**
 * Utility function to get a sample subset of time series data
 * @param seriesCount Number of data series to include (1-3)
 * @returns Subset of time series data
 */
export const getSampleTimeSeries = (seriesCount: number = 3) => {
  if (seriesCount <= 0) {
    throw new Error('Series count must be greater than 0');
  }
  if (seriesCount > timeSeriesData.length) {
    throw new Error(`Maximum ${timeSeriesData.length} series available`);
  }
  return timeSeriesData.slice(0, seriesCount);
};

/**
 * Generates random data points for demonstration purposes
 * @param count Number of data points to generate
 * @param maxX Maximum X value
 * @param maxY Maximum Y value
 * @returns Array of random points
 */
export const generateRandomData = (
  count: number = 10,
  maxX: number = 100,
  maxY: number = 100
): Point[] => {
  if (count <= 0) {
    throw new Error('Data point count must be greater than 0');
  }
  return Array.from({ length: count }, (_, i) => ({
    x: (i / (count - 1)) * maxX,
    y: Math.random() * maxY
  }));
};