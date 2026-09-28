"""Digital life state: what a being owes, owns and is responsible for.

See ``docs/v3/DIGITAL_LIFE_STATE.md``.

The distinction from memory is commitment rather than description: memory should
fade when it stops mattering, whereas an obligation must not fade at all. That
difference is why these are separate entities rather than memory tags.

Currently implements :mod:`~genesis.core.life.commitments` (Phase N1–N4).
Responsibilities, projects, habits, assets and calendar follow in the same
package so they share a home and a vocabulary.
"""

from genesis.core.life.commitments import (
    BENEFICIARY_MIND,
    BENEFICIARY_OWNER,
    BENEFICIARY_SELF,
    BENEFICIARY_THIRD_PARTY,
    Commitment,
    CommitmentError,
    CommitmentManager,
    CommitmentNotFoundError,
    CommitmentStatus,
    CommitmentTransitionError,
    TRANSITIONS,
    can_transition,
    capability_for_beneficiary,
)

__all__ = [
    "Commitment",
    "CommitmentStatus",
    "CommitmentManager",
    "CommitmentError",
    "CommitmentNotFoundError",
    "CommitmentTransitionError",
    "TRANSITIONS",
    "can_transition",
    "capability_for_beneficiary",
    "BENEFICIARY_OWNER",
    "BENEFICIARY_SELF",
    "BENEFICIARY_THIRD_PARTY",
    "BENEFICIARY_MIND",
]
