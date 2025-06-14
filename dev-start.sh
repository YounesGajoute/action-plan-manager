#!/bin/bash
# ===================================================================
# dev-start.sh - Development Environment Start Script
# ===================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Check if .env exists
check_environment() {
    if [ ! -f ".env" ]; then
        print_error ".env file not found"
        print_status "Please run ./setup.sh first or copy .env.example to .env"
        exit 1
    fi
}

# Start development environment
start_dev_environment() {
    print_header "Starting Development Environment"
    
    # Load environment variables
    export $(cat .env | grep -v '^#' | xargs)
    
    # Create necessary directories
    mkdir -p logs/{api,nginx,frontend,postgres,redis}
    mkdir -p data/{imports,exports,cache}
    mkdir -p uploads
    
    print_status "Starting core services (Database, Cache)..."
    docker-compose up -d db cache
    
    # Wait for database
    print_status "Waiting for database to be ready..."
    until docker-compose exec -T db pg_isready -U ${POSTGRES_USER:-actionplan} >/dev/null 2>&1; do
        sleep 1
        echo -n "."
    done
    echo ""
    print_success "Database is ready"
    
    # Wait for Redis
    print_status "Waiting for Redis to be ready..."
    until docker-compose exec -T cache redis-cli ping >/dev/null 2>&1; do
        sleep 1
        echo -n "."
    done
    echo ""
    print_success "Redis is ready"
    
    # Start API
    print_status "Starting API service..."
    docker-compose up -d api
    
    # Wait for API
    print_status "Waiting for API to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:5000/health >/dev/null 2>&1; then
            print_success "API is ready"
            break
        else
            if [ $i -eq 30 ]; then
                print_error "API failed to start"
                docker-compose logs api
                exit 1
            fi
            sleep 2
        fi
    done
    
    # Start Frontend
    print_status "Starting Frontend service..."
    docker-compose up -d frontend
    
    # Wait for Frontend
    print_status "Waiting for Frontend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:3000 >/dev/null 2>&1; then
            print_success "Frontend is ready"
            break
        else
            if [ $i -eq 30 ]; then
                print_error "Frontend failed to start"
                docker-compose logs frontend
                exit 1
            fi
            sleep 2
        fi
    done
}

# Show development URLs and information
show_dev_info() {
    print_header "Development Environment Ready!"
    
    echo -e "${GREEN}🚀 All services are running!${NC}"
    echo ""
    
    echo -e "${BLUE}📱 Application URLs:${NC}"
    echo "  Frontend:     http://localhost:3000"
    echo "  API:          http://localhost:5000"
    echo "  API Health:   http://localhost:5000/health"
    echo "  API Docs:     http://localhost:5000/docs"
    echo ""
    
    echo -e "${BLUE}🗄️ Database Access:${NC}"
    echo "  PostgreSQL:   localhost:5432"
    echo "  Database:     ${POSTGRES_DB:-actionplan}"
    echo "  Username:     ${POSTGRES_USER:-actionplan}"
    echo "  Redis:        localhost:6379"
    echo ""
    
    echo -e "${BLUE}🔧 Development Commands:${NC}"
    echo "  View logs:    docker-compose logs -f [service]"
    echo "  Stop all:     docker-compose down"
    echo "  Restart:      docker-compose restart [service]"
    echo "  Shell:        docker-compose exec [service] /bin/bash"
    echo ""
    
    echo -e "${BLUE}📊 Import Excel Data:${NC}"
    echo "  Place your Excel file in: data/Plan_daction.xlsx"
    echo "  Import command: docker-compose exec api python scripts/import_excel.py /app/data/Plan_daction.xlsx"
    echo ""
    
    echo -e "${BLUE}⚙️ Configuration:${NC}"
    echo "  Environment:  .env file"
    echo "  Logs:         logs/ directory"
    echo "  Data:         data/ directory"
    echo "  Uploads:      uploads/ directory"
    echo ""
    
    echo -e "${YELLOW}⚠️ Next Steps:${NC}"
    echo "1. Configure Microsoft 365 credentials in .env"
    echo "2. Import your Excel data"
    echo "3. Open http://localhost:3000 in your browser"
    echo "4. Login with Microsoft 365"
    echo ""
    
    echo -e "${GREEN}Happy coding! 💻${NC}"
}

# Check if services are already running
check_existing_services() {
    if docker-compose ps | grep -q "Up"; then
        print_warning "Some services are already running"
        read -p "Do you want to restart them? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Stopping existing services..."
            docker-compose down
        else
            print_status "Keeping existing services running"
            show_dev_info
            exit 0
        fi
    fi
}

# Monitor services (optional)
monitor_services() {
    if [ "$1" = "--monitor" ] || [ "$1" = "-m" ]; then
        print_header "Monitoring Services"
        print_status "Press Ctrl+C to stop monitoring"
        docker-compose logs -f
    fi
}

# Main function
main() {
    print_header "Action Plan Management - Development Start"
    
    # Check prerequisites
    check_environment
    
    # Check for existing services
    check_existing_services
    
    # Start development environment
    start_dev_environment
    
    # Show information
    show_dev_info
    
    # Monitor if requested
    monitor_services "$1"
}

# Handle script arguments
case "$1" in
    --help|-h)
        echo "Development Start Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --monitor, -m    Start and monitor services (follow logs)"
        echo "  --help, -h       Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0               Start development environment"
        echo "  $0 --monitor     Start and monitor logs"
        echo ""
        exit 0
        ;;
    *)
        main "$1"
        ;;
esac