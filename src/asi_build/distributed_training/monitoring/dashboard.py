"""
Real-time Training Monitoring Dashboard
Provides comprehensive monitoring and visualization for decentralized training
"""

import asyncio
import json
import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import dash
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import websocket
from dash import Input, Output, callback, dcc, html
from plotly.subplots import make_subplots


@dataclass
class TrainingMetrics:
    """Training metrics for a node"""

    node_id: str
    round_id: str
    epoch: int
    loss: float
    accuracy: float
    learning_rate: float
    batch_time: float
    communication_time: float
    memory_usage: float
    gpu_utilization: float
    timestamp: float


@dataclass
class NetworkMetrics:
    """Network-wide metrics"""

    round_id: str
    total_nodes: int
    active_nodes: int
    avg_loss: float
    avg_accuracy: float
    consensus_time: float
    data_transmitted_mb: float
    byzantine_nodes_detected: int
    timestamp: float


@dataclass
class SystemHealth:
    """System health indicators"""

    timestamp: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_latency: float
    active_connections: int
    error_rate: float


class MetricsCollector:
    """Collects and aggregates training metrics"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Metrics storage
        self.training_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.network_metrics: deque = deque(maxlen=500)
        self.system_health: deque = deque(maxlen=1000)

        # Real-time aggregations
        self.current_round_metrics: Dict[str, TrainingMetrics] = {}
        self.node_performance_history: Dict[str, Dict[str, deque]] = defaultdict(
            lambda: {
                "loss": deque(maxlen=100),
                "accuracy": deque(maxlen=100),
                "batch_time": deque(maxlen=100),
                "communication_time": deque(maxlen=100),
            }
        )

        self.logger = logging.getLogger(__name__)

    def record_training_metrics(self, metrics: TrainingMetrics):
        """Record training metrics for a node"""
        self.training_metrics[metrics.node_id].append(metrics)
        self.current_round_metrics[metrics.node_id] = metrics

        # Update performance history
        perf = self.node_performance_history[metrics.node_id]
        perf["loss"].append(metrics.loss)
        perf["accuracy"].append(metrics.accuracy)
        perf["batch_time"].append(metrics.batch_time)
        perf["communication_time"].append(metrics.communication_time)

        self.logger.debug(f"Recorded metrics for node {metrics.node_id}, round {metrics.round_id}")

    def record_network_metrics(self, metrics: NetworkMetrics):
        """Record network-wide metrics"""
        self.network_metrics.append(metrics)
        self.logger.debug(f"Recorded network metrics for round {metrics.round_id}")

    def record_system_health(self, health: SystemHealth):
        """Record system health metrics"""
        self.system_health.append(health)

    def get_current_round_summary(self) -> Dict[str, Any]:
        """Get summary of current training round"""
        if not self.current_round_metrics:
            return {}

        metrics_list = list(self.current_round_metrics.values())

        return {
            "round_id": metrics_list[0].round_id if metrics_list else "",
            "participating_nodes": len(metrics_list),
            "avg_loss": np.mean([m.loss for m in metrics_list]),
            "std_loss": np.std([m.loss for m in metrics_list]),
            "avg_accuracy": np.mean([m.accuracy for m in metrics_list]),
            "std_accuracy": np.std([m.accuracy for m in metrics_list]),
            "avg_batch_time": np.mean([m.batch_time for m in metrics_list]),
            "avg_communication_time": np.mean([m.communication_time for m in metrics_list]),
            "avg_memory_usage": np.mean([m.memory_usage for m in metrics_list]),
            "avg_gpu_utilization": np.mean([m.gpu_utilization for m in metrics_list]),
        }

    def get_node_performance_trends(self, node_id: str, window_size: int = 50) -> Dict[str, Any]:
        """Get performance trends for a specific node"""
        if node_id not in self.node_performance_history:
            return {}

        history = self.node_performance_history[node_id]

        trends = {}
        for metric, values in history.items():
            if len(values) >= 2:
                recent_values = list(values)[-window_size:]
                if len(recent_values) >= 2:
                    # Calculate trend (positive = improving for accuracy, negative = improving for loss/time)
                    if metric == "accuracy":
                        trend = np.polyfit(range(len(recent_values)), recent_values, 1)[0]
                    else:  # loss, batch_time, communication_time
                        trend = -np.polyfit(range(len(recent_values)), recent_values, 1)[0]

                    trends[f"{metric}_trend"] = trend
                    trends[f"{metric}_current"] = recent_values[-1]
                    trends[f"{metric}_avg"] = np.mean(recent_values)

        return trends

    def get_network_health_status(self) -> Dict[str, Any]:
        """Get overall network health status"""
        if not self.network_metrics:
            return {"status": "unknown"}

        recent_metrics = list(self.network_metrics)[-10:]  # Last 10 rounds

        avg_consensus_time = np.mean([m.consensus_time for m in recent_metrics])
        avg_byzantine_detections = np.mean([m.byzantine_nodes_detected for m in recent_metrics])
        participation_rate = np.mean([m.active_nodes / m.total_nodes for m in recent_metrics])

        # Health scoring
        health_score = 100

        if avg_consensus_time > 300:  # 5 minutes
            health_score -= 20

        if avg_byzantine_detections > 0.1:  # More than 10% Byzantine nodes
            health_score -= 30

        if participation_rate < 0.7:  # Less than 70% participation
            health_score -= 25

        if health_score >= 80:
            status = "healthy"
        elif health_score >= 60:
            status = "warning"
        else:
            status = "critical"

        return {
            "status": status,
            "health_score": health_score,
            "avg_consensus_time": avg_consensus_time,
            "participation_rate": participation_rate,
            "byzantine_detection_rate": avg_byzantine_detections,
        }


class VisualizationEngine:
    """Creates interactive visualizations for training metrics"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(__name__)

    def create_training_progress_chart(self) -> go.Figure:
        """Create training progress chart showing loss and accuracy over time"""

        fig = make_subplots(
            rows=2,
            cols=1,
            subplot_titles=("Training Loss", "Training Accuracy"),
            vertical_spacing=0.1,
        )

        # Collect data from all nodes
        for node_id, metrics_deque in self.metrics_collector.training_metrics.items():
            metrics_list = list(metrics_deque)

            if not metrics_list:
                continue

            timestamps = [m.timestamp for m in metrics_list]
            losses = [m.loss for m in metrics_list]
            accuracies = [m.accuracy for m in metrics_list]

            # Convert timestamps to datetime
            datetimes = [datetime.fromtimestamp(ts) for ts in timestamps]

            # Loss chart
            fig.add_trace(
                go.Scatter(
                    x=datetimes,
                    y=losses,
                    mode="lines+markers",
                    name=f"Node {node_id[:8]}",
                    line=dict(width=2),
                    showlegend=True,
                ),
                row=1,
                col=1,
            )

            # Accuracy chart
            fig.add_trace(
                go.Scatter(
                    x=datetimes,
                    y=accuracies,
                    mode="lines+markers",
                    name=f"Node {node_id[:8]}",
                    line=dict(width=2),
                    showlegend=False,
                ),
                row=2,
                col=1,
            )

        fig.update_layout(
            title="Training Progress Across All Nodes", height=600, hovermode="x unified"
        )

        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Loss", row=1, col=1)
        fig.update_yaxes(title_text="Accuracy", row=2, col=1)

        return fig

    def create_network_topology_chart(self, node_connections: Dict[str, List[str]]) -> go.Figure:
        """Create network topology visualization"""

        import networkx as nx

        # Create network graph
        G = nx.Graph()

        # Add nodes and edges
        for node_id, connected_nodes in node_connections.items():
            G.add_node(node_id)
            for connected_id in connected_nodes:
                G.add_edge(node_id, connected_id)

        # Calculate layout
        pos = nx.spring_layout(G, k=1, iterations=50)

        # Extract node and edge coordinates
        node_x = [pos[node][0] for node in G.nodes()]
        node_y = [pos[node][1] for node in G.nodes()]

        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        # Create traces
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y, line=dict(width=0.5, color="#888"), hoverinfo="none", mode="lines"
        )

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers",
            hoverinfo="text",
            text=[f"Node {node_id[:8]}" for node_id in G.nodes()],
            marker=dict(
                showscale=True,
                colorscale="Viridis",
                reversescale=True,
                color=[len(list(G.neighbors(node))) for node in G.nodes()],
                size=10,
                colorbar=dict(thickness=15, len=0.5, x=1.05, title="Connections"),
                line=dict(width=2),
            ),
        )

        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title="Network Topology",
                titlefont_size=16,
                showlegend=False,
                hovermode="closest",
                margin=dict(b=20, l=5, r=5, t=40),
                annotations=[
                    dict(
                        text="Node size represents number of connections",
                        showarrow=False,
                        xref="paper",
                        yref="paper",
                        x=0.005,
                        y=-0.002,
                        xanchor="left",
                        yanchor="bottom",
                        font=dict(size=12),
                    )
                ],
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            ),
        )

        return fig

    def create_resource_utilization_chart(self) -> go.Figure:
        """Create resource utilization chart"""

        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=("CPU Usage", "Memory Usage", "GPU Utilization", "Network Traffic"),
            vertical_spacing=0.15,
        )

        # System health data
        health_data = list(self.metrics_collector.system_health)

        if health_data:
            timestamps = [datetime.fromtimestamp(h.timestamp) for h in health_data]

            # CPU Usage
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=[h.cpu_usage for h in health_data],
                    mode="lines",
                    fill="tozeroy",
                    name="CPU %",
                ),
                row=1,
                col=1,
            )

            # Memory Usage
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=[h.memory_usage for h in health_data],
                    mode="lines",
                    fill="tozeroy",
                    name="Memory %",
                ),
                row=1,
                col=2,
            )

        # GPU utilization from training metrics
        gpu_data = defaultdict(list)
        gpu_timestamps = defaultdict(list)

        for node_id, metrics_deque in self.metrics_collector.training_metrics.items():
            for metric in list(metrics_deque)[-50:]:  # Last 50 points
                gpu_data[node_id].append(metric.gpu_utilization)
                gpu_timestamps[node_id].append(datetime.fromtimestamp(metric.timestamp))

        for node_id in gpu_data:
            fig.add_trace(
                go.Scatter(
                    x=gpu_timestamps[node_id],
                    y=gpu_data[node_id],
                    mode="lines",
                    name=f"Node {node_id[:8]} GPU",
                ),
                row=2,
                col=1,
            )

        # Network traffic from network metrics
        network_data = list(self.metrics_collector.network_metrics)
        if network_data:
            net_timestamps = [datetime.fromtimestamp(n.timestamp) for n in network_data]

            fig.add_trace(
                go.Scatter(
                    x=net_timestamps,
                    y=[n.data_transmitted_mb for n in network_data],
                    mode="lines+markers",
                    name="Data Transmitted (MB)",
                ),
                row=2,
                col=2,
            )

        fig.update_layout(title="Resource Utilization", height=600, showlegend=True)

        return fig

    def create_node_comparison_chart(self) -> go.Figure:
        """Create node performance comparison chart"""

        # Collect latest metrics for each node
        node_data = []

        for node_id, metrics_deque in self.metrics_collector.training_metrics.items():
            if metrics_deque:
                latest_metric = list(metrics_deque)[-1]
                node_data.append(
                    {
                        "node_id": node_id[:8],
                        "loss": latest_metric.loss,
                        "accuracy": latest_metric.accuracy,
                        "batch_time": latest_metric.batch_time,
                        "memory_usage": latest_metric.memory_usage,
                        "gpu_utilization": latest_metric.gpu_utilization,
                    }
                )

        if not node_data:
            return go.Figure()

        df = pd.DataFrame(node_data)

        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Loss by Node",
                "Accuracy by Node",
                "Batch Time by Node",
                "GPU Utilization by Node",
            ),
        )

        # Loss comparison
        fig.add_trace(go.Bar(x=df["node_id"], y=df["loss"], name="Loss"), row=1, col=1)

        # Accuracy comparison
        fig.add_trace(go.Bar(x=df["node_id"], y=df["accuracy"], name="Accuracy"), row=1, col=2)

        # Batch time comparison
        fig.add_trace(go.Bar(x=df["node_id"], y=df["batch_time"], name="Batch Time"), row=2, col=1)

        # GPU utilization comparison
        fig.add_trace(go.Bar(x=df["node_id"], y=df["gpu_utilization"], name="GPU %"), row=2, col=2)

        fig.update_layout(title="Node Performance Comparison", height=600, showlegend=False)

        return fig


class DashboardApp:
    """Main dashboard application using Dash"""

    def __init__(self, metrics_collector: MetricsCollector, port: int = 8050):
        self.metrics_collector = metrics_collector
        self.visualization_engine = VisualizationEngine(metrics_collector)
        self.port = port

        # Initialize Dash app
        self.app = dash.Dash(__name__)
        self.setup_layout()
        self.setup_callbacks()

        self.logger = logging.getLogger(__name__)

    def setup_layout(self):
        """Setup dashboard layout"""

        self.app.layout = html.Div(
            [
                html.H1(
                    "Decentralized AGI Training Dashboard",
                    style={"textAlign": "center", "marginBottom": 30},
                ),
                # Status cards
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3("Active Nodes"),
                                html.H2(id="active-nodes", children="0"),
                            ],
                            className="status-card",
                            style={
                                "width": "23%",
                                "display": "inline-block",
                                "margin": "1%",
                                "padding": "20px",
                                "backgroundColor": "#f0f0f0",
                                "textAlign": "center",
                            },
                        ),
                        html.Div(
                            [
                                html.H3("Current Round"),
                                html.H2(id="current-round", children="0"),
                            ],
                            className="status-card",
                            style={
                                "width": "23%",
                                "display": "inline-block",
                                "margin": "1%",
                                "padding": "20px",
                                "backgroundColor": "#f0f0f0",
                                "textAlign": "center",
                            },
                        ),
                        html.Div(
                            [
                                html.H3("Average Accuracy"),
                                html.H2(id="avg-accuracy", children="0.0%"),
                            ],
                            className="status-card",
                            style={
                                "width": "23%",
                                "display": "inline-block",
                                "margin": "1%",
                                "padding": "20px",
                                "backgroundColor": "#f0f0f0",
                                "textAlign": "center",
                            },
                        ),
                        html.Div(
                            [
                                html.H3("Network Health"),
                                html.H2(id="network-health", children="Unknown"),
                            ],
                            className="status-card",
                            style={
                                "width": "23%",
                                "display": "inline-block",
                                "margin": "1%",
                                "padding": "20px",
                                "backgroundColor": "#f0f0f0",
                                "textAlign": "center",
                            },
                        ),
                    ]
                ),
                # Main charts
                dcc.Tabs(
                    [
                        dcc.Tab(
                            label="Training Progress",
                            children=[
                                dcc.Graph(id="training-progress-chart"),
                                dcc.Interval(id="progress-interval", interval=5000, n_intervals=0),
                            ],
                        ),
                        dcc.Tab(
                            label="Network Topology",
                            children=[
                                dcc.Graph(id="network-topology-chart"),
                                dcc.Interval(id="topology-interval", interval=10000, n_intervals=0),
                            ],
                        ),
                        dcc.Tab(
                            label="Resource Utilization",
                            children=[
                                dcc.Graph(id="resource-utilization-chart"),
                                dcc.Interval(id="resource-interval", interval=3000, n_intervals=0),
                            ],
                        ),
                        dcc.Tab(
                            label="Node Comparison",
                            children=[
                                dcc.Graph(id="node-comparison-chart"),
                                dcc.Interval(
                                    id="comparison-interval", interval=5000, n_intervals=0
                                ),
                            ],
                        ),
                        dcc.Tab(
                            label="Detailed Metrics",
                            children=[
                                html.Div(id="detailed-metrics-table"),
                                dcc.Interval(id="details-interval", interval=2000, n_intervals=0),
                            ],
                        ),
                    ]
                ),
                # Global update interval
                dcc.Interval(id="global-interval", interval=1000, n_intervals=0),
            ]
        )

    def setup_callbacks(self):
        """Setup dashboard callbacks"""

        @self.app.callback(
            [
                Output("active-nodes", "children"),
                Output("current-round", "children"),
                Output("avg-accuracy", "children"),
                Output("network-health", "children"),
            ],
            [Input("global-interval", "n_intervals")],
        )
        def update_status_cards(n):
            # Get current round summary
            summary = self.metrics_collector.get_current_round_summary()

            active_nodes = summary.get("participating_nodes", 0)
            current_round = summary.get("round_id", "N/A")
            avg_accuracy = summary.get("avg_accuracy", 0.0) * 100

            # Get network health
            health = self.metrics_collector.get_network_health_status()
            health_status = health.get("status", "Unknown")

            return (str(active_nodes), current_round, f"{avg_accuracy:.1f}%", health_status.upper())

        @self.app.callback(
            Output("training-progress-chart", "figure"), [Input("progress-interval", "n_intervals")]
        )
        def update_training_progress(n):
            return self.visualization_engine.create_training_progress_chart()

        @self.app.callback(
            Output("network-topology-chart", "figure"), [Input("topology-interval", "n_intervals")]
        )
        def update_network_topology(n):
            # Mock network connections for demo
            node_connections = {}
            nodes = list(self.metrics_collector.training_metrics.keys())

            for i, node in enumerate(nodes):
                # Connect each node to 2-3 other nodes
                connected = []
                for j in range(min(3, len(nodes) - 1)):
                    target_idx = (i + j + 1) % len(nodes)
                    connected.append(nodes[target_idx])
                node_connections[node] = connected

            return self.visualization_engine.create_network_topology_chart(node_connections)

        @self.app.callback(
            Output("resource-utilization-chart", "figure"),
            [Input("resource-interval", "n_intervals")],
        )
        def update_resource_utilization(n):
            return self.visualization_engine.create_resource_utilization_chart()

        @self.app.callback(
            Output("node-comparison-chart", "figure"), [Input("comparison-interval", "n_intervals")]
        )
        def update_node_comparison(n):
            return self.visualization_engine.create_node_comparison_chart()

        @self.app.callback(
            Output("detailed-metrics-table", "children"), [Input("details-interval", "n_intervals")]
        )
        def update_detailed_metrics(n):
            # Create detailed metrics table
            table_data = []

            for node_id, metrics_deque in self.metrics_collector.training_metrics.items():
                if metrics_deque:
                    latest = list(metrics_deque)[-1]
                    trends = self.metrics_collector.get_node_performance_trends(node_id)

                    table_data.append(
                        {
                            "Node ID": node_id[:12],
                            "Round": latest.round_id,
                            "Loss": f"{latest.loss:.4f}",
                            "Accuracy": f"{latest.accuracy:.3f}",
                            "Batch Time": f"{latest.batch_time:.2f}s",
                            "Communication Time": f"{latest.communication_time:.2f}s",
                            "GPU Usage": f"{latest.gpu_utilization:.1f}%",
                            "Memory Usage": f"{latest.memory_usage:.1f}%",
                            "Loss Trend": f"{'↑' if trends.get('loss_trend', 0) > 0 else '↓'}{abs(trends.get('loss_trend', 0)):.4f}",
                            "Accuracy Trend": f"{'↑' if trends.get('accuracy_trend', 0) > 0 else '↓'}{abs(trends.get('accuracy_trend', 0)):.4f}",
                        }
                    )

            if not table_data:
                return html.Div("No data available")

            df = pd.DataFrame(table_data)

            return html.Table(
                [
                    html.Thead([html.Tr([html.Th(col) for col in df.columns])]),
                    html.Tbody(
                        [
                            html.Tr([html.Td(df.iloc[i][col]) for col in df.columns])
                            for i in range(len(df))
                        ]
                    ),
                ],
                style={"width": "100%", "margin": "20px"},
            )

    def run(self, debug: bool = False, host: str = "0.0.0.0"):
        """Run the dashboard"""
        self.logger.info(f"Starting dashboard on {host}:{self.port}")
        self.app.run_server(debug=debug, host=host, port=self.port)


class MetricsWebSocketServer:
    """WebSocket server for real-time metrics streaming"""

    def __init__(self, metrics_collector: MetricsCollector, port: int = 8765):
        self.metrics_collector = metrics_collector
        self.port = port
        self.clients = set()
        self.running = False

        self.logger = logging.getLogger(__name__)

    async def register_client(self, websocket, path):
        """Register new WebSocket client"""
        self.clients.add(websocket)
        self.logger.info(f"Client connected: {websocket.remote_address}")

        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
            self.logger.info(f"Client disconnected: {websocket.remote_address}")

    async def broadcast_metrics(self):
        """Broadcast metrics to all connected clients"""
        while self.running:
            try:
                # Prepare metrics data
                current_summary = self.metrics_collector.get_current_round_summary()
                health_status = self.metrics_collector.get_network_health_status()

                metrics_update = {
                    "type": "metrics_update",
                    "timestamp": time.time(),
                    "round_summary": current_summary,
                    "health_status": health_status,
                    "active_nodes": len(self.metrics_collector.current_round_metrics),
                }

                # Broadcast to all clients
                if self.clients:
                    message = json.dumps(metrics_update)
                    disconnected_clients = []

                    for client in self.clients:
                        try:
                            await client.send(message)
                        except Exception as e:
                            self.logger.warning(f"Failed to send to client: {e}")
                            disconnected_clients.append(client)

                    # Remove disconnected clients
                    for client in disconnected_clients:
                        self.clients.discard(client)

                await asyncio.sleep(1)  # Broadcast every second

            except Exception as e:
                self.logger.error(f"Error broadcasting metrics: {e}")
                await asyncio.sleep(5)

    async def start_server(self):
        """Start WebSocket server"""
        import websockets

        self.running = True

        # Start server
        server = await websockets.serve(self.register_client, "0.0.0.0", self.port)
        self.logger.info(f"WebSocket server started on port {self.port}")

        # Start broadcasting
        broadcast_task = asyncio.create_task(self.broadcast_metrics())

        try:
            await server.wait_closed()
        finally:
            self.running = False
            broadcast_task.cancel()


class PerformanceAnalyzer:
    """Advanced performance analysis and anomaly detection"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.anomaly_threshold = 2.0  # Standard deviations
        self.logger = logging.getLogger(__name__)

    def detect_performance_anomalies(self) -> List[Dict[str, Any]]:
        """Detect performance anomalies across nodes"""
        anomalies = []

        # Collect recent metrics
        all_recent_metrics = []
        node_recent_metrics = {}

        for node_id, metrics_deque in self.metrics_collector.training_metrics.items():
            recent = list(metrics_deque)[-10:]  # Last 10 metrics
            if recent:
                node_recent_metrics[node_id] = recent
                all_recent_metrics.extend(recent)

        if len(all_recent_metrics) < 10:
            return anomalies

        # Calculate global statistics
        global_loss_mean = np.mean([m.loss for m in all_recent_metrics])
        global_loss_std = np.std([m.loss for m in all_recent_metrics])

        global_accuracy_mean = np.mean([m.accuracy for m in all_recent_metrics])
        global_accuracy_std = np.std([m.accuracy for m in all_recent_metrics])

        global_batch_time_mean = np.mean([m.batch_time for m in all_recent_metrics])
        global_batch_time_std = np.std([m.batch_time for m in all_recent_metrics])

        # Check each node for anomalies
        for node_id, recent_metrics in node_recent_metrics.items():
            node_loss_mean = np.mean([m.loss for m in recent_metrics])
            node_accuracy_mean = np.mean([m.accuracy for m in recent_metrics])
            node_batch_time_mean = np.mean([m.batch_time for m in recent_metrics])

            # Loss anomaly
            if global_loss_std > 0:
                loss_z_score = abs(node_loss_mean - global_loss_mean) / global_loss_std
                if loss_z_score > self.anomaly_threshold:
                    anomalies.append(
                        {
                            "node_id": node_id,
                            "type": "loss_anomaly",
                            "severity": "high" if loss_z_score > 3 else "medium",
                            "z_score": loss_z_score,
                            "node_value": node_loss_mean,
                            "global_mean": global_loss_mean,
                        }
                    )

            # Accuracy anomaly
            if global_accuracy_std > 0:
                accuracy_z_score = (
                    abs(node_accuracy_mean - global_accuracy_mean) / global_accuracy_std
                )
                if accuracy_z_score > self.anomaly_threshold:
                    anomalies.append(
                        {
                            "node_id": node_id,
                            "type": "accuracy_anomaly",
                            "severity": "high" if accuracy_z_score > 3 else "medium",
                            "z_score": accuracy_z_score,
                            "node_value": node_accuracy_mean,
                            "global_mean": global_accuracy_mean,
                        }
                    )

            # Performance anomaly (batch time)
            if global_batch_time_std > 0:
                time_z_score = (
                    abs(node_batch_time_mean - global_batch_time_mean) / global_batch_time_std
                )
                if time_z_score > self.anomaly_threshold:
                    anomalies.append(
                        {
                            "node_id": node_id,
                            "type": "performance_anomaly",
                            "severity": "high" if time_z_score > 3 else "medium",
                            "z_score": time_z_score,
                            "node_value": node_batch_time_mean,
                            "global_mean": global_batch_time_mean,
                        }
                    )

        return anomalies

    def generate_training_insights(self) -> Dict[str, Any]:
        """Generate insights about training progress"""
        insights = {
            "convergence_analysis": self._analyze_convergence(),
            "node_efficiency_ranking": self._rank_node_efficiency(),
            "communication_bottlenecks": self._detect_communication_bottlenecks(),
            "resource_recommendations": self._generate_resource_recommendations(),
        }

        return insights

    def _analyze_convergence(self) -> Dict[str, Any]:
        """Analyze convergence patterns"""
        network_metrics = list(self.metrics_collector.network_metrics)

        if len(network_metrics) < 5:
            return {"status": "insufficient_data"}

        recent_losses = [m.avg_loss for m in network_metrics[-10:]]
        recent_accuracies = [m.avg_accuracy for m in network_metrics[-10:]]

        # Simple trend analysis
        loss_trend = np.polyfit(range(len(recent_losses)), recent_losses, 1)[0]
        accuracy_trend = np.polyfit(range(len(recent_accuracies)), recent_accuracies, 1)[0]

        convergence_status = (
            "converging" if loss_trend < -0.01 and accuracy_trend > 0.01 else "stable"
        )
        if abs(loss_trend) < 0.001 and abs(accuracy_trend) < 0.001:
            convergence_status = "converged"

        return {
            "status": convergence_status,
            "loss_trend": loss_trend,
            "accuracy_trend": accuracy_trend,
            "recent_loss_mean": np.mean(recent_losses),
            "recent_accuracy_mean": np.mean(recent_accuracies),
        }

    def _rank_node_efficiency(self) -> List[Dict[str, Any]]:
        """Rank nodes by training efficiency"""
        node_rankings = []

        for node_id in self.metrics_collector.training_metrics:
            trends = self.metrics_collector.get_node_performance_trends(node_id)

            if trends:
                # Efficiency score based on accuracy improvement and batch time
                accuracy_trend = trends.get("accuracy_trend", 0)
                batch_time_avg = trends.get("batch_time_avg", float("inf"))

                efficiency_score = accuracy_trend / (batch_time_avg + 1e-6)

                node_rankings.append(
                    {
                        "node_id": node_id,
                        "efficiency_score": efficiency_score,
                        "accuracy_trend": accuracy_trend,
                        "batch_time_avg": batch_time_avg,
                    }
                )

        # Sort by efficiency score
        node_rankings.sort(key=lambda x: x["efficiency_score"], reverse=True)

        return node_rankings

    def _detect_communication_bottlenecks(self) -> Dict[str, Any]:
        """Detect communication bottlenecks"""
        all_comm_times = []

        for metrics_deque in self.metrics_collector.training_metrics.values():
            recent_metrics = list(metrics_deque)[-5:]
            all_comm_times.extend([m.communication_time for m in recent_metrics])

        if not all_comm_times:
            return {"status": "no_data"}

        mean_comm_time = np.mean(all_comm_times)
        std_comm_time = np.std(all_comm_times)

        bottleneck_threshold = mean_comm_time + 2 * std_comm_time

        return {
            "mean_communication_time": mean_comm_time,
            "bottleneck_threshold": bottleneck_threshold,
            "high_latency_ratio": sum(1 for t in all_comm_times if t > bottleneck_threshold)
            / len(all_comm_times),
        }

    def _generate_resource_recommendations(self) -> List[Dict[str, str]]:
        """Generate resource optimization recommendations"""
        recommendations = []

        # Analyze resource utilization
        all_gpu_utils = []
        all_memory_utils = []

        for metrics_deque in self.metrics_collector.training_metrics.values():
            recent_metrics = list(metrics_deque)[-5:]
            all_gpu_utils.extend([m.gpu_utilization for m in recent_metrics])
            all_memory_utils.extend([m.memory_usage for m in recent_metrics])

        if all_gpu_utils:
            avg_gpu_util = np.mean(all_gpu_utils)
            if avg_gpu_util < 70:
                recommendations.append(
                    {
                        "type": "gpu_underutilization",
                        "message": f"GPU utilization is low ({avg_gpu_util:.1f}%). Consider increasing batch size or model complexity.",
                        "priority": "medium",
                    }
                )
            elif avg_gpu_util > 95:
                recommendations.append(
                    {
                        "type": "gpu_overutilization",
                        "message": f"GPU utilization is very high ({avg_gpu_util:.1f}%). Consider reducing batch size to prevent OOM errors.",
                        "priority": "high",
                    }
                )

        if all_memory_utils:
            avg_memory_util = np.mean(all_memory_utils)
            if avg_memory_util > 90:
                recommendations.append(
                    {
                        "type": "memory_pressure",
                        "message": f"Memory usage is high ({avg_memory_util:.1f}%). Consider reducing batch size or model size.",
                        "priority": "high",
                    }
                )

        return recommendations
