import '../src/styles/globals.css';
import Layout from '../src/components/Layout';
import { ErrorBoundary } from '../src/components/ErrorBoundary';
import { SWRConfig } from 'swr';
import dynamic from 'next/dynamic';
import { useState, useEffect } from 'react';

function AppContent({ Component, pageProps }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  
  if (!mounted) {
    return <Layout><div /></Layout>;
  }

  return (
    <SWRConfig value={{ revalidateOnFocus: false, shouldRetryOnError: false }}>
      <ErrorBoundary>
        <Layout>
          <Component {...pageProps} />
        </Layout>
      </ErrorBoundary>
    </SWRConfig>
  );
}

export default function App(props) {
  return <AppContent {...props} />;
}
