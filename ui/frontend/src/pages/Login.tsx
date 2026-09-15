import React, { useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, AlertCircle, Eye, EyeOff } from 'lucide-react';
import cytronLogo from '../assets/Cytron.AI-Logo.png';
import useAuthStore from '../store/authStore';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const loginStore = useAuthStore((state) => state.login);
  const logoutStore = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  const location = useLocation();
  const isExpired = location.search.includes('expired=1');

  React.useEffect(() => {
    // Clear stale session on mount
    fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});
    logoutStore();
  }, [logoutStore]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to authenticate');
      }

      const data = await response.json();
      loginStore(data.user, data.access_token, data.refresh_token);
      
      const userRoles = data.user.roles || [];
      const isAdmin = userRoles.includes('ADMIN') || userRoles.includes('SUPER_ADMIN') || userRoles.includes('SUPPORT');

      if (!isAdmin) {
        window.location.href = '/hub';
      } else if (!data.user.preferences?.preferred_language) {
        navigate('/onboarding');
      } else {
        window.location.href = '/hub';
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative px-4">
      {/* Background aurora blurs */}
      <div className="absolute top-1/4 left-1/4 w-72 h-72 rounded-full bg-accentPurple filter blur-[100px] opacity-20 animate-pulse pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-72 h-72 rounded-full bg-accentBlue filter blur-[100px] opacity-20 pointer-events-none"></div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md glass-panel rounded-2xl relative z-10 border border-white/10 shadow-2xl bg-surface"
        style={{ padding: '32px 28px', boxSizing: 'border-box' }}
      >
        {/* Header / Branding */}
        <div className="flex flex-col items-center" style={{ marginBottom: '22px' }}>
          <img src={cytronLogo} alt="Cytron.AI" style={{ height: '48px', width: 'auto', marginBottom: '16px' }} className="object-contain" />
          <p className="text-textSecondary text-xs" style={{ marginTop: '6px' }}>Sign in to orchestrate your multi-agent workspace</p>
        </div>

        {isExpired && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-2 p-3 bg-amber-500/10 border border-amber-500/20 text-amber-500 rounded-lg text-sm"
            style={{ marginBottom: '16px' }}
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>Session expired due to inactivity. Please sign in again.</span>
          </motion.div>
        )}

        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 text-red-500 rounded-lg text-sm"
            style={{ marginBottom: '16px' }}
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </motion.div>
        )}

        <form onSubmit={handleSubmit} className="w-full flex flex-col" style={{ boxSizing: 'border-box' }}>
          {/* Email Group */}
          <div className="w-full flex flex-col" style={{ marginBottom: '14px' }}>
            <label className="block text-textSecondary text-xs font-semibold uppercase tracking-wider text-left" style={{ marginBottom: '6px' }}>
              Email Address
            </label>
            <div className="relative w-full">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-textMuted" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-white/5 border border-white/10 focus:border-accentPurple/50 rounded-lg focus:outline-none text-textPrimary text-sm transition-all focus:ring-1 focus:ring-accentPurple/50"
                style={{
                  height: '42px',
                  paddingLeft: '2.5rem',
                  paddingRight: '1rem',
                  boxSizing: 'border-box'
                }}
                placeholder="name@company.com"
              />
            </div>
          </div>

          {/* Password Group */}
          <div className="w-full flex flex-col">
            <label className="block text-textSecondary text-xs font-semibold uppercase tracking-wider text-left" style={{ marginBottom: '6px' }}>
              Password
            </label>
            <div className="relative w-full">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-textMuted" />
              <input
                type={showPassword ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white/5 border border-white/10 focus:border-accentPurple/50 rounded-lg focus:outline-none text-textPrimary text-sm transition-all focus:ring-1 focus:ring-accentPurple/50"
                style={{
                  height: '42px',
                  paddingLeft: '2.5rem',
                  paddingRight: '2.5rem',
                  boxSizing: 'border-box'
                }}
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-textMuted hover:text-textPrimary"
                style={{ padding: 0, border: 'none', background: 'none' }}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {/* Forgot Password Link */}
            <div className="w-full flex justify-end" style={{ marginTop: '6px' }}>
              <Link to="/forgot-password" className="text-accentPurple hover:text-accentPurple/80 text-xs font-semibold">
                Forgot password?
              </Link>
            </div>
          </div>

          {/* Sign In Button */}
          <button
            type="submit"
            disabled={loading}
            className="self-center bg-gradient-to-r from-[var(--accent)] to-[var(--accent-2)] hover:opacity-90 text-white font-semibold rounded-lg text-sm shadow-lg glow-btn transition-all flex items-center justify-center gap-2 cursor-pointer"
            style={{
              height: '42px',
              width: 'max-content',
              paddingLeft: '32px',
              paddingRight: '32px',
              marginTop: '10px',
              border: 'none',
              boxSizing: 'border-box'
            }}
          >
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        {/* Signup Link */}
        <div className="text-center text-xs text-textSecondary" style={{ marginTop: '24px' }}>
          Don't have an account?{' '}
          <Link to="/register" className="text-accentBlue hover:underline font-semibold">
            Create an account
          </Link>
        </div>
      </motion.div>
    </div>
  );
}

