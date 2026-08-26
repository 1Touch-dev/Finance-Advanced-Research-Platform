import '../src/styles/globals.css';
import Layout from '../src/components/Layout';
import { ErrorBoundary } from '../src/components/ErrorBoundary';
import { SWRConfig } from 'swr';
import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { AuthProvider, useAuth } from '../lib/auth';
import * as Sentry from '@sentry/nextjs';

const PUBLIC_PAGES = ['/login'];

function AuthGate({ children }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user && !PUBLIC_PAGES.includes(router.pathname)) {
      router.replace('/login');
    }
  }, [loading, user, router.pathname]);

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh', color: '#888' }}>Loading...</div>;
  }

  if (!user && !PUBLIC_PAGES.includes(router.pathname)) {
    return null;
  }

  return children;
}

function AppContent({ Component, pageProps }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  
  if (!mounted) {
    return <Layout><div /></Layout>;
  }

  const router = useRouter();
  const isPublic = PUBLIC_PAGES.includes(router.pathname);

  return (
    <SWRConfig value={{ revalidateOnFocus: false, shouldRetryOnError: false }}>
      <ErrorBoundary>
        <AuthProvider>
          {isPublic ? (
            <Component {...pageProps} />
          ) : (
            <AuthGate>
              <Layout>
                <Component {...pageProps} />
              </Layout>
            </AuthGate>
          )}
        </AuthProvider>
      </ErrorBoundary>
    </SWRConfig>
  );
}

export default function App(props) {
  return (
    <Sentry.ErrorBoundary
      fallback={({ error, resetError }) => (
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          <h2>Something went wrong</h2>
          <p style={{ color: '#888', marginBottom: '1rem' }}>
            The error has been reported. You can try again or refresh the page.
          </p>
          <button onClick={resetError} style={{ padding: '0.5rem 1rem', cursor: 'pointer' }}>
            Try again
          </button>
        </div>
      )}
    >
      <AppContent {...props} />
    </Sentry.ErrorBoundary>
  );
}
