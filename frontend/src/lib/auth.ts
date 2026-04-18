import type { NextAuthOptions } from 'next-auth';
import GitHubProvider from 'next-auth/providers/github';

async function upsertUserOnBackend(params: {
  githubId: string;
  login: string;
  email?: string | null;
  avatarUrl?: string | null;
  accessToken?: string | null;
}): Promise<string | null> {
  const backend = process.env.BACKEND_URL ?? 'http://localhost:8000';
  try {
    const res = await fetch(`${backend}/users/upsert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        github_id: params.githubId,
        login: params.login,
        email: params.email ?? null,
        avatar_url: params.avatarUrl ?? null,
        access_token: params.accessToken ?? null,
      }),
      cache: 'no-store',
    });
    if (!res.ok) return null;
    const json = await res.json();
    return json.id as string;
  } catch {
    return null;
  }
}

export const authOptions: NextAuthOptions = {
  secret: process.env.NEXTAUTH_SECRET,
  providers: [
    GitHubProvider({
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: 'read:user user:email repo admin:repo_hook',
        },
      },
    }),
  ],
  session: { strategy: 'jwt' },
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account && profile) {
        const githubId = String((profile as { id: number | string }).id);
        const login = (profile as { login: string }).login;
        const email = (profile as { email?: string | null }).email ?? null;
        const avatarUrl = (profile as { avatar_url?: string }).avatar_url ?? null;
        const accessToken = (account.access_token as string | undefined) ?? null;

        token.githubId = githubId;
        token.login = login;
        token.accessToken = accessToken;

        const backendId = await upsertUserOnBackend({
          githubId,
          login,
          email,
          avatarUrl,
          accessToken,
        });
        token.backendUserId = backendId;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.login = token.login;
        session.user.githubId = token.githubId;
        session.user.backendUserId = token.backendUserId ?? null;
      }
      session.accessToken = token.accessToken ?? undefined;
      return session;
    },
  },
};
