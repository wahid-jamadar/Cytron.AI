import React from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import useAuthStore from './store/authStore';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Onboarding from './pages/Onboarding';
import AdminPanel from './pages/AdminPanel';

import SessionTimer from './components/SessionTimer';

// Helper redirect to server-side Hub
const HubRedirect = () => {
  React.useEffect(() => {
    window.location.href = '/hub';
  }, []);
  return null;
};

// Private Route wrappers
const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
  const accessToken = useAuthStore((state) => state.accessToken);
  return accessToken ? <>{children}</> : <Navigate to="/login" replace />;
};

const AdminRoute = ({ children }: { children: React.ReactNode }) => {
  const { accessToken, user } = useAuthStore();
  const isAdmin = user?.roles.includes('ADMIN') || user?.roles.includes('SUPER_ADMIN') || user?.roles.includes('SUPPORT') || user?.roles.includes('READ_ONLY_ADMIN');
  
  if (!accessToken) return <Navigate to="/login" replace />;
  if (!isAdmin) return <HubRedirect />;
  return <>{children}</>;
};

export default function App() {
  const accessToken = useAuthStore((state) => state.accessToken);

  return (
    <Router>
      <SessionTimer />
      <Routes>
        {/* Auth routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />

        {/* Workspace routes */}
        <Route
          path="/onboarding"
          element={
            <PrivateRoute>
              <Onboarding />
            </PrivateRoute>
          }
        />

        {/* Administration routes */}
        <Route
          path="/admin"
          element={
            <AdminRoute>
              <AdminPanel />
            </AdminRoute>
          }
        />

        {/* Catch-all */}
        <Route path="*" element={accessToken ? <HubRedirect /> : <Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
}
export { App };