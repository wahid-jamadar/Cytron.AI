import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Brain, Code, Monitor, Bell, Key, ArrowRight, ArrowLeft, Check } from 'lucide-react';
import useAuthStore from '../store/authStore';
import { apiFetch } from '../store/apiClient';

export default function Onboarding() {
  const [step, setStep] = useState(1);
  const [provider, setProvider] = useState('groq');
  const [language, setLanguage] = useState('javascript');
  const [theme, setTheme] = useState('dark');
  const [timezone, setTimezone] = useState('UTC');
  const [notifications, setNotifications] = useState('all');
  const [apiKey, setApiKey] = useState('');
  
  const updatePrefsStore = useAuthStore((state) => state.updatePreferences);
  const navigate = useNavigate();

  const handleNext = () => {
    if (step < 5) setStep(step + 1);
  };

  const handleBack = () => {
    if (step > 1) setStep(step - 1);
  };

  const handleComplete = async () => {
    try {
      // 1. Save preferences
      await apiFetch('/api/auth/preferences', {
        method: 'PUT',
        json: {
          preferred_provider: provider,
          preferred_language: language,
          ui_theme: theme,
          timezone,
          notification_preferences: notifications
        }
      });

      // 2. Save API key if provided
      if (apiKey.trim()) {
        await apiFetch('/api/auth/api-keys', {
          method: 'POST',
          json: {
            provider,
            key: apiKey
          }
        });
      }

      // Update state locally
      updatePrefsStore({
        preferred_provider: provider,
        preferred_language: language,
        ui_theme: theme,
        timezone,
        avatar_url: null
      });

      window.location.href = '/hub';
    } catch (error) {
      console.error('Error during onboarding save:', error);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative px-4 py-12">
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accentPurple filter blur-[150px] opacity-10 pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accentBlue filter blur-[150px] opacity-10 pointer-events-none"></div>

      <div className="w-full max-w-xl glass-panel p-8 rounded-2xl relative z-10 border border-white/5 shadow-2xl flex flex-col min-h-[500px]">
        {/* Header and Step Indicators */}
        <div className="flex justify-between items-center mb-8 pb-4 border-b border-white/5">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-accentPurple" />
            <span className="text-sm font-bold text-white">Setup Workspace</span>
          </div>
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5].map((s) => (
              <div
                key={s}
                className={`w-8 h-1.5 rounded-full transition-all duration-300 ${
                  s === step ? 'bg-accentPurple w-12' : s < step ? 'bg-accentPurple/40' : 'bg-white/10'
                }`}
              />
            ))}
          </div>
        </div>

        {/* Dynamic Wizard Steps */}
        <div className="flex-grow flex flex-col justify-center">
          <AnimatePresence mode="wait">
            {step === 1 && (
              <motion.div
                key="step1"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div className="space-y-2">
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <Brain className="w-5 h-5 text-accentPurple" /> Select AI Provider
                  </h3>
                  <p className="text-gray-400 text-sm">Choose the default Large Language Model engine for code generation.</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {[
                    { id: 'groq', name: 'Groq Cloud', desc: 'Default ultra-fast inference' },
                    { id: 'openai', name: 'OpenAI', desc: 'GPT-4o & Reasoning LLMs' },
                    { id: 'anthropic', name: 'Anthropic', desc: 'Claude 3.5 Sonnet' },
                    { id: 'gemini', name: 'Google Gemini', desc: 'Gemini 1.5 Pro models' }
                  ].map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setProvider(p.id)}
                      className={`p-4 rounded-xl text-left border transition-all ${
                        provider === p.id
                          ? 'border-accentPurple bg-accentPurple/10 text-white'
                          : 'border-white/5 bg-black/20 text-gray-400 hover:border-white/10'
                      }`}
                    >
                      <div className="font-semibold text-sm flex items-center justify-between">
                        {p.name}
                        {provider === p.id && <Check className="w-4 h-4 text-accentPurple" />}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">{p.desc}</div>
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div
                key="step2"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div className="space-y-2">
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <Code className="w-5 h-5 text-accentPurple" /> Coding Language
                  </h3>
                  <p className="text-gray-400 text-sm">Select your preferred programming language environment.</p>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: 'javascript', name: 'JavaScript' },
                    { id: 'typescript', name: 'TypeScript' },
                    { id: 'python', name: 'Python' },
                    { id: 'go', name: 'Golang' },
                    { id: 'rust', name: 'Rust' },
                    { id: 'java', name: 'Java' }
                  ].map((l) => (
                    <button
                      key={l.id}
                      onClick={() => setLanguage(l.id)}
                      className={`p-3 rounded-lg text-center border font-semibold text-sm transition-all ${
                        language === l.id
                          ? 'border-accentPurple bg-accentPurple/10 text-white'
                          : 'border-white/5 bg-black/20 text-gray-400 hover:border-white/10'
                      }`}
                    >
                      {l.name}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {step === 3 && (
              <motion.div
                key="step3"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div className="space-y-2">
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <Monitor className="w-5 h-5 text-accentPurple" /> Dashboard Customization
                  </h3>
                  <p className="text-gray-400 text-sm">Customize visual settings and timezone controls.</p>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">UI Theme</label>
                    <div className="flex gap-3">
                      {['dark', 'light', 'oled'].map((t) => (
                        <button
                          key={t}
                          onClick={() => setTheme(t)}
                          className={`flex-1 py-2 rounded-lg border text-sm font-semibold capitalize transition-all ${
                            theme === t
                              ? 'border-accentPurple bg-accentPurple/10 text-white'
                              : 'border-white/5 bg-black/20 text-gray-400 hover:border-white/10'
                          }`}
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">Timezone</label>
                    <select
                      value={timezone}
                      onChange={(e) => setTimezone(e.target.value)}
                      className="w-full p-2.5 bg-black/40 border border-white/5 rounded-lg text-sm text-white focus:outline-none focus:border-accentPurple/50"
                    >
                      <option value="UTC">UTC (Coordinated Universal Time)</option>
                      <option value="EST">EST (Eastern Standard Time)</option>
                      <option value="GMT">GMT (Greenwich Mean Time)</option>
                      <option value="IST">IST (Indian Standard Time)</option>
                      <option value="JST">JST (Japan Standard Time)</option>
                    </select>
                  </div>
                </div>
              </motion.div>
            )}

            {step === 4 && (
              <motion.div
                key="step4"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div className="space-y-2">
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <Bell className="w-5 h-5 text-accentPurple" /> Notifications
                  </h3>
                  <p className="text-gray-400 text-sm">Specify which platform updates to send via WebSocket alerts.</p>
                </div>

                <div className="space-y-3">
                  {[
                    { id: 'all', title: 'All Notifications', desc: 'Completed tasks, agent warnings, and critical errors' },
                    { id: 'critical', title: 'Critical Warnings Only', desc: 'Deploy failures, limits reached, and security events' },
                    { id: 'none', title: 'Muted', desc: 'Disable real-time pushes (dashboard view only)' }
                  ].map((n) => (
                    <button
                      key={n.id}
                      onClick={() => setNotifications(n.id)}
                      className={`w-full p-4 rounded-xl text-left border transition-all flex items-center justify-between ${
                        notifications === n.id
                          ? 'border-accentPurple bg-accentPurple/10 text-white'
                          : 'border-white/5 bg-black/20 text-gray-400 hover:border-white/10'
                      }`}
                    >
                      <div>
                        <div className="font-semibold text-sm">{n.title}</div>
                        <div className="text-xs text-gray-500 mt-0.5">{n.desc}</div>
                      </div>
                      {notifications === n.id && <Check className="w-4 h-4 text-accentPurple" />}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {step === 5 && (
              <motion.div
                key="step5"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div className="space-y-2">
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <Key className="w-5 h-5 text-accentPurple" /> Secure API Credentials (Optional)
                  </h3>
                  <p className="text-gray-400 text-sm">Provide your {provider.toUpperCase()} API key to connect. Keys are fully encrypted.</p>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-gray-400 text-xs font-semibold uppercase tracking-wider mb-2">
                      {provider.toUpperCase()} API Key
                    </label>
                    <input
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      className="w-full px-4 py-2.5 bg-black/40 border border-white/5 focus:border-accentPurple/50 rounded-lg focus:outline-none text-sm text-white transition-all font-mono"
                      placeholder="sk-..."
                    />
                    <p className="text-gray-500 text-[10px] mt-2 leading-relaxed">
                      If left blank, the platform will utilize the administrator's globally configured API keys.
                    </p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer controls */}
        <div className="flex justify-between items-center mt-8 pt-4 border-t border-white/5">
          <button
            onClick={handleBack}
            disabled={step === 1}
            className={`flex items-center gap-1 text-sm font-semibold text-gray-400 hover:text-white transition-all ${
              step === 1 ? 'opacity-0 cursor-default' : ''
            }`}
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </button>
          
          {step < 5 ? (
            <button
              onClick={handleNext}
              className="flex items-center gap-1 py-2 px-5 bg-accentPurple hover:bg-accentPurple/90 text-white font-semibold rounded-lg text-sm shadow-md transition-all glow-btn"
            >
              Continue <ArrowRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={handleComplete}
              className="flex items-center gap-1 py-2 px-5 bg-gradient-to-r from-accentPurple to-accentBlue hover:from-accentPurple/95 hover:to-accentBlue/95 text-white font-semibold rounded-lg text-sm shadow-lg shadow-accentPurple/10 transition-all glow-btn"
            >
              Complete Setup <Check className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
