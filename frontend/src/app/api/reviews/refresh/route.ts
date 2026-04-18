import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';

const BACKEND = process.env.BACKEND_URL ?? 'http://localhost:8000';

export async function POST() {
  const session = await getServerSession(authOptions);
  const userId = (session?.user as { backendUserId?: string } | undefined)?.backendUserId;
  if (!userId) return NextResponse.json({ error: 'unauthenticated' }, { status: 401 });

  const res = await fetch(`${BACKEND}/reviews/refresh?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
    cache: 'no-store',
  });
  const text = await res.text();
  return new NextResponse(text, {
    status: res.status,
    headers: { 'Content-Type': res.headers.get('Content-Type') ?? 'application/json' },
  });
}
