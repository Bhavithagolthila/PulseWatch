import {useCallback, useEffect, useState} from 'react';
import {Link} from 'react-router-dom';
import {AlertTriangle, RefreshCw} from 'lucide-react';
import api from '../services/api';
import {getErrorMessage} from '../services/errors';
import StatusBadge from '../components/StatusBadge';

export default function Incidents() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems((await api.get('/incidents')).data);
      setError('');
    } catch (e) {
      setError(getErrorMessage(e, 'Unable to load incidents. Check that the API is running.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">MONITORING / EVENTS</span>
          <h1>Incidents</h1>
          <p>Degraded responses and unreachable endpoints.</p>
        </div>
        <button className="btn secondary" onClick={load} disabled={loading}>
          <RefreshCw size={15} /> {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>
      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}
      <section className="panel table-panel">
        <div className="panel-head">
          <div>
            <h3>Incident history</h3>
            <p>{items.length} recorded events</p>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>MONITOR</th>
                <th>TIME</th>
                <th>STATUS</th>
                <th>HTTP</th>
                <th>LATENCY</th>
                <th>DETAIL</th>
              </tr>
            </thead>
            <tbody>
              {items.map((i) => (
                <tr key={i.id}>
                  <td>
                    <Link className="service-name" to={`/monitors/${i.monitored_api_id}`}>
                      {i.monitor_name}
                    </Link>
                  </td>
                  <td>{new Date(i.checked_at).toLocaleString()}</td>
                  <td>
                    <StatusBadge status={i.status} />
                  </td>
                  <td>{i.http_status_code || '—'}</td>
                  <td>{i.response_time_ms == null ? '—' : `${i.response_time_ms} ms`}</td>
                  <td className="muted">{i.error_message || 'Unsuccessful HTTP response'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {loading ? (
            <div className="empty-state">Loading incident history…</div>
          ) : (
            !items.length &&
            !error && (
              <div className="empty-state">
                <AlertTriangle size={23} />
                <b>No incidents</b>
                <span>Failed or degraded checks will appear here.</span>
              </div>
            )
          )}
        </div>
      </section>
    </>
  );
}
