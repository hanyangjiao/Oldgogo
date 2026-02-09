#!/bin/bash
# Install ngrok as a systemd service for permanent public access

set -e

if [ -z "$1" ]; then
    echo "Usage: ./install_ngrok_service.sh YOUR_NGROK_AUTHTOKEN [YOUR_STATIC_DOMAIN]"
    echo ""
    echo "Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo ""
    echo "Examples:"
    echo "  ./install_ngrok_service.sh 2abc123xyz                    # Free random URL"
    echo "  ./install_ngrok_service.sh 2abc123xyz myapp.ngrok.app    # Paid static domain"
    exit 1
fi

AUTHTOKEN=$1
STATIC_DOMAIN=${2:-}

echo "Installing ngrok..."
if ! command -v ngrok &> /dev/null; then
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
    sudo apt update && sudo apt install ngrok -y
fi

echo "Configuring ngrok authtoken..."
ngrok config add-authtoken $AUTHTOKEN

echo "Creating ngrok systemd service..."

if [ -z "$STATIC_DOMAIN" ]; then
    # Free plan - random URL
    EXEC_START="ngrok http 8000 --log stdout"
else
    # Paid plan - static domain
    EXEC_START="ngrok http 8000 --domain $STATIC_DOMAIN --log stdout"
fi

cat > /tmp/ngrok-oldgogo.service << EOF
[Unit]
Description=Ngrok Tunnel for Oldgogo UI
After=network.target oldgogo-ui.service
Requires=oldgogo-ui.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
ExecStart=/usr/local/bin/ngrok http 8000 --log stdout
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "Installing ngrok service..."
sudo cp /tmp/ngrok-oldgogo.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ngrok-oldgogo
sudo systemctl start ngrok-oldgogo

sleep 3

echo ""
echo "✓ Ngrok service installed and started!"
echo ""
echo "Getting your public URL..."
sleep 2

# Try to get the public URL from ngrok API
PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | cut -d'"' -f4 | head -1)

if [ -n "$PUBLIC_URL" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo "  Your Oldgogo UI is now publicly accessible at:"
    echo "  $PUBLIC_URL/src/app/ui/"
    echo "═══════════════════════════════════════════════════════"
    echo ""
else
    echo "Couldn't auto-detect URL. Check manually:"
    echo "  curl http://localhost:4040/api/tunnels | jq"
fi

echo ""
echo "Useful commands:"
echo "  sudo systemctl status ngrok-oldgogo    # Check status"
echo "  sudo journalctl -u ngrok-oldgogo -f    # View logs & URL"
echo "  curl http://localhost:4040/api/tunnels # Get current URL"
