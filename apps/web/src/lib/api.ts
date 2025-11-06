import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/auth/login';
    }
    return Promise.reject(error);
  }
);

export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  register: (data: { email: string; password: string; full_name: string }) =>
    api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
};

export const storesApi = {
  getTrending: (params?: any) => api.get('/stores/trending', { params }),
  getById: (id: string) => api.get(`/stores/${id}`),
  search: (query: string, params?: any) =>
    api.get('/stores/search', { params: { q: query, ...params } }),
  analyze: (domain: string) => api.post('/stores/analyze', { domain }),
};

export const usersApi = {
  getProfile: () => api.get('/users/me'),
  updateProfile: (data: any) => api.patch('/users/me', data),
  getSavedStores: (params?: any) => api.get('/users/me/saved-stores', { params }),
  saveStore: (store_id: string, notes?: string) =>
    api.post('/users/me/saved-stores', { store_id, notes }),
  unsaveStore: (store_id: string) => api.delete(`/users/me/saved-stores/${store_id}`),
  getUsage: () => api.get('/users/me/usage'),
};
