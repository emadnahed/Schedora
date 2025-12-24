#!/bin/bash
# Schedora Test Runner Script
# Provides multiple ways to run tests: complete, by segment, or individual files

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Activate virtual environment
source venv/bin/activate

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   Schedora Test Runner${NC}"
echo -e "${BLUE}================================${NC}\n"

# Function to run complete test suite
run_all_tests() {
    echo -e "${GREEN}Running complete test suite...${NC}\n"
    pytest tests/ -v --cov=src/schedora --cov-report=term-missing --cov-report=html
}

# Function to run tests by segment
run_segment_tests() {
    case $1 in
        unit)
            echo -e "${GREEN}Running unit tests...${NC}\n"
            pytest tests/unit/ -v --cov=src/schedora --cov-report=term-missing
            ;;
        integration)
            echo -e "${GREEN}Running integration tests...${NC}\n"
            pytest tests/integration/ -v --cov=src/schedora --cov-report=term-missing
            ;;
        api)
            echo -e "${GREEN}Running API tests...${NC}\n"
            pytest tests/api/ -v --cov=src/schedora --cov-report=term-missing
            ;;
        *)
            echo -e "${RED}Invalid segment: $1${NC}"
            echo "Valid segments: unit, integration, api"
            exit 1
            ;;
    esac
}

# Function to run individual test file
run_file_tests() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}Running tests from: $1${NC}\n"
        pytest "$1" -v --cov=src/schedora --cov-report=term-missing
    else
        echo -e "${RED}Test file not found: $1${NC}"
        exit 1
    fi
}

# Function to run quick tests (no coverage)
run_quick_tests() {
    echo -e "${GREEN}Running quick tests (no coverage)...${NC}\n"
    pytest tests/ -q --tb=short
}

# Function to run specific test by name
run_specific_test() {
    echo -e "${GREEN}Running test: $1${NC}\n"
    pytest tests/ -k "$1" -v --cov=src/schedora --cov-report=term-missing
}

# Function to list all test files
list_test_files() {
    echo -e "${YELLOW}Available test files:${NC}\n"
    echo -e "${BLUE}Unit Tests:${NC}"
    find tests/unit -name "test_*.py" | sed 's/^/  /'
    echo -e "\n${BLUE}Integration Tests:${NC}"
    find tests/integration -name "test_*.py" | sed 's/^/  /'
    echo -e "\n${BLUE}API Tests:${NC}"
    find tests/api -name "test_*.py" | sed 's/^/  /'
}

# Function to show test statistics
show_test_stats() {
    echo -e "${YELLOW}Test Statistics:${NC}\n"

    unit_count=$(find tests/unit -name "test_*.py" | wc -l | tr -d ' ')
    integration_count=$(find tests/integration -name "test_*.py" | wc -l | tr -d ' ')
    api_count=$(find tests/api -name "test_*.py" | wc -l | tr -d ' ')
    total=$((unit_count + integration_count + api_count))

    echo "  Unit tests:        $unit_count files"
    echo "  Integration tests: $integration_count files"
    echo "  API tests:         $api_count files"
    echo "  ─────────────────────────────"
    echo "  Total:             $total files"
    echo ""

    # Get actual test count
    echo -e "${YELLOW}Collecting test cases...${NC}"
    pytest tests/ --collect-only -q | tail -1
}

# Function to run tests with specific markers
run_marked_tests() {
    echo -e "${GREEN}Running tests with marker: $1${NC}\n"
    pytest tests/ -m "$1" -v --cov=src/schedora --cov-report=term-missing
}

# Show usage
show_usage() {
    echo -e "${YELLOW}Usage:${NC}"
    echo "  ./run_tests.sh [command] [arguments]"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  all              - Run complete test suite with coverage"
    echo "  quick            - Run all tests quickly (no coverage)"
    echo "  segment <type>   - Run tests by segment (unit/integration/api)"
    echo "  file <path>      - Run specific test file"
    echo "  test <name>      - Run specific test by name (pattern matching)"
    echo "  marker <name>    - Run tests with specific marker (unit/integration/api)"
    echo "  list             - List all test files"
    echo "  stats            - Show test statistics"
    echo "  help             - Show this help message"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  ./run_tests.sh all"
    echo "  ./run_tests.sh quick"
    echo "  ./run_tests.sh segment unit"
    echo "  ./run_tests.sh segment integration"
    echo "  ./run_tests.sh file tests/unit/test_redis_queue.py"
    echo "  ./run_tests.sh test job_service"
    echo "  ./run_tests.sh marker integration"
    echo "  ./run_tests.sh list"
    echo "  ./run_tests.sh stats"
}

# Main script logic
case ${1:-help} in
    all)
        run_all_tests
        ;;
    quick)
        run_quick_tests
        ;;
    segment)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Please specify segment (unit/integration/api)${NC}"
            exit 1
        fi
        run_segment_tests "$2"
        ;;
    file)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Please specify test file path${NC}"
            exit 1
        fi
        run_file_tests "$2"
        ;;
    test)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Please specify test name pattern${NC}"
            exit 1
        fi
        run_specific_test "$2"
        ;;
    marker)
        if [ -z "$2" ]; then
            echo -e "${RED}Error: Please specify marker (unit/integration/api)${NC}"
            exit 1
        fi
        run_marked_tests "$2"
        ;;
    list)
        list_test_files
        ;;
    stats)
        show_test_stats
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}\n"
        show_usage
        exit 1
        ;;
esac

echo -e "\n${GREEN}✓ Done!${NC}"
