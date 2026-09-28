'use client';

import { DetailRow, Section, StatusBadge } from '@/components/governance/primitives';
import { LockIcon } from '@/components/shell/icons';

interface IdentityTabProps {
  mind: any;
}

/**
 * The Mind's identity card.
 *
 * This used to render a gradient "VERIFIED DIGITAL IDENTITY / official digital
 * identity credential issued by Genesis Minds" card. None of that is true:
 * `gmid` is a local identifier with no signature behind it, so nothing here can
 * be verified by anyone. Presenting a self-issued string as a credential is the
 * exact class of claim §4 of the developer guide exists to catch, and the fix is
 * to say what the value actually is.
 */
export default function IdentityTab({ mind }: IdentityTabProps) {
  const getInitials = (name: string) => {
    if (!name) return '??';
    return name
      .split(' ')
      .map((word) => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const statusTone =
    mind.status === 'active' ? 'success' : mind.status === 'sleeping' ? 'warning' : 'neutral';

  const traits = mind.personality ? Object.entries(mind.personality).slice(0, 8) : [];

  return (
    <div className="space-y-6">
      <Section title="Identity">
        <div className="card overflow-hidden">
          <div className="flex flex-wrap items-start gap-6">
            <div className="grid h-24 w-24 flex-shrink-0 place-items-center rounded-card bg-surface-3 text-3xl font-semibold text-fg-muted">
              {getInitials(mind.name)}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-3">
                <h3 className="text-xl font-semibold text-fg">{mind.name}</h3>
                <StatusBadge tone={statusTone}>
                  {mind.status ? mind.status : 'unknown'}
                </StatusBadge>
              </div>
              <p className="mt-1 font-mono text-xs text-fg-muted">{mind.gmid}</p>

              <dl className="mt-4">
                <DetailRow label="Age">{mind.age || '—'}</DetailRow>
                <DetailRow label="Emotion">
                  <span className="capitalize">{mind.current_emotion || 'neutral'}</span>
                </DetailRow>
                <DetailRow label="Template">
                  <span className="capitalize">
                    {mind.template ? mind.template.split('/').pop()?.replace(/_/g, ' ') : 'N/A'}
                  </span>
                </DetailRow>
                <DetailRow label="Model">{mind.llm_model || 'N/A'}</DetailRow>
                <DetailRow label="Creator">
                  {mind.creator_email || mind.creator || 'N/A'}
                </DetailRow>
                <DetailRow label="Created">{formatDate(mind.created_at)}</DetailRow>
              </dl>
            </div>
          </div>
        </div>
      </Section>

      {(mind.purpose || mind.role) && (
        <Section title="Stated purpose">
          <div className="card space-y-4">
            {mind.purpose && (
              <div>
                <p className="label mb-1">Purpose</p>
                <p className="max-w-prose text-sm text-fg">{mind.purpose}</p>
              </div>
            )}
            {mind.role && (
              <div>
                <p className="label mb-1">Role</p>
                <p className="max-w-prose text-sm text-fg">{mind.role}</p>
              </div>
            )}
          </div>
        </Section>
      )}

      {traits.length > 0 && (
        <Section
          title="Personality"
          description="Trait values as configured. These bias tone and initiative; they are not measured."
        >
          <div className="flex flex-wrap gap-2">
            {traits.map(([trait, value]: [string, any]) => (
              <div key={trait} className="card-flat min-w-[7rem]">
                <p className="text-xs capitalize text-fg-muted">{trait.replace(/_/g, ' ')}</p>
                <p className="mt-0.5 text-sm font-semibold tabular-nums text-fg">
                  {typeof value === 'number' ? value.toFixed(2) : String(value)}
                </p>
              </div>
            ))}
          </div>
        </Section>
      )}

      <Section title="What this identifier is">
        <div className="card">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 text-fg-subtle">
              <LockIcon />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm text-fg-muted">
                <span className="font-medium text-fg">{mind.gmid}</span> is a local identifier. It
                uniquely names this Mind on this installation and nothing more. It is not signed, it
                is not issued by anyone, and no third party can verify it. Another installation can
                hand out the same string to a different Mind.
              </p>
              <p className="mt-3 text-sm text-fg-muted">
                Do not treat it as proof of origin, and do not paste it anywhere that would.
                Portable signed identity — the thing that would make a GMID verifiable across
                installations — is not built. See {/* keep the reference textual, not a link */}
                <span className="text-fg-subtle"> PORTABLE_BEING_FORMAT.md</span> for the intended
                shape.
              </p>
            </div>
          </div>
        </div>
      </Section>
    </div>
  );
}

