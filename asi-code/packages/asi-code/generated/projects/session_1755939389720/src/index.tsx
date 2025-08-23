import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

const render = () => {
  const rootElement = document.getElementById('root');
  if (!rootElement) {
    console.error('Failed to find the root element');
    return;
  }

  const root = ReactDOM.createRoot(rootElement);
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
};

// Check if the document is already loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', render);
} else {
  render();
}

// Enable Hot Module Replacement in development
if (import.meta.env.DEV && module.hot) {
  module.hot.accept('./App', () => {
    const NextApp = require('./App').default;
    const rootElement = document.getElementById('root');
    if (rootElement) {
      const root = ReactDOM.createRoot(rootElement);
      root.render(
        <React.StrictMode>
          <NextApp />
        </React.StrictMode>
      );
    }
  });
}