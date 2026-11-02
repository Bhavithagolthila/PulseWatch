import {useEffect, useState} from 'react';
import {Activity, LayoutDashboard, Server, AlertTriangle, Bell, Radio, WifiOff} from 'lucide-react';
import {NavLink} from 'react-router-dom';
import api from '../services/api';

const links = [
  ['/', 'Overview', LayoutDashboard],
  ['/monitors', 'Monitors', Server],
  ['/incidents', 'Incidents', AlertTriangle],
  ['/alerts', 'Alerts', Bell],
];

// Ask the backend whether it is up, so the sidebar never claims "active" while the API is down.
function useApiOnline() {
  const [online, setOnline] = useState(null); // null = still checking
  useEffect(() => {
    let cancelled = false;
    async function ping() {
      try {
        await api.get('/health');
        if (!cancelled) setOnline(true);
      } catch {
        if (!cancelled) setOnline(false);
      }
    }
    ping();
    const id = setInterval(ping, 30000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);
  return online;
}

export default function Sidebar() {
  const online = useApiOnline();
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">
          <Activity size={20} />
        </div>
        <div>
          <b>pulsewatch</b>
          <small>API MONITORING</small>
        </div>
      </div>
      <div className="workspace">
        <span className="pulse-dot" /> WORKSPACE <b>Personal</b>
      </div>
      <nav>
        {links.map(([to, label, Icon]) => (
          <NavLink key={to} to={to} end={to === '/'}>
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <div className="live-card" role="status">
          {online === false ? <WifiOff size={17} /> : <Radio size={17} />}
          <div>
            <b>{online === false ? 'API unreachable' : online ? 'API online' : 'Connecting…'}</b>
            <small>{online === false ? 'Start the backend' : 'Scheduled checks run in the backend'}</small>
          </div>
        </div>
        <small className="version">PULSEWATCH MVP · v1.0</small>
      </div>
    </aside>
  );
}
