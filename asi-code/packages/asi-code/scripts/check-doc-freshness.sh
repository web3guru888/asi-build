#!/bin/bash

# Documentation Freshness Check Script
# Checks if documentation is up to date with recent code changes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WARNINGS=0
ERRORS=0

echo -e "${BLUE}📅 Checking documentation freshness...${NC}"

# Function to check file age
check_file_freshness() {
    local file="$1"
    local context="$2"
    
    if [[ ! -f "$file" ]]; then
        return 0
    fi
    
    # Get last modified time (days ago)
    local days_old
    if command -v stat > /dev/null; then
        # Linux/macOS compatible
        local last_modified
        last_modified=$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null || echo "0")
        local current_time
        current_time=$(date +%s)
        days_old=$(( (current_time - last_modified) / 86400 ))
    else
        # Fallback to git if stat is not available
        local git_modified
        git_modified=$(git log -1 --format=%ct -- "$file" 2>/dev/null || echo "0")
        local current_time
        current_time=$(date +%s)
        days_old=$(( (current_time - git_modified) / 86400 ))
    fi
    
    # Determine freshness status
    if [[ $days_old -gt 90 ]]; then
        echo -e "${RED}❌ $(basename "$file") is very old ($days_old days) - $context${NC}"
        ((ERRORS++))
    elif [[ $days_old -gt 30 ]]; then
        echo -e "${YELLOW}⚠️ $(basename "$file") is aging ($days_old days) - $context${NC}"
        ((WARNINGS++))
    elif [[ $days_old -gt 7 ]]; then
        echo -e "${BLUE}ℹ️ $(basename "$file") is $days_old days old - $context${NC}"
    else
        echo -e "${GREEN}✅ $(basename "$file") is fresh ($days_old days old)${NC}"
    fi
}

# Check if API docs are in sync with route changes
check_api_sync() {
    local api_file="$PROJECT_ROOT/API.md"
    local routes_file="$PROJECT_ROOT/src/server/routes.ts"
    
    if [[ ! -f "$api_file" || ! -f "$routes_file" ]]; then
        return 0
    fi
    
    echo -e "\n${BLUE}Checking API documentation sync...${NC}"
    
    # Get last modified times
    local api_modified routes_modified
    if command -v stat > /dev/null; then
        api_modified=$(stat -c %Y "$api_file" 2>/dev/null || stat -f %m "$api_file" 2>/dev/null || echo "0")
        routes_modified=$(stat -c %Y "$routes_file" 2>/dev/null || stat -f %m "$routes_file" 2>/dev/null || echo "0")
    else
        api_modified=$(git log -1 --format=%ct -- "$api_file" 2>/dev/null || echo "0")
        routes_modified=$(git log -1 --format=%ct -- "$routes_file" 2>/dev/null || echo "0")
    fi
    
    # Check if routes were modified after API docs
    if [[ $routes_modified -gt $api_modified ]]; then
        local days_behind
        days_behind=$(( (routes_modified - api_modified) / 86400 ))
        if [[ $days_behind -gt 1 ]]; then
            echo -e "${YELLOW}⚠️ API.md may be outdated - routes.ts was modified $days_behind days after API.md${NC}"
            ((WARNINGS++))
        fi
    else
        echo -e "${GREEN}✅ API.md appears to be in sync with routes.ts${NC}"
    fi
}

# Check if README reflects recent changes
check_readme_relevance() {
    local readme_file="$PROJECT_ROOT/README.md"
    
    if [[ ! -f "$readme_file" ]]; then
        return 0
    fi
    
    echo -e "\n${BLUE}Checking README relevance...${NC}"
    
    # Check if package.json was updated more recently than README
    local package_file="$PROJECT_ROOT/package.json"
    if [[ -f "$package_file" ]]; then
        local readme_modified package_modified
        if command -v stat > /dev/null; then
            readme_modified=$(stat -c %Y "$readme_file" 2>/dev/null || stat -f %m "$readme_file" 2>/dev/null || echo "0")
            package_modified=$(stat -c %Y "$package_file" 2>/dev/null || stat -f %m "$package_file" 2>/dev/null || echo "0")
        else
            readme_modified=$(git log -1 --format=%ct -- "$readme_file" 2>/dev/null || echo "0")
            package_modified=$(git log -1 --format=%ct -- "$package_file" 2>/dev/null || echo "0")
        fi
        
        if [[ $package_modified -gt $readme_modified ]]; then
            local days_behind
            days_behind=$(( (package_modified - readme_modified) / 86400 ))
            if [[ $days_behind -gt 7 ]]; then
                echo -e "${YELLOW}⚠️ README.md may need updates - package.json was modified $days_behind days after README${NC}"
                ((WARNINGS++))
            fi
        fi
    fi
    
    # Check for placeholder content
    if grep -q "TODO\|FIXME\|Coming soon\|Under construction" "$readme_file"; then
        echo -e "${YELLOW}⚠️ README.md contains placeholder content (TODO/FIXME/Coming soon)${NC}"
        ((WARNINGS++))
    else
        echo -e "${GREEN}✅ README.md appears complete${NC}"
    fi
}

# Check if code changes suggest documentation updates are needed
check_significant_changes() {
    echo -e "\n${BLUE}Checking for significant changes that may require doc updates...${NC}"
    
    # Only check if we're in a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        echo -e "${BLUE}ℹ️ Not in a git repository, skipping change analysis${NC}"
        return 0
    fi
    
    # Check recent commits for API changes
    local recent_commits
    recent_commits=$(git log --oneline --since="7 days ago" --grep="API\|route\|endpoint" 2>/dev/null || echo "")
    
    if [[ -n "$recent_commits" ]]; then
        echo -e "${YELLOW}⚠️ Recent API-related commits found:${NC}"
        echo "$recent_commits" | head -3 | sed 's/^/  /'
        echo -e "${YELLOW}Consider updating API documentation${NC}"
        ((WARNINGS++))
    fi
    
    # Check for new dependencies that might need documentation
    local recent_package_changes
    recent_package_changes=$(git log --oneline --since="7 days ago" -- package.json 2>/dev/null || echo "")
    
    if [[ -n "$recent_package_changes" ]]; then
        echo -e "${BLUE}ℹ️ Recent package.json changes found - check if documentation needs updates${NC}"
    fi
    
    # Check for new source files that might need documentation
    local new_source_files
    new_source_files=$(git log --name-status --since="7 days ago" --pretty=format: | grep "^A.*\.ts$" | wc -l 2>/dev/null || echo "0")
    
    if [[ $new_source_files -gt 0 ]]; then
        echo -e "${BLUE}ℹ️ $new_source_files new TypeScript files added recently - consider documentation coverage${NC}"
    fi
}

# Check for broken references to code examples
check_example_references() {
    echo -e "\n${BLUE}Checking documentation example references...${NC}"
    
    local docs_with_examples=(
        "$PROJECT_ROOT/API.md"
        "$PROJECT_ROOT/README.md"
        "$PROJECT_ROOT/DEPLOYMENT.md"
    )
    
    for doc in "${docs_with_examples[@]}"; do
        if [[ ! -f "$doc" ]]; then
            continue
        fi
        
        # Look for references to example files
        while IFS= read -r line; do
            if [[ "$line" =~ docs/examples/[^[:space:])]+ ]]; then
                local example_ref="${BASH_REMATCH[0]}"
                local example_file="$PROJECT_ROOT/$example_ref"
                
                if [[ ! -f "$example_file" ]]; then
                    echo -e "${RED}❌ Missing example file referenced in $(basename "$doc"): $example_ref${NC}"
                    ((ERRORS++))
                fi
            fi
        done < "$doc"
    done
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    # Check core documentation files
    echo -e "${BLUE}Checking core documentation files:${NC}"
    check_file_freshness "README.md" "project overview and setup"
    check_file_freshness "API.md" "API reference documentation"
    check_file_freshness "DEPLOYMENT.md" "deployment instructions"
    check_file_freshness "SECURITY.md" "security guidelines"
    check_file_freshness "CONTRIBUTING.md" "contribution guidelines"
    
    # Check documentation directories
    if [[ -d "docs/" ]]; then
        echo -e "\n${BLUE}Checking docs/ directory structure:${NC}"
        find docs/ -name "*.md" -type f | while read -r doc_file; do
            local relative_path
            relative_path=$(basename "$doc_file")
            check_file_freshness "$doc_file" "documentation file"
        done
    fi
    
    # Perform sync checks
    check_api_sync
    check_readme_relevance
    check_significant_changes
    check_example_references
    
    # Summary
    echo -e "\n${BLUE}📊 Freshness Check Summary:${NC}"
    echo -e "  Errors: $ERRORS"
    echo -e "  Warnings: $WARNINGS"
    
    if [[ $ERRORS -eq 0 && $WARNINGS -eq 0 ]]; then
        echo -e "\n${GREEN}✅ All documentation appears fresh and up-to-date!${NC}"
        exit 0
    elif [[ $ERRORS -eq 0 ]]; then
        echo -e "\n${YELLOW}⚠️ Documentation freshness check completed with $WARNINGS warnings${NC}"
        echo -e "${YELLOW}Consider updating the flagged documentation files${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Found $ERRORS critical freshness issues${NC}"
        echo -e "${RED}Please update the outdated documentation before committing${NC}"
        exit 1
    fi
}

# Run main function
main "$@"