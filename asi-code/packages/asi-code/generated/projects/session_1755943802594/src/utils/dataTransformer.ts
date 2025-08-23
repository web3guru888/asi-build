import { ChartData, ChartOptions } from '../types';

/**
 * Transforms raw data into chart-compatible format
 * @param rawData - The raw data to transform
 * @param config - Transformation configuration
 * @returns ChartData object compatible with charting libraries
 */
export const transformToChartData = <T>(
  rawData: T[],
  config: {
    labelKey: keyof T;
    valueKeys: (keyof T)[];
    labels?: string[];
    colors?: string[];
  }
): ChartData => {
  if (!rawData || rawData.length === 0) {
    return {
      labels: [],
      datasets: [],
    };
  }

  const { labelKey, valueKeys, labels, colors } = config;

  // Extract labels from data or use provided labels
  const chartLabels = labels || rawData.map((item) => String(item[labelKey]));

  // Generate datasets for each value key
  const datasets = valueKeys.map((valueKey, index) => {
    const data = rawData.map((item) => Number(item[valueKey]));

    return {
      label: String(valueKey),
      data,
      backgroundColor: colors
        ? typeof colors === 'string'
          ? colors
          : colors[index % colors.length]
        : `hsl(${(index * 137) % 360}, 70%, 50%)`,
      borderColor: 'rgba(0, 0, 0, 0.1)',
      borderWidth: 1,
    };
  });

  return {
    labels: chartLabels,
    datasets,
  };
};

/**
 * Transforms raw data into key-value pairs for stat widgets
 * @param rawData - The raw data to transform
 * @param mapping - Key-value mapping configuration
 * @returns Object with transformed key-value pairs
 */
export const transformToKeyValue = <T>(
  rawData: T[],
  mapping: {
    key: keyof T;
    value: keyof T;
  }
): Record<string, number> => {
  if (!rawData || rawData.length === 0) {
    return {};
  }

  const { key, value } = mapping;
  return rawData.reduce((acc, item) => {
    const itemKey = String(item[key]);
    const itemValue = Number(item[value]);
    acc[itemKey] = itemValue;
    return acc;
  }, {} as Record<string, number>);
};

/**
 * Normalizes data for consistent chart rendering
 * @param data - Chart data to normalize
 * @returns Normalized chart data
 */
export const normalizeChartData = (
  data: ChartData
): ChartData => {
  if (!data?.datasets) {
    return { labels: [], datasets: [] };
  }

  const maxDataLength = Math.max(...data.datasets.map(d => d.data.length), data.labels.length);
  
  // Ensure all datasets have the same length as labels
  const normalizedDatasets = data.datasets.map(dataset => {
    const paddedData = [...dataset.data];
    while (paddedData.length < maxDataLength) {
      paddedData.push(0);
    }
    return {
      ...dataset,
      data: paddedData.slice(0, maxDataLength)
    };
  });

  // Ensure labels array matches the data length
  const normalizedLabels = [...data.labels];
  while (normalizedLabels.length < maxDataLength) {
    normalizedLabels.push('');
  }

  return {
    labels: normalizedLabels.slice(0, maxDataLength),
    datasets: normalizedDatasets
  };
};

/**
 * Generates default chart options
 * @param title - Chart title
 * @param responsive - Whether chart should be responsive
 * @returns ChartOptions object
 */
export const getDefaultChartOptions = (
  title?: string,
  responsive = true
): ChartOptions => {
  return {
    responsive,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: !!title,
        text: title || '',
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
};