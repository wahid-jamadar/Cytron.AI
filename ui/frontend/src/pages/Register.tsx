import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Mail, Lock, User, AlertCircle, CheckCircle } from 'lucide-react';
import cytronLogo from '../assets/Cytron.AI-Logo.png';

export default function Register() {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const navigate = useNavigate();

  React.useEffect(() => {
    // Clear any active session when entering registration page
    fetch('/api/auth/logout', { method: 'POST' }).catch(() => {});
    localStorage.removeItem('eto_user');
    localStorage.removeItem('eto_access');
    localStorage.removeItem('eto_refresh');
    localStorage.removeItem('eto_is_impersonating');
    localStorage.removeItem('eto_admin_access');
    localStorage.removeItem('eto_admin_user');
  }, []);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    // Validations
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    // Password regex check: at least 1 uppercase, 1 lowercase, 1 number
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$/;
    if (!passwordRegex.test(password)) {
      setError('Password must contain at least one uppercase letter, one lowercase letter, and one number');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: firstName,
          last_name: lastName,
          email,
          password
        })
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Registration failed');
      }

      setSuccess(true);
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Registration failed. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative px-4 py-12">
      {/* Background blurs */}
      <div className="absolute top-1/4 left-1/4 w-72 h-72 rounded-full bg-accentPurple filter blur-[100px] opacity-20 pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-72 h-72 rounded-full bg-accentBlue filter blur-[100px] opacity-20 pointer-events-none"></div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md glass-panel p-8 rounded-2xl relative z-10 border border-white/5 shadow-2xl"
      >
        <div className="flex flex-col items-center mb-8">
          <img src={cytronLogo} alt="Cytron.AI" style={{ height: '48px', width: 'auto', marginBottom: '16px' }} className="object-contain" />
          <p className="text-gray-400 text-xs mt-1">Get started with the autonomous agent system</p>
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
            <span>Account created successfully! Redirecting to login...</span>
          </motion.div>
        )}

        <form onSubmit={handleRegister} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">First Name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  required
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 bg-black/40 border border-white/5 focus:border-accentPurple/50 rounded-lg focus:outline-none text-sm transition-all"
                  placeholder="John"
                />
              </div>
            </div>

            <div>
              <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Last Name</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  required
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 bg-black/40 border border-white/5 focus:border-accentPurple/50 rounded-lg focus:outline-none text-sm transition-all"
                  placeholder="Doe"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-black/40 border border-white/5 focus:border-accentPurple/50 rounded-lg focus:outline-none text-sm transition-all"
                placeholder="name@company.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-black/40 border border-white/5 focus:border-accentPurple/50 rounded-lg focus:outline-none text-sm transition-all"
                placeholder="Min. 8 chars, 1 uppercase, 1 number"
              />
            </div>
          </div>

          <div>
            <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Confirm Password</label>
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
            {loading ? 'Registering...' : 'Register'}
          </button>
        </form>

        <div className="mt-8 text-center text-xs text-gray-400">
          Already have an account?{' '}
          <Link to="/login" className="text-accentBlue hover:underline font-semibold">
            Sign in
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
