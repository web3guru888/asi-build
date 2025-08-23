import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook that uses ResizeObserver to monitor element size changes
 * Provides width, height, and the observed element reference
 * Automatically cleans up observer on unmount
 * 
 * @param options Optional configuration for ResizeObserver behavior
 * @returns Object containing ref, width, and height
 */
export const useResizeObserver = <T extends HTMLElement = HTMLElement>(
  options?: ResizeObserverOptions
) => {
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({
    width: 0,
    height: 0,
  });
  const [node, setNode] = useState<T | null>(null);
  const resizeObserver = useRef<ResizeObserver | null>(null);

  // Cleanup function to disconnect observer
  const disconnectObserver = useCallback(() => {
    if (resizeObserver.current) {
      resizeObserver.current.disconnect();
      resizeObserver.current = null;
    }
  }, []);

  // Initialize or update observer when node or options change
  useEffect(() => {
    if (!node) return;

    disconnectObserver();

    resizeObserver.current = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.target === node) {
          const { width, height } = entry.contentRect;
          setDimensions({ width, height });
        }
      }
    });

    resizeObserver.current.observe(node, options);

    // Cleanup on unmount or dependency change
    return () => {
      disconnectObserver();
    };
  }, [node, options, disconnectObserver]);

  // Callback ref to set the observed element
  const ref = useCallback((element: T | null) => {
    setNode(element);
  }, []);

  return {
    ref,
    width: dimensions.width,
    height: dimensions.height,
    node,
  };
};

/**
 * Configuration options for ResizeObserver
 */
export interface ResizeObserverOptions {
  box?: 'border-box' | 'content-box' | 'device-pixel-content-box';
}