"""
Utility functions for LLM interaction, appointment booking, and email.
"""

import os
import json
import logging
from typing import Dict, Optional
from openai import OpenAI
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize OpenAI client lazily
_client = None

def get_openai_client():
    """Get or create OpenAI client."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        _client = OpenAI(api_key=api_key)
    return _client

# Office configuration
OFFICE_NAME = os.getenv("OFFICE_NAME", "Bright Smile Dental")
OFFICE_EMAIL = os.getenv("OFFICE_EMAIL")
OFFICE_PHONE = os.getenv("OFFICE_PHONE_NUMBER")

# Email configuration
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def generate_response(user_input: str, conversation_history: list = None, system_prompt: str = None) -> str:
    """
    Generate AI response using OpenAI.
    
    Args:
        user_input: The caller's speech input
        conversation_history: Previous conversation turns
        system_prompt: Optional custom system prompt (uses default if None)
    
    Returns:
        AI response text
    """
    from prompts import SYSTEM_PROMPT
    
    if conversation_history is None:
        conversation_history = []
    
    # Use provided system prompt or default
    prompt = system_prompt if system_prompt else SYSTEM_PROMPT
    
    # Build messages
    messages = [{"role": "system", "content": prompt}]
    
    # Add conversation history (only last 4 turns for speed - maintains recent context)
    # This reduces API latency while keeping essential context
    recent_history = conversation_history[-4:] if len(conversation_history) > 4 else conversation_history
    for turn in recent_history:
        messages.append({"role": "user", "content": turn.get("user", "")})
        messages.append({"role": "assistant", "content": turn.get("assistant", "")})
    
    # Add current user input
    messages.append({"role": "user", "content": user_input})
    
    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Fastest OpenAI model for maximum speed
            messages=messages,
            temperature=0.3,  # Lower for faster, more consistent responses
            max_tokens=35,  # Reduced for fastest responses (very brief)
            top_p=0.9,  # Faster generation
            frequency_penalty=0.1  # Reduce repetition
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating response: {e}", exc_info=True)
        return "I apologize, I'm having trouble processing that. Could you please repeat?"


def extract_order_info(conversation_history: list) -> Dict[str, Optional[str]]:
    """
    Extract structured order information from conversation.
    
    Returns:
        Dictionary with order details
    """
    # Combine all conversation text
    full_text = " ".join([
        turn.get("user", "") + " " + turn.get("assistant", "")
        for turn in conversation_history
    ])
    
    # Use LLM to extract structured data
    from prompts import MENU_REFERENCE
    extraction_prompt = f"""Extract pizza order information from this conversation. Match items EXACTLY to the Nunzio's Pizza menu.

MENU:
{MENU_REFERENCE}

Conversation:
{full_text}

Return ONLY a JSON object with these fields:
{{
    "customer_name": name if mentioned or null,
    "items": detailed description of ALL items ordered. MUST match menu items exactly (use exact pizza names from menu: "Vodka Pizza", "Nunzio's Special", "Chicken Parm", etc.). Include size, quantity, customizations. Format as clear string describing each item. If multiple items, list them all. If null, return empty string,
    "order_type": "delivery" or "pickup" or null,
    "delivery_address": full address if delivery mentioned or null,
    "pickup_name": name for pickup order if mentioned or null,
    "phone_number": phone number if mentioned or null,
    "special_instructions": any special requests, instructions, or notes or null,
    "payment_method": "cash" or "card" or null,
    "total_estimate": estimated total price if calculable or null,
    "order_confirmed": true if customer said "yes", "correct", "that's right" to order confirmation, false otherwise
}}

IMPORTANT: 
- Match pizza names EXACTLY to the menu (e.g., "Vodka Pizza", not "vodka sauce pizza")
- Extract everything mentioned, even partial information
- If customer confirmed the order (said yes/correct), set order_confirmed to true"""

    try:
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Fast model for data extraction
            messages=[
                {"role": "system", "content": "You are a data extraction assistant. Return only valid JSON."},
                {"role": "user", "content": extraction_prompt}
            ],
            temperature=0.2,  # Lower for more consistent extraction
            max_tokens=400,  # Reduced for faster response
            top_p=0.9
        )
        
        result_text = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        return json.loads(result_text)
    
    except Exception as e:
        print(f"Error extracting order info: {e}")
        # If extraction fails, try to get basic info from conversation text
        items_text = ""
        for turn in conversation_history:
            user_text = turn.get("user", "").lower()
            if any(word in user_text for word in ["pizza", "order", "want", "like", "get"]):
                items_text += turn.get("user", "") + " "
        
        return {
            "customer_name": None,
            "items": items_text.strip() if items_text else "Order details from conversation (extraction failed)",
            "order_type": None,
            "delivery_address": None,
            "pickup_name": None,
            "phone_number": None,
            "special_instructions": None,
            "payment_method": None,
            "total_estimate": None,
            "order_confirmed": False
        }

# Keep old function name for backward compatibility
def extract_appointment_info(conversation_history: list) -> Dict[str, Optional[str]]:
    """Alias for extract_order_info for backward compatibility."""
    return extract_order_info(conversation_history)


def send_order_summary_email(
    caller_phone: str,
    order_info: Dict,
    conversation_summary: str
) -> bool:
    """
    Send email summary to restaurant.
    
    Args:
        caller_phone: Caller's phone number
        order_info: Extracted order information
        conversation_summary: Summary of the conversation
    
    Returns:
        True if email sent successfully
    """
    if not OFFICE_EMAIL or not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("Email configuration missing. Skipping email send.")
        return False
    
    try:
        # Create email
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = OFFICE_EMAIL
        msg['Subject'] = f"New Order - {OFFICE_NAME}"
        
        # Format items
        items_text = "No items specified"
        if order_info.get('items'):
            if isinstance(order_info['items'], list):
                items_text = "\n".join([f"  - {item}" for item in order_info['items']])
            elif isinstance(order_info['items'], str) and len(order_info['items']) > 0:
                items_text = order_info['items']
            else:
                items_text = str(order_info['items']) if order_info['items'] else "No items specified"
        
        # Build email body
        body = f"""
NEW ORDER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Caller Phone: {caller_phone}

ORDER DETAILS:
- Customer Name: {order_info.get('customer_name', 'Not provided')}
- Order Type: {order_info.get('order_type', 'Not specified').upper() if order_info.get('order_type') else 'Not specified'}
- Delivery Address: {order_info.get('delivery_address', 'N/A')}
- Pickup Name: {order_info.get('pickup_name', 'N/A')}
- Payment Method: {order_info.get('payment_method', 'Not specified')}
- Estimated Total: {order_info.get('total_estimate', 'N/A')}

ITEMS ORDERED:
{items_text}

SPECIAL INSTRUCTIONS:
{order_info.get('special_instructions', 'None')}

CONVERSATION SUMMARY:
{conversation_summary}

---
This order was taken by the AI order system.
Please prepare the order and contact customer if needed.
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"Call summary email sent to {OFFICE_EMAIL}")
        return True
    
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def save_order_simple(order_info: Dict, caller_phone: str) -> bool:
    """
    Save order - sends email and optionally integrates with POS system.
    
    Args:
        order_info: Order details
        caller_phone: Caller's phone number
    
    Returns:
        True if order saved
    """
    # Send email notification
    email_sent = send_order_summary_email(
        caller_phone=caller_phone,
        order_info=order_info,
        conversation_summary="Order placed. See details above."
    )
    
    # Note: POS integration would need to be async - keeping sync for now
    # To enable POS integration, update save_order_simple to be async and call it properly
    # For now, POS integration is available but not automatically called
    # See POS_INTEGRATION_GUIDE.md for setup instructions
    
    return email_sent

# Keep old function name for backward compatibility
def book_appointment_simple(appointment_info: Dict, caller_phone: str) -> bool:
    """Alias for save_order_simple for backward compatibility."""
    return save_order_simple(appointment_info, caller_phone)

# Keep old function name for backward compatibility  
def send_call_summary_email(caller_phone: str, appointment_info: Dict, conversation_summary: str) -> bool:
    """Alias for send_order_summary_email for backward compatibility."""
    return send_order_summary_email(caller_phone, appointment_info, conversation_summary)

