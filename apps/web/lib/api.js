export function getApiBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_API_URL;
  if (configured) {
    return configured.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return 'http://localhost:8000';
}

export function isNoData(data) {
  return data && data.no_data === true;
}

export function getAdminBaseUrl() {
  const configured = process.env.NEXT_PUBLIC_ADMIN_URL;
  if (configured) {
    return configured.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:3002`;
  }
  return 'http://localhost:3002';
}

export function authHeaders() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function apiFetch(path, options = {}) {
  const base = getApiBaseUrl();
  const url = path.startsWith('http') ? path : `${base}${path.startsWith('/') ? '' : '/'}${path}`;
  const headers = { ...authHeaders(), ...(options.headers || {}) };
  return fetch(url, { ...options, headers });
}

export function authFetcher(url) {
  return apiFetch(url).then((r) => {
    if (r.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
      return null;
    }
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  });
}
