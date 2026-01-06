"""
Response templates for common phrases to speed up responses.
These are used as fallbacks or quick responses for common scenarios.
"""

RESPONSE_TEMPLATES = {
    "greeting_acknowledgment": [
        "Got it!",
        "Sure thing!",
        "Absolutely!",
        "Of course!"
    ],
    "order_confirmation": [
        "Got it, {item}!",
        "Perfect, {item}!",
        "You said {item}, got it!",
        "{item}, noted!"
    ],
    "asking_size": [
        "What size?",
        "What size would you like?",
        "Size?",
        "Small, medium, or large?"
    ],
    "asking_delivery_pickup": [
        "Delivery or pickup?",
        "Is this for delivery or pickup?",
        "Pickup or delivery?",
        "Delivery or pickup today?"
    ],
    "asking_address": [
        "What's the delivery address?",
        "Delivery address?",
        "Where should we deliver?",
        "What address?"
    ],
    "asking_name": [
        "What name for the order?",
        "Name for pickup?",
        "What name should I put this under?",
        "Name?"
    ],
    "asking_anything_else": [
        "Anything else?",
        "Is that everything?",
        "That's it?",
        "Need anything else?"
    ],
    "order_complete": [
        "Perfect! Your order is all set.",
        "Got it! Your order is ready.",
        "All set!",
        "Perfect! Order confirmed."
    ],
    "thank_you": [
        "Thank you!",
        "Thanks!",
        "Thank you for calling!",
        "Appreciate it!"
    ]
}

def get_template_response(template_key: str, **kwargs) -> str:
    """Get a random template response."""
    import random
    templates = RESPONSE_TEMPLATES.get(template_key, [])
    if templates:
        response = random.choice(templates)
        return response.format(**kwargs) if kwargs else response
    return ""

