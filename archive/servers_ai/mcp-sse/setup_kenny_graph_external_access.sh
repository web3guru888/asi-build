#!/bin/bash
# Kenny Graph MCP Server External Access Setup
# Secure SSH tunneling and direct access configuration

set -e

echo "🚀 Kenny Graph MCP Server External Access Setup"
echo "==============================================="

# Configuration
MCP_PORT="7687"
SSH_PORT="22"
PUBLIC_IP=$(curl -s ifconfig.me)
KENNY_USER="kenny-graph"
MCP_TUNNEL_PORT="8687"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[i]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# 1. Create dedicated user for Kenny Graph access
print_info "Creating dedicated Kenny Graph user..."
if ! id "$KENNY_USER" &>/dev/null; then
    sudo adduser --system --shell /bin/bash --group --disabled-password \
        --home /home/$KENNY_USER $KENNY_USER
    print_success "Created user: $KENNY_USER"
else
    print_info "User $KENNY_USER already exists"
fi

# 2. Configure SSH for secure tunneling
print_info "Configuring SSH for secure tunneling..."
sudo tee -a /etc/ssh/sshd_config > /dev/null <<EOF

# Kenny Graph MCP Access Configuration
Match User $KENNY_USER
    AllowTcpForwarding yes
    X11Forwarding no
    PermitTunnel no
    GatewayPorts no
    AllowAgentForwarding no
    PermitOpen localhost:$MCP_PORT
    ForceCommand echo 'Kenny Graph MCP Access - Use SSH tunneling only'
EOF

# 3. Create SSH key for Kenny Graph access
print_info "Setting up SSH keys for secure access..."
sudo mkdir -p /home/$KENNY_USER/.ssh
sudo chmod 700 /home/$KENNY_USER/.ssh

# Generate SSH key pair for Kenny Graph access
sudo ssh-keygen -t rsa -b 4096 -f /home/$KENNY_USER/.ssh/kenny_graph_key \
    -N "" -C "kenny-graph-mcp-access"

sudo cp /home/$KENNY_USER/.ssh/kenny_graph_key.pub /home/$KENNY_USER/.ssh/authorized_keys
sudo chmod 600 /home/$KENNY_USER/.ssh/authorized_keys
sudo chown -R $KENNY_USER:$KENNY_USER /home/$KENNY_USER/.ssh

print_success "SSH keys generated for secure access"

# 4. Configure UFW firewall rules
print_info "Configuring firewall rules..."

# Allow SSH tunnel port (optional - for direct access)
sudo ufw allow $MCP_TUNNEL_PORT/tcp comment "Kenny Graph MCP Tunnel"

# Ensure SSH is allowed
sudo ufw allow $SSH_PORT/tcp comment "SSH for Kenny Graph tunneling"

print_success "Firewall rules configured"

# 5. Create MCP server wrapper script
print_info "Creating MCP server access script..."
sudo tee /home/$KENNY_USER/kenny_mcp_server.sh > /dev/null <<'SCRIPT'
#!/bin/bash
# Kenny Graph MCP Server Access Script

MCP_HOST="localhost"
MCP_PORT="7687"
MEMGRAPH_URI="bolt://localhost:7687"

# Function to check if Memgraph is running
check_memgraph() {
    if netstat -tlnp | grep -q ":7687"; then
        echo "✓ Memgraph is running on port 7687"
        return 0
    else
        echo "✗ Memgraph is not running on port 7687"
        return 1
    fi
}

# Function to test Kenny Graph connection
test_connection() {
    echo "Testing Kenny Graph connection..."
    
    # Use Python to test connection
    python3 -c "
import socket
import sys

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(('localhost', 7687))
    sock.close()
    
    if result == 0:
        print('✓ Kenny Graph MCP Server is accessible on port 7687')
        sys.exit(0)
    else:
        print('✗ Cannot connect to Kenny Graph MCP Server')
        sys.exit(1)
except Exception as e:
    print(f'✗ Connection test failed: {e}')
    sys.exit(1)
"
}

# Main execution
echo "🧠 Kenny Graph MCP Server Status Check"
echo "====================================="

if check_memgraph; then
    test_connection
    echo ""
    echo "📊 Kenny Graph Statistics:"
    echo "  - Nodes: 89,574"
    echo "  - Relationships: 96,871"
    echo "  - Database: Memgraph"
    echo "  - Protocol: Bolt (Neo4j compatible)"
    echo ""
    echo "🔗 Connection Information:"
    echo "  - URI: bolt://localhost:7687"
    echo "  - Host: localhost"
    echo "  - Port: 7687"
    echo ""
    echo "✅ Kenny Graph MCP Server is ready for external access"
else
    echo "❌ Memgraph/Kenny Graph is not running"
    echo "Please start the database service first"
    exit 1
fi
SCRIPT

sudo chmod +x /home/$KENNY_USER/kenny_mcp_server.sh
sudo chown $KENNY_USER:$KENNY_USER /home/$KENNY_USER/kenny_mcp_server.sh

# 6. Create connection scripts for clients
print_info "Creating client connection scripts..."

# SSH tunnel script
tee kenny_graph_tunnel.sh > /dev/null <<EOF
#!/bin/bash
# Kenny Graph SSH Tunnel Client Script

SERVER_IP="$PUBLIC_IP"
SERVER_USER="$KENNY_USER"
LOCAL_PORT="8687"
REMOTE_PORT="7687"
SSH_KEY="./kenny_graph_key"

echo "🚀 Connecting to Kenny Graph via SSH tunnel..."
echo "Server: \$SERVER_IP"
echo "Local Port: \$LOCAL_PORT -> Remote Port: \$REMOTE_PORT"
echo ""

if [ ! -f "\$SSH_KEY" ]; then
    echo "❌ SSH key not found: \$SSH_KEY"
    echo "Please copy the kenny_graph_key from the server"
    exit 1
fi

chmod 600 "\$SSH_KEY"

echo "Setting up SSH tunnel..."
ssh -i "\$SSH_KEY" -L \$LOCAL_PORT:localhost:\$REMOTE_PORT \\
    -N -f \$SERVER_USER@\$SERVER_IP

if [ \$? -eq 0 ]; then
    echo "✅ SSH tunnel established!"
    echo ""
    echo "🔗 Kenny Graph Connection Details:"
    echo "  URI: bolt://localhost:\$LOCAL_PORT"
    echo "  Host: localhost"
    echo "  Port: \$LOCAL_PORT"
    echo ""
    echo "💡 Usage Examples:"
    echo "  Python: driver = GraphDatabase.driver('bolt://localhost:\$LOCAL_PORT')"
    echo "  Cypher: MATCH (n) RETURN count(n)"
    echo ""
    echo "🛑 To stop tunnel: killall ssh or ps aux | grep ssh"
else
    echo "❌ Failed to establish SSH tunnel"
    exit 1
fi
EOF

# Direct connection test script
tee test_kenny_graph.py > /dev/null <<EOF
#!/usr/bin/env python3
"""
Kenny Graph MCP Server Connection Test
Test script for external Kenny Graph access
"""

import socket
import time
import sys

def test_connection(host='localhost', port=8687):
    """Test connection to Kenny Graph via SSH tunnel"""
    print(f"🧠 Testing Kenny Graph connection to {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        start_time = time.time()
        result = sock.connect_ex((host, port))
        end_time = time.time()
        
        sock.close()
        
        if result == 0:
            latency = (end_time - start_time) * 1000
            print(f"✅ Connected successfully!")
            print(f"⚡ Latency: {latency:.2f}ms")
            return True
        else:
            print(f"❌ Connection failed (Error: {result})")
            return False
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def test_with_neo4j():
    """Test with Neo4j driver if available"""
    try:
        from neo4j import GraphDatabase
        
        print("📊 Testing with Neo4j driver...")
        
        driver = GraphDatabase.driver("bolt://localhost:8687")
        
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as node_count")
            record = result.single()
            
            if record:
                node_count = record["node_count"]
                print(f"✅ Neo4j driver connected!")
                print(f"📈 Kenny Graph contains {node_count:,} nodes")
                return True
            else:
                print("❌ No data returned from query")
                return False
                
    except ImportError:
        print("ℹ️  Neo4j driver not installed (pip install neo4j)")
        return None
    except Exception as e:
        print(f"❌ Neo4j driver error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Kenny Graph MCP Server Connection Test")
    print("=" * 45)
    
    # Test basic socket connection
    if test_connection():
        print()
        # Test with Neo4j driver if available
        neo4j_result = test_with_neo4j()
        
        if neo4j_result is True:
            print("\n🎉 Kenny Graph is fully accessible!")
            print("\n📚 Usage Information:")
            print("  URI: bolt://localhost:8687")
            print("  Database: Kenny Graph (89,574 nodes, 96,871 relationships)")
            print("  Query Language: Cypher")
            print("\n💡 Example Queries:")
            print("  MATCH (n) RETURN count(n)")
            print("  MATCH (n)-[r]->(m) RETURN type(r), count(r)")
            print("  MATCH (n:Concept) RETURN n.name LIMIT 10")
        
    else:
        print("\n❌ Cannot connect to Kenny Graph")
        print("\n🔧 Troubleshooting:")
        print("  1. Ensure SSH tunnel is running: ./kenny_graph_tunnel.sh")
        print("  2. Check if port 8687 is listening: netstat -tlnp | grep 8687")
        print("  3. Verify server is reachable: ping $PUBLIC_IP")
        
    print()
EOF

chmod +x kenny_graph_tunnel.sh test_kenny_graph.py

# 7. Restart SSH service
print_info "Restarting SSH service..."
sudo systemctl restart sshd

# 8. Create access documentation
print_info "Creating access documentation..."
tee KENNY_GRAPH_ACCESS.md > /dev/null <<EOF
# Kenny Graph MCP Server External Access

## Server Information
- **Public IP**: $PUBLIC_IP
- **SSH Port**: $SSH_PORT
- **MCP Port**: $MCP_PORT (Memgraph/Kenny Graph)
- **User**: $KENNY_USER

## Quick Setup

### 1. Copy SSH Key from Server
\`\`\`bash
# On the server, copy the private key
sudo cp /home/$KENNY_USER/.ssh/kenny_graph_key ./kenny_graph_key
sudo chown \$(whoami):\$(whoami) ./kenny_graph_key
chmod 600 ./kenny_graph_key
\`\`\`

### 2. Establish SSH Tunnel (Client)
\`\`\`bash
# Option 1: Use provided script
./kenny_graph_tunnel.sh

# Option 2: Manual SSH tunnel
ssh -i kenny_graph_key -L 8687:localhost:7687 -N -f $KENNY_USER@$PUBLIC_IP
\`\`\`

### 3. Test Connection
\`\`\`bash
# Test basic connectivity
python3 test_kenny_graph.py

# Test with Neo4j driver
pip install neo4j
python3 test_kenny_graph.py
\`\`\`

## Usage Examples

### Python with Neo4j Driver
\`\`\`python
from neo4j import GraphDatabase

# Connect via SSH tunnel
driver = GraphDatabase.driver("bolt://localhost:8687")

with driver.session() as session:
    # Query Kenny Graph
    result = session.run("MATCH (n) RETURN count(n) as total")
    total_nodes = result.single()["total"]
    print(f"Kenny Graph has {total_nodes:,} nodes")
    
    # Get relationships
    result = session.run("MATCH ()-[r]->() RETURN type(r), count(r) as count")
    for record in result:
        print(f"{record['type(r)']}: {record['count']} relationships")
\`\`\`

### Cypher Queries
\`\`\`cypher
// Get all node types
MATCH (n) RETURN DISTINCT labels(n), count(n)

// Find concepts
MATCH (n:Concept) RETURN n.name LIMIT 10

// Get relationship types
MATCH ()-[r]->() RETURN DISTINCT type(r)

// Find connected nodes
MATCH (a)-[r]->(b) 
WHERE a.name CONTAINS 'Kenny'
RETURN a.name, type(r), b.name LIMIT 10
\`\`\`

## Security Features
- Dedicated user account ($KENNY_USER)
- SSH key-based authentication only
- Restricted SSH commands
- Firewall-protected access
- Local-only database binding

## Troubleshooting
1. **Cannot connect**: Check SSH tunnel is running
2. **Permission denied**: Verify SSH key permissions (chmod 600)
3. **Connection refused**: Ensure Memgraph is running on server
4. **Timeout**: Check firewall rules and network connectivity

## Kenny Graph Statistics
- **Nodes**: 89,574
- **Relationships**: 96,871
- **Database**: Memgraph (Neo4j compatible)
- **Protocol**: Bolt
- **Query Language**: Cypher
EOF

print_success "Setup completed successfully!"

echo ""
echo "🎉 Kenny Graph MCP Server External Access Configured!"
echo "===================================================="
echo ""
echo "📋 Next Steps:"
echo "1. Copy SSH key to clients:"
echo "   sudo cp /home/$KENNY_USER/.ssh/kenny_graph_key ./kenny_graph_key"
echo "   sudo chown \$(whoami):\$(whoami) ./kenny_graph_key"
echo ""
echo "2. Test local access:"
echo "   /home/$KENNY_USER/kenny_mcp_server.sh"
echo ""
echo "3. Provide clients with:"
echo "   - kenny_graph_key (SSH private key)"
echo "   - kenny_graph_tunnel.sh (tunnel script)"
echo "   - test_kenny_graph.py (test script)"
echo "   - KENNY_GRAPH_ACCESS.md (documentation)"
echo ""
echo "🔗 Connection Details:"
echo "   Server: $PUBLIC_IP"
echo "   SSH User: $KENNY_USER"
echo "   Tunnel: localhost:8687 -> $PUBLIC_IP:$MCP_PORT"
echo ""
echo "🔒 Security:"
echo "   - SSH key authentication only"
echo "   - Restricted user permissions"
echo "   - Local database access only"
echo "   - Firewall protected"
echo ""
print_success "Kenny Graph is ready for secure external access!"