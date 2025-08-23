import { Dimensions } from '../lib/types';

/**
 * Creates and manages the header section of the webpage
 * Contains the main title and description for the SVG graph visualization demo
 */
export class Header {
  private container: HTMLElement | null = null;
  private title: string;
  private subtitle: string;

  /**
   * Initialize the Header component
   * @param title - Main title text
   * @param subtitle - Subtitle/description text
   */
  constructor(title: string = 'Custom SVG Graph Visualizations', subtitle: string = 'Interactive data visualizations using vanilla TypeScript and SVG') {
    this.title = title;
    this.subtitle = subtitle;
  }

  /**
   * Renders the header HTML structure
   * @returns The rendered header element
   */
  public render(): HTMLElement {
    this.container = document.createElement('header');
    this.container.className = 'graph-header';
    
    const titleElement = document.createElement('h1');
    titleElement.className = 'header-title';
    titleElement.textContent = this.title;
    
    const subtitleElement = document.createElement('p');
    subtitleElement.className = 'header-subtitle';
    subtitleElement.textContent = this.subtitle;
    
    this.container.appendChild(titleElement);
    this.container.appendChild(subtitleElement);
    
    return this.container;
  }

  /**
   * Mounts the header to a target element
   * @param target - The parent element to mount the header to
   * @throws Error if target element is not found
   */
  public mount(target: string | HTMLElement): void {
    const parent = typeof target === 'string' 
      ? document.querySelector(target)
      : target;
      
    if (!parent) {
      throw new Error(`Target element '${target}' not found for header mounting.`);
    }
    
    try {
      const headerElement = this.render();
      parent.appendChild(headerElement);
    } catch (error) {
      throw new Error(`Failed to mount header: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Updates the header content dynamically
   * @param title - New title text
   * @param subtitle - New subtitle text
   */
  public update(title?: string, subtitle?: string): void {
    if (this.container) {
      if (title) {
        this.title = title;
        const titleElement = this.container.querySelector('.header-title');
        if (titleElement) {
          titleElement.textContent = title;
        }
      }
      
      if (subtitle) {
        this.subtitle = subtitle;
        const subtitleElement = this.container.querySelector('.header-subtitle');
        if (subtitleElement) {
          subtitleElement.textContent = subtitle;
        }
      }
    }
  }

  /**
   * Removes the header from the DOM
   */
  public destroy(): void {
    if (this.container && this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
      this.container = null;
    }
  }

  /**
   * Gets the calculated dimensions of the header
   * @returns Dimensions object with width and height
   */
  public getDimensions(): Dimensions {
    if (!this.container) {
      this.render(); // Ensure element exists before measuring
    }
    
    return {
      width: this.container ? this.container.offsetWidth : 0,
      height: this.container ? this.container.offsetHeight : 0
    };
  }
}

/**
 * Default function to create and mount header
 * @param target - Target element to mount the header
 * @param title - Optional custom title
 * @param subtitle - Optional custom subtitle
 * @returns Header instance
 */
export function createHeader(target: string | HTMLElement, title?: string, subtitle?: string): Header {
  const header = new Header(title, subtitle);
  header.mount(target);
  return header;
}