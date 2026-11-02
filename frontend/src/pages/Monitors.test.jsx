import {describe, it, expect, vi, beforeEach} from 'vitest';
import {render, screen, fireEvent} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import Monitors from './Monitors';
import api from '../services/api';

vi.mock('../services/api', () => ({default: {get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn()}}));

const monitors = [
  {
    id: 1,
    name: 'Alpha API',
    url: 'https://alpha.example.com',
    latest_status: 'HEALTHY',
    monitoring_interval: 300,
    enabled: true,
    last_check: null,
  },
  {
    id: 2,
    name: 'Beta API',
    url: 'https://beta.example.com',
    latest_status: 'DOWN',
    monitoring_interval: 60,
    enabled: false,
    last_check: null,
  },
];

describe('Monitors', () => {
  beforeEach(() => {
    api.get.mockReset();
    api.get.mockResolvedValue({data: monitors});
  });

  const open = () =>
    render(
      <MemoryRouter>
        <Monitors />
      </MemoryRouter>,
    );

  it('lists monitors and marks never-checked ones', async () => {
    open();
    expect(await screen.findByText('Alpha API')).toBeInTheDocument();
    expect(screen.getAllByText('Never')).toHaveLength(2);
    expect(screen.getByText(/paused/)).toBeInTheDocument();
  });

  it('filters by search text', async () => {
    open();
    await screen.findByText('Alpha API');
    fireEvent.change(screen.getByLabelText('Search monitors'), {target: {value: 'beta'}});
    expect(screen.queryByText('Alpha API')).not.toBeInTheDocument();
    expect(screen.getByText('Beta API')).toBeInTheDocument();
  });

  it('filters by status', async () => {
    open();
    await screen.findByText('Alpha API');
    fireEvent.change(screen.getByLabelText('Filter by status'), {target: {value: 'DOWN'}});
    expect(screen.queryByText('Alpha API')).not.toBeInTheDocument();
    expect(screen.getByText('Beta API')).toBeInTheDocument();
  });
});
