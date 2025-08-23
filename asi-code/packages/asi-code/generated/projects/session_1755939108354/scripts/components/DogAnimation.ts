import { generateSVG } from '../utils/svg-generator';

/**
 * DogAnimation class for creating and managing dog-themed SVG animations
 * Provides methods to generate custom dog illustrations and animations
 */
class DogAnimation {
  private container: HTMLElement | null;
  private animationInterval: number | null = null;
  private currentFrame: number = 0;
  private frames: SVGSVGElement[] = [];

  /**
   * Creates an instance of DogAnimation
   * @param containerId - The ID of the container element where the animation will be rendered
   */
  constructor(containerId: string) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      throw new Error(`Container with ID '${containerId}' not found`);
    }
    this.initializeAnimation();
  }

  /**
   * Initializes the dog animation by generating SVG frames
   */
  private initializeAnimation(): void {
    try {
      this.frames = this.generateDogFrames();
      this.currentFrame = 0;
    } catch (error) {
      console.error('Failed to initialize dog animation:', error);
      this.fallbackToStaticImage();
    }
  }

  /**
   * Generates a series of SVG frames for the dog animation
   * @returns Array of SVGSVGElement objects representing animation frames
   */
  private generateDogFrames(): SVGSVGElement[] {
    const frames: SVGSVGElement[] = [];
    const baseConfig = {
      width: 200,
      height: 200,
      viewBox: '0 0 200 200'
    };

    // Frame 1: Dog sitting
    frames.push(generateSVG({
      ...baseConfig,
      elements: [
        { type: 'circle', attrs: { cx: '100', cy: '80', r: '30', fill: '#D2691E' } }, // Head
        { type: 'circle', attrs: { cx: '90', cy: '70', r: '8', fill: '#FFFFFF' } }, // Eye
        { type: 'circle', attrs: { cx: '90', cy: '70', r: '3', fill: '#000000' } }, // Pupil
        { type: 'circle', attrs: { cx: '115', cy: '75', r: '5', fill: '#D2691E' } }, // Ear
        { type: 'path', attrs: { d: 'M95,95 Q100,110 105,95', stroke: '#000000', 'stroke-width': '2', fill: 'none' } }, // Mouth
        { type: 'rect', attrs: { x: '80', y: '110', width: '40', height: '60', fill: '#D2691E', rx: '10' } }, // Body
        { type: 'rect', attrs: { x: '75', y: '160', width: '15', height: '20', fill: '#D2691E', rx: '7' } }, // Front leg
        { type: 'rect', attrs: { x: '110', y: '160', width: '15', height: '20', fill: '#D2691E', rx: '7' } }, // Back leg
        { type: 'path', attrs: { d: 'M120,140 Q140,130 140,120', stroke: '#D2691E', 'stroke-width': '10', fill: 'none', 'stroke-linecap': 'round' } } // Tail
      ],
      attrs: { class: 'dog-animation-frame', 'data-frame': 'sit' }
    }));

    // Frame 2: Dog wagging tail
    frames.push(generateSVG({
      ...baseConfig,
      elements: [
        { type: 'circle', attrs: { cx: '100', cy: '80', r: '30', fill: '#D2691E' } }, // Head
        { type: 'circle', attrs: { cx: '90', cy: '70', r: '8', fill: '#FFFFFF' } }, // Eye
        { type: 'circle', attrs: { cx: '90', cy: '70', r: '3', fill: '#000000' } }, // Pupil
        { type: 'circle', attrs: { cx: '115', cy: '75', r: '5', fill: '#D2691E' } }, // Ear
        { type: 'path', attrs: { d: 'M95,95 Q100,110 105,95', stroke: '#000000', 'stroke-width': '2', fill: 'none' } }, // Mouth
        { type: 'rect', attrs: { x: '80', y: '110', width: '40', height: '60', fill: '#D2691E', rx: '10' } }, // Body
        { type: 'rect', attrs: { x: '75', y: '160', width: '15', height: '20', fill: '#D2691E', rx: '7' } }, // Front leg
        { type: 'rect', attrs: { x: '110', y: '160', width: '15', height: '20', fill: '#D2691E', rx: '7' } }, // Back leg
        { type: 'path', attrs: { d: 'M120,140 Q150,120 150,100', stroke: '#D2691E', 'stroke-width': '10', fill: 'none', 'stroke-linecap': 'round' } } // Tail wagging
      ],
      attrs: { class: 'dog-animation-frame', 'data-frame': 'wag' }
    }));

    // Frame 3: Dog with tongue out
    frames.push(generateSVG({
      ...baseConfig,
      elements: [
        { type: 'circle', attrs: { cx: '100', cy: '80', r: '30', fill: '#D2691E' } }, // Head
        { type: 'circle', attrs: { cx: '90', cy: '70', r: '8', fill: '#FFFFFF' } }, // Eye
        { type: 'circle', attrs: { cx: '90', cy: '70', r: '3', fill: '#000000' } }, // Pupil
        { type: 'circle', attrs: { cx: '115', cy: '75', r: '5', fill: '#D2691E' } }, // Ear
        { type: 'path', attrs: { d: 'M95,95 Q100,115 105,95', stroke: '#000000', 'stroke-width': '2', fill: 'none' } }, // Mouth open
        { type: 'path', attrs: { d: 'M100,105 L100,120 L105,115', fill: '#FF69B4' } }, // Tongue
        { type: 'rect', attrs: { x: '80', y: '110', width: '40', height: '60', fill: '#D2691E', rx: '10' } }, // Body
        { type: 'rect', attrs: { x: '75', y: '160', width: '15', height: '20', fill: '#D2691E', rx: '7' } }, // Front leg
        { type: 'rect', attrs: { x: '110', y: '160', width: '15', height: '20', fill: '#D2691E', rx: '7' } }, // Back leg
        { type: 'path', attrs: { d: 'M120,140 Q140,130 140,120', stroke: '#D2691E', 'stroke-width': '10', fill: 'none', 'stroke-linecap': 'round' } } // Tail
      ],
      attrs: { class: 'dog-animation-frame', 'data-frame': 'tongue' }
    }));

    return frames;
  }

  /**
   * Displays a fallback static image when SVG generation fails
   */
  private fallbackToStaticImage(): void {
    if (!this.container) return;

    this.container.innerHTML = '';
    const img = document.createElement('img');
    img.src = '../assets/images/dog-icon.svg';
    img.alt = 'Dog illustration';
    img.style.width = '200px';
    img.style.height = '200px';
    
    img.onerror = () => {
      img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI0QyNjkxRSIvPjxjaXJjbGUgY3g9IjEwMCIgY3k9IjgwIiByPSIzMCIgZmlsbD0iI0YwRjBGMCIvPjwvc3ZnPg==';
      img.alt = 'Dog placeholder';
    };
    
    this.container.appendChild(img);
  }

  /**
   * Starts the dog animation loop
   * @param frameRate - Frames per second (default: 1)
   */
  public start(frameRate: number = 1): void {
    if (this.animationInterval !== null) {
      this.stop();
    }

    const intervalMs = 1000 / frameRate;
    this.animationInterval = window.setInterval(() => {
      this.renderCurrentFrame();
      this.currentFrame = (this.currentFrame + 1) % this.frames.length;
    }, intervalMs);
  }

  /**
   * Stops the dog animation loop
   */
  public stop(): void {
    if (this.animationInterval !== null) {
      window.clearInterval(this.animationInterval);
      this.animationInterval = null;
    }
  }

  /**
   * Renders the current frame to the container
   */
  private renderCurrentFrame(): void {
    if (!this.container || this.frames.length === 0) return;

    try {
      // Clear container and add current frame
      this.container.innerHTML = '';
      this.container.appendChild(this.frames[this.currentFrame].cloneNode(true) as SVGSVGElement);
    } catch (error) {
      console.error('Failed to render dog animation frame:', error);
    }
  }

  /**
   * Updates the animation with new custom dog SVGs
   * @param customFrames - Array of custom SVG elements
   */
  public updateFrames(customFrames: SVGSVGElement[]): void {
    if (customFrames.length === 0) {
      throw new Error('Custom frames array cannot be empty');
    }

    this.stop();
    this.frames = customFrames;
    this.currentFrame = 0;
    this.renderCurrentFrame();
  }

  /**
   * Creates a custom dog SVG based on provided parameters
   * @param options - Configuration options for the custom dog
   * @returns SVGSVGElement representing the custom dog
   */
  public createCustomDog(options: {
    color?: string;
    size?: number;
    expression?: 'happy' | 'sad' | 'excited' | 'sleepy';
    accessories?: Array<'collar' | 'hat' | 'glasses'>;
  }): SVGSVGElement {
    const size = options.size || 200;
    const color = options.color || '#D2691E';
    const expression = options.expression || 'happy';
    const accessories = options.accessories || [];

    const elements = [
      { type: 'circle', attrs: { cx: `${size/2}`, cy: `${size*0.4}`, r: `${size*0.15}`, fill: color } }, // Head
      { type: 'circle', attrs: { cx: `${size*0.45}`, cy: `${size*0.35}`, r: `${size*0.04}`, fill: '#FFFFFF' } }, // Eye
      { type: 'circle', attrs: { cx: `${size*0.45}`, cy: `${size*0.35}`, r: `${size*0.015}`, fill: '#000000' } }, // Pupil
      { type: 'circle', attrs: { cx: `${size*0.575}`, cy: `${size*0.375}`, r: `${size*0.025}`, fill: color } }, // Ear
      { type: 'rect', attrs: { x: `${size*0.4}`, y: `${size*0.55}`, width: `${size*0.2}`, height: `${size*0.3}`, fill: color, rx: `${size*0.05}` } }, // Body
      { type: 'rect', attrs: { x: `${size*0.375}`, y: `${size*0.8}`, width: `${size*0.075}`, height: `${size*0.1}`, fill: color, rx: `${size*0.035}` } }, // Front leg
      { type: 'rect', attrs: { x: `${size*0.55}`, y: `${size*0.8}`, width: `${size*0.075}`, height: `${size*0.1}`, fill: color, rx: `${size*0.035}` } }, // Back leg
      { type: 'path', attrs: { d: `M${size*0.6},${size*0.7} Q${size*0.7},${size*0.65} ${size*0.7},${size*0.6}`, stroke: color, 'stroke-width': `${size*0.05}`, fill: 'none', 'stroke-linecap': 'round' } } // Tail
    ];

    // Add expression details
    if (expression === 'happy') {
      elements.push({ 
        type: 'path', 
        attrs: { 
          d: `M${size*0.475},${size*0.475} Q${size*0.5},${size*0.55} ${size*0.525},${size*0.475}`, 
          stroke: '#000000', 
          'stroke-width': '2', 
          fill: 'none' 
        } 
      });
    } else if (expression === 'sad') {
      elements.push({ 
        type: 'path', 
        attrs: { 
          d: `M${size*0.475},${size*0.525} Q${size*0.5},${size*0.45} ${size*0.525},${size*0.525}`, 
          stroke: '#000000', 
          'stroke-width': '2', 
          fill: 'none' 
        } 
      });
    } else if (expression === 'excited') {
      elements.push({ 
        type: 'path', 
        attrs: { 
          d: `M${size*0.475},${size*0.475} Q${size*0.5},${size*0.6} ${size*0.525},${size*0.475}`, 
          stroke: '#000000', 
          'stroke-width': '2', 
          fill: 'none' 
        } 
      });
      elements.push({ 
        type: 'path', 
        attrs: { 
          d: `M${size*0.5},${size*0.525} L${size*0.5},${size*0.6} L${size*0.525},${size*0.575}`, 
          fill: '#FF69B4' 
        } 
      });
    } else if (expression === 'sleepy') {
      elements.push({ 
        type: 'path', 
        attrs: { 
          d: `M${size*0.45},${size*0.65} Q${size*0.5},${size*0.7} ${size*0.55},${size*0.65}`, 
          stroke: '#000000', 
          'stroke-width': '1', 
          fill: 'none' 
        } 
      });
    }

    // Add accessories
    if (accessories.includes('collar')) {
      elements.push({ 
        type: 'rect', 
        attrs: { 
          x: `${size*0.475}`, 
          y: `${size*0.5}`, 
          width: `${size*0.05}`, 
          height: `${size*0.02}`, 
          fill: '#000000' 
        } 
      });
    }

    if (accessories.includes('hat')) {
      elements.push({ 
        type: 'polygon', 
        attrs: { 
          points: `${size*0.45},${size*0.25} ${size*0.55},${size*0.25} ${size*0.525},${size*0