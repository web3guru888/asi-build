import { Dimensions } from '../lib/types';

/**
 * Configuration options for the footer element
 */
interface FooterOptions {
  containerId: string;
  position?: 'fixed' | 'absolute' | 'relative';
  bottom?: number;
  backgroundColor?: string;
  textColor?: string;
  fontSize?: string;
  padding?: string;
}

/**
 * Default dimensions for the footer
 */
const DEFAULT_FOOTER_DIMENSIONS: Dimensions = {
  width: 0,
  height: 60,
};

/**
 * Default configuration for the footer
 */
const DEFAULT_FOOTER_OPTIONS: Required<FooterOptions> = {
  containerId: 'footer',
  position: 'fixed',
  bottom: 0,
  backgroundColor: '#f8f9fa',
  textColor: '#6c757d',
  fontSize: '14px',
  padding: '16px',
};

/**
 * Footer class responsible for creating and managing the footer section
 * Displays attribution and helpful information about the SVG graph visualization
 */
export class Footer {
  private options: Required<FooterOptions>;
  private element: HTMLElement | null = null;
  private dimensions: Dimensions = { ...DEFAULT_FOOTER_DIMENSIONS };

  constructor(options: FooterOptions) {
    this.options = { ...DEFAULT_FOOTER_OPTIONS, ...options };
    this.initialize();
  }

  /**
   * Initializes the footer by creating the element and appending it to the DOM
   */
  private initialize(): void {
    try {
      this.createElement();
      this.setStyle();
      this.renderContent();
      this.observeContainer();
    } catch (error) {
      console.error('Failed to initialize Footer:', error);
      throw new Error(`Footer initialization failed: ${(error as Error).message}`);
    }
  }

  /**
   * Creates the footer DOM element
   */
  private createElement(): void {
    const container = document.getElementById(this.options.containerId);
    if (!container) {
      throw new Error(`Container with id "${this.options.containerId}" not found`);
    }

    this.element = document.createElement('footer');
    this.element.id = `${this.options.containerId}-element`;
    container.appendChild(this.element);
  }

  /**
   * Applies styles to the footer element
   */
  private setStyle(): void {
    if (!this.element) return;

    Object.assign(this.element.style, {
      position: this.options.position,
      bottom: `${this.options.bottom}px`,
      width: '100%',
      height: `${this.dimensions.height}px`,
      backgroundColor: this.options.backgroundColor,
      color: this.options.textColor,
      fontSize: this.options.fontSize,
      padding: this.options.padding,
      textAlign: 'center',
      borderTop: '1px solid #e9ecef',
      boxSizing: 'border-box',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    });
  }

  /**
   * Renders the content of the footer
   */
  private renderContent(): void {
    if (!this.element) return;

    this.element.innerHTML = `
      <div>
        <span>Custom SVG Graph Visualization | Powered by ASI:One</span>
      </div>
    `;
  }

  /**
   * Observes the container size changes and updates footer width accordingly
   */
  private observeContainer(): void {
    const container = document.getElementById(this.options.containerId);
    if (!container) return;

    // Update dimensions when container resizes
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        this.dimensions.width = entry.contentRect.width;
      }
    });

    resizeObserver.observe(container);
  }

  /**
   * Updates the footer content with new text
   * @param text - New text to display in the footer
   */
  public updateContent(text: string): void {
    if (!this.element) return;

    const span = this.element.querySelector('span');
    if (span) {
      span.textContent = text;
    } else {
      this.renderContent();
    }
  }

  /**
   * Updates the footer styles
   * @param styles - Partial footer options to update
   */
  public updateStyle(styles: Partial<Omit<FooterOptions, 'containerId'>>): void {
    this.options = { ...this.options, ...styles };
    this.setStyle();
  }

  /**
   * Destroys the footer instance and cleans up the DOM
   */
  public destroy(): void {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
      this.element = null;
    }
  }

  /**
   * Gets the current dimensions of the footer
   * @returns The current dimensions
   */
  public getDimensions(): Dimensions {
    return { ...this.dimensions };
  }
}