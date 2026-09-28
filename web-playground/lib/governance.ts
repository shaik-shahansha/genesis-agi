/**
 * Governance API client.
 *
 * Typed wrappers around the twelve governance endpoints added in
 * `genesis/api/governance_routes.py`. Kept separate from `lib/api.ts` (the
 * legacy catch-all client) so the governance surface has real types - the
 * approval inbox and audit timeline are only useful if the UI cannot silently
 * render `undefined` for a field that matters, such as reversibility or a
 * refusal reason.
 */

import { getFirebaseToken } from './firebase';
import { apiUrl } from './urls';

// --------------------------------------------------------------------------- //
// Types (mirror genesis/governance/models.py)
// --------------------------------------------------------------------------- //

export type RiskLevel = 'R0' | 'R1' | 'R2' | 'R3' | 'R4' | 'R5';

export type PolicyDecisionKind =
  | 'allow'
  | 'allow_with_receipt'
  | 'require_approval'
  | 'deny'
  | 'emergency_stop';

export type ApprovalStatus =
  | 'PROPOSED'
  | 'POLICY_EVALUATED'
  | 'WAITING_FOR_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'EXPIRED'
  | 'CANCELLED'
  | 'EXECUTING'
  | 'COMPLETED'
  | 'FAILED'
  | 'ROLLED_BACK';

export interface ApprovalCard {
  approval_id: string;
  status: ApprovalStatus;
  action: string;
  why: string;
  risk_level: RiskLevel;
  expected_impact: string;
  data_accessed: string[];
  recipient: string | null;
  cost_essence: number;
  reversibility: string;
  rollback: string;
  scope: string;
  duration: string;
  expires_at: string | null;
  requires_human: boolean;
  approver_role: string | null;
  requested_by: string;
  requested_at: string;
}

export interface PermissionGrant {
  grant_id: string;
  approval_id: string;
  mind_id: string;
  action_name: string;
  parameters_hash: string;
  scope: string;
  issued_by: string;
  issued_at: string;
  expires_at: string | null;
  single_use: boolean;
  max_uses: number;
  consumed_at: string | null;
  revoked_at: string | null;
}

export interface ActionReceipt {
  receipt_id: string;
  action_id: string;
  action_name: string;
  mind_id: string;
  tenant_id: string | null;
  objective_id: string | null;
  outcome: string;
  created_at: string;
  requested_by: string;
  actor_type: string;
  intent: string;
  arguments: Record<string, unknown>;
  arguments_hash: string;
  risk_level: string;
  policy_decision: PolicyDecision;
  matched_rules: string[];
  approval_id: string | null;
  approver_id: string | null;
  approved_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  affected_resources: string[];
  artifacts: Record<string, unknown>[];
  evidence: Record<string, unknown>;
  model_invocations: number;
  cost_essence: number;
  error_class: string | null;
  error_message: string | null;
  rollback: Record<string, unknown> | null;
  correlation_id: string;
  integrity_hash: string;
  sequence: number;
}

export interface PolicyDecision {
  decision: PolicyDecisionKind;
  risk: {
    level: RiskLevel;
    label: string;
    explanation: string;
    contributions: { source: string; level: RiskLevel; detail: string }[];
    capability: CapabilityProfile | null;
  };
  reason_code: string;
  explanation: string;
  matched_rules: string[];
  policy_version: string;
  charter_version: string;
  required_scopes: string[];
  missing_scopes: string[];
  requires_human: boolean;
  approver_role: string | null;
  advisory: string | null;
  evaluated_at: string;
}

export interface CapabilityProfile {
  name: string;
  risk: RiskLevel;
  category: string;
  external: boolean;
  reversible: boolean;
  physical: boolean;
  destructive: boolean;
  data_sensitivity: string;
  cost_class: string;
  required_scopes: string[];
  prohibited_reason: string | null;
  catastrophic: boolean;
}

export interface AuditEvent {
  event_id: string;
  type: string;
  schema_version: number;
  timestamp: string;
  tenant_id: string | null;
  mind_id: string;
  actor_type: string;
  actor_id: string;
  correlation_id: string;
  causation_id: string | null;
  payload: Record<string, unknown>;
  payload_hash: string;
  prev_hash: string;
  integrity_hash: string;
  sequence: number;
  stream_key: string;
}

export interface EmergencyStopState {
  mind_id: string;
  engaged: boolean;
  reason: string;
  engaged_by: string;
  engaged_at: string | null;
  released_by: string | null;
  released_at: string | null;
}

export interface JournalVerification {
  ok: boolean;
  checked: number;
  broken_at: string | null;
  reason: string;
}

export interface GovernanceSummary {
  mind_id: string;
  policy_version: string;
  charter_version: string;
  emergency_stop: EmergencyStopState;
  pending_approvals: number;
  last_24h: {
    events: number;
    policy_evaluations: number;
    executed: number;
    failed: number;
    blocked: number;
    emergency_stops: number;
  };
  journal: JournalVerification;
}

// --------------------------------------------------------------------------- //
// Transport
// --------------------------------------------------------------------------- //

export class GovernanceApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'GovernanceApiError';
    this.status = status;
  }
}

async function authHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  try {
    const token = (await getFirebaseToken()) || localStorage.getItem('genesis_token');
    if (token) headers.Authorization = `Bearer ${token}`;
  } catch {
    /* Anonymous request; the server decides whether that is allowed. */
  }
  return headers;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: { ...(await authHeaders()), ...(init.headers ?? {}) },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body?.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new GovernanceApiError(detail || `Request failed (${response.status})`, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const base = (mindId: string) => `/api/v1/minds/${encodeURIComponent(mindId)}`;

// --------------------------------------------------------------------------- //
// Endpoints
// --------------------------------------------------------------------------- //

export const governanceApi = {
  /** Pending approvals, as the plain-language cards a human decides on. */
  async approvals(mindId: string, limit = 50): Promise<ApprovalCard[]> {
    const data = await request<{ approvals: ApprovalCard[] }>(
      `${base(mindId)}/approvals?limit=${limit}`
    );
    return data.approvals ?? [];
  },

  async approvalHistory(mindId: string, limit = 50): Promise<ApprovalCard[]> {
    const data = await request<{ approvals: ApprovalCard[] }>(
      `${base(mindId)}/approvals?status=REJECTED&limit=${limit}`
    );
    return data.approvals ?? [];
  },

  /** Approve and receive a parameter-bound, single-use, expiring grant. */
  async approve(
    mindId: string,
    approvalId: string,
    options: { note?: string; ttlSeconds?: number } = {}
  ): Promise<{ success: boolean; grant: PermissionGrant; note: string }> {
    return request(`${base(mindId)}/approvals/${approvalId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ note: options.note, ttl_seconds: options.ttlSeconds }),
    });
  },

  async reject(
    mindId: string,
    approvalId: string,
    note?: string
  ): Promise<{ success: boolean }> {
    return request(`${base(mindId)}/approvals/${approvalId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    });
  },

  async receipts(
    mindId: string,
    options: { outcome?: string; limit?: number } = {}
  ): Promise<ActionReceipt[]> {
    const params = new URLSearchParams();
    if (options.outcome) params.set('outcome', options.outcome);
    params.set('limit', String(options.limit ?? 50));
    const data = await request<{ receipts: ActionReceipt[] }>(
      `${base(mindId)}/receipts?${params.toString()}`
    );
    return data.receipts ?? [];
  },

  async timeline(
    mindId: string,
    options: { hours?: number; eventType?: string; limit?: number } = {}
  ): Promise<AuditEvent[]> {
    const params = new URLSearchParams();
    params.set('hours', String(options.hours ?? 24));
    if (options.eventType) params.set('event_type', options.eventType);
    params.set('limit', String(options.limit ?? 200));
    const data = await request<{ events: AuditEvent[] }>(
      `${base(mindId)}/timeline?${params.toString()}`
    );
    return data.events ?? [];
  },

  async verifyJournal(mindId: string): Promise<JournalVerification> {
    return request(`${base(mindId)}/journal/verify`);
  },

  async summary(mindId: string): Promise<GovernanceSummary> {
    return request(`${base(mindId)}/governance`);
  },

  async capabilities(mindId: string): Promise<CapabilityProfile[]> {
    const data = await request<{ capabilities: CapabilityProfile[] }>(
      `${base(mindId)}/capabilities`
    );
    return data.capabilities ?? [];
  },

  async emergencyStopState(mindId: string): Promise<EmergencyStopState> {
    return request(`${base(mindId)}/emergency-stop`);
  },

  /**
   * Engage or release the emergency stop.
   *
   * Engaging only needs read access (a concerned user must be able to halt a
   * Mind immediately); releasing needs the owner. The server enforces both.
   */
  async setEmergencyStop(
    mindId: string,
    engage: boolean,
    reason: string
  ): Promise<{ success: boolean; state: EmergencyStopState }> {
    return request(`${base(mindId)}/emergency-stop`, {
      method: 'POST',
      body: JSON.stringify({ engage, reason }),
    });
  },
};

// --------------------------------------------------------------------------- //
// Presentation helpers
// --------------------------------------------------------------------------- //

/** Human sentence for a risk level, matching ADR-0006. */
export const RISK_DESCRIPTIONS: Record<RiskLevel, string> = {
  R0: 'Read-only, or data you already own',
  R1: 'Reversible, inside the Mind’s own workspace',
  R2: 'Changes something outside the Mind’s workspace',
  R3: 'External communication, deployment, purchase, or admin',
  R4: 'Legal, medical, financial, employment, safety, or physical impact',
  R5: 'Prohibited',
};

export function riskTone(level: RiskLevel): 'neutral' | 'success' | 'info' | 'warning' | 'danger' {
  switch (level) {
    case 'R0':
      return 'neutral';
    case 'R1':
      return 'success';
    case 'R2':
      return 'info';
    case 'R3':
      return 'warning';
    case 'R4':
    case 'R5':
      return 'danger';
    default:
      return 'neutral';
  }
}

/** How an outcome should read to a human. */
export const OUTCOME_LABELS: Record<string, string> = {
  allowed: 'Allowed',
  executed: 'Executed',
  blocked: 'Refused',
  denied: 'Denied',
  requires_approval: 'Awaiting approval',
  failed: 'Failed',
  cancelled: 'Cancelled',
  rolled_back: 'Rolled back',
  emergency_stop: 'Halted',
};

export function outcomeTone(outcome: string): 'neutral' | 'success' | 'info' | 'warning' | 'danger' {
  switch (outcome) {
    case 'executed':
    case 'allowed':
      return 'success';
    case 'requires_approval':
      return 'info';
    case 'cancelled':
      return 'neutral';
    case 'failed':
      return 'warning';
    case 'blocked':
    case 'denied':
    case 'emergency_stop':
    case 'rolled_back':
      return 'danger';
    default:
      return 'neutral';
  }
}

export function formatWhen(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  const seconds = Math.round((Date.now() - date.getTime()) / 1000);
  if (Math.abs(seconds) < 60) return seconds >= 0 ? 'just now' : 'in a moment';
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return minutes >= 0 ? `${minutes}m ago` : `in ${-minutes}m`;
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return hours >= 0 ? `${hours}h ago` : `in ${-hours}h`;
  const days = Math.round(hours / 24);
  return days >= 0 ? `${days}d ago` : `in ${-days}d`;
}

/** Short, readable rendering of an opaque identifier. */
export function shortId(value: string | null | undefined, length = 10): string {
  if (!value) return '—';
  return value.length <= length ? value : `${value.slice(0, length)}…`;
}
