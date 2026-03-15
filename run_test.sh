#!/bin/bash
# EBM 5A System Test Runner
# Usage: ./run_test.sh "Your clinical question"

# Set PYTHONPATH to current directory
export PYTHONPATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create .env file based on .env.example"
    echo "Required variables:"
    echo "  - LLM_API_KEY"
    echo "  - PUBMED_EMAIL"
    exit 1
fi

# Create logs directory if not exists
mkdir -p logs

# Get question from argument or use default
QUESTION="${1:-对于2型糖尿病患者，二甲双胍相比安慰剂是否能降低心血管事件风险？}"

# Generate log filename with timestamp
LOG_FILE="logs/test_run_$(date +%Y%m%d_%H%M%S).log"

echo "=========================================="
echo "EBM 5A System Test"
echo "=========================================="
echo "Question: $QUESTION"
echo "Log file: $LOG_FILE"
echo "=========================================="
echo ""

# Run the system
python3 src/main.py "$QUESTION" 2>&1 | tee "$LOG_FILE"

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Test completed successfully!"
    echo "Log saved to: $LOG_FILE"
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "Test failed! Check log for details."
    echo "Log saved to: $LOG_FILE"
    echo "=========================================="
    exit 1
fi
