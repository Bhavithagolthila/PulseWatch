// The login token lives in localStorage so a refresh keeps you signed in.
// It expires on the server (TOKEN_TTL_HOURS); an expired token triggers a logout on the next 401.
const KEY = 'pulsewatch-token';
export const LOGOUT_EVENT = 'pulsewatch:logout';

export function getToken() {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    localStorage.setItem(KEY, token);
  } catch {
    /* storage blocked: you will simply need to log in again after a refresh */
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
