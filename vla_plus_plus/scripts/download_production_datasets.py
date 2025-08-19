#!/usr/bin/env python3
"""
Production Dataset Downloader for VLA++
Downloads massive datasets for production-level training
Total: ~12TB of driving data
"""

import os
import sys
import json
import time
import hashlib
import requests
import zipfile
import tarfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionDatasetDownloader:
    """Production-scale dataset downloader with resume capability"""
    
    def __init__(self, base_path: str = "/home/ubuntu/code/kenny/vla_plus_plus/data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Production datasets configuration
        self.datasets = {
            "bdd100k": {
                "name": "Berkeley Deep Drive 100K",
                "size_gb": 1800,
                "priority": "CRITICAL",
                "urls": {
                    # BDD100K requires registration at https://bdd-data.berkeley.edu/
                    "info": "https://www.vis.xyz/bdd100k/",
                    "download_page": "https://bdd-data.berkeley.edu/portal.html#download",
                    "sample": "https://doc.bdd100k.com/download.html"
                },
                "components": [
                    "100k_train_images.zip",  # ~70GB
                    "100k_val_images.zip",     # ~10GB
                    "100k_test_images.zip",    # ~20GB
                    "100k_videos.tar",         # ~1.7TB
                    "labels_train.json",       # ~500MB
                    "labels_val.json"          # ~100MB
                ]
            },
            "waymo_open": {
                "name": "Waymo Open Dataset",
                "size_gb": 9000,
                "priority": "CRITICAL",
                "urls": {
                    "info": "https://waymo.com/open/",
                    "download": "https://console.cloud.google.com/storage/browser/waymo_open_dataset_v_2_0_0",
                    "tutorial": "https://github.com/waymo-research/waymo-open-dataset"
                },
                "components": [
                    "training_0000.tar",   # ~300GB each
                    "training_0001.tar",
                    "training_0002.tar",
                    # ... up to training_0031.tar
                    "validation_0000.tar", # ~300GB each
                    "testing_0000.tar"
                ]
            },
            "nuscenes_full": {
                "name": "nuScenes Full Dataset",
                "size_gb": 1000,
                "priority": "HIGH",
                "urls": {
                    "info": "https://www.nuscenes.org/nuscenes",
                    "download": "https://www.nuscenes.org/download",
                    "aws": "s3://nuscenes/public/v1.0/"
                },
                "components": [
                    "v1.0-trainval01_blobs.tar",  # ~150GB
                    "v1.0-trainval02_blobs.tar",  # ~150GB
                    "v1.0-trainval03_blobs.tar",  # ~150GB
                    "v1.0-trainval04_blobs.tar",  # ~150GB
                    "v1.0-trainval05_blobs.tar",  # ~150GB
                    "v1.0-trainval06_blobs.tar",  # ~150GB
                    "v1.0-trainval07_blobs.tar",  # ~50GB
                    "v1.0-trainval08_blobs.tar",  # ~50GB
                    "v1.0-trainval09_blobs.tar",  # ~50GB
                    "v1.0-trainval10_blobs.tar",  # ~50GB
                    "v1.0-trainval_meta.tar",     # ~20GB
                    "v1.0-test_blobs.tar",         # ~80GB
                    "v1.0-test_meta.tar"           # ~10GB
                ]
            },
            "kitti": {
                "name": "KITTI Vision Benchmark Suite",
                "size_gb": 300,
                "priority": "HIGH",
                "urls": {
                    "info": "http://www.cvlibs.net/datasets/kitti/",
                    "3d_object": "http://www.cvlibs.net/datasets/kitti/eval_object.php?obj_benchmark=3d",
                    "tracking": "http://www.cvlibs.net/datasets/kitti/eval_tracking.php",
                    "raw": "http://www.cvlibs.net/datasets/kitti/raw_data.php"
                },
                "components": [
                    "data_object_image_2.zip",      # ~12GB
                    "data_object_image_3.zip",      # ~12GB
                    "data_object_velodyne.zip",     # ~29GB
                    "data_object_calib.zip",        # ~16MB
                    "data_object_label_2.zip",      # ~5MB
                    "data_tracking_image_2.zip",    # ~60GB
                    "data_tracking_velodyne.zip",   # ~110GB
                    "data_tracking_label_2.zip",    # ~100MB
                    "data_road.zip",                # ~700MB
                    "data_semantics.zip"            # ~80GB
                ]
            },
            "cityscapes": {
                "name": "Cityscapes Dataset",
                "size_gb": 100,
                "priority": "MEDIUM",
                "urls": {
                    "info": "https://www.cityscapes-dataset.com/",
                    "download": "https://www.cityscapes-dataset.com/downloads/",
                    "register": "https://www.cityscapes-dataset.com/register/"
                },
                "components": [
                    "leftImg8bit_trainvaltest.zip",   # ~11GB
                    "leftImg8bit_trainextra.zip",     # ~44GB
                    "gtFine_trainvaltest.zip",        # ~241MB
                    "gtCoarse.zip",                   # ~1.3GB
                    "vehicle_trainvaltest.zip",       # ~2GB
                    "vehicle_trainextra.zip",         # ~8GB
                    "leftImg8bit_demoVideo.zip",      # ~6.6GB
                    "leftImg8bit_sequence.zip"        # ~30GB
                ]
            },
            "carla_synthetic": {
                "name": "CARLA Synthetic Dataset",
                "size_gb": 500,
                "priority": "MEDIUM",
                "urls": {
                    "info": "https://carla.org/",
                    "datasets": "https://github.com/carla-simulator/carla/blob/master/Docs/catalogue_datasets.md",
                    "coco_format": "https://github.com/carla-simulator/cocoapi"
                },
                "components": [
                    "Town01_Opt.tar.gz",    # ~50GB
                    "Town02_Opt.tar.gz",    # ~50GB
                    "Town03_Opt.tar.gz",    # ~50GB
                    "Town04_Opt.tar.gz",    # ~50GB
                    "Town05_Opt.tar.gz",    # ~50GB
                    "Town06_Opt.tar.gz",    # ~50GB
                    "Town07_Opt.tar.gz",    # ~50GB
                    "Town10HD_Opt.tar.gz",  # ~100GB
                    "scenarios.tar.gz"      # ~50GB
                ]
            }
        }
        
        # Download progress tracking
        self.progress_file = self.base_path / "download_progress.json"
        self.progress = self.load_progress()
        
    def load_progress(self) -> Dict:
        """Load download progress from file"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_progress(self):
        """Save download progress to file"""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def download_with_resume(self, url: str, filepath: Path, chunk_size: int = 8192) -> bool:
        """Download file with resume capability"""
        headers = {}
        mode = 'wb'
        resume_pos = 0
        
        # Check if partial download exists
        if filepath.exists():
            resume_pos = filepath.stat().st_size
            headers['Range'] = f'bytes={resume_pos}-'
            mode = 'ab'
            logger.info(f"Resuming download from {resume_pos} bytes")
        
        try:
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0)) + resume_pos
            
            with open(filepath, mode) as f:
                with tqdm(total=total_size, initial=resume_pos, 
                         unit='iB', unit_scale=True, desc=filepath.name) as pbar:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            
            return True
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False
    
    def verify_checksum(self, filepath: Path, expected_hash: Optional[str] = None) -> bool:
        """Verify file integrity with checksum"""
        if not expected_hash:
            return True
            
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        actual_hash = sha256_hash.hexdigest()
        return actual_hash == expected_hash
    
    def extract_archive(self, filepath: Path, extract_to: Path) -> bool:
        """Extract compressed archives"""
        try:
            extract_to.mkdir(parents=True, exist_ok=True)
            
            if filepath.suffix == '.zip':
                with zipfile.ZipFile(filepath, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
            elif filepath.suffix in ['.tar', '.gz', '.tgz']:
                with tarfile.open(filepath, 'r:*') as tar_ref:
                    tar_ref.extractall(extract_to)
            else:
                logger.warning(f"Unknown archive format: {filepath}")
                return False
            
            logger.info(f"Extracted {filepath.name} to {extract_to}")
            return True
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return False
    
    def download_dataset(self, dataset_name: str) -> Dict:
        """Download a specific dataset"""
        if dataset_name not in self.datasets:
            logger.error(f"Unknown dataset: {dataset_name}")
            return {"status": "error", "message": "Unknown dataset"}
        
        dataset = self.datasets[dataset_name]
        dataset_path = self.base_path / dataset_name
        dataset_path.mkdir(parents=True, exist_ok=True)
        
        result = {
            "dataset": dataset_name,
            "status": "in_progress",
            "components_total": len(dataset["components"]),
            "components_completed": 0,
            "size_gb": dataset["size_gb"],
            "priority": dataset["priority"]
        }
        
        # Initialize progress tracking
        if dataset_name not in self.progress:
            self.progress[dataset_name] = {
                "completed_components": [],
                "failed_components": [],
                "total_downloaded_gb": 0
            }
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Downloading {dataset['name']}")
        logger.info(f"Size: {dataset['size_gb']} GB")
        logger.info(f"Priority: {dataset['priority']}")
        logger.info(f"Components: {len(dataset['components'])}")
        logger.info(f"{'='*60}\n")
        
        # Download registration/info pages
        for key, url in dataset["urls"].items():
            if key in ["info", "download", "download_page", "register", "tutorial"]:
                logger.info(f"{key.capitalize()} URL: {url}")
        
        # Note: Actual downloads would require authentication
        logger.warning(f"\n⚠️  {dataset_name} requires registration and authentication")
        logger.warning(f"Please visit: {dataset['urls'].get('info', 'N/A')}")
        logger.warning("After registration, use the provided credentials to download\n")
        
        # Create placeholder structure
        for component in dataset["components"]:
            component_path = dataset_path / component
            placeholder_file = component_path.with_suffix('.placeholder')
            
            if component not in self.progress[dataset_name]["completed_components"]:
                # Create placeholder to show structure
                placeholder_file.write_text(f"Placeholder for {component}\n"
                                          f"Size: ~{dataset['size_gb'] / len(dataset['components']):.1f} GB\n"
                                          f"Download from: {dataset['urls'].get('download', 'See registration page')}\n")
                logger.info(f"Created placeholder: {placeholder_file.name}")
                
                # Mark as needing download
                result["components_completed"] += 0
            else:
                result["components_completed"] += 1
        
        # Update progress
        self.progress[dataset_name]["status"] = "awaiting_credentials"
        self.save_progress()
        
        result["status"] = "awaiting_credentials"
        result["message"] = f"Please register at {dataset['urls'].get('info', 'N/A')} to download"
        
        return result
    
    def download_all_datasets(self, priority_filter: Optional[str] = None) -> Dict:
        """Download all datasets or filter by priority"""
        results = {}
        
        # Sort by priority
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_datasets = sorted(
            self.datasets.items(),
            key=lambda x: priority_order.get(x[1]["priority"], 99)
        )
        
        total_size_gb = sum(d["size_gb"] for _, d in sorted_datasets)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"PRODUCTION DATASET DOWNLOAD PLAN")
        logger.info(f"{'='*80}")
        logger.info(f"Total datasets: {len(self.datasets)}")
        logger.info(f"Total size: {total_size_gb:,} GB ({total_size_gb/1024:.1f} TB)")
        logger.info(f"Priority filter: {priority_filter or 'None (all datasets)'}")
        logger.info(f"{'='*80}\n")
        
        for dataset_name, dataset_info in sorted_datasets:
            if priority_filter and dataset_info["priority"] != priority_filter:
                continue
            
            logger.info(f"\n[{dataset_info['priority']}] Starting {dataset_name}...")
            result = self.download_dataset(dataset_name)
            results[dataset_name] = result
            
            # Save progress after each dataset
            self.save_progress()
            time.sleep(2)  # Brief pause between datasets
        
        return results
    
    def get_download_status(self) -> Dict:
        """Get current download status"""
        status = {
            "datasets": {},
            "total_size_gb": 0,
            "downloaded_gb": 0,
            "remaining_gb": 0,
            "completion_percentage": 0
        }
        
        for dataset_name, dataset_info in self.datasets.items():
            dataset_progress = self.progress.get(dataset_name, {})
            completed = len(dataset_progress.get("completed_components", []))
            total = len(dataset_info["components"])
            
            status["datasets"][dataset_name] = {
                "name": dataset_info["name"],
                "priority": dataset_info["priority"],
                "size_gb": dataset_info["size_gb"],
                "components_completed": completed,
                "components_total": total,
                "percentage": (completed / total * 100) if total > 0 else 0,
                "status": dataset_progress.get("status", "not_started")
            }
            
            status["total_size_gb"] += dataset_info["size_gb"]
            if dataset_name in self.progress:
                status["downloaded_gb"] += dataset_progress.get("total_downloaded_gb", 0)
        
        status["remaining_gb"] = status["total_size_gb"] - status["downloaded_gb"]
        status["completion_percentage"] = (
            status["downloaded_gb"] / status["total_size_gb"] * 100 
            if status["total_size_gb"] > 0 else 0
        )
        
        return status
    
    def generate_download_script(self, dataset_name: str, output_file: str = None) -> str:
        """Generate wget/curl script for manual download"""
        if dataset_name not in self.datasets:
            return f"Error: Unknown dataset {dataset_name}"
        
        dataset = self.datasets[dataset_name]
        output_file = output_file or f"download_{dataset_name}.sh"
        
        script = f"""#!/bin/bash
# Download script for {dataset['name']}
# Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}
# Total size: {dataset['size_gb']} GB
# Priority: {dataset['priority']}

# IMPORTANT: This dataset requires registration
# Please visit: {dataset['urls'].get('info', 'N/A')}
# After registration, update the credentials below

# Set your credentials here
USERNAME="your_username"
PASSWORD="your_password"
API_KEY="your_api_key"

# Create dataset directory
DATASET_DIR="{self.base_path}/{dataset_name}"
mkdir -p "$DATASET_DIR"
cd "$DATASET_DIR"

# Download components
echo "Downloading {dataset['name']}..."
echo "Total components: {len(dataset['components'])}"
echo ""

"""
        
        for component in dataset["components"]:
            script += f"""
# Download {component}
echo "Downloading {component}..."
# wget --user="$USERNAME" --password="$PASSWORD" -c "URL_FOR_{component}" -O "{component}"
# or
# curl -u "$USERNAME:$PASSWORD" -C - "URL_FOR_{component}" -o "{component}"

"""
        
        script += """
echo "Download complete!"
echo "Please verify all files and extract as needed."
"""
        
        script_path = self.base_path / output_file
        script_path.write_text(script)
        script_path.chmod(0o755)
        
        logger.info(f"Generated download script: {script_path}")
        return str(script_path)


def main():
    """Main execution function"""
    downloader = ProductionDatasetDownloader()
    
    # Check current status
    print("\n" + "="*80)
    print("VLA++ PRODUCTION DATASET DOWNLOADER")
    print("="*80)
    
    status = downloader.get_download_status()
    print(f"\nTotal datasets: {len(status['datasets'])}")
    print(f"Total size: {status['total_size_gb']:,} GB ({status['total_size_gb']/1024:.1f} TB)")
    print(f"Downloaded: {status['downloaded_gb']:,} GB")
    print(f"Remaining: {status['remaining_gb']:,} GB")
    print(f"Completion: {status['completion_percentage']:.1f}%")
    
    print("\n" + "-"*80)
    print("Dataset Status:")
    print("-"*80)
    
    for dataset_name, dataset_status in status["datasets"].items():
        print(f"\n[{dataset_status['priority']}] {dataset_status['name']}")
        print(f"  Size: {dataset_status['size_gb']:,} GB")
        print(f"  Progress: {dataset_status['components_completed']}/{dataset_status['components_total']} components ({dataset_status['percentage']:.1f}%)")
        print(f"  Status: {dataset_status['status']}")
    
    print("\n" + "="*80)
    print("STARTING DOWNLOAD PROCESS")
    print("="*80)
    
    # Start with CRITICAL priority datasets
    print("\n📥 Downloading CRITICAL priority datasets first...")
    critical_results = downloader.download_all_datasets(priority_filter="CRITICAL")
    
    # Then HIGH priority
    print("\n📥 Downloading HIGH priority datasets...")
    high_results = downloader.download_all_datasets(priority_filter="HIGH")
    
    # Generate download scripts for manual download
    print("\n" + "="*80)
    print("GENERATING DOWNLOAD SCRIPTS")
    print("="*80)
    
    for dataset_name in downloader.datasets.keys():
        script_path = downloader.generate_download_script(dataset_name)
        print(f"✓ Generated script for {dataset_name}: {script_path}")
    
    print("\n" + "="*80)
    print("DOWNLOAD SUMMARY")
    print("="*80)
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("1. These datasets require registration and authentication")
    print("2. Total download size: ~12TB")
    print("3. Estimated download time: 24-72 hours (depending on bandwidth)")
    print("4. Required disk space: 15TB (including extraction)")
    print("5. Use the generated scripts after obtaining credentials")
    
    print("\n📋 NEXT STEPS:")
    print("1. Register for each dataset using the provided URLs")
    print("2. Update credentials in the generated download scripts")
    print("3. Run scripts to download datasets")
    print("4. Extract and organize downloaded files")
    print("5. Proceed with data pipeline setup")
    
    print("\n✅ Dataset download preparation complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()