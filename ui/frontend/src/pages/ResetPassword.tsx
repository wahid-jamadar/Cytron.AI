import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Lock, AlertCircle, CheckCircle, ArrowLeft, Key } from 'lucide-react';
import cytronLogo from '../assets/Cytron.AI-Logo.png';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const navigate = useNavigate();

  useEffect(() => {
    const tokenParam = searchParams.get('token');
    if (tokenParam) {
      setToken(tokenParam);
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
    if (!passwordRegex.test(newPassword)) {
      setError('Password must contain at least one uppercase letter, one lowercase letter, and one number');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: newPassword })
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Reset password failed');
      }

      setSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Verification failed. Token may be invalid or expired.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative px-4">
      {/* Background blurs */}
      <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-accentPurple filter blur-[100px] opacity-20 pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-accentBlue filter blur-[100px] opacity-20 pointer-events-none"></div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md glass-panel p-8 rounded-2xl relative z-10 border border-white/5 shadow-2xl"
      >
        <div className="flex flex-col items-center mb-8">
          <img src={cytronLogo} alt="Cytron.AI" style={{ height: '48px', width: 'auto', marginBottom: '16px' }} className="object-contain" />
          <h2 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">
            Reset Password
          </h2>
          <p className="text-gray-400 text-xs mt-1 text-center">
            Set your new credentials below. Remember, you cannot reuse any of your last 3 passwords.
          </p>
        </div>

        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm mb-6"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </motion.div>
        )}

        {success && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/20 text-green-400 rounded-lg text-sm mb-6"
          >
            <CheckCircle className="w-4 h-4 shrink-0" />
            <span>Password reset completed! Redirecting to login...</span>
          </motion.div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Reset Token</label>
            <div className="relative">
              <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                required
                value={token}
                onChange={(e) => setToken(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-black/40 border border-white/5 focus:border-accentPurple/50 rounded-lg focus:outline-none text-sm transition-all"
                placeholder="Paste token here"
              />
            </div>
          </div>

          <div>
            <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">New Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="password"
                required
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-black/40 border border-white/5 focus:border-accentPurple/50 rounded-lg focus:outline-none text-sm transition-all"
                placeholder="Min. 8 chars, 1 uppercase, 1 number"
              />
            </div>
          </div>

          <div>
            <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Confirm New Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-black/40 border border-white/5 focus:border-accentPurple/50 rounded-lg focus:outline-none text-sm transition-all"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || success}
            className="w-full py-2.5 mt-4 bg-gradient-to-r from-accentPurple to-accentBlue hover:from-accentPurple/90 hover:to-accentBlue/90 text-white font-semibold rounded-lg text-sm shadow-lg shadow-accentPurple/10 glow-btn transition-all"
          >
            {loading ? 'Updating Password...' : 'Reset Password'}
          </button>
        </form>

        <div className="mt-8 text-center">
          <Link to="/login" className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-white font-semibold transition-all">
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Login
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
