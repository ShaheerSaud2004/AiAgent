"""
Organization management for multi-tenant SaaS.
"""
from typing import Dict, List, Optional
from database import get_pool
from auth import get_password_hash


async def create_organization(name: str, subdomain: str = None) -> int:
    """Create a new organization."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        org_id = await conn.fetchval(
            "INSERT INTO organizations (name, subdomain) VALUES ($1, $2) RETURNING id",
            name, subdomain or name.lower().replace(" ", "-")
        )
        return org_id


async def create_user(
    email: str,
    password: str,
    organization_id: int,
    full_name: str = None,
    role: str = "admin"
) -> int:
    """Create a new user."""
    password_hash = get_password_hash(password)
    pool = await get_pool()
    async with pool.acquire() as conn:
        user_id = await conn.fetchval(
            """INSERT INTO users (email, password_hash, organization_id, full_name, role)
               VALUES ($1, $2, $3, $4, $5) RETURNING id""",
            email, password_hash, organization_id, full_name or email.split("@")[0], role
        )
        return user_id


async def get_organization(organization_id: int) -> Optional[Dict]:
    """Get organization by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM organizations WHERE id = $1", organization_id)
        return dict(row) if row else None


async def get_organization_users(organization_id: int) -> List[Dict]:
    """Get all users in an organization."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, email, full_name, role, is_active, created_at FROM users WHERE organization_id = $1",
            organization_id
        )
        return [dict(row) for row in rows]


async def get_organization_by_phone(phone_number: str) -> Optional[int]:
    """Get organization ID by phone number (from businesses table)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        org_id = await conn.fetchval(
            """SELECT organization_id FROM businesses 
               WHERE phone_number = $1 AND is_active = true 
               LIMIT 1""",
            phone_number
        )
        
        if org_id:
            return org_id
        
        # Fallback: get first organization (for development)
        org_id = await conn.fetchval("SELECT id FROM organizations LIMIT 1")
        return org_id
