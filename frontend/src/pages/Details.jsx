import {useCallback, useEffect, useState} from 'react';
import {useParams, Link} from 'react-router-dom';
import {ArrowLeft, Play, Clock3} from 'lucide-react';
import api from '../services/api';
import {getErrorMessage} from '../services/errors';
import StatusBadge from '../components/StatusBadge';

export default function Details() {
  const {id} = useParams();
  const [monitor, setMonitor] = useState(null);
  const [history, setHistory] = useState([]);
  const [message, setMessage] = useState('');
  const [running, setRunning] = useState(false);

  const load = useCallback(async () => {
    try {
      const [m, h] = await Promise.all([api.get(`/monitors/${id}`), api.get(`/monitors/${id}/history`)]);
      setMonitor(m.data);
      setHistory(h.data);
    } catch (e) {
      setMessage(getErrorMessage(e, 'Monitor could not be loaded.'));
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function check() {
    setRunning(true);
    setMessage('Running check…');
    try {
      await api.post(`/monitors/${id}/check`);
      setMessage('Check saved.');
      await load();
    } catch (e) {
      setMessage(getErrorMessage(e, 'Check failed.'));
    } finally {
      setRunning(false);
    }
  }

  if (!monitor) {
    return (
      <div>
        {message || 'Loading monitor…'} <Link to="/monitors">Back to monitors</Link>
      </div>
    );
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <Link to="/monitors" className="back-link">
            <ArrowLeft size={15} /> All monitors
          </Link>
          <h1>{monitor.name}</h1>
          <p>{monitor.url}</p>
        </div>
        <button className="btn primary" onClick={check} disabled={running}>
          <Play size={15} /> {running ? 'Checking…' : 'Check now'}
        </button>
      </div>
      {message && (
        <div className="notice" role="status">
          {message}
        </div>
      )}
      <div className="detail-cards">
        <div className="stat-card">
          <small>Current status</small>
          <StatusBadge status={monitor.latest_status} />
        </div>
        <div className="stat-card">
          <small>Monitoring interval</small>
          <strong>{monitor.monitoring_interval}s</strong>
        </div>
        <div className="stat-card">
          <small>Monitoring</small>
          <strong>{monitor.enabled ? 'Enabled' : 'Paused'}</strong>
        </div>
      </div>
      <section className="panel table-panel">
        <div className="panel-head">
          <div>
            <h3>Health-check history</h3>
            <p>Latest {history.length} recorded checks</p>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>TIME</th>
                <th>STATUS</th>
                <th>HTTP</th>
                <th>RESPONSE TIME</th>
                <th>ERROR</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h) => (
                <tr key={h.id}>
                  <td>{new Date(h.checked_at).toLocaleString()}</td>
                  <td>
                    <StatusBadge status={h.status} />
                  </td>
                  <td>{h.http_status_code || '—'}</td>
                  <td>{h.response_time_ms == null ? '—' : `${h.response_time_ms} ms`}</td>
                  <td className="muted">{h.error_message || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!history.length && (
            <div className="empty-state">
              <Clock3 />
              No health checks have been recorded.
            </div>
          )}
        </div>
      </section>
    </>
  );
}
