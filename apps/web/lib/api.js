export function getApiBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_API_URL;
  if (configured) {
    return configured.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:3001`;
  }
  return 'http://localhost:3001';
}
