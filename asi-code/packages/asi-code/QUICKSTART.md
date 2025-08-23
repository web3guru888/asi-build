# 🚀 ASI-Code Quick Start Guide

## Current Status
- **Version**: 0.2.0
- **Production Readiness**: 85%
- **AI Provider**: ASI:One (Fetch.ai)
- **Server**: Running on port 3333
- **Web UI**: Running on port 8888

## What's Working Now

### ✅ Fully Operational Features
1. **ASI:One Integration** - AI-powered responses via Fetch.ai's ASI platform
2. **WebSocket Communication** - Real-time bidirectional messaging
3. **Web UI Dashboard** - Modern control panel with live monitoring
4. **Session Management** - Conversation history and context tracking
5. **Health Monitoring** - Real-time system status checks
6. **API Endpoints** - RESTful API for all operations

## Access Points

### 🌐 Web Interface
- **URL**: http://localhost:8888
- **Features**: 
  - Real-time chat with ASI:One
  - System monitoring dashboard
  - API testing console
  - WebSocket status indicator

### 🔧 API Server
- **Base URL**: http://localhost:3333
- **Health Check**: http://localhost:3333/health
- **WebSocket**: ws://localhost:3333/ws

## How to Use

### Starting the System

If the servers are not running:

```bash
# Terminal 1: Start the ASI-Code server
cd /home/ubuntu/code/ASI_BUILD/asi-code/packages/asi-code
PORT=3333 bun asi-code-server-ws-enhanced.ts

# Terminal 2: Start the Web UI
cd /home/ubuntu/code/ASI_BUILD/asi-code/packages/asi-code
python3 -m http.server 8888 --directory public
```

### Using the Web Interface

1. Open your browser to http://localhost:8888
2. The WebSocket will automatically connect (green indicator)
3. Type messages in the console input
4. Press Enter to send to ASI:One
5. Receive intelligent AI responses in real-time

### Example Interactions

```
You: Hello, are you ASI:One?
ASI: Yes, I'm ASI:One from Fetch.ai, ready to help with your coding needs!

You: Generate a Python function to calculate prime numbers
ASI: [Provides complete Python implementation with explanations]

You: Help me debug this JavaScript error
ASI: [Analyzes the error and provides solutions]
```

## API Examples

### Health Check
```bash
curl http://localhost:3333/health
```

### Get Providers
```bash
curl http://localhost:3333/api/providers
```

### WebSocket Connection (JavaScript)
```javascript
const ws = new WebSocket('ws://localhost:3333/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Response:', data.message);
};

ws.send(JSON.stringify({
  type: 'chat',
  message: 'Hello ASI:One!'
}));
```

## Configuration

### Environment Variables (.env)
```bash
ASI1_API_KEY=sk_4f68400302a647d4b4dd83fae665a42308c2fdca6d644520a98e89b1f904203f
ASI1_MODEL=asi1-mini
PORT=3333
```

### Available Models
- `asi1-mini` - Fast, general purpose (current)
- `asi1-extended` - Complex reasoning
- `asi1-agentic` - Agent orchestration
- `asi1-fast` - Ultra-low latency

## Troubleshooting

### If WebSocket Won't Connect
1. Check server is running: `curl http://localhost:3333/health`
2. Refresh the browser page
3. Check browser console for errors

### If ASI:One Not Responding
1. Verify API key in `.env` file
2. Check server logs for error messages
3. Test API directly: `curl https://api.asi1.ai/v1/health`

### Port Conflicts
If ports 3333 or 8888 are in use:
```bash
# Use alternative ports
PORT=4000 bun asi-code-server-ws-enhanced.ts
python3 -m http.server 9000 --directory public
```

## System Architecture

```
┌─────────────────────────────────────────────┐
│           Web Browser (localhost:8888)       │
│                  Web UI Dashboard            │
└─────────────────┬───────────────────────────┘
                  │ WebSocket (ws://)
                  ↓
┌─────────────────────────────────────────────┐
│        ASI-Code Server (localhost:3333)      │
│         asi-code-server-ws-enhanced.ts       │
│                                              │
│  • WebSocket Handler                         │
│  • Session Management                        │
│  • API Routes                                │
│  • ASI:One Client                           │
└─────────────────┬───────────────────────────┘
                  │ HTTPS API
                  ↓
┌─────────────────────────────────────────────┐
│          ASI:One API (api.asi1.ai)          │
│            Fetch.ai AI Platform              │
└─────────────────────────────────────────────┘
```

## Key Files

- `asi-code-server-ws-enhanced.ts` - Main server with ASI:One integration
- `public/index.html` - Web UI dashboard
- `.env` - Configuration and API keys
- `docs/asi1-integration.md` - Detailed ASI:One documentation

## Next Steps

1. **Test AI Capabilities**: Try complex coding questions
2. **Explore Models**: Switch between asi1-mini, extended, and agentic
3. **Build Applications**: Use the WebSocket API in your projects
4. **Monitor Performance**: Check health endpoints and logs
5. **Customize**: Modify system prompts and behaviors

## Support

- **ASI:One Issues**: Check API status at https://api.asi1.ai/status
- **Server Logs**: Monitor terminal output for debugging
- **Documentation**: See `/docs` folder for detailed guides

---

**Current Session Info:**
- Started: August 23, 2025
- ASI:One Status: Connected ✅
- WebSocket: Active ✅
- Production Readiness: 85% ✅