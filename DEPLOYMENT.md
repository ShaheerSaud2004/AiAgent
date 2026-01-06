# Deployment Guide - Vercel

## Quick Deploy Steps

### 1. Push to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - AI Phone Receptionist SaaS"

# Add remote (if not already added)
git remote add origin https://github.com/ShaheerSaud2004/AiAgent.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### 2. Deploy to Vercel

1. **Go to Vercel Dashboard**
   - Visit [vercel.com](https://vercel.com)
   - Sign in with GitHub

2. **Import Project**
   - Click "Add New..." → "Project"
   - Select your GitHub repository: `ShaheerSaud2004/AiAgent`
   - Click "Import"

3. **Configure Project**
   - **Framework Preset**: Other (or leave blank)
   - **Root Directory**: `./` (default)
   - **Build Command**: Leave empty (Vercel auto-detects)
   - **Output Directory**: Leave empty
   - **Install Command**: `pip install -r requirements.txt`

4. **Add Environment Variables**
   Click "Environment Variables" and add:

   ```
   OPENAI_API_KEY=your_openai_key_here
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_PHONE_NUMBER=your_twilio_number
   BASE_URL=https://your-app.vercel.app
   OFFICE_PHONE_NUMBER=your_phone
   OFFICE_EMAIL=your_email
   OFFICE_NAME=Your Business Name
   GMAIL_USER=your_gmail
   GMAIL_APP_PASSWORD=your_app_password
   JWT_SECRET_KEY=generate_a_secure_random_string_here
   DATABASE_URL=/tmp/receptionist.db
   ```

   **Important**: Generate a secure `JWT_SECRET_KEY`:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

5. **Deploy**
   - Click "Deploy"
   - Wait for build to complete
   - Copy your deployment URL (e.g., `https://ai-agent.vercel.app`)

### 3. Update Twilio Webhooks

1. **Go to Twilio Console**
   - Visit [console.twilio.com](https://console.twilio.com)
   - Navigate to Phone Numbers → Manage → Active Numbers
   - Click on your phone number

2. **Update Webhooks**
   - **Voice & Fax** → **A CALL COMES IN**:
     - Webhook URL: `https://your-app.vercel.app/answer`
     - HTTP: `POST`
   
   - **Voice & Fax** → **CALL STATUS CHANGES**:
     - Webhook URL: `https://your-app.vercel.app/hangup`
     - HTTP: `POST`

3. **Save Configuration**

### 4. Update BASE_URL in Vercel

After deployment, update the `BASE_URL` environment variable in Vercel:
- Go to Vercel Dashboard → Your Project → Settings → Environment Variables
- Update `BASE_URL` to your actual Vercel URL
- Redeploy (or it will auto-update)

## Important Notes

### Database Limitations on Vercel

⚠️ **SQLite on Vercel**: Vercel's serverless functions are stateless. SQLite files in `/tmp` are **ephemeral** and will be lost between deployments.

**Solutions**:
1. **Use Vercel Postgres** (Recommended)
   - Add Vercel Postgres in Vercel dashboard
   - Update `database.py` to use PostgreSQL instead of SQLite
   - Connection string will be in `DATABASE_URL` env var

2. **Use External Database**
   - Supabase (free tier available)
   - PlanetScale
   - Railway
   - Render

3. **For Testing Only**: Current SQLite setup works for testing but data won't persist

### File System

- Vercel serverless functions can write to `/tmp` directory
- Files in `/tmp` are temporary and cleared between invocations
- Static files should be in `static/` directory (served automatically)

### Function Timeout

- Default timeout: 10 seconds
- Maximum timeout: 30 seconds (configured in `vercel.json`)
- For longer operations, consider background jobs

## Troubleshooting

### Build Fails

1. Check `requirements.txt` - ensure all dependencies are listed
2. Check Python version compatibility
3. Review build logs in Vercel dashboard

### Database Errors

1. Ensure `DATABASE_URL` is set correctly
2. For SQLite, ensure path is `/tmp/receptionist.db`
3. Consider migrating to PostgreSQL

### Webhook Not Working

1. Verify Twilio webhook URLs are correct
2. Check Vercel function logs
3. Ensure `BASE_URL` environment variable is set

### Static Files Not Loading

1. Static files are automatically served from `static/` directory
2. Check file paths in HTML/CSS
3. Ensure files are committed to git

## Next Steps

1. **Migrate to PostgreSQL** (for production)
2. **Add Vercel Postgres** integration
3. **Set up custom domain** (optional)
4. **Configure CI/CD** (automatic deployments on git push)

## Support

If you encounter issues:
1. Check Vercel function logs
2. Review Twilio webhook logs
3. Check environment variables
4. Open an issue on GitHub

