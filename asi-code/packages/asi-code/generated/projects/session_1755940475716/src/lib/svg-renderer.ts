import { VisualizationConfig, Point, Dimensions } from '../lib/types';

/**
 * SVGRenderer class for creating and managing SVG elements
 * Handles the core SVG rendering functionality for data visualizations
 */
export class SVGRenderer {
  private svg: SVGSVGElement | null = null;
  private container: HTMLElement | null = null;
  private width: number = 0;
  private height: number = 0;

  /**
   * Initialize the SVG renderer with a container and dimensions
   * @param containerId - The ID of the container element
   * @param dimensions - Width and height for the SVG
   */
  init(containerId: string, dimensions: Dimensions): void {
    this.container = document.getElementById(containerId);
    
    if (!this.container) {
      throw new Error(`Container with id '${containerId}' not found`);
    }

    this.width = dimensions.width;
    this.height = dimensions.height;
    this.createSVG();
  }

  /**
   * Create the SVG element and append it to the container
   */
  private createSVG(): void {
    // Remove any existing SVG
    this.clear();
    
    this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    this.svg.setAttribute('width', this.width.toString());
    this.svg.setAttribute('height', this.height.toString());
    this.svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    this.svg.setAttribute('version', '1.1');
    
    // Add accessibility attributes
    this.svg.setAttribute('role', 'img');
    this.svg.setAttribute('aria-label', 'Data visualization chart');
    
    this.container?.appendChild(this.svg);
  }

  /**
   * Clear the SVG content
   */
  clear(): void {
    if (this.svg && this.svg.parentNode) {
      this.svg.parentNode.removeChild(this.svg);
      this.svg = null;
    }
  }

  /**
   * Get the SVG element
   * @returns The SVG element or null if not initialized
   */
  getSVG(): SVGSVGElement | null {
    return this.svg;
  }

  /**
   * Create a group element in the SVG
   * @returns The created group element
   */
  createGroup(): SVGGElement {
    if (!this.svg) {
      throw new Error('SVG not initialized. Call init() first.');
    }

    const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    this.svg.appendChild(group);
    return group;
  }

  /**
   * Create an SVG line
   * @param x1 - Starting x coordinate
   * @param y1 - Starting y coordinate
   * @param x2 - Ending x coordinate
   * @param y2 - Ending y coordinate
   * @param className - CSS class name for styling
   * @returns The created line element
   */
  createLine(x1: number, y1: number, x2: number, y2: number, className?: string): SVGLineElement {
    if (!this.svg) {
      throw new Error('SVG not initialized. Call init() first.');
    }

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', x1.toString());
    line.setAttribute('y1', y1.toString());
    line.setAttribute('x2', x2.toString());
    line.setAttribute('y2', y2.toString());
    
    if (className) {
      line.setAttribute('class', className);
    }

    this.svg.appendChild(line);
    return line;
  }

  /**
   * Create an SVG circle
   * @param cx - Center x coordinate
   * @param cy - Center y coordinate
   * @param r - Radius
   * @param className - CSS class name for styling
   * @returns The created circle element
   */
  createCircle(cx: number, cy: number, r: number, className?: string): SVGCircleElement {
    if (!this.svg) {
      throw new Error('SVG not initialized. Call init() first.');
    }

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', cx.toString());
    circle.setAttribute('cy', cy.toString());
    circle.setAttribute('r', r.toString());
    
    if (className) {
      circle.setAttribute('class', className);
    }

    this.svg.appendChild(circle);
    return circle;
  }

  /**
   * Create an SVG text element
   * @param x - X coordinate
   * @param y - Y coordinate
   * @param content - Text content
   * @param className - CSS class name for styling
   * @returns The created text element
   */
  createText(x: number, y: number, content: string, className?: string): SVGTextElement {
    if (!this.svg) {
      throw new Error('SVG not initialized. Call init() first.');
    }

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', x.toString());
    text.setAttribute('y', y.toString());
    text.textContent = content;
    
    if (className) {
      text.setAttribute('class', className);
    }

    this.svg.appendChild(text);
    return text;
  }

  /**
   * Create an SVG path
   * @param d - Path data string
   * @param className - CSS class name for styling
   * @returns The created path element
   */
  createPath(d: string, className?: string): SVGPathElement {
    if (!this.svg) {
      throw new Error('SVG not initialized. Call init() first.');
    }

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', d);
    
    if (className) {
      path.setAttribute('class', className);
    }

    this.svg.appendChild(path);
    return path;
  }

  /**
   * Create grid lines for the visualization
   * @param config - Visualization configuration
   */
  createGrid(config: VisualizationConfig): void {
    if (!this.svg) {
      throw new Error('SVG not initialized. Call init() first.');
    }

    const { width, height, margin } = config.dimensions;
    const { grid } = config;

    if (!grid.enabled) {
      return;
    }

    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    // Create horizontal grid lines
    if (grid.horizontal) {
      const count = grid.horizontalCount || 5;
      for (let i = 0; i <= count; i++) {
        const y = margin.top + (i * innerHeight) / count;
        this.createLine(
          margin.left,
          y,
          width - margin.right,
          y,
          'grid-line horizontal'
        );
      }
    }

    // Create vertical grid lines
    if (grid.vertical) {
      const count = grid.verticalCount || 5;
      for (let i = 0; i <= count; i++) {
        const x = margin.left + (i * innerWidth) / count;
        this.createLine(
          x,
          margin.top,
          x,
          height - margin.bottom,
          'grid-line vertical'
        );
      }
    }
  }

  /**
   * Create axes for the visualization
   * @param config - Visualization configuration
   */
  createAxes(config: VisualizationConfig): void {
    if (!this.svg) {
      throw new Error('SVG not initialized. Call init() first.');
    }

    const { width, height, margin } = config.dimensions;

    // X axis
    this.createLine(
      margin.left,
      height - margin.bottom,
      width - margin.right,
      height - margin.bottom,
      'axis x-axis'
    );

    // Y axis
    this.createLine(
      margin.left,
      margin.top,
      margin.left,
      height - margin.bottom,
      'axis y-axis'
    );

    // Axis labels
    if (config.axes?.x?.label) {
      this.createText(
        width / 2,
        height - margin.bottom + 30,
        config.axes.x.label,
        'axis-label x-axis-label'
      );
    }

    if (config.axes?.y?.label) {
      const text = this.createText(
        margin.left - 50,
        height / 2,
        config.axes.y.label,
        'axis-label y-axis-label'
      );
      // Rotate Y axis label
      text.setAttribute('transform', `rotate(-90, ${margin.left - 50}, ${height / 2})`);
    }
  }

  /**
   * Update the dimensions of the SVG
   * @param dimensions - New dimensions
   */
  updateDimensions(dimensions: Dimensions): void {
    this.width = dimensions.width;
    this.height = dimensions.height;

    if (this.svg) {
      this.svg.setAttribute('width', this.width.toString());
      this.svg.setAttribute('height', this.height.toString());
    }
  }

  /**
   * Check if the renderer is initialized
   * @returns Boolean indicating if initialized
   */
  isInitialized(): boolean {
    return this.svg !== null && this.container !== null;
  }
}