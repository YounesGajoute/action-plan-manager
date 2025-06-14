#!/bin/bash
# scripts/validate-nginx.sh

set -e

echo "🔍 Validating Nginx configuration..."

# Test nginx configuration syntax
if nginx -t 2>/dev/null; then
    echo "✅ Nginx configuration syntax is valid"
else
    echo "❌ Nginx configuration syntax errors found:"
    nginx -t
    exit 1
fi

# Check if all required files exist
REQUIRED_FILES=(
    "/etc/nginx/nginx.conf"
    "/etc/nginx/conf.d/actionplan.conf"
    "/etc/nginx/conf.d/ssl.conf"
    "/etc/nginx/conf.d/security.conf"
    "/etc/ssl/certs/actionplan.crt"
    "/etc/ssl/certs/actionplan.key"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file is missing"
        exit 1
    fi
done

echo "🎉 All Nginx configuration files are valid and ready!"