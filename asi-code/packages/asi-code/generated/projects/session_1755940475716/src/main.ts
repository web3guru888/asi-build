import { renderBarGraph } from './lib/data-visualizations';
import { initDemo } from './demo/init-demo';
import { createHeader } from './components/header';
import { createFooter } from './components/footer';
import { createGraphContainer } from './components/graph-container';

// Ensure DOM is fully loaded before manipulation
document.addEventListener('DOMContentLoaded', () => {
  try {
    // Inject header and footer
    const header = createHeader();
    const footer = createFooter();
    
    const headerContainer = document.getElementById('header');
    const footerContainer = document.getElementById('footer');
    
    if (!headerContainer || !footerContainer) {
      throw new Error("Required DOM elements 'header' or 'footer' not found in index.html");
    }
    
    headerContainer.appendChild(header);
    footerContainer.appendChild(footer);

    // Initialize demo data and render graph
    const { data, config } = initDemo();
    
    const graphContainerElement = createGraphContainer();
    const container = document.getElementById('graph-container');
    
    if (!container) {
      throw new Error("Required DOM element 'graph-container' not found in index.html");
    }
    
    container.appendChild(graphContainerElement);

    const svgElement = renderBarGraph(data, config);
    graphContainerElement.appendChild(svgElement);

  } catch (error) {
    console.error('Failed to initialize the application:', error instanceof Error ? error.message : error);
    // Create user-friendly error message in the UI
    const container = document.getElementById('graph-container');
    if (container) {
      const errorElement = document.createElement('div');
      errorElement.style.color = 'red';
      errorElement.style.padding = '1rem';
      errorElement.style.backgroundColor = '#ffebee';
      errorElement.style.border = '1px solid #ffcdd2';
      errorElement.style.borderRadius = '4px';
      errorElement.textContent = 'Error loading graph: Please check console for details.';
      container.appendChild(errorElement);
    }
  }
});

// Enable Hot Module Replacement in development (if supported)
if (import.meta.hot) {
  import.meta.hot.accept((module) => {
    if (module) {
      console.log('Main module updated - reloading graph...');
      // In a real HMR scenario, we'd selectively update components
      // For simplicity, we reload the window
      window.location.reload();
    }
  });
}