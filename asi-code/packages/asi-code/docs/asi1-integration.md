# ASI:One Integration Guide

## Overview

ASI-Code is now fully integrated with ASI:One (Fetch.ai's Artificial Superintelligence), providing advanced AI capabilities for code generation, analysis, and intelligent assistance.

## Features

### 🧠 Intelligent AI Responses
- Powered by ASI:One's advanced language models
- Context-aware code generation
- Multi-turn conversations with session management
- Real-time streaming responses via WebSocket

### 🔗 OpenAI-Compatible API
ASI:One provides full OpenAI API compatibility, making integration seamless:
- Standard chat completions endpoint
- Streaming support
- Temperature and token controls
- Web search capabilities

### 🚀 Available Models
- **asi1-mini** - Fast, efficient responses for general tasks
- **asi1-fast** - Ultra-low latency for real-time applications
- **asi1-extended** - Complex reasoning and analysis
- **asi1-agentic** - Agent orchestration with Agentverse integration

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# ASI:One Configuration
ASI1_API_KEY=sk_your_api_key_here
ASI1_MODEL=asi1-mini
ASI1_API_URL=https://api.asi1.ai  # Optional, this is the default

# Server Configuration
PORT=3333
HOST=0.0.0.0
```

### Getting an API Key

1. Visit [ASI:One Platform](https://asi1.ai)
2. Sign up for an account
3. Generate an API key from your dashboard
4. Add the key to your `.env` file

## Usage

### Starting the Server

```bash
# Start the enhanced ASI-Code server with ASI:One integration
bun asi-code-server-ws-enhanced.ts

# Or with custom port
PORT=3000 bun asi-code-server-ws-enhanced.ts
```

### Web UI Access

1. Start the UI server:
```bash
python3 -m http.server 8888 --directory public
```

2. Open your browser to http://localhost:8888

3. The WebSocket will automatically connect to ASI:One

### API Endpoints

#### Health Check
```bash
curl http://localhost:3333/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-23T06:30:00.000Z",
  "components": {
    "kenny": "operational",
    "asi1": "connected",
    "toolRegistry": "loaded",
    "sessionManager": "active",
    "websocket": "enabled"
  }
}
```

#### WebSocket Connection

Connect to `ws://localhost:3333/ws` for real-time communication:

```javascript
const ws = new WebSocket('ws://localhost:3333/ws');

ws.onopen = () => {
  // Send a chat message
  ws.send(JSON.stringify({
    type: 'chat',
    message: 'Hello, ASI:One!'
  }));
};

ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log('ASI:One says:', response.message);
};
```

### Message Types

The WebSocket server supports various message types:

- **chat** - General conversation
- **command** - Execute specific commands
- **ping/pong** - Connection keepalive
- **history** - Get conversation history

Example messages:

```javascript
// Chat message
{
  "type": "chat",
  "message": "Generate a Python function to calculate fibonacci"
}

// Command execution
{
  "type": "command",
  "data": "analyze code structure"
}

// Get history
{
  "type": "history"
}
```

## Features in Action

### Intelligent Code Generation
ASI:One can generate complete functions, classes, and even entire applications:

```
User: "Create a React component for user authentication"
ASI:One: [Generates complete authentication component with best practices]
```

### Code Analysis
Get intelligent insights about your codebase:

```
User: "Analyze this function for performance improvements"
ASI:One: [Provides detailed analysis with specific optimization suggestions]
```

### Debugging Assistance
ASI:One helps identify and fix bugs:

```
User: "Why is this async function not working?"
ASI:One: [Explains the issue and provides corrected code]
```

## Advanced Configuration

### Custom System Prompts

Modify the ASI:One system prompt in `asi-code-server-ws-enhanced.ts`:

```typescript
messages: [
  { 
    role: 'system', 
    content: 'You are ASI-Code, an expert coding assistant specializing in [your tech stack].' 
  },
  { role: 'user', content: message }
]
```

### Session Management

Sessions are automatically created and managed. Each WebSocket connection gets a unique session ID:

```json
{
  "type": "welcome",
  "sessionId": "session_1755930530503",
  "asi1Status": "connected"
}
```

### Error Handling

The system gracefully handles API errors and provides fallback responses:

- Connection failures return informative error messages
- Mock mode available when API key is not set
- Automatic retry logic for transient failures

## Monitoring

### Server Logs

Monitor the server output for debugging:

```bash
# View real-time logs
tail -f asi-code.log

# Check ASI:One connection status
grep "ASI1" asi-code.log
```

### Metrics

The health endpoint provides real-time status:
- ASI:One connection status
- Active WebSocket connections
- Session count
- Response times

## Troubleshooting

### Common Issues

#### API Key Not Working
- Verify the key is correctly set in `.env`
- Check the key hasn't expired
- Ensure proper formatting: `ASI1_API_KEY=sk_...`

#### Connection Refused
- Verify ASI:One API is accessible: `curl https://api.asi1.ai/v1/health`
- Check firewall/proxy settings
- Ensure the server is running on the correct port

#### Slow Responses
- Consider using `asi1-fast` model for lower latency
- Check network connection to ASI:One API
- Monitor server resources

### Debug Mode

Enable debug logging:

```bash
DEBUG=* bun asi-code-server-ws-enhanced.ts
```

## Security Best Practices

1. **Never commit API keys** - Use environment variables
2. **Use HTTPS in production** - Secure WebSocket connections
3. **Implement rate limiting** - Prevent API abuse
4. **Validate inputs** - Sanitize user messages
5. **Monitor usage** - Track API consumption

## API Rate Limits

ASI:One has usage limits based on your plan:
- Requests per minute
- Tokens per request
- Total monthly tokens

Monitor your usage in the ASI:One dashboard.

## Support

### Resources
- [ASI:One Documentation](https://docs.asi1.ai)
- [API Reference](https://api.asi1.ai/docs)
- [Fetch.ai Community](https://fetch.ai/community)

### Contact
- Technical Issues: Open an issue in the ASI-Code repository
- API Support: Contact ASI:One support
- Feature Requests: Submit via GitHub discussions

## Future Enhancements

Planned improvements for ASI:One integration:
- [ ] Streaming responses in the UI
- [ ] Multi-model support (model switching)
- [ ] Agentverse marketplace integration
- [ ] Custom tool calling
- [ ] Fine-tuning support
- [ ] Batch processing API
- [ ] Cost tracking and optimization

## Conclusion

The ASI:One integration brings powerful AI capabilities to ASI-Code, enabling intelligent code assistance, generation, and analysis. With OpenAI-compatible APIs and real-time WebSocket support, developers can leverage cutting-edge AI technology for enhanced productivity.

---

*Last Updated: August 23, 2025*  
*ASI-Code Version: 0.2.0*  
*Status: 85% Production Ready*