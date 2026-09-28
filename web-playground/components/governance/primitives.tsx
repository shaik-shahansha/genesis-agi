'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { RISK_DESCRIPTIONS, riskTone, type RiskLevel } from '@/lib/governance';
import { AlertIcon, RefreshIcon } from '@/components/shell/icons';

/**
 * Risk badge.
 *
 * The level is always rendered as text (`R3`), never conveyed by colour alone,
 * and the tooltip spells out the ADR-0006 meaning. Risk is the single most
 * consequential thing a user reads on these screens, so it must not depend on
 * colour perception.
 */
export function RiskBadge({ level, showDescription = false }: { level: string; showDescription?: boolean }) {
  const tone = riskTone(level as RiskLevel);
  const description = RISK_DESCRIPTIONS[level as RiskLevel];
  return (
    <span className={`badge badge-${tone}`} title={description}>
      <span className="font-semibold tabular-nums">{level}</span>
      {showDescription && description && <span className="font-normal">· {description}</span>}
    </span>
  );
}

export function StatusBadge({ tone, children }: { tone: string; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state rounded-card border border-line bg-surface">
      <div className="mb-3 grid h-10 w-10 place-items-center rounded-full bg-surface-2 text-fg-subtle">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden="true">
          <path d="M5 7h14M5 12h14M5 17h8" strokeLinecap="round" />
        </svg>
      </div>
      <p className="text-sm font-medium text-fg">{title}</p>
      {description && <p className="mt-1 max-w-md text-sm text-fg-muted">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
  hint,
}: {
  message: string;
  onRetry?: () => void;
  hint?: string;
}) {
  return (
    <div className="rounded-card border border-danger/40 bg-danger/5 p-5">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 text-danger">
          <AlertIcon />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-fg">Could not load this</p>
          <p className="mt-1 text-sm text-fg-muted break-words">{message}</p>
          {hint && <p className="mt-2 text-xs text-fg-subtle">{hint}</p>}
          {onRetry && (
            <button type="button" onClick={onRetry} className="btn-secondary btn-sm mt-3">
              <RefreshIcon className="h-4 w-4" />
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function LoadingRows({ rows = 3, label = 'Loading' }: { rows?: number; label?: string }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label={label}>
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="rounded-card border border-line bg-surface p-5">
          <div className="skeleton h-4 w-1/3" />
          <div className="skeleton mt-3 h-3 w-2/3" />
          <div className="skeleton mt-2 h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}

/** Section wrapper with a consistent heading and optional actions. */
export function Section({
  title,
  description,
  actions,
  children,
  className = '',
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={className}>
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="section-title">{title}</h2>
          {description && <p className="mt-0.5 text-xs text-fg-muted">{description}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

/** A labelled key/value row, used in receipt and approval detail. */
export function DetailRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[9rem_1fr] gap-3 py-1.5 text-sm">
      <dt className="text-fg-muted">{label}</dt>
      <dd className="min-w-0 break-words text-fg">{children}</dd>
    </div>
  );
}

/** A link that reads as a link without looking like a primary action. */
export function InlineLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="text-accent underline-offset-2 hover:underline">
      {children}
    </Link>
  );
}
