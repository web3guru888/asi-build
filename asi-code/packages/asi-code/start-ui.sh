#!/bin/bash

echo "🎨 Starting ASI-Code Web UI..."
echo ""
echo "The UI will be available at:"
echo "  http://localhost:8090"
echo ""
echo "Make sure the ASI-Code server is running on port 3000"
echo ""

cd /home/ubuntu/code/ASI_BUILD/asi-code/packages/asi-code
python3 -m http.server 8090 --directory public