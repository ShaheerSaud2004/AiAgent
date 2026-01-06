"""
Organization management for multi-tenant SaaS.
"""
import aiosqlite
from typing import Dict, List, Optional
from database import DB_PATH
from auth import get_password_hash


async def create_organization(name: str, subdomain: str = None) -> int:
    """Create a new organization."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO organizations (name, subdomain) VALUES (?, ?)",
            (name, subdomain or name.lower().replace(" ", "-"))
        )
        await db.commit()
        return cursor.lastrowid


async def create_user(
    email: str,
    password: str,
    organization_id: int,
    full_name: str = None,
    role: str = "admin"
) -> int:
    """Create a new user."""
    password_hash = get_password_hash(password)
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO users (email, password_hash, organization_id, full_name, role)
               VALUES (?, ?, ?, ?, ?)""",
            (email, password_hash, organization_id, full_name or email.split("@")[0], role)
        )
        await db.commit()
        return cursor.lastrowid


async def get_organization(organization_id: int) -> Optional[Dict]:
    """Get organization by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM organizations WHERE id = ?", (organization_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_organization_users(organization_id: int) -> List[Dict]:
    """Get all users in an organization."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, email, full_name, role, is_active, created_at FROM users WHERE organization_id = ?",
            (organization_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_organization_by_phone(phone_number: str) -> Optional[int]:
    """Get organization ID by phone number (from businesses table)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT organization_id FROM businesses 
               WHERE phone_number = ? AND is_active = 1 
               LIMIT 1""",
            (phone_number,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
        
        # Fallback: get first organization (for development)
        async with db.execute("SELECT id FROM organizations LIMIT 1") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

