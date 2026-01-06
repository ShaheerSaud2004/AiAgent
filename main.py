"""
FastAPI backend for AI phone receptionist.
Handles Twilio webhooks and manages call flow.
"""

import os
import logging
from fastapi import FastAPI, Request, Form, Query, HTTPException, Depends, status
from fastapi.responses import Response, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from twilio.twiml.voice_response import VoiceResponse, Gather, Dial
from twilio.request_validator import RequestValidator
from dotenv import load_dotenv
from typing import Optional
import json
import csv
import io
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from prompts import check_for_emergency, ORDER_QUESTIONS, get_business_prompt
from utils import generate_response, extract_order_info, save_order_simple
from database import (
    init_db, save_call_start, save_call_end, save_conversation_turn,
    save_appointment, save_order, mark_call_emergency, get_recent_calls, get_call_details,
    get_statistics, get_appointments, update_appointment_status, get_chart_data,
    search_calls, search_appointments, get_all_calls_for_export,
    get_all_appointments_for_export,
    get_orders, get_order, update_order_status, get_order_statistics, search_orders,
    get_active_business, get_all_businesses, set_active_business, update_business, get_business,
    delete_business, delete_businesses_by_assistant_name
)
from auth import (
    authenticate_user, create_access_token, get_current_user, get_current_organization,
    get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
)
from datetime import timedelta
from organizations import create_organization, create_user, get_organization, get_organization_users, get_organization_by_phone
from pydantic import BaseModel, EmailStr

# Load environment variables
load_dotenv()

app = FastAPI(
    title="AI Phone Receptionist SaaS",
    version="2.0.0",
    description="Multi-tenant B2B SaaS platform for AI-powered phone receptionists"
)

# Initialize database on startup
@app.on_event("startup")
async def startup():
    await init_db()
    # Load active business configuration
    from prompts import load_active_business
    await load_active_business()

# Serve static files (frontend)
# On Vercel, static files are served automatically, but we keep this for local dev
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    pass  # Vercel handles static files differently

# Configuration
OFFICE_PHONE = os.getenv("OFFICE_PHONE_NUMBER")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
BASE_URL = os.getenv("BASE_URL", "https://your-domain.com")

# In-memory call state (use Redis in production)
call_sessions = {}


def get_call_session(call_sid: str) -> dict:
    """Get or create call session."""
    if call_sid not in call_sessions:
        call_sessions[call_sid] = {
            "conversation_history": [],
            "questions_asked": 0,
            "appointment_info": {},
            "is_emergency": False,
            "caller_phone": None
        }
    return call_sessions[call_sid]


@app.post("/answer")
async def answer_call(request: Request):
    """
    Twilio webhook: Called when a call comes in.
    Determines organization from phone number or subdomain.
    """
    form = await request.form()
    call_sid = form.get("CallSid")
    caller_phone = form.get("From", "Unknown")
    called_number = form.get("Called", "")
    
    # Determine organization from phone number
    # In production, you'd have a mapping table: phone_number -> organization_id
    # For now, use default organization or find by phone number
    organization_id = await get_organization_by_phone(called_number)
    
    # Save call to database
    await save_call_start(call_sid, caller_phone, organization_id)
    
    # Initialize call session
    session = get_call_session(call_sid)
    session["caller_phone"] = caller_phone
    session["start_time"] = datetime.now()
    
    response = VoiceResponse()
    
    # Get active business configuration for this organization
    business = await get_active_business(organization_id)
    if business:
        greeting = business.get("greeting", "Thank you for calling! How can I help you today?")
        voice = business.get("voice", "Polly.Matthew-Neural")  # Default voice
    else:
        greeting = f"Thank you for calling {os.getenv('OFFICE_NAME', 'Nunzio\'s Pizza')}! This is John. How can I help you today?"
        voice = "Polly.Matthew-Neural"
    
    gather = Gather(
        input="speech",
        action=f"{BASE_URL}/process",
        method="POST",
        timeout=5,
        speech_timeout="auto",
        language="en-US"
    )
    
    gather.say(greeting, voice=voice)
    response.append(gather)
    
    # Fallback if no input
    response.say("I didn't catch that. Please call back if you need assistance.", voice=voice)
    response.hangup()
    
    return Response(content=str(response), media_type="application/xml")


@app.post("/process")
async def process_speech(request: Request):
    """
    Process caller's speech input and generate response.
    """
    form = await request.form()
    call_sid = form.get("CallSid")
    user_input = form.get("SpeechResult", "").strip()
    caller_phone = form.get("From", "Unknown")
    
    logger.info(f"Received speech input for call {call_sid}: '{user_input}'")
    
    if not call_sid:
        response = VoiceResponse()
        # Get voice from business
        business = await get_active_business()
        voice = business.get("voice", "Polly.Matthew-Neural") if business else "Polly.Matthew-Neural"
        response.say("I'm sorry, there was an error. Please call back.", voice=voice)
        response.hangup()
        return Response(content=str(response), media_type="application/xml")
    
    session = get_call_session(call_sid)
    session["caller_phone"] = caller_phone
    
    response = VoiceResponse()
    
    # Handle empty input - might be timeout or no speech detected
    if not user_input:
        logger.warning(f"Empty speech input for call {call_sid}")
        gather = Gather(
            input="speech",
            action=f"{BASE_URL}/process",
            method="POST",
            timeout=5,
            speech_timeout="auto",
            language="en-US"
        )
        # Get voice from business
        business = await get_active_business()
        voice = business.get("voice", "Polly.Matthew-Neural") if business else "Polly.Matthew-Neural"
        gather.say("I'm sorry, I didn't catch that. Could you please repeat?", voice=voice)
        response.append(gather)
        response.say("I didn't catch that. Could you please repeat?", voice=voice)
        response.redirect(f"{BASE_URL}/process", method="POST")
        return Response(content=str(response), media_type="application/xml")
    
    # Add user input to conversation history
    session["conversation_history"].append({"user": user_input, "assistant": ""})
    turn_number = len(session["conversation_history"])
    
    # Get organization from call (stored in session or from phone number)
    organization_id = session.get("organization_id")
    if not organization_id:
        # Try to get from phone number
        organization_id = await get_organization_by_phone(form.get("Called", ""))
        if organization_id:
            session["organization_id"] = organization_id
    
    # Get active business for prompt
    business = await get_active_business(organization_id)
    system_prompt = None
    if business:
        system_prompt = business.get("system_prompt")
        # Update cache
        from prompts import _active_business_cache
        _active_business_cache = dict(business)
    
    # Generate AI response first (before creating response)
    ai_response = generate_response(
        user_input=user_input,
        conversation_history=session["conversation_history"][:-1],  # Exclude current turn
        system_prompt=system_prompt
    )
    
    # Add AI response to history
    session["conversation_history"][-1]["assistant"] = ai_response
    
    # Save conversation turn to database
    await save_conversation_turn(call_sid, user_input, ai_response, turn_number)
    
    # Extract and save order info (run less frequently for speed - every 3+ turns to reduce API calls)
    if len(session["conversation_history"]) >= 3:
        try:
            order_info = extract_order_info(session["conversation_history"])
            session["order_info"] = order_info
            logger.info(f"Extracted order info for call {call_sid}: {order_info}")
            
            # Check if we have items (most important) - more lenient check
            items_str = str(order_info.get("items", "") or "")
            has_items = items_str and items_str.lower() not in ["null", "none", ""] and len(items_str.strip()) > 2
            
            # MORE ROBUST: Save order whenever we detect items, even if already saved (updates)
            if has_items:
                try:
                    # Always save/update order if we have items
                    order_id = await save_order(call_sid, caller_phone, order_info, organization_id)
                    logger.info(f"Order saved/updated in database with ID {order_id} for call {call_sid}")
                    
                    # Mark as saved
                    if not session.get("order_saved"):
                        session["order_saved"] = True
                        session["order_id"] = order_id
                        # Send email on first save
                        save_order_simple(order_info, caller_phone)
                except Exception as e:
                    logger.error(f"Error saving order to database: {e}", exc_info=True)
                    # Continue conversation even if save fails
        except Exception as e:
            logger.error(f"Error extracting order info: {e}", exc_info=True)
    
    # Check if caller wants to end the call
    user_lower = user_input.lower()
    end_call_phrases = ["no", "no thanks", "nothing else", "that's all", "no that's it", "goodbye", "bye", "that's everything", "yes that's correct", "yes that's right", "correct", "that's correct"]
    if any(phrase in user_lower for phrase in end_call_phrases) and session.get("order_saved"):
        # Final closing message
        # Get voice from business
        business = await get_active_business()
        voice = business.get("voice", "Polly.Matthew-Neural") if business else "Polly.Matthew-Neural"
        response.say(
            "Perfect! Your order is all set. Thank you for calling! Have a great day!",
            voice=voice
        )
        response.hangup()
        return Response(content=str(response), media_type="application/xml")
    
    # Speak the response immediately (removed processing delay for speed)
    gather = Gather(
        input="speech",
        action=f"{BASE_URL}/process",
        method="POST",
        timeout=5,
        speech_timeout="auto",
        language="en-US"
    )
    
    # Get voice from business config
    business = await get_active_business(organization_id)
    voice = "Polly.Matthew-Neural"  # Default
    if business:
        voice = business.get("voice", "Polly.Matthew-Neural")
    
    gather.say(ai_response, voice=voice)
    response.append(gather)
    
    # Fallback for no response
    response.say("I didn't catch that. Could you please repeat?", voice=voice)
    response.redirect(f"{BASE_URL}/process", method="POST")
    
    return Response(content=str(response), media_type="application/xml")


@app.post("/hangup")
async def hangup_call(request: Request):
    """
    Called when call ends. Clean up and send final summary.
    """
    form = await request.form()
    call_sid = form.get("CallSid")
    caller_phone = form.get("From", "Unknown")
    
    # Calculate call duration
    duration_seconds = None
    if call_sid in call_sessions:
        session = call_sessions[call_sid]
        if "start_time" in session:
            duration = datetime.now() - session["start_time"]
            duration_seconds = int(duration.total_seconds())
    
    # Save call end to database
    await save_call_end(call_sid, duration_seconds)
    
    if call_sid in call_sessions:
        session = call_sessions[call_sid]
        
        # Extract final order info - ALWAYS save at end of call
        if session["conversation_history"]:
            try:
                order_info = extract_order_info(session["conversation_history"])
                logger.info(f"Final order extraction for call {call_sid}: {order_info}")
                
                # ALWAYS save order at end of call, even if incomplete
                # This ensures we capture everything that was discussed
                if not session.get("order_saved"):
                    try:
                        # Get organization from session
                        org_id = session.get("organization_id")
                        if not org_id:
                            org_id = await get_organization_by_phone(form.get("Called", ""))
                        # Save to database
                        order_id = await save_order(call_sid, caller_phone, order_info, org_id)
                        logger.info(f"Order saved to database with ID {order_id} for call {call_sid} (end of call)")
                        
                        # Also send email
                        save_order_simple(order_info, caller_phone)
                        session["order_saved"] = True
                    except Exception as e:
                        logger.error(f"Error saving order at end of call: {e}", exc_info=True)
                        # Still try to send email
                        try:
                            save_order_simple(order_info, caller_phone)
                        except Exception as email_error:
                            logger.error(f"Error sending email: {email_error}", exc_info=True)
                else:
                    logger.info(f"Order already saved for call {call_sid}, skipping duplicate save")
                
                # Send summary email with full conversation
                from utils import send_order_summary_email
                conversation_summary = "\n".join([
                    f"Caller: {turn.get('user', '')}\nAssistant: {turn.get('assistant', '')}"
                    for turn in session["conversation_history"]
                ])
                
                # Always send email summary, even if order extraction wasn't perfect
                try:
                    send_order_summary_email(
                        caller_phone=caller_phone,
                        order_info=order_info,
                        conversation_summary=conversation_summary
                    )
                except Exception as e:
                    logger.error(f"Error sending summary email: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error processing order at end of call: {e}", exc_info=True)
        
        # Clean up session
        del call_sessions[call_sid]
    
    response = VoiceResponse()
    response.hangup()
    return Response(content=str(response), media_type="application/xml")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "AI Receptionist"}


# Dashboard API endpoints
@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics."""
    stats = await get_statistics()
    return stats


@app.get("/api/calls")
async def get_calls(limit: int = 50):
    """Get recent calls."""
    calls = await get_recent_calls(limit)
    return {"calls": calls}


@app.get("/api/calls/{call_sid}")
async def get_call(call_sid: str):
    """Get details of a specific call."""
    call = await get_call_details(call_sid)
    if not call:
        return {"error": "Call not found"}, 404
    return call


@app.get("/api/appointments")
async def get_appts(limit: int = 50, search: Optional[str] = None):
    """Get all appointments."""
    if search:
        appointments = await search_appointments(search, limit)
    else:
        appointments = await get_appointments(limit)
    return {"appointments": appointments}


@app.get("/api/calls")
async def get_calls(limit: int = 50, search: Optional[str] = None):
    """Get recent calls."""
    if search:
        calls = await search_calls(search, limit)
    else:
        calls = await get_recent_calls(limit)
    return {"calls": calls}


@app.get("/api/charts")
async def get_charts(days: int = 30):
    """Get chart data."""
    chart_data = await get_chart_data(days)
    return chart_data


@app.put("/api/appointments/{appointment_id}/status")
async def update_appt_status(appointment_id: int, status: str = Query(...)):
    """Update appointment status."""
    await update_appointment_status(appointment_id, status)
    return {"success": True, "appointment_id": appointment_id, "status": status}


@app.get("/api/export/calls")
async def export_calls_csv():
    """Export all calls to CSV."""
    calls = await get_all_calls_for_export()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Call SID", "Caller Phone", "Start Time", "End Time", 
        "Duration (seconds)", "Emergency", "Status", "Conversation Turns"
    ])
    
    # Write data
    for call in calls:
        writer.writerow([
            call.get("call_sid", ""),
            call.get("caller_phone", ""),
            call.get("start_time", ""),
            call.get("end_time", ""),
            call.get("duration_seconds", ""),
            "Yes" if call.get("is_emergency") else "No",
            call.get("status", ""),
            call.get("conversation_turns", 0)
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=calls_export.csv"}
    )


# Order API endpoints
@app.get("/api/orders")
async def get_orders_api(limit: int = 50, status: Optional[str] = None, order_type: Optional[str] = None, search: Optional[str] = None):
    """Get orders with optional filtering."""
    if search:
        orders = await search_orders(search, limit)
    else:
        orders = await get_orders(limit, status, order_type)
    return {"orders": orders}


@app.get("/api/orders/{order_id}")
async def get_order_api(order_id: int):
    """Get a specific order."""
    order = await get_order(order_id)
    if not order:
        return {"error": "Order not found"}, 404
    
    # Get conversation if available
    if order.get("call_sid"):
        call_details = await get_call_details(order["call_sid"])
        order["conversation"] = call_details.get("conversation", []) if call_details else []
    
    return order


@app.put("/api/orders/{order_id}/status")
async def update_order_status_api(order_id: int, status: str = Query(...)):
    """Update order status."""
    await update_order_status(order_id, status)
    return {"success": True, "order_id": order_id, "status": status}


@app.get("/api/orders/stats")
async def get_order_stats():
    """Get order statistics."""
    stats = await get_order_statistics()
    return stats


@app.get("/api/export/orders")
async def export_orders_csv():
    """Export all orders to CSV."""
    orders = await get_orders(limit=10000)  # Get all orders
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "Call SID", "Caller Phone", "Customer Name", "Items", 
        "Order Type", "Delivery Address", "Pickup Name", "Phone Number",
        "Special Instructions", "Payment Method", "Total Estimate",
        "Order Status", "Created At"
    ])
    
    # Write data
    for order in orders:
        writer.writerow([
            order.get("id", ""),
            order.get("call_sid", ""),
            order.get("caller_phone", ""),
            order.get("customer_name", ""),
            order.get("items", ""),
            order.get("order_type", ""),
            order.get("delivery_address", ""),
            order.get("pickup_name", ""),
            order.get("phone_number", ""),
            order.get("special_instructions", ""),
            order.get("payment_method", ""),
            order.get("total_estimate", ""),
            order.get("order_status", ""),
            order.get("created_at", "")
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders_export.csv"}
    )


@app.get("/api/export/appointments")
async def export_appointments_csv():
    """Export all appointments to CSV."""
    appointments = await get_all_appointments_for_export()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "Call SID", "Caller Phone", "Patient Status", "Reason", 
        "Insurance", "Preferred Time", "Caller Name", "Emergency", 
        "Booking Status", "Created At"
    ])
    
    # Write data
    for apt in appointments:
        writer.writerow([
            apt.get("id", ""),
            apt.get("call_sid", ""),
            apt.get("caller_phone", ""),
            apt.get("patient_status", ""),
            apt.get("reason", ""),
            apt.get("insurance", ""),
            apt.get("preferred_time", ""),
            apt.get("caller_name", ""),
            "Yes" if apt.get("is_emergency") else "No",
            apt.get("booking_status", ""),
            apt.get("created_at", "")
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=appointments_export.csv"}
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "AI Phone Receptionist SaaS"}


@app.get("/")
async def root():
    """Serve landing page."""
    return FileResponse("static/landing.html")


@app.get("/login")
async def login_page():
    """Serve login page."""
    return FileResponse("static/login.html")


@app.get("/signup")
async def signup_page():
    """Serve signup page."""
    return FileResponse("static/signup.html")


@app.get("/dashboard")
async def dashboard_page():
    """Serve customer dashboard."""
    return FileResponse("static/customer_dashboard.html")


@app.get("/admin")
async def admin_page():
    """Serve admin dashboard (legacy)."""
    return FileResponse("static/admin.html")


@app.get("/dashboard")
async def dashboard():
    """Serve business dashboard."""
    return FileResponse("static/dashboard.html")

@app.get("/old")
async def old_dashboard():
    """Serve old dashboard."""
    return FileResponse("static/index.html")


# Business Management API endpoints
@app.get("/api/businesses")
async def get_businesses_api(org_id: int = Depends(get_current_organization)):
    """Get all businesses for current organization."""
    businesses = await get_all_businesses(org_id)
    return {"businesses": businesses}


@app.get("/api/businesses/active")
async def get_active_business_api(org_id: int = Depends(get_current_organization)):
    """Get the currently active business for current organization."""
    business = await get_active_business(org_id)
    return {"business": business}


@app.post("/api/businesses/{business_id}/activate")
async def activate_business_api(business_id: int, org_id: int = Depends(get_current_organization)):
    """Activate a business (deactivates all others in organization)."""
    # Verify business belongs to organization
    business = await get_business(business_id)
    if not business or business.get("organization_id") != org_id:
        raise HTTPException(status_code=404, detail="Business not found")
    
    await set_active_business(business_id, org_id)
    # Reload active business in prompts cache
    from prompts import load_active_business
    await load_active_business()
    return {"success": True, "business_id": business_id}


@app.get("/api/businesses/{business_id}")
async def get_business_api(business_id: int, org_id: int = Depends(get_current_organization)):
    """Get a specific business."""
    business = await get_business(business_id)
    if not business or business.get("organization_id") != org_id:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


@app.put("/api/businesses/{business_id}")
async def update_business_api(business_id: int, request: Request, org_id: int = Depends(get_current_organization)):
    """Update business configuration."""
    data = await request.json()
    # Verify business belongs to organization
    business = await get_business(business_id)
    if not business or business.get("organization_id") != org_id:
        raise HTTPException(status_code=404, detail="Business not found")
    
    await update_business(business_id, data)
    # Reload if this is the active business
    active = await get_active_business(org_id)
    if active and active.get("id") == business_id:
        from prompts import load_active_business
        await load_active_business()
    return {"success": True, "business_id": business_id}


# Authentication endpoints
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    organization_name: str
    full_name: str = None


@app.post("/api/auth/login")
async def login(login_data: LoginRequest):
    """Login endpoint."""
    user = await authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"], "org_id": user["organization_id"]},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user.get("full_name"),
            "role": user.get("role"),
            "organization_id": user["organization_id"]
        }
    }


@app.post("/api/auth/signup")
async def signup(signup_data: SignupRequest):
    """Signup endpoint."""
    # Check if user already exists
    from auth import get_user_by_email
    existing_user = await get_user_by_email(signup_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create organization
    org_id = await create_organization(signup_data.organization_name)
    
    # Create user
    user_id = await create_user(
        email=signup_data.email,
        password=signup_data.password,
        organization_id=org_id,
        full_name=signup_data.full_name or signup_data.email.split("@")[0],
        role="admin"
    )
    
    # Create default business for the organization
    from database import init_default_businesses_for_org
    try:
        await init_default_businesses_for_org(org_id)
    except Exception as e:
        logger.error(f"Error creating default business: {e}")
    
    # Login the user
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id, "org_id": org_id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": signup_data.email,
            "full_name": signup_data.full_name,
            "role": "admin",
            "organization_id": org_id
        }
    }


@app.get("/api/auth/me")
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current user information."""
    org = await get_organization(user["organization_id"])
    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user.get("full_name"),
            "role": user.get("role"),
            "organization_id": user["organization_id"]
        },
        "organization": dict(org) if org else None
    }


@app.delete("/api/businesses/{business_id}")
async def delete_business_api(business_id: int):
    """Delete a business."""
    # Check if it's the active business
    active = await get_active_business()
    if active and active.get("id") == business_id:
        return {"error": "Cannot delete active business. Please activate another business first."}, 400
    
    await delete_business(business_id)
    return {"success": True, "business_id": business_id}


@app.delete("/api/businesses/assistant/{assistant_name}")
async def delete_businesses_by_assistant_api(assistant_name: str):
    """Delete all businesses with a specific assistant name."""
    # Check if any are active
    active = await get_active_business()
    if active and active.get("assistant_name") == assistant_name:
        return {"error": f"Cannot delete businesses with assistant '{assistant_name}' as one is currently active. Please activate another business first."}, 400
    
    deleted_count = await delete_businesses_by_assistant_name(assistant_name)
    return {"success": True, "deleted_count": deleted_count, "assistant_name": assistant_name}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

