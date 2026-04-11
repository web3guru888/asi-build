# Cudo Compute GPU Types and Pricing

## Available GPU Types via API (Current Live Pricing)

| GPU Model | Price per Hour (On-Demand) | Availability | Use Cases |
|-----------|---------------------------|--------------|-----------|
| **NVIDIA H100 SXM** | $2.60 - $3.10/hr | 2 data centers | AI training, Large language models |
| **NVIDIA H100 NVL** | $2.47/hr | 1 data center | AI inference, Training |
| **NVIDIA A800 PCIe** | $1.60/hr | 1 data center | AI training, HPC |
| **NVIDIA A100 80GB PCIe** | $1.50 - $1.70/hr | 2 data centers | Deep learning, Scientific computing |
| **NVIDIA L40S (compute)** | $0.87 - $1.15/hr | 2 data centers | AI inference, Graphics workloads |
| **NVIDIA L40S (graphics)** | $1.15/hr | 1 data center | 3D rendering, Visualization |
| **NVIDIA A40 (compute)** | $0.62/hr | 2 data centers | AI inference, Virtual workstations |
| **NVIDIA A40 (graphics)** | $0.62/hr | 2 data centers | Professional graphics, Rendering |
| **NVIDIA RTX A6000** | $0.62/hr | 1 data center | Professional visualization, AI |
| **NVIDIA RTX A5000** | $0.36/hr | 1 data center | Workstation graphics, AI development |
| **NVIDIA V100** | $0.52/hr | 1 data center | Legacy AI workloads, Training |

## Commitment Pricing Discounts

Longer commitments provide significant discounts:
- **1 Month**: ~5% discount
- **3 Months**: ~10% discount  
- **6 Months**: ~15% discount
- **12 Months**: ~23% discount
- **24 Months**: ~25% discount
- **36 Months**: ~30% discount

### Example: H100 NVL Pricing with Commitments
- On-demand: $2.47/hr
- 1 month: $2.35/hr
- 3 months: $2.22/hr
- 6 months: $2.10/hr
- 12 months: $1.90/hr
- 24 months: $1.85/hr
- 36 months: $1.73/hr

## Additional Costs

### Compute Resources
- **vCPU**: $0.0024 - $0.0049/hr per vCPU
- **Memory**: $0.0036 - $0.0049/hr per GiB
- **Storage**: $0.00011 - $0.00014/hr per GiB
- **IPv4 Address**: $0.0035/hr
- **Network Traffic**: $0.0042 - $0.0045/hr

### Data Centers
Available in multiple locations worldwide:
- Australia (Melbourne)
- Canada (Montreal) - Multiple sites
- Czech Republic (Prague)
- Norway (Hamar, Oslo)
- Serbia (Belgrade)
- Sweden (Kil, Norrköping, Stockholm)
- UK (Belfast, Basildon)
- USA (Las Vegas, Washington)

## API Access

### Authentication
```bash
curl 'https://rest.compute.cudo.org/v1/vms/machine-types' \
  -H 'Authorization: bearer YOUR_API_KEY' \
  -H 'Accept: application/json'
```

### Key Endpoints
- List machine types: `GET /v1/vms/machine-types`
- List data centers: `GET /v1/vms/data-centers`
- Create VM: `POST /v1/vms`
- List VMs: `GET /v1/vms`

## Notes
- Prices are subject to change and availability
- Some high-end GPUs (H200, B200, GB200) require custom pricing quotes
- Bare metal servers with multiple GPUs are also available
- Network bandwidth and storage costs are additional to GPU pricing
- Free tier includes some IPv4 addresses per data center

## Cost Examples

### Small AI Development Setup
- GPU: 1x RTX A5000 ($0.36/hr)
- vCPU: 8 cores ($0.04/hr)
- Memory: 32 GiB ($0.16/hr)
- Storage: 500 GiB ($0.07/hr)
- **Total: ~$0.63/hr or ~$454/month**

### Production AI Training
- GPU: 4x A100 80GB ($6.00/hr)
- vCPU: 64 cores ($0.31/hr)
- Memory: 256 GiB ($1.25/hr)
- Storage: 2000 GiB ($0.28/hr)
- **Total: ~$7.84/hr or ~$5,645/month**

### Enterprise LLM Deployment
- GPU: 8x H100 SXM ($24.80/hr)
- vCPU: 128 cores ($0.63/hr)
- Memory: 1024 GiB ($5.02/hr)
- Storage: 10000 GiB ($1.40/hr)
- **Total: ~$31.85/hr or ~$22,932/month**

---
*Last updated: January 15, 2025*
*Source: Cudo Compute REST API v1*