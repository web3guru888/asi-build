"""Tests for neuromorphic computing module (Candidate 10)."""
import pytest
psutil = pytest.importorskip("psutil", reason="psutil not installed")
import numpy as np


class TestSpikeEvent:
    """Test spike event dataclass."""

    def test_create_spike(self):
        from src.asi_build.neuromorphic.core.neural_base import SpikeEvent
        spike = SpikeEvent(neuron_id=1, timestamp=0.01, amplitude=1.0)
        assert spike.neuron_id == 1
        assert spike.timestamp == 0.01

    def test_synaptic_event(self):
        from src.asi_build.neuromorphic.core.neural_base import SynapticEvent
        se = SynapticEvent(pre_neuron_id=1, post_neuron_id=2,
                           timestamp=0.01, weight=0.5, delay=0.001)
        assert se.event_type == "excitatory"


class TestNeuronBase:
    """Test neuron base class functionality."""

    def _make_neuron(self):
        """Create a concrete neuron for testing."""
        from src.asi_build.neuromorphic.core.neural_base import NeuronBase
        import numpy as np

        class TestNeuron(NeuronBase):
            def compute_membrane_dynamics(self, dt):
                tau = self.parameters['tau_membrane']
                v_rest = self.parameters['v_rest']
                v_mem = self.state['membrane_potential']
                i_input = self.state['input_current']
                cap = self.parameters['capacitance']
                return (-(v_mem - v_rest) / tau + i_input / cap)

        return TestNeuron(neuron_id=0, neuron_type="excitatory")

    def test_initial_state(self):
        n = self._make_neuron()
        assert n.state['membrane_potential'] == -65.0e-3
        assert n.state['input_current'] == 0.0

    def test_add_input_current(self):
        n = self._make_neuron()
        n.add_input_current(1e-9)
        assert n.state['input_current'] == 1e-9

    def test_refractory_initially_false(self):
        n = self._make_neuron()
        assert not n.is_refractory()

    def test_spike_on_threshold(self):
        n = self._make_neuron()
        n.state['membrane_potential'] = -49.0e-3  # above threshold
        assert n._check_spike_condition() is True

    def test_spike_generation(self):
        n = self._make_neuron()
        n.current_time = 0.01
        n._generate_spike()
        assert len(n.state['spike_times']) == 1
        assert n.state['membrane_potential'] == n.parameters['v_reset']

    def test_firing_rate_empty(self):
        n = self._make_neuron()
        assert n.get_firing_rate() == 0.0

    def test_reset(self):
        n = self._make_neuron()
        n.state['membrane_potential'] = -30e-3
        n.state['spike_times'] = [0.01, 0.02]
        n.reset()
        assert n.state['membrane_potential'] == n.parameters['v_rest']
        assert len(n.state['spike_times']) == 0

    def test_update_step(self):
        n = self._make_neuron()
        n.add_input_current(5e-9)  # strong input
        n.update(1e-3)  # 1ms step
        # Potential should have changed
        assert n.state['membrane_potential'] != -65.0e-3

    def test_spike_triggers_refractory(self):
        n = self._make_neuron()
        n.current_time = 0.01
        n._generate_spike()
        assert n.state['refractory_until'] > 0.01

    def test_monitoring(self):
        n = self._make_neuron()
        n.enable_monitoring(['membrane_potential'])
        n.update(1e-3)
        data = n.get_recorded_data('membrane_potential')
        assert len(data) >= 1


class TestSynapseBase:
    """Test synapse base functionality."""

    def _make_synapse(self):
        from src.asi_build.neuromorphic.core.neural_base import NeuronBase, SynapseBase, SpikeEvent

        class SimpleNeuron(NeuronBase):
            def compute_membrane_dynamics(self, dt):
                return 0.0

        class SimpleSynapse(SynapseBase):
            def compute_psc(self, spike_event):
                return self.state['weight'] * spike_event.amplitude

            def _update_plasticity(self, dt):
                pass

        pre = SimpleNeuron(0)
        post = SimpleNeuron(1)
        syn = SimpleSynapse(100, pre, post)
        return syn, pre, post

    def test_initial_weight(self):
        syn, _, _ = self._make_synapse()
        assert syn.get_weight() == 1.0

    def test_set_weight_clipped(self):
        syn, _, _ = self._make_synapse()
        syn.set_weight(10.0)
        assert syn.get_weight() == syn.parameters['max_weight']
        syn.set_weight(-5.0)
        assert syn.get_weight() == syn.parameters['min_weight']

    def test_receive_spike_adds_delay(self):
        syn, pre, post = self._make_synapse()
        from src.asi_build.neuromorphic.core.neural_base import SpikeEvent
        spike = SpikeEvent(neuron_id=0, timestamp=0.01)
        syn.receive_spike(spike)
        assert len(syn.state['delayed_spikes']) == 1
        delayed = syn.state['delayed_spikes'][0]
        assert delayed.timestamp > 0.01

    def test_process_delayed_spike_delivers_current(self):
        syn, pre, post = self._make_synapse()
        from src.asi_build.neuromorphic.core.neural_base import SpikeEvent
        spike = SpikeEvent(neuron_id=0, timestamp=0.001)
        syn.receive_spike(spike)
        syn.current_time = 0.01  # well past delay
        syn._process_delayed_spikes()
        assert post.state['input_current'] != 0.0


class TestSTDP:
    """Test STDP learning parameters."""

    def test_stdp_parameters_defaults(self):
        from src.asi_build.neuromorphic.learning.stdp import STDPParameters
        params = STDPParameters()
        assert params.tau_plus == 20.0e-3
        assert params.a_plus == 0.01
        assert params.a_minus == 0.012
        assert params.w_min == 0.0
        assert params.w_max == 1.0


class TestChipSimulator:
    """Test neuromorphic chip simulation."""

    def test_chip_config(self):
        from src.asi_build.neuromorphic.hardware.chip_simulator import ChipConfig, ChipType
        config = ChipConfig(chip_type=ChipType.LOIHI, num_cores=4)
        assert config.num_cores == 4
        assert config.neurons_per_core == 1024

    def test_core_state_init(self):
        from src.asi_build.neuromorphic.hardware.chip_simulator import CoreState
        core = CoreState(core_id=0, num_neurons=10, utilization=0.5)
        assert core.core_id == 0
        assert core.utilization == 0.5
