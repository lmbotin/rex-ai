"""
Storage module for persisting claims and processing results.

Provides SQLite-based storage for:
- Property damage claims
- Processing results (validation, fraud, routing)
- Call/session metadata
"""

from .claim_store import (
    ClaimStore,
    StoredClaim,
    get_claim_store,
    save_claim,
    get_claim,
    list_claims,
    update_claim_status,
)

__all__ = [
    "ClaimStore",
    "StoredClaim",
    "get_claim_store",
    "save_claim",
    "get_claim",
    "list_claims",
    "update_claim_status",
]
