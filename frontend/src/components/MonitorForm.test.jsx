import {describe, it, expect, vi} from 'vitest';
import {render, screen, fireEvent, waitFor} from '@testing-library/react';
import MonitorForm, {validateMonitor} from './MonitorForm';

const valid = {name: 'My API', url: 'https://example.com/health', monitoring_interval: 300};

describe('validateMonitor', () => {
  it('accepts a valid monitor', () => expect(validateMonitor(valid)).toBeNull());
  it('rejects non-http URLs', () =>
    expect(validateMonitor({...valid, url: 'ftp://example.com'})).toMatch(/HTTP or HTTPS/));
  it('rejects text that is not a URL', () => expect(validateMonitor({...valid, url: 'example'})).toMatch(/full URL/));
  it('rejects short names', () => expect(validateMonitor({...valid, name: ' a '})).toMatch(/at least 2/));
  it('rejects out-of-range intervals', () => {
    expect(validateMonitor({...valid, monitoring_interval: 5})).toMatch(/between 30 and 86,400/);
    expect(validateMonitor({...valid, monitoring_interval: 1.5})).toMatch(/between 30 and 86,400/);
  });
});

describe('MonitorForm', () => {
  const fill = (name, url) => {
    fireEvent.change(screen.getByLabelText(/Monitor name/), {target: {name: 'name', value: name}});
    fireEvent.change(screen.getByLabelText(/Endpoint URL/), {target: {name: 'url', value: url}});
  };

  it('does not call onSave when validation fails', () => {
    const onSave = vi.fn();
    render(<MonitorForm onClose={() => {}} onSave={onSave} />);
    fill('My API', 'ftp://example.com');
    fireEvent.submit(screen.getByRole('dialog'));
    expect(screen.getByRole('alert')).toHaveTextContent('Use an HTTP or HTTPS URL.');
    expect(onSave).not.toHaveBeenCalled();
  });

  it('submits trimmed values', async () => {
    const onSave = vi.fn().mockResolvedValue();
    render(<MonitorForm onClose={() => {}} onSave={onSave} />);
    fill('  My API  ', 'https://example.com');
    fireEvent.submit(screen.getByRole('dialog'));
    await waitFor(() => expect(onSave).toHaveBeenCalled());
    expect(onSave.mock.calls[0][0]).toMatchObject({
      name: 'My API',
      url: 'https://example.com',
      monitoring_interval: 300,
    });
  });

  it('shows backend validation errors as text instead of crashing', async () => {
    const error = {response: {data: {detail: [{msg: 'Value error, URL is not allowed.'}]}}};
    render(<MonitorForm onClose={() => {}} onSave={vi.fn().mockRejectedValue(error)} />);
    fill('My API', 'https://example.com');
    fireEvent.submit(screen.getByRole('dialog'));
    expect(await screen.findByRole('alert')).toHaveTextContent('URL is not allowed.');
  });
});
