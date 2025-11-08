#!/bin/bash
# Run the Wren interview agent CLI

cd "$(dirname "$0")"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found"
    echo "Please create .env file with your API credentials"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Run the CLI
python3 cli_interview.py

