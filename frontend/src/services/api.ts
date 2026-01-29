/**
 * API client configuration for AuditEng V2 backend
 */
import axios, { AxiosInstance, AxiosError } from 'axios';

// Determine API URL based on environment
const getApiUrl = (): string => {
  // Check for env variable first
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  // Production detection by hostname
  if (typeof window !== 'undefined' && window.location.hostname.includes('railway.app')) {
    return 'https://humble-warmth-production-e0c9.up.railway.app';
  }
  // Default for local development
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiUrl();

// Create axios instance with default config
export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to login
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export interface ApiError {
  detail: string;
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const apiError = error.response?.data as ApiError;
    return apiError?.detail || error.message;
  }
  return 'An unexpected error occurred';
}

export default api;
