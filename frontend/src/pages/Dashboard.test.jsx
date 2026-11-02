import {describe, it, expect, vi, beforeEach} from 'vitest';
import {render, screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import Dashboard from './Dashboard';
import api from '../services/api';

vi.mock('../services/api', () => ({default: {get: vi.fn(), post: vi.fn()}}));

const responses = {
  '/dashboard/stats': {
    total_monitors: 2,
    healthy: 1,
    degraded: 1,
    down: 0,
    pending: 0,
    average_response_time_ms: 82,
    availability_percent: 50,
  },
  '/monitors': [
    {
      id: 1,
      name: 'Example API',
      url: 'https://example.com',
      latest_status: 'HEALTHY',
      monitoring_interval: 300,
      enabled: true,
      last_check: {id: 9, checked_at: new Date().toISOString(), response_time_ms: 34.5, status: 'HEALTHY'},
    },
  ],
  '/dashboard/response-times': [],
  '/incidents?limit=5': [
    {
      id: 3,
      monitored_api_id: 1,
      monitor_name: 'Billing API',
      status: 'DEGRADED',
      http_status_code: 503,
      error_message: null,
      checked_at: new Date().toISOString(),
    },
  ],
};

// Dashboard uses <Link>, which only works inside a Router.
const renderDashboard = () =>
  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );

describe('Dashboard', () => {
  beforeEach(() => {
    api.get.mockReset();
    api.get.mockImplementation((path) => Promise.resolve({data: responses[path] ?? []}));
  });

  it('renders backend-derived metrics, monitors and incidents', async () => {
    renderDashboard();
    expect(await screen.findByText('System overview')).toBeInTheDocument();
    expect(await screen.findByText('Example API')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText('82 ms')).toBeInTheDocument();
    expect(screen.getByText('34.5 ms')).toBeInTheDocument(); // from last_check, no extra requests
    expect(screen.getByText('Billing API reported degraded')).toBeInTheDocument();
  });

  it('makes one request per endpoint, not one per monitor', async () => {
    renderDashboard();
    await screen.findByText('Example API');
    expect(api.get).toHaveBeenCalledTimes(4);
    expect(api.get).not.toHaveBeenCalledWith(expect.stringContaining('/history'));
  });

  it('shows an error banner when the API is unreachable', async () => {
    api.get.mockRejectedValue(new Error('Network Error'));
    renderDashboard();
    expect(await screen.findByRole('alert')).toHaveTextContent(/Could not connect to the API/);
  });
});
