import axios from 'axios';
import { ChartData } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'https://api.example.com';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Fetches chart data from the API
 * @param endpoint - API endpoint to fetch data from
 * @returns Promise resolving to ChartData
 */
export const fetchChartData = async (endpoint: string): Promise<ChartData> => {
  try {
    const response = await apiClient.get<ChartData>(endpoint);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.message || error.message;
      throw new Error(`Failed to fetch chart data: ${message}`);
    }
    throw new Error('An unknown error occurred while fetching chart data');
  }
};

/**
 * Posts data to the API
 * @param endpoint - API endpoint to post data to
 * @param data - Data to be posted
 * @returns Promise resolving to the response data
 */
export const postChartData = async <T,>(endpoint: string, data: T): Promise<T> => {
  try {
    const response = await apiClient.post<T>(endpoint, data);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.message || error.message;
      throw new Error(`Failed to post data: ${message}`);
    }
    throw new Error('An unknown error occurred while posting data');
  }
};

/**
 * Updates data via PUT request
 * @param endpoint - API endpoint to update data at
 * @param data - Data to be updated
 * @returns Promise resolving to the response data
 */
export const updateChartData = async <T,>(endpoint: string, data: T): Promise<T> => {
  try {
    const response = await apiClient.put<T>(endpoint, data);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.message || error.message;
      throw new Error(`Failed to update data: ${message}`);
    }
    throw new Error('An unknown error occurred while updating data');
  }
};

/**
 * Deletes data via DELETE request
 * @param endpoint - API endpoint to delete data from
 * @returns Promise resolving when deletion is complete
 */
export const deleteChartData = async (endpoint: string): Promise<void> => {
  try {
    await apiClient.delete(endpoint);
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.message || error.message;
      throw new Error(`Failed to delete data: ${message}`);
    }
    throw new Error('An unknown error occurred while deleting data');
  }
};

/**
 * Generic GET request handler
 * @param endpoint - API endpoint to request
 * @returns Promise resolving to response data
 */
export const get = async <T,>(endpoint: string): Promise<T> => {
  try {
    const response = await apiClient.get<T>(endpoint);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.message || error.message;
      throw new Error(`Request failed: ${message}`);
    }
    throw new Error('An unknown error occurred during the request');
  }
};

export default apiClient;