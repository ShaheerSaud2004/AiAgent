# Tech Stack Overview

## 🏗️ Architecture
- **Type**: Full-stack web application with voice integration
- **Pattern**: REST API backend + Static frontend + Voice webhooks
- **Deployment**: Local development with ngrok tunnel

---

## 🔧 Backend (Python)

### Core Framework
- **FastAPI** (v0.104.1+) - Modern, fast web framework for building APIs
  - Async/await support
  - Automatic API documentation
  - Type hints and validation with Pydantic

### Web Server
- **Uvicorn** (v0.24.0+) - ASGI server
  - Hot reload for development
  - Handles async requests efficiently

### Voice/Telephony
- **Twilio** (v8.10.0+) - Voice API integration
  - TwiML (Twilio Markup Language) for call flow
  - Speech recognition via `<Gather>` verb
  - Text-to-speech via Amazon Polly voices
  - Webhook endpoints for call events

### AI/ML
- **OpenAI** (v1.3.5+) - GPT models for conversation
  - Model: `gpt-4o-mini` (fastest, cost-effective)
  - Chat completions API
  - Structured data extraction

### Database
- **aiosqlite** (v0.19.0+) - Async SQLite database
  - SQLite database file: `receptionist.db`
  - Tables: calls, conversations, appointments, orders

### Email
- **smtplib** (built-in) - SMTP email sending
- **email.mime** (built-in) - Email message formatting
  - Gmail SMTP integration
  - HTML/plain text email support

### Configuration
- **python-dotenv** (v1.0.0+) - Environment variable management
  - `.env` file for secrets and configuration

### Validation
- **Pydantic** (v2.8.0+) - Data validation
- **email-validator** (v2.1.0+) - Email format validation

### Utilities
- **python-multipart** (v0.0.6+) - Form data parsing
- **Google API Client** (v2.108.0+) - Google APIs (if needed)

---

## 🎨 Frontend

### Core
- **HTML5** - Markup
- **CSS3** - Styling (vanilla CSS, no frameworks)
- **JavaScript (ES6+)** - Vanilla JS (no frameworks)
  - Fetch API for HTTP requests
  - DOM manipulation
  - Async/await patterns

### Data Visualization
- **Chart.js** (v4.4.0) - Charting library
  - Line charts for call trends
  - Bar charts for appointments
  - CDN hosted

### Design
- Responsive design (mobile-friendly)
- Custom CSS styling
- No CSS frameworks (Bootstrap, Tailwind, etc.)

---

## 🗄️ Database

- **SQLite** - File-based relational database
  - File: `receptionist.db`
  - Schema:
    - `calls` - Call metadata (SID, phone, duration, etc.)
    - `conversations` - Conversation turns (user/assistant exchanges)
    - `appointments` - Appointment bookings (legacy/for reference)
    - `orders` - Pizza orders (items, delivery/pickup, etc.)

---

## 🔌 External Services & APIs

### Voice/Telephony
- **Twilio Voice API**
  - Phone number management
  - Inbound/outbound call handling
  - Speech recognition
  - Text-to-speech (Polly voices)

### AI
- **OpenAI API**
  - GPT-4o-mini for conversation
  - Structured data extraction
  - Natural language understanding

### Email
- **Gmail SMTP**
  - Order confirmation emails
  - Call summaries

### Development/Deployment
- **ngrok** - Tunneling service
  - Exposes localhost to internet
  - HTTPS endpoint for Twilio webhooks

---

## 📁 Project Structure

```
AI Agent/
├── main.py              # FastAPI server, webhooks, API endpoints
├── utils.py             # AI functions, email, order processing
├── prompts.py           # AI system prompts and instructions
├── database.py          # Database operations (SQLite)
├── run.py               # Server launcher
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (secrets)
├── receptionist.db      # SQLite database
├── menu_reference.txt   # Menu data for AI
├── static/              # Frontend files
│   ├── index.html       # Dashboard HTML
│   ├── script.js        # Frontend JavaScript
│   └── style.css        # Styling
└── venv/                # Python virtual environment
```

---

## 🚀 Runtime Environment

- **Language**: Python 3.14 (or compatible 3.8+)
- **Runtime**: CPython
- **Package Management**: pip
- **Virtual Environment**: venv
- **OS**: Cross-platform (macOS, Linux, Windows)

---

## 🔄 Data Flow

1. **Incoming Call** → Twilio → `/answer` webhook
2. **Speech Input** → Twilio Speech Recognition → `/process` webhook
3. **AI Processing** → OpenAI GPT-4o-mini → Response generation
4. **Data Storage** → SQLite database (orders, conversations)
5. **Notifications** → Gmail SMTP (email summaries)
6. **Dashboard** → FastAPI REST API → Frontend (Chart.js)

---

## 🔐 Security & Configuration

- Environment variables (`.env` file)
  - API keys (OpenAI, Twilio)
  - Email credentials
  - Phone numbers
  - Office information
- Twilio webhook validation (optional)
- HTTPS via ngrok (development)

---

## 📊 Key Features

- Real-time voice conversations
- AI-powered order taking
- Speech-to-text (Twilio)
- Text-to-speech (Twilio/Polly)
- Order extraction and storage
- Email notifications
- Dashboard analytics
- CSV export functionality
- Call history tracking

---

## 🛠️ Development Tools

- **Python logging** - Debugging and monitoring
- **Uvicorn hot reload** - Auto-restart on code changes
- **ngrok web interface** - Request inspection (localhost:4040)

---

*Last updated: Based on current codebase analysis*


