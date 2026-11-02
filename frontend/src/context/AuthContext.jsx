import {createContext, useCallback, useContext, useEffect, useMemo, useState} from 'react';
import api from '../services/api';
import {clearToken, getToken, LOGOUT_EVENT, setToken} from '../services/auth';

const AuthContext = createContext(null);

export function AuthProvider({children}) {
  const [token, setTokenState] = useState(getToken);

  useEffect(() => {
    const onLogout = () => setTokenState(null);
    window.addEventListener(LOGOUT_EVENT, onLogout);
    return () => window.removeEventListener(LOGOUT_EVENT, onLogout);
  }, []);

  const login = useCallback(async (username, password) => {
    const {data} = await api.post('/auth/login', {username, password});
    setToken(data.access_token);
    setTokenState(data.access_token);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setTokenState(null);
  }, []);

  const value = useMemo(() => ({isAuthenticated: Boolean(token), login, logout}), [token, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>');
  return value;
}
