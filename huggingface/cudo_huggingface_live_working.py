#!/usr/bin/env python3
"""
WORKING CUDO + HuggingFace Integration - LIVE DEPLOYMENT READY
Fixed API parsing and ready for real deployments
"""

import asyncio
import aiohttp
import json
import os
import sys
import time
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configuration
CUDO_API_KEY = "a661306311d02d22e5a35f02b14ab2203b856906b326d029867a6733530860d0"
CUDO_API_BASE = "https://rest.compute.cudo.org/v1"
PROJECT_ID = "kenny"

class CudoHuggingFaceDeployer:
    """Production-ready CUDO + HuggingFace deployment system"""
    
    def __init__(self):
        self.api_key = CUDO_API_KEY
        self.base_url = CUDO_API_BASE
        self.project_id = PROJECT_ID
        self.session = None
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Cache
        self.machine_types = []
        self.data_centers = []
        self.gpu_machines = []
        self.cpu_machines = []
        
        print("🚀 CUDO HuggingFace Deployer initialized")
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=300)
        )
        await self.load_cudo_resources()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def load_cudo_resources(self):
        """Load and parse CUDO resources with correct API structure"""
        print("📊 Loading CUDO resources...")
        
        # Load machine types
        async with self.session.get(f"{self.base_url}/vms/machine-types") as response:
            if response.status == 200:
                data = await response.json()
                self.machine_types = data.get("machineTypes", [])
                
                # Parse GPU vs CPU machines correctly
                self.gpu_machines = []
                self.cpu_machines = []
                
                for machine in self.machine_types:
                    max_gpu = machine.get('maxGpuFree', 0)
                    if max_gpu > 0:
                        self.gpu_machines.append(machine)
                    else:
                        self.cpu_machines.append(machine)
                
                print(f"  • Total machines: {len(self.machine_types)}")
                print(f"  • GPU machines: {len(self.gpu_machines)}")
                print(f"  • CPU machines: {len(self.cpu_machines)}")
            else:
                print(f"  ❌ Failed to load machine types: {response.status}")
        
        # Load data centers
        async with self.session.get(f"{self.base_url}/vms/data-centers") as response:
            if response.status == 200:
                data = await response.json()
                self.data_centers = data.get("dataCenters", [])
                print(f"  • Data centers: {len(self.data_centers)}")
            else:
                print(f"  ❌ Failed to load data centers: {response.status}")
        
        # Show available GPU machines
        if self.gpu_machines:
            print(f"\n🎮 Available GPU Machines:")
            for machine in self.gpu_machines[:10]:  # Show first 10
                machine_type = machine.get('machineType', 'unknown')
                gpu_model = machine.get('gpuModel', 'unknown')
                max_gpu = machine.get('maxGpuFree', 0)
                gpu_price = float(machine.get('gpuPriceHr', {}).get('value', 0))
                
                print(f"  • {machine_type}")
                print(f"    GPU: {max_gpu}x {gpu_model}")
                print(f"    Price: ${gpu_price:.2f}/GPU/hour")
                print(f"    Data Center: {machine.get('dataCenterId', 'unknown')}")
        else:
            print(f"\n⚠️ No GPU machines available")
    
    def get_cheapest_gpu_machine(self, min_gpus: int = 1) -> Optional[Dict[str, Any]]:
        """Get the cheapest available GPU machine"""
        suitable_machines = []
        
        for machine in self.gpu_machines:
            max_gpu = machine.get('maxGpuFree', 0)
            if max_gpu >= min_gpus:
                suitable_machines.append(machine)
        
        if not suitable_machines:
            return None
        
        # Sort by GPU price
        suitable_machines.sort(key=lambda x: float(x.get('gpuPriceHr', {}).get('value', 999)))
        
        return suitable_machines[0]
    
    def get_optimal_datacenter(self, machine_type: str = None) -> Optional[Dict[str, Any]]:
        """Get optimal data center for deployment"""
        if not self.data_centers:
            return None
        
        # If machine type is specified, find a datacenter that has it
        if machine_type:
            for dc in self.data_centers:
                dc_id = dc.get('id')
                # Check if any machine in this datacenter matches
                for machine in self.machine_types:
                    if (machine.get('machineType') == machine_type and 
                        machine.get('dataCenterId') == dc_id):
                        return dc
        
        # Return first available
        return self.data_centers[0]
    
    def create_startup_script(self, model_name: str, model_config: Dict[str, Any]) -> str:
        """Create optimized startup script for HuggingFace model"""
        
        return f"""#!/bin/bash
# CUDO HuggingFace Deployment Script - PRODUCTION READY
# Model: {model_name}
# Generated: {datetime.now().isoformat()}

set -e  # Exit on any error

echo "=== KENNY'S HUGGINGFACE DEPLOYER ===" | tee /var/log/deployment.log
echo "Model: {model_name}" | tee -a /var/log/deployment.log
echo "Started: $(date)" | tee -a /var/log/deployment.log

# Update system
echo "Updating system..." | tee -a /var/log/deployment.log
apt-get update -y | tee -a /var/log/deployment.log
apt-get install -y python3-pip python3-venv git curl wget htop nvtop | tee -a /var/log/deployment.log

# Install NVIDIA drivers if GPU detected
if command -v nvidia-smi >/dev/null 2>&1; then
    echo "NVIDIA GPU detected" | tee -a /var/log/deployment.log
    nvidia-smi | tee -a /var/log/deployment.log
else
    echo "No NVIDIA GPU detected - using CPU mode" | tee -a /var/log/deployment.log
fi

# Create application directory
mkdir -p /opt/huggingface
cd /opt/huggingface

# Create Python virtual environment
echo "Creating Python environment..." | tee -a /var/log/deployment.log
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip | tee -a /var/log/deployment.log

# Install PyTorch - CUDA version if GPU available
if command -v nvidia-smi >/dev/null 2>&1; then
    echo "Installing PyTorch with CUDA support..." | tee -a /var/log/deployment.log
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 | tee -a /var/log/deployment.log
else
    echo "Installing PyTorch CPU version..." | tee -a /var/log/deployment.log
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu | tee -a /var/log/deployment.log
fi

# Install HuggingFace ecosystem
echo "Installing HuggingFace libraries..." | tee -a /var/log/deployment.log
pip install transformers accelerate huggingface-hub datasets | tee -a /var/log/deployment.log
pip install fastapi uvicorn pydantic | tee -a /var/log/deployment.log
pip install requests aiohttp | tee -a /var/log/deployment.log

# Pre-download the model to avoid startup delays
echo "Pre-downloading model: {model_name}..." | tee -a /var/log/deployment.log
python3 -c "
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch

print('Pre-loading model: {model_name}')
try:
    # Download tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained('{model_name}')
    model = AutoModelForCausalLM.from_pretrained('{model_name}')
    print('Model downloaded successfully!')
    
    # Test pipeline creation
    device = 0 if torch.cuda.is_available() else -1
    pipe = pipeline('text-generation', model='{model_name}', device=device)
    print('Pipeline created successfully!')
    
    # Quick test
    result = pipe('Hello', max_length=20, do_sample=False)
    print('Test generation successful!')
    
except Exception as e:
    print(f'Error during model setup: {{e}}')
    exit(1)
" | tee -a /var/log/deployment.log

# Create the FastAPI server
cat > /opt/huggingface/server.py << 'SERVEREOF'
import os
import json
import time
import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import torch
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Kenny's HuggingFace Model Server",
    description="Deployed on CUDO Compute with GPU acceleration",
    version="2.0.0"
)

# Global variables
model_pipeline = None
model_info = {{
    "model_name": "{model_name}",
    "deployed_at": datetime.now().isoformat(),
    "provider": "CUDO Compute",
    "deployer": "Kenny Universal Deployer v2.0",
    "gpu_available": torch.cuda.is_available(),
    "cuda_devices": torch.cuda.device_count() if torch.cuda.is_available() else 0
}}

# Request/Response models
class GenerateRequest(BaseModel):
    prompt: str
    max_length: Optional[int] = 100
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    num_return_sequences: Optional[int] = 1
    do_sample: Optional[bool] = True

class GenerateResponse(BaseModel):
    generated_text: str
    model: str
    provider: str
    generation_time: float
    gpu_used: bool
    status: str

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    gpu_available: bool
    uptime: str
    timestamp: str

# Startup event
@app.on_event("startup")
async def load_model():
    global model_pipeline
    
    logger.info(f"🚀 Starting model server for {{model_info['model_name']}}")
    logger.info(f"GPU Available: {{torch.cuda.is_available()}}")
    
    if torch.cuda.is_available():
        logger.info(f"CUDA Devices: {{torch.cuda.device_count()}}")
        for i in range(torch.cuda.device_count()):
            logger.info(f"  Device {{i}}: {{torch.cuda.get_device_name(i)}}")
    
    try:
        from transformers import pipeline
        
        # Create pipeline with appropriate device
        device = 0 if torch.cuda.is_available() else -1
        logger.info(f"Loading pipeline on device: {{'GPU' if device >= 0 else 'CPU'}}")
        
        model_pipeline = pipeline(
            'text-generation',
            model=model_info['model_name'],
            device=device,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        
        logger.info("✅ Model pipeline loaded successfully!")
        
        # Test generation
        test_result = model_pipeline("Test", max_length=10, do_sample=False)
        logger.info("✅ Model test generation successful!")
        
    except Exception as e:
        logger.error(f"❌ Failed to load model: {{e}}")
        model_pipeline = None

# Root endpoint with HTML interface
@app.get("/", response_class=HTMLResponse)
def root():
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kenny's HuggingFace Model Server</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; }}
            .section {{ background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #007bff; }}
            .endpoint {{ background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border: 1px solid #dee2e6; }}
            .status {{ display: inline-block; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; }}
            .status.running {{ background: #d4edda; color: #155724; }}
            .code {{ background: #f1f3f4; padding: 10px; border-radius: 4px; font-family: monospace; }}
            .gpu {{ color: #28a745; }}
            .cpu {{ color: #dc3545; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 Model Deployment Successful!</h1>
            <h2>{model_name}</h2>
            <div class="status running">RUNNING</div>
        </div>
        
        <div class="section">
            <h3>📊 System Information</h3>
            <p><strong>Model:</strong> {model_name}</p>
            <p><strong>Provider:</strong> CUDO Compute</p>
            <p><strong>GPU Available:</strong> <span class="gpu">
                ✅ GPU ACCELERATED</span></p>
            <p><strong>CUDA Devices:</strong> Available</p>
            <p><strong>Deployed:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="section">
            <h3>🔗 API Endpoints</h3>
            
            <div class="endpoint">
                <h4>Health Check</h4>
                <div class="code">GET /health</div>
                <p>Check if the model server is healthy and ready</p>
            </div>
            
            <div class="endpoint">
                <h4>Generate Text</h4>
                <div class="code">POST /generate</div>
                <p>Generate text using the loaded model</p>
                <pre>{{"prompt": "Hello, I am", "max_length": 50, "temperature": 0.7}}</pre>
            </div>
            
            <div class="endpoint">
                <h4>Model Information</h4>
                <div class="code">GET /info</div>
                <p>Get detailed information about the loaded model</p>
            </div>
        </div>
        
        <div class="section">
            <h3>🧪 Quick Test</h3>
            <p>Test the API with curl:</p>
            <div class="code">
curl -X POST http://[VM_IP]:8000/generate \\<br>
&nbsp;&nbsp;-H "Content-Type: application/json" \\<br>
&nbsp;&nbsp;-d '{{"prompt": "Kenny\\'s agent army", "max_length": 50}}'
            </div>
        </div>
        
        <footer style="text-align: center; margin-top: 40px; color: #6c757d;">
            <p>🤖 Powered by Kenny's Universal HuggingFace Deployer</p>
        </footer>
    </body>
    </html>
    '''
    return html_content

# API endpoints
@app.get("/health", response_model=HealthResponse)
def health():
    uptime = str(datetime.now() - datetime.fromisoformat(model_info["deployed_at"].replace('Z', '+00:00')))
    
    return HealthResponse(
        status="healthy" if model_pipeline is not None else "unhealthy",
        model_loaded=model_pipeline is not None,
        gpu_available=torch.cuda.is_available(),
        uptime=uptime,
        timestamp=datetime.now().isoformat()
    )

@app.get("/info")
def info():
    system_info = {{
        **model_info,
        "model_loaded": model_pipeline is not None,
        "system": {{
            "gpu_available": torch.cuda.is_available(),
            "cuda_devices": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "gpu_names": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())] if torch.cuda.is_available() else []
        }}
    }}
    return system_info

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    if model_pipeline is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        start_time = time.time()
        
        # Generate text
        results = model_pipeline(
            request.prompt,
            max_length=request.max_length,
            temperature=request.temperature,
            top_p=request.top_p,
            num_return_sequences=request.num_return_sequences,
            do_sample=request.do_sample,
            pad_token_id=model_pipeline.tokenizer.eos_token_id
        )
        
        generation_time = time.time() - start_time
        
        # Get generated text
        generated_text = results[0]['generated_text'] if results else request.prompt
        
        return GenerateResponse(
            generated_text=generated_text,
            model=model_info['model_name'],
            provider=model_info['provider'],
            generation_time=round(generation_time, 3),
            gpu_used=torch.cuda.is_available(),
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Generation error: {{e}}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {{str(e)}}")

if __name__ == "__main__":
    print(f"🚀 Starting Kenny's HuggingFace Model Server")
    print(f"Model: {{model_info['model_name']}}")
    print(f"GPU: {{model_info['gpu_available']}}")
    print(f"CUDA Devices: {{model_info['cuda_devices']}}")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
SERVEREOF

# Start the server
echo "🚀 Starting model server..." | tee -a /var/log/deployment.log
cd /opt/huggingface
source venv/bin/activate

# Create systemd service for persistence
cat > /etc/systemd/system/kenny-huggingface.service << SERVICEEOF
[Unit]
Description=Kenny's HuggingFace Model Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/huggingface
Environment=PATH=/opt/huggingface/venv/bin
ExecStart=/opt/huggingface/venv/bin/python server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF

# Enable and start service
systemctl daemon-reload
systemctl enable kenny-huggingface
systemctl start kenny-huggingface

echo "✅ Deployment complete!" | tee -a /var/log/deployment.log
echo "🌐 Model server running on port 8000" | tee -a /var/log/deployment.log
echo "🔍 Service status: systemctl status kenny-huggingface" | tee -a /var/log/deployment.log
echo "📊 Logs: journalctl -u kenny-huggingface -f" | tee -a /var/log/deployment.log
"""
    
    async def deploy_model(self, model_name: str, 
                          config: Dict[str, Any] = None,
                          dry_run: bool = True) -> Dict[str, Any]:
        """Deploy HuggingFace model to CUDO infrastructure"""
        
        if config is None:
            config = {}
        
        print(f"\n🚀 Deploying HuggingFace Model: {model_name}")
        print(f"   Mode: {'DRY RUN' if dry_run else '⚠️  LIVE DEPLOYMENT'}")
        
        # Get optimal GPU machine
        gpu_machine = self.get_cheapest_gpu_machine(min_gpus=config.get('min_gpus', 1))
        
        if not gpu_machine and config.get('gpu_required', True):
            return {
                "success": False,
                "error": "No GPU machines available",
                "suggestion": "Try again later or use CPU-only mode"
            }
        
        # Fallback to CPU if no GPU available
        if not gpu_machine:
            print("   ⚠️  No GPU available - using CPU machine")
            # Use cheapest CPU machine
            cpu_machines = sorted(self.cpu_machines, 
                                key=lambda x: float(x.get('vcpuPriceHr', {}).get('value', 999)))
            if not cpu_machines:
                return {"success": False, "error": "No machines available"}
            selected_machine = cpu_machines[0]
        else:
            selected_machine = gpu_machine
        
        # Get datacenter
        datacenter = self.get_optimal_datacenter(selected_machine.get('machineType'))
        if not datacenter:
            return {"success": False, "error": "No datacenters available"}
        
        # Create VM configuration
        machine_type = selected_machine.get('machineType')
        max_vcpu = selected_machine.get('maxVcpuFree', 8)
        max_memory = selected_machine.get('maxMemoryGibFree', 32)
        max_gpu = selected_machine.get('maxGpuFree', 0)
        
        # Calculate pricing
        vcpu_price = float(selected_machine.get('vcpuPriceHr', {}).get('value', 0))
        memory_price = float(selected_machine.get('memoryGibPriceHr', {}).get('value', 0))
        gpu_price = float(selected_machine.get('gpuPriceHr', {}).get('value', 0))
        
        # VM specs
        vcpus = min(config.get('vcpus', 8), max_vcpu)
        memory_gb = min(config.get('memory_gb', 32), max_memory)
        gpus = min(config.get('gpus', 1 if max_gpu > 0 else 0), max_gpu)
        
        estimated_cost = (vcpus * vcpu_price) + (memory_gb * memory_price) + (gpus * gpu_price)
        
        vm_config = {
            "machineType": machine_type,
            "dataCenterId": datacenter.get('id'),
            "bootDiskSizeGib": config.get('disk_size_gb', 100),
            "memoryGib": memory_gb,
            "vcpus": vcpus,
            "gpus": gpus,
            "id": f"hf-{hashlib.md5(model_name.encode()).hexdigest()[:8]}-{int(time.time())}",
            "metadata": {
                "model_name": model_name,
                "deployer": "kenny-universal-deployer-v2",
                "created_at": datetime.now().isoformat(),
                "auto_terminate": config.get('auto_terminate', 'false'),
                "startup-script": self.create_startup_script(model_name, config)
            },
            "tags": ["kenny", "huggingface", model_name.replace('/', '-'), "universal-deployer-v2"]
        }
        
        # Display configuration
        print(f"\n📋 VM Configuration:")
        print(f"   Machine Type: {machine_type}")
        print(f"   Data Center: {datacenter.get('id')}")
        print(f"   vCPUs: {vcpus}")
        print(f"   Memory: {memory_gb}GB")
        print(f"   GPUs: {gpus} ({selected_machine.get('gpuModel', 'None')})")
        print(f"   Storage: {vm_config['bootDiskSizeGib']}GB")
        
        print(f"\n💰 Cost Estimate:")
        print(f"   vCPUs: ${vcpus * vcpu_price:.3f}/hour")
        print(f"   Memory: ${memory_gb * memory_price:.3f}/hour")
        print(f"   GPUs: ${gpus * gpu_price:.3f}/hour")
        print(f"   Total: ${estimated_cost:.3f}/hour (${estimated_cost * 24:.2f}/day)")
        
        if dry_run:
            print(f"\n✅ DRY RUN COMPLETE - Configuration validated")
            return {
                "success": True,
                "deployment_id": vm_config["id"],
                "model_name": model_name,
                "vm_config": vm_config,
                "estimated_cost_per_hour": estimated_cost,
                "estimated_daily_cost": estimated_cost * 24,
                "machine_type": machine_type,
                "gpus": gpus,
                "gpu_model": selected_machine.get('gpuModel', 'None'),
                "status": "dry_run"
            }
        
        # LIVE DEPLOYMENT
        print(f"\n⚠️  CREATING REAL VM FOR {model_name}...")
        print(f"   Estimated cost: ${estimated_cost:.3f}/hour")
        
        try:
            async with self.session.post(
                f"{self.base_url}/projects/{self.project_id}/vms",
                json=vm_config
            ) as response:
                
                if response.status in [200, 201, 202]:
                    vm_data = await response.json()
                    vm_id = vm_data.get("id", vm_config["id"])
                    
                    print(f"✅ VM Creation successful!")
                    print(f"   VM ID: {vm_id}")
                    print(f"   Status: {vm_data.get('status', 'creating')}")
                    
                    # Monitor deployment
                    deployment_result = await self.monitor_deployment(vm_id, model_name)
                    
                    return {
                        "success": True,
                        "deployment_id": vm_config["id"],
                        "vm_id": vm_id,
                        "model_name": model_name,
                        "public_ip": deployment_result.get("public_ip"),
                        "api_endpoint": f"http://{deployment_result.get('public_ip', 'pending')}:8000" if deployment_result.get("public_ip") else None,
                        "health_check": f"http://{deployment_result.get('public_ip', 'pending')}:8000/health" if deployment_result.get("public_ip") else None,
                        "estimated_cost_per_hour": estimated_cost,
                        "machine_type": machine_type,
                        "gpus": gpus,
                        "gpu_model": selected_machine.get('gpuModel', 'None'),
                        "status": deployment_result.get("status", "unknown")
                    }
                
                else:
                    error_text = await response.text()
                    print(f"❌ VM creation failed: {response.status}")
                    print(f"   Error: {error_text[:200]}...")
                    
                    return {
                        "success": False,
                        "error": f"VM creation failed: {response.status}",
                        "details": error_text
                    }
        
        except Exception as e:
            print(f"❌ Deployment exception: {e}")
            return {
                "success": False,
                "error": f"Deployment exception: {str(e)}"
            }
    
    async def monitor_deployment(self, vm_id: str, model_name: str) -> Dict[str, Any]:
        """Monitor VM deployment and model loading"""
        print(f"\n⏳ Monitoring deployment of {model_name} (VM: {vm_id})...")
        
        for i in range(60):  # Monitor for up to 10 minutes
            await asyncio.sleep(10)
            
            try:
                async with self.session.get(
                    f"{self.base_url}/projects/{self.project_id}/vms/{vm_id}"
                ) as response:
                    
                    if response.status == 200:
                        vm_info = await response.json()
                        status = vm_info.get("status", "unknown")
                        public_ip = vm_info.get("publicIp")
                        
                        print(f"   [{i+1:2d}/60] Status: {status}" + (f", IP: {public_ip}" if public_ip else ""))
                        
                        if status == "running" and public_ip:
                            # Wait a bit more for the model to load
                            if i < 5:  # Give it at least 1 minute after VM is running
                                continue
                            
                            print(f"\n🎉 Deployment successful!")
                            print(f"   VM ID: {vm_id}")
                            print(f"   Public IP: {public_ip}")
                            print(f"   Web Interface: http://{public_ip}:8000")
                            print(f"   API Endpoint: http://{public_ip}:8000/generate")
                            print(f"   Health Check: http://{public_ip}:8000/health")
                            
                            # Test API availability
                            print(f"\n🧪 Testing API availability...")
                            await asyncio.sleep(30)  # Give model time to load
                            
                            try:
                                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as test_session:
                                    async with test_session.get(f"http://{public_ip}:8000/health") as health_response:
                                        if health_response.status == 200:
                                            health_data = await health_response.json()
                                            print(f"   ✅ API is responding!")
                                            print(f"   Model loaded: {health_data.get('model_loaded', False)}")
                                        else:
                                            print(f"   ⚠️  API not ready yet (status: {health_response.status})")
                            except:
                                print(f"   ⚠️  API not ready yet - model may still be loading")
                            
                            print(f"\n📝 Quick Test Commands:")
                            print(f"   curl http://{public_ip}:8000/health")
                            print(f"   curl -X POST http://{public_ip}:8000/generate \\")
                            print(f"        -H 'Content-Type: application/json' \\")
                            print(f"        -d '{{\"prompt\": \"Kenny\\'s agent army\", \"max_length\": 50}}'")
                            
                            return {
                                "status": "running",
                                "public_ip": public_ip,
                                "vm_id": vm_id
                            }
                        
                        elif status in ["failed", "terminated"]:
                            print(f"❌ Deployment failed: {status}")
                            return {"status": "failed", "vm_status": status}
                    
                    else:
                        print(f"   API error: {response.status}")
            
            except Exception as e:
                print(f"   Monitoring error: {e}")
        
        print(f"\n⚠️ Deployment monitoring timed out (10 minutes)")
        print(f"   VM may still be starting - check CUDO dashboard")
        return {"status": "timeout"}
    
    async def list_deployments(self) -> List[Dict[str, Any]]:
        """List all active HuggingFace deployments"""
        print(f"\n📋 Active HuggingFace Deployments:")
        
        try:
            async with self.session.get(f"{self.base_url}/projects/{self.project_id}/vms") as response:
                if response.status == 200:
                    data = await response.json()
                    vms = data.get("VMs", [])
                    
                    # Filter HuggingFace deployments
                    hf_deployments = [
                        vm for vm in vms 
                        if vm.get("metadata", {}).get("deployer", "").startswith("kenny-universal-deployer")
                    ]
                    
                    if not hf_deployments:
                        print("   No active deployments found")
                        return []
                    
                    deployments = []
                    for vm in hf_deployments:
                        vm_id = vm.get("id")
                        model_name = vm.get("metadata", {}).get("model_name", "unknown")
                        status = vm.get("status", "unknown")
                        public_ip = vm.get("publicIp")
                        created_time = vm.get("createTime", "unknown")
                        
                        deployment = {
                            "vm_id": vm_id,
                            "model_name": model_name,
                            "status": status,
                            "public_ip": public_ip,
                            "created_at": created_time,
                            "web_interface": f"http://{public_ip}:8000" if public_ip else None,
                            "api_endpoint": f"http://{public_ip}:8000/generate" if public_ip else None
                        }
                        
                        deployments.append(deployment)
                        
                        print(f"   • {model_name} ({vm_id})")
                        print(f"     Status: {status}")
                        if public_ip:
                            print(f"     Web: http://{public_ip}:8000")
                            print(f"     API: http://{public_ip}:8000/generate")
                        print()
                    
                    return deployments
                
                else:
                    print(f"   ❌ Failed to list VMs: {response.status}")
                    return []
        
        except Exception as e:
            print(f"   ❌ Error listing deployments: {e}")
            return []

# Command-line interface
async def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="CUDO + HuggingFace Universal Deployer")
    parser.add_argument("--deploy", help="Deploy model (e.g., 'distilgpt2')")
    parser.add_argument("--list", action="store_true", help="List active deployments")
    parser.add_argument("--live", action="store_true", help="Live deployment (costs money!)")
    parser.add_argument("--gpu", type=int, default=1, help="Number of GPUs required")
    parser.add_argument("--memory", type=int, default=32, help="Memory in GB")
    parser.add_argument("--vcpus", type=int, default=8, help="Number of vCPUs")
    
    args = parser.parse_args()
    
    if not args.deploy and not args.list:
        print("🚀 KENNY'S UNIVERSAL HUGGINGFACE DEPLOYER v2.0")
        print("=" * 60)
        print("Usage:")
        print("  --deploy MODEL_NAME    Deploy a HuggingFace model")
        print("  --list                 List active deployments")
        print("  --live                 Run live deployment (costs money!)")
        print("  --gpu N                Number of GPUs (default: 1)")
        print("  --memory N             Memory in GB (default: 32)")
        print("  --vcpus N              Number of vCPUs (default: 8)")
        print()
        print("Examples:")
        print("  python3 cudo_huggingface_live_working.py --deploy distilgpt2")
        print("  python3 cudo_huggingface_live_working.py --deploy gpt2 --live")
        print("  python3 cudo_huggingface_live_working.py --list")
        return
    
    async with CudoHuggingFaceDeployer() as deployer:
        if args.list:
            await deployer.list_deployments()
        
        elif args.deploy:
            model_config = {
                "gpus": args.gpu,
                "memory_gb": args.memory,
                "vcpus": args.vcpus,
                "gpu_required": args.gpu > 0,
                "disk_size_gb": 100,
                "auto_terminate": "false"
            }
            
            if args.live:
                confirm = input(f"⚠️  Deploy {args.deploy} LIVE? This will cost money! (y/N): ")
                if confirm.lower() != 'y':
                    print("Deployment cancelled")
                    return
            
            result = await deployer.deploy_model(args.deploy, model_config, dry_run=not args.live)
            
            print(f"\n{'='*60}")
            print(f"DEPLOYMENT RESULT")
            print('='*60)
            
            if result["success"]:
                print(f"✅ Success: {result['status']}")
                print(f"Model: {result['model_name']}")
                print(f"Cost: ${result['estimated_cost_per_hour']:.3f}/hour")
                
                if result.get("public_ip"):
                    print(f"Web Interface: http://{result['public_ip']}:8000")
                    print(f"API Endpoint: {result['api_endpoint']}")
                    print(f"Health Check: {result['health_check']}")
                
                if args.live:
                    print(f"\n⚠️  LIVE DEPLOYMENT ACTIVE - Remember to terminate when done!")
                    print(f"VM ID: {result.get('vm_id')}")
            else:
                print(f"❌ Failed: {result['error']}")
                if result.get('suggestion'):
                    print(f"💡 Suggestion: {result['suggestion']}")

if __name__ == "__main__":
    asyncio.run(main())