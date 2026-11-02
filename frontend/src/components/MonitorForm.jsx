import {useEffect, useState} from 'react';
import {X} from 'lucide-react';
import {getErrorMessage} from '../services/errors';

/** Client-side checks give instant feedback; the backend repeats them and is the real authority. */
export function validateMonitor(form) {
  let parsed;
  try {
    parsed = new URL(form.url);
  } catch {
    return 'Enter a full URL such as https://api.example.com/health.';
  }
  if (!['http:', 'https:'].includes(parsed.protocol)) return 'Use an HTTP or HTTPS URL.';
  if (form.name.trim().length < 2) return 'Name must contain at least 2 characters.';
  const interval = Number(form.monitoring_interval);
  if (!Number.isInteger(interval) || interval < 30 || interval > 86400) {
    return 'Interval must be between 30 and 86,400 seconds.';
  }
  return null;
}

export default function MonitorForm({initial, onClose, onSave}) {
  const [form, setForm] = useState({
    name: initial?.name || '',
    url: initial?.url || '',
    monitoring_interval: initial?.monitoring_interval || 300,
    enabled: initial?.enabled ?? true,
  });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape' && !busy) onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [busy, onClose]);

  const change = (e) => {
    const {name, type, checked, value} = e.target;
    setForm((current) => ({...current, [name]: type === 'checkbox' ? checked : value}));
  };

  async function submit(e) {
    e.preventDefault();
    setError('');
    const problem = validateMonitor(form);
    if (problem) {
      setError(problem);
      return;
    }
    setBusy(true);
    try {
      await onSave({...form, name: form.name.trim(), monitoring_interval: Number(form.monitoring_interval)});
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save monitor.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && !busy && onClose()}>
      <form className="modal" onSubmit={submit} role="dialog" aria-modal="true" aria-labelledby="monitor-form-title">
        <div className="modal-head">
          <div>
            <span className="eyebrow">MONITOR CONFIGURATION</span>
            <h2 id="monitor-form-title">{initial ? 'Edit monitor' : 'Add endpoint'}</h2>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} disabled={busy} aria-label="Close dialog">
            <X size={18} />
          </button>
        </div>
        <label>
          Monitor name
          <input
            name="name"
            value={form.name}
            onChange={change}
            placeholder="Production API"
            required
            maxLength="120"
            autoFocus
          />
        </label>
        <label>
          Endpoint URL
          <input
            name="url"
            value={form.url}
            onChange={change}
            placeholder="https://api.example.com/health"
            required
            inputMode="url"
          />
        </label>
        <label>
          Check interval <span className="muted">(seconds)</span>
          <input
            type="number"
            name="monitoring_interval"
            min="30"
            max="86400"
            step="1"
            value={form.monitoring_interval}
            onChange={change}
          />
        </label>
        <label className="toggle-row">
          <span>
            <b>Enable monitoring</b>
            <small>Run scheduled health checks for this endpoint.</small>
          </span>
          <input type="checkbox" name="enabled" checked={form.enabled} onChange={change} />
        </label>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="modal-actions">
          <button type="button" className="btn secondary" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button className="btn primary" disabled={busy}>
            {busy ? 'Saving…' : 'Save monitor'}
          </button>
        </div>
      </form>
    </div>
  );
}
