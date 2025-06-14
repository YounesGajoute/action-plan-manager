#!/bin/bash
# ===================================================================
# status.sh - System Status Check Script
# ===================================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Icons
CHECK="✅"
CROSS="❌"
WARNING="⚠️"
INFO="ℹ️"
ROCKET="🚀"
DATABASE="🗄️"
GLOBE="🌐"
GEAR="⚙️"

print_header() {
    echo -e "${BLUE}"
    echo "================================================================="
    echo "$1"
    echo "================================================================="
    echo -e "${NC}"
}

print_service_status() {
    local service=$1
    local status=$2
    local port=$3
    local url=$4
    
    if [ "$status" = "running" ]; then
        echo -e "${GREEN}${CHECK} ${service}${NC} - Running"
        if [ ! -z "$port" ]; then
            echo -e "    ${CYAN}Port:${NC} $port"
        fi
        if [ ! -z "$url" ]; then
            echo -e "    ${CYAN}URL:${NC} $url"
        fi
    elif [ "$status" = "stopped" ]; then
        echo -e "${RED}${CROSS} ${service}${NC} - Stopped"
    elif [ "$status" = "unhealthy" ]; then
        echo -e "${YELLOW}${WARNING} ${service}${NC} - Unhealthy"
    else
        echo -e "${YELLOW}${WARNING} ${service}${NC} - $status"
    fi
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}${CROSS} Docker is not installed${NC}"
        return 1
    fi
    
    if ! docker info &> /dev/null; then
        echo -e "${RED}${CROSS} Docker is not running${NC}"
        return 1
    fi
    
    echo -e "${GREEN}${CHECK} Docker is running${NC}"
    return 0
}

check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}${CROSS} Docker Compose is not installed${NC}"
        return 1
    fi
    
    echo -e "${GREEN}${CHECK} Docker Compose is available${NC}"
    return 0
}

get_container_status() {
    local container_name=$1
    local status=$(docker-compose ps -q $container_name 2>/dev/null)
    
    if [ -z "$status" ]; then
        echo "stopped"
        return
    fi
    
    local health=$(docker inspect --format='{{.State.Health.Status}}' $status 2>/dev/null)
    local state=$(docker inspect --format='{{.State.Status}}' $status 2>/dev/null)
    
    if [ "$health" = "healthy" ]; then
        echo "running"
    elif [ "$health" = "unhealthy" ]; then
        echo "unhealthy"
    elif [ "$state" = "running" ]; then
        echo "running"
    elif [ "$state" = "exited" ]; then
        echo "stopped"
    else
        echo "$state"
    fi
}

check_service_health() {
    local service=$1
    local url=$2
    local timeout=${3:-5}
    
    if curl -s --max-time $timeout "$url" > /dev/null 2>&1; then
        echo "healthy"
    else
        echo "unhealthy"
    fi
}

check_database_connection() {
    local status=$(docker-compose exec -T db pg_isready -U actionplan 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "healthy"
    else
        echo "unhealthy"
    fi
}

check_redis_connection() {
    local status=$(docker-compose exec -T cache redis-cli ping 2>/dev/null)
    if [ "$status" = "PONG" ]; then
        echo "healthy"
    else
        echo "unhealthy"
    fi
}

show_container_stats() {
    print_header "${GEAR} Container Resource Usage"
    
    if docker-compose ps -q > /dev/null 2>&1; then
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" $(docker-compose ps -q 2>/dev/null) 2>/dev/null || echo "No containers running"
    else
        echo "No containers found"
    fi
}

show_disk_usage() {
    print_header "${DATABASE} Disk Usage"
    
    echo -e "${CYAN}Project Directory:${NC}"
    du -sh . 2>/dev/null || echo "Unable to calculate"
    
    echo -e "\n${CYAN}Docker Volumes:${NC}"
    docker system df 2>/dev/null || echo "Unable to get Docker disk usage"
    
    echo -e "\n${CYAN}Log Files:${NC}"
    if [ -d "logs" ]; then
        du -sh logs/* 2>/dev/null || echo "No log files found"
    else
        echo "Logs directory not found"
    fi
}

show_recent_logs() {
    print_header "${INFO} Recent Logs (Last 10 lines)"
    
    services=("api" "frontend" "db" "cache")
    
    for service in "${services[@]}"; do
        echo -e "\n${YELLOW}=== $service ===${NC}"
        docker-compose logs --tail=5 $service 2>/dev/null || echo "Service not found or no logs"
    done
}

show_environment_info() {
    print_header "${GEAR} Environment Information"
    
    if [ -f ".env" ]; then
        echo -e "${GREEN}${CHECK} .env file exists${NC}"
        
        # Show non-sensitive environment variables
        echo -e "\n${CYAN}Configuration:${NC}"
        grep -E "^(FLASK_ENV|NODE_ENV|ENABLE_|POSTGRES_DB|POSTGRES_USER)" .env 2>/dev/null | while read line; do
            echo "  $line"
        done
    else
        echo -e "${RED}${CROSS} .env file not found${NC}"
    fi
    
    echo -e "\n${CYAN}System Information:${NC}"
    echo "  OS: $(uname -s)"
    echo "  Architecture: $(uname -m)"
    
    if command -v docker &> /dev/null; then
        echo "  Docker: $(docker --version | cut -d' ' -f3 | cut -d',' -f1)"
    fi
    
    if command -v docker-compose &> /dev/null; then
        echo "  Docker Compose: $(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)"
    fi
}

show_service_urls() {
    print_header "${GLOBE} Service URLs"
    
    echo -e "${CYAN}Application Services:${NC}"
    echo "  Frontend:     http://localhost:3000"
    echo "  API:          http://localhost:5000"
    echo "  API Health:   http://localhost:5000/health"
    echo "  API Docs:     http://localhost:5000/docs"
    
    echo -e "\n${CYAN}Development Services:${NC}"
    echo "  PostgreSQL:   localhost:5432"
    echo "  Redis:        localhost:6379"
    
    echo -e "\n${CYAN}Monitoring (if enabled):${NC}"
    echo "  Grafana:      http://localhost:3001"
    echo "  Prometheus:   http://localhost:9090"
    echo "  Kibana:       http://localhost:5601"
}

main_status_check() {
    print_header "${ROCKET} Action Plan Management System - Status"
    
    # Check prerequisites
    echo -e "${PURPLE}Prerequisites:${NC}"
    check_docker
    check_docker_compose
    
    echo ""
    
    # Check core services
    print_header "${DATABASE} Core Services"
    
    # Database
    db_status=$(get_container_status "db")
    if [ "$db_status" = "running" ]; then
        db_health=$(check_database_connection)
        if [ "$db_health" = "healthy" ]; then
            print_service_status "PostgreSQL Database" "running" "5432" "localhost:5432"
        else
            print_service_status "PostgreSQL Database" "unhealthy" "5432" "localhost:5432"
        fi
    else
        print_service_status "PostgreSQL Database" "$db_status"
    fi
    
    # Redis Cache
    cache_status=$(get_container_status "cache")
    if [ "$cache_status" = "running" ]; then
        cache_health=$(check_redis_connection)
        if [ "$cache_health" = "healthy" ]; then
            print_service_status "Redis Cache" "running" "6379" "localhost:6379"
        else
            print_service_status "Redis Cache" "unhealthy" "6379" "localhost:6379"
        fi
    else
        print_service_status "Redis Cache" "$cache_status"
    fi
    
    # API
    api_status=$(get_container_status "api")
    if [ "$api_status" = "running" ]; then
        api_health=$(check_service_health "API" "http://localhost:5000/health")
        if [ "$api_health" = "healthy" ]; then
            print_service_status "Backend API" "running" "5000" "http://localhost:5000"
        else
            print_service_status "Backend API" "unhealthy" "5000" "http://localhost:5000"
        fi
    else
        print_service_status "Backend API" "$api_status"
    fi
    
    # Frontend
    frontend_status=$(get_container_status "frontend")
    if [ "$frontend_status" = "running" ]; then
        frontend_health=$(check_service_health "Frontend" "http://localhost:3000")
        if [ "$frontend_health" = "healthy" ]; then
            print_service_status "Frontend" "running" "3000" "http://localhost:3000"
        else
            print_service_status "Frontend" "unhealthy" "3000" "http://localhost:3000"
        fi
    else
        print_service_status "Frontend" "$frontend_status"
    fi
    
    echo ""
    
    # Check optional services
    print_header "${GEAR} Optional Services"
    
    # Nginx
    nginx_status=$(get_container_status "nginx")
    print_service_status "Nginx Proxy" "$nginx_status" "80,443" "http://localhost"
    
    # OneDrive Sync
    onedrive_status=$(get_container_status "onedrive-sync")
    print_service_status "OneDrive Sync" "$onedrive_status"
    
    # Email Service
    email_status=$(get_container_status "email-service")
    print_service_status "Email Service" "$email_status"
    
    # Telegram Bot
    telegram_status=$(get_container_status "telegram-bot")
    print_service_status "Telegram Bot" "$telegram_status"
    
    # Monitoring
    prometheus_status=$(get_container_status "prometheus")
    print_service_status "Prometheus" "$prometheus_status" "9090" "http://localhost:9090"
    
    grafana_status=$(get_container_status "grafana")
    print_service_status "Grafana" "$grafana_status" "3001" "http://localhost:3001"
}

# Handle command line arguments
case "$1" in
    --detailed|-d)
        main_status_check
        show_container_stats
        show_environment_info
        show_service_urls
        ;;
    --logs|-l)
        main_status_check
        show_recent_logs
        ;;
    --disk|-disk)
        main_status_check
        show_disk_usage
        ;;
    --urls|-u)
        show_service_urls
        ;;
    --help|-h)
        echo "System Status Check Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --detailed, -d    Show detailed status with resource usage"
        echo "  --logs, -l        Show status with recent logs"
        echo "  --disk            Show status with disk usage"
        echo "  --urls, -u        Show service URLs only"
        echo "  --help, -h        Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                Basic status check"
        echo "  $0 --detailed     Detailed status with system info"
        echo "  $0 --logs         Status with recent logs"
        echo ""
        ;;
    *)
        main_status_check
        ;;
esac