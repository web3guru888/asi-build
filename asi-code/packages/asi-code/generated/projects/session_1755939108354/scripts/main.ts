import { generateDogSvg } from './utils/svg-generator';
import { DogAnimation } from './components/DogAnimation';

// Main application class
class DogWebsiteApp {
  private container: HTMLElement | null;
  private dogContainer: HTMLElement | null;
  private animation: DogAnimation | null;

  constructor() {
    this.container = null;
    this.dogContainer = null;
    this.animation = null;
    this.initialize();
  }

  private initialize(): void {
    // Wait for DOM to be fully loaded
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setupApp());
    } else {
      this.setupApp();
    }
  }

  private setupApp(): void {
    try {
      // Get main container
      this.container = document.querySelector('.container');
      if (!this.container) {
        throw new Error('Container element not found');
      }

      // Create and append hero section
      this.createHeroSection();

      // Create and append dog gallery section
      this.createDogGallery();

      // Initialize dog animation
      this.dogContainer = document.querySelector('#dog-animation-container');
      if (this.dogContainer) {
        this.animation = new DogAnimation(this.dogContainer);
        this.animation.start();
      }

      // Create and append info section
      this.createInfoSection();

      // Create and append footer
      this.createFooter();

      // Add event listeners
      this.addEventListeners();

      console.log('DogWebsiteApp initialized successfully');
    } catch (error) {
      console.error('Failed to initialize DogWebsiteApp:', error);
      this.showError('Failed to load the application. Please refresh the page.');
    }
  }

  private createHeroSection(): void {
    const hero = document.createElement('section');
    hero.className = 'hero';
    hero.innerHTML = `
      <div class="hero-content">
        <h1>Adopt a Furry Friend Today</h1>
        <p>Discover the joy of dog ownership with our custom illustrations and heartwarming stories</p>
        <button id="explore-btn" class="btn-primary">Explore Dog Breeds</button>
      </div>
      <div class="hero-image">
        ${generateDogSvg({
          type: 'sitting',
          colors: { body: '#8B4513', ears: '#A0522D' },
          size: 300
        })}
      </div>
    `;
    this.container?.appendChild(hero);
  }

  private createDogGallery(): void {
    const gallery = document.createElement('section');
    gallery.className = 'dog-gallery';
    gallery.innerHTML = `
      <h2>Beautiful Dog Illustrations</h2>
      <div class="gallery-grid" id="dog-gallery-container">
        <!-- Generated via JavaScript -->
      </div>
    `;
    this.container?.appendChild(gallery);

    const galleryContainer = document.querySelector('#dog-gallery-container');
    if (galleryContainer) {
      const dogTypes = ['sitting', 'running', 'sleeping', 'barking'] as const;
      const colors = [
        { body: '#8B4513', ears: '#A0522D' }, // Brown
        { body: '#D2B48C', ears: '#C19A6B' }, // Tan
        { body: '#000000', ears: '#333333' }, // Black
        { body: '#FFD700', ears: '#FFA500' }  // Golden
      ];

      // Generate 8 random dog SVGs
      for (let i = 0; i < 8; i++) {
        const dogType = dogTypes[i % dogTypes.length];
        const color = colors[Math.floor(Math.random() * colors.length)];
        
        const figure = document.createElement('figure');
        figure.className = 'gallery-item';
        figure.innerHTML = `
          ${generateDogSvg({ type: dogType, colors: color, size: 200 })}
          <figcaption>Dog illustration - ${dogType}</figcaption>
        `;
        galleryContainer.appendChild(figure);
      }
    }
  }

  private createInfoSection(): void {
    const info = document.createElement('section');
    info.className = 'info-section';
    info.innerHTML = `
      <div class="info-grid">
        <div class="info-card">
          <div class="info-icon">${generateDogSvg({ type: 'sitting', size: 60, colors: { body: '#696969', ears: '#2F4F4F' } })}</div>
          <h3>Why Adopt?</h3>
          <p>Dogs provide companionship, reduce stress, and encourage an active lifestyle. Adopting gives a deserving animal a second chance.</p>
        </div>
        <div class="info-card">
          <div class="info-icon">${generateDogSvg({ type: 'barking', size: 60, colors: { body: '#CD853F', ears: '#8B4513' } })}</div>
          <h3>Care Tips</h3>
          <p>Proper nutrition, regular vet visits, daily exercise, and lots of love are key to raising a happy, healthy dog.</p>
        </div>
        <div class="info-card">
          <div class="info-icon">${generateDogSvg({ type: 'sleeping', size: 60, colors: { body: '#F5DEB3', ears: '#DEB887' } })}</div>
          <h3>Training</h3>
          <p>Consistent positive reinforcement helps dogs learn commands and behaviors. Start early for best results.</p>
        </div>
      </div>
    `;
    this.container?.appendChild(info);
  }

  private createFooter(): void {
    const footer = document.createElement('footer');
    footer.className = 'footer';
    footer.innerHTML = `
      <div class="footer-content">
        <div class="footer-logo">
          ${generateDogSvg({ type: 'sitting', size: 80, colors: { body: '#4a4a4a', ears: '#2F2F2F' } })}
          <p>Dog Illustrations &copy; ${new Date().getFullYear()}</p>
        </div>
        <nav class="footer-nav">
          <ul>
            <li><a href="#about">About</a></li>
            <li><a href="#gallery">Gallery</a></li>
            <li><a href="#contact">Contact</a></li>
          </ul>
        </nav>
      </div>
    `;
    document.body.appendChild(footer);
  }

  private addEventListeners(): void {
    // Explore button scroll functionality
    const exploreBtn = document.querySelector('#explore-btn');
    if (exploreBtn) {
      exploreBtn.addEventListener('click', () => {
        const gallery = document.querySelector('.dog-gallery');
        if (gallery) {
          gallery.scrollIntoView({ behavior: 'smooth' });
        }
      });
    }

    // Handle window resize events
    window.addEventListener('resize', () => {
      this.handleResize();
    });
  }

  private handleResize(): void {
    // Restart animation on resize to ensure proper positioning
    if (this.animation) {
      this.animation.stop();
      this.animation.start();
    }
  }

  private showError(message: string): void {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.style.cssText = `
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      background-color: #ff4757;
      color: white;
      padding: 15px 30px;
      border-radius: 5px;
      z-index: 1000;
      text-align: center;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    errorDiv.textContent = message;
    document.body.appendChild(errorDiv);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (errorDiv.parentElement) {
        document.body.removeChild(errorDiv);
      }
    }, 5000);
  }
}

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  try {
    // eslint-disable-next-line no-new
    new DogWebsiteApp();
  } catch (error) {
    console.error('Critical error initializing application:', error);
  }
});

// Handle window load event
window.addEventListener('load', () => {
  // Additional initialization after all resources are loaded
  console.log('All resources loaded');
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
  console.warn('Unhandled promise rejection:', event.reason);
  event.preventDefault();
});

// Export for testing purposes (if needed)
if (typeof window !== 'undefined') {
  (window as any).DogWebsiteApp = DogWebsiteApp;
}