import {describe, it, expect, vi, beforeEach} from 'vitest';
import {render, screen, fireEvent, waitFor} from '@testing-library/react';
import App from '../App';
import api from '../services/api';
import {clearToken, getToken} from '../services/auth';

vi.mock('../services/api', () => ({default: {get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn()}}));
// The signed-in screens fetch data; Recharts is not needed for these tests.
vi.mock('./Dashboard', () => ({default: () => <h1>Dashboard page</h1>}));

describe('Login gate', () => {
  beforeEach(() => {
    clearToken();
    vi.clearAllMocks();
    api.get.mockResolvedValue({data: {status: 'ok'}});
  });

  it('shows the login form instead of the app when signed out', () => {
    render(<App />);
    expect(screen.getByRole('button', {name: 'Sign in'})).toBeInTheDocument();
    expect(screen.queryByText('Dashboard page')).not.toBeInTheDocument();
  });

  it('shows the server error for a wrong password and stays signed out', async () => {
    api.post.mockRejectedValue({response: {status: 401, data: {detail: 'Incorrect username or password.'}}});
    render(<App />);
    fireEvent.change(screen.getByLabelText('Username'), {target: {value: 'owner'}});
    fireEvent.change(screen.getByLabelText('Password'), {target: {value: 'nope'}});
    fireEvent.click(screen.getByRole('button', {name: 'Sign in'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect username or password.');
    expect(getToken()).toBeNull();
  });

  it('stores the token and opens the app after a correct login, and signs out again', async () => {
    api.post.mockResolvedValue({data: {access_token: 'abc.def'}});
    render(<App />);
    fireEvent.change(screen.getByLabelText('Username'), {target: {value: 'owner'}});
    fireEvent.change(screen.getByLabelText('Password'), {target: {value: 'right'}});
    fireEvent.click(screen.getByRole('button', {name: 'Sign in'}));
    expect(await screen.findByText('Dashboard page')).toBeInTheDocument();
    expect(getToken()).toBe('abc.def');

    fireEvent.click(screen.getByRole('button', {name: 'Sign out'}));
    await waitFor(() => expect(screen.getByRole('button', {name: 'Sign in'})).toBeInTheDocument());
    expect(getToken()).toBeNull();
  });

  it('toggles and remembers the theme', async () => {
    api.post.mockResolvedValue({data: {access_token: 'abc.def'}});
    render(<App />);
    fireEvent.change(screen.getByLabelText('Username'), {target: {value: 'o'}});
    fireEvent.change(screen.getByLabelText('Password'), {target: {value: 'p'}});
    fireEvent.click(screen.getByRole('button', {name: 'Sign in'}));
    const toggle = await screen.findByRole('button', {name: /Switch to (light|dark) mode/});
    const before = document.documentElement.dataset.theme;
    fireEvent.click(toggle);
    expect(document.documentElement.dataset.theme).not.toBe(before);
    expect(localStorage.getItem('pulsewatch-theme')).toBe(document.documentElement.dataset.theme);
  });
});
