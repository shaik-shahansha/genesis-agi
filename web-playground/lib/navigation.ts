/**
 * The playground's route map, in one place.
 *
 * Two goals:
 *
 * 1. Every surface that belongs to a Mind lives under `/minds/{id}/...`. The
 *    repository previously had both `/mind/{id}` and `/minds/{id}` with
 *    different content and no cross-links, which is part of why the app felt
 *    incoherent.
 * 2. In development, a navigation entry that points at a route which no longer
 *    exists logs a warning instead of silently 404ing. This caught a stale link
 *    during the revamp.
 */

export interface NavItem {
  label: string;
  href: string;
  /** Icon component name from `components/shell/icons`. */
  icon: string;
  description?: string;
  /** Shown in the topbar command palette. */
  keywords?: string[];
}

export function mindRoutes(mindId: string) {
  return {
    overview: `/minds/${mindId}`,
    conversation: `/chat/${mindId}`,
    governance: `/minds/${mindId}/governance`,
    receipts: `/minds/${mindId}/receipts`,
    timeline: `/minds/${mindId}/timeline`,
    capabilities: `/minds/${mindId}/capabilities`,
  };
}

/** Nav shown once a Mind is in context. */
export function mindNav(mindId: string): NavItem[] {
  const routes = mindRoutes(mindId);
  return [
    {
      label: 'Overview',
      href: routes.overview,
      icon: 'GaugeIcon',
      description: 'State, memory, personality, autonomy',
      keywords: ['profile', 'state', 'status'],
    },
    {
      label: 'Conversation',
      href: routes.conversation,
      icon: 'ChatIcon',
      description: 'Talk to this Mind',
      keywords: ['chat', 'talk', 'message'],
    },
    {
      label: 'Governance',
      href: routes.governance,
      icon: 'ShieldIcon',
      description: 'Approvals awaiting your decision, and the emergency stop',
      keywords: ['approval', 'approvals', 'inbox', 'permission', 'stop', 'halt', 'policy'],
    },
    {
      label: 'Receipts',
      href: routes.receipts,
      icon: 'ReceiptIcon',
      description: 'Every action this Mind attempted, including the refused ones',
      keywords: ['actions', 'receipt', 'audit', 'blocked', 'history'],
    },
    {
      label: 'Timeline',
      href: routes.timeline,
      icon: 'ClockIcon',
      description: 'The event journal: what happened, in order',
      keywords: ['events', 'journal', 'timeline', 'log'],
    },
    {
      label: 'Capabilities',
      href: routes.capabilities,
      icon: 'PlugIcon',
      description: 'What this Mind can do and what each capability is allowed to do alone',
      keywords: ['permissions', 'risk', 'skills', 'tools', 'scopes'],
    },
  ];
}

/** Nav that is not scoped to one Mind. */
export function platformNav(): NavItem[] {
  return [
    {
      label: 'All Minds',
      href: '/',
      icon: 'GridIcon',
      description: 'Every Mind you can access',
      keywords: ['dashboard', 'home', 'list'],
    },
    {
      label: 'New Mind',
      href: '/create',
      icon: 'PlusIcon',
      description: 'Create a Mind',
      keywords: ['create', 'new', 'birth'],
    },
    {
      label: 'Environments',
      href: '/environments',
      icon: 'GlobeIcon',
      description: 'Shared spaces Minds can inhabit',
      keywords: ['world', 'space', 'room'],
    },
    {
      label: 'Marketplace',
      href: '/marketplace',
      icon: 'StoreIcon',
      description: 'Skills and Minds published by others',
      keywords: ['store', 'buy', 'plugins', 'skills'],
    },
    {
      label: 'Settings',
      href: '/settings',
      icon: 'SettingsIcon',
      description: 'Models, providers, keys',
      keywords: ['config', 'keys', 'providers'],
    },
  ];
}

/**
 * Extract the Mind id from a pathname.
 *
 * Layouts in the App Router do not reliably expose the dynamic segment, so the
 * id is read from the path. `/chat/{id}` is included because conversation is a
 * Mind surface even though it lives under its own segment.
 */
export function mindIdFromPath(pathname: string | null): string | null {
  if (!pathname) return null;
  const match = pathname.match(/^\/(?:minds|mind|chat)\/([^/?#]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

/** True when `href` is the active route (exact, or the active prefix). */
export function isActivePath(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  if (href === '/') return pathname === '/';
  return pathname === href || pathname.startsWith(`${href}/`);
}
