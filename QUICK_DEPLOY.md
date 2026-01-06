# 🚀 Quick Deploy to Vercel

## Step 1: Push to GitHub

Run these commands:

```bash
cd "/Users/shaheersaud/AI Agent"
git add .
git commit -m "Initial commit - AI Phone Receptionist SaaS"
git branch -M main
git push -u origin main
```

**Note**: If you get authentication errors, you may need to:
- Set up GitHub CLI: `gh auth login`
- Or use a personal access token

## Step 2: Deploy to Vercel

1. Go to https://vercel.com and sign in with GitHub
2. Click "Add New..." → "Project"
3. Import repository: `ShaheerSaud2004/AiAgent`
4. Configure:
   - Framework: Other
   - Root Directory: `./`
   - Build Command: (leave empty)
   - Output Directory: (leave empty)

## Step 3: Add Environment Variables

In Vercel dashboard → Settings → Environment Variables, add:

```
OPENAI_API_KEY=your_key_here
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=your_number
BASE_URL=https://your-app.vercel.app (update after first deploy)
OFFICE_PHONE_NUMBER=your_phone
OFFICE_EMAIL=your_email
OFFICE_NAME=Your Business
GMAIL_USER=your_gmail
GMAIL_APP_PASSWORD=your_app_password
JWT_SECRET_KEY=run: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
DATABASE_URL=/tmp/receptionist.db
```

## Step 4: Deploy & Update Webhooks

1. Click "Deploy"
2. Copy your Vercel URL (e.g., `https://ai-agent.vercel.app`)
3. Update `BASE_URL` in Vercel env vars
4. Update Twilio webhooks:
   - Voice URL: `https://your-app.vercel.app/answer`
   - Status: `https://your-app.vercel.app/hangup`

## ⚠️ Important Notes

- **Database**: SQLite on Vercel is temporary. For production, use Vercel Postgres or external DB.
- **First Deploy**: Update `BASE_URL` after getting your Vercel URL.
- **Webhooks**: Must update Twilio after deployment.

## Need Help?

See `DEPLOYMENT.md` for detailed instructions.
