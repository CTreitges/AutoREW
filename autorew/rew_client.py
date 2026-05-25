"""REW REST API Client für AutoREW."""

from __future__ import annotations

import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Callable, Optional

import requests

from autorew.models import (
    AudioConfig,
    AudioDevice,
    DriverType,
    EQCommand,
    FilterSetting,
    FilterType,
    FrequencyPoint,
    FrequencyResponse,
    ImpulseResponse,
    MeasurementSummary,
    ProcessCommand,
    SweepConfig,
    TargetSettings,
)

logger = logging.getLogger(__name__)


class REWClientError(Exception):
    """Fehler bei der REW API-Kommunikation."""


class REWClient:
    """HTTP-Client für die REW REST API."""

    def __init__(self, host: str = "localhost", port: int = 4735, timeout: float = 10.0):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self._session = requests.Session()
        self._webhook_server: Optional[HTTPServer] = None
        self._webhook_callbacks: dict[str, Callable] = {}

    # ─── Helpers ──────────────────────────────────────────────

    def _get(self, path: str, **params) -> Any:
        try:
            r = self._session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
            r.raise_for_status()
            return r.json() if r.content else None
        except requests.ConnectionError:
            raise REWClientError("Keine Verbindung zu REW. Ist die API aktiviert?")
        except requests.HTTPError as e:
            raise REWClientError(f"REW API Fehler: {e.response.status_code} - {e.response.text}")

    def _post(self, path: str, data: Any = None, **params) -> Any:
        try:
            r = self._session.post(f"{self.base_url}{path}", json=data, params=params, timeout=self.timeout)
            r.raise_for_status()
            return r.json() if r.content else None
        except requests.ConnectionError:
            raise REWClientError("Keine Verbindung zu REW. Ist die API aktiviert?")
        except requests.HTTPError as e:
            raise REWClientError(f"REW API Fehler: {e.response.status_code} - {e.response.text}")

    def _put(self, path: str, data: Any = None) -> Any:
        try:
            r = self._session.put(f"{self.base_url}{path}", json=data, timeout=self.timeout)
            r.raise_for_status()
            return r.json() if r.content else None
        except requests.ConnectionError:
            raise REWClientError("Keine Verbindung zu REW. Ist die API aktiviert?")
        except requests.HTTPError as e:
            raise REWClientError(f"REW API Fehler: {e.response.status_code} - {e.response.text}")

    def _delete(self, path: str) -> Any:
        try:
            r = self._session.delete(f"{self.base_url}{path}", timeout=self.timeout)
            r.raise_for_status()
            return r.json() if r.content else None
        except requests.ConnectionError:
            raise REWClientError("Keine Verbindung zu REW. Ist die API aktiviert?")
        except requests.HTTPError as e:
            raise REWClientError(f"REW API Fehler: {e.response.status_code} - {e.response.text}")

    # ─── Connection ───────────────────────────────────────────

    def is_connected(self) -> bool:
        try:
            self._get("/application/commands")
            return True
        except REWClientError:
            return False

    def get_commands(self) -> list[str]:
        result = self._get("/application/commands")
        return result if isinstance(result, list) else []

    def is_pro_license(self) -> bool:
        """Prüft ob Pro-Lizenz vorhanden (Sweep-Messung benötigt Pro)."""
        try:
            commands = self._get("/measure/commands")
            if isinstance(commands, list):
                return "SPL" in commands
            return False
        except REWClientError:
            return False

    def set_blocking(self, blocking: bool = True) -> None:
        self._post("/application/blocking", {"blocking": blocking})

    # ─── Audio Configuration ──────────────────────────────────

    def get_audio_status(self) -> dict:
        return self._get("/audio") or {}

    def get_driver_type(self) -> str:
        result = self._get("/audio/driver")
        return result.get("driver", "Java") if isinstance(result, dict) else "Java"

    def set_driver_type(self, driver: DriverType) -> None:
        self._post("/audio/driver", {"driver": driver.value})

    def get_sample_rates(self) -> list[int]:
        result = self._get("/audio/samplerates")
        if not isinstance(result, list):
            return []
        rates = []
        for item in result:
            if isinstance(item, dict):
                rates.append(int(item.get("value", 0)))
            elif isinstance(item, (int, float)):
                rates.append(int(item))
        return [r for r in rates if r > 0]

    def get_sample_rate(self) -> int:
        result = self._get("/audio/samplerate")
        if isinstance(result, dict):
            return int(result.get("samplerate", 48000))
        return 48000

    def set_sample_rate(self, rate: int) -> None:
        self._post("/audio/samplerate", {"samplerate": rate})

    # --- Java Audio ---

    def get_java_input_devices(self) -> list[str]:
        result = self._get("/audio/java/input-devices")
        return result if isinstance(result, list) else []

    def get_java_output_devices(self) -> list[str]:
        result = self._get("/audio/java/output-devices")
        return result if isinstance(result, list) else []

    def set_java_input_device(self, device: str) -> None:
        self._post("/audio/java/input-device", {"input-device": device})

    def set_java_output_device(self, device: str) -> None:
        self._post("/audio/java/output-device", {"output-device": device})

    def set_java_input_channel(self, channel: int) -> None:
        self._post("/audio/java/input-channel", {"input-channel": channel})

    def set_java_output_channel(self, channel: int) -> None:
        self._post("/audio/java/output-channel", {"output-channel": channel})

    def get_java_num_input_channels(self) -> int:
        result = self._get("/audio/java/num-input-channels")
        if isinstance(result, dict):
            return int(result.get("num-input-channels", 2))
        return 2

    # --- ASIO Audio ---

    def get_asio_devices(self) -> list[str]:
        result = self._get("/audio/asio/devices")
        return result if isinstance(result, list) else []

    def set_asio_device(self, device: str) -> None:
        self._post("/audio/asio/device", {"device": device})

    def get_asio_inputs(self) -> list[str]:
        result = self._get("/audio/asio/inputs")
        return result if isinstance(result, list) else []

    def get_asio_outputs(self) -> list[str]:
        result = self._get("/audio/asio/outputs")
        return result if isinstance(result, list) else []

    def set_asio_input(self, inp: str) -> None:
        self._post("/audio/asio/input", {"input": inp})

    def set_asio_output(self, out: str) -> None:
        self._post("/audio/asio/output", {"output": out})

    # --- Mic Calibration ---

    def load_mic_cal(self, path: str) -> None:
        self._put("/audio/input-cal", {"path": path.replace("\\", "/")})

    def get_mic_cal(self) -> str:
        result = self._get("/audio/input-cal")
        if isinstance(result, dict):
            return result.get("path", "")
        return ""

    # ─── Measurements ─────────────────────────────────────────

    def get_measurements(self) -> list[MeasurementSummary]:
        result = self._get("/measurements")
        if not isinstance(result, list):
            return []
        measurements = []
        for i, item in enumerate(result):
            if isinstance(item, dict):
                measurements.append(MeasurementSummary(
                    index=item.get("index", i),
                    uuid=item.get("uuid", ""),
                    name=item.get("name", f"Measurement {i}"),
                    notes=item.get("notes", ""),
                ))
            elif isinstance(item, str):
                measurements.append(MeasurementSummary(index=i, name=item))
        return measurements

    def get_measurement(self, index: int) -> MeasurementSummary:
        result = self._get(f"/measurements/{index}")
        if isinstance(result, dict):
            return MeasurementSummary(
                index=result.get("index", index),
                uuid=result.get("uuid", ""),
                name=result.get("name", ""),
                notes=result.get("notes", ""),
            )
        return MeasurementSummary(index=index)

    def set_measurement_name(self, index: int, name: str, notes: str = "") -> None:
        data = {"name": name}
        if notes:
            data["notes"] = notes
        self._put(f"/measurements/{index}", data)

    def delete_measurement(self, index: int) -> None:
        self._delete(f"/measurements/{index}")

    def get_selected_measurement(self) -> int:
        result = self._get("/measurements/selected")
        if isinstance(result, dict):
            return int(result.get("selected", 0))
        return 0

    def set_selected_measurement(self, index: int) -> None:
        self._post("/measurements/selected", {"selected": index})

    # ─── Frequency & Impulse Response ─────────────────────────

    def get_frequency_response(self, index: int, smoothing: str = "1/12",
                                start_freq: float = 20.0, ppo: int = 96) -> FrequencyResponse:
        result = self._get(
            f"/measurements/{index}/frequency-response",
            smoothing=smoothing, startFrequency=start_freq, ppo=ppo,
        )
        points = []
        if isinstance(result, dict):
            freqs = result.get("frequencies", [])
            mags = result.get("magnitudes", [])
            phases = result.get("phases", [])
            for i in range(min(len(freqs), len(mags))):
                p = FrequencyPoint(
                    frequency=freqs[i],
                    magnitude=mags[i],
                    phase=phases[i] if i < len(phases) else None,
                )
                points.append(p)
        return FrequencyResponse(data=points, smoothing=smoothing)

    def get_impulse_response(self, index: int, windowed: bool = False) -> ImpulseResponse:
        params = {}
        if windowed:
            params["windowed"] = "true"
        result = self._get(f"/measurements/{index}/impulse-response", **params)
        if isinstance(result, dict):
            return ImpulseResponse(
                sample_rate=result.get("sampleRate", 48000),
                data=result.get("data", []),
                peak_index=result.get("peakIndex", 0),
                peak_time_ms=result.get("peakTimeMs", 0.0),
            )
        return ImpulseResponse()

    # ─── Sweep / Measure ──────────────────────────────────────

    def configure_sweep(self, config: SweepConfig) -> None:
        self._post("/measure/sweep/configuration", {
            "startFrequency": config.start_freq,
            "endFrequency": config.end_freq,
            "length": config.length.value,
        })
        self._post("/measure/level", {"level": config.level, "unit": config.level_unit})
        self._post("/measure/sweep/repetitions", {"repetitions": config.repetitions})
        self._post("/measure/start-delay", {"startDelay": config.start_delay})

    def start_sweep(self) -> None:
        """Startet eine SPL-Messung (benötigt Pro-Lizenz)."""
        self._post("/measure/command", {"command": "SPL"})

    def set_measurement_notes(self, notes: str) -> None:
        self._post("/measure/notes", {"notes": notes})

    def set_measurement_name_format(self, naming: str) -> None:
        self._post("/measure/naming", {"naming": naming})

    def set_output_channel(self, channel: int) -> None:
        """Setzt den Ausgabekanal für die nächste Messung."""
        driver = self.get_driver_type()
        if driver == "ASIO":
            outputs = self.get_asio_outputs()
            if 1 <= channel <= len(outputs):
                self.set_asio_output(outputs[channel - 1])
        else:
            self.set_java_output_channel(channel)

    # ─── Processing ───────────────────────────────────────────

    def process_measurements(self, indices: list[int], command: ProcessCommand,
                              params: Optional[dict] = None) -> None:
        data: dict[str, Any] = {
            "command": command.value,
            "measurements": indices,
        }
        if params:
            data["parameters"] = params
        self._post("/measurements/process-measurements", data)

    def get_process_result(self) -> dict:
        return self._get("/measurements/process-result") or {}

    def align_spl(self, indices: list[int], target_db: float = 85.0,
                   freq_hz: float = 1000.0, span_octaves: float = 2.0) -> None:
        self.process_measurements(indices, ProcessCommand.ALIGN_SPL, {
            "targetdB": str(target_db),
            "frequencyHz": str(freq_hz),
            "spanOctaves": span_octaves,
        })

    def time_align(self, indices: list[int]) -> None:
        self.process_measurements(indices, ProcessCommand.TIME_ALIGN)

    def cross_corr_align(self, indices: list[int]) -> None:
        self.process_measurements(indices, ProcessCommand.CROSS_CORR_ALIGN)

    def average_measurements(self, indices: list[int],
                              method: ProcessCommand = ProcessCommand.VECTOR_AVERAGE) -> None:
        self.process_measurements(indices, method)

    # ─── Alignment Tool ───────────────────────────────────────

    def configure_alignment(self, index_a: int, index_b: int,
                             frequency: float = 1000.0) -> None:
        self._post("/alignment-tool/index-a", {"index-a": index_a})
        self._post("/alignment-tool/index-b", {"index-b": index_b})
        self._post("/alignment-tool/frequency", {"frequency": frequency})

    def run_alignment(self) -> dict:
        commands = self._get("/alignment-tool/commands")
        if isinstance(commands, list) and commands:
            self._post("/alignment-tool/command", {"command": commands[0]})
        return self.get_alignment_result()

    def get_alignment_result(self) -> dict:
        return self._get("/alignment-tool/result") or {}

    def set_alignment_delay(self, side: str, delay_ms: float) -> None:
        self._post(f"/alignment-tool/delay-{side}", {f"delay-{side}": delay_ms})

    def set_alignment_gain(self, side: str, gain_db: float) -> None:
        self._post(f"/alignment-tool/gain-{side}", {f"gain-{side}": gain_db})

    def set_alignment_invert(self, side: str, invert: bool) -> None:
        self._post(f"/alignment-tool/invert-{side}", {f"invert-{side}": invert})

    def get_aligned_response(self) -> FrequencyResponse:
        result = self._get("/alignment-tool/aligned-frequency-response")
        return self._parse_freq_response(result)

    # ─── EQ ───────────────────────────────────────────────────

    def get_equalisers(self) -> list[str]:
        result = self._get("/eq/equalisers")
        return result if isinstance(result, list) else []

    def set_equaliser(self, index: int, equaliser: str) -> None:
        self._post(f"/measurements/{index}/equaliser", {"equaliser": equaliser})

    def get_filters(self, index: int) -> list[FilterSetting]:
        result = self._get(f"/measurements/{index}/filters")
        filters = []
        if isinstance(result, list):
            for i, f in enumerate(result):
                if isinstance(f, dict):
                    filters.append(FilterSetting(
                        index=i,
                        enabled=f.get("enabled", True),
                        filter_type=FilterType(f.get("type", "PK")),
                        frequency=f.get("frequency", 1000.0),
                        gain=f.get("gain", 0.0),
                        q=f.get("q", 1.0),
                    ))
        return filters

    def set_filters(self, index: int, filters: list[FilterSetting]) -> None:
        filter_list = []
        for f in filters:
            filter_list.append({
                "enabled": f.enabled,
                "type": f.filter_type.value,
                "frequency": f.frequency,
                "gain": f.gain,
                "q": f.q,
            })
        self._post(f"/measurements/{index}/filters", filter_list)

    def set_target_settings(self, index: int, settings: TargetSettings) -> None:
        self._post(f"/measurements/{index}/target-settings", {
            "targetLevel": settings.target_level,
            "shape": settings.shape,
        })

    def set_target_level(self, index: int, level: float) -> None:
        self._post(f"/measurements/{index}/target-level", {"targetLevel": level})

    def eq_command(self, index: int, command: EQCommand) -> None:
        self._post(f"/measurements/{index}/eq/command", {"command": command.value})

    def match_target(self, index: int) -> list[FilterSetting]:
        self.eq_command(index, EQCommand.MATCH_TARGET)
        return self.get_filters(index)

    def get_predicted_response(self, index: int, smoothing: str = "1/12") -> FrequencyResponse:
        result = self._get(f"/measurements/{index}/eq/frequency-response", smoothing=smoothing)
        return self._parse_freq_response(result)

    def get_target_response(self, index: int) -> FrequencyResponse:
        result = self._get(f"/measurements/{index}/target-response")
        return self._parse_freq_response(result)

    def get_filters_impulse_response(self, index: int, sample_rate: int = 48000,
                                      length: int = 65536) -> ImpulseResponse:
        result = self._get(
            f"/measurements/{index}/filters-impulse-response",
            samplerate=sample_rate, length=length,
        )
        if isinstance(result, dict):
            return ImpulseResponse(
                sample_rate=sample_rate,
                data=result.get("data", []),
            )
        return ImpulseResponse(sample_rate=sample_rate)

    # ─── Signal Generator ─────────────────────────────────────

    def start_generator(self) -> None:
        self._post("/generator/command", {"command": "Start"})

    def stop_generator(self) -> None:
        self._post("/generator/command", {"command": "Stop"})

    def set_generator_signal(self, signal: str) -> None:
        self._put("/generator/signal", {"signal": signal})

    def set_generator_level(self, level: float, unit: str = "dBFS") -> None:
        self._post("/generator/level", {"level": level, "unit": unit})

    def set_generator_frequency(self, freq: float) -> None:
        self._post("/generator/frequency", {"frequency": freq})

    # ─── SPL Meter ────────────────────────────────────────────

    def start_spl_meter(self, meter_id: int = 1) -> None:
        self._post(f"/spl-meter/{meter_id}/command", {"command": "Start"})

    def stop_spl_meter(self, meter_id: int = 1) -> None:
        self._post(f"/spl-meter/{meter_id}/command", {"command": "Stop"})

    def get_spl_levels(self, meter_id: int = 1) -> dict:
        return self._get(f"/spl-meter/{meter_id}/levels") or {}

    def configure_spl_meter(self, meter_id: int = 1, weighting: str = "C",
                             filter_speed: str = "Slow") -> None:
        self._post(f"/spl-meter/{meter_id}/configuration", {
            "mode": "SPL",
            "weighting": weighting,
            "filter": filter_speed,
        })

    # ─── RTA ──────────────────────────────────────────────────

    def get_rta_status(self) -> dict:
        return self._get("/rta/status") or {}

    def get_rta_levels(self) -> dict:
        return self._get("/rta/levels") or {}

    # ─── Webhooks / Subscriptions ─────────────────────────────

    def _start_webhook_server(self, port: int = 5374) -> None:
        """Startet einen lokalen HTTP-Server für REW-Webhooks."""
        if self._webhook_server:
            return

        client = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                import json
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}
                callback = client._webhook_callbacks.get(self.path)
                if callback:
                    callback(body)
                self.send_response(200)
                self.end_headers()

            def log_message(self, format, *args):
                pass  # Suppress logging

        self._webhook_server = HTTPServer(("127.0.0.1", port), Handler)
        thread = threading.Thread(target=self._webhook_server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"Webhook-Server gestartet auf Port {port}")

    def subscribe(self, rew_endpoint: str, callback: Callable,
                   callback_path: str = "/webhook", port: int = 5374,
                   params: Optional[dict] = None) -> None:
        self._start_webhook_server(port)
        self._webhook_callbacks[callback_path] = callback
        data: dict[str, Any] = {"url": f"http://127.0.0.1:{port}{callback_path}"}
        if params:
            data["parameters"] = params
        self._post(rew_endpoint, data)

    def subscribe_measurement_progress(self, callback: Callable, port: int = 5374) -> None:
        self.subscribe("/measure/subscribe", callback, "/measure-progress", port)

    def subscribe_measurement_list(self, callback: Callable, port: int = 5374) -> None:
        self.subscribe("/measurements/subscribe", callback, "/measurement-list", port)

    def subscribe_eq_progress(self, callback: Callable, port: int = 5374) -> None:
        self.subscribe("/eq/subscribe", callback, "/eq-progress", port)

    def subscribe_spl_levels(self, callback: Callable, meter_id: int = 1,
                              port: int = 5374) -> None:
        self.subscribe(
            f"/spl-meter/{meter_id}/subscribe", callback,
            f"/spl-levels-{meter_id}", port,
        )

    def stop_webhooks(self) -> None:
        if self._webhook_server:
            self._webhook_server.shutdown()
            self._webhook_server = None
            self._webhook_callbacks.clear()

    # ─── Import ───────────────────────────────────────────────

    def import_frequency_response(self, path: str) -> None:
        self._post("/import/frequency-response", {"path": path.replace("\\", "/")})

    def import_impulse_response(self, path: str, channel: str = "1") -> None:
        self._post("/import/impulse-response", {
            "path": path.replace("\\", "/"),
            "channels": channel,
        })

    # ─── Utilities ────────────────────────────────────────────

    def _parse_freq_response(self, result: Any) -> FrequencyResponse:
        points = []
        if isinstance(result, dict):
            freqs = result.get("frequencies", [])
            mags = result.get("magnitudes", [])
            phases = result.get("phases", [])
            for i in range(min(len(freqs), len(mags))):
                points.append(FrequencyPoint(
                    frequency=freqs[i],
                    magnitude=mags[i],
                    phase=phases[i] if i < len(phases) else None,
                ))
        return FrequencyResponse(data=points)

    def close(self) -> None:
        self.stop_webhooks()
        self._session.close()
