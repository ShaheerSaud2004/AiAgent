# AI Phone Receptionist - B2B SaaS Platform

A multi-tenant B2B SaaS platform for AI-powered phone receptionists. Built with FastAPI, Twilio, and OpenAI.

## Features

- 🤖 **AI-Powered Phone Receptionist** - Never miss a call with 24/7 intelligent automation
- 🏢 **Multi-Tenant Architecture** - Complete data isolation per organization
- 🔐 **Secure Authentication** - JWT-based user authentication
- 📊 **Analytics Dashboard** - Track calls, orders, and customer interactions
- 🎯 **Multi-Business Support** - Switch between pizza shops, cafes, medical offices, and more
- ⚡ **Fast & Optimized** - GPT-3.5-Turbo with optimized prompts for speed

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite (local) / PostgreSQL (production)
- **Voice**: Twilio Voice API
- **AI**: OpenAI GPT-3.5-Turbo
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Deployment**: Vercel

## Setup

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/ShaheerSaud2004/AiAgent.git
   cd AiAgent
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file:
   ```env
   OPENAI_API_KEY=your_openai_key
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_PHONE_NUMBER=your_twilio_number
   BASE_URL=http://localhost:8000
   OFFICE_PHONE_NUMBER=your_phone
   OFFICE_EMAIL=your_email
   OFFICE_NAME=Your Business Name
   GMAIL_USER=your_gmail
   GMAIL_APP_PASSWORD=your_app_password
   JWT_SECRET_KEY=your_secret_key_change_in_production
   ```

5. **Initialize database**
   ```bash
   python3 -c "from database import init_db; import asyncio; asyncio.run(init_db())"
   ```

6. **Run the server**
   ```bash
   python3 run.py
   ```

7. **Access the application**
   - Landing page: http://localhost:8000/
   - Signup: http://localhost:8000/signup
   - Login: http://localhost:8000/login
   - Dashboard: http://localhost:8000/dashboard

## Deployment to Vercel

### Prerequisites

1. **GitHub Repository** - Code must be pushed to GitHub
2. **Vercel Account** - Sign up at [vercel.com](https://vercel.com)

### Steps

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/ShaheerSaud2004/AiAgent.git
   git push -u origin main
   ```

2. **Deploy to Vercel**
   - Go to [vercel.com](https://vercel.com)
   - Click "New Project"
   - Import your GitHub repository
   - Configure environment variables (see below)
   - Deploy!

3. **Environment Variables in Vercel**
   Add these in Vercel dashboard → Settings → Environment Variables:
   - `OPENAI_API_KEY`
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_PHONE_NUMBER`
   - `BASE_URL` (your Vercel URL)
   - `OFFICE_PHONE_NUMBER`
   - `OFFICE_EMAIL`
   - `OFFICE_NAME`
   - `GMAIL_USER`
   - `GMAIL_APP_PASSWORD`
   - `JWT_SECRET_KEY` (generate a secure random string)

4. **Update Twilio Webhooks**
   - Go to Twilio Console → Phone Numbers
   - Update webhook URLs to your Vercel domain:
     - Voice URL: `https://your-app.vercel.app/answer`
     - Status Callback: `https://your-app.vercel.app/hangup`

## Project Structure

```
AiAgent/
├── main.py              # FastAPI application
├── database.py          # Database operations
├── auth.py              # Authentication & JWT
├── organizations.py     # Organization management
├── utils.py             # AI functions, email
├── prompts.py           # AI prompts
├── run.py               # Local server runner
├── api/
│   └── index.py         # Vercel serverless entry point
├── static/              # Frontend files
│   ├── landing.html     # Landing page
│   ├── login.html       # Login page
│   ├── signup.html      # Signup page
│   ├── customer_dashboard.html
│   └── ...
├── requirements.txt     # Python dependencies
├── vercel.json          # Vercel configuration
└── README.md
```

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Create account
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user

### Businesses
- `GET /api/businesses` - List businesses (protected)
- `GET /api/businesses/active` - Get active business (protected)
- `POST /api/businesses/{id}/activate` - Activate business (protected)

### Twilio Webhooks
- `POST /answer` - Incoming call handler
- `POST /process` - Speech processing
- `POST /hangup` - Call end handler

## Pricing Plans

- **Free**: 50 calls/month, 1 AI bot
- **Starter ($29/mo)**: 500 calls/month, 3 AI bots
- **Pro ($99/mo)**: 2,000 calls/month, 10 AI bots
- **Enterprise**: Custom pricing

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.
