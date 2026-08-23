import { useState } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../lib/auth';

export default function LoginPage() {
  const { login, register, user } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (user) {
    router.replace('/');
    return null;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isRegister) {
        await register(email, password);
      } else {
        await login(email, password);
      }
      router.push('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}>
      <div style={{ width: '100%', maxWidth: 400, padding: 32, background: '#1a1a2e', borderRadius: 12, border: '1px solid #333' }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8, color: '#fff' }}>
          {isRegister ? 'Create Account' : 'Sign In'}
        </h1>
        <p style={{ color: '#888', fontSize: 14, marginBottom: 24 }}>
          Finance Advanced Research Platform
        </p>

        {error && (
          <div style={{ background: '#4a1c1c', border: '1px solid #e53935', borderRadius: 6, padding: '8px 12px', marginBottom: 16, color: '#ff8a80', fontSize: 13 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <label style={{ display: 'block', marginBottom: 12 }}>
            <span style={{ display: 'block', color: '#aaa', fontSize: 12, marginBottom: 4 }}>Email</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={{ width: '100%', padding: '10px 12px', borderRadius: 6, border: '1px solid #444', background: '#0d0d1a', color: '#fff', fontSize: 14 }}
              placeholder="you@company.com"
            />
          </label>

          <label style={{ display: 'block', marginBottom: 20 }}>
            <span style={{ display: 'block', color: '#aaa', fontSize: 12, marginBottom: 4 }}>Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              style={{ width: '100%', padding: '10px 12px', borderRadius: 6, border: '1px solid #444', background: '#0d0d1a', color: '#fff', fontSize: 14 }}
              placeholder="••••••••"
            />
          </label>

          <button
            type="submit"
            disabled={loading}
            style={{ width: '100%', padding: '12px', borderRadius: 6, border: 'none', background: '#4f46e5', color: '#fff', fontSize: 14, fontWeight: 600, cursor: loading ? 'wait' : 'pointer', opacity: loading ? 0.7 : 1 }}
          >
            {loading ? '...' : isRegister ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        <p style={{ marginTop: 16, textAlign: 'center', fontSize: 13, color: '#888' }}>
          {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            onClick={() => { setIsRegister(!isRegister); setError(''); }}
            style={{ background: 'none', border: 'none', color: '#818cf8', cursor: 'pointer', fontSize: 13 }}
          >
            {isRegister ? 'Sign in' : 'Register'}
          </button>
        </p>
      </div>
    </div>
  );
}
