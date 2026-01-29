#!/usr/bin/env python3
"""
View stored claims from the database.

Usage:
    python view_claims.py              # List all claims
    python view_claims.py CLM-xxx      # View specific claim details
    python view_claims.py --status submitted  # Filter by status
    python view_claims.py --source voice      # Filter by source
    python view_claims.py --stats             # Show statistics
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.storage import get_claim_store, StoredClaim


def format_datetime(iso_str: str) -> str:
    """Format ISO datetime string for display."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_str


def print_claim_list(claims: list):
    """Print a table of claims."""
    if not claims:
        print("\nNo claims found.")
        return
    
    print(f"\n{'─' * 90}")
    print(f"{'Claim ID':<25} {'Status':<15} {'Source':<10} {'Created':<20} {'Claimant':<20}")
    print(f"{'─' * 90}")
    
    for claim in claims:
        claimant_name = claim.claimant.get("name", "Unknown")[:18]
        created = format_datetime(claim.created_at)[:19]
        print(f"{claim.claim_id:<25} {claim.status:<15} {claim.source:<10} {created:<20} {claimant_name:<20}")
    
    print(f"{'─' * 90}")
    print(f"Total: {len(claims)} claim(s)")


def print_claim_detail(claim: StoredClaim):
    """Print detailed view of a single claim."""
    print(f"\n{'═' * 70}")
    print(f"  CLAIM DETAILS: {claim.claim_id}")
    print(f"{'═' * 70}")
    
    # Status & Metadata
    print(f"\n📋 STATUS & METADATA")
    print(f"   Status:     {claim.status}")
    print(f"   Source:     {claim.source}")
    print(f"   Created:    {format_datetime(claim.created_at)}")
    print(f"   Updated:    {format_datetime(claim.updated_at)}")
    if claim.call_sid:
        print(f"   Call SID:   {claim.call_sid}")
    if claim.session_id:
        print(f"   Session:    {claim.session_id}")
    if claim.notes:
        print(f"   Notes:      {claim.notes}")
    
    # Claimant
    print(f"\n👤 CLAIMANT")
    if claim.claimant:
        for key, value in claim.claimant.items():
            if value:
                print(f"   {key}: {value}")
    else:
        print("   (No claimant data)")
    
    # Incident
    print(f"\n🔥 INCIDENT")
    if claim.incident:
        for key, value in claim.incident.items():
            if value:
                if key == "incident_description" and len(str(value)) > 60:
                    print(f"   {key}: {str(value)[:60]}...")
                else:
                    print(f"   {key}: {value}")
    else:
        print("   (No incident data)")
    
    # Property Damage
    print(f"\n🏠 PROPERTY DAMAGE")
    if claim.property_damage:
        for key, value in claim.property_damage.items():
            if value:
                if key == "estimated_repair_cost":
                    print(f"   {key}: ${value:,.2f}")
                else:
                    print(f"   {key}: {value}")
    else:
        print("   (No property damage data)")
    
    # Evidence
    print(f"\n📎 EVIDENCE")
    if claim.evidence:
        for key, value in claim.evidence.items():
            if value:
                print(f"   {key}: {value}")
    else:
        print("   (No evidence data)")
    
    # Processing Results
    if claim.validation_result or claim.fraud_result or claim.routing_result:
        print(f"\n⚙️  PROCESSING RESULTS")
        
        if claim.validation_result:
            print(f"\n   Validation:")
            vr = claim.validation_result
            print(f"      Complete: {vr.get('is_complete', 'N/A')}")
            if vr.get("missing_fields"):
                print(f"      Missing: {', '.join(vr['missing_fields'][:5])}")
            if vr.get("errors"):
                print(f"      Errors: {', '.join(vr['errors'][:3])}")
        
        if claim.fraud_result:
            print(f"\n   Fraud Analysis:")
            fr = claim.fraud_result
            print(f"      Score: {fr.get('score', 'N/A')}")
            if fr.get("indicators"):
                print(f"      Indicators:")
                for ind in fr["indicators"][:3]:
                    print(f"         - {ind}")
        
        if claim.routing_result:
            print(f"\n   Routing:")
            rr = claim.routing_result
            print(f"      Decision: {rr.get('decision', 'N/A')}")
            print(f"      Priority: {rr.get('priority', 'N/A')}")
            print(f"      Reason: {rr.get('reason', 'N/A')}")
    
    print(f"\n{'═' * 70}")


def print_stats(store):
    """Print database statistics."""
    total = store.count()
    
    print(f"\n{'═' * 50}")
    print(f"  DATABASE STATISTICS")
    print(f"{'═' * 50}")
    print(f"\n  Total Claims: {total}")
    
    # By status
    print(f"\n  By Status:")
    for status in ["draft", "submitted", "processing", "approved", "denied", "pending_review"]:
        count = store.count(status=status)
        if count > 0:
            print(f"    {status}: {count}")
    
    # By source
    print(f"\n  By Source:")
    claims = store.list_all(limit=1000)
    sources = {}
    for c in claims:
        sources[c.source] = sources.get(c.source, 0) + 1
    for source, count in sorted(sources.items()):
        print(f"    {source}: {count}")
    
    print(f"\n  Database: {store.db_path}")
    print(f"{'═' * 50}")


def export_claim(claim: StoredClaim, format: str = "json"):
    """Export a claim to JSON."""
    data = {
        "claim_id": claim.claim_id,
        "status": claim.status,
        "source": claim.source,
        "created_at": claim.created_at,
        "updated_at": claim.updated_at,
        "claimant": claim.claimant,
        "incident": claim.incident,
        "property_damage": claim.property_damage,
        "evidence": claim.evidence,
        "validation_result": claim.validation_result,
        "fraud_result": claim.fraud_result,
        "routing_result": claim.routing_result,
        "call_sid": claim.call_sid,
        "notes": claim.notes,
    }
    print(json.dumps(data, indent=2))


def main():
    parser = argparse.ArgumentParser(description="View stored claims")
    parser.add_argument("claim_id", nargs="?", help="Specific claim ID to view")
    parser.add_argument("--status", help="Filter by status")
    parser.add_argument("--source", help="Filter by source (text, image, voice)")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--export", action="store_true", help="Export claim as JSON")
    parser.add_argument("--limit", type=int, default=50, help="Max claims to list")
    
    args = parser.parse_args()
    
    store = get_claim_store()
    
    if args.stats:
        print_stats(store)
        return
    
    if args.claim_id:
        # View specific claim
        claim = store.get(args.claim_id)
        if claim:
            if args.export:
                export_claim(claim)
            else:
                print_claim_detail(claim)
        else:
            print(f"\nClaim not found: {args.claim_id}")
            sys.exit(1)
    else:
        # List claims
        claims = store.list_all(
            status=args.status,
            source=args.source,
            limit=args.limit
        )
        print_claim_list(claims)


if __name__ == "__main__":
    main()
