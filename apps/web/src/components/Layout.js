import Link from 'next/link';
import { useRouter } from 'next/router';
import { useMemo } from 'react';
import { getAdminBaseUrl, getApiBaseUrl } from '../../lib/api';
import styles from '../styles/Layout.module.css';

const links = [
  { href: '/', label: 'Home' },
  { href: '/intelligence', label: 'Intelligence' },
  { href: '/timeline', label: 'Timeline' },
  { href: '/compare', label: 'Compare' },
  { href: '/tracking', label: 'Tracking' },
  { href: '/search', label: 'Search' },
  { href: '/graph', label: 'Graph' },
  { href: '/entities/merge', label: 'Merge' },
  { href: '/registry', label: 'Registry' },
  { href: '/economics', label: 'Economics' },
  { href: '/stock', label: 'Stock' },
  { href: '/skills', label: 'Skills' },
  { href: '/alerts', label: 'Alerts' },
];

export default function Layout({ children }) {
  const router = useRouter();
  const path = router.pathname || '/';
  const adminUrl = useMemo(() => getAdminBaseUrl(), []);
  const apiUrl = useMemo(() => getApiBaseUrl(), []);

  return (
    <div className={styles.shell}>
      <header className={styles.topBar}>
        <Link href="/">
          <a className={styles.brand}>
            Enterprise <span>Intelligence</span>
          </a>
        </Link>
        <nav className={styles.nav} aria-label="Main">
          {links.map(({ href, label }) => {
            const active =
              href === '/'
                ? path === '/'
                : path === href || path.startsWith(`${href}/`);
            return (
              <Link href={href} key={href}>
                <a
                  className={
                    active
                      ? `${styles.navLink} ${styles.navLinkActive}`
                      : styles.navLink
                  }
                >
                  {label}
                </a>
              </Link>
            );
          })}
        </nav>
        <a
          className={styles.adminLink}
          href={adminUrl}
          target="_blank"
          rel="noreferrer"
        >
          Admin →
        </a>
      </header>
      <main className={styles.main}>{children}</main>
      <footer className={styles.footer}>
        API endpoint: {apiUrl}
      </footer>
    </div>
  );
}
