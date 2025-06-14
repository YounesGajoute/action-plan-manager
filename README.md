# 🎯 Action Plan Management System

> A comprehensive task management solution built with React, TypeScript, and Flask, featuring Microsoft 365 integration and real-time collaboration.

[![React](https://img.shields.io/badge/React-18.2.0-blue)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-4.9.5-blue)](https://www.typescriptlang.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green)](https://flask.palletsprojects.com/)
[![Material-UI](https://img.shields.io/badge/Material--UI-5.14.20-blue)](https://mui.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://docs.docker.com/compose/)

## 🌟 Features

### 📊 **Task Management**
- ✅ Create, edit, and track action plans
- 📋 Excel file integration and synchronization
- 🏷️ Categories: Installation, Réparation, Développement, Livraison, Commercial
- ⏰ Deadline management and notifications
- 📈 Priority levels and status tracking

### 🔄 **Microsoft 365 Integration**
- 🗂️ OneDrive automatic synchronization
- 📧 Outlook email notifications
- 👤 Azure AD authentication
- 📅 Calendar integration for deadlines

### 📱 **Multi-Platform Support**
- 💻 Responsive web application
- 🤖 Telegram bot integration
- 📱 Mobile-friendly PWA
- 🖥️ Desktop notifications

### 📈 **Analytics & Reporting**
- 📊 Real-time dashboard
- 📈 Performance metrics
- 📉 Task completion analytics
- 📋 Exportable reports (Excel, CSV, PDF)

### 🔒 **Security & Access Control**
- 🔐 Role-based permissions (Admin, Manager, User, Read-only)
- 🛡️ JWT authentication
- 🔑 Microsoft 365 SSO
- 🚫 Rate limiting and security headers

### ⚡ **Real-time Features**
- 🔄 Live updates via WebSocket
- 👥 Multi-user collaboration
- 🔔 Instant notifications
- 📊 Live dashboard metrics

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Frontend (React + TypeScript)"
        A[Web App] --> B[Redux Store]
        B --> C[Material-UI Components]
        C --> D[WebSocket Client]
    end
    
    subgraph "Backend (Flask + Python)"
        E[Flask API] --> F[JWT Auth]
        F --> G[SQLAlchemy ORM]
        G --> H[PostgreSQL]
        E --> I[SocketIO Server]
    end
    
    subgraph "Microsoft 365"
        J[Azure AD] --> K[Graph API]
        K --> L[OneDrive]
        K --> M[Outlook]
    end
    
    subgraph "Services"
        N[Redis Cache] --> O[Celery Tasks]
        O --> P[Email Service]
        O --> Q[Telegram Bot]
    end
    
    A --> E
    E --> J
    E --> N
    
    subgraph "Deployment"
        R[Docker Compose] --> S[Nginx Proxy]
        S --> T[SSL/TLS]
    end
```

## 🚀 Quick Start

### Prerequisites
- **Node.js 18+**
- **Python 3.11+**
- **Docker & Docker Compose**
- **PostgreSQL 15+**
- **Redis 7+**

### 1. 📥 Download & Setup

```bash
# Clone the repository
git clone <repository-url>
cd action-plan-manager

# Run automated setup
chmod +x setup.sh
./setup.sh
```

### 2. ⚙️ Configuration

Edit `.env` file with your settings:

```env
# Microsoft 365 (required)
MS_TENANT_ID=your-azure-tenant-id
MS_CLIENT_ID=your-azure-client-id
MS_CLIENT_SECRET=your-azure-client-secret

# Database
DATABASE_URL=postgresql://actionplan:password@localhost:5432/actionplan

# Security
JWT_SECRET=your-very-secure-jwt-secret

# Optional: Telegram Bot
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
```

### 3. 🚀 Start the Application

**Development Mode:**
```bash
./dev-start.sh
```

**Production Mode (Docker):**
```bash
./prod-start.sh
```

### 4. 📊 Import Your Data

```bash
# Place your Excel file in the data directory
cp "Plan d'action.xlsx" ./data/

# Import the data
python scripts/import_excel.py ./data/Plan_daction.xlsx
```

### 5. 🎉 Access the Application

- **Frontend**: http://localhost:3000
- **API**: http://localhost:5000
- **Grafana**: http://localhost:3001

## 📱 Telegram Bot Setup

### 1. Create Bot
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy your bot token

### 2. Configure Bot
```env
TELEGRAM_BOT_TOKEN=your-bot-token-here
```

### 3. Available Commands
```
/start    - Initialize and register
/status   - View task summary
/add      - Create new task
/update   - Update existing task
/search   - Search tasks
/help     - Show help menu
```

## 🗂️ Excel Data Format

Your Excel file should have these columns:

| Column | Description | Required |
|--------|-------------|----------|
| Date | Task creation date | ✅ |
| PO | Purchase Order number | ✅ |
| Catégorie | Task category | ❌ |
| Action | Task description | ✅ |
| Customer | Customer name | ✅ |
| Requester | Person who requested | ✅ |
| Techmac Resp | Responsible person | ✅ |
| Dead line | Task deadline | ❌ |
| Status | Current status | ❌ |
| Note | Additional notes | ❌ |

## 🔧 Development

### Frontend Development
```bash
cd frontend
npm start           # Development server
npm run build       # Production build
npm test           # Run tests
npm run lint       # Code linting
```

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py      # Development server
```

### API Documentation
Visit http://localhost:5000/docs for interactive API documentation.

## 🐳 Docker Deployment

### Development with Docker
```bash
# Build development containers
docker-compose -f docker-compose.dev.yml up --build

# Run specific service
docker-compose up api
```

### Production Deployment
```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Scale services
docker-compose up --scale api=3
```

### Docker Services
- **nginx**: Reverse proxy and SSL termination
- **frontend**: React application
- **api**: Flask backend API
- **db**: PostgreSQL database
- **cache**: Redis cache
- **telegram-bot**: Telegram bot service
- **onedrive-sync**: OneDrive synchronization
- **email-service**: Email notification service
- **monitoring**: Prometheus + Grafana

## 📊 Monitoring & Analytics

### Grafana Dashboards
Access Grafana at http://localhost:3001
- **System Overview**: Server metrics, uptime, resource usage
- **Application Metrics**: API performance, user activity, task analytics
- **Business Intelligence**: Completion rates, team performance, trending

### Prometheus Metrics
- API response times
- Database query performance
- Redis cache hit rates
- Task creation/completion rates
- User session analytics

### Health Checks
```bash
# Application health
curl http://localhost:5000/health

# Database connectivity
curl http://localhost:5000/health/db

# Redis connectivity  
curl http://localhost:5000/health/redis
```

## 🔐 Security

### Authentication
- **JWT tokens** with 1-hour expiration
- **Refresh tokens** with 7-day expiration
- **Azure AD integration** for SSO
- **Role-based access control**

### API Security
- Rate limiting (100 requests/minute)
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CORS configuration

### Data Protection
- Encrypted database connections
- SSL/TLS in production
- Secure cookie handling
- Environment variable protection

## 🤝 User Roles & Permissions

| Role | Permissions |
|------|-------------|
| **Admin** | Full system access, user management, settings |
| **Manager** | Task management, team oversight, reports |
| **User** | Create/edit own tasks, view team tasks |
| **Read-only** | View tasks and reports only |

## 📋 API Endpoints

### Authentication
```http
POST   /auth/login           # User login
POST   /auth/logout          # User logout
POST   /auth/refresh         # Refresh token
GET    /auth/me             # Current user info
```

### Tasks
```http
GET    /api/tasks           # List tasks
POST   /api/tasks           # Create task
GET    /api/tasks/{id}      # Get task details
PUT    /api/tasks/{id}      # Update task
DELETE /api/tasks/{id}      # Delete task
```

### Analytics
```http
GET    /api/analytics/dashboard    # Dashboard metrics
GET    /api/analytics/performance  # Performance data
GET    /api/analytics/reports      # Generate reports
```

## 🔄 OneDrive Synchronization

### Automatic Sync
- **Real-time**: Webhook-based file change detection
- **Periodic**: Scheduled sync every 5 minutes
- **Conflict Resolution**: Timestamp-based or manual review

### Sync Configuration
```python
SYNC_CONFIG = {
    'folder_path': '/Action Plans',
    'file_name': 'Plan_daction.xlsx',
    'sync_interval': 300,  # 5 minutes
    'conflict_resolution': 'timestamp'
}
```

## 📧 Email Notifications

### Notification Types
- ✅ Task assigned
- ⏰ Deadline approaching (3 days before)
- 🚨 Task overdue
- ✅ Task completed
- 📊 Weekly summary reports

### Email Templates
- Modern responsive design
- Corporate branding
- Multi-language support (French/English)
- Actionable buttons

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Error
```bash
# Check PostgreSQL status
sudo systemctl status postgresql
sudo systemctl restart postgresql

# Test connection
psql -h localhost -U actionplan -d actionplan
```

#### Frontend Build Errors
```bash
# Clear cache and reinstall
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

#### Docker Issues
```bash
# View logs
docker-compose logs -f [service-name]

# Restart service
docker-compose restart api

# Clean rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### Microsoft Graph API Errors
```bash
# Test token validity
curl -H "Authorization: Bearer {token}" \
  https://graph.microsoft.com/v1.0/me
```

### Log Locations
- **Application**: `logs/api/app.log`
- **Nginx**: `logs/nginx/access.log`
- **Database**: `logs/postgres/`
- **Sync Service**: `logs/sync/onedrive.log`

## 🔄 Backup & Recovery

### Automated Backups
- **Database**: Daily PostgreSQL dumps
- **Files**: OneDrive versioning + local snapshots
- **Configuration**: Environment variables backup

### Backup Commands
```bash
# Manual database backup
docker-compose exec db pg_dump -U actionplan actionplan > backup_$(date +%Y%m%d).sql

# Restore from backup
docker-compose exec db psql -U actionplan actionplan < backup_20241115.sql
```

## 📈 Performance Optimization

### Database
- Indexed columns for fast queries
- Connection pooling
- Query optimization
- Automated maintenance

### Frontend
- Code splitting
- Lazy loading
- Bundle optimization
- CDN for static assets

### Backend
- Redis caching
- API response compression
- Background task processing
- Load balancing ready

## 🌍 Internationalization

### Supported Languages
- 🇫🇷 French (default)
- 🇺🇸 English
- 🇲🇦 Arabic (planned)

### Adding Languages
1. Add translation files in `frontend/src/locales/`
2. Update language selector component
3. Configure date/time formats

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Code Style
- **Frontend**: ESLint + Prettier
- **Backend**: Black + Flake8
- **TypeScript**: Strict mode enabled
- **Testing**: Jest + React Testing Library

## 📞 Support & Documentation

### Getting Help
1. **Check Documentation**: This README and inline comments
2. **API Reference**: http://localhost:5000/docs
3. **GitHub Issues**: Report bugs and feature requests
4. **Microsoft Docs**: For Graph API integration

### Useful Resources
- [Microsoft Graph API](https://docs.microsoft.com/en-us/graph/)
- [React TypeScript Guide](https://react-typescript-cheatsheet.netlify.app/)
- [Material-UI Documentation](https://mui.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **TechMac Team** for requirements and testing
- **Microsoft Graph API** for seamless Office 365 integration
- **Material-UI** for beautiful React components
- **Flask Community** for excellent backend framework
- **Open Source Contributors** for amazing libraries and tools

---

## 🎯 Quick Commands Reference

```bash
# Setup
./setup.sh                    # Complete automated setup

# Development
./dev-start.sh                # Start development mode
./status.sh                   # Check system status

# Production
./prod-start.sh              # Start production mode
docker-compose logs -f       # View logs
docker-compose down          # Stop all services

# Data Management
python scripts/import_excel.py data/Plan_daction.xlsx  # Import Excel data
docker-compose exec db pg_dump -U actionplan actionplan > backup.sql  # Backup database

# Monitoring
curl http://localhost:5000/health          # Health check
curl http://localhost:5000/metrics         # Prometheus metrics
```

**Happy Task Managing! 🚀**