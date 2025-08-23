import { renderLineGraph } from '../lib/data-visualizations';
import { Point, Dimensions } from '../lib/types/index';
import { selectElement } from '../lib/utils';
import { createHeader } from '../components/header';
import { createFooter } from '../components/footer';
import { createGraphContainer } from '../components/graph-container';
import { sampleTimeSeriesData, sampleScatterData, chartDimensions } from './sample-data';

/**
 * Initializes the demo application by rendering sample SVG graphs
 * and setting up the page structure with header and footer
 */
function initDemo(): void {
  try {
    // Get the root container for the app
    const appContainer = selectElement('#app');
    
    // Clear any existing content
    appContainer.innerHTML = '';

    // Create and append header
    const header = createHeader();
    appContainer.appendChild(header);

    // Create main content wrapper
    const mainWrapper = document.createElement('main');
    mainWrapper.style.padding = '20px';
    mainWrapper.style.maxWidth = '1200px';
    mainWrapper.style.margin = '0 auto';

    // Render time series line graph
    const lineGraphData: Point[] = sampleTimeSeriesData;
    const lineGraphContainer = createGraphContainer('Time Series Line Graph');
    const lineGraphSvg = renderLineGraph(lineGraphData, chartDimensions);
    lineGraphContainer.appendChild(lineGraphSvg);
    mainWrapper.appendChild(lineGraphContainer);

    // Render scatter plot graph
    const scatterData: Point[] = sampleScatterData;
    const scatterGraphContainer = createGraphContainer('Scatter Plot Graph');
    const scatterGraphSvg = renderLineGraph(scatterData, chartDimensions, { type: 'scatter' });
    scatterGraphContainer.appendChild(scatterGraphSvg);
    mainWrapper.appendChild(scatterGraphContainer);

    // Append main wrapper to app container
    appContainer.appendChild(mainWrapper);

    // Create and append footer
    const footer = createFooter();
    appContainer.appendChild(footer);
  } catch (error) {
    console.error('Failed to initialize demo:', error);
    const appContainer = selectElement('#app');
    appContainer.innerHTML = '<div style="color: red; padding: 20px;">Error loading demo: Unable to render visualizations</div>';
  }
}

/**
 * Ensures DOM is fully loaded before initializing the demo
 */
function onDomReady(): void {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDemo);
  } else {
    initDemo();
  }
}

// Initialize the demo when DOM is ready
onDomReady();

// Export for potential use in tests or other modules
export { initDemo };