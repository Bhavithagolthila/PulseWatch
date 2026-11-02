import {BrowserRouter, Routes, Route} from 'react-router-dom';
import {AuthProvider, useAuth} from './context/AuthContext';
import {ThemeProvider} from './context/ThemeContext';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Monitors from './pages/Monitors';
import Details from './pages/Details';
import Incidents from './pages/Incidents';
import Alerts from './pages/Alerts';
import Login from './pages/Login';

function Gate() {
  const {isAuthenticated} = useAuth();
  if (!isAuthenticated) return <Login />;
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/monitors" element={<Monitors />} />
          <Route path="/monitors/:id" element={<Details />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/alerts" element={<Alerts />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Gate />
      </AuthProvider>
    </ThemeProvider>
  );
}
