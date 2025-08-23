#!/bin/bash

# Quick Code Examples Validation Script
# Performs lightweight validation of code examples for pre-commit hooks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0

echo -e "${BLUE}🧪 Quick validation of code examples...${NC}"

# Function to validate JSON code blocks
validate_json() {
    local file="$1"
    local json_content="$2"
    local line_num="$3"
    
    if echo "$json_content" | jq . > /dev/null 2>&1; then
        return 0
    else
        echo -e "${RED}❌ Invalid JSON in $(basename "$file") at line ~$line_num${NC}"
        ((ERRORS++))
        return 1
    fi
}

# Function to check JavaScript/TypeScript syntax
validate_js_syntax() {
    local file="$1"
    local code="$2"
    local language="$3"
    local line_num="$4"
    
    # Skip incomplete snippets
    if [[ ${#code} -lt 50 ]]; then
        return 0
    fi
    
    # Skip examples with placeholders
    if echo "$code" | grep -q "your-api-key\|example\.com\|TODO\|FIXME"; then
        return 0
    fi
    
    # Create temp file
    local temp_file="/tmp/validate-${language}-$$.${language}"
    echo "$code" > "$temp_file"
    
    # Basic syntax check with node (for JS) or tsc (for TS)
    if [[ "$language" == "typescript" ]] && command -v tsc > /dev/null; then
        if ! tsc --noEmit --skipLibCheck "$temp_file" 2>/dev/null; then
            echo -e "${YELLOW}⚠️ TypeScript syntax issue in $(basename "$file") at line ~$line_num${NC}"
        fi
    elif [[ "$language" == "javascript" ]] && command -v node > /dev/null; then
        if ! node -c "$temp_file" 2>/dev/null; then
            echo -e "${YELLOW}⚠️ JavaScript syntax issue in $(basename "$file") at line ~$line_num${NC}"
        fi
    fi
    
    rm -f "$temp_file"
    return 0
}

# Function to validate curl commands
validate_curl_quick() {
    local file="$1"
    local curl_cmd="$2"
    local line_num="$3"
    
    # Check for basic curl syntax issues
    if ! echo "$curl_cmd" | grep -q "^curl\s"; then
        echo -e "${RED}❌ Invalid curl command in $(basename "$file") at line ~$line_num${NC}"
        ((ERRORS++))
        return 1
    fi
    
    # Check for missing URLs
    if ! echo "$curl_cmd" | grep -qE "https?://|localhost"; then
        echo -e "${YELLOW}⚠️ Curl command missing URL in $(basename "$file") at line ~$line_num${NC}"
    fi
    
    # Check for potentially dangerous commands
    if echo "$curl_cmd" | grep -qE "\-X\s+(DELETE|PUT)" && echo "$curl_cmd" | grep -q "rm\|delete\|DROP"; then
        echo -e "${YELLOW}⚠️ Potentially dangerous curl command in $(basename "$file") at line ~$line_num${NC}"
    fi
    
    return 0
}

# Main validation function
validate_file() {
    local file="$1"
    
    echo -e "${BLUE}Checking $(basename "$file")...${NC}"
    
    local line_num=1
    local in_code_block=false
    local code_language=""
    local code_content=""
    
    while IFS= read -r line; do
        # Detect code block start
        if [[ "$line" =~ ^\`\`\`([a-zA-Z]*) ]]; then
            if [[ "$in_code_block" == true ]]; then
                # End of code block - validate accumulated content
                case "$code_language" in
                    "json")
                        validate_json "$file" "$code_content" "$line_num"
                        ;;
                    "javascript"|"js")
                        validate_js_syntax "$file" "$code_content" "javascript" "$line_num"
                        ;;
                    "typescript"|"ts")
                        validate_js_syntax "$file" "$code_content" "typescript" "$line_num"
                        ;;
                    "bash"|"sh")
                        if echo "$code_content" | grep -q "^curl"; then
                            validate_curl_quick "$file" "$code_content" "$line_num"
                        fi
                        ;;
                esac
                
                # Reset for next block
                in_code_block=false
                code_language=""
                code_content=""
            else
                # Start of code block
                in_code_block=true
                code_language="${BASH_REMATCH[1]}"
            fi
        elif [[ "$in_code_block" == true ]]; then
            # Accumulate code content
            code_content+="$line"$'\n'
        elif [[ "$line" =~ ^curl[[:space:]] ]]; then
            # Inline curl command
            validate_curl_quick "$file" "$line" "$line_num"
        fi
        
        ((line_num++))
    done < "$file"
    
    # Handle case where file ends with open code block
    if [[ "$in_code_block" == true ]]; then
        echo -e "${RED}❌ Unclosed code block in $(basename "$file")${NC}"
        ((ERRORS++))
    fi
}

# Find and validate markdown files
find_and_validate() {
    local search_paths=("$@")
    
    for search_path in "${search_paths[@]}"; do
        if [[ -f "$search_path" && "$search_path" =~ \.md$ ]]; then
            validate_file "$search_path"
        elif [[ -d "$search_path" ]]; then
            while IFS= read -r -d '' file; do
                if [[ ! "$file" =~ (node_modules|dist|coverage|\.git)/ ]]; then
                    validate_file "$file"
                fi
            done < <(find "$search_path" -name "*.md" -type f -print0)
        fi
    done
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    # Check if we have the necessary tools
    local missing_tools=()
    if ! command -v jq > /dev/null; then
        missing_tools+=("jq")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        echo -e "${YELLOW}⚠️ Missing tools: ${missing_tools[*]}${NC}"
        echo -e "${YELLOW}Some validations will be skipped${NC}"
    fi
    
    # If specific files are provided as arguments, validate those
    if [[ $# -gt 0 ]]; then
        find_and_validate "$@"
    else
        # Validate all documentation
        find_and_validate "API.md" "README.md" "DEPLOYMENT.md" "docs/"
    fi
    
    # Summary
    if [[ $ERRORS -eq 0 ]]; then
        echo -e "\n${GREEN}✅ Quick validation passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Found $ERRORS issues in code examples${NC}"
        echo -e "${RED}Run 'npm run test:examples' for detailed validation${NC}"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"