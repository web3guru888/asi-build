export interface ChartData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor?: string | string[];
    borderColor?: string | string[];
    borderWidth?: number;
  }[];
}

export interface ChartOptions {
  responsive?: boolean;
  plugins?: {
    legend?: {
      position?: 'top' | 'bottom' | 'left' | 'right' | 'chartArea';
      display?: boolean;
    };
    title?: {
      display?: boolean;
      text?: string;
    };
  };
  scales?: {
    x?: {
      title?: {
        display?: boolean;
        text?: string;
      };
    };
    y?: {
      title?: {
        display?: boolean;
        text?: string;
      };
      beginAtZero?: boolean;
    };
  };
}

export interface WidgetProps {
  title: string;
  subtitle?: string;
  isLoading?: boolean;
  error?: string | null;
}

export interface DataWidgetProps extends WidgetProps {
  data?: Record<string, unknown> | null;
}

export interface StatWidgetProps extends WidgetProps {
  value: string | number;
  change?: number;
  changeType?: 'increase' | 'decrease';
}

export type FetchType = 'json' | 'text' | 'blob' | 'arrayBuffer';

export interface FetchConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  headers?: Record<string, string>;
  body?: BodyInit | null;
}

export interface FetchResponse<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface ChartTypeProps {
  data: ChartData;
  options?: ChartOptions;
  width?: string;
  height?: string;
}

export interface FilterBarProps {
  filters: Record<string, string | number | null>;
  onFilterChange: (filters: Record<string, string | number | null>) => void;
  availableFilters?: string[];
}