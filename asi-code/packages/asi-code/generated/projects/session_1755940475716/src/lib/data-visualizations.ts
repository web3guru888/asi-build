import { VisualizationConfig, Point, Dimensions } from './types';
import { SVGRenderer } from './svg-renderer';

/**
 * DataVisualizations class
 * Provides high-level methods to create common SVG-based data visualizations
 * such as line charts, bar charts, and scatter plots.
 */
export class DataVisualizations {
  private renderer: SVGRenderer;
  private config: VisualizationConfig;

  /**
   * Creates an instance of DataVisualizations
   * @param containerId - The ID of the DOM element where the visualization will be rendered
   * @param config - Configuration options for the visualization
   */
  constructor(containerId: string, config: VisualizationConfig) {
    if (!containerId) {
      throw new Error('Container ID is required to initialize DataVisualizations');
    }

    this.config = {
      width: 600,
      height: 400,
      margin: { top: 20, right: 20, bottom: 30, left: 40 },
      xAxisLabel: '',
      yAxisLabel: '',
      title: '',
      ...config,
    };

    this.renderer = new SVGRenderer(containerId, this.config.width, this.config.height);
  }

  /**
   * Renders a line chart based on the provided data points
   * @param data - Array of { x, y } points to plot
   */
  renderLineChart(data: Point[]): void {
    if (!data || data.length === 0) {
      console.warn('No data provided to renderLineChart');
      return;
    }

    try {
      const { margin } = this.config;
      const chartWidth = this.config.width - margin.left - margin.right;
      const chartHeight = this.config.height - margin.top - margin.bottom;

      // Clear previous content
      this.renderer.clear();

      // Create group for chart elements
      const g = this.renderer.createGroup(margin.left, margin.top);

      // Determine scales
      const xExtent = this.getExtent(data, 'x');
      const yExtent = this.getExtent(data, 'y');

      const xScale = (value: number) =>
        ((value - xExtent.min) / (xExtent.max - xExtent.min)) * chartWidth;
      const yScale = (value: number) =>
        chartHeight - ((value - yExtent.min) / (yExtent.max - yExtent.min)) * chartHeight;

      // Create path data
      const pathData = data
        .map((point, i) => {
          const x = xScale(point.x);
          const y = yScale(point.y);
          return `${i === 0 ? 'M' : 'L'} ${x},${y}`;
        })
        .join(' ');

      // Draw line
      const path = this.renderer.createPath(pathData);
      this.renderer.setStyle(path, 'fill', 'none');
      this.renderer.setStyle(path, 'stroke', this.config.lineColor || '#4c84ff');
      this.renderer.setStyle(path, 'stroke-width', '2px');
      g.appendChild(path);

      // Draw markers
      data.forEach((point) => {
        const x = xScale(point.x);
        const y = yScale(point.y);
        const circle = this.renderer.createCircle(x, y, 4);
        this.renderer.setStyle(circle, 'fill', '#4c84ff');
        this.renderer.setStyle(circle, 'stroke', '#fff');
        this.renderer.setStyle(circle, 'stroke-width', '2px');
        g.appendChild(circle);
      });

      // Draw X and Y axis lines
      const xAxisLine = this.renderer.createLine(0, chartHeight, chartWidth, chartHeight);
      this.renderer.setStyle(xAxisLine, 'stroke', '#ccc');
      g.appendChild(xAxisLine);

      const yAxisLine = this.renderer.createLine(0, 0, 0, chartHeight);
      this.renderer.setStyle(yAxisLine, 'stroke', '#ccc');
      g.appendChild(yAxisLine);

      // Add X and Y axis labels if provided
      if (this.config.xAxisLabel) {
        const xAxisText = this.renderer.createText(
          chartWidth / 2,
          chartHeight + margin.bottom - 5,
          this.config.xAxisLabel
        );
        this.renderer.setStyle(xAxisText, 'text-anchor', 'middle');
        this.renderer.setStyle(xAxisText, 'font-size', '12px');
        this.renderer.setStyle(xAxisText, 'fill', '#333');
        g.appendChild(xAxisText);
      }

      if (this.config.yAxisLabel) {
        const yAxisText = this.renderer.createText(
          -chartHeight / 2,
          -margin.left + 10,
          this.config.yAxisLabel
        );
        this.renderer.setStyle(yAxisText, 'text-anchor', 'middle');
        this.renderer.setStyle(yAxisText, 'font-size', '12px');
        this.renderer.setStyle(yAxisText, 'fill', '#333');
        this.renderer.rotateElement(yAxisText, -90);
        g.appendChild(yAxisText);
      }

      // Add title if provided
      if (this.config.title) {
        const title = this.renderer.createText(
          chartWidth / 2,
          -margin.top / 2,
          this.config.title
        );
        this.renderer.setStyle(title, 'text-anchor', 'middle');
        this.renderer.setStyle(title, 'font-size', '16px');
        this.renderer.setStyle(title, 'font-weight', 'bold');
        this.renderer.setStyle(title, 'fill', '#333');
        g.appendChild(title);
      }
    } catch (error) {
      console.error('Error rendering line chart:', error);
      throw error;
    }
  }

  /**
   * Renders a bar chart based on the provided data points
   * @param data - Array of { x, y } points to represent as bars
   */
  renderBarChart(data: Point[]): void {
    if (!data || data.length === 0) {
      console.warn('No data provided to renderBarChart');
      return;
    }

    try {
      const { margin } = this.config;
      const chartWidth = this.config.width - margin.left - margin.right;
      const chartHeight = this.config.height - margin.top - margin.bottom;

      // Clear previous content
      this.renderer.clear();

      // Create group for chart elements
      const g = this.renderer.createGroup(margin.left, margin.top);

      // Determine scales
      const xExtent = this.getExtent(data, 'x');
      const yExtent = this.getExtent(data, 'y');

      const xScale = (value: number) =>
        ((value - xExtent.min) / (xExtent.max - xExtent.min)) * chartWidth;
      const yScale = (value: number) =>
        chartHeight - ((value - yExtent.min) / (yExtent.max - yExtent.min)) * chartHeight;

      // Bar width based on spacing
      const barWidth = chartWidth / data.length - 10;

      // Draw bars
      data.forEach((point, i) => {
        const x = xScale(point.x);
        const y = yScale(point.y);
        const height = chartHeight - y;

        const rect = this.renderer.createRectangle(x, y, barWidth, height);
        this.renderer.setStyle(rect, 'fill', this.config.barColor || '#4c84ff');
        this.renderer.setStyle(rect, 'stroke', '#333');
        this.renderer.setStyle(rect, 'stroke-width', '1px');
        g.appendChild(rect);
      });

      // Draw X and Y axis lines
      const xAxisLine = this.renderer.createLine(0, chartHeight, chartWidth, chartHeight);
      this.renderer.setStyle(xAxisLine, 'stroke', '#ccc');
      g.appendChild(xAxisLine);

      const yAxisLine = this.renderer.createLine(0, 0, 0, chartHeight);
      this.renderer.setStyle(yAxisLine, 'stroke', '#ccc');
      g.appendChild(yAxisLine);

      // Add X and Y axis labels if provided
      if (this.config.xAxisLabel) {
        const xAxisText = this.renderer.createText(
          chartWidth / 2,
          chartHeight + margin.bottom - 5,
          this.config.xAxisLabel
        );
        this.renderer.setStyle(xAxisText, 'text-anchor', 'middle');
        this.renderer.setStyle(xAxisText, 'font-size', '12px');
        this.renderer.setStyle(xAxisText, 'fill', '#333');
        g.appendChild(xAxisText);
      }

      if (this.config.yAxisLabel) {
        const yAxisText = this.renderer.createText(
          -chartHeight / 2,
          -margin.left + 10,
          this.config.yAxisLabel
        );
        this.renderer.setStyle(yAxisText, 'text-anchor', 'middle');
        this.renderer.setStyle(yAxisText, 'font-size', '12px');
        this.renderer.setStyle(yAxisText, 'fill', '#333');
        this.renderer.rotateElement(yAxisText, -90);
        g.appendChild(yAxisText);
      }

      // Add title if provided
      if (this.config.title) {
        const title = this.renderer.createText(
          chartWidth / 2,
          -margin.top / 2,
          this.config.title
        );
        this.renderer.setStyle(title, 'text-anchor', 'middle');
        this.renderer.setStyle(title, 'font-size', '16px');
        this.renderer.setStyle(title, 'font-weight', 'bold');
        this.renderer.setStyle(title, 'fill', '#333');
        g.appendChild(title);
      }
    } catch (error) {
      console.error('Error rendering bar chart:', error);
      throw error;
    }
  }

  /**
   * Renders a scatter plot based on the provided data points
   * @param data - Array of { x, y } points to plot as dots
   */
  renderScatterPlot(data: Point[]): void {
    if (!data || data.length === 0) {
      console.warn('No data provided to renderScatterPlot');
      return;
    }

    try {
      const { margin } = this.config;
      const chartWidth = this.config.width - margin.left - margin.right;
      const chartHeight = this.config.height - margin.top - margin.bottom;

      // Clear previous content
      this.renderer.clear();

      // Create group for chart elements
      const g = this.renderer.createGroup(margin.left, margin.top);

      // Determine scales
      const xExtent = this.getExtent(data, 'x');
      const yExtent = this.getExtent(data, 'y');

      const xScale = (value: number) =>
        ((value - xExtent.min) / (xExtent.max - xExtent.min)) * chartWidth;
      const yScale = (value: number) =>
        chartHeight - ((value - yExtent.min) / (yExtent.max - yExtent.min)) * chartHeight;

      // Draw points
      data.forEach((point) => {
        const x = xScale(point.x);
        const y = yScale(point.y);
        const circle = this.renderer.createCircle(x, y, 5);
        this.renderer.setStyle(circle, 'fill', this.config.pointColor || '#ff5722');
        this.renderer.setStyle(circle, 'stroke', '#fff');
        this.renderer.setStyle(circle, 'stroke-width', '1.5px');
        g.appendChild(circle);
      });

      // Draw X and Y axis lines
      const xAxisLine = this.renderer.createLine(0, chartHeight, chartWidth, chartHeight);
      this.renderer.setStyle(xAxisLine, 'stroke', '#ccc');
      g.appendChild(xAxisLine);

      const yAxisLine = this.renderer.createLine(0, 0, 0, chartHeight);
      this.renderer.setStyle(yAxisLine, 'stroke', '#ccc');
      g.appendChild(yAxisLine);

      // Add X and Y axis labels if provided
      if (this.config.xAxisLabel) {
        const xAxisText = this.renderer.createText(
          chartWidth / 2,
          chartHeight + margin.bottom - 5,
          this.config.xAxisLabel
        );
        this.renderer.setStyle(xAxisText, 'text-anchor', 'middle');
        this.renderer.setStyle(xAxisText, 'font-size', '12px');
        this.renderer.setStyle(xAxisText, 'fill', '#333');
        g.appendChild(xAxisText);
      }

      if (this.config.yAxisLabel) {
        const yAxisText = this.renderer.createText(
          -chartHeight / 2,
          -margin.left + 10,
          this.config.yAxisLabel
        );
        this.renderer.setStyle(yAxisText, 'text-anchor', 'middle');
        this.renderer.setStyle(yAxisText, 'font-size', '12px');
        this.renderer.setStyle(yAxisText, 'fill', '#333');
        this.renderer.rotateElement(yAxisText, -90);
        g.appendChild(yAxisText);
      }

      // Add title if provided
      if (this.config.title) {
        const title = this.renderer.createText(
          chartWidth / 2,
          -margin.top / 2,
          this.config.title
        );
        this.renderer.setStyle(title, 'text-anchor', 'middle');
        this.renderer.setStyle(title, 'font-size', '16px');
        this.renderer.setStyle(title, 'font-weight', 'bold');
        this.renderer.setStyle(title, 'fill', '#333');
        g.appendChild(title);
      }
    } catch (error) {
      console.error('Error rendering scatter plot:', error);
      throw error;
    }
  }

  /**
   * Utility method to get min and max values of a property in data array
   * @param data - Array of data points
   * @param key - Property key to analyze ('x' or 'y')
   * @returns Object containing min and max values
   */
  private getExtent(data: Point[], key: 'x' | 'y'): { min: number; max: number } {
    return data.reduce(
      (acc, point) => {
        const value = point[key];
        if (value < acc.min) acc.min = value;
        if (value > acc.max) acc.max = value;
        return acc;
      },
      { min: Infinity, max: -Infinity }
    );
  }

  /**
   * Updates the configuration of the visualization
   * @param newConfig - New configuration options to merge with existing config
   */
  updateConfig(newConfig: Partial<VisualizationConfig>): void {
    this.config = { ...this.config, ...newConfig };
  }

  /**
   * Returns the current configuration
   */
  getConfig(): VisualizationConfig {
    return { ...this.config };
  }

  /**
   * Destroys the visualization and cleans up resources
   */
  destroy(): void {
    this.renderer.destroy();
  }
}