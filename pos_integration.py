"""
POS System Integration Module

Handles integration with various Point of Sale systems.
Supports: Square, Toast, Clover, and generic REST API.
"""

import os
import json
import logging
import httpx
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# POS Configuration from environment
POS_SYSTEM = os.getenv("POS_SYSTEM", "").lower()
POS_API_KEY = os.getenv("POS_API_KEY", "")
POS_LOCATION_ID = os.getenv("POS_LOCATION_ID", "")
POS_API_URL = os.getenv("POS_API_URL", "")


async def create_pos_order(order_info: Dict, caller_phone: str) -> Dict:
    """
    Create order in POS system based on configured provider.
    
    Args:
        order_info: Order details dictionary
        caller_phone: Customer phone number
    
    Returns:
        Dict with success status and POS order ID if successful
    """
    if not POS_SYSTEM or not POS_API_KEY:
        logger.warning("POS integration not configured")
        return {"success": False, "error": "POS not configured"}
    
    try:
        if POS_SYSTEM == "square":
            return await create_square_order(order_info, caller_phone)
        elif POS_SYSTEM == "toast":
            return await create_toast_order(order_info, caller_phone)
        elif POS_SYSTEM == "clover":
            return await create_clover_order(order_info, caller_phone)
        elif POS_SYSTEM == "generic":
            return await create_generic_order(order_info, caller_phone)
        else:
            logger.error(f"Unsupported POS system: {POS_SYSTEM}")
            return {"success": False, "error": f"Unsupported POS: {POS_SYSTEM}"}
    except Exception as e:
        logger.error(f"Error creating POS order: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def create_square_order(order_info: Dict, caller_phone: str) -> Dict:
    """
    Create order in Square POS.
    
    Square API Documentation: https://developer.squareup.com/reference/square/orders-api
    """
    try:
        # Parse items from order_info
        items = parse_order_items(order_info.get("items", ""))
        
        # Build Square order line items
        line_items = []
        for item in items:
            # Note: You'll need to map menu items to Square catalog item IDs
            # This is a simplified example - actual implementation needs catalog mapping
            line_items.append({
                "quantity": item.get("quantity", "1"),
                "name": item.get("name", ""),
                # "catalog_object_id": "ITEM_ID_FROM_SQUARE",  # Map menu items to Square catalog
                "variation_name": item.get("size", ""),
            })
        
        # Build Square order payload
        order_data = {
            "idempotency_key": f"order_{caller_phone}_{order_info.get('order_type', 'pickup')}",
            "order": {
                "location_id": POS_LOCATION_ID,
                "line_items": line_items,
                "fulfillments": [{
                    "type": "PICKUP" if order_info.get("order_type") == "pickup" else "SHIPMENT",
                    "pickup_details" if order_info.get("order_type") == "pickup" else "shipment_details": {
                        "recipient": {
                            "display_name": order_info.get("pickup_name") or order_info.get("customer_name", ""),
                            "phone_number": caller_phone,
                        },
                        "expected_duration": "PT30M"
                    } if order_info.get("order_type") == "pickup" else {
                        "recipient": {
                            "display_name": order_info.get("customer_name", ""),
                            "address": {
                                "address_line_1": order_info.get("delivery_address", "")
                            },
                            "phone_number": caller_phone,
                        }
                    }
                }],
                "note": order_info.get("special_instructions", "")
            }
        }
        
        # Make API call to Square
        headers = {
            "Authorization": f"Bearer {POS_API_KEY}",
            "Content-Type": "application/json",
            "Square-Version": "2023-10-18"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{POS_API_URL}/orders",
                json=order_data,
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "pos_order_id": result.get("order", {}).get("id"),
                "pos_system": "square"
            }
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Square API error: {e.response.text}")
        return {"success": False, "error": f"Square API error: {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Error creating Square order: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def create_toast_order(order_info: Dict, caller_phone: str) -> Dict:
    """
    Create order in Toast POS.
    
    Toast API Documentation: https://developer.toasttab.com/
    """
    try:
        items = parse_order_items(order_info.get("items", ""))
        
        # Build Toast order payload
        order_data = {
            "guid": f"order_{caller_phone}",
            "checks": [{
                "orderedItems": [
                    {
                        "itemGuid": item.get("toast_item_id", ""),  # Need to map menu items to Toast GUIDs
                        "quantity": int(item.get("quantity", 1)),
                        "modifiers": []
                    }
                    for item in items
                ],
                "customer": {
                    "firstName": order_info.get("customer_name", "").split()[0] if order_info.get("customer_name") else "",
                    "phone": caller_phone
                },
                "serviceType": order_info.get("order_type", "PICKUP").upper(),
                "guestCount": 1,
                "note": order_info.get("special_instructions", "")
            }]
        }
        
        headers = {
            "Authorization": f"Bearer {POS_API_KEY}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{POS_API_URL}/online-ordering/v2/orders",
                json=order_data,
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "pos_order_id": result.get("guid"),
                "pos_system": "toast"
            }
            
    except Exception as e:
        logger.error(f"Error creating Toast order: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def create_clover_order(order_info: Dict, caller_phone: str) -> Dict:
    """
    Create order in Clover POS.
    
    Clover API Documentation: https://docs.clover.com/
    """
    try:
        items = parse_order_items(order_info.get("items", ""))
        
        # Build Clover order payload
        order_data = {
            "currency": "USD",
            "title": f"Order from {caller_phone}",
            "note": order_info.get("special_instructions", ""),
            "orderType": {
                "id": "PICKUP" if order_info.get("order_type") == "pickup" else "DELIVERY"
            },
            "lineItems": [
                {
                    "item": {
                        "id": item.get("clover_item_id", "")  # Need to map menu items
                    },
                    "unitQty": int(item.get("quantity", 1))
                }
                for item in items
            ]
        }
        
        headers = {
            "Authorization": f"Bearer {POS_API_KEY}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{POS_API_URL}/v3/merchants/{POS_LOCATION_ID}/orders",
                json=order_data,
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "success": True,
                "pos_order_id": result.get("id"),
                "pos_system": "clover"
            }
            
    except Exception as e:
        logger.error(f"Error creating Clover order: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def create_generic_order(order_info: Dict, caller_phone: str) -> Dict:
    """
    Create order via generic REST API endpoint.
    For custom POS systems or webhooks.
    """
    try:
        # Build generic order payload
        order_data = {
            "phone": caller_phone,
            "customer_name": order_info.get("customer_name"),
            "items": order_info.get("items"),
            "order_type": order_info.get("order_type"),
            "delivery_address": order_info.get("delivery_address"),
            "pickup_name": order_info.get("pickup_name"),
            "special_instructions": order_info.get("special_instructions"),
            "payment_method": order_info.get("payment_method"),
            "total_estimate": order_info.get("total_estimate")
        }
        
        headers = {
            "Authorization": f"Bearer {POS_API_KEY}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                POS_API_URL,
                json=order_data,
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "pos_order_id": response.json().get("order_id"),
                "pos_system": "generic"
            }
            
    except Exception as e:
        logger.error(f"Error creating generic order: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def parse_order_items(items_str: str) -> list:
    """
    Parse order items string into structured format.
    
    Args:
        items_str: String or JSON containing order items
    
    Returns:
        List of item dictionaries
    """
    items = []
    
    try:
        # Try parsing as JSON first
        if isinstance(items_str, str):
            parsed = json.loads(items_str)
            if isinstance(parsed, list):
                items = parsed
            elif isinstance(parsed, dict) and "items" in parsed:
                items = parsed["items"]
        elif isinstance(items_str, list):
            items = items_str
    except (json.JSONDecodeError, TypeError):
        # If not JSON, create simple item from string
        items = [{"name": items_str, "quantity": 1, "size": ""}]
    
    return items


# Note: For production use, you'll need to:
# 1. Create a menu mapping (menu items → POS item IDs)
# 2. Handle authentication (OAuth, API keys)
# 3. Map item names from your menu to POS catalog items
# 4. Handle pricing and taxes
# 5. Test thoroughly with your specific POS system

