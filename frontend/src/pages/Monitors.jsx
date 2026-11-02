import {useCallback, useEffect, useState} from 'react';
import {Link} from 'react-router-dom';
import {Plus, Search, Play, Trash2, Edit2, ExternalLink} from 'lucide-react';
import api from '../services/api';
import {getErrorMessage} from '../services/errors';
import StatusBadge from '../components/StatusBadge';
import MonitorForm from '../components/MonitorForm';

export default function Monitors() {
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('ALL');
  const [editing, setEditing] = useState(null);
  const [adding, setAdding] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    try {
      setItems((await api.get('/monitors')).data);
    } catch (e) {
      setMessage(getErrorMessage(e, 'Unable to load monitors. Is the backend running?'));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const q = query.toLowerCase();
  const visible = items.filter(
    (m) =>
      (m.name.toLowerCase().includes(q) || m.url.toLowerCase().includes(q)) &&
      (filter === 'ALL' || (m.latest_status || 'PENDING') === filter),
  );

  async function save(data) {
    const wasEditing = Boolean(editing);
    if (editing) await api.put(`/monitors/${editing.id}`, data);
    else await api.post('/monitors', data);
    setAdding(false);
    setEditing(null);
    setMessage(wasEditing ? 'Monitor updated.' : 'Monitor created.');
    load();
  }

  async function check(id) {
    setBusyId(id);
    try {
      await api.post(`/monitors/${id}/check`);
      setMessage('Health check completed.');
    } catch (e) {
      setMessage(getErrorMessage(e, 'Health check failed.'));
    } finally {
      setBusyId(null);
      load();
    }
  }

  async function remove(id) {
    if (!window.confirm('Delete this monitor and its check history?')) return;
    try {
      await api.delete(`/monitors/${id}`);
      setMessage('Monitor deleted.');
      load();
    } catch (e) {
      setMessage(getErrorMessage(e, 'Could not delete monitor.'));
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">MONITORING / ENDPOINTS</span>
          <h1>Monitored APIs</h1>
          <p>Manage endpoints and inspect their latest health.</p>
        </div>
        <button className="btn primary" onClick={() => setAdding(true)}>
          <Plus size={17} /> Add API
        </button>
      </div>
      {message && (
        <div className="notice" role="status">
          {message}
          <button onClick={() => setMessage('')} aria-label="Dismiss message">
            ×
          </button>
        </div>
      )}
      <section className="panel table-panel">
        <div className="toolbar">
          <div className="search-input">
            <Search size={16} />
            <input
              placeholder="Search by name or URL…"
              aria-label="Search monitors"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <select value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter by status">
            <option value="ALL">All statuses</option>
            <option>HEALTHY</option>
            <option>DEGRADED</option>
            <option>DOWN</option>
            <option>PENDING</option>
          </select>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>SERVICE</th>
                <th>STATUS</th>
                <th>LAST CHECK</th>
                <th>RESPONSE</th>
                <th>INTERVAL</th>
                <th>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((m) => (
                <tr key={m.id}>
                  <td>
                    <Link className="service-name" to={`/monitors/${m.id}`}>
                      {m.name}
                    </Link>
                    <small className="url-cell">
                      {m.url}
                      {!m.enabled && ' · paused'}
                    </small>
                  </td>
                  <td>
                    <StatusBadge status={m.latest_status} />
                  </td>
                  <td className="muted">
                    {m.last_check ? new Date(m.last_check.checked_at).toLocaleString() : 'Never'}
                  </td>
                  <td>{m.last_check?.response_time_ms == null ? '—' : `${m.last_check.response_time_ms} ms`}</td>
                  <td>{m.monitoring_interval}s</td>
                  <td>
                    <div className="row-actions">
                      <button
                        title="Check now"
                        aria-label={`Check ${m.name} now`}
                        disabled={busyId === m.id}
                        onClick={() => check(m.id)}
                      >
                        <Play size={15} />
                      </button>
                      <button title="Edit" aria-label={`Edit ${m.name}`} onClick={() => setEditing(m)}>
                        <Edit2 size={15} />
                      </button>
                      <button title="Delete" aria-label={`Delete ${m.name}`} onClick={() => remove(m.id)}>
                        <Trash2 size={15} />
                      </button>
                      <Link title="Details" aria-label={`Details for ${m.name}`} to={`/monitors/${m.id}`}>
                        <ExternalLink size={15} />
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!visible.length && (
            <div className="empty-state">
              {items.length ? 'No matching endpoints.' : 'No monitors yet. Click “Add API” to create one.'}
            </div>
          )}
        </div>
      </section>
      {(adding || editing) && (
        <MonitorForm
          initial={editing}
          onClose={() => {
            setAdding(false);
            setEditing(null);
          }}
          onSave={save}
        />
      )}
    </>
  );
}
