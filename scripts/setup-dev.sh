#!/bin/bash

###############################################################################
# Duty Bot - Development Environment Setup Script
#
# This script sets up a local development environment for Duty Bot.
# It configures Python virtual environment, installs dependencies,
# generates security keys, and initializes the database.
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking prerequisites"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    print_success "Python 3 found: $(python3 --version)"

    # Check Node.js (for webapp)
    if ! command -v node &> /dev/null; then
        print_warning "Node.js is not installed (needed for webapp development)"
        print_warning "Skipping webapp setup"
        SKIP_WEBAPP=true
    else
        print_success "Node.js found: $(node --version)"
    fi

    # Check git
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed"
        exit 1
    fi
    print_success "Git found: $(git --version)"
}

# Setup Python virtual environment
setup_python_venv() {
    print_header "Setting up Python virtual environment"

    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists"
    else
        python3 -m venv venv
        print_success "Virtual environment created"
    fi

    # Activate virtual environment
    source venv/bin/activate
    print_success "Virtual environment activated"

    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    print_success "Pip upgraded"
}

# Install Python dependencies
install_python_deps() {
    print_header "Installing Python dependencies"

    pip install -r requirements.txt
    print_success "Python dependencies installed"
}

# Setup Node.js dependencies
setup_node_deps() {
    if [ "$SKIP_WEBAPP" = true ]; then
        print_warning "Skipping Node.js setup (Node.js not found)"
        return
    fi

    print_header "Setting up Node.js dependencies"

    cd webapp
    npm install
    print_success "Node.js dependencies installed"
    cd ..
}

# Generate security keys
generate_security_keys() {
    print_header "Generating security keys"

    if [ -f ".env" ]; then
        # Check if keys already exist
        if grep -q "ENCRYPTION_KEY=" .env && [ "$(grep 'ENCRYPTION_KEY=' .env | cut -d= -f2)" != "generate_with_python_command" ]; then
            print_warning "Security keys already exist in .env, skipping generation"
            return
        fi
    fi

    # Generate and save keys
    python3 scripts/generate_security_keys.py --output .env.keys

    if [ -f ".env" ]; then
        # Append keys to existing .env (removing old placeholder values)
        grep -v "ENCRYPTION_KEY=\|SECRET_KEY=\|SESSION_SECRET=\|API_TOKEN=" .env > .env.tmp
        mv .env.tmp .env
        cat .env.keys >> .env
        rm .env.keys
        print_success "Security keys appended to .env"
    else
        mv .env.keys .env
        print_success "Security keys saved to .env"
    fi
}

# Setup environment file
setup_env_file() {
    print_header "Setting up environment file"

    if [ ! -f ".env" ]; then
        print_warning ".env file not found"
        print_warning "Copying from .env.example..."
        cp .env.example .env
        print_warning "Please update .env with your configuration:"
        print_warning "  - TELEGRAM_TOKEN"
        print_warning "  - SLACK_BOT_TOKEN"
        print_warning "  - SLACK_CLIENT_ID and SLACK_CLIENT_SECRET"
        print_warning "  - Database credentials (if not using Docker)"
    else
        print_success ".env file already exists"
    fi
}

# Setup database
setup_database() {
    print_header "Setting up database"

    # Check if PostgreSQL is running (if not using Docker)
    if command -v psql &> /dev/null; then
        print_success "PostgreSQL client found"
        # Note: Actual DB setup is handled by migrations
    fi

    # Run Alembic migrations
    if [ -d "migrations" ]; then
        alembic upgrade head
        print_success "Database migrations applied"
    fi
}

# Verify installation
verify_installation() {
    print_header "Verifying installation"

    # Test Python imports
    python3 -c "import fastapi; import sqlalchemy; import telegram; import slack_bolt" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "Python dependencies verified"
    else
        print_error "Some Python dependencies are missing"
        exit 1
    fi

    # Test Node.js (if installed)
    if [ "$SKIP_WEBAPP" != true ]; then
        cd webapp
        npm list react react-dom 2>/dev/null | grep -q "react" && print_success "Node.js dependencies verified"
        cd ..
    fi
}

# Print next steps
print_next_steps() {
    echo ""
    print_header "Setup complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Update .env with your configuration:"
    echo "     - TELEGRAM_TOKEN (from @BotFather)"
    echo "     - SLACK_BOT_TOKEN (from Slack App settings)"
    echo "  2. Start development servers:"
    echo "     - Backend:  python -m uvicorn app.main:app --reload"
    echo "     - Frontend: cd webapp && npm run dev"
    echo "  3. Or use Docker Compose:"
    echo "     - docker-compose up"
    echo ""
    echo "For more information, see docs/SETUP_GUIDE.md"
    echo ""
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║          Duty Bot - Development Environment Setup             ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""

    # Change to project root
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$SCRIPT_DIR/.."

    check_prerequisites
    setup_env_file
    setup_python_venv
    install_python_deps
    setup_node_deps
    generate_security_keys
    verify_installation
    print_next_steps
}

# Run main
main
