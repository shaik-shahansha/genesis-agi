import type { ReactNode } from 'react';

/**
 * Standard page header used by every new surface.
 *
 * Pages previously invented their own headers (some had none, some a hero, some
 * a bare `<h1>`), which is a large part of why the playground felt
 * inconsistent. One component, one rhythm.
 */
export default function PageHeader({
  title,
  description,
  breadcrumb,
  actions,
}: {
  title: ReactNode;
  description?: ReactNode;
  breadcrumb?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="border-b border-line bg-surface/60">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        {breadcrumb && <div className="mb-2 text-xs text-fg-subtle">{breadcrumb}</div>}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="page-title">{title}</h1>
            {description && (
              <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-fg-muted">
                {description}
              </p>
            )}
          </div>
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </div>
      </div>
    </div>
  );
}
