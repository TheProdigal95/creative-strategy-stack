#!/bin/bash
# Creative Strategy Stack — One-command setup
# Run from the repo root: ./setup.sh

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "=================================="
echo " Creative Strategy Stack — Setup"
echo "=================================="
echo ""

# -------------------------------------------------------------------
# 1. Check for Node.js
# -------------------------------------------------------------------
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}[OK]${NC} Node.js found: $NODE_VERSION"
else
    echo -e "${YELLOW}[!]${NC} Node.js not found."

    # Check for Homebrew (macOS)
    if command -v brew &> /dev/null; then
        echo "    Installing Node.js via Homebrew..."
        brew install node
        echo -e "${GREEN}[OK]${NC} Node.js installed: $(node --version)"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "    Homebrew not found. Installing Homebrew first..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Add Homebrew to PATH for this session
        if [[ -f /opt/homebrew/bin/brew ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [[ -f /usr/local/bin/brew ]]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi

        echo "    Installing Node.js..."
        brew install node
        echo -e "${GREEN}[OK]${NC} Node.js installed: $(node --version)"
    else
        echo -e "${RED}[ERROR]${NC} Please install Node.js manually: https://nodejs.org/"
        exit 1
    fi
fi

# -------------------------------------------------------------------
# 2. Check for Python 3
# -------------------------------------------------------------------
if command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 --version)
    echo -e "${GREEN}[OK]${NC} $PY_VERSION found"
else
    echo -e "${YELLOW}[!]${NC} Python 3 not found."
    if command -v brew &> /dev/null; then
        echo "    Installing Python 3 via Homebrew..."
        brew install python
        echo -e "${GREEN}[OK]${NC} $(python3 --version) installed"
    else
        echo -e "${RED}[ERROR]${NC} Please install Python 3: https://www.python.org/downloads/"
        exit 1
    fi
fi

# -------------------------------------------------------------------
# 3. Install npm dependencies
# -------------------------------------------------------------------
echo ""
echo "Installing tool dependencies..."

cd "$REPO_DIR/tools/ad-library"
npm install --silent 2>/dev/null
echo -e "${GREEN}[OK]${NC} Ad Library tools installed"

cd "$REPO_DIR/tools/gemini-api"
npm install --silent 2>/dev/null
echo -e "${GREEN}[OK]${NC} Gemini API tools installed"

cd "$REPO_DIR"

# -------------------------------------------------------------------
# 4. Install Research Engine Python dependencies
# -------------------------------------------------------------------
echo ""
echo "Installing Research Engine dependencies..."

pip3 install -q -r "$REPO_DIR/research-engine/requirements.txt" 2>/dev/null
echo -e "${GREEN}[OK]${NC} Research Engine Python packages installed"

# -------------------------------------------------------------------
# 5. Copy skills and commands to Claude Code config
# -------------------------------------------------------------------
echo ""
echo "Installing skills and commands into Claude Code..."

mkdir -p ~/.claude/skills ~/.claude/commands

cp -r "$REPO_DIR/skills/"* ~/.claude/skills/
echo -e "${GREEN}[OK]${NC} Skills installed ($(ls -d skills/*/ | wc -l | tr -d ' ') skills)"

cp -r "$REPO_DIR/commands/"* ~/.claude/commands/
echo -e "${GREEN}[OK]${NC} Commands installed ($(ls commands/*.md | wc -l | tr -d ' ') commands)"

# -------------------------------------------------------------------
# 6. Configure Research Engine as MCP server
# -------------------------------------------------------------------
echo ""
echo "Configuring Research Engine MCP server..."

MCP_CONFIG="$HOME/.mcp.json"
PYTHON_PATH=$(which python3)
MCP_SERVER_PATH="$REPO_DIR/research-engine/engine/mcp_server.py"

if [ -f "$MCP_CONFIG" ]; then
    # Check if research-engine is already configured
    if grep -q "research-engine" "$MCP_CONFIG" 2>/dev/null; then
        echo -e "${GREEN}[OK]${NC} Research Engine MCP already configured"
    else
        # Add research-engine to existing config
        # Use Python to safely merge JSON
        python3 -c "
import json, sys
with open('$MCP_CONFIG') as f:
    config = json.load(f)
if 'mcpServers' not in config:
    config['mcpServers'] = {}
config['mcpServers']['research-engine'] = {
    'command': '$PYTHON_PATH',
    'args': ['$MCP_SERVER_PATH']
}
with open('$MCP_CONFIG', 'w') as f:
    json.dump(config, f, indent=2)
print('Added research-engine to existing .mcp.json')
"
        echo -e "${GREEN}[OK]${NC} Research Engine added to MCP config"
    fi
else
    # Create new .mcp.json
    cat > "$MCP_CONFIG" << MCPEOF
{
  "mcpServers": {
    "research-engine": {
      "command": "$PYTHON_PATH",
      "args": ["$MCP_SERVER_PATH"]
    }
  }
}
MCPEOF
    echo -e "${GREEN}[OK]${NC} MCP config created at $MCP_CONFIG"
fi

# -------------------------------------------------------------------
# 7. Set up API keys
# -------------------------------------------------------------------
echo ""
echo "Setting up API keys..."

NEEDS_KEYS=false

if [ ! -f "$REPO_DIR/tools/ad-library/.env" ]; then
    cp "$REPO_DIR/.env.example" "$REPO_DIR/tools/ad-library/.env"
    NEEDS_KEYS=true
fi

if [ ! -f "$REPO_DIR/tools/gemini-api/.env" ]; then
    cp "$REPO_DIR/.env.example" "$REPO_DIR/tools/gemini-api/.env"
    NEEDS_KEYS=true
fi

if [ "$NEEDS_KEYS" = true ]; then
    echo ""
    echo -e "${YELLOW}[ACTION NEEDED]${NC} Add your API keys to these files:"
    echo "    1. $REPO_DIR/tools/ad-library/.env"
    echo "    2. $REPO_DIR/tools/gemini-api/.env"
    echo ""
    echo "  You need:"
    echo "    - GEMINI_API_KEY — Get from https://aistudio.google.com/apikey"
    echo "    - APIFY_TOKEN   — Get from https://apify.com/ (for Meta Ad Library scraping)"

    # Try to interactively set keys
    echo ""
    read -p "  Enter your GEMINI_API_KEY (or press Enter to skip): " GEMINI_KEY
    if [ -n "$GEMINI_KEY" ]; then
        sed -i '' "s/your_gemini_api_key_here/$GEMINI_KEY/" "$REPO_DIR/tools/ad-library/.env" 2>/dev/null || \
        sed -i "s/your_gemini_api_key_here/$GEMINI_KEY/" "$REPO_DIR/tools/ad-library/.env"
        sed -i '' "s/your_gemini_api_key_here/$GEMINI_KEY/" "$REPO_DIR/tools/gemini-api/.env" 2>/dev/null || \
        sed -i "s/your_gemini_api_key_here/$GEMINI_KEY/" "$REPO_DIR/tools/gemini-api/.env"
        echo -e "  ${GREEN}[OK]${NC} Gemini API key saved"
    fi

    read -p "  Enter your APIFY_TOKEN (or press Enter to skip): " APIFY_KEY
    if [ -n "$APIFY_KEY" ]; then
        sed -i '' "s/your_apify_token_here/$APIFY_KEY/" "$REPO_DIR/tools/ad-library/.env" 2>/dev/null || \
        sed -i "s/your_apify_token_here/$APIFY_KEY/" "$REPO_DIR/tools/ad-library/.env"
        echo -e "  ${GREEN}[OK]${NC} Apify token saved"
    fi
else
    echo -e "${GREEN}[OK]${NC} API key files already exist"
fi

# -------------------------------------------------------------------
# 8. Check for optional dependencies
# -------------------------------------------------------------------
echo ""
echo "Checking optional dependencies..."

# ffmpeg (needed for MLX transcription)
if command -v ffmpeg &> /dev/null; then
    echo -e "${GREEN}[OK]${NC} ffmpeg found (needed for local transcription)"
else
    echo -e "${YELLOW}[OPTIONAL]${NC} ffmpeg not found — needed only for local MLX transcription"
    echo "    Install with: brew install ffmpeg"
fi

# Python + MLX (Apple Silicon only)
if [[ "$(uname -m)" == "arm64" ]]; then
    if python3 -c "import mlx_whisper" 2>/dev/null; then
        echo -e "${GREEN}[OK]${NC} MLX Whisper found (local transcription available)"
    else
        echo -e "${YELLOW}[OPTIONAL]${NC} MLX Whisper not found — needed only for free local transcription"
        echo "    Install with: pip install mlx mlx-whisper numpy"
        echo "    Or install Pinokio (https://pinokio.computer/) with the MLX Video Transcription app"
    fi
else
    echo -e "${YELLOW}[INFO]${NC} Not Apple Silicon — local MLX transcription unavailable. Use Gemini transcription instead."
fi

# -------------------------------------------------------------------
# Done
# -------------------------------------------------------------------
echo ""
echo "=================================="
echo -e " ${GREEN}Setup complete!${NC}"
echo "=================================="
echo ""
echo " What was installed:"
echo "   - 7 AI skills → ~/.claude/skills/"
echo "   - 2 commands → ~/.claude/commands/"
echo "   - Ad Library tools (Node.js)"
echo "   - Gemini API tools (Node.js)"
echo "   - Research Engine (Python, MCP server)"
echo ""
echo " Next steps:"
echo "   1. Open this folder in Claude Code"
echo "   2. Read how-i-work.md for the full process"
echo "   3. Try: /statics-briefer, /native-ad-creative, /listicle-writer"
echo ""
echo " Available skills:"
echo "   /statics-briefer         — Static ad briefs (TEEP + Selves + Zones)"
echo "   /native-ad-creative      — Native ad headlines + image direction"
echo "   /listicle-writer         — Research-driven listicle landing pages"
echo "   /editorial-image-prompts — Editorial-style image prompts"
echo "   /story-selling           — Meta ad scripts where story earns the sale"
echo "   /critique                — Score work against any framework"
echo "   /gemini-api              — Gemini for images, video, text"
echo ""
echo " Available commands:"
echo "   /ad-library              — Scrape Meta Ad Library"
echo "   /transcribe              — Transcribe video/audio"
echo ""
echo " Research Engine (MCP — available automatically in Claude Code):"
echo "   create_brand             — Create a new brand from product info"
echo "   run_research_sprint      — Run Reddit research sprints"
echo "   check_sprint_status      — Monitor sprint progress"
echo "   list_brands / list_sprints — Browse existing brands and sprints"
echo ""
echo " Note: The Research Engine uses your Claude Code session for auth —"
echo " no separate API key needed. Just use it from within Claude Code."
echo ""
