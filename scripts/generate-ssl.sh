#!/bin/bash
# scripts/generate-ssl.sh

set -e

DOMAIN="actionplan.techmac.ma"
SSL_DIR="/etc/ssl/certs"
NGINX_DIR="/etc/nginx"

echo "🔐 Generating SSL certificates for $DOMAIN"

# Create directories
mkdir -p $SSL_DIR
mkdir -p $NGINX_DIR

# Generate DH parameters
if [ ! -f "$NGINX_DIR/dhparam.pem" ]; then
    echo "📝 Generating DH parameters..."
    openssl dhparam -out $NGINX_DIR/dhparam.pem 2048
fi

# Generate private key
echo "🔑 Generating private key..."
openssl genrsa -out $SSL_DIR/actionplan.key 2048

# Generate certificate signing request
echo "📄 Generating CSR..."
openssl req -new -key $SSL_DIR/actionplan.key -out $SSL_DIR/actionplan.csr -subj "/C=MA/ST=Tanger-Tetouan-Al Hoceima/L=Tangier/O=Techmac/CN=$DOMAIN"

# Generate self-signed certificate (for development)
echo "📜 Generating self-signed certificate..."
openssl x509 -req -days 365 -in $SSL_DIR/actionplan.csr -signkey $SSL_DIR/actionplan.key -out $SSL_DIR/actionplan.crt

echo "✅ SSL certificates generated successfully!"
echo "📍 Certificate: $SSL_DIR/actionplan.crt"
echo "📍 Private key: $SSL_DIR/actionplan.key"
echo "📍 DH params: $NGINX_DIR/dhparam.pem"