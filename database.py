"""
Database models and functions for storing call data and statistics.
Uses PostgreSQL (Supabase) for persistent storage.
"""

import asyncpg
import json
from datetime import datetime
from typing import Dict, List, Optional
import os

# Get database URL from environment (Supabase connection string)
DATABASE_URL = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")

# Connection pool (will be initialized on first use)
_pool = None

async def get_pool():
    """Get or create database connection pool."""
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise ValueError(
                "DATABASE_URL or POSTGRES_URL environment variable must be set. "
                "Please add POSTGRES_URL to your Vercel environment variables."
            )
        try:
            _pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
        except Exception as e:
            raise ValueError(
                f"Failed to connect to Postgres database: {str(e)}. "
                "Please check your POSTGRES_URL in Vercel environment variables."
            ) from e
    return _pool

async def init_db():
    """Initialize the database with required tables."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Organizations table (multi-tenancy)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                subdomain VARCHAR(255) UNIQUE,
                subscription_tier VARCHAR(50) DEFAULT 'free',
                stripe_customer_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                organization_id INTEGER,
                role VARCHAR(50) DEFAULT 'admin',
                full_name VARCHAR(255),
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
            )
        """)
        
        # Businesses table (now with organization_id)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(50) NOT NULL,
                is_active BOOLEAN DEFAULT false,
                greeting TEXT,
                assistant_name VARCHAR(100),
                system_prompt TEXT,
                menu_reference TEXT,
                phone_number VARCHAR(50),
                email VARCHAR(255),
                address TEXT,
                config_json TEXT,
                voice VARCHAR(100) DEFAULT 'Polly.Matthew-Neural',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
            )
        """)
        
        # Calls table (now with organization_id)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                id SERIAL PRIMARY KEY,
                call_sid VARCHAR(255) UNIQUE NOT NULL,
                caller_phone VARCHAR(50) NOT NULL,
                organization_id INTEGER NOT NULL,
                business_id INTEGER,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration_seconds INTEGER,
                is_emergency BOOLEAN DEFAULT false,
                status VARCHAR(50) DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE SET NULL
            )
        """)
        
        # Conversations table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                call_sid VARCHAR(255) NOT NULL,
                user_input TEXT,
                assistant_response TEXT,
                turn_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (call_sid) REFERENCES calls(call_sid) ON DELETE CASCADE
            )
        """)
        
        # Appointments table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id SERIAL PRIMARY KEY,
                call_sid VARCHAR(255) NOT NULL,
                caller_phone VARCHAR(50) NOT NULL,
                patient_status VARCHAR(50),
                reason TEXT,
                insurance VARCHAR(255),
                preferred_time VARCHAR(255),
                caller_name VARCHAR(255),
                is_emergency BOOLEAN DEFAULT false,
                booking_status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (call_sid) REFERENCES calls(call_sid) ON DELETE CASCADE
            )
        """)
        
        # Orders table (now with organization_id)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                call_sid VARCHAR(255) NOT NULL,
                organization_id INTEGER NOT NULL,
                caller_phone VARCHAR(50) NOT NULL,
                customer_name VARCHAR(255),
                items TEXT,
                order_type VARCHAR(50),
                delivery_address TEXT,
                pickup_name VARCHAR(255),
                phone_number VARCHAR(50),
                special_instructions TEXT,
                payment_method VARCHAR(50),
                total_estimate VARCHAR(50),
                order_status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY (call_sid) REFERENCES calls(call_sid) ON DELETE CASCADE
            )
        """)
        
        # Add organization_id to existing tables if they don't have it (migration)
        # Postgres doesn't support IF NOT EXISTS for ALTER TABLE, so we check first
        try:
            result = await conn.fetchval("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'businesses' AND column_name = 'organization_id'
            """)
            if not result:
                await conn.execute("ALTER TABLE businesses ADD COLUMN organization_id INTEGER")
        except:
            pass
        
        try:
            result = await conn.fetchval("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'calls' AND column_name = 'organization_id'
            """)
            if not result:
                await conn.execute("ALTER TABLE calls ADD COLUMN organization_id INTEGER")
        except:
            pass
        
        try:
            result = await conn.fetchval("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'orders' AND column_name = 'organization_id'
            """)
            if not result:
                await conn.execute("ALTER TABLE orders ADD COLUMN organization_id INTEGER")
        except:
            pass
        
        # Add voice column if it doesn't exist (for existing databases)
        try:
            result = await conn.fetchval("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'businesses' AND column_name = 'voice'
            """)
            if not result:
                await conn.execute("ALTER TABLE businesses ADD COLUMN voice VARCHAR(100) DEFAULT 'Polly.Matthew-Neural'")
        except Exception as e:
            pass  # Column already exists or other error
        
        # Update existing businesses to have voice if null
        await conn.execute("UPDATE businesses SET voice = 'Polly.Matthew-Neural' WHERE voice IS NULL OR voice = ''")
        
        # Initialize default businesses if they don't exist (legacy - for existing data)
        await init_default_businesses()
        
        # Migrate existing data to default organization if needed
        await migrate_existing_data_to_org()


async def init_default_businesses():
    """Initialize default business configurations."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if businesses exist
        count = await conn.fetchval("SELECT COUNT(*) FROM businesses")
        
        if count == 0:
            # Load menu reference for pizza
            menu_ref = ""
            try:
                with open("menu_reference.txt", "r") as f:
                    menu_ref = f.read()
            except:
                menu_ref = "Menu information not available."
            
            # Pizza Restaurant - Optimized for speed
            pizza_prompt = f"""You are John, a pizza order taker for Nunzio's Pizza.

MENU: {menu_ref}

RULES: Brief responses (1 sentence, max 12 words). Be friendly, efficient. Repeat back items. Don't repeat questions.

COLLECT: Items (pizza, size, qty) → Delivery/pickup → Address/name → Confirm → Done.

FLOW: Greet → Listen → Ask missing info → Confirm order → Thank.

If item in MENU, it exists. Match menu names exactly."""
            
            # Get default organization for legacy businesses
            default_org_id = await conn.fetchval("SELECT id FROM organizations LIMIT 1")
            
            if not default_org_id:
                # Create default organization
                default_org_id = await conn.fetchval(
                    "INSERT INTO organizations (name, subdomain) VALUES ($1, $2) RETURNING id",
                    "Default Organization", "default"
                )
                if not default_org_id:
                    # If still None, try to get it again
                    default_org_id = await conn.fetchval("SELECT id FROM organizations WHERE name = 'Default Organization' LIMIT 1")
            
            await conn.execute("""
                INSERT INTO businesses (organization_id, name, type, is_active, greeting, assistant_name, system_prompt, menu_reference, phone_number, email, address, voice)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """, (
                default_org_id,
                "Nunzio's Pizza",
                "pizza",
                True,  # Active by default
                "Thank you for calling Nunzio's Pizza! This is John. How can I help you today?",
                "John",
                pizza_prompt,
                menu_ref,
                "+17323147497",
                "shaheersaud2004@gmail.com",
                "492 Manalapan Rd, Spotswood, NJ 08883",
                "Polly.Matthew-Neural"
            ))
            
            # Doctor's Office - Optimized
            doctor_prompt = """You are Sarah, a medical office receptionist.

RULES: Brief responses (1 sentence). No medical advice. No diagnoses. Only intake questions.

COLLECT: New/existing patient → Reason for visit → Insurance → Preferred time → Emergency check.

EMERGENCY: If severe pain, bleeding, swelling, infection, urgent - say "This sounds urgent. Please stay on the line while I connect you."

FLOW: Greet → Ask questions → Confirm → "Perfect! Our office will call you back within 24 hours to confirm." → End."""
            
            await conn.execute("""
                INSERT INTO businesses (organization_id, name, type, is_active, greeting, assistant_name, system_prompt, phone_number, email, address, voice)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """, (
                default_org_id,
                "Medical Office",
                "doctor",
                False,
                "Thank you for calling our medical office. This is Sarah. How can I help you today?",
                "Sarah",
                doctor_prompt,
                "+17323147497",
                "shaheersaud2004@gmail.com",
                "",
                "Polly.Matthew-Neural"
            ))
            
            # Dentist Office - Optimized
            dentist_prompt = """You are Sarah, a dental office receptionist.

RULES: Brief responses (1 sentence). No medical advice. No diagnoses. Only intake questions.

COLLECT: New/existing patient → Reason for visit → Dental insurance → Preferred time → Emergency check.

EMERGENCY: If severe pain, bleeding, swelling, infection, urgent - say "This sounds urgent. Please stay on the line while I connect you."

FLOW: Greet → Ask questions → Confirm → "Perfect! Our office will call you back within 24 hours to confirm." → End."""
            
            await conn.execute("""
                INSERT INTO businesses (organization_id, name, type, is_active, greeting, assistant_name, system_prompt, phone_number, email, address, voice)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """, (
                default_org_id,
                "Dental Office",
                "dentist",
                False,
                "Thank you for calling our dental office. This is Sarah. How can I help you today?",
                "Sarah",
                dentist_prompt,
                "+17323147497",
                "shaheersaud2004@gmail.com",
                "",
                "Polly.Matthew-Neural"
            ))
            
            # Cafe - Optimized
            cafe_prompt = """You are Alex, a cafe order taker.

RULES: Brief responses (1 sentence, max 12 words). Be friendly, efficient. Help with menu.

COLLECT: Items (coffee, food) → Size/type → Delivery/pickup → Address/name → Confirm → Done.

FLOW: Greet → Listen → Ask missing info → Confirm order → Thank."""
            
            await conn.execute("""
                INSERT INTO businesses (organization_id, name, type, is_active, greeting, assistant_name, system_prompt, phone_number, email, address, voice)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """, (
                default_org_id,
                "Cafe",
                "cafe",
                False,
                "Thank you for calling! This is Alex. How can I help you today?",
                "Alex",
                cafe_prompt,
                "+17323147497",
                "shaheersaud2004@gmail.com",
                "",
                "Polly.Matthew-Neural"
            ))
            
            # Bagel Shop - Optimized
            bagel_prompt = """You are Sam, a bagel shop order taker.

RULES: Brief responses (1 sentence, max 12 words). Be friendly, efficient. Help with menu.

COLLECT: Items (bagels, cream cheese, sandwiches) → Type/qty → Delivery/pickup → Address/name → Confirm → Done.

FLOW: Greet → Listen → Ask missing info → Confirm order → Thank."""
            
            await conn.execute("""
                INSERT INTO businesses (organization_id, name, type, is_active, greeting, assistant_name, system_prompt, phone_number, email, address, voice)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """, (
                default_org_id,
                "Bagel Shop",
                "bagel",
                False,
                "Thank you for calling! This is Sam. How can I help you today?",
                "Sam",
                bagel_prompt,
                "+17323147497",
                "shaheersaud2004@gmail.com",
                "",
                "Polly.Matthew-Neural"
            ))


async def init_default_businesses_for_org(organization_id: int):
    """Initialize default businesses for a new organization."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if businesses exist for this org
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM businesses WHERE organization_id = $1",
            organization_id
        )
        
        if count == 0:
            # Create a default pizza business
            pizza_prompt = """You are John, a pizza order taker.

RULES: Brief responses (1 sentence, max 12 words). Be friendly, efficient. Repeat back items. Don't repeat questions.

COLLECT: Items (pizza, size, qty) → Delivery/pickup → Address/name → Confirm → Done.

FLOW: Greet → Listen → Ask missing info → Confirm order → Thank."""
            
            await conn.execute("""
                INSERT INTO businesses (organization_id, name, type, is_active, greeting, assistant_name, system_prompt, voice)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, (
                organization_id,
                "My Business",
                "pizza",
                True,
                "Thank you for calling! This is John. How can I help you today?",
                "John",
                pizza_prompt,
                "Polly.Matthew-Neural"
            ))


async def migrate_existing_data_to_org():
    """Migrate existing data to a default organization."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if default org exists
        org = await conn.fetchrow(
            "SELECT id FROM organizations WHERE name = 'Default Organization' LIMIT 1"
        )
        
        if not org:
            # Create default org
            default_org_id = await conn.fetchval(
                "INSERT INTO organizations (name, subdomain) VALUES ($1, $2) RETURNING id",
                "Default Organization", "default"
            )
            
            if default_org_id:
                # Update existing businesses
                await conn.execute(
                    "UPDATE businesses SET organization_id = $1 WHERE organization_id IS NULL",
                    default_org_id
                )
                
                # Update existing calls
                await conn.execute(
                    "UPDATE calls SET organization_id = $1 WHERE organization_id IS NULL",
                    default_org_id
                )
                
                # Update existing orders
                await conn.execute(
                    "UPDATE orders SET organization_id = $1 WHERE organization_id IS NULL",
                    default_org_id
                )


async def save_call_start(call_sid: str, caller_phone: str, organization_id: int = None) -> int:
    """Save call start and return call ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if organization_id:
            call_id = await conn.fetchval("""
                INSERT INTO calls (call_sid, caller_phone, organization_id, start_time)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (call_sid) DO NOTHING
                RETURNING id
            """, call_sid, caller_phone, organization_id, datetime.now())
        else:
            call_id = await conn.fetchval("""
                INSERT INTO calls (call_sid, caller_phone, start_time)
                VALUES ($1, $2, $3)
                ON CONFLICT (call_sid) DO NOTHING
                RETURNING id
            """, call_sid, caller_phone, datetime.now())
        
        # If conflict, get existing ID
        if not call_id:
            call_id = await conn.fetchval("SELECT id FROM calls WHERE call_sid = $1", call_sid)
        
        return call_id


async def save_call_end(call_sid: str, duration_seconds: int = None):
    """Update call with end time and duration."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE calls 
            SET end_time = $1, duration_seconds = $2
            WHERE call_sid = $3
        """, datetime.now(), duration_seconds, call_sid)


async def save_conversation_turn(call_sid: str, user_input: str, assistant_response: str, turn_number: int):
    """Save a conversation turn."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO conversations (call_sid, user_input, assistant_response, turn_number)
            VALUES ($1, $2, $3, $4)
        """, call_sid, user_input, assistant_response, turn_number)


async def save_appointment(call_sid: str, caller_phone: str, appointment_info: Dict):
    """Save appointment information."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO appointments (
                call_sid, caller_phone, patient_status, reason, insurance,
                preferred_time, caller_name, is_emergency
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, (
            call_sid,
            caller_phone,
            appointment_info.get("patient_status"),
            appointment_info.get("reason"),
            appointment_info.get("insurance"),
            appointment_info.get("preferred_time"),
            appointment_info.get("caller_name"),
            appointment_info.get("emergency", False)
        ))


async def save_order(call_sid: str, caller_phone: str, order_info: Dict, organization_id: int = None) -> int:
    """Save order information to database."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Convert items list to JSON string if it's a list
        items_value = order_info.get("items")
        if isinstance(items_value, list):
            items_value = json.dumps(items_value)
        elif items_value is None:
            items_value = None
        else:
            items_value = str(items_value)
        
        order_id = await conn.fetchval("""
            INSERT INTO orders (
                call_sid, caller_phone, customer_name, items, order_type,
                delivery_address, pickup_name, phone_number, special_instructions,
                payment_method, total_estimate, organization_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id
        """, (
            call_sid,
            caller_phone,
            order_info.get("customer_name"),
            items_value,
            order_info.get("order_type"),
            order_info.get("delivery_address"),
            order_info.get("pickup_name"),
            order_info.get("phone_number"),
            order_info.get("special_instructions"),
            order_info.get("payment_method"),
            order_info.get("total_estimate"),
            organization_id
        ))
        return order_id


async def mark_call_emergency(call_sid: str):
    """Mark a call as emergency."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE calls SET is_emergency = true WHERE call_sid = $1
        """, call_sid)


async def get_recent_calls(limit: int = 50) -> List[Dict]:
    """Get recent calls with full details."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.*, 
                   COUNT(DISTINCT conv.id) as conversation_turns,
                   a.id as appointment_id,
                   a.booking_status
            FROM calls c
            LEFT JOIN conversations conv ON c.call_sid = conv.call_sid
            LEFT JOIN appointments a ON c.call_sid = a.call_sid
            GROUP BY c.id, a.id
            ORDER BY c.start_time DESC
            LIMIT $1
        """, limit)
        return [dict(row) for row in rows]


async def get_call_details(call_sid: str) -> Optional[Dict]:
    """Get full details of a specific call."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get call info
        call = await conn.fetchrow("SELECT * FROM calls WHERE call_sid = $1", call_sid)
        if not call:
            return None
        
        call_dict = dict(call)
        
        # Get conversation
        conversations = await conn.fetch("""
            SELECT * FROM conversations 
            WHERE call_sid = $1 
            ORDER BY turn_number
        """, call_sid)
        call_dict["conversation"] = [dict(conv) for conv in conversations]
        
        # Get appointment
        appointment = await conn.fetchrow("SELECT * FROM appointments WHERE call_sid = $1", call_sid)
        call_dict["appointment"] = dict(appointment) if appointment else None
        
        return call_dict


async def get_statistics() -> Dict:
    """Get dashboard statistics."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        stats = {}
        
        # Total calls
        stats["total_calls"] = await conn.fetchval("SELECT COUNT(*) FROM calls")
        
        # Emergency calls
        stats["emergency_calls"] = await conn.fetchval("SELECT COUNT(*) FROM calls WHERE is_emergency = true")
        
        # Appointments booked
        stats["appointments_booked"] = await conn.fetchval("SELECT COUNT(*) FROM appointments")
        
        # Calls today
        stats["calls_today"] = await conn.fetchval("""
            SELECT COUNT(*) FROM calls 
            WHERE DATE(start_time) = CURRENT_DATE
        """)
        
        # Average call duration
        avg_duration = await conn.fetchval("""
            SELECT AVG(duration_seconds) FROM calls 
            WHERE duration_seconds IS NOT NULL
        """)
        stats["avg_call_duration"] = int(avg_duration) if avg_duration else 0
        
        # Calls this week
        stats["calls_this_week"] = await conn.fetchval("""
            SELECT COUNT(*) FROM calls 
            WHERE start_time >= NOW() - INTERVAL '7 days'
        """)
        
        # New vs existing patients
        row = await conn.fetchrow("""
            SELECT 
                SUM(CASE WHEN patient_status = 'new' THEN 1 ELSE 0 END) as new_patients,
                SUM(CASE WHEN patient_status = 'existing' THEN 1 ELSE 0 END) as existing_patients
            FROM appointments
        """)
        stats["new_patients"] = row['new_patients'] or 0 if row else 0
        stats["existing_patients"] = row['existing_patients'] or 0 if row else 0
        
        return stats


async def get_appointments(limit: int = 50) -> List[Dict]:
    """Get all appointments."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT a.*, c.start_time, c.duration_seconds
            FROM appointments a
            LEFT JOIN calls c ON a.call_sid = c.call_sid
            ORDER BY a.created_at DESC
            LIMIT $1
        """, limit)
        return [dict(row) for row in rows]


async def update_appointment_status(appointment_id: int, status: str):
    """Update appointment booking status."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE appointments 
            SET booking_status = $1
            WHERE id = $2
        """, status, appointment_id)


async def get_chart_data(days: int = 30) -> Dict:
    """Get data for charts - daily calls, appointments, etc."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Daily calls for last N days
        daily_calls = await conn.fetch(f"""
            SELECT 
                DATE(start_time) as date,
                COUNT(*)::int as count,
                SUM(CASE WHEN is_emergency = true THEN 1 ELSE 0 END)::int as emergencies
            FROM calls
            WHERE start_time >= NOW() - INTERVAL '{days} days'
            GROUP BY DATE(start_time)
            ORDER BY date ASC
        """)
        
        # Daily appointments
        daily_appointments = await conn.fetch(f"""
            SELECT 
                DATE(created_at) as date,
                COUNT(*)::int as count
            FROM appointments
            WHERE created_at >= NOW() - INTERVAL '{days} days'
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """)
        
        return {
            "daily_calls": [{"date": str(row["date"]), "count": row["count"], "emergencies": row["emergencies"]} for row in daily_calls],
            "daily_appointments": [{"date": str(row["date"]), "count": row["count"]} for row in daily_appointments]
        }


async def search_calls(query: str, limit: int = 50) -> List[Dict]:
    """Search calls by caller phone or call SID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        search_term = f"%{query}%"
        rows = await conn.fetch("""
            SELECT c.*, 
                   COUNT(DISTINCT conv.id) as conversation_turns,
                   a.id as appointment_id,
                   a.booking_status
            FROM calls c
            LEFT JOIN conversations conv ON c.call_sid = conv.call_sid
            LEFT JOIN appointments a ON c.call_sid = a.call_sid
            WHERE c.caller_phone LIKE $1 OR c.call_sid LIKE $1
            GROUP BY c.id, a.id
            ORDER BY c.start_time DESC
            LIMIT $2
        """, search_term, limit)
        return [dict(row) for row in rows]


async def search_appointments(query: str, limit: int = 50) -> List[Dict]:
    """Search appointments by caller phone, reason, or insurance."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        search_term = f"%{query}%"
        rows = await conn.fetch("""
            SELECT a.*, c.start_time, c.duration_seconds
            FROM appointments a
            LEFT JOIN calls c ON a.call_sid = c.call_sid
            WHERE a.caller_phone LIKE $1 
               OR a.reason LIKE $1 
               OR a.insurance LIKE $1
               OR a.caller_name LIKE $1
            ORDER BY a.created_at DESC
            LIMIT $2
        """, search_term, limit)
        return [dict(row) for row in rows]


async def get_all_calls_for_export() -> List[Dict]:
    """Get all calls for CSV export."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.*, 
                   COUNT(DISTINCT conv.id) as conversation_turns,
                   a.id as appointment_id,
                   a.booking_status
            FROM calls c
            LEFT JOIN conversations conv ON c.call_sid = conv.call_sid
            LEFT JOIN appointments a ON c.call_sid = a.call_sid
            GROUP BY c.id, a.id
            ORDER BY c.start_time DESC
        """)
        return [dict(row) for row in rows]


async def get_all_appointments_for_export() -> List[Dict]:
    """Get all appointments for CSV export."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT a.*, c.start_time, c.duration_seconds
            FROM appointments a
            LEFT JOIN calls c ON a.call_sid = c.call_sid
            ORDER BY a.created_at DESC
        """)
        return [dict(row) for row in rows]


# ==================== ORDER FUNCTIONS ====================

async def get_orders(limit: int = 50, status: Optional[str] = None, order_type: Optional[str] = None) -> List[Dict]:
    """Get orders with optional filtering."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if status and order_type:
            rows = await conn.fetch("""
                SELECT * FROM orders 
                WHERE order_status = $1 AND order_type = $2
                ORDER BY created_at DESC LIMIT $3
            """, status, order_type, limit)
        elif status:
            rows = await conn.fetch("""
                SELECT * FROM orders 
                WHERE order_status = $1
                ORDER BY created_at DESC LIMIT $2
            """, status, limit)
        elif order_type:
            rows = await conn.fetch("""
                SELECT * FROM orders 
                WHERE order_type = $1
                ORDER BY created_at DESC LIMIT $2
            """, order_type, limit)
        else:
            rows = await conn.fetch("""
                SELECT * FROM orders 
                ORDER BY created_at DESC LIMIT $1
            """, limit)
        return [dict(row) for row in rows]


async def get_order(order_id: int) -> Optional[Dict]:
    """Get a specific order by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
        return dict(row) if row else None


async def update_order_status(order_id: int, status: str):
    """Update order status."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE orders 
            SET order_status = $1
            WHERE id = $2
        """, status, order_id)


async def get_order_statistics() -> Dict:
    """Get order statistics."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        stats = {}
        
        # Total orders
        stats["total_orders"] = await conn.fetchval("SELECT COUNT(*) FROM orders")
        
        # Orders today
        stats["orders_today"] = await conn.fetchval("""
            SELECT COUNT(*) FROM orders 
            WHERE DATE(created_at) = CURRENT_DATE
        """)
        
        # Orders by status
        rows = await conn.fetch("""
            SELECT order_status, COUNT(*) as count 
            FROM orders 
            GROUP BY order_status
        """)
        status_counts = {}
        for row in rows:
            status_counts[row['order_status'] or "pending"] = row['count']
        stats["orders_by_status"] = status_counts
        
        # Orders by type
        rows = await conn.fetch("""
            SELECT order_type, COUNT(*) as count 
            FROM orders 
            WHERE order_type IS NOT NULL
            GROUP BY order_type
        """)
        type_counts = {}
        for row in rows:
            type_counts[row['order_type']] = row['count']
        stats["orders_by_type"] = type_counts
        
        # Orders this week
        stats["orders_this_week"] = await conn.fetchval("""
            SELECT COUNT(*) FROM orders 
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        
        return stats


async def search_orders(query: str, limit: int = 50) -> List[Dict]:
    """Search orders by phone, name, or items."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        search_term = f"%{query}%"
        rows = await conn.fetch("""
            SELECT * FROM orders 
            WHERE caller_phone LIKE $1 
               OR customer_name LIKE $1
               OR pickup_name LIKE $1
               OR items LIKE $1
            ORDER BY created_at DESC
            LIMIT $2
        """, search_term, limit)
        return [dict(row) for row in rows]


# Business management functions
async def get_active_business(organization_id: int = None) -> Optional[Dict]:
    """Get the currently active business for an organization."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if organization_id:
            business = await conn.fetchrow("""
                SELECT * FROM businesses WHERE is_active = true AND organization_id = $1 LIMIT 1
            """, organization_id)
        else:
            business = await conn.fetchrow("""
                SELECT * FROM businesses WHERE is_active = true LIMIT 1
            """)
        return dict(business) if business else None


async def get_all_businesses(organization_id: int = None) -> List[Dict]:
    """Get all businesses for an organization."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if organization_id:
            rows = await conn.fetch("""
                SELECT * FROM businesses WHERE organization_id = $1 ORDER BY is_active DESC, name ASC
            """, organization_id)
        else:
            rows = await conn.fetch("""
                SELECT * FROM businesses ORDER BY is_active DESC, name ASC
            """)
        return [dict(row) for row in rows]


async def set_active_business(business_id: int, organization_id: int = None):
    """Set a business as active (deactivates all others in organization)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if organization_id:
            # Deactivate all in organization
            await conn.execute("UPDATE businesses SET is_active = false WHERE organization_id = $1", organization_id)
            # Activate selected
            await conn.execute("UPDATE businesses SET is_active = true WHERE id = $1 AND organization_id = $2", business_id, organization_id)
        else:
            # Deactivate all (legacy)
            await conn.execute("UPDATE businesses SET is_active = false")
            # Activate selected
            await conn.execute("UPDATE businesses SET is_active = true WHERE id = $1", business_id)


async def update_business(business_id: int, updates: Dict):
    """Update business configuration."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        allowed_keys = ['name', 'type', 'greeting', 'assistant_name', 'system_prompt', 
                       'menu_reference', 'phone_number', 'email', 'address', 'config_json', 'voice']
        
        # Build update query dynamically
        set_clauses = []
        values = []
        param_num = 1
        
        for key, value in updates.items():
            if key in allowed_keys:
                set_clauses.append(f"{key} = ${param_num}")
                values.append(value)
                param_num += 1
        
        if set_clauses:
            set_clauses.append(f"updated_at = ${param_num}")
            values.append(datetime.now())
            param_num += 1
            
            values.append(business_id)
            query = f"""
                UPDATE businesses 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_num}
            """
            await conn.execute(query, *values)


async def get_business(business_id: int) -> Optional[Dict]:
    """Get a specific business."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        business = await conn.fetchrow("SELECT * FROM businesses WHERE id = $1", business_id)
        return dict(business) if business else None


async def delete_business(business_id: int):
    """Delete a business."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM businesses WHERE id = $1", business_id)


async def delete_businesses_by_assistant_name(assistant_name: str):
    """Delete all businesses with a specific assistant name."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # First, deactivate if any are active
        await conn.execute("UPDATE businesses SET is_active = false WHERE assistant_name = $1", assistant_name)
        # Then delete
        await conn.execute("DELETE FROM businesses WHERE assistant_name = $1", assistant_name)
        # Return count of deleted businesses
        return await conn.fetchval("SELECT COUNT(*) FROM businesses WHERE assistant_name = $1", assistant_name)
