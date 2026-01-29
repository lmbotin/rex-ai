"""
Script to display all claims from the SQLite database with full details.
Run with: python data/show_claims.py
"""

from pathlib import Path
import sqlite3
import json
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

DB_PATH = Path(__file__).parent / "claims.db"

console = Console()


def format_datetime(dt_str: str) -> str:
    """Format ISO datetime to readable format."""
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return str(dt_str)[:16] if dt_str else ""


def truncate(text: str, max_len: int = 50) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ""
    text = str(text)
    if len(text) > max_len:
        return text[:max_len-3] + "..."
    return text


def safe_get(data: dict, *keys, default=""):
    """Safely get nested dictionary value."""
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key, default)
        else:
            return default
    return result if result is not None else default


def make_summary_table(rows: list) -> Table:
    """Create summary table with key claim info."""
    table = Table(
        title="📋 All Claims", 
        box=box.ROUNDED, 
        header_style="bold cyan",
        show_lines=True,
    )
    
    table.add_column("Claim ID", style="bold")
    table.add_column("Created", style="dim")
    table.add_column("Status", style="bold")
    table.add_column("Name")
    table.add_column("Policy #")
    table.add_column("Phone")
    table.add_column("Damage Type")
    table.add_column("Severity")
    table.add_column("Est. Cost")
    table.add_column("Address")
    table.add_column("Description")
    
    for row in rows:
        # Parse JSON fields
        claimant = json.loads(row["claimant"]) if row["claimant"] else {}
        incident = json.loads(row["incident"]) if row["incident"] else {}
        property_damage = json.loads(row["property_damage"]) if row["property_damage"] else {}
        
        # Extract key fields
        name = safe_get(claimant, "name")
        policy = safe_get(claimant, "policy_number")
        phone = safe_get(claimant, "contact_phone")
        damage_type = safe_get(incident, "damage_type")
        address = safe_get(incident, "incident_location")
        description = safe_get(incident, "incident_description")
        severity = safe_get(property_damage, "damage_severity")
        cost = safe_get(property_damage, "estimated_repair_cost")
        
        # Format cost
        try:
            cost_str = f"${float(cost):,.0f}" if cost and cost != "" else ""
        except (ValueError, TypeError):
            cost_str = str(cost) if cost else ""
        
        # Color-code status
        status = row["status"]
        if status == "approved":
            status_style = "[green]" + status + "[/green]"
        elif status in ("under_investigation", "denied"):
            status_style = "[red]" + status + "[/red]"
        elif status in ("pending_review", "in_progress"):
            status_style = "[yellow]" + status + "[/yellow]"
        else:
            status_style = status
        
        table.add_row(
            row["claim_id"],
            format_datetime(row["created_at"]),
            status_style,
            truncate(name, 20),
            truncate(policy, 15),
            truncate(phone, 15),
            truncate(damage_type, 12),
            truncate(severity, 10),
            cost_str,
            truncate(address, 25),
            truncate(description, 40),
        )
    
    return table


def make_full_table(rows: list) -> None:
    """Print each claim as a detailed card/panel."""
    for i, row in enumerate(rows):
        # Parse JSON fields
        claimant = json.loads(row["claimant"]) if row["claimant"] else {}
        incident = json.loads(row["incident"]) if row["incident"] else {}
        property_damage = json.loads(row["property_damage"]) if row["property_damage"] else {}
        evidence = json.loads(row["evidence"]) if row["evidence"] else {}
        validation = json.loads(row["validation_result"]) if row["validation_result"] else {}
        fraud = json.loads(row["fraud_result"]) if row["fraud_result"] else {}
        routing = json.loads(row["routing_result"]) if row["routing_result"] else {}
        
        # Create a detailed table for this claim
        table = Table(
            title=f"📋 Claim #{i+1}: {row['claim_id']}",
            box=box.ROUNDED,
            show_header=False,
            padding=(0, 1),
        )
        table.add_column("Field", style="bold cyan", width=20)
        table.add_column("Value", overflow="fold")
        
        # Basic info
        table.add_row("Status", row["status"])
        table.add_row("Source", row["source"])
        table.add_row("Created", format_datetime(row["created_at"]))
        if row["call_sid"]:
            table.add_row("Call SID", row["call_sid"])
        
        table.add_row("", "")  # Separator
        table.add_row("[bold]CLAIMANT[/bold]", "")
        table.add_row("Name", safe_get(claimant, "name") or "-")
        table.add_row("Policy #", safe_get(claimant, "policy_number") or "-")
        table.add_row("Phone", safe_get(claimant, "contact_phone") or "-")
        table.add_row("Email", safe_get(claimant, "contact_email") or "-")
        
        table.add_row("", "")
        table.add_row("[bold]INCIDENT[/bold]", "")
        table.add_row("Damage Type", safe_get(incident, "damage_type") or "-")
        table.add_row("Date", format_datetime(safe_get(incident, "incident_date")) or "-")
        table.add_row("Location", safe_get(incident, "incident_location") or "-")
        table.add_row("Description", safe_get(incident, "incident_description") or "-")
        
        table.add_row("", "")
        table.add_row("[bold]PROPERTY DAMAGE[/bold]", "")
        table.add_row("Property Type", safe_get(property_damage, "property_type") or "-")
        table.add_row("Room/Area", safe_get(property_damage, "room_location") or "-")
        table.add_row("Severity", safe_get(property_damage, "damage_severity") or "-")
        cost = safe_get(property_damage, "estimated_repair_cost")
        try:
            table.add_row("Est. Cost", f"${float(cost):,.2f}" if cost else "-")
        except (ValueError, TypeError):
            table.add_row("Est. Cost", str(cost) if cost else "-")
        
        table.add_row("", "")
        table.add_row("[bold]EVIDENCE[/bold]", "")
        table.add_row("Has Photos", "Yes" if safe_get(evidence, "has_damage_photos") else "No")
        table.add_row("Photo Count", str(safe_get(evidence, "damage_photo_count", 0)))
        table.add_row("Has Estimate", "Yes" if safe_get(evidence, "has_repair_estimate") else "No")
        missing = safe_get(evidence, "missing_evidence", [])
        table.add_row("Missing", ", ".join(missing) if missing else "-")
        
        if validation or fraud or routing:
            table.add_row("", "")
            table.add_row("[bold]PROCESSING[/bold]", "")
            if validation:
                table.add_row("Complete", "Yes" if safe_get(validation, "is_complete") else "No")
                missing_f = safe_get(validation, "missing_fields", [])
                if missing_f:
                    table.add_row("Missing Fields", ", ".join(missing_f))
            if fraud:
                score = float(safe_get(fraud, "fraud_score", 0) or 0)
                table.add_row("Fraud Score", f"{score:.2f}")
                indicators = safe_get(fraud, "fraud_indicators", [])
                if indicators:
                    table.add_row("Fraud Flags", ", ".join(indicators[:3]))
            if routing:
                table.add_row("Priority", safe_get(routing, "priority") or "-")
                table.add_row("Routing", safe_get(routing, "routing_decision") or "-")
                table.add_row("Reason", safe_get(routing, "routing_reason") or "-")
        
        console.print(table)
        console.print()


def show_claim_detail(row: dict):
    """Show detailed view of a single claim."""
    claimant = json.loads(row["claimant"]) if row["claimant"] else {}
    incident = json.loads(row["incident"]) if row["incident"] else {}
    property_damage = json.loads(row["property_damage"]) if row["property_damage"] else {}
    evidence = json.loads(row["evidence"]) if row["evidence"] else {}
    validation = json.loads(row["validation_result"]) if row["validation_result"] else {}
    fraud = json.loads(row["fraud_result"]) if row["fraud_result"] else {}
    routing = json.loads(row["routing_result"]) if row["routing_result"] else {}
    
    # New columns (may not exist in older DBs)
    transcript = []
    try:
        if row["transcript"]:
            transcript = json.loads(row["transcript"])
    except (KeyError, TypeError):
        pass
    
    console.print()
    console.print(Panel(f"[bold cyan]Claim: {row['claim_id']}[/bold cyan]", expand=False))
    
    # Basic info
    console.print("\n[bold]📌 Basic Info[/bold]")
    console.print(f"  Status: [bold]{row['status']}[/bold]")
    console.print(f"  Source: {row['source']}")
    console.print(f"  Created: {format_datetime(row['created_at'])}")
    console.print(f"  Updated: {format_datetime(row['updated_at'])}")
    if row["call_sid"]:
        console.print(f"  Call SID: {row['call_sid']}")
    
    # Claimant info
    console.print("\n[bold]👤 Claimant Information[/bold]")
    console.print(f"  Name: {safe_get(claimant, 'name') or '[dim]Not provided[/dim]'}")
    console.print(f"  Policy #: {safe_get(claimant, 'policy_number') or '[dim]Not provided[/dim]'}")
    console.print(f"  Phone: {safe_get(claimant, 'contact_phone') or '[dim]Not provided[/dim]'}")
    console.print(f"  Email: {safe_get(claimant, 'contact_email') or '[dim]Not provided[/dim]'}")
    
    # Incident info
    console.print("\n[bold]🔥 Incident Details[/bold]")
    console.print(f"  Damage Type: {safe_get(incident, 'damage_type') or '[dim]Not provided[/dim]'}")
    console.print(f"  Date: {format_datetime(safe_get(incident, 'incident_date')) or '[dim]Not provided[/dim]'}")
    console.print(f"  Location: {safe_get(incident, 'incident_location') or '[dim]Not provided[/dim]'}")
    
    description = safe_get(incident, 'incident_description')
    if description:
        console.print(f"  Description:")
        # Wrap long descriptions
        for line in str(description).split('\n'):
            console.print(f"    {line}")
    else:
        console.print(f"  Description: [dim]Not provided[/dim]")
    
    # Property damage details
    console.print("\n[bold]🏠 Property Damage Details[/bold]")
    console.print(f"  Property Type: {safe_get(property_damage, 'property_type') or '[dim]Not provided[/dim]'}")
    console.print(f"  Room/Area: {safe_get(property_damage, 'room_location') or '[dim]Not provided[/dim]'}")
    
    severity = safe_get(property_damage, 'damage_severity')
    if severity:
        severity_color = "green" if severity == "minor" else "yellow" if severity == "moderate" else "red"
        console.print(f"  Severity: [{severity_color}]{severity}[/{severity_color}]")
    else:
        console.print(f"  Severity: [dim]Not provided[/dim]")
    
    cost = safe_get(property_damage, 'estimated_repair_cost')
    if cost:
        try:
            console.print(f"  Est. Repair Cost: [bold]${float(cost):,.2f}[/bold]")
        except (ValueError, TypeError):
            console.print(f"  Est. Repair Cost: {cost}")
    else:
        console.print("  Est. Repair Cost: [dim]Not provided[/dim]")
    
    # Evidence
    console.print("\n[bold]📷 Evidence[/bold]")
    console.print(f"  Has Photos: {'✅ Yes' if safe_get(evidence, 'has_damage_photos') else '❌ No'}")
    photo_count = safe_get(evidence, 'damage_photo_count', 0)
    if photo_count:
        console.print(f"  Photo Count: {photo_count}")
    console.print(f"  Has Repair Estimate: {'✅ Yes' if safe_get(evidence, 'has_repair_estimate') else '❌ No'}")
    console.print(f"  Has Incident Report: {'✅ Yes' if safe_get(evidence, 'has_incident_report') else '❌ No'}")
    
    missing = safe_get(evidence, 'missing_evidence', [])
    if missing:
        console.print(f"  Missing: {', '.join(missing)}")
    
    # Processing results
    if validation or fraud or routing:
        console.print("\n[bold]⚙️ Processing Results[/bold]")
        
        if validation:
            is_complete = safe_get(validation, 'is_complete')
            console.print(f"  Complete: {'✅ Yes' if is_complete else '❌ No'}")
            missing_fields = safe_get(validation, 'missing_fields', [])
            if missing_fields:
                console.print(f"  Missing Fields: {', '.join(missing_fields)}")
            errors = safe_get(validation, 'validation_errors', [])
            if errors:
                console.print(f"  Errors: {', '.join(errors)}")
        
        if fraud:
            score = float(safe_get(fraud, 'fraud_score', 0) or 0)
            score_color = "green" if score < 0.3 else "yellow" if score < 0.7 else "red"
            console.print(f"  Fraud Score: [{score_color}]{score:.2f}[/{score_color}]")
            indicators = safe_get(fraud, 'fraud_indicators', [])
            if indicators:
                console.print(f"  Fraud Indicators:")
                for ind in indicators[:5]:
                    console.print(f"    - {ind}")
        
        if routing:
            console.print(f"  Priority: {safe_get(routing, 'priority')}")
            console.print(f"  Routing: {safe_get(routing, 'routing_decision')}")
            console.print(f"  Reason: {safe_get(routing, 'routing_reason')}")
            console.print(f"  Final Status: {safe_get(routing, 'final_status')}")
            next_actions = safe_get(routing, 'next_actions', [])
            if next_actions:
                console.print(f"  Next Actions:")
                for action in next_actions:
                    console.print(f"    - {action}")
    
    # Transcript (if available)
    if transcript:
        console.print("\n[bold]💬 Conversation Transcript[/bold]")
        for entry in transcript[-10:]:  # Show last 10 entries
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            role_color = "cyan" if role == "assistant" else "green"
            console.print(f"  [{role_color}]{role.upper()}[/{role_color}]: {truncate(content, 80)}")
        if len(transcript) > 10:
            console.print(f"  [dim]... and {len(transcript) - 10} more entries[/dim]")
    
    if row["notes"]:
        console.print(f"\n[bold]📝 Notes[/bold]: {row['notes']}")


def main(mode: str = "summary"):
    """
    Main function to display claims.
    
    Args:
        mode: "summary" (default), "table", or "all"
    """
    console.print(f"\n[bold]Database:[/bold] {DB_PATH.resolve()}\n")
    
    if not DB_PATH.exists():
        console.print("[yellow]No database found. Run the voice agent to create claims.[/yellow]")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Count total
    cur.execute("SELECT COUNT(*) FROM claims")
    total = cur.fetchone()[0]
    console.print(f"[bold]Total claims:[/bold] {total}\n")
    
    if total == 0:
        console.print("[yellow]No claims in database yet.[/yellow]")
        conn.close()
        return
    
    # Get all claims
    cur.execute("""
        SELECT * FROM claims
        ORDER BY created_at DESC
    """)
    rows = [dict(row) for row in cur.fetchall()]
    
    if mode == "table":
        # Show all claims as detailed table cards
        make_full_table(rows)
    elif mode == "all":
        # Show all claims in narrative detail
        for row in rows:
            show_claim_detail(row)
            console.print("\n" + "-"*70)
    else:
        # Default: summary table + most recent detail
        console.print(make_summary_table(rows))
        
        # Show status breakdown
        cur.execute("""
            SELECT status, COUNT(*) as n
            FROM claims
            GROUP BY status
            ORDER BY n DESC
        """)
        status_rows = cur.fetchall()
        
        console.print("\n[bold]Status Breakdown:[/bold]")
        for status, count in status_rows:
            console.print(f"  {status}: {count}")
        
        # Show detailed view of most recent claim
        if rows:
            console.print("\n" + "="*70)
            console.print("[bold]📄 Most Recent Claim - Full Details:[/bold]")
            show_claim_detail(rows[0])
        
        console.print("\n[dim]Options:[/dim]")
        console.print("[dim]  --table  Show all claims as detailed table cards[/dim]")
        console.print("[dim]  --all    Show narrative details for all claims[/dim]")
    
    conn.close()


if __name__ == "__main__":
    import sys
    
    if "--table" in sys.argv:
        main(mode="table")
    elif "--all" in sys.argv:
        main(mode="all")
    else:
        main(mode="summary")
