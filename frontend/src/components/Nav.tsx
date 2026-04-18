'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { signIn, signOut, useSession } from 'next-auth/react';
import { cn } from '@/lib/cn';

const tabs = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/settings', label: 'Settings' },
];

export function Nav() {
  const pathname = usePathname();
  const { data: session, status } = useSession();

  return (
    <header className="border-b border-slate-200 bg-white/70 backdrop-blur dark:border-slate-800 dark:bg-slate-950/70">
      <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
        <Link href="/" className="font-semibold">
          🤖 AI PR Reviewer
        </Link>
        <nav className="flex items-center gap-4">
          {tabs.map((t) => (
            <Link
              key={t.href}
              href={t.href}
              className={cn(
                'text-sm',
                pathname?.startsWith(t.href)
                  ? 'font-semibold text-brand-600'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white',
              )}
            >
              {t.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3 text-sm">
          {status === 'loading' ? null : session?.user ? (
            <>
              <span className="text-slate-600 dark:text-slate-300">
                {(session.user as { login?: string }).login ?? session.user.name}
              </span>
              <button
                onClick={() => signOut({ callbackUrl: '/' })}
                className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
              >
                Sign out
              </button>
            </>
          ) : (
            <button
              onClick={() => signIn('github', { callbackUrl: '/dashboard' })}
              className="rounded bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 dark:bg-white dark:text-slate-900"
            >
              Sign in with GitHub
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
