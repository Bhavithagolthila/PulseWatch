import axios from 'axios';
import {clearToken, getToken, LOGOUT_EVENT} from './auth';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 12000,
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // A 401 anywhere except the login form itself means the token is missing or expired.
    if (error.response?.status === 401 && !String(error.config?.url).includes('/auth/login')) {
      clearToken();
      window.dispatchEvent(new Event(LOGOUT_EVENT));
    }
    return Promise.reject(error);
  },
);

export default api;
