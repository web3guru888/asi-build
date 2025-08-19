"""
Network Manager - Manages network bandwidth and connectivity resources
"""

import asyncio
import logging
import time
import psutil
import subprocess
import json
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
import socket
import ipaddress


class NetworkType(Enum):
    ETHERNET = "ethernet"
    INFINIBAND = "infiniband"
    WIFI = "wifi"
    LOOPBACK = "loopback"
    VIRTUAL = "virtual"
    TUNNEL = "tunnel"


class NetworkState(Enum):
    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class NetworkInterface:
    """Network interface information"""
    interface_id: str
    name: str
    network_type: NetworkType
    state: NetworkState
    mtu: int = 1500
    speed_mbps: int = 0  # Link speed in Mbps
    mac_address: str = ""
    ip_addresses: List[str] = field(default_factory=list)
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    tx_packets: int = 0
    rx_errors: int = 0
    tx_errors: int = 0
    rx_dropped: int = 0
    tx_dropped: int = 0
    rx_bandwidth_mbps: float = 0.0  # Current receive bandwidth
    tx_bandwidth_mbps: float = 0.0  # Current transmit bandwidth
    latency_ms: float = 0.0
    packet_loss_percent: float = 0.0
    
    @property
    def total_bandwidth_mbps(self) -> float:
        return self.rx_bandwidth_mbps + self.tx_bandwidth_mbps
    
    @property
    def utilization_percent(self) -> float:
        if self.speed_mbps > 0:
            return (self.total_bandwidth_mbps / self.speed_mbps) * 100
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "interface_id": self.interface_id,
            "name": self.name,
            "network_type": self.network_type.value,
            "state": self.state.value,
            "mtu": self.mtu,
            "speed_mbps": self.speed_mbps,
            "mac_address": self.mac_address,
            "ip_addresses": self.ip_addresses,
            "rx_bytes": self.rx_bytes,
            "tx_bytes": self.tx_bytes,
            "rx_packets": self.rx_packets,
            "tx_packets": self.tx_packets,
            "rx_errors": self.rx_errors,
            "tx_errors": self.tx_errors,
            "rx_dropped": self.rx_dropped,
            "tx_dropped": self.tx_dropped,
            "rx_bandwidth_mbps": self.rx_bandwidth_mbps,
            "tx_bandwidth_mbps": self.tx_bandwidth_mbps,
            "total_bandwidth_mbps": self.total_bandwidth_mbps,
            "utilization_percent": self.utilization_percent,
            "latency_ms": self.latency_ms,
            "packet_loss_percent": self.packet_loss_percent
        }


@dataclass
class NetworkRoute:
    """Network route information"""
    destination: str
    gateway: str
    interface: str
    metric: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "destination": self.destination,
            "gateway": self.gateway,
            "interface": self.interface,
            "metric": self.metric
        }


@dataclass
class BandwidthAllocation:
    """Network bandwidth allocation"""
    allocation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = ""
    user_id: str = ""
    interface_names: List[str] = field(default_factory=list)
    rx_bandwidth_mbps: float = 0.0
    tx_bandwidth_mbps: float = 0.0
    total_bandwidth_mbps: float = 0.0
    priority: int = 0  # 0-7 (7 = highest)
    burst_allowed: bool = True
    allocated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allocation_id": self.allocation_id,
            "job_id": self.job_id,
            "user_id": self.user_id,
            "interface_names": self.interface_names,
            "rx_bandwidth_mbps": self.rx_bandwidth_mbps,
            "tx_bandwidth_mbps": self.tx_bandwidth_mbps,
            "total_bandwidth_mbps": self.total_bandwidth_mbps,
            "priority": self.priority,
            "burst_allowed": self.burst_allowed,
            "allocated_at": self.allocated_at,
            "expires_at": self.expires_at
        }


@dataclass
class NetworkQoSRule:
    """Quality of Service rule"""
    rule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""  # IP/CIDR or interface
    destination: str = ""  # IP/CIDR or interface
    protocol: str = ""  # tcp, udp, icmp, etc.
    port_range: str = ""  # e.g., "80", "8000-9000"
    bandwidth_limit_mbps: float = 0.0
    priority: int = 0
    dscp_marking: int = 0  # DSCP marking for QoS
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "source": self.source,
            "destination": self.destination,
            "protocol": self.protocol,
            "port_range": self.port_range,
            "bandwidth_limit_mbps": self.bandwidth_limit_mbps,
            "priority": self.priority,
            "dscp_marking": self.dscp_marking
        }


class NetworkManager:
    """
    Comprehensive network manager for bandwidth allocation and QoS
    """
    
    def __init__(self):
        self.logger = logging.getLogger("network_manager")
        
        # Network interfaces and routing
        self.interfaces: Dict[str, NetworkInterface] = {}
        self.routes: List[NetworkRoute] = []
        
        # Bandwidth management
        self.allocations: Dict[str, BandwidthAllocation] = {}
        self.qos_rules: Dict[str, NetworkQoSRule] = {}
        
        # Traffic shaping support
        self.traffic_control_enabled = False
        self.tc_available = False
        
        # Monitoring
        self.monitoring_interval = 10.0  # 10 seconds
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Network topology discovery
        self.topology_discovery_enabled = True
        self.discovered_peers: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self._stats = {
            "total_interfaces": 0,
            "active_interfaces": 0,
            "total_bandwidth_mbps": 0.0,
            "allocated_bandwidth_mbps": 0.0,
            "average_utilization": 0.0,
            "total_rx_bytes": 0,
            "total_tx_bytes": 0,
            "total_rx_packets": 0,
            "total_tx_packets": 0,
            "total_errors": 0,
            "total_dropped": 0,
            "active_allocations": 0,
            "active_qos_rules": 0
        }
        
    async def initialize(self) -> None:
        """Initialize the network manager"""
        self.logger.info("Initializing network manager")
        
        # Check for traffic control tools
        await self._check_traffic_control_support()
        
        # Discover network interfaces
        await self._discover_network_interfaces()
        
        # Discover network routes
        await self._discover_network_routes()
        
        # Start network monitoring
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info(f"Network manager initialized with {len(self.interfaces)} interfaces")
        
    async def _check_traffic_control_support(self) -> None:
        """Check if traffic control (tc) is available"""
        try:
            result = subprocess.run(
                ["tc", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                self.tc_available = True
                self.traffic_control_enabled = True
                self.logger.info("Traffic control (tc) support available")
            else:
                self.logger.warning("Traffic control (tc) not available - bandwidth limiting disabled")
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.logger.warning("Traffic control (tc) not found - bandwidth limiting disabled")
            
    async def _discover_network_interfaces(self) -> None:
        """Discover available network interfaces"""
        try:
            # Get interface statistics
            net_io = psutil.net_io_counters(pernic=True)
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()
            
            for interface_name, io_stats in net_io.items():
                try:
                    # Get interface addresses
                    ip_addresses = []
                    mac_address = ""
                    
                    if interface_name in net_if_addrs:
                        for addr in net_if_addrs[interface_name]:
                            if addr.family == socket.AF_INET or addr.family == socket.AF_INET6:
                                ip_addresses.append(addr.address)
                            elif hasattr(socket, 'AF_PACKET') and addr.family == socket.AF_PACKET:
                                mac_address = addr.address
                    
                    # Get interface stats
                    mtu = 1500
                    speed_mbps = 0
                    state = NetworkState.UNKNOWN
                    
                    if interface_name in net_if_stats:
                        stats = net_if_stats[interface_name]
                        mtu = stats.mtu
                        speed_mbps = stats.speed if stats.speed and stats.speed > 0 else 0
                        state = NetworkState.UP if stats.isup else NetworkState.DOWN
                    
                    # Determine network type
                    network_type = await self._determine_network_type(interface_name)
                    
                    interface = NetworkInterface(
                        interface_id=f"net_{len(self.interfaces)}",
                        name=interface_name,
                        network_type=network_type,
                        state=state,
                        mtu=mtu,
                        speed_mbps=speed_mbps,
                        mac_address=mac_address,
                        ip_addresses=ip_addresses,
                        rx_bytes=io_stats.bytes_recv,
                        tx_bytes=io_stats.bytes_sent,
                        rx_packets=io_stats.packets_recv,
                        tx_packets=io_stats.packets_sent,
                        rx_errors=io_stats.errin,
                        tx_errors=io_stats.errout,
                        rx_dropped=io_stats.dropin,
                        tx_dropped=io_stats.dropout
                    )
                    
                    self.interfaces[interface_name] = interface
                    
                    self.logger.info(
                        f"Discovered network interface: {interface_name} "
                        f"({network_type.value}, {speed_mbps} Mbps, {state.value})"
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error processing interface {interface_name}: {e}")
                    continue
            
            self._update_interface_stats()
            
        except Exception as e:
            self.logger.error(f"Error discovering network interfaces: {e}")
            
    async def _determine_network_type(self, interface_name: str) -> NetworkType:
        """Determine the type of network interface"""
        name = interface_name.lower()
        
        if name.startswith("lo"):
            return NetworkType.LOOPBACK
        elif name.startswith(("eth", "en", "em")):
            return NetworkType.ETHERNET
        elif name.startswith(("wlan", "wl", "wifi")):
            return NetworkType.WIFI
        elif name.startswith(("ib", "infiniband")):
            return NetworkType.INFINIBAND
        elif name.startswith(("veth", "br", "docker", "virbr", "tun", "tap")):
            return NetworkType.VIRTUAL
        elif name.startswith(("ppp", "vpn")):
            return NetworkType.TUNNEL
        else:
            return NetworkType.ETHERNET  # Default assumption
            
    async def _discover_network_routes(self) -> None:
        """Discover network routing table"""
        try:
            # Try to get routes using ip route command
            result = subprocess.run(
                ["ip", "route", "show"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.routes = await self._parse_ip_routes(result.stdout)
            else:
                # Fallback to reading /proc/net/route
                await self._parse_proc_net_route()
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # Fallback to /proc/net/route
            await self._parse_proc_net_route()
            
    async def _parse_ip_routes(self, route_output: str) -> List[NetworkRoute]:
        """Parse 'ip route' command output"""
        routes = []
        
        for line in route_output.strip().split('\n'):
            if not line.strip():
                continue
            
            parts = line.split()
            if len(parts) < 3:
                continue
            
            destination = parts[0] if parts[0] != "default" else "0.0.0.0/0"
            gateway = ""
            interface = ""
            metric = 0
            
            # Parse route components
            for i, part in enumerate(parts):
                if part == "via" and i + 1 < len(parts):
                    gateway = parts[i + 1]
                elif part == "dev" and i + 1 < len(parts):
                    interface = parts[i + 1]
                elif part == "metric" and i + 1 < len(parts):
                    metric = int(parts[i + 1])
            
            routes.append(NetworkRoute(
                destination=destination,
                gateway=gateway,
                interface=interface,
                metric=metric
            ))
        
        return routes
        
    async def _parse_proc_net_route(self) -> None:
        """Parse /proc/net/route as fallback"""
        try:
            with open("/proc/net/route", "r") as f:
                lines = f.readlines()[1:]  # Skip header
                
                for line in lines:
                    fields = line.strip().split('\t')
                    if len(fields) >= 8:
                        interface = fields[0]
                        destination_hex = fields[1]
                        gateway_hex = fields[2]
                        metric = int(fields[6]) if fields[6].isdigit() else 0
                        
                        # Convert hex addresses to dotted decimal
                        destination = socket.inet_ntoa(bytes.fromhex(destination_hex)[::-1])
                        gateway = socket.inet_ntoa(bytes.fromhex(gateway_hex)[::-1])
                        
                        if destination == "0.0.0.0":
                            destination = "0.0.0.0/0"
                        
                        route = NetworkRoute(
                            destination=destination,
                            gateway=gateway if gateway != "0.0.0.0" else "",
                            interface=interface,
                            metric=metric
                        )
                        
                        self.routes.append(route)
                        
        except Exception as e:
            self.logger.error(f"Error parsing /proc/net/route: {e}")
            
    async def allocate_bandwidth(
        self,
        job_id: str,
        user_id: str,
        bandwidth_mbps: float,
        interface_names: Optional[List[str]] = None,
        rx_tx_split: Tuple[float, float] = (0.5, 0.5),
        priority: int = 0,
        burst_allowed: bool = True,
        duration: Optional[float] = None
    ) -> Optional[BandwidthAllocation]:
        """Allocate network bandwidth"""
        self.logger.info(f"Allocating {bandwidth_mbps} Mbps bandwidth for job {job_id}")
        
        # Find suitable interfaces if not specified
        if not interface_names:
            interface_names = await self._find_suitable_interfaces(bandwidth_mbps)
        
        if not interface_names:
            self.logger.warning("No suitable network interfaces found")
            return None
        
        # Check if we have enough bandwidth
        total_available = 0.0
        for interface_name in interface_names:
            if interface_name in self.interfaces:
                interface = self.interfaces[interface_name]
                available = interface.speed_mbps - interface.total_bandwidth_mbps
                total_available += max(0, available)
        
        if total_available < bandwidth_mbps:
            self.logger.warning(f"Insufficient bandwidth: need {bandwidth_mbps}, available {total_available}")
            return None
        
        # Calculate RX/TX split
        rx_bandwidth = bandwidth_mbps * rx_tx_split[0]
        tx_bandwidth = bandwidth_mbps * rx_tx_split[1]
        
        # Create allocation
        allocation = BandwidthAllocation(
            job_id=job_id,
            user_id=user_id,
            interface_names=interface_names,
            rx_bandwidth_mbps=rx_bandwidth,
            tx_bandwidth_mbps=tx_bandwidth,
            total_bandwidth_mbps=bandwidth_mbps,
            priority=priority,
            burst_allowed=burst_allowed
        )
        
        if duration:
            allocation.expires_at = time.time() + duration
        
        # Apply traffic shaping if supported
        if self.traffic_control_enabled:
            await self._apply_traffic_shaping(allocation)
        
        self.allocations[allocation.allocation_id] = allocation
        self._stats["active_allocations"] += 1
        self._stats["allocated_bandwidth_mbps"] += bandwidth_mbps
        
        self.logger.info(f"Allocated {bandwidth_mbps} Mbps to job {job_id}")
        return allocation
        
    async def _find_suitable_interfaces(self, bandwidth_mbps: float) -> List[str]:
        """Find network interfaces suitable for bandwidth allocation"""
        suitable_interfaces = []
        
        for interface_name, interface in self.interfaces.items():
            # Skip loopback and down interfaces
            if interface.network_type == NetworkType.LOOPBACK or interface.state != NetworkState.UP:
                continue
            
            # Check if interface has enough available bandwidth
            available_bandwidth = interface.speed_mbps - interface.total_bandwidth_mbps
            if available_bandwidth >= bandwidth_mbps:
                suitable_interfaces.append(interface_name)
        
        # Sort by available bandwidth (descending) and preference
        interface_preference = {
            NetworkType.INFINIBAND: 5,
            NetworkType.ETHERNET: 4,
            NetworkType.VIRTUAL: 3,
            NetworkType.WIFI: 2,
            NetworkType.TUNNEL: 1
        }
        
        suitable_interfaces.sort(key=lambda name: (
            -interface_preference.get(self.interfaces[name].network_type, 0),
            -(self.interfaces[name].speed_mbps - self.interfaces[name].total_bandwidth_mbps)
        ))
        
        return suitable_interfaces
        
    async def _apply_traffic_shaping(self, allocation: BandwidthAllocation) -> bool:
        """Apply traffic shaping rules using tc (traffic control)"""
        if not self.tc_available:
            return False
        
        try:
            for interface_name in allocation.interface_names:
                # Create HTB (Hierarchical Token Bucket) qdisc if not exists
                await self._ensure_htb_qdisc(interface_name)
                
                # Create class for this allocation
                class_id = f"1:{len(self.allocations)}"
                
                # Add class with bandwidth limit
                cmd = [
                    "tc", "class", "add",
                    "dev", interface_name,
                    "parent", "1:0",
                    "classid", class_id,
                    "htb",
                    "rate", f"{allocation.total_bandwidth_mbps}mbit",
                    "prio", str(7 - allocation.priority)  # Convert to tc priority (0 = highest)
                ]
                
                if allocation.burst_allowed:
                    cmd.extend(["ceil", f"{allocation.total_bandwidth_mbps * 1.2}mbit"])
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode != 0:
                    self.logger.error(f"Failed to create tc class: {result.stderr}")
                    return False
            
            self.logger.info(f"Applied traffic shaping for allocation {allocation.allocation_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying traffic shaping: {e}")
            return False
            
    async def _ensure_htb_qdisc(self, interface_name: str) -> None:
        """Ensure HTB qdisc exists on interface"""
        try:
            # Check if HTB qdisc already exists
            result = subprocess.run(
                ["tc", "qdisc", "show", "dev", interface_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if "htb" not in result.stdout:
                # Create HTB root qdisc
                cmd = [
                    "tc", "qdisc", "add",
                    "dev", interface_name,
                    "root", "handle", "1:",
                    "htb", "default", "30"
                ]
                
                subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
        except Exception as e:
            self.logger.error(f"Error ensuring HTB qdisc: {e}")
            
    async def deallocate_bandwidth(self, allocation_id: str) -> bool:
        """Deallocate network bandwidth"""
        if allocation_id not in self.allocations:
            self.logger.warning(f"Allocation {allocation_id} not found")
            return False
        
        allocation = self.allocations.pop(allocation_id)
        
        # Remove traffic shaping rules if applied
        if self.traffic_control_enabled:
            await self._remove_traffic_shaping(allocation)
        
        self._stats["active_allocations"] -= 1
        self._stats["allocated_bandwidth_mbps"] -= allocation.total_bandwidth_mbps
        
        self.logger.info(f"Deallocated {allocation.total_bandwidth_mbps} Mbps bandwidth")
        return True
        
    async def _remove_traffic_shaping(self, allocation: BandwidthAllocation) -> None:
        """Remove traffic shaping rules for an allocation"""
        try:
            for interface_name in allocation.interface_names:
                # This is simplified - in practice, you'd track class IDs
                # and remove specific classes
                pass
                
        except Exception as e:
            self.logger.error(f"Error removing traffic shaping: {e}")
            
    async def create_qos_rule(
        self,
        source: str = "",
        destination: str = "",
        protocol: str = "",
        port_range: str = "",
        bandwidth_limit_mbps: float = 0.0,
        priority: int = 0,
        dscp_marking: int = 0
    ) -> str:
        """Create a Quality of Service rule"""
        rule = NetworkQoSRule(
            source=source,
            destination=destination,
            protocol=protocol,
            port_range=port_range,
            bandwidth_limit_mbps=bandwidth_limit_mbps,
            priority=priority,
            dscp_marking=dscp_marking
        )
        
        self.qos_rules[rule.rule_id] = rule
        self._stats["active_qos_rules"] += 1
        
        # Apply QoS rule if traffic control is available
        if self.traffic_control_enabled:
            await self._apply_qos_rule(rule)
        
        self.logger.info(f"Created QoS rule: {rule.rule_id}")
        return rule.rule_id
        
    async def _apply_qos_rule(self, rule: NetworkQoSRule) -> None:
        """Apply QoS rule using iptables and tc"""
        try:
            # This would involve creating iptables rules for packet marking
            # and tc filters for traffic classification
            # Implementation details depend on specific requirements
            pass
            
        except Exception as e:
            self.logger.error(f"Error applying QoS rule: {e}")
            
    async def remove_qos_rule(self, rule_id: str) -> bool:
        """Remove a Quality of Service rule"""
        if rule_id not in self.qos_rules:
            return False
        
        rule = self.qos_rules.pop(rule_id)
        self._stats["active_qos_rules"] -= 1
        
        # Remove QoS rule from system
        if self.traffic_control_enabled:
            await self._remove_qos_rule(rule)
        
        self.logger.info(f"Removed QoS rule: {rule_id}")
        return True
        
    async def _remove_qos_rule(self, rule: NetworkQoSRule) -> None:
        """Remove QoS rule from system"""
        try:
            # Remove iptables rules and tc filters
            pass
            
        except Exception as e:
            self.logger.error(f"Error removing QoS rule: {e}")
            
    async def test_connectivity(self, target: str, timeout: float = 5.0) -> Dict[str, Any]:
        """Test network connectivity to a target"""
        try:
            start_time = time.time()
            
            # Parse target (IP or hostname)
            try:
                ip = ipaddress.ip_address(target)
                hostname = str(ip)
            except ValueError:
                hostname = target
            
            # Ping test
            ping_result = await self._ping_test(hostname, timeout)
            
            # Try TCP connection test on common ports
            tcp_results = {}
            for port in [22, 80, 443]:  # SSH, HTTP, HTTPS
                tcp_results[port] = await self._tcp_connect_test(hostname, port, timeout)
            
            end_time = time.time()
            
            return {
                "target": target,
                "ping": ping_result,
                "tcp_ports": tcp_results,
                "test_duration": end_time - start_time
            }
            
        except Exception as e:
            self.logger.error(f"Error testing connectivity to {target}: {e}")
            return {"target": target, "error": str(e)}
            
    async def _ping_test(self, hostname: str, timeout: float) -> Dict[str, Any]:
        """Perform ping test"""
        try:
            cmd = ["ping", "-c", "4", "-W", str(int(timeout)), hostname]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
            
            if result.returncode == 0:
                # Parse ping statistics
                output = result.stdout
                packet_loss = 0
                avg_latency = 0
                
                for line in output.split('\n'):
                    if "packet loss" in line:
                        import re
                        match = re.search(r'(\d+)% packet loss', line)
                        if match:
                            packet_loss = int(match.group(1))
                    elif "min/avg/max" in line:
                        parts = line.split('=')[1].strip().split('/')
                        if len(parts) >= 2:
                            avg_latency = float(parts[1])
                
                return {
                    "success": True,
                    "packet_loss_percent": packet_loss,
                    "avg_latency_ms": avg_latency
                }
            else:
                return {"success": False, "error": result.stderr}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _tcp_connect_test(self, hostname: str, port: int, timeout: float) -> Dict[str, Any]:
        """Perform TCP connection test"""
        try:
            start_time = time.time()
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(hostname, port),
                timeout=timeout
            )
            
            connect_time = time.time() - start_time
            writer.close()
            await writer.wait_closed()
            
            return {
                "success": True,
                "connect_time_ms": connect_time * 1000
            }
            
        except asyncio.TimeoutError:
            return {"success": False, "error": "Connection timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive network status"""
        return {
            "interfaces": {
                name: interface.to_dict()
                for name, interface in self.interfaces.items()
            },
            "routes": [route.to_dict() for route in self.routes],
            "allocations": {
                allocation_id: allocation.to_dict()
                for allocation_id, allocation in self.allocations.items()
            },
            "qos_rules": {
                rule_id: rule.to_dict()
                for rule_id, rule in self.qos_rules.items()
            },
            "statistics": self._stats.copy(),
            "traffic_control_enabled": self.traffic_control_enabled
        }
        
    async def get_utilization(self) -> Dict[str, float]:
        """Get network utilization metrics"""
        if not self.interfaces:
            return {}
        
        total_bandwidth = sum(iface.speed_mbps for iface in self.interfaces.values() if iface.speed_mbps > 0)
        total_utilization = sum(iface.total_bandwidth_mbps for iface in self.interfaces.values())
        
        avg_utilization = 0.0
        active_interfaces = [iface for iface in self.interfaces.values() if iface.state == NetworkState.UP]
        
        if active_interfaces:
            avg_utilization = sum(iface.utilization_percent for iface in active_interfaces) / len(active_interfaces)
        
        return {
            "network_interfaces_total": len(self.interfaces),
            "network_interfaces_active": len(active_interfaces),
            "network_bandwidth_total_mbps": total_bandwidth,
            "network_bandwidth_used_mbps": total_utilization,
            "network_utilization_avg": avg_utilization,
            "network_allocated_bandwidth_mbps": self._stats["allocated_bandwidth_mbps"],
            "network_rx_bytes_total": self._stats["total_rx_bytes"],
            "network_tx_bytes_total": self._stats["total_tx_bytes"],
            "network_packets_total": self._stats["total_rx_packets"] + self._stats["total_tx_packets"],
            "network_errors_total": self._stats["total_errors"],
            "network_dropped_total": self._stats["total_dropped"],
            "active_allocations": self._stats["active_allocations"],
            "active_qos_rules": self._stats["active_qos_rules"]
        }
        
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop for network metrics"""
        while True:
            try:
                await self._update_interface_metrics()
                await self._cleanup_expired_allocations()
                self._update_interface_stats()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in network monitoring loop: {e}")
                await asyncio.sleep(30.0)
                
    async def _update_interface_metrics(self) -> None:
        """Update network interface metrics"""
        try:
            # Get current network I/O counters
            net_io = psutil.net_io_counters(pernic=True)
            
            if not hasattr(self, '_previous_net_io'):
                self._previous_net_io = net_io
                self._previous_net_time = time.time()
                return
            
            current_time = time.time()
            time_delta = current_time - self._previous_net_time
            
            if time_delta <= 0:
                return
            
            for interface_name, interface in self.interfaces.items():
                if interface_name in net_io and interface_name in self._previous_net_io:
                    current = net_io[interface_name]
                    previous = self._previous_net_io[interface_name]
                    
                    # Update counters
                    interface.rx_bytes = current.bytes_recv
                    interface.tx_bytes = current.bytes_sent
                    interface.rx_packets = current.packets_recv
                    interface.tx_packets = current.packets_sent
                    interface.rx_errors = current.errin
                    interface.tx_errors = current.errout
                    interface.rx_dropped = current.dropin
                    interface.tx_dropped = current.dropout
                    
                    # Calculate bandwidth (Mbps)
                    rx_bytes_delta = current.bytes_recv - previous.bytes_recv
                    tx_bytes_delta = current.bytes_sent - previous.bytes_sent
                    
                    interface.rx_bandwidth_mbps = (rx_bytes_delta * 8) / (time_delta * 1024 * 1024)
                    interface.tx_bandwidth_mbps = (tx_bytes_delta * 8) / (time_delta * 1024 * 1024)
            
            self._previous_net_io = net_io
            self._previous_net_time = current_time
            
        except Exception as e:
            self.logger.error(f"Error updating interface metrics: {e}")
            
    async def _cleanup_expired_allocations(self) -> None:
        """Clean up expired bandwidth allocations"""
        current_time = time.time()
        expired_allocations = []
        
        for allocation_id, allocation in self.allocations.items():
            if allocation.expires_at and allocation.expires_at <= current_time:
                expired_allocations.append(allocation_id)
        
        for allocation_id in expired_allocations:
            await self.deallocate_bandwidth(allocation_id)
            self.logger.info(f"Cleaned up expired bandwidth allocation: {allocation_id}")
            
    def _update_interface_stats(self) -> None:
        """Update network interface statistics"""
        self._stats["total_interfaces"] = len(self.interfaces)
        self._stats["active_interfaces"] = len([
            iface for iface in self.interfaces.values() 
            if iface.state == NetworkState.UP
        ])
        
        self._stats["total_bandwidth_mbps"] = sum(
            iface.speed_mbps for iface in self.interfaces.values() 
            if iface.speed_mbps > 0
        )
        
        self._stats["total_rx_bytes"] = sum(iface.rx_bytes for iface in self.interfaces.values())
        self._stats["total_tx_bytes"] = sum(iface.tx_bytes for iface in self.interfaces.values())
        self._stats["total_rx_packets"] = sum(iface.rx_packets for iface in self.interfaces.values())
        self._stats["total_tx_packets"] = sum(iface.tx_packets for iface in self.interfaces.values())
        self._stats["total_errors"] = sum(iface.rx_errors + iface.tx_errors for iface in self.interfaces.values())
        self._stats["total_dropped"] = sum(iface.rx_dropped + iface.tx_dropped for iface in self.interfaces.values())
        
        active_interfaces = [iface for iface in self.interfaces.values() if iface.state == NetworkState.UP]
        if active_interfaces:
            self._stats["average_utilization"] = sum(iface.utilization_percent for iface in active_interfaces) / len(active_interfaces)
        
    async def get_pool_statistics(self) -> Dict[str, Any]:
        """Get comprehensive network pool statistics"""
        interface_type_distribution = {}
        for network_type in NetworkType:
            interfaces = [iface for iface in self.interfaces.values() if iface.network_type == network_type]
            if interfaces:
                interface_type_distribution[network_type.value] = {
                    "count": len(interfaces),
                    "total_bandwidth_mbps": sum(iface.speed_mbps for iface in interfaces),
                    "average_utilization": sum(iface.utilization_percent for iface in interfaces) / len(interfaces)
                }
        
        return {
            **self._stats,
            "interface_type_distribution": interface_type_distribution,
            "traffic_control_available": self.tc_available,
            "topology_discovery_enabled": self.topology_discovery_enabled
        }
        
    async def shutdown(self) -> None:
        """Shutdown the network manager"""
        self.logger.info("Shutting down network manager")
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Deallocate all active bandwidth allocations
        allocation_ids = list(self.allocations.keys())
        for allocation_id in allocation_ids:
            await self.deallocate_bandwidth(allocation_id)
        
        # Remove all QoS rules
        rule_ids = list(self.qos_rules.keys())
        for rule_id in rule_ids:
            await self.remove_qos_rule(rule_id)
        
        self.logger.info("Network manager shutdown complete")