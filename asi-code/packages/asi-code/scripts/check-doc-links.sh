#!/bin/bash

# Check Documentation Links Script
# Validates internal links in documentation files

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Checking internal documentation links...${NC}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0
WARNINGS=0

# Function to check if a file exists
check_file_exists() {
    local link="$1"
    local source_file="$2"
    
    # Convert relative path to absolute path
    local abs_path
    if [[ "$link" == /* ]]; then
        # Absolute path from project root
        abs_path="${PROJECT_ROOT}${link}"
    else
        # Relative path from source file directory
        local source_dir
        source_dir="$(dirname "$source_file")"
        abs_path="$(cd "$source_dir" && realpath "$link" 2>/dev/null || echo "INVALID")"
    fi
    
    if [[ "$abs_path" == "INVALID" ]] || [[ ! -f "$abs_path" ]]; then
        echo -e "${RED}❌ Broken link in $(basename "$source_file"): $link${NC}"
        ((ERRORS++))
        return 1
    fi
    
    return 0
}

# Function to check internal links in a markdown file
check_markdown_links() {
    local file="$1"
    
    echo -e "${BLUE}Checking $file...${NC}"
    
    # Extract markdown links: [text](link)
    while IFS= read -r line; do
        # Skip external links (http/https) and anchors (#)
        if [[ "$line" =~ ^\[.*\]\(([^)]+)\)$ ]] && [[ ! "${BASH_REMATCH[1]}" =~ ^(https?:|#) ]]; then
            local link="${BASH_REMATCH[1]}"
            
            # Remove anchor from link if present
            local file_link
            file_link="${link%%#*}"
            
            if [[ -n "$file_link" ]]; then
                check_file_exists "$file_link" "$file"
            fi
        fi
    done < <(grep -o '\[.*\](.*\.md\|.*\.txt\|.*\.js\|.*\.ts\|.*\.json\|.*\.yaml\|.*\.yml\|/[^)]*[^#])' "$file" 2>/dev/null || true)
    
    # Check relative includes and references
    while IFS= read -r line; do
        if [[ "$line" =~ \./[^[:space:])]+\.(md|ts|js|json|yaml|yml) ]]; then
            local link="${BASH_REMATCH[0]}"
            check_file_exists "$link" "$file"
        fi
    done < <(grep -o '\./[^[:space:])]*\.\(md\|ts\|js\|json\|yaml\|yml\)' "$file" 2>/dev/null || true)
}

# Function to check API documentation cross-references
check_api_cross_references() {
    local api_file="$PROJECT_ROOT/API.md"
    
    if [[ ! -f "$api_file" ]]; then
        echo -e "${YELLOW}⚠️ API.md not found, skipping API cross-reference check${NC}"
        return
    fi
    
    echo -e "${BLUE}Checking API.md cross-references...${NC}"
    
    # Check references to example files in docs/examples/
    while IFS= read -r line; do
        if [[ "$line" =~ docs/examples/[^[:space:])]+\.(js|ts|md|json) ]]; then
            local example_file="$PROJECT_ROOT/${BASH_REMATCH[0]}"
            if [[ ! -f "$example_file" ]]; then
                echo -e "${RED}❌ Missing example file referenced in API.md: ${BASH_REMATCH[0]}${NC}"
                ((ERRORS++))
            fi
        fi
    done < "$api_file"
    
    # Check that documented endpoints have examples
    local endpoints_without_examples=0
    while IFS= read -r line; do
        if [[ "$line" =~ ^####[[:space:]]+(GET|POST|PUT|DELETE|PATCH)[[:space:]]+(/.*) ]]; then
            local method="${BASH_REMATCH[1]}"
            local path="${BASH_REMATCH[2]}"
            local endpoint="$method $path"
            
            # Look for examples in the next 20 lines
            local has_example=false
            local line_num
            line_num=$(grep -n "^$line" "$api_file" | cut -d: -f1)
            if [[ -n "$line_num" ]]; then
                local next_lines
                next_lines=$(sed -n "$((line_num+1)),$((line_num+20))p" "$api_file")
                if echo "$next_lines" | grep -q '```\|**Request:\|**Response:'; then
                    has_example=true
                fi
            fi
            
            if [[ "$has_example" == false ]]; then
                echo -e "${YELLOW}⚠️ Endpoint lacks examples: $endpoint${NC}"
                ((endpoints_without_examples++))
                ((WARNINGS++))
            fi
        fi
    done < "$api_file"
    
    if [[ $endpoints_without_examples -gt 0 ]]; then
        echo -e "${YELLOW}Found $endpoints_without_examples endpoints without examples${NC}"
    fi
}

# Check documentation hierarchy and organization
check_doc_structure() {
    echo -e "${BLUE}Checking documentation structure...${NC}"
    
    local required_docs=(
        "README.md"
        "API.md"
        "DEPLOYMENT.md"
        "SECURITY.md"
    )
    
    local missing_docs=()
    for doc in "${required_docs[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$doc" ]]; then
            missing_docs+=("$doc")
        fi
    done
    
    if [[ ${#missing_docs[@]} -gt 0 ]]; then
        echo -e "${RED}❌ Missing required documentation files:${NC}"
        printf "${RED}  - %s${NC}\n" "${missing_docs[@]}"
        ERRORS=$((ERRORS + ${#missing_docs[@]}))
    fi
    
    # Check docs/ directory structure
    local docs_dir="$PROJECT_ROOT/docs"
    if [[ -d "$docs_dir" ]]; then
        local expected_subdirs=(
            "developer"
            "user"
            "api"
            "examples"
        )
        
        for subdir in "${expected_subdirs[@]}"; do
            if [[ ! -d "$docs_dir/$subdir" ]]; then
                echo -e "${YELLOW}⚠️ Recommended docs subdirectory missing: docs/$subdir${NC}"
                ((WARNINGS++))
            fi
        done
    else
        echo -e "${YELLOW}⚠️ docs/ directory not found${NC}"
        ((WARNINGS++))
    fi
}

# Main execution
main() {
    cd "$PROJECT_ROOT"
    
    # Find all markdown files
    local md_files=()
    while IFS= read -r -d '' file; do
        # Skip node_modules and other build directories
        if [[ ! "$file" =~ (node_modules|dist|coverage|\.git)/ ]]; then
            md_files+=("$file")
        fi
    done < <(find . -name "*.md" -type f -print0)
    
    echo -e "${BLUE}Found ${#md_files[@]} markdown files to check${NC}"
    
    # Check each markdown file
    for file in "${md_files[@]}"; do
        check_markdown_links "$file"
    done
    
    # Check API cross-references
    check_api_cross_references
    
    # Check documentation structure
    check_doc_structure
    
    # Summary
    echo -e "\n${BLUE}📊 Link Check Summary:${NC}"
    echo -e "  Errors: $ERRORS"
    echo -e "  Warnings: $WARNINGS"
    
    if [[ $ERRORS -eq 0 ]]; then
        echo -e "\n${GREEN}✅ All documentation links are valid!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Found $ERRORS broken links. Please fix them before committing.${NC}"
        exit 1
    fi
}

# Run main function
main "$@"