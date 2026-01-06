# B2B SaaS Conversion Plan

## Overview
Convert the AI Phone Receptionist from a single-tenant system to a multi-tenant B2B SaaS platform.

## Core Requirements

### 1. Multi-Tenancy Architecture
- **Organizations/Tenants**: Each customer is an organization
- **Data Isolation**: Complete separation between organizations
- **Shared Infrastructure**: Single codebase, multi-tenant database

### 2. User Management
- **Authentication**: JWT-based auth system
- **Roles**: Super Admin, Org Admin, Org User
- **User Management**: Invite users, manage permissions

### 3. Subscription & Billing
- **Plans**: Free, Starter, Pro, Enterprise
- **Billing**: Stripe integration
- **Usage Limits**: Calls per month, features per plan
- **Invoicing**: Automatic billing, receipts

### 4. Customer Onboarding
- **Signup Flow**: Email/password, organization creation
- **Setup Wizard**: Configure phone number, business type, greeting
- **Twilio Setup**: Guide customers through Twilio configuration

### 5. Customer Dashboard
- **Business Management**: Create/edit/delete AI bots
- **Call Analytics**: View calls, orders, statistics
- **Settings**: Configure business details, voice, prompts
- **Billing**: View invoices, update payment method

### 6. API Access
- **API Keys**: Generate/manage API keys per organization
- **Rate Limiting**: Per-organization limits
- **Webhooks**: Allow customers to receive call events

### 7. Super Admin Dashboard
- **Customer Management**: View all organizations, users
- **Analytics**: Platform-wide metrics
- **Billing Management**: Handle subscriptions, refunds
- **Support**: Customer support tools

## Database Schema Changes

### New Tables Needed:
1. **organizations** - Customer organizations
2. **users** - User accounts (linked to organizations)
3. **subscriptions** - Subscription plans and billing
4. **api_keys** - API authentication keys
5. **usage_metrics** - Track calls, API usage per org
6. **invoices** - Billing records

### Modified Tables:
- **businesses** - Add `organization_id` foreign key
- **calls** - Add `organization_id` foreign key
- **orders** - Add `organization_id` foreign key
- All tables need organization isolation

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Multi-tenant database schema
- [ ] User authentication (JWT)
- [ ] Organization management
- [ ] Basic customer dashboard

### Phase 2: Core Features (Week 3-4)
- [ ] Business management per organization
- [ ] Call routing with organization context
- [ ] Data isolation enforcement
- [ ] Customer onboarding flow

### Phase 3: Billing (Week 5-6)
- [ ] Stripe integration
- [ ] Subscription management
- [ ] Usage tracking
- [ ] Invoice generation

### Phase 4: Advanced Features (Week 7-8)
- [ ] API key system
- [ ] Webhooks
- [ ] Super admin dashboard
- [ ] Analytics & reporting

### Phase 5: Polish (Week 9-10)
- [ ] Email notifications
- [ ] Documentation
- [ ] Testing
- [ ] Deployment

## Technology Stack Additions

### Authentication
- **FastAPI Users** or **Authlib** - User management
- **JWT** - Token-based authentication
- **bcrypt** - Password hashing

### Billing
- **Stripe** - Payment processing
- **Stripe Python SDK** - Integration

### Email
- **SendGrid** or **Resend** - Transactional emails
- **Jinja2** - Email templates

### Monitoring
- **Sentry** - Error tracking
- **Posthog** or **Mixpanel** - Analytics

## Pricing Plans

### Free Tier
- 50 calls/month
- 1 AI bot
- Basic analytics
- Email support

### Starter ($29/month)
- 500 calls/month
- 3 AI bots
- Advanced analytics
- Priority support
- API access

### Pro ($99/month)
- 2,000 calls/month
- 10 AI bots
- Custom voice options
- Webhooks
- Dedicated support

### Enterprise (Custom)
- Unlimited calls
- Unlimited bots
- Custom integrations
- SLA guarantee
- Dedicated account manager

## Security Considerations

1. **Data Isolation**: Row-level security, ensure no cross-org data access
2. **API Security**: Rate limiting, API key validation
3. **Authentication**: Secure JWT, refresh tokens
4. **Payment Security**: PCI compliance via Stripe
5. **Encryption**: Encrypt sensitive data at rest

## Deployment Strategy

### Infrastructure
- **Database**: PostgreSQL (multi-tenant ready)
- **Hosting**: AWS/GCP/Azure
- **CDN**: CloudFront/Cloudflare
- **Load Balancer**: For scaling

### Scaling
- **Horizontal Scaling**: Multiple app instances
- **Database**: Read replicas, connection pooling
- **Caching**: Redis for sessions, frequently accessed data

## Next Steps

1. Review this plan
2. Choose implementation approach (gradual vs. full rewrite)
3. Set up development environment
4. Start with Phase 1 (Foundation)

