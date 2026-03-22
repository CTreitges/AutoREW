"""Demo-Client fuer AutoREW - simuliert REW API ohne echte Verbindung."""

from __future__ import annotations

import math
import random
from typing import Any, Callable, Optional

from autorew.models import (
    DriverType,
    FilterSetting,
    FilterType,
    FrequencyPoint,
    FrequencyResponse,
    ImpulseResponse,
    MeasurementSummary,
    SweepConfig,
    TargetSettings,
)
from autorew.rew_client import REWClient


class DemoClient(REWClient):
    """Simuliert die REW API mit realistischen Demo-Daten."""

    def __init__(self):
        super().__init__()
        self._connected = True
        self._driver = "ASIO"
        self._sample_rate = 48000
        self._measurements: list[MeasurementSummary] = []
        self._filters: dict[int, list[FilterSetting]] = {}
        self._output_channel = 1
        self._mic_cal = ""
        self._seed_demo_measurements()

    def _seed_demo_measurements(self):
        self._measurements = [
            MeasurementSummary(index=0, name="Main L - Pos 1", notes="Demo"),
            MeasurementSummary(index=1, name="Main L - Pos 2", notes="Demo"),
            MeasurementSummary(index=2, name="Main R - Pos 1", notes="Demo"),
            MeasurementSummary(index=3, name="Main R - Pos 2", notes="Demo"),
            MeasurementSummary(index=4, name="Sub - Pos 1", notes="Demo"),
        ]

    # --- Connection ---

    def is_connected(self) -> bool:
        return self._connected

    def is_pro_license(self) -> bool:
        return True

    def set_blocking(self, blocking: bool = True) -> None:
        pass

    # --- Audio ---

    def get_audio_status(self) -> dict:
        return {"driver": self._driver, "sampleRate": self._sample_rate}

    def get_driver_type(self) -> str:
        return self._driver

    def set_driver_type(self, driver: DriverType) -> None:
        self._driver = driver.value

    def get_sample_rates(self) -> list[int]:
        return [44100, 48000, 88200, 96000]

    def get_sample_rate(self) -> int:
        return self._sample_rate

    def set_sample_rate(self, rate: int) -> None:
        self._sample_rate = rate

    def get_java_input_devices(self) -> list[str]:
        return ["Primary Sound Driver", "Realtek HD Audio Input", "Flow 8 USB Input"]

    def get_java_output_devices(self) -> list[str]:
        return ["Primary Sound Driver", "Realtek HD Audio Output", "Flow 8 USB Output"]

    def set_java_input_device(self, device: str) -> None:
        pass

    def set_java_output_device(self, device: str) -> None:
        pass

    def set_java_input_channel(self, channel: int) -> None:
        pass

    def set_java_output_channel(self, channel: int) -> None:
        self._output_channel = channel

    def get_java_num_input_channels(self) -> int:
        return 2

    def get_asio_devices(self) -> list[str]:
        return ["ASIO4ALL v2", "Flow 8 USB ASIO", "Focusrite USB ASIO"]

    def set_asio_device(self, device: str) -> None:
        pass

    def get_asio_inputs(self) -> list[str]:
        return ["Input 1", "Input 2"]

    def get_asio_outputs(self) -> list[str]:
        return ["Output 1", "Output 2", "Output 3", "Output 4"]

    def set_asio_input(self, inp: str) -> None:
        pass

    def set_asio_output(self, out: str) -> None:
        pass

    def load_mic_cal(self, path: str) -> None:
        self._mic_cal = path

    def get_mic_cal(self) -> str:
        return self._mic_cal

    # --- Measurements ---

    def get_measurements(self) -> list[MeasurementSummary]:
        return list(self._measurements)

    def get_measurement(self, index: int) -> MeasurementSummary:
        if 0 <= index < len(self._measurements):
            return self._measurements[index]
        return MeasurementSummary(index=index, name=f"Demo {index}")

    def set_measurement_name(self, index: int, name: str, notes: str = "") -> None:
        if 0 <= index < len(self._measurements):
            self._measurements[index].name = name

    def delete_measurement(self, index: int) -> None:
        self._measurements = [m for m in self._measurements if m.index != index]

    def get_selected_measurement(self) -> int:
        return 0

    def set_selected_measurement(self, index: int) -> None:
        pass

    # --- Frequency & Impulse Response ---

    def _generate_freq_response(self, index: int, smoothing: str = "1/12") -> FrequencyResponse:
        random.seed(index * 42)
        points = []
        freqs = []
        f = 20.0
        while f <= 20000:
            freqs.append(f)
            f *= 1.02

        for freq in freqs:
            # Realistische PA-Kurve: flach in der Mitte, Roll-off an den Raendern
            base = 85.0
            # LF roll-off
            if freq < 60:
                base -= 12 * (1 - freq / 60)
            # HF roll-off
            if freq > 12000:
                base -= 8 * ((freq - 12000) / 8000)

            # Raummoden und Resonanzen
            variation = 3 * math.sin(math.log2(freq) * 2.5 + index)
            variation += 2 * math.sin(math.log2(freq) * 5.1 + index * 0.7)
            noise = random.gauss(0, 0.8)

            # Sub hat anderen Charakter
            if index == 4:
                if freq > 200:
                    base -= 24 * ((freq - 200) / 800)
                    base = max(base, 30)
                else:
                    base += 3

            mag = base + variation + noise
            points.append(FrequencyPoint(frequency=freq, magnitude=mag))

        return FrequencyResponse(data=points, smoothing=smoothing)

    def get_frequency_response(self, index: int, smoothing: str = "1/12",
                                start_freq: float = 20.0, ppo: int = 96) -> FrequencyResponse:
        return self._generate_freq_response(index, smoothing)

    def get_impulse_response(self, index: int, windowed: bool = False) -> ImpulseResponse:
        data = [0.0] * 4096
        peak = 1024 + index * 50
        data[peak] = 1.0
        for i in range(1, 20):
            data[peak + i] = math.exp(-i * 0.3) * (0.5 if i % 2 == 0 else -0.3)
        return ImpulseResponse(
            sample_rate=self._sample_rate,
            data=data,
            peak_index=peak,
            peak_time_ms=peak / self._sample_rate * 1000,
        )

    # --- Sweep ---

    def configure_sweep(self, config: SweepConfig) -> None:
        pass

    def start_sweep(self) -> None:
        # Simuliere eine neue Messung
        idx = len(self._measurements)
        self._measurements.append(MeasurementSummary(
            index=idx,
            name=f"Messung {idx + 1}",
            notes="Demo Sweep",
        ))

    def set_measurement_notes(self, notes: str) -> None:
        pass

    def set_output_channel(self, channel: int) -> None:
        self._output_channel = channel

    # --- Processing ---

    def process_measurements(self, indices, command, params=None) -> None:
        pass

    def align_spl(self, indices, target_db=85.0, freq_hz=1000.0, span_octaves=2.0) -> None:
        pass

    def time_align(self, indices) -> None:
        pass

    def average_measurements(self, indices, method=None) -> None:
        # Simuliere: neue gemittelte Messung
        idx = len(self._measurements)
        self._measurements.append(MeasurementSummary(
            index=idx, name=f"Average ({len(indices)} Messungen)", notes="Demo",
        ))

    # --- Alignment ---

    def configure_alignment(self, index_a, index_b, frequency=1000.0) -> None:
        pass

    def run_alignment(self) -> dict:
        delay = round(random.uniform(0.5, 8.0), 3)
        gain = round(random.uniform(-3.0, 3.0), 1)
        return {"delay-b": delay, "gain-b": gain}

    def get_alignment_result(self) -> dict:
        return self.run_alignment()

    # --- EQ ---

    def get_equalisers(self) -> list[str]:
        return ["Generic", "miniDSP", "Behringer DEQ2496"]

    def set_equaliser(self, index: int, equaliser: str) -> None:
        pass

    def get_filters(self, index: int) -> list[FilterSetting]:
        return self._filters.get(index, [])

    def set_filters(self, index: int, filters: list[FilterSetting]) -> None:
        self._filters[index] = filters

    def set_target_level(self, index: int, level: float) -> None:
        pass

    def set_target_settings(self, index: int, settings: TargetSettings) -> None:
        pass

    def match_target(self, index: int) -> list[FilterSetting]:
        random.seed(index * 7)
        filters = []
        typical_freqs = [63, 125, 250, 500, 800, 1200, 2000, 3500, 6000, 10000]
        for i, freq in enumerate(typical_freqs):
            gain = round(random.uniform(-6, 2), 1)
            q = round(random.uniform(1.0, 8.0), 2)
            filters.append(FilterSetting(
                index=i, enabled=abs(gain) > 0.5,
                filter_type=FilterType.PK, frequency=freq, gain=gain, q=q,
            ))
        self._filters[index] = filters
        return filters

    def get_predicted_response(self, index: int, smoothing: str = "1/12") -> FrequencyResponse:
        resp = self._generate_freq_response(index, smoothing)
        # Geglaettete Version (naeher am Target)
        for p in resp.data:
            diff = 75.0 - p.magnitude
            p.magnitude += diff * 0.7
        return resp

    def get_target_response(self, index: int) -> FrequencyResponse:
        points = []
        f = 20.0
        while f <= 20000:
            mag = 75.0
            if f < 60:
                mag -= 6 * (1 - f / 60)
            if f > 16000:
                mag -= 3 * ((f - 16000) / 4000)
            points.append(FrequencyPoint(frequency=f, magnitude=mag))
            f *= 1.02
        return FrequencyResponse(data=points)

    def get_filters_impulse_response(self, index: int, sample_rate: int = 48000,
                                      length: int = 65536) -> ImpulseResponse:
        data = [0.0] * length
        data[0] = 1.0
        return ImpulseResponse(sample_rate=sample_rate, data=data)

    # --- Generator / SPL ---

    def start_generator(self) -> None:
        pass

    def stop_generator(self) -> None:
        pass

    def set_generator_signal(self, signal: str) -> None:
        pass

    def set_generator_level(self, level: float, unit: str = "dBFS") -> None:
        pass

    def set_generator_frequency(self, freq: float) -> None:
        pass

    def start_spl_meter(self, meter_id: int = 1) -> None:
        pass

    def stop_spl_meter(self, meter_id: int = 1) -> None:
        pass

    def get_spl_levels(self, meter_id: int = 1) -> dict:
        return {"spl": 75.0 + random.gauss(0, 2), "peak": 82.0}

    # --- Webhooks (no-op) ---

    def subscribe(self, *args, **kwargs) -> None:
        pass

    def subscribe_measurement_progress(self, *args, **kwargs) -> None:
        pass

    def subscribe_measurement_list(self, *args, **kwargs) -> None:
        pass

    def stop_webhooks(self) -> None:
        pass

    def close(self) -> None:
        pass
