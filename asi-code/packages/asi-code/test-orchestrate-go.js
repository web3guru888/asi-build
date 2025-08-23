const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:3333/ws');

ws.on('open', function open() {
  console.log('Connected to server');
  
  // Send orchestrate command for Go MLOps platform
  ws.send(JSON.stringify({
    type: "command",
    data: "orchestrate: build a mlops platform using golang with api gateway and model serving",
    message: "orchestrate: build a mlops platform using golang with api gateway and model serving"
  }));
});

ws.on('message', function message(data) {
  const msg = JSON.parse(data.toString());
  console.log('Received:', msg.type, '-', msg.message || '');
  
  // Exit after completion
  if (msg.type === 'orchestration-completed') {
    console.log('\n✅ Test completed\!');
    if (msg.filesGenerated) {
      console.log('Files generated:', msg.filesGenerated.length);
      console.log('Output path:', msg.outputPath);
    }
    ws.close();
    process.exit(0);
  }
});

ws.on('error', function error(err) {
  console.error('WebSocket error:', err);
  process.exit(1);
});

// Timeout after 60 seconds
setTimeout(() => {
  console.log('Test timeout');
  ws.close();
  process.exit(1);
}, 60000);
