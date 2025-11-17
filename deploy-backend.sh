#!/bin/bash
#
# Automated Backend Deployment Script
# Deploys Vercel backend and automatically aliases to production domain
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_ROOT="$HOME/Documents/northwoods-events-v2"
BACKEND_DIR="backend-example"
PROD_DOMAIN="northwoods-reel-api.vercel.app"
API_PATH="/api/generate-reel"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Backend Deployment Automation${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check we're in the right directory
if [ ! -d "$REPO_ROOT" ]; then
    echo -e "${RED}❌ Error: Repository not found at $REPO_ROOT${NC}"
    exit 1
fi

cd "$REPO_ROOT"

if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}❌ Error: Backend directory not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Repository found: $REPO_ROOT"
echo -e "${GREEN}✓${NC} Backend directory: $BACKEND_DIR"
echo ""

# Deploy to Vercel
echo -e "${YELLOW}🚀 Deploying to Vercel...${NC}"
echo ""

OUTPUT=$(vercel --prod --force 2>&1)
echo "$OUTPUT"

# Extract deployment URL
DEPLOY_URL=$(echo "$OUTPUT" | grep -o 'https://northwoods-reel-[a-z0-9\-]*-dan-sundts-projects\.vercel\.app' | head -1)

if [ -z "$DEPLOY_URL" ]; then
    echo ""
    echo -e "${RED}❌ Error: Could not extract deployment URL${NC}"
    echo -e "${YELLOW}Please manually run:${NC}"
    echo "  vercel ls | head -2"
    echo "  vercel alias [deployment-url] $PROD_DOMAIN"
    exit 1
fi

echo ""
echo -e "${GREEN}✓${NC} Deployment successful!"
echo -e "${BLUE}📦 Deployment URL:${NC} $DEPLOY_URL"
echo ""

# Wait for deployment to stabilize
echo -e "${YELLOW}⏳ Waiting 10 seconds for deployment to stabilize...${NC}"
sleep 10

# Alias to production domain
echo -e "${YELLOW}🔗 Aliasing to production domain...${NC}"
vercel alias "$DEPLOY_URL" "$PROD_DOMAIN"

echo ""
echo -e "${GREEN}✓${NC} Alias created successfully!"
echo ""

# Wait for DNS propagation
echo -e "${YELLOW}⏳ Waiting 10 seconds for DNS propagation...${NC}"
sleep 10

# Test OPTIONS (CORS preflight)
echo -e "${YELLOW}🧪 Testing CORS (OPTIONS)...${NC}"
OPTIONS_RESULT=$(curl -I -X OPTIONS "https://${PROD_DOMAIN}${API_PATH}" 2>&1 | head -1)

if echo "$OPTIONS_RESULT" | grep -q "200"; then
    echo -e "${GREEN}✓${NC} OPTIONS test passed (200 OK)"
else
    echo -e "${RED}⚠️${NC}  OPTIONS test failed: $OPTIONS_RESULT"
    echo -e "${YELLOW}   This may resolve in a few minutes. Check manually:${NC}"
    echo "   curl -I -X OPTIONS https://${PROD_DOMAIN}${API_PATH}"
fi

# Test GET (health check)
echo -e "${YELLOW}🧪 Testing GET (health check)...${NC}"
GET_RESULT=$(curl -s "https://${PROD_DOMAIN}${API_PATH}" 2>&1)

if echo "$GET_RESULT" | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✓${NC} GET test passed (health check OK)"
    echo "$GET_RESULT" | head -c 100
    echo "..."
else
    echo -e "${RED}⚠️${NC}  GET test failed"
    echo "$GET_RESULT" | head -c 200
fi

echo ""
echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo -e "${BLUE}Production URL:${NC}"
echo "  https://${PROD_DOMAIN}${API_PATH}"
echo ""
echo -e "${BLUE}Deployment URL:${NC}"
echo "  ${DEPLOY_URL}${API_PATH}"
echo ""
echo -e "${BLUE}Test commands:${NC}"
echo "  curl https://${PROD_DOMAIN}${API_PATH}"
echo "  curl -I -X OPTIONS https://${PROD_DOMAIN}${API_PATH}"
echo ""
echo -e "${YELLOW}Note: If tests failed, wait 1-2 minutes and test manually.${NC}"
echo -e "${YELLOW}DNS propagation can take a few moments.${NC}"
echo ""
