import {useEffect, useState} from 'react';
import {Mail, Send} from 'lucide-react';
import api from '../services/api';
import {getErrorMessage} from '../services/errors';

// Show only the first letters of the address, e.g. ba•••@gmail.com, so screenshots do not leak it.
function maskEmail(email) {
  const [name, domain] = String(email || '').split('@');
  if (!domain) return 'your email';
  return `${name.slice(0, name.length > 2 ? 2 : 1)}•••@${domain}`;
}

export default function Alerts() {
  const [config, setConfig] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null); // {ok: boolean, text: string}

  useEffect(() => {
    api
      .get('/alerts/config')
      .then((response) => setConfig(response.data))
      .catch((e) => setLoadError(getErrorMessage(e, 'Unable to load alert settings.')));
  }, []);

  async function sendTest() {
    setBusy(true);
    setResult(null);
    try {
      const {data} = await api.post('/alerts/test');
      setResult({ok: true, text: `Test email sent to ${maskEmail(data.sent_to)}. Check your inbox (and spam folder).`});
    } catch (e) {
      setResult({ok: false, text: getErrorMessage(e, 'Could not send the test email.')});
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">MONITORING / ALERTS</span>
          <h1>Email alerts</h1>
          <p>Get an email when a monitor goes down, becomes degraded, or recovers.</p>
        </div>
      </div>
      <section className="panel alert-panel">
        <div className="alert-row">
          <Mail size={20} />
          <div>
            <b>{config?.configured ? 'Email alerts are on' : 'Email alerts are not set up'}</b>
            <small>
              {loadError ||
                (config === null
                  ? 'Loading…'
                  : config.configured
                    ? `Alerts are sent to ${maskEmail(config.recipient)}.`
                    : 'Set SMTP_HOST, ALERT_EMAIL_TO and the other SMTP_* values in backend/.env, then restart the backend.')}
            </small>
          </div>
          <button className="btn primary" onClick={sendTest} disabled={busy || !config?.configured}>
            <Send size={16} /> {busy ? 'Sending…' : 'Send test email'}
          </button>
        </div>
        {result && (
          <p className={result.ok ? 'notice-ok' : 'form-error'} role={result.ok ? 'status' : 'alert'}>
            {result.text}
          </p>
        )}
        <ul className="alert-rules">
          <li>An email is sent only when the status changes, not on every check.</li>
          <li>Down, degraded and recovered are separate emails.</li>
          <li>A first-ever check that is healthy sends nothing.</li>
        </ul>
      </section>
    </>
  );
}
