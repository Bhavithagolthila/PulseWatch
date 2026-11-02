import {LogOut, Moon, Sun} from 'lucide-react';
import {useAuth} from '../context/AuthContext';
import {useTheme} from '../context/ThemeContext';
import Sidebar from './Sidebar';

export default function Layout({children}) {
  const {theme, toggle} = useTheme();
  const {logout} = useAuth();
  const next = theme === 'dark' ? 'light' : 'dark';
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main">
        <header className="topbar">
          <div className="crumb">
            <span>Workspace</span>
            <b>/</b> Reliability
          </div>
          <div className="top-actions">
            <button className="icon-btn" onClick={toggle} aria-label={`Switch to ${next} mode`} title={`Switch to ${next} mode`}>
              {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <button className="icon-btn" onClick={logout} aria-label="Sign out" title="Sign out">
              <LogOut size={17} />
            </button>
            <div className="avatar" aria-label="PulseWatch workspace">
              PW
            </div>
          </div>
        </header>
        <div className="page-content">{children}</div>
      </main>
    </div>
  );
}
