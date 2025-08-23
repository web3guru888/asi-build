import { useState, useEffect, useCallback } from 'react';

/**
 * Custom hook to fetch data from an API endpoint
 * Handles loading states, error states, and provides a refresh function
 * 
 * @param url - The API endpoint to fetch data from
 * @returns Object containing data, loading state, error state, and refresh function
 */
export const useFetchData = <T,>(url: string) => {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: T = await response.json();
      setData(result);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unknown error occurred');
      }
    } finally {
      setLoading(false);
    }
  }, [url]);

  useEffect(() => {
    if (!url) {
      setError('URL is required');
      setLoading(false);
      return;
    }
    
    fetchData();
  }, [fetchData, url]);

  return { data, loading, error, refresh: fetchData };
};