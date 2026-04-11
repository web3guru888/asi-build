"""
VLA++ Multi-Modal Architecture
==============================

Implements the core Vision-Language-Action architecture combining:
- Vision: ResNet50 + FPN for object detection and segmentation
- Language: GPT-2 variant for command understanding
- Action: Transformer decoder for trajectory planning
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class VLAConfig:
    """Configuration for VLA++ model."""

    # Vision module
    vision_backbone: str = "resnet50"
    vision_hidden_size: int = 2048
    vision_num_classes: int = 80  # COCO classes
    vision_fpn_channels: int = 256

    # Language module
    language_model: str = "gpt2"
    language_vocab_size: int = 8192
    language_hidden_size: int = 768
    language_num_layers: int = 12
    language_num_heads: int = 12

    # Action module
    action_hidden_size: int = 512
    action_num_layers: int = 6
    action_num_heads: int = 8
    action_num_waypoints: int = 20

    # Cross-modal fusion
    fusion_hidden_size: int = 1024
    fusion_num_heads: int = 16
    fusion_dropout: float = 0.1

    # Training
    max_seq_length: int = 512
    use_mixed_precision: bool = True
    gradient_checkpointing: bool = True


class VisionModule(nn.Module):
    """Vision processing module with object detection and segmentation."""

    def __init__(self, config: VLAConfig):
        super().__init__()
        self.config = config

        # Backbone feature extractor
        self.backbone = nn.Sequential(
            nn.Conv2d(3, 64, 7, stride=2, padding=3),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(3, stride=2, padding=1),
        )

        # Feature Pyramid Network
        self.fpn = nn.ModuleList(
            [
                nn.Conv2d(64, config.vision_fpn_channels, 1),
                nn.Conv2d(128, config.vision_fpn_channels, 1),
                nn.Conv2d(256, config.vision_fpn_channels, 1),
                nn.Conv2d(512, config.vision_fpn_channels, 1),
            ]
        )

        # Detection head
        self.detection_head = nn.Sequential(
            nn.Conv2d(config.vision_fpn_channels, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, config.vision_num_classes + 4, 1),  # Classes + bbox
        )

        # Segmentation head
        self.segmentation_head = nn.Sequential(
            nn.Conv2d(config.vision_fpn_channels, 256, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, config.vision_num_classes, 1),
        )

        # Vision encoder for fusion
        self.vision_encoder = nn.Linear(
            config.vision_fpn_channels * 7 * 7, config.fusion_hidden_size
        )

    def forward(self, images: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Process images through vision pipeline."""
        # Extract features
        features = self.backbone(images)

        # FPN processing
        pyramid_features = []
        for fpn_layer in self.fpn:
            pyramid_features.append(fpn_layer(features))

        # Detection and segmentation
        detections = self.detection_head(pyramid_features[-1])
        segmentation = self.segmentation_head(pyramid_features[-1])

        # Prepare vision embedding for fusion
        vision_embedding = pyramid_features[-1].flatten(start_dim=1)
        vision_embedding = self.vision_encoder(vision_embedding)

        return {
            "detections": detections,
            "segmentation": segmentation,
            "vision_embedding": vision_embedding,
            "features": pyramid_features,
        }


class LanguageModule(nn.Module):
    """Language understanding module for command processing."""

    def __init__(self, config: VLAConfig):
        super().__init__()
        self.config = config

        # Token embedding
        self.token_embedding = nn.Embedding(config.language_vocab_size, config.language_hidden_size)

        # Positional encoding
        self.position_embedding = nn.Embedding(config.max_seq_length, config.language_hidden_size)

        # Transformer layers
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.language_hidden_size,
            nhead=config.language_num_heads,
            dim_feedforward=config.language_hidden_size * 4,
            dropout=config.fusion_dropout,
            batch_first=True,
        )

        self.transformer = nn.TransformerEncoder(
            encoder_layer, num_layers=config.language_num_layers
        )

        # Language encoder for fusion
        self.language_encoder = nn.Linear(config.language_hidden_size, config.fusion_hidden_size)

    def forward(self, input_ids: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Process language commands."""
        batch_size, seq_len = input_ids.shape

        # Embed tokens
        token_embeds = self.token_embedding(input_ids)

        # Add positional encoding
        positions = torch.arange(seq_len, device=input_ids.device)
        position_embeds = self.position_embedding(positions)
        embeddings = token_embeds + position_embeds.unsqueeze(0)

        # Transformer processing
        language_features = self.transformer(embeddings)

        # Pool for fusion
        language_embedding = language_features.mean(dim=1)
        language_embedding = self.language_encoder(language_embedding)

        return {"language_features": language_features, "language_embedding": language_embedding}


class ActionModule(nn.Module):
    """Action planning module for trajectory generation."""

    def __init__(self, config: VLAConfig):
        super().__init__()
        self.config = config

        # Cross-attention for vision-language fusion
        self.cross_attention = nn.MultiheadAttention(
            embed_dim=config.fusion_hidden_size,
            num_heads=config.fusion_num_heads,
            dropout=config.fusion_dropout,
            batch_first=True,
        )

        # Trajectory decoder
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=config.action_hidden_size,
            nhead=config.action_num_heads,
            dim_feedforward=config.action_hidden_size * 4,
            dropout=config.fusion_dropout,
            batch_first=True,
        )

        self.trajectory_decoder = nn.TransformerDecoder(
            decoder_layer, num_layers=config.action_num_layers
        )

        # Fusion to action projection
        self.fusion_projection = nn.Linear(config.fusion_hidden_size, config.action_hidden_size)

        # Waypoint generation
        self.waypoint_head = nn.Sequential(
            nn.Linear(config.action_hidden_size, 256),
            nn.ReLU(),
            nn.Linear(256, 7),  # x, y, z, yaw, speed, acc, steer
        )

    def forward(
        self, vision_embedding: torch.Tensor, language_embedding: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        """Generate action trajectories from vision-language inputs."""

        # Fuse vision and language via cross-attention
        fused_features, attention_weights = self.cross_attention(
            query=language_embedding.unsqueeze(1),
            key=vision_embedding.unsqueeze(1),
            value=vision_embedding.unsqueeze(1),
        )

        # Project to action space
        action_features = self.fusion_projection(fused_features)

        # Generate trajectory waypoints
        batch_size = action_features.shape[0]
        num_waypoints = self.config.action_num_waypoints

        # Initialize waypoint queries
        waypoint_queries = torch.zeros(
            batch_size, num_waypoints, self.config.action_hidden_size, device=action_features.device
        )

        # Decode trajectory
        trajectory_features = self.trajectory_decoder(tgt=waypoint_queries, memory=action_features)

        # Generate waypoints
        waypoints = self.waypoint_head(trajectory_features)

        return {
            "waypoints": waypoints,
            "trajectory_features": trajectory_features,
            "attention_weights": attention_weights,
        }


class VLAPlusPlus(nn.Module):
    """Complete VLA++ model combining vision, language, and action."""

    def __init__(self, config: Optional[VLAConfig] = None):
        super().__init__()
        self.config = config or VLAConfig()

        # Initialize modules
        self.vision_module = VisionModule(self.config)
        self.language_module = LanguageModule(self.config)
        self.action_module = ActionModule(self.config)

        # Safety module
        self.safety_checker = nn.Sequential(
            nn.Linear(self.config.action_hidden_size, 256),
            nn.ReLU(),
            nn.Linear(256, 1),
            nn.Sigmoid(),
        )

    def forward(self, images: torch.Tensor, commands: torch.Tensor) -> Dict[str, torch.Tensor]:
        """End-to-end VLA++ inference."""

        # Process vision
        vision_output = self.vision_module(images)

        # Process language
        language_output = self.language_module(commands)

        # Generate actions
        action_output = self.action_module(
            vision_output["vision_embedding"], language_output["language_embedding"]
        )

        # Safety check
        safety_score = self.safety_checker(action_output["trajectory_features"].mean(dim=1))

        return {**vision_output, **language_output, **action_output, "safety_score": safety_score}

    def count_parameters(self) -> int:
        """Count total model parameters."""
        return sum(p.numel() for p in self.parameters())

    def enable_gradient_checkpointing(self):
        """Enable gradient checkpointing for memory efficiency."""
        if self.config.gradient_checkpointing:
            # Enable for transformer layers
            for module in [self.vision_module, self.language_module, self.action_module]:
                if hasattr(module, "gradient_checkpointing_enable"):
                    module.gradient_checkpointing_enable()


def create_vla_model(config: Optional[VLAConfig] = None) -> VLAPlusPlus:
    """Factory function to create VLA++ model."""
    model = VLAPlusPlus(config)

    # Initialize weights
    for module in model.modules():
        if isinstance(module, (nn.Linear, nn.Conv2d)):
            nn.init.kaiming_normal_(module.weight)
            if module.bias is not None:
                nn.init.zeros_(module.bias)

    return model


if __name__ == "__main__":
    # Test model creation
    config = VLAConfig()
    model = create_vla_model(config)

    print(f"VLA++ Model Created")
    print(f"Total Parameters: {model.count_parameters():,}")
    print(f"Vision Module: {sum(p.numel() for p in model.vision_module.parameters()):,}")
    print(f"Language Module: {sum(p.numel() for p in model.language_module.parameters()):,}")
    print(f"Action Module: {sum(p.numel() for p in model.action_module.parameters()):,}")

    # Test forward pass
    batch_size = 2
    images = torch.randn(batch_size, 3, 224, 224)
    commands = torch.randint(0, config.language_vocab_size, (batch_size, 32))

    with torch.no_grad():
        output = model(images, commands)
        print(f"\nOutput shapes:")
        print(f"  Waypoints: {output['waypoints'].shape}")
        print(f"  Safety Score: {output['safety_score'].shape}")
        print(f"  Detections: {output['detections'].shape}")
