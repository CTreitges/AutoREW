"""Datenmodelle fuer AutoREW."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# --- Enums ---

class ZoneType(str, Enum):
    MAIN_LEFT = "Main L"
    MAIN_RIGHT = "Main R"
    SUB = "Sub"
    DELAY_LEFT = "Delay L"
    DELAY_RIGHT = "Delay R"
    FILL_LEFT = "Fill L"
    FILL_RIGHT = "Fill R"
    INFILL = "Infill"
    MONITOR = "Monitor"
    CUSTOM = "Custom"


class DriverType(str, Enum):
    JAVA = "Java"
    ASIO = "ASIO"


class SweepLength(str, Enum):
    S_256K = "256k"
    S_512K = "512k"
    S_1M = "1M"


class MeasurementMode(str, Enum):
    SINGLE = "Single"
    REPEATED = "Repeated"
    RAMPED = "Ramped"
    SEQUENTIAL = "Sequential"


class ProcessCommand(str, Enum):
    ALIGN_SPL = "Align SPL"
    TIME_ALIGN = "Time align"
    ALIGN_IR_START = "Align IR start"
    CROSS_CORR_ALIGN = "Cross corr align"
    VECTOR_AVERAGE = "Vector average"
    RMS_AVERAGE = "RMS average"
    DB_AVERAGE = "dB average"
    SMOOTH = "Smooth"


class EQCommand(str, Enum):
    CALC_TARGET_LEVEL = "Calculate target level"
    MATCH_TARGET = "Match target"
    OPTIMISE_GAINS = "Optimise gains"
    OPTIMISE_GAINS_QS = "Optimise gains and Qs"
    OPTIMISE_ALL = "Optimise gains, Qs and Fcs"
    GENERATE_PREDICTED = "Generate predicted measurement"
    GENERATE_FILTERS = "Generate filters measurement"
    GENERATE_TARGET = "Generate target measurement"


# --- Audio Config ---

class AudioDevice(BaseModel):
    name: str
    index: int = 0


class AudioConfig(BaseModel):
    driver: DriverType = DriverType.JAVA
    input_device: str = ""
    output_device: str = ""
    input_channel: int = 1
    output_channel: int = 1
    sample_rate: int = 48000
    mic_cal_path: str = ""


# --- Measurement Positions ---

POSITION_PRESETS: dict[int, list[str]] = {
    1: [
        "FOH (Front of House) - Mischpultposition, zentral im Publikumsbereich",
    ],
    2: [
        "FOH (Front of House) - Mischpultposition, zentral im Publikumsbereich",
        "Off-Axis - 2-3m seitlich versetzt von der Mittelachse",
    ],
    3: [
        "FOH (Front of House) - Mischpultposition, zentral im Publikumsbereich",
        "Nah - Ca. 1/3 der Distanz zwischen PA und FOH, mittig",
        "Fern - Ca. 2/3 der Distanz, leicht seitlich versetzt",
    ],
    4: [
        "FOH (Front of House) - Mischpultposition, zentral im Publikumsbereich",
        "Nah Mitte - Ca. 1/3 der Distanz, mittig",
        "Fern Links - Ca. 2/3 der Distanz, links versetzt",
        "Fern Rechts - Ca. 2/3 der Distanz, rechts versetzt",
    ],
    5: [
        "FOH (Front of House) - Mischpultposition, zentral",
        "Nah Mitte - Ca. 1/3 der Distanz, mittig",
        "Nah Seite - Ca. 1/3 der Distanz, seitlich am Rand der Abdeckung",
        "Fern Mitte - Ca. 2/3 der Distanz, mittig",
        "Fern Seite - Ca. 2/3 der Distanz, am Rand der Abdeckung",
    ],
}

SUB_POSITION_PRESETS: dict[int, list[str]] = {
    1: [
        "FOH - Mischpultposition, Mikro auf Ohrenhoehe",
    ],
    2: [
        "FOH - Mischpultposition, Mikro auf Ohrenhoehe",
        "Nah - 3-5m vor dem Sub, bodennah (ca. 1m Hoehe)",
    ],
    3: [
        "FOH - Mischpultposition, Mikro auf Ohrenhoehe",
        "Nah - 3-5m vor dem Sub, bodennah",
        "Seite - Seitlich versetzt, halbe Raumdistanz",
    ],
}


def get_position_description(position: int, total: int, is_sub: bool = False) -> str:
    """Gibt die Beschreibung fuer eine Messposition zurueck."""
    presets = SUB_POSITION_PRESETS if is_sub else POSITION_PRESETS
    best_key = 1
    for key in sorted(presets.keys()):
        if key <= total:
            best_key = key
    descriptions = presets[best_key]
    if position <= len(descriptions):
        return descriptions[position - 1]
    return f"Position {position} - Mikrofon umsetzen, gleichmaessig verteilt im Abdeckungsbereich"


# --- Zones ---

class Zone(BaseModel):
    name: str
    zone_type: ZoneType = ZoneType.CUSTOM
    output_channel: int = 1
    crossover_freq: Optional[float] = None
    is_sub: bool = False
    measurement_ids: list[int] = Field(default_factory=list)
    positions: int = 1

    def get_position_name(self, position: int) -> str:
        return get_position_description(position, self.positions, self.is_sub)

    @property
    def display_name(self) -> str:
        if self.zone_type == ZoneType.CUSTOM:
            return self.name
        return self.zone_type.value


# --- Sweep / Measurement ---

class SweepConfig(BaseModel):
    start_freq: float = 20.0
    end_freq: float = 20000.0
    length: SweepLength = SweepLength.S_512K
    level: float = -12.0
    level_unit: str = "dBFS"
    repetitions: int = 1
    start_delay: float = 2.0


class MeasurementSummary(BaseModel):
    index: int
    uuid: str = ""
    name: str = ""
    notes: str = ""
    has_data: bool = True


class FrequencyPoint(BaseModel):
    frequency: float
    magnitude: float
    phase: Optional[float] = None


class FrequencyResponse(BaseModel):
    data: list[FrequencyPoint] = Field(default_factory=list)
    smoothing: str = "None"
    unit: str = "SPL"


class ImpulseResponse(BaseModel):
    sample_rate: float = 48000.0
    data: list[float] = Field(default_factory=list)
    peak_index: int = 0
    peak_time_ms: float = 0.0


# --- EQ / Filter ---

class FilterType(str, Enum):
    PK = "PK"
    LP = "LP"
    HP = "HP"
    LS = "LS"
    HS = "HS"
    NO = "NO"
    AP = "AP"


class FilterSetting(BaseModel):
    index: int = 0
    enabled: bool = True
    filter_type: FilterType = FilterType.PK
    frequency: float = 1000.0
    gain: float = 0.0
    q: float = 1.0


class TargetSettings(BaseModel):
    target_level: float = 75.0
    shape: str = "None"
    lf_rise: float = 0.0
    lf_cutoff: float = 0.0
    hf_fall: float = 0.0
    hf_cutoff: float = 20000.0


class CrossoverType(str, Enum):
    BUTTERWORTH = "Butterworth"
    BESSEL = "Bessel"
    LINKWITZ_RILEY = "Linkwitz-Riley"


class EqualizerPreset(BaseModel):
    """Beschreibt die Faehigkeiten eines DSP/Equalizers."""
    name: str
    peq_bands: int = 9
    filter_types: list[FilterType] = Field(default_factory=lambda: [FilterType.PK])
    freq_min: float = 20.0
    freq_max: float = 20000.0
    gain_min: float = -15.0
    gain_max: float = 15.0
    q_min: float = 0.4
    q_max: float = 128.0
    has_crossover: bool = False
    crossover_types: list[CrossoverType] = Field(default_factory=list)
    crossover_slopes: list[int] = Field(default_factory=list)
    has_delay: bool = False
    delay_max_ms: float = 0.0
    has_limiter: bool = False
    has_compressor: bool = False
    has_geq: bool = False
    geq_bands: int = 0
    inputs: int = 0
    outputs: int = 0
    sample_rate: int = 48000
    notes: str = ""


EQUALIZER_PRESETS: dict[str, EqualizerPreset] = {
    "Generic": EqualizerPreset(
        name="Generic",
        peq_bands=20,
        filter_types=[FilterType.PK, FilterType.LS, FilterType.HS,
                      FilterType.LP, FilterType.HP, FilterType.NO, FilterType.AP],
        gain_min=-30.0,
        gain_max=30.0,
        q_min=0.1,
        q_max=200.0,
        notes="Generisches Preset ohne Hardware-Einschraenkungen.",
    ),
    "t.racks DSP 306": EqualizerPreset(
        name="t.racks DSP 306",
        peq_bands=9,
        filter_types=[FilterType.PK, FilterType.LS, FilterType.HS,
                      FilterType.LP, FilterType.HP, FilterType.NO, FilterType.AP],
        freq_min=20.0,
        freq_max=20000.0,
        gain_min=-15.0,
        gain_max=15.0,
        q_min=0.4,
        q_max=128.0,
        has_crossover=True,
        crossover_types=[CrossoverType.BUTTERWORTH, CrossoverType.BESSEL, CrossoverType.LINKWITZ_RILEY],
        crossover_slopes=[6, 12, 18, 24, 48],
        has_delay=True,
        delay_max_ms=680.0,
        has_limiter=True,
        has_compressor=True,
        has_geq=True,
        geq_bands=31,
        inputs=3,
        outputs=6,
        sample_rate=96000,
        notes="3-In / 6-Out Speaker Management. 9 PEQ pro Kanal, "
              "31-Band GEQ, Crossover (BW/BS/LR bis 48dB/Oct), "
              "Delay bis 680ms, Limiter & Kompressor pro Ausgang.",
    ),
    "t.racks DS 2/4": EqualizerPreset(
        name="t.racks DS 2/4",
        peq_bands=5,
        filter_types=[FilterType.PK, FilterType.LS, FilterType.HS,
                      FilterType.LP, FilterType.HP],
        freq_min=20.0,
        freq_max=20000.0,
        gain_min=-12.0,
        gain_max=12.0,
        q_min=0.5,
        q_max=10.0,
        has_crossover=True,
        crossover_types=[CrossoverType.BUTTERWORTH],
        crossover_slopes=[6, 12, 18, 24, 48],
        has_delay=True,
        delay_max_ms=7.0,
        has_limiter=True,
        inputs=2,
        outputs=4,
        sample_rate=96000,
        notes="2-In / 4-Out Speaker Processor. 5 PEQ pro Ausgang (ISO-Terz-Frequenzraster), "
              "Q 0.5-10, Gain +/-12 dB in 1-dB-Schritten, "
              "HP/LP 6-48 dB/Oct, Delay 0-7 ms in 0.5-ms-Schritten, Limiter.",
    ),
    "miniDSP 2x4 HD": EqualizerPreset(
        name="miniDSP 2x4 HD",
        peq_bands=10,
        filter_types=[FilterType.PK, FilterType.LS, FilterType.HS,
                      FilterType.LP, FilterType.HP],
        gain_min=-16.0,
        gain_max=16.0,
        q_min=0.5,
        q_max=16.0,
        has_crossover=True,
        crossover_types=[CrossoverType.BUTTERWORTH, CrossoverType.LINKWITZ_RILEY],
        crossover_slopes=[6, 12, 24, 48],
        has_delay=True,
        delay_max_ms=7.5,
        inputs=2,
        outputs=4,
        sample_rate=96000,
        notes="2-In / 4-Out. 10 PEQ pro Kanal, Crossover (BW/LR).",
    ),
    "Behringer DEQ2496": EqualizerPreset(
        name="Behringer DEQ2496",
        peq_bands=10,
        filter_types=[FilterType.PK, FilterType.LS, FilterType.HS, FilterType.NO],
        gain_min=-15.0,
        gain_max=15.0,
        q_min=0.4,
        q_max=100.0,
        has_delay=True,
        delay_max_ms=300.0,
        has_limiter=True,
        inputs=2,
        outputs=2,
        sample_rate=96000,
        notes="Stereo 10-Band PEQ + 31-Band GEQ. "
              "AES/EBU und S/PDIF Digital I/O.",
    ),
}


# --- Alignment ---

class AlignmentResult(BaseModel):
    zone_a: str = ""
    zone_b: str = ""
    delay_ms: float = 0.0
    delay_samples: int = 0
    gain_diff_db: float = 0.0
    polarity_inverted: bool = False


class DelayRecommendation(BaseModel):
    zone_name: str
    delay_ms: float = 0.0
    delay_meters: float = 0.0
    level_db: float = 0.0


# --- Workflow ---

class WorkflowStep(str, Enum):
    SETUP = "setup"
    CONNECTION = "connection"
    ZONE_SETUP = "zone_setup"
    MEASUREMENT = "measurement"
    ANALYSIS = "analysis"
    EQ = "eq"
    EXPORT = "export"


# --- Setup Wizard ---

class TopConfig(str, Enum):
    STEREO = "Stereo L+R"
    MONO = "Mono"
    STEREO_DELAY = "Stereo + Delay"


class SetupConfig(BaseModel):
    """Konfiguration aus dem Setup-Wizard."""
    top_config: TopConfig = TopConfig.STEREO
    num_subs: int = 1
    num_positions: int = 3
    dsp_preset_name: str = "Generic"
    target_curve_path: str = ""

    def generate_zones(self) -> list[Zone]:
        """Generiert Zonen basierend auf der Setup-Konfiguration."""
        zones: list[Zone] = []
        ch = 1
        pos = self.num_positions
        sub_pos = max(1, pos - 1)

        if self.top_config in (TopConfig.STEREO, TopConfig.STEREO_DELAY):
            zones.append(Zone(name="Top L", zone_type=ZoneType.MAIN_LEFT,
                              output_channel=ch, positions=pos))
            ch += 1
            zones.append(Zone(name="Top R", zone_type=ZoneType.MAIN_RIGHT,
                              output_channel=ch, positions=pos))
            ch += 1
        else:
            zones.append(Zone(name="Top", zone_type=ZoneType.CUSTOM,
                              output_channel=ch, positions=pos))
            ch += 1

        if self.top_config == TopConfig.STEREO_DELAY:
            zones.append(Zone(name="Delay L", zone_type=ZoneType.DELAY_LEFT,
                              output_channel=ch, positions=max(1, pos - 1)))
            ch += 1
            zones.append(Zone(name="Delay R", zone_type=ZoneType.DELAY_RIGHT,
                              output_channel=ch, positions=max(1, pos - 1)))
            ch += 1

        for i in range(self.num_subs):
            name = "Sub" if self.num_subs == 1 else f"Sub {i + 1}"
            zones.append(Zone(name=name, zone_type=ZoneType.SUB,
                              output_channel=ch, is_sub=True,
                              crossover_freq=120.0, positions=sub_pos))
            ch += 1

        return zones


# --- Project Config ---

class ProjectConfig(BaseModel):
    """Gesamte Projekt-Konfiguration."""
    name: str = "Neues Projekt"
    audio: AudioConfig = Field(default_factory=AudioConfig)
    zones: list[Zone] = Field(default_factory=list)
    sweep: SweepConfig = Field(default_factory=SweepConfig)
    target: TargetSettings = Field(default_factory=TargetSettings)
    delays: list[DelayRecommendation] = Field(default_factory=list)
    filters: dict[str, list[FilterSetting]] = Field(default_factory=dict)
    filter_warnings: dict[str, list[dict]] = Field(default_factory=dict)
    alignments: list[AlignmentResult] = Field(default_factory=list)
    current_step: WorkflowStep = WorkflowStep.SETUP
    is_pro_license: bool = False
    setup: SetupConfig = Field(default_factory=SetupConfig)


# --- Device Presets ---

class DevicePreset(BaseModel):
    """Vordefinierte Audio-Interface-Konfiguration."""
    name: str
    driver: DriverType = DriverType.JAVA
    input_hint: str = ""
    output_hint: str = ""
    input_channel: int = 1
    sample_rate: int = 48000
    usb_channels_in: int = 2
    usb_channels_out: int = 2
    notes: str = ""


DEVICE_PRESETS: dict[str, DevicePreset] = {
    "Behringer Flow 8": DevicePreset(
        name="Behringer Flow 8",
        driver=DriverType.ASIO,
        input_hint="Flow 8",
        output_hint="Flow 8",
        input_channel=1,
        sample_rate=48000,
        usb_channels_in=2,
        usb_channels_out=4,
        notes="ASIO4ALL empfohlen. EQ/Kompressor am Messkanal deaktivieren. "
              "USB-Outputs: Ch 1-2 = Main, Ch 3-4 = Aux.",
    ),
    "Behringer XR18 / X Air": DevicePreset(
        name="Behringer XR18 / X Air",
        driver=DriverType.ASIO,
        input_hint="X Air",
        output_hint="X Air",
        input_channel=1,
        sample_rate=48000,
        usb_channels_in=18,
        usb_channels_out=18,
        notes="Eigener ASIO-Treiber verfuegbar (X-USB). "
              "Alle 18 Kanaele einzeln ueber USB erreichbar.",
    ),
    "Behringer X32 / M32": DevicePreset(
        name="Behringer X32 / M32",
        driver=DriverType.ASIO,
        input_hint="X32",
        output_hint="X32",
        input_channel=1,
        sample_rate=48000,
        usb_channels_in=32,
        usb_channels_out=32,
        notes="X-USB Karte: 32x32 Kanaele. "
              "Routing ueber X32-Edit oder am Pult konfigurieren.",
    ),
    "Focusrite Scarlett": DevicePreset(
        name="Focusrite Scarlett",
        driver=DriverType.ASIO,
        input_hint="Focusrite",
        output_hint="Focusrite",
        input_channel=1,
        sample_rate=48000,
        usb_channels_in=2,
        usb_channels_out=2,
        notes="Focusrite ASIO-Treiber verwenden. "
              "Kanalanzahl je nach Modell (2i2, 4i4, 18i20 etc.).",
    ),
    "RME Fireface / Babyface": DevicePreset(
        name="RME Fireface / Babyface",
        driver=DriverType.ASIO,
        input_hint="RME",
        output_hint="RME",
        input_channel=1,
        sample_rate=48000,
        usb_channels_in=2,
        usb_channels_out=2,
        notes="RME ASIO-Treiber (TotalMix). Niedrigste Latenz. "
              "Routing ueber TotalMix FX konfigurieren.",
    ),
    "MOTU M2 / M4": DevicePreset(
        name="MOTU M2 / M4",
        driver=DriverType.ASIO,
        input_hint="MOTU",
        output_hint="MOTU",
        input_channel=1,
        sample_rate=48000,
        usb_channels_in=2,
        usb_channels_out=2,
        notes="MOTU ASIO-Treiber verwenden. Loopback-Funktion deaktivieren.",
    ),
}

MANUAL_DEVICE_NAME = "Manuell konfigurieren"


# --- Zone Presets ---

ZONE_PRESETS: dict[str, list[Zone]] = {
    "Stereo + Sub": [
        Zone(name="Main L", zone_type=ZoneType.MAIN_LEFT, output_channel=1),
        Zone(name="Main R", zone_type=ZoneType.MAIN_RIGHT, output_channel=2),
        Zone(name="Sub", zone_type=ZoneType.SUB, output_channel=3, is_sub=True, crossover_freq=120.0),
    ],
    "Stereo (ohne Sub)": [
        Zone(name="Main L", zone_type=ZoneType.MAIN_LEFT, output_channel=1),
        Zone(name="Main R", zone_type=ZoneType.MAIN_RIGHT, output_channel=2),
    ],
    "LR + Delay + Fill": [
        Zone(name="Main L", zone_type=ZoneType.MAIN_LEFT, output_channel=1),
        Zone(name="Main R", zone_type=ZoneType.MAIN_RIGHT, output_channel=2),
        Zone(name="Sub", zone_type=ZoneType.SUB, output_channel=3, is_sub=True, crossover_freq=120.0),
        Zone(name="Delay L", zone_type=ZoneType.DELAY_LEFT, output_channel=4),
        Zone(name="Delay R", zone_type=ZoneType.DELAY_RIGHT, output_channel=5),
        Zone(name="Fill L", zone_type=ZoneType.FILL_LEFT, output_channel=6),
        Zone(name="Fill R", zone_type=ZoneType.FILL_RIGHT, output_channel=7),
    ],
    "Mono PA + Sub": [
        Zone(name="Main", zone_type=ZoneType.CUSTOM, output_channel=1),
        Zone(name="Sub", zone_type=ZoneType.SUB, output_channel=2, is_sub=True, crossover_freq=120.0),
    ],
}
