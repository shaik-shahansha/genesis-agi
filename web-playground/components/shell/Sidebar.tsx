'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  mindIdFromPath,
  isActivePath,
  mindNav,
  platformNav,
  type NavItem,
} from '@/lib/navigation';
import { governanceApi } from '@/lib/governance';
import * as Icons from './icons';

type IconName = keyof typeof Icons;

function NavIcon({ name }: { name: string }) {
  const Component = (Icons as Record<string, unknown>)[name] as
    | React.ComponentType<{ className?: string }>
    | undefined;
  return Component ? <Component className="shrink-0" /> : <Icons.GridIcon className="shrink-0" />;
}

function NavLink({
  item,
  active,
  badge,
  onNavigate,
}: {
  item: NavItem;
  active: boolean;
  badge?: number;
  onNavigate?: () => void;
}) {
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      title={item.description}
      className={`nav-item ${active ? 'nav-item-active' : ''}`}
      aria-current={active ? 'page' : undefined}
    >
      <NavIcon name={item.icon} />
      <span className="truncate flex-1">{item.label}</span>
      {badge ? (
        <span
          className="badge badge-warning shrink-0 tabular-nums"
          aria-label={`${badge} awaiting your decision`}
        >
          {badge}
        </span>
      ) : null}
    </Link>
  );
}

export default function Sidebar({
  onNavigate,
  className = '',
}: {
  onNavigate?: () => void;
  className?: string;
}) {
  const pathname = usePathname();
  const mindId = mindIdFromPath(pathname);
  const [pendingApprovals, setPendingApprovals] = useState<number>(0);

  // Poll the approval count so the badge is real rather than decorative. It is
  // the one number that tells a user "something needs you", so a stale badge is
  // worse than no badge.
  useEffect(() => {
    if (!mindId) {
      setPendingApprovals(0);
      return;
    }
    let cancelled = false;

    const load = async () => {
      try {
        const summary = await governanceApi.summary(mindId);
        if (!cancelled) setPendingApprovals(summary.pending_approvals ?? 0);
      } catch {
        if (!cancelled) setPendingApprovals(0);
      }
    };

    load();
    const interval = window.setInterval(load, 20_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [mindId]);

  const platform = platformNav();
  const mind = mindId ? mindNav(mindId) : [];

  return (
    <nav
      className={`flex h-full w-64 flex-col border-r border-line bg-surface ${className}`}
      aria-label="Primary"
    >
      <div className="flex h-14 items-center gap-2.5 px-4 border-b border-line">
        <Link
          href="/"
          onClick={onNavigate}
          className="flex items-center gap-2.5 min-w-0"
          aria-label="Genesis home"
        >
          <span
            className="grid h-7 w-7 shrink-0 place-items-center rounded-md text-sm font-bold"
            style={{ backgroundColor: 'rgb(var(--accent))', color: 'rgb(var(--accent-fg))' }}
          >
            G
          </span>
          <span className="truncate text-sm font-semibold tracking-tight">Genesis</span>
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto px-2.5 py-3 space-y-5">
        {mindId && (
          <div>
            <p className="px-3 pb-1.5 text-[0.6875rem] font-semibold uppercase tracking-wider text-fg-subtle">
              This Mind
            </p>
            <div className="space-y-0.5">
              {mind.map((item) => (
                <NavLink
                  key={item.href}
                  item={item}
                  active={isActivePath(pathname, item.href)}
                  badge={item.label === 'Governance' ? pendingApprovals : undefined}
                  onNavigate={onNavigate}
                />
              ))}
            </div>
          </div>
        )}

        <div>
          <p className="px-3 pb-1.5 text-[0.6875rem] font-semibold uppercase tracking-wider text-fg-subtle">
            Platform
          </p>
          <div className="space-y-0.5">
            {platform.map((item) => (
              <NavLink
                key={item.href}
                item={item}
                active={isActivePath(pathname, item.href)}
                onNavigate={onNavigate}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="border-t border-line px-3 py-3">
        <p className="text-[0.6875rem] leading-relaxed text-fg-subtle">
          Every consequential action this Mind takes is evaluated, and either
          approved by you or recorded as a receipt.
        </p>
      </div>
    </nav>
  );
}
