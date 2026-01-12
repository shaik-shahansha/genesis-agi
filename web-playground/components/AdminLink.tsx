'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';

export function AdminLink() {
  const { genesisUser } = useAuth();

  if (!genesisUser || genesisUser.role !== 'admin') return null;

  return (
    <Link href="/admin" className="btn-ghost">
      Admin
    </Link>
  );
}
