#!/bin/bash
# ===================================================================
# setup.sh - Automated Setup Script for Action Plan Management System
# ===================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}"
    echo "================================================================="
    echo "$1"
    echo "================================================================="
    echo -e "${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_warning "This script should not be run as root"
        print_status "Please run as a regular user with sudo privileges"
        exit 1
    fi
}

# Check system requirements
check_requirements() {
    print_header "Checking System Requirements"
    
    # Check OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_success "Operating System: Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        print_success "Operating System: macOS"
    else
        print_error "Unsupported operating system: $OSTYPE"
        exit 1
    fi
    
    # Check Docker
    if command -v docker &> /dev/null; then
        print_success "Docker is installed: $(docker --version)"
    else
        print_error "Docker is not installed"
        print_status "Please install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose is installed: $(docker-compose --version)"
    else
        print_error "Docker Compose is not installed"
        print_status "Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check Node.js (for development)
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js is installed: $NODE_VERSION"
        
        # Check if version is 18 or higher
        MAJOR_VERSION=$(echo $NODE_VERSION | cut -d'.' -f1 | sed 's/v//')
        if [ "$MAJOR_VERSION" -ge 18 ]; then
            print_success "Node.js version is compatible (>=18)"
        else
            print_warning "Node.js version should be 18 or higher. Current: $NODE_VERSION"
        fi
    else
        print_warning "Node.js is not installed (required for development)"
        print_status "You can install it later for development: https://nodejs.org/"
    fi
    
    # Check Python (for development)
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_success "Python is installed: $PYTHON_VERSION"
    else
        print_warning "Python 3 is not installed (required for development)"
    fi
    
    # Check available disk space (at least 2GB)
    AVAILABLE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -ge 2 ]; then
        print_success "Sufficient disk space available: ${AVAILABLE_SPACE}GB"
    else
        print_warning "Low disk space. Available: ${AVAILABLE_SPACE}GB. Recommended: 2GB+"
    fi
}

# Create directory structure
create_directories() {
    print_header "Creating Directory Structure"
    
    directories=(
        "data"
        "data/imports"
        "data/exports"
        "data/templates"
        "data/cache"
        "backups"
        "backups/database"
        "backups/files"
        "backups/config"
        "logs"
        "logs/api"
        "logs/nginx"
        "logs/sync"
        "logs/telegram"
        "logs/email"
        "uploads"
        "ssl"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "Created directory: $dir"
        else
            print_status "Directory already exists: $dir"
        fi
    done
    
    # Set proper permissions
    chmod 755 logs uploads data backups
    chmod 700 ssl  # SSL certificates should be more restricted
}

# Setup environment files
setup_environment() {
    print_header "Setting Up Environment Configuration"
    
    # Check if .env already exists
    if [ -f ".env" ]; then
        print_warning ".env file already exists"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Keeping existing .env file"
            return
        fi
    fi
    
    # Create .env from example
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "Created .env from .env.example"
    else
        print_warning ".env.example not found, creating basic .env"
        create_basic_env
    fi
    
    # Generate secure keys
    print_status "Generating secure keys..."
    
    # Generate JWT secret
    JWT_SECRET=$(openssl rand -hex 32)
    sed -i.bak "s/your_jwt_secret_key_here_make_it_very_long_and_random/$JWT_SECRET/" .env
    
    # Generate session secret
    SESSION_SECRET=$(openssl rand -hex 32)
    sed -i.bak "s/your_session_secret_key_here/$SESSION_SECRET/" .env
    
    # Generate encryption key
    ENCRYPTION_KEY=$(openssl rand -hex 32)
    sed -i.bak "s/your_encryption_key_here/$ENCRYPTION_KEY/" .env
    
    # Clean up backup files
    rm -f .env.bak
    
    print_success "Generated secure keys"
    print_warning "Please edit .env and configure your Microsoft 365 credentials"
}

create_basic_env() {
    cat > .env << 'EOF'
# Basic Environment Configuration
FLASK_ENV=development
NODE_ENV=development
DEBUG=true

# Database
DATABASE_URL=postgresql://actionplan:secure_password@db:5432/actionplan
REDIS_URL=redis://cache:6379

# Security (generated during setup)
JWT_SECRET=generated_during_setup
SESSION_SECRET=generated_during_setup
ENCRYPTION_KEY=generated_during_setup

# Microsoft 365 Integration (REQUIRED - Update these)
MS_TENANT_ID=your-azure-tenant-id
MS_CLIENT_ID=your-azure-client-id
MS_CLIENT_SECRET=your-azure-client-secret

# Email Configuration
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@yourdomain.com
SMTP_PASSWORD=your-email-password

# Features
ENABLE_ONEDRIVE_SYNC=true
ENABLE_EMAIL_NOTIFICATIONS=true
ENABLE_TELEGRAM_BOT=false

# OneDrive
ONEDRIVE_FOLDER_PATH=/Action Plans
ONEDRIVE_FILE_NAME=Plan_daction.xlsx
SYNC_INTERVAL=300

# URLs
REACT_APP_API_URL=http://localhost:5000
REACT_APP_WS_URL=ws://localhost:5000
EOF
}

# Initialize database
init_database() {
    print_header "Initializing Database"
    
    # Start database container
    print_status "Starting PostgreSQL container..."
    docker-compose up -d db
    
    # Wait for database to be ready
    print_status "Waiting for database to be ready..."
    sleep 10
    
    # Run database migrations
    print_status "Running database migrations..."
    docker-compose exec -T db psql -U actionplan -d actionplan -c "SELECT 1;" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        print_success "Database is ready"
    else
        print_error "Database connection failed"
        print_status "Checking database logs..."
        docker-compose logs db
        exit 1
    fi
}

# Setup Excel data
setup_excel_data() {
    print_header "Setting Up Excel Data"
    
    # Check if Excel file exists
    EXCEL_FILE="data/Plan_daction.xlsx"
    
    if [ -f "Plan daction.xlsx" ]; then
        print_status "Found Excel file in current directory"
        mv "Plan daction.xlsx" "$EXCEL_FILE"
        print_success "Moved Excel file to data directory"
    elif [ -f "$EXCEL_FILE" ]; then
        print_success "Excel file already exists in data directory"
    else
        print_warning "Excel file not found"
        print_status "You can add your Excel file later to: $EXCEL_FILE"
        
        # Create sample Excel file
        print_status "Creating sample Excel template..."
        # This would be created by the Python script when containers are running
    fi
}

# Build and start services
start_services() {
    print_header "Building and Starting Services"
    
    # Build containers
    print_status "Building Docker containers..."
    docker-compose build --no-cache
    
    if [ $? -ne 0 ]; then
        print_error "Failed to build containers"
        exit 1
    fi
    
    print_success "Containers built successfully"
    
    # Start all services
    print_status "Starting all services..."
    docker-compose up -d
    
    if [ $? -ne 0 ]; then
        print_error "Failed to start services"
        exit 1
    fi
    
    print_success "Services started successfully"
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 15
    
    # Check service health
    check_service_health
}

# Check service health
check_service_health() {
    print_header "Checking Service Health"
    
    # Check API health
    print_status "Checking API health..."
    for i in {1..30}; do
        if curl -s http://localhost:5000/health > /dev/null 2>&1; then
            print_success "API is healthy"
            break
        else
            if [ $i -eq 30 ]; then
                print_error "API health check failed"
                docker-compose logs api
                exit 1
            fi
            print_status "Waiting for API... ($i/30)"
            sleep 2
        fi
    done
    
    # Check Frontend
    print_status "Checking Frontend..."
    for i in {1..30}; do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            print_success "Frontend is accessible"
            break
        else
            if [ $i -eq 30 ]; then
                print_error "Frontend health check failed"
                docker-compose logs frontend
                exit 1
            fi
            print_status "Waiting for Frontend... ($i/30)"
            sleep 2
        fi
    done
    
    # Check Database
    print_status "Checking Database..."
    if docker-compose exec -T db pg_isready -U actionplan > /dev/null 2>&1; then
        print_success "Database is ready"
    else
        print_error "Database is not ready"
        docker-compose logs db
        exit 1
    fi
    
    # Check Redis
    print_status "Checking Redis..."
    if docker-compose exec -T cache redis-cli ping > /dev/null 2>&1; then
        print_success "Redis is ready"
    else
        print_error "Redis is not ready"
        docker-compose logs cache
        exit 1
    fi
}

# Import Excel data
import_excel_data() {
    print_header "Importing Excel Data"
    
    EXCEL_FILE="data/Plan_daction.xlsx"
    
    if [ -f "$EXCEL_FILE" ]; then
        print_status "Importing Excel data..."
        docker-compose exec -T api python scripts/import_excel.py /app/data/Plan_daction.xlsx
        
        if [ $? -eq 0 ]; then
            print_success "Excel data imported successfully"
        else
            print_warning "Excel import failed, but you can import later"
            print_status "Use: docker-compose exec api python scripts/import_excel.py /app/data/Plan_daction.xlsx"
        fi
    else
        print_warning "No Excel file to import"
        print_status "You can import later by placing your file in data/Plan_daction.xlsx"
        print_status "Then run: docker-compose exec api python scripts/import_excel.py /app/data/Plan_daction.xlsx"
    fi
}

# Create admin user
create_admin_user() {
    print_header "Creating Admin User"
    
    print_status "Creating default admin user..."
    docker-compose exec -T api python -c "
from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    admin_user = User.query.filter_by(email='admin@techmac.ma').first()
    if not admin_user:
        admin_user = User(
            email='admin@techmac.ma',
            name='Administrator',
            roles=['admin', 'manager', 'user'],
            department='IT',
            position='System Administrator'
        )
        db.session.add(admin_user)
        db.session.commit()
        print('Admin user created successfully')
    else:
        print('Admin user already exists')
"
    
    if [ $? -eq 0 ]; then
        print_success "Admin user setup completed"
    else
        print_warning "Admin user creation failed, but you can create one later"
    fi
}

# Show final status and instructions
show_final_status() {
    print_header "Setup Complete!"
    
    echo -e "${GREEN}"
    echo "🎉 Action Plan Management System has been set up successfully!"
    echo -e "${NC}"
    
    echo -e "${BLUE}Access URLs:${NC}"
    echo "  Frontend:  http://localhost:3000"
    echo "  API:       http://localhost:5000"
    echo "  Health:    http://localhost:5000/health"
    echo "  Grafana:   http://localhost:3001 (admin/admin)"
    echo ""
    
    echo -e "${BLUE}Default Admin User:${NC}"
    echo "  Email:     admin@techmac.ma"
    echo "  Login:     Use Microsoft 365 authentication"
    echo ""
    
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. 📝 Configure Microsoft 365 credentials in .env file"
    echo "2. 📊 Place your Excel file in data/Plan_daction.xlsx"
    echo "3. 📤 Import Excel data: docker-compose exec api python scripts/import_excel.py /app/data/Plan_daction.xlsx"
    echo "4. 🌐 Open http://localhost:3000 in your browser"
    echo "5. 🔐 Login with your Microsoft 365 account"
    echo ""
    
    echo -e "${BLUE}Management Commands:${NC}"
    echo "  Start:     ./dev-start.sh    or    docker-compose up -d"
    echo "  Stop:      docker-compose down"
    echo "  Status:    ./status.sh"
    echo "  Logs:      docker-compose logs -f [service-name]"
    echo "  Backup:    docker-compose exec api python scripts/backup_database.py"
    echo ""
    
    echo -e "${YELLOW}Important Notes:${NC}"
    echo "• Edit .env file to configure Microsoft 365 integration"
    echo "• The system uses Microsoft 365 for authentication"
    echo "• OneDrive sync requires proper Microsoft Graph API permissions"
    echo "• Email notifications use Office 365 SMTP by default"
    echo ""
    
    echo -e "${BLUE}Troubleshooting:${NC}"
    echo "• Check logs: docker-compose logs -f"
    echo "• Restart services: docker-compose restart"
    echo "• Reset database: docker-compose down -v && docker-compose up -d"
    echo "• View documentation: cat README.md"
    echo ""
    
    echo -e "${GREEN}Happy task managing! 🚀${NC}"
}

# Main setup function
main() {
    print_header "Action Plan Management System - Automated Setup"
    
    echo "This script will set up the complete Action Plan Management System"
    echo "including Docker containers, database, and initial configuration."
    echo ""
    
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Setup cancelled by user"
        exit 0
    fi
    
    # Run setup steps
    check_root
    check_requirements
    create_directories
    setup_environment
    setup_excel_data
    init_database
    start_services
    import_excel_data
    create_admin_user
    show_final_status
}

# Run main function
main "$@"