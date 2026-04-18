import type { Metadata } from 'next';
import { Nav } from '@/components/Nav';
import { Providers } from './providers';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI PR Reviewer',
  description: 'Automated AI code reviews for your GitHub pull requests.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <Nav />
          <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
