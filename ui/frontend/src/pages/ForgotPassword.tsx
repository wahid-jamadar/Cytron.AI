import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, AlertCircle, ArrowLeft, Key } from 'lucide-react';
import cytronLogo from '../assets/Cytron.AI-Logo.png';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    setResetToken('');
    setLoading(true);

    try {
      const response = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });

      if (!response.ok) {
        throw new Error('Failed to generate reset link');
      }

      const data = await response.json();
      setMessage(data.message);
      if (data.reset_token) {
        setResetToken(data.reset_token);
      }
    } catch (err: any) {
      setError(err.message || 'Something went wrong. Please try again.');
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
            Forgot Password
          </h2>
          <p className="text-gray-400 text-xs mt-1 text-center">
            Enter your email address and we'll provide a reset token to restore your credentials.
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

        {message && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="p-3 bg-green-500/10 border border-green-500/20 text-green-400 rounded-lg text-sm mb-6"
          >
            <span>{message}</span>
          </motion.div>
        )}

        {resetToken && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="p-4 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-lg text-sm mb-6"
          >
            <div className="font-semibold uppercase tracking-wider text-xs mb-1 text-purple-300">Sandbox Reset Token:</div>
            <code className="block select-all bg-black/60 p-2 rounded text-xs break-all text-white font-mono">{resetToken}</code>
            <div className="mt-3 text-right">
              <Link
                to={`/reset-password?token=${resetToken}`}
                className="text-xs font-semibold text-accentBlue hover:underline"
              >
                Proceed to Reset Password &rarr;
              </Link>
            </div>
          </motion.div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-black/40 border border-white/5 focus:border-accentPurple/50 rounded-lg focus:outline-none text-sm transition-all focus:ring-1 focus:ring-accentPurple/50"
                placeholder="name@company.com"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-gradient-to-r from-accentPurple to-accentBlue hover:from-accentPurple/90 hover:to-accentBlue/90 text-white font-semibold rounded-lg text-sm shadow-lg shadow-accentPurple/10 glow-btn transition-all"
          >
            {loading ? 'Processing...' : 'Request Reset Token'}
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
