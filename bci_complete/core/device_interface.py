"""
BCI Device Interface - Hardware abstraction layer

Provides unified interface for various BCI devices (EEG, EMG, fNIRS, etc.)
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
import threading
import queue
import time
from datetime import datetime

from .config import BCIConfig


@dataclass
class DeviceInfo:
    """Information about connected BCI device"""
    device_id: str
    device_type: str
    manufacturer: str
    model: str
    serial_number: str
    firmware_version: str
    sampling_rate: float
    channels: List[str]
    impedances: Dict[str, float]
    battery_level: Optional[float] = None
    connection_quality: float = 1.0


@dataclass
class DataPacket:
    """Single data packet from BCI device"""
    timestamp: float
    sample_number: int
    data: np.ndarray  # Shape: (n_channels, n_samples)
    trigger_events: List[Dict[str, Any]]
    device_status: Dict[str, Any]


class BCIDevice(ABC):
    """Abstract base class for BCI devices"""
    
    @abstractmethod
    async def connect(self, **kwargs) -> bool:
        """Connect to the device"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the device"""
        pass
    
    @abstractmethod
    def read_data(self) -> Optional[DataPacket]:
        """Read data from device"""
        pass
    
    @abstractmethod
    def get_device_info(self) -> DeviceInfo:
        """Get device information"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if device is connected"""
        pass
    
    @abstractmethod
    def start_acquisition(self) -> bool:
        """Start data acquisition"""
        pass
    
    @abstractmethod
    def stop_acquisition(self) -> bool:
        """Stop data acquisition"""
        pass


class SimulatedEEGDevice(BCIDevice):
    """Simulated EEG device for testing and development"""
    
    def __init__(self, config: BCIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.connected = False
        self.acquiring = False
        self.sample_counter = 0
        
        # Simulation parameters
        self.sampling_rate = config.device.sampling_rate
        self.channels = config.device.channels
        self.n_channels = len(self.channels)
        
        # Data generation
        self.noise_level = 10.0  # μV
        self.signal_amplitude = 50.0  # μV
        self.alpha_freq = 10.0  # Hz
        self.beta_freq = 20.0  # Hz
        
        # Trigger simulation
        self.trigger_probability = 0.01  # 1% chance per sample
        
        self.logger.info("Simulated EEG device initialized")
    
    async def connect(self, **kwargs) -> bool:
        """Connect to simulated device"""
        try:
            await asyncio.sleep(0.1)  # Simulate connection delay
            self.connected = True
            self.logger.info("Connected to simulated EEG device")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from simulated device"""
        try:
            self.acquiring = False
            await asyncio.sleep(0.1)
            self.connected = False
            self.logger.info("Disconnected from simulated EEG device")
            return True
        except Exception as e:
            self.logger.error(f"Failed to disconnect: {e}")
            return False
    
    def read_data(self) -> Optional[DataPacket]:
        """Generate simulated EEG data"""
        if not self.connected or not self.acquiring:
            return None
        
        try:
            # Generate time vector for one sample
            n_samples = 1
            t = np.arange(n_samples) / self.sampling_rate + self.sample_counter / self.sampling_rate
            
            # Generate simulated EEG signals
            data = np.zeros((self.n_channels, n_samples))
            
            for ch_idx, channel in enumerate(self.channels):
                # Base noise
                noise = np.random.normal(0, self.noise_level, n_samples)
                
                # Alpha rhythm (more prominent in occipital channels)
                alpha_amplitude = self.signal_amplitude
                if channel in ['O1', 'O2', 'Oz']:
                    alpha_amplitude *= 2
                alpha_signal = alpha_amplitude * np.sin(2 * np.pi * self.alpha_freq * t)
                
                # Beta rhythm (more prominent in central channels)
                beta_amplitude = self.signal_amplitude * 0.5
                if channel in ['C3', 'C4', 'Cz']:
                    beta_amplitude *= 1.5
                beta_signal = beta_amplitude * np.sin(2 * np.pi * self.beta_freq * t)
                
                # Combine signals
                data[ch_idx, :] = noise + alpha_signal + beta_signal
            
            # Generate triggers
            trigger_events = []
            if np.random.random() < self.trigger_probability:
                trigger_events.append({
                    'code': np.random.randint(1, 5),
                    'timestamp': time.time(),
                    'description': 'Simulated trigger'
                })
            
            # Create data packet
            packet = DataPacket(
                timestamp=time.time(),
                sample_number=self.sample_counter,
                data=data,
                trigger_events=trigger_events,
                device_status={'temperature': 25.0, 'status': 'ok'}
            )
            
            self.sample_counter += 1
            return packet
            
        except Exception as e:
            self.logger.error(f"Error reading simulated data: {e}")
            return None
    
    def get_device_info(self) -> DeviceInfo:
        """Get simulated device information"""
        # Simulate impedances
        impedances = {}
        for channel in self.channels:
            impedances[channel] = np.random.uniform(1.0, 10.0)  # kOhms
        
        return DeviceInfo(
            device_id="SIM001",
            device_type="eeg",
            manufacturer="SimulationCorp",
            model="SimEEG-64",
            serial_number="SIM123456789",
            firmware_version="1.0.0",
            sampling_rate=self.sampling_rate,
            channels=self.channels,
            impedances=impedances,
            battery_level=75.0,
            connection_quality=0.95
        )
    
    def is_connected(self) -> bool:
        """Check if simulated device is connected"""
        return self.connected
    
    def start_acquisition(self) -> bool:
        """Start simulated data acquisition"""
        if not self.connected:
            return False
        
        self.acquiring = True
        self.sample_counter = 0
        self.logger.info("Started simulated data acquisition")
        return True
    
    def stop_acquisition(self) -> bool:
        """Stop simulated data acquisition"""
        self.acquiring = False
        self.logger.info("Stopped simulated data acquisition")
        return True


class OpenBCIDevice(BCIDevice):
    """OpenBCI device interface"""
    
    def __init__(self, config: BCIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.connected = False
        self.acquiring = False
        
        # OpenBCI-specific parameters
        self.board = None
        self.board_id = None
        
        try:
            # Try to import OpenBCI library
            import brainflow
            from brainflow import BoardShim, BrainFlowInputParams
            
            self.brainflow = brainflow
            self.BoardShim = BoardShim
            self.BrainFlowInputParams = BrainFlowInputParams
            
            self.logger.info("OpenBCI device interface initialized")
            
        except ImportError:
            self.logger.warning("BrainFlow library not available - OpenBCI features disabled")
            self.brainflow = None
    
    async def connect(self, port: str = "/dev/ttyUSB0", board_id: int = 0) -> bool:
        """Connect to OpenBCI device"""
        if self.brainflow is None:
            self.logger.error("BrainFlow library not available")
            return False
        
        try:
            # Setup board parameters
            params = self.BrainFlowInputParams()
            params.serial_port = port
            
            self.board_id = board_id
            self.board = self.BoardShim(board_id, params)
            
            # Connect
            self.board.prepare_session()
            self.connected = True
            
            self.logger.info(f"Connected to OpenBCI device (board_id: {board_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to OpenBCI device: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from OpenBCI device"""
        try:
            if self.board is not None:
                if self.acquiring:
                    self.stop_acquisition()
                
                self.board.release_session()
                self.board = None
            
            self.connected = False
            self.logger.info("Disconnected from OpenBCI device")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to disconnect from OpenBCI device: {e}")
            return False
    
    def read_data(self) -> Optional[DataPacket]:
        """Read data from OpenBCI device"""
        if not self.connected or not self.acquiring or self.board is None:
            return None
        
        try:
            # Get available data
            data = self.board.get_current_board_data(1)  # Get 1 sample
            
            if data.shape[1] == 0:
                return None
            
            # Extract EEG channels
            eeg_channels = self.BoardShim.get_eeg_channels(self.board_id)
            eeg_data = data[eeg_channels, :]
            
            # Extract timestamp
            timestamp_channel = self.BoardShim.get_timestamp_channel(self.board_id)
            timestamp = data[timestamp_channel, 0]
            
            # Extract sample number
            sample_num_channel = self.BoardShim.get_package_num_channel(self.board_id)
            sample_number = int(data[sample_num_channel, 0])
            
            # Create data packet
            packet = DataPacket(
                timestamp=timestamp,
                sample_number=sample_number,
                data=eeg_data,
                trigger_events=[],  # Would need additional parsing
                device_status={'status': 'ok'}
            )
            
            return packet
            
        except Exception as e:
            self.logger.error(f"Error reading OpenBCI data: {e}")
            return None
    
    def get_device_info(self) -> DeviceInfo:
        """Get OpenBCI device information"""
        if self.board is None:
            raise RuntimeError("Device not connected")
        
        # Get board description
        board_desc = self.BoardShim.get_board_descr(self.board_id)
        
        return DeviceInfo(
            device_id=f"OpenBCI_{self.board_id}",
            device_type="eeg",
            manufacturer="OpenBCI",
            model=board_desc.get('name', 'Unknown'),
            serial_number="Unknown",
            firmware_version="Unknown",
            sampling_rate=float(board_desc.get('sampling_rate', 250)),
            channels=[f"Ch{i+1}" for i in range(board_desc.get('num_rows', 8))],
            impedances={}
        )
    
    def is_connected(self) -> bool:
        """Check if OpenBCI device is connected"""
        return self.connected and self.board is not None
    
    def start_acquisition(self) -> bool:
        """Start OpenBCI data acquisition"""
        if not self.connected or self.board is None:
            return False
        
        try:
            self.board.start_stream()
            self.acquiring = True
            self.logger.info("Started OpenBCI data acquisition")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start OpenBCI acquisition: {e}")
            return False
    
    def stop_acquisition(self) -> bool:
        """Stop OpenBCI data acquisition"""
        if not self.acquiring or self.board is None:
            return False
        
        try:
            self.board.stop_stream()
            self.acquiring = False
            self.logger.info("Stopped OpenBCI data acquisition")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop OpenBCI acquisition: {e}")
            return False


class DeviceInterface:
    """
    Main device interface for BCI systems
    
    Manages multiple device types and provides unified access
    """
    
    def __init__(self, config: BCIConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Device registry
        self.devices: Dict[str, BCIDevice] = {
            'simulated_eeg': SimulatedEEGDevice(config),
            'openbci': OpenBCIDevice(config)
        }
        
        # Current active device
        self.active_device: Optional[BCIDevice] = None
        self.device_type: Optional[str] = None
        
        # Data streaming
        self.streaming = False
        self.data_queue = queue.Queue(maxsize=1000)
        self.streaming_thread: Optional[threading.Thread] = None
        
        # Callbacks
        self.data_callbacks: List[Callable] = []
        
        self.logger.info("Device Interface initialized")
    
    async def connect(self, device_type: str, **kwargs) -> bool:
        """Connect to specified device type"""
        if device_type not in self.devices:
            self.logger.error(f"Unknown device type: {device_type}")
            return False
        
        try:
            device = self.devices[device_type]
            success = await device.connect(**kwargs)
            
            if success:
                self.active_device = device
                self.device_type = device_type
                self.logger.info(f"Connected to {device_type}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to {device_type}: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from active device"""
        if self.active_device is None:
            return True
        
        try:
            # Stop streaming if active
            if self.streaming:
                self.stop_streaming()
            
            # Disconnect device
            success = await self.active_device.disconnect()
            
            if success:
                self.active_device = None
                self.device_type = None
                self.logger.info("Device disconnected")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to disconnect device: {e}")
            return False
    
    def start_streaming(self) -> bool:
        """Start data streaming from active device"""
        if self.active_device is None or not self.active_device.is_connected():
            self.logger.error("No device connected")
            return False
        
        if self.streaming:
            return True
        
        try:
            # Start device acquisition
            if not self.active_device.start_acquisition():
                return False
            
            # Start streaming thread
            self.streaming = True
            self.streaming_thread = threading.Thread(
                target=self._streaming_loop,
                daemon=True
            )
            self.streaming_thread.start()
            
            self.logger.info("Data streaming started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start streaming: {e}")
            return False
    
    def stop_streaming(self) -> bool:
        """Stop data streaming"""
        if not self.streaming:
            return True
        
        try:
            # Stop streaming
            self.streaming = False
            
            # Stop device acquisition
            if self.active_device is not None:
                self.active_device.stop_acquisition()
            
            # Wait for thread to finish
            if self.streaming_thread is not None:
                self.streaming_thread.join(timeout=5.0)
            
            self.logger.info("Data streaming stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop streaming: {e}")
            return False
    
    def _streaming_loop(self):
        """Main streaming loop"""
        while self.streaming and self.active_device is not None:
            try:
                # Read data from device
                packet = self.active_device.read_data()
                
                if packet is not None:
                    # Add to queue
                    try:
                        self.data_queue.put_nowait(packet)
                    except queue.Full:
                        # Remove oldest packet if queue is full
                        try:
                            self.data_queue.get_nowait()
                            self.data_queue.put_nowait(packet)
                        except queue.Empty:
                            pass
                    
                    # Notify callbacks
                    for callback in self.data_callbacks:
                        try:
                            callback(packet)
                        except Exception as e:
                            self.logger.error(f"Callback error: {e}")
                
                # Small delay to prevent CPU overload
                time.sleep(0.001)
                
            except Exception as e:
                self.logger.error(f"Streaming loop error: {e}")
                time.sleep(0.1)
    
    def read_data(self) -> Optional[np.ndarray]:
        """Read latest data from queue"""
        try:
            packet = self.data_queue.get_nowait()
            return packet.data
        except queue.Empty:
            return None
    
    def get_data_packet(self) -> Optional[DataPacket]:
        """Get latest data packet from queue"""
        try:
            return self.data_queue.get_nowait()
        except queue.Empty:
            return None
    
    async def get_device_info(self) -> Optional[DeviceInfo]:
        """Get information about active device"""
        if self.active_device is None:
            return None
        
        try:
            return self.active_device.get_device_info()
        except Exception as e:
            self.logger.error(f"Failed to get device info: {e}")
            return None
    
    def is_connected(self) -> bool:
        """Check if any device is connected"""
        return self.active_device is not None and self.active_device.is_connected()
    
    def is_streaming(self) -> bool:
        """Check if data streaming is active"""
        return self.streaming
    
    def add_data_callback(self, callback: Callable):
        """Add callback for real-time data"""
        self.data_callbacks.append(callback)
    
    def remove_data_callback(self, callback: Callable):
        """Remove data callback"""
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
    
    def get_available_devices(self) -> List[str]:
        """Get list of available device types"""
        return list(self.devices.keys())
    
    def get_status(self) -> Dict[str, Any]:
        """Get interface status"""
        status = {
            'connected': self.is_connected(),
            'streaming': self.is_streaming(),
            'active_device': self.device_type,
            'available_devices': self.get_available_devices(),
            'queue_size': self.data_queue.qsize()
        }
        
        if self.active_device is not None:
            try:
                device_info = self.active_device.get_device_info()
                status['device_info'] = {
                    'sampling_rate': device_info.sampling_rate,
                    'channels': len(device_info.channels),
                    'battery_level': device_info.battery_level,
                    'connection_quality': device_info.connection_quality
                }
            except Exception:
                pass
        
        return status
    
    async def cleanup(self):
        """Cleanup device interface"""
        if self.streaming:
            self.stop_streaming()
        
        if self.active_device is not None:
            await self.disconnect()
        
        self.data_callbacks.clear()
        
        # Clear queue
        while not self.data_queue.empty():
            try:
                self.data_queue.get_nowait()
            except queue.Empty:
                break
        
        self.logger.info("Device Interface cleanup complete")