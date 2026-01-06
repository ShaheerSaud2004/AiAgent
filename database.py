"""
Database models and functions for storing call data and statistics.
Uses SQLite for simple local storage.
"""

import aiosqlite
import json
from datetime import datetime
from typing import Dict, List, Optional
import os

# Use environment variable for database path (Vercel uses /tmp for writable storage)
import os
DB_PATH = os.getenv("DATABASE_URL", os.path.join(os.getenv("TMPDIR", "/tmp"), "receptionist.db"))


async def init_db():
    """Initialize the database with required tables."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Organizations table (multi-tenancy)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                subdomain TEXT UNIQUE,
                subscription_tier TEXT DEFAULT 'free',
                stripe_customer_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                organization_id INTEGER,
                role TEXT DEFAULT 'admin',
                full_name TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id)
            )
        """)
        
        # Businesses table (now with organization_id)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 0,
                greeting TEXT,
                assistant_name TEXT,
                system_prompt TEXT,
                menu_reference TEXT,
                phone_number TEXT,
                email TEXT,
                address TEXT,
                config_json TEXT,
                voice TEXT DEFAULT 'Polly.Matthew-Neural',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id)
            )
        """)
        
        # Calls table (now with organization_id)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_sid TEXT UNIQUE NOT NULL,
                caller_phone TEXT NOT NULL,
                organization_id INTEGER NOT NULL,
                business_id INTEGER,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration_seconds INTEGER,
                is_emergency BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (business_id) REFERENCES businesses(id)
            )
        """)
        
        # Conversations table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_sid TEXT NOT NULL,
                user_input TEXT,
                assistant_response TEXT,
                turn_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (call_sid) REFERENCES calls(call_sid)
            )
        """)
        
        # Appointments table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_sid TEXT NOT NULL,
                caller_phone TEXT NOT NULL,
                patient_status TEXT,
                reason TEXT,
                insurance TEXT,
                preferred_time TEXT,
                caller_name TEXT,
                is_emergency BOOLEAN DEFAULT 0,
                booking_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (call_sid) REFERENCES calls(call_sid)
            )
        """)
        
        # Orders table (now with organization_id)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_sid TEXT NOT NULL,
                organization_id INTEGER NOT NULL,
                caller_phone TEXT NOT NULL,
                customer_name TEXT,
                items TEXT,
                order_type TEXT,
                delivery_address TEXT,
                pickup_name TEXT,
                phone_number TEXT,
                special_instructions TEXT,
                payment_method TEXT,
                total_estimate TEXT,
                order_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (call_sid) REFERENCES calls(call_sid)
            )
        """)
        
        # Add organization_id to existing tables if they don't have it
        try:
            await db.execute("ALTER TABLE businesses ADD COLUMN organization_id INTEGER")
        except:
            pass
        
        try:
            await db.execute("ALTER TABLE calls ADD COLUMN organization_id INTEGER")
        except:
            pass
        
        try:
            await db.execute("ALTER TABLE orders ADD COLUMN organization_id INTEGER")
        except:
            pass
        
        await db.commit()
        
        # Add voice column if it doesn't exist (for existing databases)
        try:
            await db.execute("ALTER TABLE businesses ADD COLUMN voice TEXT DEFAULT 'Polly.Matthew-Neural'")
            await db.commit()
        except Exception as e:
            pass  # Column already exists or other error
        
        # Update existing businesses to have voice if null
        try:
            await db.execute("UPDATE businesses SET voice = 'Polly.Matthew-Neural' WHERE voice IS NULL OR voice = ''")
            await db.commit()
        except:
            pass
        
        # Initialize default businesses if they don't exist (legacy - for existing data)
        await init_default_businesses()
        
        # Migrate existing data to default organization if needed
        await migrate_existing_data_to_org()


async def init_default_businesses():
    """Initialize default business configurations."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if businesses exist
        async with db.execute("SELECT COUNT(*) as count FROM businesses") as cursor:
            count = (await cursor.fetchone())[0]
        
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
            async with db.execute("SELECT id FROM organizations LIMIT 1") as cursor:
                default_org = await cursor.fetchone()
                default_org_id = default_org[0] if default_org else None
            
            if not default_org_id:
                # Create default organization
                cursor = await db.execute("INSERT INTO organizations (name, subdomain) VALUES (?, ?)", ("Default Organization", "default"))
                default_org_id = cursor.lastrowid
                await db.commit()
            
            await db.execute("""
                INSERT INTO businesses (organization_id, name, type, is_active, greeting, assistant_name, system_prompt, menu_reference, phone_number, email, address, voice)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                default_org_id,
                "Nunzio's Pizza",
                "pizza",
                1,  # Active by default
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
            
            await db.execute("""
                INSERT INTO businesses (organization_id, name, type, is_active, greeting, assistant_name, system_prompt, phone_number, email, address, voice)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                default_org_id,
                "Medical Office",
                "doctor",
                0,
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
            
            await db.execute("""
                INSERT INTO businesses (organization_id, name, type, is_active, greeting, assistant_name, system_prompt, phone_number, email, address, voice)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                default_org_id,
                "Dental Office",
                "dentist",
                0,
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
            
            await db.execute("""
                INSERT INTO businesses (organization_id, name, type, is_active, greeting, assistant_name, system_prompt, phone_number, email, address, voice)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                default_org_id,
                "Cafe",
                "cafe",
                0,
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
            
            await db.execute("""
                INSERT INTO businesses (organization_id, name, type, is_active, greeting, assistant_name, system_prompt, phone_number, email, address, voice)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                default_org_id,
                "Bagel Shop",
                "bagel",
                0,
                "Thank you for calling! This is Sam. How can I help you today?",
                "Sam",
                bagel_prompt,
                "+17323147497",
                "shaheersaud2004@gmail.com",
                "",
                "Polly.Matthew-Neural"
            ))
            
            await db.commit()


async def init_default_businesses_for_org(organization_id: int):
    """Initialize default businesses for a new organization."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if businesses exist for this org
        async with db.execute(
            "SELECT COUNT(*) as count FROM businesses WHERE organization_id = ?",
            (organization_id,)
        ) as cursor:
            count = (await cursor.fetchone())[0]
        
        if count == 0:
            # Create a default pizza business
            pizza_prompt = """You are John, a pizza order taker.

RULES: Brief responses (1 sentence, max 12 words). Be friendly, efficient. Repeat back items. Don't repeat questions.

COLLECT: Items (pizza, size, qty) → Delivery/pickup → Address/name → Confirm → Done.

FLOW: Greet → Listen → Ask missing info → Confirm order → Thank."""
            
            await db.execute("""
                INSERT INTO businesses (organization_id, name, type, is_active, greeting, assistant_name, system_prompt, voice)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                organization_id,
                "My Business",
                "pizza",
                1,
                "Thank you for calling! This is John. How can I help you today?",
                "John",
                pizza_prompt,
                "Polly.Matthew-Neural"
            ))
            await db.commit()


async def migrate_existing_data_to_org():
    """Migrate existing data to a default organization."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if default org exists
        async with db.execute(
            "SELECT id FROM organizations WHERE name = 'Default Organization' LIMIT 1"
        ) as cursor:
            org = await cursor.fetchone()
        
        if not org:
            # Create default org
            cursor = await db.execute(
                "INSERT INTO organizations (name, subdomain) VALUES (?, ?)",
                ("Default Organization", "default")
            )
            default_org_id = cursor.lastrowid
            await db.commit()
            
            # Update existing businesses
            await db.execute(
                "UPDATE businesses SET organization_id = ? WHERE organization_id IS NULL",
                (default_org_id,)
            )
            
            # Update existing calls
            await db.execute(
                "UPDATE calls SET organization_id = ? WHERE organization_id IS NULL",
                (default_org_id,)
            )
            
            # Update existing orders
            await db.execute(
                "UPDATE orders SET organization_id = ? WHERE organization_id IS NULL",
                (default_org_id,)
            )
            
            await db.commit()


async def save_call_start(call_sid: str, caller_phone: str, organization_id: int = None) -> int:
    """Save call start and return call ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        if organization_id:
            cursor = await db.execute("""
                INSERT OR IGNORE INTO calls (call_sid, caller_phone, organization_id, start_time)
                VALUES (?, ?, ?, ?)
            """, (call_sid, caller_phone, organization_id, datetime.now()))
        else:
            cursor = await db.execute("""
                INSERT OR IGNORE INTO calls (call_sid, caller_phone, start_time)
                VALUES (?, ?, ?)
            """, (call_sid, caller_phone, datetime.now()))
        await db.commit()
        return cursor.lastrowid


async def save_call_end(call_sid: str, duration_seconds: int = None):
    """Update call with end time and duration."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE calls 
            SET end_time = ?, duration_seconds = ?
            WHERE call_sid = ?
        """, (datetime.now(), duration_seconds, call_sid))
        await db.commit()


async def save_conversation_turn(call_sid: str, user_input: str, assistant_response: str, turn_number: int):
    """Save a conversation turn."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO conversations (call_sid, user_input, assistant_response, turn_number)
            VALUES (?, ?, ?, ?)
        """, (call_sid, user_input, assistant_response, turn_number))
        await db.commit()


async def save_appointment(call_sid: str, caller_phone: str, appointment_info: Dict):
    """Save appointment information."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO appointments (
                call_sid, caller_phone, patient_status, reason, insurance,
                preferred_time, caller_name, is_emergency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
        await db.commit()


async def save_order(call_sid: str, caller_phone: str, order_info: Dict, organization_id: int = None) -> int:
    """Save order information to database."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Convert items list to JSON string if it's a list
        items_value = order_info.get("items")
        if isinstance(items_value, list):
            items_value = json.dumps(items_value)
        elif items_value is None:
            items_value = None
        else:
            items_value = str(items_value)
        
        cursor = await db.execute("""
            INSERT INTO orders (
                call_sid, caller_phone, customer_name, items, order_type,
                delivery_address, pickup_name, phone_number, special_instructions,
                payment_method, total_estimate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            order_info.get("total_estimate")
        ))
        await db.commit()
        return cursor.lastrowid


async def mark_call_emergency(call_sid: str):
    """Mark a call as emergency."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE calls SET is_emergency = 1 WHERE call_sid = ?
        """, (call_sid,))
        await db.commit()


async def get_recent_calls(limit: int = 50) -> List[Dict]:
    """Get recent calls with full details."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT c.*, 
                   COUNT(DISTINCT conv.id) as conversation_turns,
                   a.id as appointment_id,
                   a.booking_status
            FROM calls c
            LEFT JOIN conversations conv ON c.call_sid = conv.call_sid
            LEFT JOIN appointments a ON c.call_sid = a.call_sid
            GROUP BY c.id
            ORDER BY c.start_time DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_call_details(call_sid: str) -> Optional[Dict]:
    """Get full details of a specific call."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Get call info
        async with db.execute("""
            SELECT * FROM calls WHERE call_sid = ?
        """, (call_sid,)) as cursor:
            call = await cursor.fetchone()
            if not call:
                return None
            
            call_dict = dict(call)
            
            # Get conversation
            async with db.execute("""
                SELECT * FROM conversations 
                WHERE call_sid = ? 
                ORDER BY turn_number
            """, (call_sid,)) as cursor:
                conversations = await cursor.fetchall()
                call_dict["conversation"] = [dict(conv) for conv in conversations]
            
            # Get appointment
            async with db.execute("""
                SELECT * FROM appointments WHERE call_sid = ?
            """, (call_sid,)) as cursor:
                appointment = await cursor.fetchone()
                call_dict["appointment"] = dict(appointment) if appointment else None
            
            return call_dict


async def get_statistics() -> Dict:
    """Get dashboard statistics."""
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}
        
        # Total calls
        async with db.execute("SELECT COUNT(*) as count FROM calls") as cursor:
            stats["total_calls"] = (await cursor.fetchone())[0]
        
        # Emergency calls
        async with db.execute("SELECT COUNT(*) as count FROM calls WHERE is_emergency = 1") as cursor:
            stats["emergency_calls"] = (await cursor.fetchone())[0]
        
        # Appointments booked
        async with db.execute("SELECT COUNT(*) as count FROM appointments") as cursor:
            stats["appointments_booked"] = (await cursor.fetchone())[0]
        
        # Calls today
        async with db.execute("""
            SELECT COUNT(*) as count FROM calls 
            WHERE DATE(start_time) = DATE('now')
        """) as cursor:
            stats["calls_today"] = (await cursor.fetchone())[0]
        
        # Average call duration
        async with db.execute("""
            SELECT AVG(duration_seconds) as avg FROM calls 
            WHERE duration_seconds IS NOT NULL
        """) as cursor:
            avg_duration = (await cursor.fetchone())[0]
            stats["avg_call_duration"] = int(avg_duration) if avg_duration else 0
        
        # Calls this week
        async with db.execute("""
            SELECT COUNT(*) as count FROM calls 
            WHERE start_time >= datetime('now', '-7 days')
        """) as cursor:
            stats["calls_this_week"] = (await cursor.fetchone())[0]
        
        # New vs existing patients
        async with db.execute("""
            SELECT 
                SUM(CASE WHEN patient_status = 'new' THEN 1 ELSE 0 END) as new_patients,
                SUM(CASE WHEN patient_status = 'existing' THEN 1 ELSE 0 END) as existing_patients
            FROM appointments
        """) as cursor:
            row = await cursor.fetchone()
            stats["new_patients"] = row[0] or 0
            stats["existing_patients"] = row[1] or 0
        
        return stats


async def get_appointments(limit: int = 50) -> List[Dict]:
    """Get all appointments."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT a.*, c.start_time, c.duration_seconds
            FROM appointments a
            LEFT JOIN calls c ON a.call_sid = c.call_sid
            ORDER BY a.created_at DESC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def update_appointment_status(appointment_id: int, status: str):
    """Update appointment booking status."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE appointments 
            SET booking_status = ?
            WHERE id = ?
        """, (status, appointment_id))
        await db.commit()


async def get_chart_data(days: int = 30) -> Dict:
    """Get data for charts - daily calls, appointments, etc."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Daily calls for last N days
        async with db.execute("""
            SELECT 
                DATE(start_time) as date,
                COUNT(*) as count,
                SUM(CASE WHEN is_emergency = 1 THEN 1 ELSE 0 END) as emergencies
            FROM calls
            WHERE start_time >= datetime('now', '-' || ? || ' days')
            GROUP BY DATE(start_time)
            ORDER BY date ASC
        """, (days,)) as cursor:
            daily_calls = await cursor.fetchall()
        
        # Daily appointments
        async with db.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as count
            FROM appointments
            WHERE created_at >= datetime('now', '-' || ? || ' days')
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """, (days,)) as cursor:
            daily_appointments = await cursor.fetchall()
        
        return {
            "daily_calls": [{"date": row["date"], "count": row["count"], "emergencies": row["emergencies"]} for row in daily_calls],
            "daily_appointments": [{"date": row["date"], "count": row["count"]} for row in daily_appointments]
        }


async def search_calls(query: str, limit: int = 50) -> List[Dict]:
    """Search calls by caller phone or call SID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        search_term = f"%{query}%"
        async with db.execute("""
            SELECT c.*, 
                   COUNT(DISTINCT conv.id) as conversation_turns,
                   a.id as appointment_id,
                   a.booking_status
            FROM calls c
            LEFT JOIN conversations conv ON c.call_sid = conv.call_sid
            LEFT JOIN appointments a ON c.call_sid = a.call_sid
            WHERE c.caller_phone LIKE ? OR c.call_sid LIKE ?
            GROUP BY c.id
            ORDER BY c.start_time DESC
            LIMIT ?
        """, (search_term, search_term, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def search_appointments(query: str, limit: int = 50) -> List[Dict]:
    """Search appointments by caller phone, reason, or insurance."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        search_term = f"%{query}%"
        async with db.execute("""
            SELECT a.*, c.start_time, c.duration_seconds
            FROM appointments a
            LEFT JOIN calls c ON a.call_sid = c.call_sid
            WHERE a.caller_phone LIKE ? 
               OR a.reason LIKE ? 
               OR a.insurance LIKE ?
               OR a.caller_name LIKE ?
            ORDER BY a.created_at DESC
            LIMIT ?
        """, (search_term, search_term, search_term, search_term, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_all_calls_for_export() -> List[Dict]:
    """Get all calls for CSV export."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT c.*, 
                   COUNT(DISTINCT conv.id) as conversation_turns,
                   a.id as appointment_id,
                   a.booking_status
            FROM calls c
            LEFT JOIN conversations conv ON c.call_sid = conv.call_sid
            LEFT JOIN appointments a ON c.call_sid = a.call_sid
            GROUP BY c.id
            ORDER BY c.start_time DESC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_all_appointments_for_export() -> List[Dict]:
    """Get all appointments for CSV export."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT a.*, c.start_time, c.duration_seconds
            FROM appointments a
            LEFT JOIN calls c ON a.call_sid = c.call_sid
            ORDER BY a.created_at DESC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ==================== ORDER FUNCTIONS ====================

async def get_orders(limit: int = 50, status: Optional[str] = None, order_type: Optional[str] = None) -> List[Dict]:
    """Get orders with optional filtering."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM orders WHERE 1=1"
        params = []
        
        if status:
            query += " AND order_status = ?"
            params.append(status)
        
        if order_type:
            query += " AND order_type = ?"
            params.append(order_type)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_order(order_id: int) -> Optional[Dict]:
    """Get a specific order by ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_order_status(order_id: int, status: str):
    """Update order status."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE orders 
            SET order_status = ?
            WHERE id = ?
        """, (status, order_id))
        await db.commit()


async def get_order_statistics() -> Dict:
    """Get order statistics."""
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}
        
        # Total orders
        async with db.execute("SELECT COUNT(*) as count FROM orders") as cursor:
            stats["total_orders"] = (await cursor.fetchone())[0]
        
        # Orders today
        async with db.execute("""
            SELECT COUNT(*) as count FROM orders 
            WHERE DATE(created_at) = DATE('now')
        """) as cursor:
            stats["orders_today"] = (await cursor.fetchone())[0]
        
        # Orders by status
        async with db.execute("""
            SELECT order_status, COUNT(*) as count 
            FROM orders 
            GROUP BY order_status
        """) as cursor:
            status_counts = {}
            for row in await cursor.fetchall():
                status_counts[row[0] or "pending"] = row[1]
            stats["orders_by_status"] = status_counts
        
        # Orders by type
        async with db.execute("""
            SELECT order_type, COUNT(*) as count 
            FROM orders 
            WHERE order_type IS NOT NULL
            GROUP BY order_type
        """) as cursor:
            type_counts = {}
            for row in await cursor.fetchall():
                type_counts[row[0]] = row[1]
            stats["orders_by_type"] = type_counts
        
        # Orders this week
        async with db.execute("""
            SELECT COUNT(*) as count FROM orders 
            WHERE created_at >= datetime('now', '-7 days')
        """) as cursor:
            stats["orders_this_week"] = (await cursor.fetchone())[0]
        
        return stats


async def search_orders(query: str, limit: int = 50) -> List[Dict]:
    """Search orders by phone, name, or items."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        search_term = f"%{query}%"
        async with db.execute("""
            SELECT * FROM orders 
            WHERE caller_phone LIKE ? 
               OR customer_name LIKE ?
               OR pickup_name LIKE ?
               OR items LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (search_term, search_term, search_term, search_term, limit)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# Business management functions
async def get_active_business(organization_id: int = None) -> Optional[Dict]:
    """Get the currently active business for an organization."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if organization_id:
            async with db.execute("""
                SELECT * FROM businesses WHERE is_active = 1 AND organization_id = ? LIMIT 1
            """, (organization_id,)) as cursor:
                business = await cursor.fetchone()
                return dict(business) if business else None
        else:
            async with db.execute("""
                SELECT * FROM businesses WHERE is_active = 1 LIMIT 1
            """) as cursor:
                business = await cursor.fetchone()
                return dict(business) if business else None


async def get_all_businesses(organization_id: int = None) -> List[Dict]:
    """Get all businesses for an organization."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if organization_id:
            async with db.execute("""
                SELECT * FROM businesses WHERE organization_id = ? ORDER BY is_active DESC, name ASC
            """, (organization_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        else:
            async with db.execute("""
                SELECT * FROM businesses ORDER BY is_active DESC, name ASC
            """) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


async def set_active_business(business_id: int, organization_id: int = None):
    """Set a business as active (deactivates all others in organization)."""
    async with aiosqlite.connect(DB_PATH) as db:
        if organization_id:
            # Deactivate all in organization
            await db.execute("UPDATE businesses SET is_active = 0 WHERE organization_id = ?", (organization_id,))
            # Activate selected
            await db.execute("UPDATE businesses SET is_active = 1 WHERE id = ? AND organization_id = ?", (business_id, organization_id))
        else:
            # Deactivate all (legacy)
            await db.execute("UPDATE businesses SET is_active = 0")
            # Activate selected
            await db.execute("UPDATE businesses SET is_active = 1 WHERE id = ?", (business_id,))
        await db.commit()


async def update_business(business_id: int, updates: Dict):
    """Update business configuration."""
    async with aiosqlite.connect(DB_PATH) as db:
        fields = []
        values = []
        for key, value in updates.items():
            if key in ['name', 'type', 'greeting', 'assistant_name', 'system_prompt', 
                      'menu_reference', 'phone_number', 'email', 'address', 'config_json']:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if fields:
            values.append(business_id)
            await db.execute(f"""
                UPDATE businesses 
                SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            await db.commit()


async def get_business(business_id: int) -> Optional[Dict]:
    """Get a specific business."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM businesses WHERE id = ?", (business_id,)) as cursor:
            business = await cursor.fetchone()
            return dict(business) if business else None


async def delete_business(business_id: int):
    """Delete a business."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM businesses WHERE id = ?", (business_id,))
        await db.commit()


async def delete_businesses_by_assistant_name(assistant_name: str):
    """Delete all businesses with a specific assistant name."""
    async with aiosqlite.connect(DB_PATH) as db:
        # First, deactivate if any are active
        await db.execute("UPDATE businesses SET is_active = 0 WHERE assistant_name = ?", (assistant_name,))
        # Then delete
        await db.execute("DELETE FROM businesses WHERE assistant_name = ?", (assistant_name,))
        await db.commit()
        # Return count of deleted businesses
        async with db.execute("SELECT changes()") as cursor:
            return (await cursor.fetchone())[0]

