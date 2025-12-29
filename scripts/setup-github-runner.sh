#!/bin/bash
# GitHub Actions Self-Hosted Runner Setup
# Run this script on your server to install and configure the runner

set -e

echo "🤖 GitHub Actions Self-Hosted Runner Setup"
echo "==========================================="
echo ""

# CUSTOMIZE THESE FOR YOUR ENVIRONMENT
GITHUB_REPO="${GITHUB_REPO:-your_username/zapply}"
RUNNER_NAME="${RUNNER_NAME:-zapply-runner}"
RUNNER_WORK_DIR="${RUNNER_WORK_DIR:-/path/to/zapply/runner-work}"
RUNNER_DIR="${RUNNER_DIR:-/path/to/zapply/github-runner}"

echo "📋 Step 1: Prerequisites"
echo "========================"
echo ""
echo "Before proceeding, make sure you have:"
echo "  1. Docker installed on your server"
echo "  2. A GitHub Personal Access Token (PAT) or repository admin access"
echo "  3. The runner registration token from GitHub"
echo ""
echo "To get the registration token:"
echo "  1. Go to: https://github.com/${GITHUB_REPO}/settings/actions/runners/new"
echo "  2. Copy the token from the 'Configure' section"
echo ""
read -p "Do you have the registration token? (yes/no): " has_token

if [ "$has_token" != "yes" ]; then
    echo ""
    echo "Please get the registration token first, then run this script again."
    echo "Run this command to get it:"
    echo "  gh api -X POST repos/${GITHUB_REPO}/actions/runners/registration-token --jq .token"
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
RUNNER_VERSION="2.321.0"  # Update to latest version as needed
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
    --url https://github.com/${GITHUB_REPO} \
    --token "$RUNNER_TOKEN" \
    --name "$RUNNER_NAME" \
    --work "$RUNNER_WORK_DIR" \
    --labels self-hosted,linux,x64 \
    --unattended \
    --replace

echo ""
echo "✅ Runner configured successfully"
echo ""

echo "🚀 Step 5: Creating control scripts"
echo "===================================="

# Create start script
cat > start-runner.sh << 'STARTSCRIPT'
#!/bin/bash
cd "$(dirname "$0")/github-runner"
nohup ./run.sh > ../runner.log 2>&1 &
echo $! > ../runner.pid
echo "GitHub Actions runner started (PID: $(cat ../runner.pid))"
STARTSCRIPT
chmod +x start-runner.sh

# Create stop script
cat > stop-runner.sh << 'STOPSCRIPT'
#!/bin/bash
SCRIPT_DIR="$(dirname "$0")"
if [ -f "$SCRIPT_DIR/runner.pid" ]; then
    PID=$(cat "$SCRIPT_DIR/runner.pid")
    kill $PID
    rm "$SCRIPT_DIR/runner.pid"
    echo "GitHub Actions runner stopped"
else
    echo "Runner PID file not found"
fi
STOPSCRIPT
chmod +x stop-runner.sh

echo "✅ Control scripts created"
echo ""

echo "🎯 Step 6: Starting the runner"
echo "==============================="
./start-runner.sh

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "✅ GitHub Actions runner is now configured and running"
echo ""
echo "Runner details:"
echo "  Name: $RUNNER_NAME"
echo "  Labels: self-hosted, linux, x64"
echo "  Work directory: $RUNNER_WORK_DIR"
echo ""
echo "Management commands:"
echo "  Start:  ./start-runner.sh"
echo "  Stop:   ./stop-runner.sh"
echo "  Logs:   tail -f runner.log"
echo "  Status: ps aux | grep run.sh"
echo ""
echo "Next steps:"
echo "  1. Verify runner appears on GitHub:"
echo "     https://github.com/${GITHUB_REPO}/settings/actions/runners"
echo "  2. Push a commit to main branch to trigger deployment"
echo "  3. Watch the workflow run!"
echo ""
