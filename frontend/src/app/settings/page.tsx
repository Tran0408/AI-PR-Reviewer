import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import { authOptions } from '@/lib/auth';
import { backend, type Repo } from '@/lib/api';
import { SettingsClient } from './SettingsClient';

export const dynamic = 'force-dynamic';

export default async function SettingsPage() {
  const session = await getServerSession(authOptions);
  if (!session) redirect('/api/auth/signin');

  const userId = (session.user as { backendUserId?: string }).backendUserId;
  const accessToken = (session as { accessToken?: string }).accessToken;

  if (!userId || !accessToken) {
    return (
      <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-800 dark:bg-amber-900/30">
        Missing backend user or access token. Try signing out and back in.
      </div>
    );
  }

  await backend(`/repositories/sync`, {
    method: 'POST',
    body: { user_id: userId, access_token: accessToken },
    revalidate: false,
  }).catch(() => null);

  const { items } = await backend<{ items: Repo[] }>(`/repositories?user_id=${userId}`, {
    revalidate: false,
  });

  return <SettingsClient userId={userId} repos={items} />;
}
