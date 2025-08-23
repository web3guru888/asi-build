import { Dimensions, Margin } from '../lib/types';
import { renderSVG, createGroup, createRect, createText } from '../lib/svg-renderer';

/**
 * Configuration options for the GraphContainer
 */
interface GraphContainerOptions {
  containerId: string;
  width?: number;
  height?: number;
  margin?: Margin;
  backgroundColor?: string;
  className?: string;
}

/**
 * Simple data point interface for graphing
 */
interface DataPoint {
  label: string;
  value: number;
  color?: string;
}

/**
 * GraphContainer class for creating SVG-based visualizations
 * Manages the SVG canvas and rendering of various graph types
 */
export class GraphContainer {
  private containerId: string;
  private dimensions: Dimensions;
  private margin: Margin;
  private backgroundColor: string;
  private svgElement: SVGElement | null = null;
  private dataPoints: DataPoint[] = [];
  private className: string;

  constructor(options: GraphContainerOptions) {
    this.containerId = options.containerId;
    this.dimensions = {
      width: options.width || 800,
      height: options.height || 600,
    };
    this.margin = options.margin || { top: 40, right: 20, bottom: 60, left: 60 };
    this.backgroundColor = options.backgroundColor || '#f9f9f9';
    this.className = options.className || 'graph-container';

    this.initializeContainer();
  }

  /**
   * Initializes the container element and creates the SVG canvas
   */
  private initializeContainer(): void {
    const container = document.getElementById(this.containerId);
    if (!container) {
      throw new Error(`Container element with id '${this.containerId}' not found`);
    }

    // Clear existing content
    container.innerHTML = '';

    // Set up container styles
    container.style.position = 'relative';
    container.style.width = `${this.dimensions.width}px`;
    container.style.height = `${this.dimensions.height}px`;
    container.style.margin = '0 auto';
    container.style.backgroundColor = this.backgroundColor;
    container.style.borderRadius = '8px';
    container.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';

    // Create SVG element
    this.svgElement = renderSVG({
      width: this.dimensions.width,
      height: this.dimensions.height,
    });

    if (this.className) {
      this.svgElement.classList.add(this.className);
    }

    // Append SVG to container
    container.appendChild(this.svgElement);
  }

  /**
   * Gets the available drawing area within the margins
   */
  private getDrawingArea(): Dimensions {
    return {
      width: this.dimensions.width - this.margin.left - this.margin.right,
      height: this.dimensions.height - this.margin.top - this.margin.bottom,
    };
  }

  /**
   * Sets the data points for the graph
   * @param data Array of data points
   */
  setData(data: DataPoint[]): void {
    if (!Array.isArray(data) || data.length === 0) {
      throw new Error('Data must be a non-empty array');
    }
    this.dataPoints = [...data];
  }

  /**
   * Renders a bar chart with the current data
   */
  renderBarChart(): void {
    if (this.dataPoints.length === 0) {
      throw new Error('No data available to render. Call setData() first.');
    }

    if (!this.svgElement) {
      throw new Error('SVG element not initialized');
    }

    // Clear previous content
    this.svgElement.innerHTML = '';

    const { width, height } = this.getDrawingArea();

    // Find maximum value for scaling
    const maxValue = Math.max(...this.dataPoints.map(d => d.value));

    // Calculate bar width and spacing
    const barWidth = width / this.dataPoints.length * 0.6;
    const spacing = width / this.dataPoints.length - barWidth;
    const xScale = width / (this.dataPoints.length * barWidth + (this.dataPoints.length - 1) * spacing);
    const yScale = height / maxValue;

    // Create group for the chart content
    const chartGroup = createGroup({
      transform: `translate(${this.margin.left}, ${this.margin.top})`
    });

    // Draw bars
    this.dataPoints.forEach((point, index) => {
      const x = index * (barWidth + spacing);
      const barHeight = point.value * yScale;
      const y = height - barHeight;

      // Draw bar
      const bar = createRect({
        x,
        y,
        width: barWidth,
        height: barHeight,
        fill: point.color || '#3b82f6',
        stroke: '#1e40af',
        strokeWidth: 1,
        rx: 4,
        ry: 4
      });

      // Add hover effect
      bar.addEventListener('mouseenter', () => {
        (bar as SVGRectElement).setAttribute('fill', '#1d4ed8');
        tooltip.textContent = `${point.label}: ${point.value}`;
        const bbox = bar.getBoundingClientRect();
        const svgBBox = this.svgElement!.getBoundingClientRect();
        tooltip.style.left = `${bbox.left - svgBBox.left + barWidth / 2}px`;
        tooltip.style.top = `${bbox.top - svgBBox.top - 10}px`;
        tooltip.style.opacity = '1';
      });

      bar.addEventListener('mouseleave', () => {
        (bar as SVGRectElement).setAttribute('fill', point.color || '#3b82f6');
        tooltip.style.opacity = '0';
      });

      chartGroup.appendChild(bar);

      // Add label
      const label = createText({
        x: x + barWidth / 2,
        y: height + 20,
        text: point.label,
        fontSize: 12,
        fontFamily: 'system-ui, sans-serif',
        fill: '#374151',
        textAnchor: 'middle'
      });

      chartGroup.appendChild(label);

      // Add value label on top of bar
      const valueLabel = createText({
        x: x + barWidth / 2,
        y: y - 5,
        text: point.value.toString(),
        fontSize: 12,
        fontFamily: 'system-ui, sans-serif',
        fill: '#374151',
        textAnchor: 'middle'
      });

      chartGroup.appendChild(valueLabel);
    });

    // Add Y-axis grid lines and labels
    const numGridLines = 5;
    for (let i = 0; i <= numGridLines; i++) {
      const gridValue = (maxValue / numGridLines) * i;
      const gridY = height - (gridValue * yScale);

      // Grid line
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', '0');
      line.setAttribute('y1', gridY.toString());
      line.setAttribute('x2', width.toString());
      line.setAttribute('y2', gridY.toString());
      line.setAttribute('stroke', '#e5e7eb');
      line.setAttribute('stroke-width', '1');
      if (i > 0) line.setAttribute('stroke-dasharray', '4,4');

      chartGroup.appendChild(line);

      // Y-axis label
      const label = createText({
        x: -10,
        y: gridY + 4,
        text: Math.round(gridValue).toString(),
        fontSize: 12,
        fontFamily: 'system-ui, sans-serif',
        fill: '#6b7280',
        textAnchor: 'end'
      });

      chartGroup.appendChild(label);
    }

    // Add Y-axis label
    const yAxisLabel = createText({
      x: -height / 2,
      y: -40,
      text: 'Values',
      fontSize: 14,
      fontFamily: 'system-ui, sans-serif',
      fill: '#111827',
      textAnchor: 'middle',
      transform: 'rotate(-90)'
    });

    chartGroup.appendChild(yAxisLabel);

    // Add chart title
    const title = createText({
      x: width / 2,
      y: -10,
      text: 'Bar Chart',
      fontSize: 16,
      fontFamily: 'system-ui, sans-serif',
      fill: '#111827',
      fontWeight: 'bold',
      textAnchor: 'middle'
    });

    chartGroup.appendChild(title);

    // Add tooltip element
    const tooltip = document.createElement('div');
    tooltip.style.position = 'absolute';
    tooltip.style.background = 'rgba(0, 0, 0, 0.8)';
    tooltip.style.color = 'white';
    tooltip.style.padding = '4px 8px';
    tooltip.style.borderRadius = '4px';
    tooltip.style.fontSize = '12px';
    tooltip.style.pointerEvents = 'none';
    tooltip.style.opacity = '0';
    tooltip.style.transition = 'opacity 0.2s';
    tooltip.style.zIndex = '1000';
    tooltip.style.top = '0';
    tooltip.style.left = '0';

    this.svgElement.parentNode?.appendChild(tooltip);

    // Add the chart group to SVG
    this.svgElement.appendChild(chartGroup);
  }

  /**
   * Renders a line chart with the current data
   */
  renderLineChart(): void {
    if (this.dataPoints.length === 0) {
      throw new Error('No data available to render. Call setData() first.');
    }

    if (!this.svgElement) {
      throw new Error('SVG element not initialized');
    }

    // Clear previous content
    this.svgElement.innerHTML = '';

    const { width, height } = this.getDrawingArea();

    // Find max value for scaling
    const maxValue = Math.max(...this.dataPoints.map(d => d.value));
    const minValue = Math.min(...this.dataPoints.map(d => d.value));
    const valueRange = maxValue - minValue || 1; // Avoid division by zero

    // Calculate scales
    const xScale = width / Math.max(1, this.dataPoints.length - 1);
    const yScale = height / valueRange;

    // Create group for the chart content
    const chartGroup = createGroup({
      transform: `translate(${this.margin.left}, ${this.margin.top})`
    });

    // Create path for the line
    let pathData = '';
    this.dataPoints.forEach((point, index) => {
      const x = index * xScale;
      const y = height - (point.value - minValue) * yScale;

      if (index === 0) {
        pathData += `M ${x} ${y}`;
      } else {
        pathData += ` L ${x} ${y}`;
      }
    });

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', pathData);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', '#3b82f6');
    path.setAttribute('stroke-width', '3');
    path.setAttribute('stroke-linejoin', 'round');
    path.setAttribute('stroke-linecap', 'round');

    chartGroup.appendChild(path);

    // Add data points
    this.dataPoints.forEach((point, index) => {
      const x = index * xScale;
      const y = height - (point.value - minValue) * yScale;

      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', x.toString());
      circle.setAttribute('cy', y.toString());
      circle.setAttribute('r', '5');
      circle.setAttribute('fill', point.color || '#3b82f6');
      circle.setAttribute('stroke', '#1e40af');
      circle.setAttribute('stroke-width', '2');

      // Add hover effect and tooltip
      circle.addEventListener('mouseenter', () => {
        (circle as SVGCircleElement).setAttribute('r', '7');
        tooltip.textContent = `${point.label}: ${point.value}`;
        const bbox = circle.getBoundingClientRect();
        const svgBBox = this.svgElement!.getBoundingClientRect();
        tooltip.style.left = `${bbox.left - svgBBox.left}px`;
        tooltip.style.top = `${bbox.top - svgBBox.top - 10}px`;
        tooltip.style.opacity = '1';
      });

      circle.addEventListener('mouseleave', () => {
        (circle as SVGCircleElement).setAttribute('r', '5');
        tooltip.style.opacity = '0';
      });

      chartGroup.appendChild(circle);
    });

    // Add X-axis labels
    this.dataPoints.forEach((point, index) => {
      const x = index * xScale;
      const label = createText({
        x: x,
        y: height + 20,
        text: point.label,
        fontSize: 12,
        fontFamily: 'system-ui, sans-serif',
        fill: '#374151',
        textAnchor: 'middle'
      });

      chartGroup.appendChild(label);
    });

    // Add Y-axis grid lines and labels
    const numGridLines = 5;
    for (let i = 0; i <= numGridLines; i++) {
      const gridValue = minValue + (valueRange / numGridLines) * i;
      const gridY = height - (gridValue - minValue) * yScale;

      // Grid line
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', '0');
      line.setAttribute('y1', gridY.toString());
      line.setAttribute('x2', width.toString());
      line.setAttribute('y2', gridY.toString());
      line.setAttribute('stroke', '#e5e7eb');
      line.setAttribute('stroke-width', '1');
      if (i > 0) line.setAttribute('stroke-dasharray', '4,4');

      chartGroup.appendChild(line);

      // Y-axis label
      const label = createText({
        x: -10,
        y: gridY + 4,
        text: Math.round(gridValue).toString(),
        fontSize: 12,
        fontFamily: 'system-ui, sans-serif',
        fill: '#6b7280',
        textAnchor: 'end'
      });

      chartGroup.appendChild(label);
    }

    // Add Y-axis label
    const yAxisLabel = createText({
      x: -height / 2,
      y: -40,
      text: 'Values',
      fontSize: 14,
      fontFamily: 'system-ui, sans-serif',
      fill: '#111827',
      textAnchor: 'middle',
      transform: 'rotate(-90)'
    });

    chartGroup.appendChild(yAxisLabel);

    // Add chart title
    const title = createText({
      x: width / 2,
      y: -10,
      text: 'Line Chart',
      fontSize: 16,
      fontFamily: 'system-ui, sans-serif',
      fill: '#111827',
      fontWeight: 'bold',
      textAnchor: 'middle'
    });

    chartGroup.appendChild(title);

    // Add tooltip element
    const tooltip = document.createElement('div');
    tooltip.style.position = 'absolute';
    tooltip.style.background = 'rgba(0, 0, 0, 0.8)';
    tooltip.style.color = 'white';
    tooltip.style.padding = '4px 8px';
    tooltip.style.borderRadius = '4px';
    tooltip.style.fontSize = '12px';
    tooltip.style.pointerEvents = 'none';
    tooltip.style.opacity = '0';
    tooltip.style.transition = 'opacity 0.2s';
    tooltip.style.zIndex = '1000';
    tooltip.style.top = '0';
    tooltip.style.left = '0';

    this.svgElement.parentNode?.appendChild(tooltip);

    // Add the chart group to SVG
    this.svgElement.appendChild(chartGroup);
  }

  /**
   * Gets the current dimensions of the container
   */
  getDimensions(): Dimensions {
    return { ...this.dimensions };
  }

  /**
   * Updates the dimensions of the container and resizes the SVG
   * @param width New width
   * @param height New height
   */
  resize(width: number, height: number): void {
    if (width <= 0 || height <= 0) {
      throw new Error('Dimensions must be positive numbers');
    }

    this.dimensions = { width, height };
    this.initializeContainer();

    // Re-render the current chart type if data exists
    if (this.dataPoints.length > 0) {
      // Since we can't know the previous chart type, default to bar chart
      this.renderBarChart();
    }
  }

  /**
   * Destroys the graph container and cleans up event listeners
   */
  destroy(): void {
    if (this.svgElement && this.svgElement.parentNode) {
      // Remove all tooltips
      const tooltips = document.querySelectorAll('div[style*="rgba(0, 0, 0, 0.8)"]');
      tooltips.forEach(tooltip => {
        if (tooltip.parentNode) {
          tooltip.parentNode.removeChild(tooltip);
        }
      });

      // Remove the SVG element
      this.svgElement.parentNode.removeChild(this.svgElement);
      this.svgElement = null;
    }
  }
}