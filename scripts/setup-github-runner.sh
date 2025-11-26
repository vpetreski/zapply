#!/bin/bash
# GitHub Actions Self-Hosted Runner Setup for Synology NAS
# Run this script on your NAS to install and configure the runner

set -e

echo "🤖 GitHub Actions Self-Hosted Runner Setup"
echo "==========================================="
echo ""

# Configuration
RUNNER_NAME="zapply-nas-runner"
RUNNER_WORK_DIR="/volume1/docker/zapply/runner-work"
RUNNER_DIR="/volume1/docker/zapply/github-runner"

# Check if running on NAS
if [ ! -d "/volume1/docker" ]; then
    echo "❌ Error: This script must be run on a Synology NAS"
    echo "   /volume1/docker directory not found"
    exit 1
fi

echo "📋 Step 1: Prerequisites"
echo "========================"
echo ""
echo "Before proceeding, make sure you have:"
echo "  1. Docker installed on your NAS (Container Manager package)"
echo "  2. A GitHub Personal Access Token (PAT) or repository admin access"
echo "  3. The runner registration token from GitHub"
echo ""
echo "To get the registration token:"
echo "  1. Go to: https://github.com/vpetreski/zapply/settings/actions/runners/new"
echo "  2. Copy the token from the 'Configure' section"
echo ""
read -p "Do you have the registration token? (yes/no): " has_token

if [ "$has_token" != "yes" ]; then
    echo ""
    echo "Please get the registration token first, then run this script again."
    echo "Run this command to get it:"
    echo "  gh api -X POST repos/vpetreski/zapply/actions/runners/registration-token --jq .token"
    exit 0
fi

echo ""
read -p "Enter your GitHub runner registration token: " RUNNER_TOKEN

if [ -z "$RUNNER_TOKEN" ]; then
    echo "❌ Error: Registration token cannot be empty"
    exit 1
fi

echo ""
echo "📦 Step 2: Creating directories"
echo "================================"
mkdir -p "$RUNNER_DIR"
mkdir -p "$RUNNER_WORK_DIR"
cd "$RUNNER_DIR"

echo "✅ Directories created:"
echo "   Runner: $RUNNER_DIR"
echo "   Work: $RUNNER_WORK_DIR"
echo ""

echo "📥 Step 3: Downloading GitHub Actions Runner"
echo "=============================================="
RUNNER_VERSION="2.321.0"  # Latest as of 2025
RUNNER_URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz"

echo "Downloading runner v${RUNNER_VERSION}..."
curl -o actions-runner-linux-x64.tar.gz -L "$RUNNER_URL"

echo "Extracting..."
tar xzf ./actions-runner-linux-x64.tar.gz
rm actions-runner-linux-x64.tar.gz

echo "✅ Runner downloaded and extracted"
echo ""

echo "⚙️  Step 4: Configuring runner"
echo "=============================="
./config.sh \
    --url https://github.com/vpetreski/zapply \
    --token "$RUNNER_TOKEN" \
    --name "$RUNNER_NAME" \
    --work "$RUNNER_WORK_DIR" \
    --labels self-hosted,linux,x64,synology,nas \
    --unattended \
    --replace

echo ""
echo "✅ Runner configured successfully"
echo ""

echo "🚀 Step 5: Installing runner as a service"
echo "=========================================="
echo ""
echo "Creating systemd service file..."

# For Synology, we'll create a simple startup script instead of systemd
cat > /volume1/docker/zapply/start-runner.sh << 'STARTSCRIPT'
#!/bin/bash
cd /volume1/docker/zapply/github-runner
nohup ./run.sh > /volume1/docker/zapply/runner.log 2>&1 &
echo $! > /volume1/docker/zapply/runner.pid
echo "GitHub Actions runner started (PID: $(cat /volume1/docker/zapply/runner.pid))"
STARTSCRIPT

chmod +x /volume1/docker/zapply/start-runner.sh

cat > /volume1/docker/zapply/stop-runner.sh << 'STOPSCRIPT'
#!/bin/bash
if [ -f /volume1/docker/zapply/runner.pid ]; then
    PID=$(cat /volume1/docker/zapply/runner.pid)
    kill $PID
    rm /volume1/docker/zapply/runner.pid
    echo "GitHub Actions runner stopped"
else
    echo "Runner PID file not found"
fi
STOPSCRIPT

chmod +x /volume1/docker/zapply/stop-runner.sh

echo "✅ Control scripts created:"
echo "   Start: /volume1/docker/zapply/start-runner.sh"
echo "   Stop: /volume1/docker/zapply/stop-runner.sh"
echo ""

echo "🎯 Step 6: Starting the runner"
echo "==============================="
/volume1/docker/zapply/start-runner.sh

echo ""
echo "✅ Runner is now running!"
echo ""

echo "📝 Step 7: Setting up auto-start"
echo "================================="
echo ""
echo "To make the runner start automatically on NAS boot:"
echo "  1. Open DSM Control Panel → Task Scheduler"
echo "  2. Create → Triggered Task → User-defined script"
echo "  3. General:"
echo "     - Task name: Start GitHub Actions Runner"
echo "     - User: root"
echo "     - Event: Boot-up"
echo "  4. Task Settings → Run command:"
echo "     /volume1/docker/zapply/start-runner.sh"
echo "  5. Save"
echo ""

echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "✅ GitHub Actions runner is now configured and running on your NAS"
echo ""
echo "Runner details:"
echo "  Name: $RUNNER_NAME"
echo "  Labels: self-hosted, linux, x64, synology, nas"
echo "  Work directory: $RUNNER_WORK_DIR"
echo ""
echo "Management commands:"
echo "  Start:  /volume1/docker/zapply/start-runner.sh"
echo "  Stop:   /volume1/docker/zapply/stop-runner.sh"
echo "  Logs:   tail -f /volume1/docker/zapply/runner.log"
echo "  Status: ps aux | grep run.sh"
echo ""
echo "Next steps:"
echo "  1. Verify runner appears on GitHub:"
echo "     https://github.com/vpetreski/zapply/settings/actions/runners"
echo "  2. Push a commit to main branch to trigger deployment"
echo "  3. Watch the workflow run on your NAS!"
echo ""
