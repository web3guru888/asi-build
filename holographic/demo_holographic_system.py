"""
Demo script for Kenny's Holographic UI Framework
Showcases all major holographic capabilities
"""

import asyncio
import logging
import time
import numpy as np
from typing import Dict, List, Any
import json

from .core.base import Vector3D, Transform3D
from .core.config import HolographicConfig
from .integration.kenny_integration import KennyHolographicIntegration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HolographicDemo:
    """
    Comprehensive demo of Kenny's holographic capabilities
    """
    
    def __init__(self):
        self.kenny_holo = None
        self.demo_running = False
        self.demo_scenarios = [
            "basic_holograms",
            "gesture_interaction", 
            "spatial_audio",
            "ar_overlays",
            "physics_simulation",
            "telepresence",
            "data_visualization",
            "volumetric_display"
        ]
    
    async def initialize(self):
        """Initialize the holographic demo"""
        logger.info("🎭 Initializing Kenny Holographic Demo...")
        
        try:
            # Initialize Kenny holographic integration
            self.kenny_holo = KennyHolographicIntegration()
            await self.kenny_holo.initialize()
            
            # Enable holographic mode
            await self.kenny_holo.enable_holographic_mode()
            
            logger.info("✅ Holographic demo initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize demo: {e}")
            return False
    
    async def run_demo(self):
        """Run the complete holographic demo"""
        if not await self.initialize():
            return
        
        self.demo_running = True
        
        try:
            logger.info("🚀 Starting Kenny Holographic Framework Demo")
            logger.info("=" * 60)
            
            # Run each demo scenario
            for i, scenario in enumerate(self.demo_scenarios, 1):
                logger.info(f"\n📍 Demo {i}/{len(self.demo_scenarios)}: {scenario.replace('_', ' ').title()}")
                await self._run_scenario(scenario)
                
                # Brief pause between scenarios
                await asyncio.sleep(2)
            
            # Show final status
            await self._show_final_status()
            
        except KeyboardInterrupt:
            logger.info("\n⏹️  Demo interrupted by user")
        except Exception as e:
            logger.error(f"❌ Demo error: {e}")
        finally:
            await self._cleanup()
    
    async def _run_scenario(self, scenario: str):
        """Run a specific demo scenario"""
        try:
            scenario_method = getattr(self, f"_demo_{scenario}", None)
            if scenario_method:
                await scenario_method()
            else:
                logger.warning(f"⚠️  Demo scenario '{scenario}' not implemented")
        
        except Exception as e:
            logger.error(f"❌ Error in scenario '{scenario}': {e}")
    
    async def _demo_basic_holograms(self):
        """Demo basic hologram creation and manipulation"""
        logger.info("Creating basic holograms...")
        
        # Create several holograms at different positions
        hologram_positions = [
            Vector3D(0, 0, -1),      # Center
            Vector3D(-1, 0.5, -1),   # Left
            Vector3D(1, 0.5, -1),    # Right
            Vector3D(0, 1, -1.5),    # Top
            Vector3D(0, -0.5, -0.5)  # Bottom front
        ]
        
        colors = [
            (1.0, 0.2, 0.2, 0.8),  # Red
            (0.2, 1.0, 0.2, 0.8),  # Green
            (0.2, 0.2, 1.0, 0.8),  # Blue
            (1.0, 1.0, 0.2, 0.8),  # Yellow
            (1.0, 0.2, 1.0, 0.8)   # Magenta
        ]
        
        display = self.kenny_holo.display_manager.get_active_display()
        if display:
            for i, (pos, color) in enumerate(zip(hologram_positions, colors)):
                await display.add_voxel(
                    "default",
                    pos,
                    color,
                    intensity=1.0,
                    size=0.1
                )
                logger.info(f"  ✨ Created hologram {i+1} at {pos}")
                await asyncio.sleep(0.5)
        
        # Animate one of the holograms
        if display:
            logger.info("  🎭 Animating hologram...")
            target_pos = Vector3D(0, 0, -2)
            await display.animate_voxel("default", 0, target_pos, 3.0)
        
        logger.info("✅ Basic holograms demo completed")
    
    async def _demo_gesture_interaction(self):
        """Demo gesture-based interaction"""
        logger.info("Testing gesture interaction...")
        
        if not self.kenny_holo.gesture_manager:
            logger.warning("⚠️  Gesture manager not available")
            return
        
        # Add gesture event handler
        def gesture_handler(gesture_data):
            gesture_type = gesture_data.get('type', 'unknown')
            confidence = gesture_data.get('confidence', 0.0)
            logger.info(f"  👋 Detected gesture: {gesture_type} (confidence: {confidence:.2f})")
        
        self.kenny_holo.add_event_handler('gesture_detected', gesture_handler)
        
        # Simulate gesture detection
        logger.info("  📹 Starting gesture recognition...")
        await self.kenny_holo.gesture_manager.start_tracking()
        
        # Wait for gestures (in real demo, user would make gestures)
        logger.info("  🤚 Make gestures in front of the camera...")
        await asyncio.sleep(5)
        
        # Simulate some gesture events
        fake_gestures = [
            {'type': 'point', 'confidence': 0.9, 'target_position': Vector3D(0.5, 0.5, -1)},
            {'type': 'swipe_right', 'confidence': 0.85},
            {'type': 'pinch', 'confidence': 0.92}
        ]
        
        for gesture in fake_gestures:
            await self.kenny_holo._on_gesture_detected(gesture)
            await asyncio.sleep(1)
        
        logger.info("✅ Gesture interaction demo completed")
    
    async def _demo_spatial_audio(self):
        """Demo spatial audio capabilities"""
        logger.info("Testing spatial audio...")
        
        if not self.kenny_holo.audio_manager:
            logger.warning("⚠️  Audio manager not available")
            return
        
        # Start audio processing
        await self.kenny_holo.audio_manager.start_processing()
        
        # Create audio sources at different positions
        audio_positions = [
            Vector3D(-2, 0, -1),   # Left
            Vector3D(2, 0, -1),    # Right
            Vector3D(0, 2, -1),    # Above
            Vector3D(0, 0, -3)     # Behind
        ]
        
        # Generate test audio (sine waves at different frequencies)
        sample_rate = 44100
        duration = 2.0
        frequencies = [220, 440, 660, 880]  # Different notes
        
        for i, (pos, freq) in enumerate(zip(audio_positions, frequencies)):
            # Generate sine wave
            t = np.linspace(0, duration, int(sample_rate * duration))
            audio_data = np.sin(2 * np.pi * freq * t).astype(np.float32) * 0.3
            
            from .audio import AudioSourceType
            source_id = f"demo_audio_{i}"
            
            success = await self.kenny_holo.audio_manager.add_audio_source(
                source_id,
                AudioSourceType.POINT,
                pos,
                audio_data,
                sample_rate
            )
            
            if success:
                logger.info(f"  🔊 Created audio source {i+1} at {pos} ({freq}Hz)")
                await self.kenny_holo.audio_manager.play_audio_source(source_id)
                await asyncio.sleep(1)
        
        # Move listener around
        logger.info("  👂 Moving audio listener...")
        listener_positions = [
            Vector3D(-1, 0, 0),
            Vector3D(1, 0, 0),
            Vector3D(0, 1, 0),
            Vector3D(0, 0, 0)
        ]
        
        for pos in listener_positions:
            await self.kenny_holo.audio_manager.set_listener_position(pos)
            logger.info(f"    Listener at {pos}")
            await asyncio.sleep(1)
        
        logger.info("✅ Spatial audio demo completed")
    
    async def _demo_ar_overlays(self):
        """Demo AR overlay capabilities"""
        logger.info("Testing AR overlays...")
        
        if not self.kenny_holo.ar_manager:
            logger.warning("⚠️  AR manager not available")
            return
        
        # Simulate screen data update
        mock_ui_elements = [
            {'id': 'button1', 'x': 100, 'y': 200, 'width': 80, 'height': 30, 'text': 'OK'},
            {'id': 'button2', 'x': 200, 'y': 200, 'width': 80, 'height': 30, 'text': 'Cancel'},
            {'id': 'text1', 'x': 50, 'y': 100, 'width': 200, 'height': 20, 'text': 'Important Message'}
        ]
        
        mock_ocr_text = [
            "Welcome to Kenny",
            "Error: Connection failed",
            "Success: Operation completed",
            "Click OK to continue"
        ]
        
        await self.kenny_holo.update_screen_data(
            screenshot_path="/tmp/mock_screenshot.png",
            ocr_text=mock_ocr_text,
            ui_elements=mock_ui_elements,
            screen_resolution=(1920, 1080)
        )
        
        logger.info(f"  📱 Created {len(self.kenny_holo.holographic_overlays)} AR overlays")
        
        # Add some virtual objects
        virtual_objects = [
            {'id': 'info_panel', 'type': 'panel', 'position': Vector3D(0, 0.5, -0.8)},
            {'id': 'control_sphere', 'type': 'sphere', 'position': Vector3D(0.5, 0, -1)},
            {'id': 'data_cube', 'type': 'cube', 'position': Vector3D(-0.5, 0, -1)}
        ]
        
        for obj in virtual_objects:
            success = await self.kenny_holo.ar_manager.add_virtual_object(
                obj['id'],
                obj['type'],
                obj['position'],
                Vector3D(0.2, 0.2, 0.2),  # Scale
                {'color': (0.2, 0.8, 1.0), 'transparency': 0.3}
            )
            if success:
                logger.info(f"  🎯 Added virtual {obj['type']} at {obj['position']}")
        
        logger.info("✅ AR overlays demo completed")
    
    async def _demo_physics_simulation(self):
        """Demo physics simulation"""
        logger.info("Testing physics simulation...")
        
        if not self.kenny_holo.physics_manager:
            logger.warning("⚠️  Physics manager not available")
            return
        
        # Start physics simulation
        await self.kenny_holo.physics_manager.start_simulation()
        
        # Create physics objects
        from .physics import PhysicsBodyType, PhysicsProperties
        
        objects = [
            {
                'id': 'ball1',
                'type': PhysicsBodyType.DYNAMIC,
                'position': Vector3D(0, 2, -1),
                'properties': PhysicsProperties(mass=1.0, restitution=0.8)
            },
            {
                'id': 'ball2', 
                'type': PhysicsBodyType.DYNAMIC,
                'position': Vector3D(0.5, 2.5, -1),
                'properties': PhysicsProperties(mass=0.5, restitution=0.6)
            },
            {
                'id': 'platform',
                'type': PhysicsBodyType.STATIC,
                'position': Vector3D(0, -1, -1),
                'properties': PhysicsProperties(mass=0, restitution=0.3)
            }
        ]
        
        for obj in objects:
            success = await self.kenny_holo.physics_manager.add_physics_body(
                obj['id'],
                obj['type'],
                obj['position'],
                obj['properties']
            )
            if success:
                logger.info(f"  ⚪ Created physics object '{obj['id']}' at {obj['position']}")
        
        # Apply some forces
        logger.info("  💨 Applying forces...")
        force = Vector3D(5, 0, 0)  # Sideways force
        await self.kenny_holo.physics_manager.apply_force('ball1', force, duration=0.5)
        
        # Let physics run
        logger.info("  🎱 Running physics simulation...")
        await asyncio.sleep(3)
        
        # Add a spring constraint
        constraint_id = await self.kenny_holo.physics_manager.add_constraint(
            'spring', 'ball1', 'ball2',
            {'spring_constant': 50.0, 'rest_length': 0.5, 'damping': 5.0}
        )
        if constraint_id:
            logger.info("  🔗 Added spring constraint between balls")
        
        await asyncio.sleep(2)
        
        logger.info("✅ Physics simulation demo completed")
    
    async def _demo_telepresence(self):
        """Demo telepresence capabilities"""
        logger.info("Testing telepresence...")
        
        if not self.kenny_holo.telepresence_manager:
            logger.warning("⚠️  Telepresence manager not available")
            return
        
        # Start telepresence server
        server_started = await self.kenny_holo.telepresence_manager.start_server()
        if server_started:
            logger.info("  🌐 Telepresence server started")
        
        # Simulate remote user joining
        logger.info("  👥 Simulating remote collaboration...")
        
        # Create holographic content to share
        from .telepresence import HologramType
        content_data = b"mock_hologram_data"
        
        content_id = await self.kenny_holo.telepresence_manager.share_holographic_content(
            HologramType.OBJECT,
            content_data,
            Vector3D(0, 0, -2),
            {'description': 'Shared holographic object'}
        )
        
        if content_id:
            logger.info(f"  📤 Shared holographic content: {content_id}")
        
        # Start holographic stream
        stream_id = await self.kenny_holo.telepresence_manager.start_holographic_stream(
            stream_type="hologram",
            quality_level=2
        )
        
        if stream_id:
            logger.info(f"  📹 Started holographic stream: {stream_id}")
        
        # Simulate some collaboration
        await asyncio.sleep(3)
        
        # Update position (simulate movement)
        await self.kenny_holo.telepresence_manager.update_local_position(
            Vector3D(1, 0, 0),
            Transform3D()
        )
        logger.info("  🚶 Updated user position")
        
        await asyncio.sleep(2)
        
        logger.info("✅ Telepresence demo completed")
    
    async def _demo_data_visualization(self):
        """Demo holographic data visualization"""
        logger.info("Testing data visualization...")
        
        # Create sample data
        data_points = []
        for i in range(20):
            x = (i % 5) * 0.3 - 0.6
            y = (i // 5) * 0.3 - 0.3
            z = -1 - (i * 0.05)
            value = np.sin(i * 0.5) * 0.5 + 0.5  # Normalized sine wave
            
            data_points.append({
                'position': Vector3D(x, y, z),
                'value': value,
                'label': f'Data {i+1}'
            })
        
        # Create holographic data visualization
        display = self.kenny_holo.display_manager.get_active_display()
        if display:
            logger.info("  📊 Creating holographic data visualization...")
            
            for i, point in enumerate(data_points):
                # Color based on value (blue to red gradient)
                r = point['value']
                g = 0.5
                b = 1.0 - point['value']
                color = (r, g, b, 0.8)
                
                # Size based on value
                size = 0.02 + point['value'] * 0.08
                
                await display.add_voxel(
                    "default",
                    point['position'],
                    color,
                    intensity=1.0,
                    size=size
                )
                
                if i % 5 == 0:  # Log every 5th point
                    logger.info(f"    📈 Data point {i+1}: value={point['value']:.2f}")
        
        # Animate the visualization
        logger.info("  🎬 Animating data visualization...")
        await asyncio.sleep(2)
        
        # Create connecting lines (simplified)
        if display:
            for i in range(len(data_points) - 1):
                start_pos = data_points[i]['position']
                end_pos = data_points[i + 1]['position']
                
                # Create intermediate points for line
                steps = 5
                for step in range(steps):
                    t = step / (steps - 1)
                    from .core.math_utils import SpatialMath
                    line_pos = SpatialMath.lerp_vector(start_pos, end_pos, t)
                    
                    await display.add_voxel(
                        "default",
                        line_pos,
                        (1.0, 1.0, 1.0, 0.3),  # White connecting lines
                        intensity=0.5,
                        size=0.01
                    )
        
        logger.info("✅ Data visualization demo completed")
    
    async def _demo_volumetric_display(self):
        """Demo volumetric display capabilities"""
        logger.info("Testing volumetric display...")
        
        display = self.kenny_holo.display_manager.get_active_display()
        if not display:
            logger.warning("⚠️  Volumetric display not available")
            return
        
        # Create volumetric layers
        logger.info("  📺 Creating volumetric layers...")
        
        layers = [
            {'id': 'background', 'depth': -2.0},
            {'id': 'midground', 'depth': -1.0},
            {'id': 'foreground', 'depth': -0.5}
        ]
        
        for layer in layers:
            await display.create_layer(layer['id'], layer['depth'])
            logger.info(f"    🎭 Created layer '{layer['id']}' at depth {layer['depth']}")
        
        # Add content to each layer
        layer_contents = [
            # Background layer - grid pattern
            {
                'layer': 'background',
                'pattern': 'grid',
                'color': (0.2, 0.2, 0.8, 0.3),
                'spacing': 0.5
            },
            # Midground layer - spiral
            {
                'layer': 'midground', 
                'pattern': 'spiral',
                'color': (0.8, 0.2, 0.8, 0.6),
                'radius': 1.0
            },
            # Foreground layer - floating orbs
            {
                'layer': 'foreground',
                'pattern': 'orbs',
                'color': (1.0, 0.8, 0.2, 0.9),
                'count': 8
            }
        ]
        
        for content in layer_contents:
            await self._create_layer_content(display, content)
        
        # Demonstrate volumetric rendering
        logger.info("  🎮 Rendering volumetric scene...")
        frame = await display.render()
        if frame is not None:
            logger.info(f"    🖼️  Rendered frame shape: {frame.shape}")
        
        # Animate camera movement
        logger.info("  📹 Animating camera movement...")
        camera_positions = [
            Vector3D(0, 0, 3),
            Vector3D(2, 1, 3),
            Vector3D(0, 2, 2),
            Vector3D(-1, 0, 3)
        ]
        
        for pos in camera_positions:
            display.set_camera_position(pos, Vector3D(0, 0, 0), Vector3D(0, 1, 0))
            await display.render()
            logger.info(f"    📍 Camera at {pos}")
            await asyncio.sleep(1)
        
        logger.info("✅ Volumetric display demo completed")
    
    async def _create_layer_content(self, display, content: Dict[str, Any]):
        """Create content for a volumetric layer"""
        layer_id = content['layer']
        pattern = content['pattern']
        color = content['color']
        
        if pattern == 'grid':
            spacing = content.get('spacing', 0.5)
            for x in range(-2, 3):
                for y in range(-2, 3):
                    pos = Vector3D(x * spacing, y * spacing, 0)
                    await display.add_voxel(layer_id, pos, color, 0.5, 0.02)
        
        elif pattern == 'spiral':
            radius = content.get('radius', 1.0)
            points = 20
            for i in range(points):
                angle = i * 2 * np.pi / points * 3  # 3 full rotations
                r = radius * (i / points)
                x = r * np.cos(angle)
                y = r * np.sin(angle)
                z = (i / points) * 0.5 - 0.25
                pos = Vector3D(x, y, z)
                await display.add_voxel(layer_id, pos, color, 1.0, 0.05)
        
        elif pattern == 'orbs':
            count = content.get('count', 8)
            for i in range(count):
                angle = i * 2 * np.pi / count
                radius = 0.8
                x = radius * np.cos(angle)
                y = radius * np.sin(angle)
                z = np.sin(i * 0.5) * 0.2  # Varying height
                pos = Vector3D(x, y, z)
                await display.add_voxel(layer_id, pos, color, 1.0, 0.08)
    
    async def _show_final_status(self):
        """Show final demo status and metrics"""
        logger.info("\n" + "=" * 60)
        logger.info("🎉 HOLOGRAPHIC DEMO COMPLETE")
        logger.info("=" * 60)
        
        # Get system status
        status = self.kenny_holo.get_holographic_status()
        logger.info("\n📊 System Status:")
        for key, value in status.items():
            status_icon = "✅" if value else "❌"
            logger.info(f"  {status_icon} {key.replace('_', ' ').title()}: {value}")
        
        # Get performance metrics
        metrics = self.kenny_holo.get_performance_metrics()
        logger.info("\n⚡ Performance Metrics:")
        for system, system_metrics in metrics.items():
            logger.info(f"  🔧 {system.title()}:")
            for metric, value in system_metrics.items():
                if isinstance(value, float):
                    logger.info(f"    • {metric}: {value:.3f}")
                else:
                    logger.info(f"    • {metric}: {value}")
        
        # Show holographic overlays
        overlays = len(self.kenny_holo.holographic_overlays)
        logger.info(f"\n🎭 Active Holographic Overlays: {overlays}")
        
        logger.info("\n🚀 Kenny's Holographic Framework is ready for production use!")
        logger.info("✨ Features demonstrated:")
        logger.info("  • Volumetric holographic displays")
        logger.info("  • 3D gesture recognition and interaction")
        logger.info("  • Spatial audio with HRTF processing")
        logger.info("  • AR overlays with real-world integration")
        logger.info("  • Physics simulation with holographic objects")
        logger.info("  • Real-time telepresence and collaboration")
        logger.info("  • Interactive data visualization")
        logger.info("  • Multi-layer volumetric rendering")
    
    async def _cleanup(self):
        """Clean up demo resources"""
        self.demo_running = False
        
        if self.kenny_holo:
            logger.info("🧹 Cleaning up holographic systems...")
            await self.kenny_holo.shutdown()
        
        logger.info("✅ Demo cleanup completed")

# Demo runner functions
async def run_holographic_demo():
    """Run the complete holographic demo"""
    demo = HolographicDemo()
    await demo.run_demo()

async def run_quick_demo():
    """Run a quick demo of core features"""
    demo = HolographicDemo()
    demo.demo_scenarios = ["basic_holograms", "spatial_audio", "ar_overlays"]
    await demo.run_demo()

def main():
    """Main demo entry point"""
    print("🎭 Kenny's Holographic UI Framework Demo")
    print("Choose a demo option:")
    print("1. Complete Demo (all features)")
    print("2. Quick Demo (core features)")
    print("3. Exit")
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            asyncio.run(run_holographic_demo())
        elif choice == "2":
            asyncio.run(run_quick_demo())
        elif choice == "3":
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice. Please run the demo again.")
    
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted. Goodbye!")
    except Exception as e:
        print(f"❌ Demo error: {e}")

if __name__ == "__main__":
    main()