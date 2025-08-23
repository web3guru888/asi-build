import { createSVGElement } from './svg-utils';

/**
 * Configuration interface for dog-themed SVG generation
 */
interface DogSVGConfig {
  width?: number;
  height?: number;
  color?: string;
  variant?: 'sitting' | 'running' | 'barking' | 'sleeping';
  details?: boolean;
  className?: string;
}

/**
 * Generates dog-themed SVG elements based on configuration
 * Supports multiple dog variants with customizable appearance
 */
class SVGGenerator {
  /**
   * Creates an SVG of a dog in various poses
   * @param config Configuration options for the dog SVG
   * @returns SVG element representing a dog
   */
  static generateDog(config: DogSVGConfig = {}): SVGSVGElement {
    const {
      width = 200,
      height = 200,
      color = '#8B4513',
      variant = 'sitting',
      details = true,
      className = 'dog-svg',
    } = config;

    try {
      const svg = createSVGElement('svg', {
        width,
        height,
        viewBox: '0 0 100 100',
        xmlns: 'http://www.w3.org/2000/svg',
        class: className,
      });

      // Base styles for dog elements
      const baseStyles = {
        fill: color,
        stroke: '#654321',
        strokeWidth: 0.5,
      };

      switch (variant) {
        case 'sitting':
          this.addSittingDog(svg, baseStyles, details);
          break;
        case 'running':
          this.addRunningDog(svg, baseStyles, details);
          break;
        case 'barking':
          this.addBarkingDog(svg, baseStyles, details);
          break;
        case 'sleeping':
          this.addSleepingDog(svg, baseStyles, details);
          break;
      }

      // Add decorative elements if requested
      if (details) {
        this.addDecorativeElements(svg, width, height);
      }

      return svg;
    } catch (error) {
      console.error('Failed to generate dog SVG:', error);
      throw new Error(`SVG generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Adds a sitting dog composition to the SVG
   */
  private static addSittingDog(
    svg: SVGSVGElement,
    styles: { fill: string; stroke: string; strokeWidth: number },
    details: boolean
  ): void {
    // Body
    createSVGElement('ellipse', {
      cx: 50,
      cy: 60,
      rx: 25,
      ry: 18,
      fill: styles.fill,
      stroke: styles.stroke,
      'stroke-width': styles.strokeWidth,
    }, svg);

    // Head
    createSVGElement('circle', {
      cx: 50,
      cy: 35,
      r: 18,
      fill: styles.fill,
      stroke: styles.stroke,
      'stroke-width': styles.strokeWidth,
    }, svg);

    // Ears (left)
    createSVGElement('path', {
      d: 'M42,22 C40,18 48,16 50,20',
      fill: 'none',
      stroke: styles.stroke,
      'stroke-width': styles.strokeWidth,
    }, svg);

    // Ears (right)
    createSVGElement('path', {
      d: 'M58,22 C60,18 52,16 50,20',
      fill: 'none',
      stroke: styles.stroke,
      'stroke-width': styles.strokeWidth,
    }, svg);

    // Legs (front)
    createSVGElement('path', {
      d: 'M40,75 L40,85 L43,85 L43,75 Z',
      fill: styles.fill,
      stroke: styles.stroke,
      'stroke-width': styles.strokeWidth,
    }, svg);

    createSVGElement('path', {
      d: 'M60,75 L60,85 L57,85 L57,75 Z',
      fill: styles.fill,
      stroke: styles.stroke,
      'stroke-width': styles.strokeWidth,
    }, svg);

    // Tail
    createSVGElement('path', {
      d: 'M75,55 C80,50 85,40 78,38',
      fill: 'none',
      stroke: styles.fill,
      'stroke-width': 3,
      'stroke-linecap': 'round',
    }, svg);

    if (details) {
      // Eyes
      createSVGElement('circle', { cx: 46, cy: 32, r: 2, fill: '#000' }, svg);
      createSVGElement('circle', { cx: 54, cy: 32, r: 2, fill: '#000' }, svg);

      // Nose
      createSVGElement('circle', { cx: 50, cy: 38, r: 1.5, fill: '#000' }, svg);

      // Mouth
      createSVGElement('path', { d: 'M50,38 L50,41', stroke: '#000', 'stroke-width': 1 }, svg);
    }
  }

  /**
   * Adds a running dog composition to the SVG
   */
  private static addRunningDog(
    svg: SVGSVGElement,
    styles: { fill: string; stroke: string; strokeWidth: number },
    details: boolean
  ): void {
    // Body (dynamic pose)
    createSVGElement('ellipse', {
      cx: 50,
      cy: 60,
      rx: 28,
      ry: 16,
      fill: styles.fill,
      stroke: styles.stroke,
      'stroke-width': styles.strokeWidth,
      transform: 'rotate(-10, 50, 60)',
    }, svg);

    // Head
    createSVGElement('circle', {
      cx: 68,
      cy: 50,
      r: 16,
      fill: styles.fill,
      stroke: styles.stroke,
      'stroke-width': styles.strokeWidth,
    }, svg);

    // Legs (running pose - extended)
    createSVGElement('path', {
      d: 'M35,70 L25,85',
      stroke: styles.fill,
      'stroke-width': 4,
      'stroke-linecap': 'round',
    }, svg);

    createSVGElement('path', {
      d: 'M45,72 L35,88',
      stroke: styles.fill,
      'stroke-width': 4,
      'stroke-linecap': 'round',
    }, svg);

    createSVGElement('path', {
      d: 'M60,70 L70,85',
      stroke: styles.fill,
      'stroke-width': 4,
      'stroke-linecap': 'round',
    }, svg);

    createSVGElement('path', {
      d: 'M70,72 L80,88',
      stroke: styles.fill,
      'stroke-width': 4,
      'stroke-linecap': 'round',
    }, svg);

    // Tail (waving)
    createSVGElement('path', {
      d: 'M78,55 C90,45 95,30 85,25',
      fill: 'none',
      stroke: styles.fill,
      'stroke-width': 3,
      'stroke-linecap': 'round',
    }, svg);

    if (details) {
      // Eyes
      createSVGElement('circle', { cx: 64, cy: 47, r: 2, fill: '#000' }, svg);
      createSVGElement('circle', { cx: 72, cy: 47, r: 2, fill: '#000' }, svg);

      // Nose
      createSVGElement('circle', { cx: 68, cy: 51, r: 1.8, fill: '#000' }, svg);

      // Mouth line
      createSVGElement('path', { d: 'M68,51 L73,53', stroke: '#000', 'stroke-width': 1 }, svg);
    }
  }

  /**
   * Adds a barking dog composition to the SVG
   */
  private static addBarkingDog(
    svg: SVGSVGElement,
    styles: { fill: string; stroke: string; strokeWidth: number },
    details: boolean
  ): void {
    // Body (upright position)
    createSVGElement('ellipse', {
      cx: 50,
      cy: 65,
      rx: 22,
      ry: 15,
      fill: styles.fill,
      stroke: styles.stroke,
      'stroke-width': styles.strokeWidth,
    }, svg);

    // Head (raised)
    createSVGElement('circle', {
      cx: 50,
      cy: 38,
      r: 17,
      fill: styles.fill,
      stroke: styles.stroke,
      'stroke-width': styles.strokeWidth,
    }, svg);

    // Front legs (up)
    createSVGElement('path', {
      d: 'M40,75 L40,60',
      stroke: styles.fill,
      'stroke-width': 4,
      'stroke-linecap': 'round',
    }, svg);

    createSVGElement('path', {
      d: 'M60,75 L60,60',
      stroke: styles.fill,
      'stroke-width': 4,
      'stroke-linecap': 'round',
    }, svg);

    // Tail (up)
    createSVGElement('path', {
      d: 'M72,60 C80,50 85,40 80,30',
      fill: 'none',
      stroke: styles.fill,
      'stroke-width': 3,
      'stroke-linecap': 'round',
    }, svg);

    if (details) {
      // Eyes (alert expression)
      createSVGElement('circle', { cx: 46, cy: 35, r: 2.5, fill: '#000' }, svg);
      createSVGElement('circle', { cx: 54, cy: 35, r: 2.5, fill: '#000' }, svg);

      // Nose
      createSVGElement('circle', { cx: 50, cy: 41, r: 1.8, fill: '#000' }, svg);

      // Open mouth
      createSVGElement('path', { d: 'M50,41 L50,46 L53,46', stroke: '#000', 'stroke-width': 1.2 }, svg);

      // Sound waves
      createSVGElement('path', {
        d: 'M75,30 Q80,28 85,30',
        fill: 'none',
        stroke: '#555',
        'stroke-width': 1.5,
      }, svg);

      createSVGElement('path', {
        d: 'M75,33 Q82,30 85,35',
        fill: 'none',
        stroke: '#555',
        'stroke-width': 1.2,
      }, svg);
    }
  }

  /**
   * Adds a sleeping dog composition to the SVG
   */
  private static addSleepingDog(
    svg: SVGSVGElement,
    styles: { fill: string; stroke: string; strokeWidth: number },
    details: boolean
  ): void {
    // Body (curled position)
    createSVGElement('path', {
      d: 'M35,70 C35,60 50,50 65,60 C80,70 75,80 65,80 C55,80 45,80 35,70 Z',
      fill: styles.fill,
      stroke: styles.stroke,
      'stroke-width': styles.strokeWidth,
    }, svg);

    // Head (down)
    createSVGElement('circle', {
      cx: 38,
      cy: 68,
      r: 14,
      fill: styles.fill,
      stroke: styles.stroke,
      'stroke-width': styles.strokeWidth,
    }, svg);

    // Tail (curled)
    createSVGElement('path', {
      d: 'M68,58 C75,55 78,50 75,47 C72,44 68,46 66,48',
      fill: 'none',
      stroke: styles.fill,
      'stroke-width': 3,
      'stroke-linecap': 'round',
    }, svg);

    if (details) {
      // Closed eyes (sleeping)
      createSVGElement('path', { d: 'M34,65 L38,67 L42,65', stroke: '#000', 'stroke-width': 1 }, svg);
      createSVGElement('path', { d: 'M34,68 L38,70 L42,68', stroke: '#000', 'stroke-width': 1 }, svg);

      // Nose
      createSVGElement('circle', { cx: 38, cy: 72, r: 1.5, fill: '#000' }, svg);

      // Zzz indicator
      createSVGElement('text', {
        x: 70,
        y: 40,
        fill: '#555',
        'font-size': '6',
        'font-family': 'Arial, sans-serif',
      }, svg).textContent = 'Zzz';
    }
  }

  /**
   * Adds decorative elements around the dog SVG
   */
  private static addDecorativeElements(svg: SVGSVGElement, width: number, height: number): void {
    // Add a bone near the dog
    const boneGroup = createSVGElement('g', {}, svg);
    createSVGElement('path', {
      d: 'M80,85 C85,80 90,85 85,90 C80,95 75,90 80,85 Z',
      fill: '#FFF',
      stroke: '#DDD',
      'stroke-width': 0.5,
    }, boneGroup);

    createSVGElement('circle', { cx: 80, cy: 85, r: 3, fill: '#FFF' }, boneGroup);
    createSVGElement('circle', { cx: 85, cy: 90, r: 3, fill: '#FFF' }, boneGroup);

    // Add paw prints around
    const paw1 = createSVGElement('g', { opacity: '0.7' }, svg);
    this.addPawPrint(paw1, 15, 85, 0.3);

    const paw2 = createSVGElement('g', { opacity: '0.6' }, svg);
    this.addPawPrint(paw2, 22, 88, 0.25);

    const paw3 = createSVGElement('g', { opacity: '0.5' }, svg);
    this.addPawPrint(paw3, 10, 90, 0.2);
  }

  /**
   * Adds a paw print design to the specified parent element
   */
  private static addPawPrint(parent: SVGElement, x: number, y: number, scale: number): void {
    const pawGroup = createSVGElement('g', {
      transform: `translate(${x}, ${y}) scale(${scale})`,
    }, parent);

    // Main pad
    createSVGElement('circle', { cx: 0, cy: 0, r: 8, fill: '#666' }, pawGroup);

    // Toe pads
    createSVGElement('circle', { cx: -8, cy: -5, r: 4, fill: '#666' }, pawGroup);
    createSVGElement('circle', { cx: -5, cy: -8, r: 4, fill: '#666' }, pawGroup);
    createSVGElement('circle', { cx: -2, cy: -6, r: 4, fill: '#666' }, pawGroup);
    createSVGElement('circle', { cx: 5, cy: -7, r: 4, fill: '#666' }, pawGroup);
  }

  /**
   * Generates a decorative border with dog-themed elements
   */
  static generateThemedBorder(config: { size: 'small' | 'medium' | 'large'; color?: string } = { size: 'medium' }) {
    const { size, color = '#D2691E' } = config;
    let spacing: number;

    switch (size) {
      case 'small':
        spacing = 15;
        break;
      case 'medium':
        spacing = 25;
        break;
      case 'large':
        spacing = 40;
        break;
    }

    try {
      const svg = createSVGElement('svg', {
        width: '100%',
        height: '100%',
        viewBox: '0 0 100 100',
        xmlns: 'http://www.w3.org/2000/svg',
      });

      // Create pattern of bones along edges
      for (let x = spacing; x < 100; x += spacing) {
        this.addMiniBone(svg, x, 10, 8, color);
        this.addMiniBone(svg, x, 90, 8, color);
      }

      for (let y = spacing; y < 100; y += spacing) {
        this.addMiniBone(svg, 10, y, 8, color);
        this.addMiniBone(svg, 90, y, 8, color);
      }

      return svg;
    } catch (error) {
      console.error('Failed to generate themed border