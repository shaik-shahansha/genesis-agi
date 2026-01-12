'use client';

import AdminPanel from '@/components/admin/AdminPanel';

export default function AdminPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-gray-100">
      <div className="max-w-7xl mx-auto p-6">
        <h1 className="text-3xl font-bold gradient-text mb-8">Admin Panel</h1>
        <AdminPanel />
      </div>
    </div>
  );
}
