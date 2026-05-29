import Link from 'next/link';
import { useRouter } from 'next/router';
import styles from '../styles/Layout.module.css';

const links = [
  { href: '/', label: 'Home' },
  { href: '/search', label: 'Search' },
  { href: '/graph', label: 'Graph' },
  { href: '/stock', label: 'Stock' },
  { href: '/skills', label: 'Skills' },
];

export default function Layout({ children }) {
  const router = useRouter();
  const path = router.pathname || '/';

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
          href="http://localhost:3002"
          target="_blank"
          rel="noreferrer"
        >
          Admin →
        </a>
      </header>
      <main className={styles.main}>{children}</main>
      <footer className={styles.footer}>
        API default: {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001'}
      </footer>
    </div>
  );
}
