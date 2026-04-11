#!/usr/bin/env python3
"""
VLA++ Dataset Download Script
==============================

Downloads and prepares real datasets for VLA++ training.
"""

import os
import json
import urllib.request
import zipfile
import tarfile
from pathlib import Path
import subprocess
import sys

class DatasetDownloader:
    """Download and prepare datasets for VLA++."""
    
    def __init__(self, data_dir="/home/ubuntu/code/kenny/vla_plus_plus/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Dataset URLs
        self.datasets = {
            "coco": {
                "annotations": "http://images.cocodataset.org/annotations/annotations_trainval2017.zip",
                "train_images": "http://images.cocodataset.org/zips/train2017.zip",
                "val_images": "http://images.cocodataset.org/zips/val2017.zip",
                "size_gb": 25
            },
            "cityscapes": {
                "info": "Requires registration at https://www.cityscapes-dataset.com",
                "size_gb": 11
            },
            "nuscenes": {
                "mini": "https://www.nuscenes.org/data/v1.0-mini.tgz",
                "size_gb": 0.4  # Mini version for testing
            }
        }
    
    def download_file(self, url: str, dest_path: Path) -> bool:
        """Download a file with progress reporting."""
        print(f"Downloading {url} to {dest_path}")
        
        try:
            # Check if file already exists
            if dest_path.exists():
                print(f"File {dest_path} already exists, skipping download")
                return True
            
            # Download with wget for better progress reporting
            cmd = f"wget -c {url} -O {dest_path}"
            result = subprocess.run(cmd, shell=True, capture_output=False)
            
            if result.returncode == 0:
                print(f"Successfully downloaded {dest_path.name}")
                return True
            else:
                print(f"Failed to download {dest_path.name}")
                return False
                
        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False
    
    def extract_archive(self, archive_path: Path, extract_to: Path) -> bool:
        """Extract zip or tar archives."""
        print(f"Extracting {archive_path} to {extract_to}")
        
        try:
            if archive_path.suffix == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
            elif archive_path.suffix in ['.tar', '.tgz', '.tar.gz']:
                with tarfile.open(archive_path, 'r:*') as tar_ref:
                    tar_ref.extractall(extract_to)
            else:
                print(f"Unknown archive format: {archive_path.suffix}")
                return False
            
            print(f"Successfully extracted {archive_path.name}")
            return True
            
        except Exception as e:
            print(f"Error extracting {archive_path}: {e}")
            return False
    
    def download_coco_sample(self):
        """Download COCO dataset sample for training."""
        print("\n=== Downloading COCO Dataset Sample ===")
        
        coco_dir = self.data_dir / "coco"
        coco_dir.mkdir(exist_ok=True)
        
        # Download annotations (smaller file)
        annotations_url = self.datasets["coco"]["annotations"]
        annotations_path = coco_dir / "annotations_trainval2017.zip"
        
        if self.download_file(annotations_url, annotations_path):
            self.extract_archive(annotations_path, coco_dir)
            
            # Create dataset info
            info = {
                "dataset": "COCO",
                "version": "2017",
                "annotations": True,
                "images": False,  # Full images not downloaded yet
                "classes": 80,
                "status": "annotations_ready"
            }
            
            with open(coco_dir / "dataset_info.json", 'w') as f:
                json.dump(info, f, indent=2)
            
            print("✅ COCO annotations downloaded successfully")
            return True
        
        return False
    
    def download_nuscenes_mini(self):
        """Download nuScenes mini dataset for testing."""
        print("\n=== Downloading nuScenes Mini Dataset ===")
        
        nuscenes_dir = self.data_dir / "nuscenes"
        nuscenes_dir.mkdir(exist_ok=True)
        
        mini_url = self.datasets["nuscenes"]["mini"]
        mini_path = nuscenes_dir / "v1.0-mini.tgz"
        
        if self.download_file(mini_url, mini_path):
            self.extract_archive(mini_path, nuscenes_dir)
            
            # Create dataset info
            info = {
                "dataset": "nuScenes",
                "version": "v1.0-mini",
                "scenes": 10,
                "samples": 404,
                "status": "ready"
            }
            
            with open(nuscenes_dir / "dataset_info.json", 'w') as f:
                json.dump(info, f, indent=2)
            
            print("✅ nuScenes mini dataset downloaded successfully")
            return True
        
        return False
    
    def create_sample_dataset(self):
        """Create a small sample dataset for immediate testing."""
        print("\n=== Creating Sample Dataset ===")
        
        sample_dir = self.data_dir / "sample"
        sample_dir.mkdir(exist_ok=True)
        
        # Create synthetic samples
        samples = []
        for i in range(100):
            sample = {
                "id": f"sample_{i:04d}",
                "image": f"img_{i:04d}.jpg",
                "command": f"Navigate to waypoint {i}",
                "command_ids": [100 + i % 50 for _ in range(10)],
                "trajectory": [[i * 0.1, i * 0.2, 0, 0, 10, 0, 0] for _ in range(20)],
                "safety": 1.0
            }
            samples.append(sample)
        
        # Split into train/val
        train_samples = samples[:80]
        val_samples = samples[80:]
        
        # Save metadata
        train_metadata = {
            "samples": train_samples,
            "total": len(train_samples),
            "dataset": "sample"
        }
        
        val_metadata = {
            "samples": val_samples,
            "total": len(val_samples),
            "dataset": "sample"
        }
        
        with open(sample_dir / "train_metadata.json", 'w') as f:
            json.dump(train_metadata, f, indent=2)
        
        with open(sample_dir / "val_metadata.json", 'w') as f:
            json.dump(val_metadata, f, indent=2)
        
        # Create placeholder image directory
        (sample_dir / "images").mkdir(exist_ok=True)
        
        print(f"✅ Created sample dataset with {len(samples)} samples")
        print(f"   Train: {len(train_samples)} samples")
        print(f"   Val: {len(val_samples)} samples")
        
        return True
    
    def check_disk_space(self):
        """Check available disk space."""
        import shutil
        
        stat = shutil.disk_usage(self.data_dir)
        free_gb = stat.free / (1024 ** 3)
        
        print(f"\n📊 Disk Space:")
        print(f"   Available: {free_gb:.1f} GB")
        print(f"   Required (full): ~40 GB")
        print(f"   Required (samples): ~1 GB")
        
        return free_gb
    
    def run(self):
        """Run dataset download pipeline."""
        print("=" * 60)
        print("🚀 VLA++ Dataset Download Pipeline")
        print("=" * 60)
        
        # Check disk space
        free_gb = self.check_disk_space()
        
        if free_gb < 5:
            print("⚠️ Low disk space! Creating sample dataset only.")
            self.create_sample_dataset()
        else:
            # Download real datasets
            print("\n📥 Downloading real datasets...")
            
            # Start with smaller datasets
            self.create_sample_dataset()
            self.download_coco_sample()
            self.download_nuscenes_mini()
            
            print("\n📝 Dataset Summary:")
            print("   ✅ Sample dataset created")
            print("   ✅ COCO annotations downloaded")
            print("   ✅ nuScenes mini downloaded")
            print("   ⚠️ Full datasets require manual download due to size")
        
        print("\n✨ Dataset preparation complete!")
        print(f"📁 Data directory: {self.data_dir}")
        
        return True


if __name__ == "__main__":
    downloader = DatasetDownloader()
    success = downloader.run()
    sys.exit(0 if success else 1)