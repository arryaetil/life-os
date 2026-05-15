from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    MetaData, Table, insert, select, update, desc,
)
from app import config

# Railway uses postgres://, SQLAlchemy 2.0 needs postgresql://
_db_url = config.DATABASE_URL.replace("postgres://", "postgresql://", 1)
_engine = create_engine(_db_url)
_metadata = MetaData()

transactions = Table(
    "transactions",
    _metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("timestamp", String),
    Column("date", String),
    Column("week_start", String),
    Column("month", String),
    Column("type", String),
    Column("amount", Float),
    Column("description", String),
    Column("category", String),
    Column("tag", String, default=""),
    Column("payment_type", String, default=""),
    Column("is_impulse", Boolean, default=False),
    Column("is_necessary", String, default=""),
    Column("notes", String, default=""),
)

def init_db() -> None:
    _metadata.create_all(_engine)

def append_transaction(parsed: dict, category: str) -> int:
    with _engine.connect() as conn:
        result = conn.execute(
            insert(transactions).values(
                timestamp=parsed["timestamp"],
                date=parsed["date"],
                week_start=parsed["week_start"],
                month=parsed["month"],
                type=parsed["type"],
                amount=parsed["amount"],
                description=parsed["description"],
                category=category,
                tag="",
                payment_type="",
                is_impulse=parsed["is_impulse"],
                is_necessary="",
                notes="",
            )
        )
        conn.commit()
        return result.inserted_primary_key[0]

def get_all_transactions() -> list[dict]:
    with _engine.connect() as conn:
        result = conn.execute(select(transactions).order_by(transactions.c.id))
        return [dict(row._mapping) for row in result]

def undo_last_transaction() -> dict | None:
    with _engine.connect() as conn:
        result = conn.execute(
            select(transactions).order_by(desc(transactions.c.id)).limit(1)
        )
        row = result.fetchone()
        if row is None:
            return None
        record = dict(row._mapping)
        conn.execute(
            update(transactions)
            .where(transactions.c.id == record["id"])
            .values(notes="[UNDONE]")
        )
        conn.commit()
        return record
