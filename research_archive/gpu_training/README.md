# GPU Training Research

This directory contains research files and scripts related to GPU training infrastructure, cost optimization, and cloud computing solutions for Kenny AGI.

## Files

- `vla_gpu_training_research.json` - Comprehensive GPU training research findings
- `vla_cudo_gpu_comprehensive_research.json` - Cudo Compute specific research and recommendations
- `research_cudo_gpu_training.py` - Cudo Compute research automation script
- `direct_cudo_research.py` - Direct Cudo API research and testing

## Research Focus

### GPU Requirements Analysis
- Minimum, recommended, and optimal GPU configurations
- Cost-performance analysis across different providers
- Training time estimates for various model sizes

### Cloud Provider Evaluation
- Cudo Compute cost analysis (30-70% cheaper than major providers)
- AWS, GCP, Azure comparison
- Spot instance availability and pricing

### Optimization Strategies
- Gradient checkpointing for memory reduction
- Mixed precision training (BF16) for 2x speedup
- LoRA for efficient fine-tuning
- Knowledge distillation techniques

### Cost Projections
- Development: $0.50-1.00/hour (RTX 3090 spot)
- Training: $8-12/hour (4x A100 cluster)
- Production: $30-50/hour (8x H100 cluster)

## Usage

Run research scripts to gather current pricing and availability data:

```bash
python research_cudo_gpu_training.py
python direct_cudo_research.py
```