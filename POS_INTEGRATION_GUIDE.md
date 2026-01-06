# POS Integration Guide

## Current Order Flow

Orders are currently saved to:
1. **SQLite Database** (`receptionist.db` → `orders` table)
2. **Email Notifications** (sent to restaurant email)

## Integration Approach

### Option 1: Direct POS API Integration (Recommended)

Connect directly to your POS system's API to create orders automatically.

**Common POS Systems & APIs:**

#### 1. **Square POS** ⭐ Popular for Restaurants
- API: Square Connect API
- Documentation: https://developer.squareup.com/docs
- Features: Orders API, Payments API
- Requires: OAuth token, Location ID

#### 2. **Toast POS** ⭐ Restaurant-Focused
- API: Toast Platform API
- Documentation: https://developer.toasttab.com/
- Features: Online Ordering API, Menu API
- Requires: API Key, Restaurant ID

#### 3. **Clover POS**
- API: Clover REST API
- Documentation: https://docs.clover.com/
- Features: Orders API, Items API
- Requires: API Token, Merchant ID

#### 4. **Lightspeed Restaurant**
- API: Lightspeed Restaurant API
- Documentation: https://developers.lightspeedhq.com/
- Features: Orders, Menu Items
- Requires: OAuth, Account ID

#### 5. **TouchBistro**
- API: TouchBistro API
- Documentation: https://developer.touchbistro.com/
- Features: Orders, Menu
- Requires: API Key

### Option 2: Webhook Integration

Your POS system sends webhooks → Your system processes orders

### Option 3: Middleware (Zapier, Make.com)

Use middleware to connect:
- Twilio/Your System → Zapier/Make → POS System

## Implementation Steps

### Step 1: Get POS API Credentials

1. Log into your POS system's developer/admin portal
2. Create an API application
3. Get:
   - API Key / Access Token
   - Location/Merchant ID
   - API Endpoint URL

### Step 2: Add Credentials to `.env`

```bash
# POS Configuration
POS_SYSTEM=square  # or toast, clover, etc.
POS_API_KEY=your_api_key_here
POS_LOCATION_ID=your_location_id
POS_API_URL=https://api.squareup.com/v2
```

### Step 3: Install POS SDK (if available)

For Square:
```bash
pip install squareup
```

For Toast:
```bash
pip install toast-api
```

### Step 4: Create POS Integration Module

Create `pos_integration.py` (see example below)

### Step 5: Update `save_order_simple()` function

Modify `utils.py` to call POS integration after saving to database.

## Example Code Structure

See `pos_integration.py` for implementation examples.

## Testing

1. Test with a small order first
2. Verify order appears in POS system
3. Check for errors in logs
4. Test with different order types (delivery/pickup)

## Troubleshooting

- **API Errors**: Check API credentials and permissions
- **Item Matching**: Ensure menu items match POS item names/IDs
- **Order Format**: Verify order data format matches POS requirements
- **Rate Limits**: Check POS API rate limits

## Support Resources

- Square: https://developer.squareup.com/docs
- Toast: https://developer.toasttab.com/docs
- Clover: https://docs.clover.com/
- Lightspeed: https://developers.lightspeedhq.com/


