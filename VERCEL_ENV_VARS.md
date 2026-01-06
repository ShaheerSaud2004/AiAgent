# Vercel Environment Variables - Complete List

## ✅ Add These to Vercel (Settings → Environment Variables)

### Database (Supabase Postgres)
```
POSTGRES_URL=postgres://postgres.qiahalzjtrhsgzskdhnc:G2aQAI5tmv6dT3zH@aws-1-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require&supa=base-pooler.x
```

### OpenAI
```
OPENAI_API_KEY=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
```

### Twilio
```
TWILIO_ACCOUNT_SID=AC35ef2a3d6d64e383a1d422136db6a673
TWILIO_AUTH_TOKEN=10f7fed78203387aa97eccd19ae3ab1c
TWILIO_PHONE_NUMBER=+17323147497
```

### Gmail
```
GMAIL_USER=shaheersaud2004@gmail.com
GMAIL_APP_PASSWORD=ubtdnoasbjvvqwmk
```

### Office Info
```
OFFICE_PHONE_NUMBER=+17326464595
OFFICE_EMAIL=shaheersaud2004@gmail.com
OFFICE_NAME=Nunzio's Pizza
```

### App Configuration
```
BASE_URL=https://ai-agentic-sage.vercel.app
JWT_SECRET_KEY=DXXVeIc5uzN25ai8kh8p061IpaO0B-NlhnUyUWK9s5U
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

