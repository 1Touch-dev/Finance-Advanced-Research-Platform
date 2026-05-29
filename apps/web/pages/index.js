import Head from 'next/head';
import Link from 'next/link';
import styles from '../src/styles/Home.module.css';

const cards = [
  {
    href: '/search',
    title: 'Global search',
    desc: 'Query entities and documents against the API.',
  },
  {
    href: '/graph',
    title: 'Relationship graph',
    desc: 'Explore connections between entities.',
  },
  {
    href: '/stock',
    title: 'Stock research',
    desc: 'Quotes, fundamentals-style views, and analysis.',
  },
  {
    href: '/skills',
    title: 'Skills & automation',
    desc: 'Skill definitions and orchestration hooks.',
  },
  {
    href: '/portfolio/1',
    title: 'Portfolio exposure',
    desc: 'Sample portfolio view (replace ID as needed).',
  },
];

export default function Home() {
  return (
    <>
      <Head>
        <title>Enterprise Intelligence Platform</title>
        <meta
          name="description"
          content="Public-record intelligence, research, and monitoring."
        />
      </Head>
      <div className={styles.hero}>
        <p className={styles.eyebrow}>Research & compliance</p>
        <h1 className={styles.title}>Evidence-first intelligence workspace</h1>
        <p className={styles.subtitle}>
          Navigate search, graph, equities, and skills from the shell above, or
          jump in below.
        </p>
      </div>
      <div className={styles.grid}>
        {cards.map((c) => (
          <Link href={c.href} key={c.href}>
            <a className={styles.card}>
              <h2 className={styles.cardTitle}>{c.title}</h2>
              <p className={styles.cardDesc}>{c.desc}</p>
              <div className={styles.cardArrow}>Open →</div>
            </a>
          </Link>
        ))}
      </div>
    </>
  );
}
