import { Point, Dimensions, Margin } from './types';

/**
 * Gets or creates an SVG element with specified dimensions
 * @param container - The container element to append the SVG to
 * @param dimensions - The width and height for the SVG
 * @param margin - Optional margin to apply (default: 40 on all sides)
 * @returns SVG element and its view dimensions
 */
export function setupSVG(
  container: HTMLElement,
  dimensions: Dimensions,
  margin: Margin = { top: 40, right: 40, bottom: 40, left: 40 }
): { svg: SVGSVGElement; viewDimensions: Dimensions } {
  // Clear container
  container.innerHTML = '';

  // Create SVG element
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', (dimensions.width + margin.left + margin.right).toString());
  svg.setAttribute('height', (dimensions.height + margin.top + margin.bottom).toString());

  container.appendChild(svg);

  const viewDimensions = {
    width: dimensions.width,
    height: dimensions.height,
  };

  return { svg, viewDimensions };
}

/**
 * Linear scale function to map data range to visual range
 * @param domain - Input data range [min, max]
 * @param range - Output visual range [min, max]
 * @returns Scaling function
 */
export function scaleLinear(
  domain: [number, number],
  range: [number, number]
): (value: number) => number {
  const [domainMin, domainMax] = domain;
  const [rangeMin, rangeMax] = range;

  if (domainMin === domainMax) {
    return () => rangeMin;
  }

  const ratio = (rangeMax - rangeMin) / (domainMax - domainMin);
  return (value: number): number => rangeMin + (value - domainMin) * ratio;
}

/**
 * Generate path data for a line from array of points
 * @param points Array of Point objects
 * @param xScale Scaling function for x-axis
 * @param yScale Scaling function for y-axis
 * @returns String suitable for SVG path 'd' attribute
 */
export function generateLinePath(
  points: Point[],
  xScale: (n: number) => number,
  yScale: (n: number) => number
): string {
  if (!points.length) return '';

  return points
    .map((point, i) => {
      const x = xScale(point.x);
      const y = yScale(point.y);
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');
}

/**
 * Generate path data for an area (filled region under a line)
 * @param points Array of Point objects
 * @param xScale Scaling function for x-axis
 * @param yScale Scaling function for y-axis
 * @param baseY Base y-value for bottom of area (e.g., for axes)
 * @returns String suitable for SVG path 'd' attribute
 */
export function generateAreaPath(
  points: Point[],
  xScale: (n: number) => number,
  yScale: (n: number) => number,
  baseY: number
): string {
  if (!points.length) return '';

  const start = points[0];
  let path = `M ${xScale(start.x)} ${yScale(start.y)}`;

  points.slice(1).forEach((point) => {
    path += ` L ${xScale(point.x)} ${yScale(point.y)}`;
  });

  // Close the path
  const lastPoint = points[points.length - 1];
  path += ` L ${xScale(lastPoint.x)} ${baseY} L ${xScale(start.x)} ${baseY} Z`;

  return path;
}

/**
 * Create an SVG group (g) element with optional translation
 * @param parent Parent SVG element
 * @param x X translation
 * @param y Y translation
 * @returns Created SVG group element
 */
export function createGroup(parent: SVGSVGElement, x = 0, y = 0): SVGGElement {
  const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  if (x !== 0 || y !== 0) {
    g.setAttribute('transform', `translate(${x}, ${y})`);
  }
  parent.appendChild(g);
  return g;
}

/**
 * Add axis labels and ticks to SVG
 * @param parent Parent group element
 * @param scale Value scaling function
 * @param orientation 'bottom', 'top', 'left', or 'right'
 * @param label Axis label text
 * @param length Length of the axis line
 * @param position Position offset from origin
 */
export function drawAxis(
  parent: SVGGElement,
  scale: (n: number) => number,
  orientation: 'bottom' | 'left',
  label: string,
  length: number,
  position: number
): void {
  const isHorizontal = orientation === 'bottom';
  const tickSize = 6;
  const domain = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]; // default ticks

  // Axis line
  const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  line.setAttribute(isHorizontal ? 'x1' : 'y1', '0');
  line.setAttribute(isHorizontal ? 'y1' : 'x1', position.toString());
  line.setAttribute(isHorizontal ? 'x2' : 'y2', (isHorizontal ? length : 0).toString());
  line.setAttribute(isHorizontal ? 'y2' : 'x2', (isHorizontal ? 0 : length).toString());
  line.setAttribute('stroke', '#333');
  parent.appendChild(line);

  // Ticks and labels
  domain.forEach((value) => {
    const scaledValue = scale(value);
    const tickLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');

    if (isHorizontal) {
      tickLine.setAttribute('x1', scaledValue.toString());
      tickLine.setAttribute('y1', position.toString());
      tickLine.setAttribute('x2', scaledValue.toString());
      tickLine.setAttribute('y2', (position + tickSize).toString());
      tickLine.setAttribute('stroke', '#333');

      text.setAttribute('x', scaledValue.toString());
      text.setAttribute('y', (position + tickSize + 15).toString());
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('font-size', '12px');
      text.setAttribute('fill', '#333');
      text.textContent = value.toString();
    } else {
      tickLine.setAttribute('x1', position.toString());
      tickLine.setAttribute('y1', scaledValue.toString());
      tickLine.setAttribute('x2', (position + tickSize).toString());
      tickLine.setAttribute('y2', scaledValue.toString());
      tickLine.setAttribute('stroke', '#333');

      text.setAttribute('x', (position + tickSize + 5).toString());
      text.setAttribute('y', (scaledValue + 4).toString());
      text.setAttribute('text-anchor', 'start');
      text.setAttribute('font-size', '12px');
      text.setAttribute('fill', '#333');
      text.textContent = value.toString();
    }

    parent.appendChild(tickLine);
    parent.appendChild(text);
  });

  // Axis label
  const labelEl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  labelEl.setAttribute('x', (isHorizontal ? length / 2 : -position).toString());
  labelEl.setAttribute('y', isHorizontal ? position + 40 : -15);
  labelEl.setAttribute('text-anchor', 'middle');
  labelEl.setAttribute('font-size', '14px');
  labelEl.setAttribute('font-weight', 'bold');
  labelEl.setAttribute('fill', '#333');
  labelEl.textContent = label;
  if (!isHorizontal) {
    labelEl.setAttribute('transform', `rotate(-90)`);
    labelEl.setAttribute('text-anchor', 'middle');
    labelEl.setAttribute('x', -length / 2);
    labelEl.setAttribute('y', 15);
  }
  parent.appendChild(labelEl);
}