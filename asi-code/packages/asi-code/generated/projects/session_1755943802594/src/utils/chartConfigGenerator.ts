import { ChartData, ChartOptions } from '../types';

/**
 * Generates chart configuration based on input data and chart type
 * @param chartType - The type of chart to generate configuration for
 * @param data - The data to be used in the chart
 * @param options - Optional custom chart options to override defaults
 * @returns Complete chart configuration including data and options
 */
export const generateChartConfig = <T extends 'bar' | 'line' | 'pie'>(
  chartType: T,
  data: {
    labels: string[];
    values: number[] | number[][];
    datasetLabels?: string[];
    backgroundColors?: string[] | string;
    borderColors?: string[] | string;
  },
  options?: ChartOptions
): { type: T; data: ChartData; options: ChartOptions } => {
  // Validate input data
  if (!data.labels || !data.values) {
    throw new Error('Chart data must include labels and values');
  }

  if (data.labels.length === 0) {
    throw new Error('Labels array cannot be empty');
  }

  // Handle single dataset (common for line and bar charts with one series)
  const isSingleDataset = Array.isArray(data.values) && typeof data.values[0] === 'number';
  
  const chartData: ChartData = {
    labels: data.labels,
    datasets: isSingleDataset
      ? [
          {
            label: data.datasetLabels?.[0] || 'Dataset 1',
            data: data.values as number[],
            backgroundColor: data.backgroundColors || getDefaultBackgroundColor(chartType),
            borderColor: data.borderColors || getDefaultBorderColor(chartType),
            borderWidth: 1,
          },
        ]
      : (data.values as number[][]).map((valueSet, index) => ({
          label: data.datasetLabels?.[index] || `Dataset ${index + 1}`,
          data: valueSet,
          backgroundColor:
            Array.isArray(data.backgroundColors) && data.backgroundColors[index]
              ? data.backgroundColors[index]
              : getDefaultBackgroundColor(chartType, index),
          borderColor:
            Array.isArray(data.borderColors) && data.borderColors[index]
              ? data.borderColors[index]
              : getDefaultBorderColor(chartType, index),
          borderWidth: 1,
        })),
  };

  // Default options based on chart type
  const defaultOptions: ChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
      },
      tooltip: {
        enabled: true,
      },
    },
    scales:
      chartType === 'bar' || chartType === 'line'
        ? {
            x: {
              beginAtZero: false,
              grid: {
                display: true,
              },
            },
            y: {
              beginAtZero: true,
              grid: {
                display: true,
              },
            },
          }
        : undefined,
  };

  // For pie charts, remove scale options since they're not applicable
  if (chartType === 'pie') {
    delete (defaultOptions as any).scales;
  }

  // Merge user-provided options with defaults
  const mergedOptions = mergeOptions(defaultOptions, options);

  return {
    type: chartType,
    data: chartData,
    options: mergedOptions,
  };
};

/**
 * Merges user-provided options with default options recursively
 * @param defaults - Default options
 * @param userOptions - User-provided options to override defaults
 * @returns Merged options object
 */
const mergeOptions = (defaults: ChartOptions, userOptions?: ChartOptions): ChartOptions => {
  if (!userOptions) return defaults;

  return {
    ...defaults,
    ...userOptions,
    plugins: {
      ...(defaults.plugins || {}),
      ...(userOptions.plugins || {}),
    },
    scales: userOptions.scales
      ? {
          ...(defaults.scales || {}),
          ...userOptions.scales,
          x: userOptions.scales.x
            ? { ...(defaults.scales?.x || {}), ...userOptions.scales.x }
            : defaults.scales?.x,
          y: userOptions.scales.y
            ? { ...(defaults.scales?.y || {}), ...userOptions.scales.y }
            : defaults.scales?.y,
        }
      : defaults.scales,
  };
};

/**
 * Gets default background color based on chart type and dataset index
 * @param chartType - Type of chart
 * @param index - Dataset index for multi-dataset charts
 * @returns Default background color(s)
 */
const getDefaultBackgroundColor = (chartType: string, index = 0): string | string[] => {
  const colors = [
    'rgba(54, 162, 235, 0.6)', // blue
    'rgba(255, 99, 132, 0.6)', // red
    'rgba(75, 192, 192, 0.6)', // green
    'rgba(255, 205, 86, 0.6)', // yellow
    'rgba(153, 102, 255, 0.6)', // purple
    'rgba(255, 159, 64, 0.6)', // orange
  ];

  if (chartType === 'pie') {
    return colors;
  }

  return colors[index % colors.length];
};

/**
 * Gets default border color based on chart type and dataset index
 * @param chartType - Type of chart
 * @param index - Dataset index for multi-dataset charts
 * @returns Default border color(s)
 */
const getDefaultBorderColor = (chartType: string, index = 0): string | string[] => {
  const colors = [
    'rgba(54, 162, 235, 1)', // blue
    'rgba(255, 99, 132, 1)', // red
    'rgba(75, 192, 192, 1)', // green
    'rgba(255, 205, 86, 1)', // yellow
    'rgba(153, 102, 255, 1)', // purple
    'rgba(255, 159, 64, 1)', // orange
  ];

  if (chartType === 'pie') {
    return colors.map(color => color.replace('1)', '0.8)'));
  }

  return colors[index % colors.length];
};