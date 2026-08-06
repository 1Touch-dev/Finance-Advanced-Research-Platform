import '../src/styles/globals.css';
import Layout from '../src/components/Layout';
import { ErrorBoundary } from '../src/components/ErrorBoundary';

export default function App({ Component, pageProps }) {
  return (
    <ErrorBoundary>
      <Layout>
        <Component {...pageProps} />
      </Layout>
    </ErrorBoundary>
  );
}
