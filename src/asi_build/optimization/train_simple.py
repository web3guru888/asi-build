#!/usr/bin/env python3
"""
VLA++ Simple Training Script - Working Implementation
======================================================

A simplified but functional training script for VLA++ that actually trains.
"""

import json
import logging
import os
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleVLAModel(nn.Module):
    """Simplified VLA++ model that works."""

    def __init__(self, vocab_size=8192, hidden_size=256):
        super().__init__()

        # Vision encoder (simplified)
        self.vision_encoder = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Flatten(),
            nn.Linear(64 * 56 * 56, hidden_size),
        )

        # Language encoder
        self.language_encoder = nn.Sequential(
            nn.Embedding(vocab_size, hidden_size),
            nn.LSTM(hidden_size, hidden_size, batch_first=True),
        )

        # Fusion layer
        self.fusion = nn.Linear(hidden_size * 2, hidden_size)

        # Action decoder
        self.action_decoder = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 20 * 7),  # 20 waypoints × 7 values
        )

        # Safety checker
        self.safety_checker = nn.Sequential(
            nn.Linear(hidden_size, 64), nn.ReLU(), nn.Linear(64, 1), nn.Sigmoid()
        )

    def forward(self, images, commands):
        # Vision encoding
        vision_features = self.vision_encoder(images)

        # Language encoding
        lang_embed = self.language_encoder[0](commands)
        lstm_out, _ = self.language_encoder[1](lang_embed)
        language_features = lstm_out.mean(dim=1)

        # Fusion
        combined = torch.cat([vision_features, language_features], dim=1)
        fused = self.fusion(combined)

        # Outputs
        waypoints = self.action_decoder(fused).reshape(-1, 20, 7)
        safety = self.safety_checker(fused)

        return {"waypoints": waypoints, "safety_score": safety}


class SimpleDataset(Dataset):
    """Simple dataset for testing."""

    def __init__(self, num_samples=100):
        self.num_samples = num_samples

    def __len__(self):
        return self.num_samples

    def __getitem__(self, idx):
        return {
            "images": torch.randn(3, 224, 224),
            "commands": torch.randint(0, 8192, (32,)),
            "trajectories": torch.randn(20, 7),
            "safety_label": torch.tensor(1.0),
        }


def train_vla():
    """Main training function."""

    logger.info("Starting VLA++ Training (Simplified)")

    # Configuration
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    # Model
    model = SimpleVLAModel().to(device)
    param_count = sum(p.numel() for p in model.parameters())
    logger.info(f"Model parameters: {param_count:,}")

    # Data
    train_dataset = SimpleDataset(80)
    val_dataset = SimpleDataset(20)

    train_loader = DataLoader(train_dataset, batch_size=4, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=4, shuffle=False)

    # Training setup
    optimizer = optim.AdamW(model.parameters(), lr=1e-4)
    mse_loss = nn.MSELoss()
    bce_loss = nn.BCELoss()

    # Training loop
    epochs = 5
    logger.info(f"Training for {epochs} epochs")

    for epoch in range(1, epochs + 1):
        # Training
        model.train()
        train_losses = []

        for batch_idx, batch in enumerate(train_loader):
            batch = {k: v.to(device) for k, v in batch.items()}

            # Forward
            outputs = model(batch["images"], batch["commands"])

            # Loss
            traj_loss = mse_loss(outputs["waypoints"], batch["trajectories"])
            safety_loss = bce_loss(outputs["safety_score"].squeeze(), batch["safety_label"])
            total_loss = traj_loss + 0.1 * safety_loss

            # Backward
            optimizer.zero_grad()
            total_loss.backward()
            optimizer.step()

            train_losses.append(total_loss.item())

            if batch_idx % 5 == 0:
                logger.info(
                    f"Epoch {epoch}, Batch {batch_idx}/{len(train_loader)}, Loss: {total_loss.item():.4f}"
                )

        # Validation
        model.eval()
        val_losses = []

        with torch.no_grad():
            for batch in val_loader:
                batch = {k: v.to(device) for k, v in batch.items()}
                outputs = model(batch["images"], batch["commands"])

                traj_loss = mse_loss(outputs["waypoints"], batch["trajectories"])
                safety_loss = bce_loss(outputs["safety_score"].squeeze(), batch["safety_label"])
                total_loss = traj_loss + 0.1 * safety_loss

                val_losses.append(total_loss.item())

        avg_train_loss = sum(train_losses) / len(train_losses)
        avg_val_loss = sum(val_losses) / len(val_losses)

        logger.info(
            f"Epoch {epoch} - Train Loss: {avg_train_loss:.4f}, Val Loss: {avg_val_loss:.4f}"
        )

    # Save model
    checkpoint_dir = Path("/home/ubuntu/code/kenny/vla_plus_plus/checkpoints")
    checkpoint_dir.mkdir(exist_ok=True)

    model_path = checkpoint_dir / "vla_model.pt"
    torch.save({"model_state_dict": model.state_dict(), "param_count": param_count}, model_path)

    logger.info(f"Model saved to {model_path}")
    logger.info("Training complete!")

    return model


if __name__ == "__main__":
    model = train_vla()
    logger.info("VLA++ model training successful!")
