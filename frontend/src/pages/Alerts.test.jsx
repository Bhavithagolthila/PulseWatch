import {describe, it, expect, vi, beforeEach} from 'vitest';
import {render, screen, fireEvent} from '@testing-library/react';
import Alerts from './Alerts';
import api from '../services/api';

vi.mock('../services/api', () => ({default: {get: vi.fn(), post: vi.fn()}}));

describe('Alerts page', () => {
  beforeEach(() => vi.clearAllMocks());

  it('disables the test button and explains setup when email is not configured', async () => {
    api.get.mockResolvedValue({data: {configured: false, recipient: null}});
    render(<Alerts />);
    expect(await screen.findByText('Email alerts are not set up')).toBeInTheDocument();
    expect(screen.getByRole('button', {name: /Send test email/})).toBeDisabled();
  });

  it('sends a test email and reports success', async () => {
    api.get.mockResolvedValue({data: {configured: true, recipient: 'me@example.com'}});
    api.post.mockResolvedValue({data: {sent_to: 'me@example.com'}});
    render(<Alerts />);
    const button = await screen.findByRole('button', {name: /Send test email/});
    await vi.waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    expect(await screen.findByRole('status')).toHaveTextContent('Test email sent to me@example.com');
    expect(api.post).toHaveBeenCalledWith('/alerts/test');
  });

  it('shows the SMTP error when sending fails', async () => {
    api.get.mockResolvedValue({data: {configured: true, recipient: 'me@example.com'}});
    api.post.mockRejectedValue({response: {status: 502, data: {detail: 'Could not send email: SMTPAuthenticationError: bad login'}}});
    render(<Alerts />);
    const button = await screen.findByRole('button', {name: /Send test email/});
    await vi.waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    expect(await screen.findByRole('alert')).toHaveTextContent('SMTPAuthenticationError');
  });
});
