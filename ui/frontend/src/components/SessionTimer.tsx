import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { AlertTriangle, Clock, RefreshCw, LogOut } from 'lucide-react';
import useAuthStore from '../store/authStore';
import { apiFetch } from '../store/apiClient';

export default function SessionTimer() {
  const { accessToken, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  const [showWarning, setShowWarning] = useState(false);
  const [countdown, setCountdown] = useState(300); // 5 minutes in seconds

  const lastActivityRef = useRef<number>(Date.now());
  const sessionStartRef = useRef<number>(Date.now());
  const timerRef = useRef<any>(null);

  // Constants (in milliseconds)
  const INACTIVITY_LIMIT = 15 * 60 * 1000; // 15 minutes
  const SESSION_LIMIT = 30 * 60 * 1000; // 30 minutes
  const WARNING_THRESHOLD = 25 * 60 * 1000; // 25 minutes

  // Reset session start ref whenever accessToken changes (after a successful login/refresh)
  useEffect(() => {
    if (accessToken) {
      sessionStartRef.current = Date.now();
      lastActivityRef.current = Date.now();
      setShowWarning(false);
    }
  }, [accessToken]);

  // Track user activity events
  useEffect(() => {
    if (!accessToken) return;

    const handleUserActivity = () => {
      lastActivityRef.current = Date.now();
    };

    // Listen to standard user interaction events
    const events = ['mousemove', 'keydown', 'click', 'scroll'];
    events.forEach(event => {
      window.addEventListener(event, handleUserActivity);
    });

    return () => {
      events.forEach(event => {
        window.removeEventListener(event, handleUserActivity);
      });
    };
  }, [accessToken]);

  // Main monitoring interval
  useEffect(() => {
    if (!accessToken) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }

    // Set up monitoring loop
    timerRef.current = setInterval(() => {
      const now = Date.now();
      const idleTime = now - lastActivityRef.current;
      const sessionTime = now - sessionStartRef.current;

      // 1. Inactivity check (15 minutes)
      if (idleTime >= INACTIVITY_LIMIT) {
        clearInterval(timerRef.current);
        handleAutoLogout(true); // Expired due to inactivity
        return;
      }

      // 2. Hard session timeout check (30 minutes)
      if (sessionTime >= SESSION_LIMIT) {
        clearInterval(timerRef.current);
        handleAutoLogout(true); // Expired due to session length
        return;
      }

      // 3. Show warning at 25 minutes
      if (sessionTime >= WARNING_THRESHOLD) {
        setShowWarning(true);
        // Calculate remaining seconds
        const remainingSeconds = Math.max(0, Math.floor((SESSION_LIMIT - sessionTime) / 1000));
        setCountdown(remainingSeconds);
      } else {
        setShowWarning(false);
      }
    }, 1000);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [accessToken]);

  const handleAutoLogout = async (expired: boolean) => {
    try {
      // Invalidate on backend
      await apiFetch('/api/auth/logout', { method: 'POST' });
    } catch (err) {
      console.warn('Backend logout failed or was already cleared:', err);
    } finally {
      // Invalidate on client
      logout();
      if (expired) {
        navigate('/login?expired=1', { replace: true });
      } else {
        navigate('/login', { replace: true });
      }
    }
  };

  const handleExtendSession = async () => {
    try {
      // Call backend refresh
      await apiFetch('/api/auth/refresh', { method: 'POST' });
      // Reset local tracking
      sessionStartRef.current = Date.now();
      lastActivityRef.current = Date.now();
      setShowWarning(false);
    } catch (err) {
      console.error('Failed to extend session:', err);
      handleAutoLogout(true);
    }
  };

  if (!accessToken || !showWarning) return null;

  // Format countdown seconds into MM:SS
  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const remaining = secs % 60;
    return `${mins.toString().padStart(2, '0')}:${remaining.toString().padStart(2, '0')}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm transition-all duration-300">
      <div className="w-[450px] glass-panel border border-white/10 p-8 rounded-2xl shadow-2xl flex flex-col items-center text-center space-y-6">
        <div className="w-14 h-14 rounded-full bg-amber-500/10 border border-amber-500/35 flex items-center justify-center text-amber-400">
          <AlertTriangle className="w-7 h-7" />
        </div>

        <div className="space-y-2">
          <h3 className="text-xl font-bold text-white tracking-tight">Session Expiry Warning</h3>
          <p className="text-gray-400 text-sm leading-relaxed">
            For security, your active workspace session is about to expire. You will be automatically logged out due to inactivity in:
          </p>
        </div>

        {/* Live Countdown Badge */}
        <div className="py-2.5 px-6 bg-black/45 border border-white/5 rounded-xl flex items-center gap-3">
          <Clock className="w-5 h-5 text-accentPurple animate-pulse" />
          <span className="font-mono font-extrabold text-2xl text-white tracking-widest">
            {formatTime(countdown)}
          </span>
        </div>

        {/* Actions Row */}
        <div className="w-full grid grid-cols-2 gap-4">
          <button
            onClick={() => handleAutoLogout(false)}
            className="py-2.5 border border-white/5 hover:border-white/15 hover:bg-white/2 text-gray-400 hover:text-white font-semibold rounded-xl text-sm transition-all flex items-center justify-center gap-1.5"
          >
            <LogOut className="w-4 h-4" /> Cancel
          </button>
          <button
            onClick={handleExtendSession}
            className="py-2.5 bg-gradient-to-r from-accentPurple to-accentBlue hover:from-accentPurple/95 hover:to-accentBlue/95 text-white font-semibold rounded-xl text-sm shadow-lg shadow-accentPurple/10 glow-btn transition-all flex items-center justify-center gap-1.5"
          >
            <RefreshCw className="w-4 h-4" /> Continue Session
          </button>
        </div>
      </div>
    </div>
  );
}
