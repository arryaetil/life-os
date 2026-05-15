#!/usr/bin/env python3
"""
One-time admin script: delete all net_worth_snapshots and insert a single
clean baseline snapshot (total_net_worth = 15000, all components = 0 except other_assets).

Usage:
    python scripts/reset_networth.py [--dry-run]

Does NOT touch transactions or any other table.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
load_dotenv(REPO_ROOT / ".env")

from sqlalchemy import delete, select, func
from app.database import _engine, net_worth_snapshots, create_net_worth_snapshot, transactions

DRY_RUN = "--dry-run" in sys.argv


def main():
    # Sanity check: confirm transactions are untouched
    with _engine.connect() as conn:
        tx_count = conn.execute(select(func.count()).select_from(transactions)).scalar()
        snapshot_count = conn.execute(
            select(func.count()).select_from(net_worth_snapshots)
        ).scalar()

    print(f"Transactions in DB : {tx_count}  (will not be touched)")
    print(f"Net worth snapshots: {snapshot_count}  (will be deleted)")

    if DRY_RUN:
        print("\nDRY RUN — no changes made.")
        return

    # Delete all snapshots
    with _engine.connect() as conn:
        conn.execute(delete(net_worth_snapshots))
        conn.commit()
    print("Deleted all net worth snapshots.")

    # Insert clean baseline
    snapshot_id = create_net_worth_snapshot({
        "other_assets": 15000.0,
        "notes": "baseline",
    })
    print(f"Inserted baseline snapshot (id={snapshot_id}, total_net_worth=15000).")

    # Verify
    with _engine.connect() as conn:
        row = conn.execute(
            select(net_worth_snapshots).order_by(net_worth_snapshots.c.id.desc()).limit(1)
        ).fetchone()
    print(f"Verified: {dict(row._mapping)}")


if __name__ == "__main__":
    main()
