#!/bin/bash
# API Protection Setup and Testing Script

echo "🔒 Setting up API Protection for EnerVibe API..."

# Install new requirements
echo "📦 Installing protection libraries..."
pip install -r requirements.txt

# Create blocked IPs file if it doesn't exist
if [ ! -f "blocked_ips.json" ]; then
    echo "📋 Creating blocked IPs configuration..."
    cat > blocked_ips.json << EOL
{
  "ips": [],
  "ranges": [
    "127.0.0.1/32"
  ],
  "updated": "$(date -Iseconds)"
}
EOL
fi

# Copy environment variables
if [ ! -f ".env" ]; then
    echo "⚙️ Creating environment configuration..."
    cp .env.example .env
    echo "Please edit .env file with your specific configuration"
fi

echo "🧪 Running API protection tests..."

# Test 1: Health check
echo "Test 1: Health check..."
curl -s "http://localhost:8000/healthz" | jq .

# Test 2: Rate limiting (should work initially)
echo "Test 2: Normal request..."
curl -s "http://localhost:8000/run?key=E1A77476-19DE-4E0C-AA54-53F7047EA56E&q=8394f36d-2c9c-4871-ab8a-5489175e32e4&demo=true" | jq .

# Test 3: Rate limiting (rapid requests)
echo "Test 3: Testing rate limiting with rapid requests..."
for i in {1..15}; do
    echo "Request $i:"
    curl -s "http://localhost:8000/run?key=E1A77476-19DE-4E0C-AA54-53F7047EA56E&q=8394f36d-2c9c-4871-ab8a-5489175e32e4&demo=true" | jq .
done

echo "✅ API Protection setup complete!"
echo ""
echo "📊 Monitoring:"
echo "- Check api_security.log for security events"
echo "- Use /usage endpoint to check quota usage"
echo "- Monitor blocked_ips.json for auto-blocked IPs"
echo ""
echo "🔧 Configuration files:"
echo "- .env - Environment variables"
echo "- blocked_ips.json - IP blocking configuration"
echo "- api_security.log - Security event log"
