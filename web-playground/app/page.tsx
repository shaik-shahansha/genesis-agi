// Genesis Playground - Clean Dashboard
'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import AuthRequired from '@/components/AuthRequired';

interface Mind {
  gmid: string;
  name: string;
  model: string;
  status: string;
  memory_count: number;
  daemon_running?: boolean;
}

function Home() {
  const [minds, setMinds] = useState<Mind[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const isFetchingRef = useRef(false);

  useEffect(() => {
    const safeFetch = () => {
      if (isFetchingRef.current) return;
      isFetchingRef.current = true;
      fetchMinds().finally(() => (isFetchingRef.current = false));
    };

    safeFetch();

    // Reload when window gains focus (e.g., after navigation back)
    const handleFocus = () => safeFetch();
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, []);

  const fetchMinds = async () => {
    try {
      const data = await api.getMinds();
      setMinds(data);
    } catch (error) {
      console.error('Error fetching minds:', error);
      // If unauthorized, redirect to login
      if (error instanceof Error && error.message.includes('401')) {
        router.push('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <div className="spinner-large"></div>
          <p className="text-gray-400 text-sm animate-pulse">Loading minds...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-semibold text-white">Minds</h1>
          <p className="text-gray-300 mt-1">{minds.length} total</p>
        </div>
        <Link href="/create" className="btn-primary">
          New Mind
        </Link>
      </div>

      {/* Minds List */}
      {minds.length === 0 ? (
        <div className="text-center py-12 bg-slate-800 border border-slate-700 rounded-lg">
          <p className="text-gray-300 mb-4">No minds yet</p>
          <Link href="/create" className="btn-primary">
            Create Your First Mind
          </Link>
        </div>
      ) : (
        <div className="grid gap-4">
          {minds.map((mind) => (
            <Link
              key={mind.gmid}
              href={`/minds/${mind.gmid}`}
              className="clean-card p-6 flex items-center justify-between hover:border-purple-500 transition-colors"
            >
              <div>
                <h3 className="text-lg font-semibold text-white">{mind.name}</h3>
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-300">
                  <span>{mind.status}</span>
                  <span>·</span>
                  <span>{(mind as any).age || 'Unknown age'}</span>
                  <span>·</span>
                  <span>{mind.memory_count} memories</span>
                  {mind.daemon_running && (
                    <>
                      <span>·</span>
                      <span className="badge-success">Active</span>
                    </>
                  )}
                </div>
              </div>
              <svg className="w-5 h-5 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

// Wrap with AuthRequired
const HomeWithAuth = () => (
  <AuthRequired>
    <Home />
  </AuthRequired>
);

export default HomeWithAuth;
