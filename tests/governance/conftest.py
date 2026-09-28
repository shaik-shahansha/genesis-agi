"""Fixtures for governance tests.

Every test gets a fresh in-memory store, so the tests are hermetic and do not
touch the workspace database or the JSONL action log.
"""

from __future__ import annotations

import pytest

from genesis.governance import (
    ApprovalService,
    AuditService,
    EmergencyStopService,
    GovernanceGate,
    InMemoryGovernanceStore,
    PolicyEngine,
)


@pytest.fixture
def store() -> InMemoryGovernanceStore:
    return InMemoryGovernanceStore()


@pytest.fixture
def audit(store) -> AuditService:
    return AuditService(store=store)


@pytest.fixture
def approvals(store, audit) -> ApprovalService:
    return ApprovalService(store=store, audit=audit)


@pytest.fixture
def estop(audit) -> EmergencyStopService:
    return EmergencyStopService(audit=audit)


@pytest.fixture
def engine() -> PolicyEngine:
    return PolicyEngine()


@pytest.fixture
def gate(engine, approvals, audit, estop) -> GovernanceGate:
    return GovernanceGate(
        engine=engine, approvals=approvals, audit=audit, emergency_stop=estop
    )
