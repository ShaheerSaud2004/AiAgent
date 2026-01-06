# Quick POS Setup Instructions

## Step 1: Choose Your POS System

Which POS system does the restaurant use?
- Square
- Toast
- Clover
- Lightspeed
- Other (generic REST API)

## Step 2: Get API Credentials

### For Square:
1. Go to https://developer.squareup.com/
2. Create account / log in
3. Create new application
4. Get Access Token
5. Get Location ID from Square Dashboard

### For Toast:
1. Go to https://developer.toasttab.com/
2. Create developer account
3. Register your application
4. Get API Key and Restaurant ID

### For Clover:
1. Go to https://docs.clover.com/
2. Register application
3. Get API Token and Merchant ID

## Step 3: Add to .env File

Add these lines to your `.env` file:

```bash
# POS Integration (choose one)
POS_SYSTEM=square  # or toast, clover, generic
POS_API_KEY=your_api_key_here
POS_LOCATION_ID=your_location_id_here
POS_API_URL=https://api.squareup.com/v2  # or your POS API URL
```

## Step 4: Install Additional Dependencies (if needed)

For Square:
```bash
pip install squareup
```

For HTTP requests (already included):
```bash
pip install httpx
```

## Step 5: Test Integration

1. Make a test order via phone
2. Check logs for POS integration messages
3. Verify order appears in your POS system

## Step 6: Map Menu Items (Important!)

You'll need to create a mapping between your menu items and POS item IDs.

Create a `menu_mapping.json` file:

```json
{
  "Vodka Pizza": {
    "square_id": "ITEM_ID_FROM_SQUARE",
    "toast_id": "ITEM_GUID_FROM_TOAST"
  },
  "Large Pepperoni": {
    "square_id": "ITEM_ID_FROM_SQUARE"
  }
}
```

## Current Status

POS integration code is ready but not automatically enabled.
- Orders are saved to database ✓
- Orders are sent via email ✓
- POS integration available but needs configuration ⚠️

See `POS_INTEGRATION_GUIDE.md` for detailed implementation guide.


