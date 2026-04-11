"""
Spike Monitoring System for Neuromorphic Computing

Provides comprehensive monitoring and analysis of spike activity
including real-time visualization, statistical analysis, and
performance tracking.
"""

import time
import numpy as np
import threading
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
import logging
import json
from pathlib import Path

@dataclass
class SpikeRecord:
    """Record of a single spike event."""
    neuron_id: int
    timestamp: float
    amplitude: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MonitoringStats:
    """Statistics for spike monitoring."""
    total_spikes: int = 0
    active_neurons: int = 0
    avg_firing_rate: float = 0.0
    max_firing_rate: float = 0.0
    network_synchrony: float = 0.0
    recording_duration: float = 0.0
    last_update: float = 0.0

class SpikeMonitor:
    """
    Comprehensive spike monitoring and analysis system.
    
    Features:
    - Real-time spike recording
    - Statistical analysis
    - Firing rate calculations
    - Synchrony measurements
    - Data export and visualization
    - Performance tracking
    """
    
    def __init__(self, config):
        """Initialize spike monitor."""
        self.config = config
        
        # Recording state
        self.is_recording = False
        self.start_time = 0.0
        self.current_time = 0.0
        
        # Spike data storage
        self.spike_records = deque()
        self.spike_times_by_neuron = defaultdict(deque)
        self.spike_counts = defaultdict(int)
        
        # Monitoring windows
        self.analysis_window = 1.0  # 1 second analysis window
        self.recording_window = 10.0  # 10 second recording window
        
        # Statistical tracking
        self.stats = MonitoringStats()
        self.firing_rates = defaultdict(float)
        self.isi_distributions = defaultdict(list)
        
        # Real-time analysis
        self.sliding_window_data = deque(maxlen=1000)
        self.synchrony_history = deque(maxlen=1000)
        self.rate_history = defaultdict(lambda: deque(maxlen=100))
        
        # Performance monitoring
        self.processing_times = deque(maxlen=1000)
        self.memory_usage = deque(maxlen=100)
        
        # Export settings
        self.auto_export = False
        self.export_interval = 60.0  # Export every minute
        self.last_export_time = 0.0
        self.export_directory = Path("neuromorphic_data")
        
        # Threading
        self._lock = threading.Lock()
        self._analysis_thread = None
        self._export_thread = None
        self._stop_event = threading.Event()
        
        # Callbacks
        self.spike_callbacks = []
        self.stats_callbacks = []
        self.analysis_callbacks = []
        
        # Filters
        self.neuron_filters = set()  # Only monitor specific neurons
        self.amplitude_threshold = 0.0
        
        # Logging
        self.logger = logging.getLogger("neuromorphic.spike_monitor")
        
        # Visualization data
        self.raster_data = defaultdict(list)
        self.histogram_data = defaultdict(list)
        
        # Advanced analysis
        self.burst_detection_enabled = True
        self.oscillation_analysis_enabled = True
        self.pattern_recognition_enabled = True
    
    def initialize(self) -> None:
        """Initialize the spike monitor."""
        self.logger.info("Initializing spike monitor")
        
        # Create export directory
        self.export_directory.mkdir(parents=True, exist_ok=True)
        
        # Start analysis thread
        self._start_analysis_thread()
        
        # Start export thread if auto-export enabled
        if self.auto_export:
            self._start_export_thread()
        
        self.logger.info("Spike monitor initialized")
    
    def shutdown(self) -> None:
        """Shutdown the spike monitor."""
        self.logger.info("Shutting down spike monitor")
        
        # Stop recording
        if self.is_recording:
            self.stop_recording()
        
        # Stop threads
        self._stop_event.set()
        
        if self._analysis_thread and self._analysis_thread.is_alive():
            self._analysis_thread.join(timeout=5.0)
        
        if self._export_thread and self._export_thread.is_alive():
            self._export_thread.join(timeout=5.0)
        
        # Final export if needed
        if self.auto_export and self.spike_records:
            self.export_data()
        
        self.logger.info("Spike monitor shutdown complete")
    
    def start_recording(self) -> None:
        """Start spike recording."""
        with self._lock:
            if self.is_recording:
                self.logger.warning("Recording already in progress")
                return
            
            self.is_recording = True
            self.start_time = time.time()
            self.current_time = 0.0
            
            # Clear previous data
            self.spike_records.clear()
            self.spike_times_by_neuron.clear()
            self.spike_counts.clear()
            
            # Reset statistics
            self.stats = MonitoringStats()
            
        self.logger.info("Started spike recording")
    
    def stop_recording(self) -> None:
        """Stop spike recording."""
        with self._lock:
            if not self.is_recording:
                self.logger.warning("No recording in progress")
                return
            
            self.is_recording = False
            
            # Update final statistics
            self._update_statistics()
            
        self.logger.info(f"Stopped spike recording. Total spikes: {self.stats.total_spikes}")
    
    def record_spike(self, neuron_id: int, timestamp: float, 
                    amplitude: float = 1.0, metadata: Dict[str, Any] = None) -> None:
        """Record a spike event."""
        if not self.is_recording:
            return
        
        # Apply filters
        if self.neuron_filters and neuron_id not in self.neuron_filters:
            return
        
        if amplitude < self.amplitude_threshold:
            return
        
        # Create spike record
        spike_record = SpikeRecord(
            neuron_id=neuron_id,
            timestamp=timestamp,
            amplitude=amplitude,
            metadata=metadata or {}
        )
        
        with self._lock:
            # Add to main record
            self.spike_records.append(spike_record)
            
            # Add to neuron-specific storage
            self.spike_times_by_neuron[neuron_id].append(timestamp)
            self.spike_counts[neuron_id] += 1
            
            # Limit storage size
            max_records = 100000  # Limit to prevent memory issues
            if len(self.spike_records) > max_records:
                # Remove oldest records
                old_record = self.spike_records.popleft()
                old_neuron = old_record.neuron_id
                
                if old_neuron in self.spike_times_by_neuron:
                    if self.spike_times_by_neuron[old_neuron]:
                        self.spike_times_by_neuron[old_neuron].popleft()
            
            # Update real-time data
            self._update_realtime_data(spike_record)
        
        # Call spike callbacks
        for callback in self.spike_callbacks:
            try:
                callback(spike_record)
            except Exception as e:
                self.logger.warning(f"Spike callback failed: {e}")
    
    def update(self, dt: float) -> None:
        """Update monitor for one time step."""
        if not self.is_recording:
            return
        
        start_time = time.perf_counter()
        
        with self._lock:
            self.current_time += dt
            
            # Periodic statistics update
            if self.current_time - self.stats.last_update > 0.1:  # Every 100ms
                self._update_statistics()
        
        # Record processing time
        processing_time = time.perf_counter() - start_time
        self.processing_times.append(processing_time)
    
    def get_firing_rate(self, neuron_id: int, time_window: float = 1.0) -> float:
        """Get firing rate for a specific neuron."""
        if neuron_id not in self.spike_times_by_neuron:
            return 0.0
        
        cutoff_time = self.current_time - time_window
        recent_spikes = [
            t for t in self.spike_times_by_neuron[neuron_id]
            if t >= cutoff_time
        ]
        
        return len(recent_spikes) / time_window
    
    def get_network_firing_rate(self, time_window: float = 1.0) -> float:
        """Get network-wide firing rate."""
        cutoff_time = self.current_time - time_window
        total_spikes = 0
        
        for spike_times in self.spike_times_by_neuron.values():
            recent_spikes = [t for t in spike_times if t >= cutoff_time]
            total_spikes += len(recent_spikes)
        
        active_neurons = len(self.spike_times_by_neuron)
        
        if active_neurons == 0:
            return 0.0
        
        return total_spikes / (time_window * active_neurons)
    
    def get_synchrony_index(self, neuron_ids: List[int] = None, 
                           time_window: float = 1.0) -> float:
        """Calculate synchrony index for specified neurons."""
        if neuron_ids is None:
            neuron_ids = list(self.spike_times_by_neuron.keys())
        
        if len(neuron_ids) < 2:
            return 0.0
        
        cutoff_time = self.current_time - time_window
        
        # Get spike times for each neuron
        spike_trains = []
        for neuron_id in neuron_ids:
            if neuron_id in self.spike_times_by_neuron:
                recent_spikes = [
                    t for t in self.spike_times_by_neuron[neuron_id]
                    if t >= cutoff_time
                ]
                spike_trains.append(recent_spikes)
            else:
                spike_trains.append([])
        
        # Calculate synchrony using coincidence detection
        return self._calculate_synchrony(spike_trains, time_window)
    
    def get_isi_distribution(self, neuron_id: int) -> Dict[str, Any]:
        """Get inter-spike interval distribution for a neuron."""
        if neuron_id not in self.spike_times_by_neuron:
            return {'intervals': [], 'mean': 0.0, 'std': 0.0, 'cv': 0.0}
        
        spike_times = list(self.spike_times_by_neuron[neuron_id])
        
        if len(spike_times) < 2:
            return {'intervals': [], 'mean': 0.0, 'std': 0.0, 'cv': 0.0}
        
        intervals = np.diff(sorted(spike_times))
        
        mean_isi = np.mean(intervals)
        std_isi = np.std(intervals)
        cv_isi = std_isi / mean_isi if mean_isi > 0 else 0.0
        
        return {
            'intervals': intervals.tolist(),
            'mean': mean_isi,
            'std': std_isi,
            'cv': cv_isi,
            'count': len(intervals)
        }
    
    def get_burst_analysis(self, neuron_id: int) -> Dict[str, Any]:
        """Analyze burst patterns for a neuron."""
        if not self.burst_detection_enabled:
            return {}
        
        if neuron_id not in self.spike_times_by_neuron:
            return {'bursts': [], 'burst_rate': 0.0}
        
        spike_times = list(self.spike_times_by_neuron[neuron_id])
        
        if len(spike_times) < 3:
            return {'bursts': [], 'burst_rate': 0.0}
        
        # Detect bursts (3+ spikes within 50ms)
        bursts = []
        i = 0
        
        while i < len(spike_times) - 2:
            burst_start = spike_times[i]
            burst_spikes = [burst_start]
            
            # Look for consecutive spikes within burst window
            j = i + 1
            while j < len(spike_times) and spike_times[j] - burst_start <= 0.05:
                burst_spikes.append(spike_times[j])
                j += 1
            
            # If we found a burst (3+ spikes)
            if len(burst_spikes) >= 3:
                bursts.append({
                    'start_time': burst_start,
                    'end_time': burst_spikes[-1],
                    'duration': burst_spikes[-1] - burst_start,
                    'spike_count': len(burst_spikes),
                    'inter_burst_interval': bursts[-1]['start_time'] - burst_start if bursts else 0.0
                })
            
            i = j  # Skip past this burst
        else:
            i += 1
        
    burst_rate = len(bursts) / (self.current_time - self.start_time) if self.current_time > self.start_time else 0.0
    
    return {
        'bursts': bursts,
        'burst_rate': burst_rate,
        'total_bursts': len(bursts)
    }

def add_neuron_filter(self, neuron_id: int) -> None:
    """Add neuron to monitoring filter."""
    self.neuron_filters.add(neuron_id)

def remove_neuron_filter(self, neuron_id: int) -> None:
    """Remove neuron from monitoring filter."""
    self.neuron_filters.discard(neuron_id)

def clear_neuron_filters(self) -> None:
    """Clear all neuron filters."""
    self.neuron_filters.clear()

def set_amplitude_threshold(self, threshold: float) -> None:
    """Set minimum amplitude threshold for spike recording."""
    self.amplitude_threshold = threshold

def add_spike_callback(self, callback: Callable) -> None:
    """Add callback for spike events."""
    self.spike_callbacks.append(callback)

def add_stats_callback(self, callback: Callable) -> None:
    """Add callback for statistics updates."""
    self.stats_callbacks.append(callback)

def get_raster_data(self, time_window: float = None) -> Dict[int, List[float]]:
    """Get raster plot data."""
    if time_window is None:
        # Return all data
        return {nid: list(times) for nid, times in self.spike_times_by_neuron.items()}
    
    cutoff_time = self.current_time - time_window
    raster_data = {}
    
    for neuron_id, spike_times in self.spike_times_by_neuron.items():
        recent_spikes = [t for t in spike_times if t >= cutoff_time]
        if recent_spikes:
            raster_data[neuron_id] = recent_spikes
    
    return raster_data

def get_rate_histogram(self, bin_size: float = 0.01) -> Tuple[np.ndarray, np.ndarray]:
    """Get firing rate histogram."""
    if not self.spike_records:
        return np.array([]), np.array([])
    
    # Create time bins
    max_time = max(record.timestamp for record in self.spike_records)
    bins = np.arange(0, max_time + bin_size, bin_size)
    
    # Count spikes in each bin
    spike_times = [record.timestamp for record in self.spike_records]
    counts, _ = np.histogram(spike_times, bins=bins)
    
    # Convert to rates (spikes/second)
    rates = counts / bin_size
    
    return bins[:-1], rates

def export_data(self, filename: str = None) -> str:
    """Export recorded data to file."""
    if filename is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"spike_data_{timestamp}.json"
    
    filepath = self.export_directory / filename
    
    # Prepare export data
    export_data = {
        'metadata': {
            'recording_start': self.start_time,
            'recording_duration': self.current_time,
            'total_spikes': len(self.spike_records),
            'active_neurons': len(self.spike_times_by_neuron),
            'export_timestamp': time.time()
        },
        'statistics': {
            'total_spikes': self.stats.total_spikes,
            'avg_firing_rate': self.stats.avg_firing_rate,
            'max_firing_rate': self.stats.max_firing_rate,
            'network_synchrony': self.stats.network_synchrony
        },
        'spike_data': [
            {
                'neuron_id': record.neuron_id,
                'timestamp': record.timestamp,
                'amplitude': record.amplitude,
                'metadata': record.metadata
            }
            for record in self.spike_records
        ],
        'firing_rates': dict(self.firing_rates),
        'neuron_spike_counts': dict(self.spike_counts)
    }
    
    try:
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.logger.info(f"Exported spike data to {filepath}")
        return str(filepath)
        
    except Exception as e:
        self.logger.error(f"Failed to export data: {e}")
        raise

def get_statistics(self) -> MonitoringStats:
    """Get current monitoring statistics."""
    with self._lock:
        return self.stats

def get_monitor_performance(self) -> Dict[str, Any]:
    """Get monitor performance metrics."""
    avg_processing_time = (
        np.mean(self.processing_times) if self.processing_times else 0.0
    )
    
    return {
        'avg_processing_time': avg_processing_time,
        'max_processing_time': max(self.processing_times) if self.processing_times else 0.0,
        'total_records': len(self.spike_records),
        'memory_usage_mb': sum(self.memory_usage) / len(self.memory_usage) if self.memory_usage else 0.0,
        'recording_duration': self.current_time,
        'records_per_second': len(self.spike_records) / self.current_time if self.current_time > 0 else 0.0
    }

def _update_statistics(self) -> None:
    """Update monitoring statistics."""
    self.stats.total_spikes = len(self.spike_records)
    self.stats.active_neurons = len(self.spike_times_by_neuron)
    self.stats.recording_duration = self.current_time
    
    # Calculate firing rates
    if self.spike_times_by_neuron:
        rates = []
        for neuron_id in self.spike_times_by_neuron:
            rate = self.get_firing_rate(neuron_id)
            self.firing_rates[neuron_id] = rate
            rates.append(rate)
        
        self.stats.avg_firing_rate = np.mean(rates) if rates else 0.0
        self.stats.max_firing_rate = max(rates) if rates else 0.0
    
    # Calculate network synchrony
    self.stats.network_synchrony = self.get_synchrony_index()
    
    self.stats.last_update = self.current_time
    
    # Call statistics callbacks
    for callback in self.stats_callbacks:
        try:
            callback(self.stats)
        except Exception as e:
            self.logger.warning(f"Stats callback failed: {e}")

def _update_realtime_data(self, spike_record: SpikeRecord) -> None:
    """Update real-time analysis data."""
    # Add to sliding window
    self.sliding_window_data.append(spike_record)
    
    # Update raster data
    self.raster_data[spike_record.neuron_id].append(spike_record.timestamp)
    
    # Limit raster data size
    max_raster_points = 1000
    if len(self.raster_data[spike_record.neuron_id]) > max_raster_points:
        self.raster_data[spike_record.neuron_id] = (
            self.raster_data[spike_record.neuron_id][-max_raster_points:]
        )

def _calculate_synchrony(self, spike_trains: List[List[float]], 
                       time_window: float) -> float:
    """Calculate synchrony index between spike trains."""
    if len(spike_trains) < 2:
        return 0.0
    
    # Remove empty spike trains
    non_empty_trains = [train for train in spike_trains if train]
    
    if len(non_empty_trains) < 2:
        return 0.0
    
    # Calculate pairwise synchrony
    synchrony_values = []
    coincidence_window = 0.005  # 5ms
    
    for i in range(len(non_empty_trains)):
        for j in range(i + 1, len(non_empty_trains)):
            train_a = non_empty_trains[i]
            train_b = non_empty_trains[j]
            
            coincidences = 0
            for spike_a in train_a:
                for spike_b in train_b:
                    if abs(spike_a - spike_b) <= coincidence_window:
                        coincidences += 1
                        break
            
            max_coincidences = min(len(train_a), len(train_b))
            if max_coincidences > 0:
                sync = coincidences / max_coincidences
                synchrony_values.append(sync)
    
    return np.mean(synchrony_values) if synchrony_values else 0.0

def _start_analysis_thread(self) -> None:
    """Start background analysis thread."""
    self._analysis_thread = threading.Thread(
        target=self._analysis_loop,
        daemon=True
    )
    self._analysis_thread.start()
    self.logger.debug("Started analysis thread")

def _start_export_thread(self) -> None:
    """Start background export thread."""
    self._export_thread = threading.Thread(
        target=self._export_loop,
        daemon=True
    )
    self._export_thread.start()
    self.logger.debug("Started export thread")

def _analysis_loop(self) -> None:
    """Background analysis loop."""
    while not self._stop_event.is_set():
        try:
            if self.is_recording:
                # Perform periodic analysis
                self._perform_advanced_analysis()
            
            # Sleep for analysis interval
            time.sleep(1.0)  # Analyze every second
            
        except Exception as e:
            self.logger.error(f"Analysis loop error: {e}")

def _export_loop(self) -> None:
    """Background export loop."""
    while not self._stop_event.is_set():
        try:
            current_time = time.time()
            
            if (self.is_recording and 
                current_time - self.last_export_time > self.export_interval):
                
                self.export_data()
                self.last_export_time = current_time
            
            # Sleep for export check interval
            time.sleep(10.0)  # Check every 10 seconds
            
        except Exception as e:
            self.logger.error(f"Export loop error: {e}")

def _perform_advanced_analysis(self) -> None:
    """Perform advanced spike train analysis."""
    # This method can be extended with more sophisticated analysis
    # For now, it updates basic statistics
    
    if not self.is_recording or not self.spike_records:
        return
    
    # Update synchrony history
    current_synchrony = self.get_synchrony_index(time_window=1.0)
    self.synchrony_history.append(current_synchrony)
    
    # Update rate history for active neurons
    for neuron_id in self.spike_times_by_neuron:
        current_rate = self.get_firing_rate(neuron_id, time_window=1.0)
        self.rate_history[neuron_id].append(current_rate)"