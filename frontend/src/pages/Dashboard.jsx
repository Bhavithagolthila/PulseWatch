import {useCallback, useEffect, useState} from 'react';
import {Link} from 'react-router-dom';
import {
  Plus,
  ArrowUpRight,
  Clock3,
  Activity,
  Server,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
} from 'lucide-react';
import {AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell} from 'recharts';
import api from '../services/api';
import StatusBadge from '../components/StatusBadge';
import MonitorForm from '../components/MonitorForm';

const COLORS = {HEALTHY: 'var(--ok)', DEGRADED: 'var(--warn)', DOWN: 'var(--bad)', PENDING: 'var(--faint)'};
const REFRESH_MS = 15000;

function StatCard({label, value, hint, Icon, tone}) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <span>{label}</span>
        <Icon size={17} className={tone ? `tone-${tone}` : undefined} />
      </div>
      <strong>{value}</strong>
      <small>{hint}</small>
    </div>
  );
}

function ResponseChart({data}) {
  if (!data.length) {
    return (
      <div className="empty-chart">
        <Activity size={25} />
        <b>No response data yet</b>
        <span>Run a check to start building your latency history.</span>
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={230}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="latencyFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.28} />
            <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="time" tickLine={false} axisLine={false} tick={{fill: 'var(--muted)', fontSize: 11}} />
        <YAxis tickLine={false} axisLine={false} tick={{fill: 'var(--muted)', fontSize: 11}} width={45} />
        <Tooltip
          formatter={(value) => [`${value} ms`, 'Avg response']}
          contentStyle={{background: 'var(--panel)', border: '1px solid var(--border-strong)', borderRadius: 9, color: 'var(--text)'}}
        />
        <Area type="monotone" dataKey="response_time_ms" stroke="var(--accent)" strokeWidth={2} fill="url(#latencyFill)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [monitors, setMonitors] = useState([]);
  const [trend, setTrend] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      // /monitors already includes each monitor's last_check, so no per-monitor requests are needed.
      const [s, m, t, i] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/monitors'),
        api.get('/dashboard/response-times'),
        api.get('/incidents?limit=5'),
      ]);
      setStats(s.data);
      setMonitors(m.data);
      setTrend(
        t.data.map((x) => ({
          ...x,
          time: new Date(x.time).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}),
        })),
      );
      setIncidents(i.data);
      setError('');
    } catch {
      setError('Could not connect to the API. Start the backend and check VITE_API_URL.');
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => clearInterval(id);
  }, [load]);

  async function save(data) {
    await api.post('/monitors', data);
    setShowForm(false);
    load();
  }

  const avg = stats?.average_response_time_ms;
  const availability = stats?.availability_percent;
  const distribution = [
    {name: 'Healthy', value: stats?.healthy || 0, color: COLORS.HEALTHY},
    {name: 'Degraded', value: stats?.degraded || 0, color: COLORS.DEGRADED},
    {name: 'Down', value: stats?.down || 0, color: COLORS.DOWN},
    {name: 'Pending', value: stats?.pending || 0, color: COLORS.PENDING},
  ];

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">MONITORING / OVERVIEW</span>
          <h1>System overview</h1>
          <p>Your API health at a glance. Updated every 15 seconds.</p>
        </div>
        <div className="heading-actions">
          <button className="btn secondary" onClick={load}>
            <RefreshCw size={15} /> Refresh
          </button>
          <button className="btn primary" onClick={() => setShowForm(true)}>
            <Plus size={17} /> Add API
          </button>
        </div>
      </div>
      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}

      <div className="stat-grid">
        <StatCard
          label="Total monitors"
          value={stats?.total_monitors ?? '—'}
          hint="Registered endpoints"
          Icon={Server}
          tone="neutral"
        />
        <StatCard
          label="Healthy"
          value={stats?.healthy ?? '—'}
          hint="Current monitor status"
          Icon={CheckCircle2}
          tone="green"
        />
        <StatCard
          label="Degraded"
          value={stats?.degraded ?? '—'}
          hint="Current monitor status"
          Icon={AlertTriangle}
          tone="amber"
        />
        <StatCard label="Down" value={stats?.down ?? '—'} hint="Current monitor status" Icon={XCircle} tone="red" />
        <StatCard label="Avg. response" value={avg == null ? '—' : `${avg} ms`} hint="Last 24 hours" Icon={Clock3} />
        <StatCard
          label="Availability"
          value={availability == null ? '—' : `${availability}%`}
          hint="Last 24 hours"
          Icon={Activity}
        />
      </div>

      <div className="dashboard-grid">
        <section className="panel chart-panel">
          <div className="panel-head">
            <div>
              <h3>Response time</h3>
              <p>Average latency per 30 minutes · last 24 hours</p>
            </div>
            <span className="chart-legend">
              <i /> Response (ms)
            </span>
          </div>
          <ResponseChart data={trend} />
        </section>

        <section className="panel health-panel">
          <div className="panel-head">
            <div>
              <h3>Service health</h3>
              <p>Latest status by endpoint</p>
            </div>
          </div>
          <div className="donut-wrap">
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={distribution}
                  dataKey="value"
                  innerRadius={57}
                  outerRadius={77}
                  paddingAngle={4}
                  stroke="none"
                >
                  {distribution.map((d) => (
                    <Cell key={d.name} fill={d.color} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="donut-center">
              <b>{stats?.total_monitors ?? 0}</b>
              <span>services</span>
            </div>
          </div>
          <div className="health-legend">
            {distribution.map((d) => (
              <div key={d.name}>
                <i style={{background: d.color}} />
                {d.name}
                <b>{d.value}</b>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="panel table-panel">
        <div className="panel-head">
          <div>
            <h3>Monitored services</h3>
            <p>Live status across your endpoints</p>
          </div>
          <Link to="/monitors" className="text-link">
            View all <ArrowUpRight size={14} />
          </Link>
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
              </tr>
            </thead>
            <tbody>
              {monitors.slice(0, 6).map((m) => (
                <tr key={m.id}>
                  <td>
                    <Link className="service-name" to={`/monitors/${m.id}`}>
                      {m.name}
                    </Link>
                    <small className="url-cell">{m.url}</small>
                  </td>
                  <td>
                    <StatusBadge status={m.latest_status} />
                  </td>
                  <td className="muted">
                    {m.last_check ? new Date(m.last_check.checked_at).toLocaleString() : 'Never'}
                  </td>
                  <td>{m.last_check?.response_time_ms == null ? '—' : `${m.last_check.response_time_ms} ms`}</td>
                  <td>{m.monitoring_interval}s</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!monitors.length && (
            <div className="empty-state">
              <Server size={24} />
              <b>No monitors configured</b>
              <span>Add an endpoint to begin tracking uptime and latency.</span>
              <button className="btn primary" onClick={() => setShowForm(true)}>
                <Plus size={15} /> Add your first API
              </button>
            </div>
          )}
        </div>
      </section>

      <section className="panel table-panel">
        <div className="panel-head">
          <div>
            <h3>Recent incidents</h3>
            <p>Latest degraded and failed checks</p>
          </div>
          <Link to="/incidents" className="text-link">
            All incidents <ArrowUpRight size={14} />
          </Link>
        </div>
        {incidents.length ? (
          <div className="incident-list">
            {incidents.map((i) => (
              <div className="incident-row" key={i.id}>
                <span className={`incident-icon ${i.status.toLowerCase()}`}>
                  <AlertTriangle size={16} />
                </span>
                <div>
                  <b>
                    {i.monitor_name} reported {i.status.toLowerCase()}
                  </b>
                  <small>
                    {i.error_message || `HTTP ${i.http_status_code || '—'}`} · {new Date(i.checked_at).toLocaleString()}
                  </small>
                </div>
                <StatusBadge status={i.status} />
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-inline">
            <CheckCircle2 size={17} /> No incidents recorded in the latest results.
          </div>
        )}
      </section>

      {showForm && <MonitorForm onClose={() => setShowForm(false)} onSave={save} />}
    </>
  );
}
