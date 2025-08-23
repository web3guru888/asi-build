export interface Point {
  x: number;
  y: number;
}

export interface Dimensions {
  width: number;
  height: number;
}

export interface Margin {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export interface DataSeries {
  label?: string;
  data: Point[];
  color?: string;
}

export type ChartType = 'line' | 'bar' | 'scatter' | 'area';

export interface ChartConfig {
  container: HTMLElement | string;
  width?: number;
  height?: number;
  margin?: Margin;
  xAxisLabel?: string;
  yAxisLabel?: string;
  title?: string;
  type: ChartType;
  series: DataSeries[];
}

export interface RenderContext {
  svg: SVGSVGElement;
  plotArea: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

export type RenderFunction = (config: ChartConfig, ctx: RenderContext) => void;

export interface AxisScale {
  x: (value: number) => number;
  y: (value: number) => number;
}

export interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}