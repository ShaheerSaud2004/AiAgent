# Vercel Environment Variables - Complete List

## ✅ Add These to Vercel (Settings → Environment Variables)

### Database (Supabase Postgres)
```
POSTGRES_URL=postgres://postgres.qiahalzjtrhsgzskdhnc:G2aQAI5tmv6dT3zH@aws-1-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require&supa=base-pooler.x
```

### OpenAI
```
OPENAI_API_KEY=your_openai_key_here
```

### Twilio
```
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_phone
```

### Gmail
```
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
```

### Office Info
```
OFFICE_PHONE_NUMBER=your_office_phone
OFFICE_EMAIL=your_email@example.com
OFFICE_NAME=Your Business Name
```

### App Configuration
```
BASE_URL=https://your-app.vercel.app
JWT_SECRET_KEY=generate_secure_random_string
```

## ❌ DO NOT ADD (These are for Next.js frontend only)

These `NEXT_PUBLIC_*` variables are for Next.js frontend apps, not needed for FastAPI:
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` ❌
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` ❌
- `NEXT_PUBLIC_SUPABASE_URL` ❌
- `SUPABASE_PUBLISHABLE_KEY` ❌
- `SUPABASE_SECRET_KEY` ❌
- `SUPABASE_SERVICE_ROLE_KEY` ❌
- `SUPABASE_URL` ❌
- `SUPABASE_JWT_SECRET` ❌

## 📝 Summary

**You only need `POSTGRES_URL` from Supabase!**

The backend uses `asyncpg` to connect directly to Postgres using the connection string. We don't use the Supabase client library, so we don't need the Supabase API keys.

## 🔑 Quick Setup

1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables
2. Add `POSTGRES_URL` with your Supabase connection string
3. Add all your existing API keys (OpenAI, Twilio, Gmail, etc.)
4. **Do NOT add any `NEXT_PUBLIC_*` or `SUPABASE_*` variables** (except POSTGRES_URL)
