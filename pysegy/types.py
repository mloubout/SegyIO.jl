"""Shared data structures for the minimal Python implementation."""

from dataclasses import dataclass, field
from typing import Dict, List

# Byte locations for binary file header fields
FH_BYTE2SAMPLE: Dict[str, int] = {
    "Job": 3200,
    "Line": 3204,
    "Reel": 3208,
    "DataTracePerEnsemble": 3212,
    "AuxiliaryTracePerEnsemble": 3214,
    "dt": 3216,
    "dtOrig": 3218,
    "ns": 3220,
    "nsOrig": 3222,
    "DataSampleFormat": 3224,
    "EnsembleFold": 3226,
    "TraceSorting": 3228,
    "VerticalSumCode": 3230,
    "SweepFrequencyStart": 3232,
    "SweepFrequencyEnd": 3234,
    "SweepLength": 3236,
    "SweepType": 3238,
    "SweepChannel": 3240,
    "SweepTaperlengthStart": 3242,
    "SweepTaperLengthEnd": 3244,
    "TaperType": 3246,
    "CorrelatedDataTraces": 3248,
    "BinaryGain": 3250,
    "AmplitudeRecoveryMethod": 3252,
    "MeasurementSystem": 3254,
    "ImpulseSignalPolarity": 3256,
    "VibratoryPolarityCode": 3258,
    "SegyFormatRevisionNumber": 3500,
    "FixedLengthTraceFlag": 3502,
    "NumberOfExtTextualHeaders": 3504,
}

TH_BYTE2SAMPLE: Dict[str, int] = {
    "TraceNumWithinLine": 0,
    "TraceNumWithinFile": 4,
    "FieldRecord": 8,
    "TraceNumber": 12,
    "EnergySourcePoint": 16,
    "CDP": 20,
    "CDPTrace": 24,
    "TraceIDCode": 28,
    "NSummedTraces": 30,
    "NStackedTraces": 32,
    "DataUse": 34,
    "Offset": 36,
    "RecGroupElevation": 40,
    "SourceSurfaceElevation": 44,
    "SourceDepth": 48,
    "RecDatumElevation": 52,
    "SourceDatumElevation": 56,
    "SourceWaterDepth": 60,
    "GroupWaterDepth": 64,
    "ElevationScalar": 68,
    "RecSourceScalar": 70,
    "SourceX": 72,
    "SourceY": 76,
    "GroupX": 80,
    "GroupY": 84,
    "CoordUnits": 88,
    "WeatheringVelocity": 90,
    "SubWeatheringVelocity": 92,
    "UpholeTimeSource": 94,
    "UpholeTimeGroup": 96,
    "StaticCorrectionSource": 98,
    "StaticCorrectionGroup": 100,
    "TotalStaticApplied": 102,
    "LagTimeA": 104,
    "LagTimeB": 106,
    "DelayRecordingTime": 108,
    "MuteTimeStart": 110,
    "MuteTimeEnd": 112,
    "ns": 114,
    "dt": 116,
    "GainType": 118,
    "InstrumentGainConstant": 120,
    "InstrumntInitialGain": 122,
    "Correlated": 124,
    "SweepFrequencyStart": 126,
    "SweepFrequencyEnd": 128,
    "SweepLength": 130,
    "SweepType": 132,
    "SweepTraceTaperLengthStart": 134,
    "SweepTraceTaperLengthEnd": 136,
    "TaperType": 138,
    "AliasFilterFrequency": 140,
    "AliasFilterSlope": 142,
    "NotchFilterFrequency": 144,
    "NotchFilterSlope": 146,
    "LowCutFrequency": 148,
    "HighCutFrequency": 150,
    "LowCutSlope": 152,
    "HighCutSlope": 154,
    "Year": 156,
    "DayOfYear": 158,
    "HourOfDay": 160,
    "MinuteOfHour": 162,
    "SecondOfMinute": 164,
    "TimeCode": 166,
    "TraceWeightingFactor": 168,
    "GeophoneGroupNumberRoll": 170,
    "GeophoneGroupNumberTraceStart": 172,
    "GeophoneGroupNumberTraceEnd": 174,
    "GapSize": 176,
    "OverTravel": 178,
    "CDPX": 180,
    "CDPY": 184,
    "Inline3D": 188,
    "Crossline3D": 192,
    "ShotPoint": 196,
    "ShotPointScalar": 200,
    "TraceValueMeasurmentUnit": 202,
    "TransductionConstnatMantissa": 204,
    "TransductionConstantPower": 208,
    "TransductionUnit": 210,
    "TraceIdentifier": 212,
    "ScalarTraceHeader": 214,
    "SourceType": 216,
    "SourceEnergyDirectionMantissa": 218,
    "SourceEnergyDirectionExponent": 222,
    "SourceMeasurmentMantissa": 224,
    "SourceMeasurementExponent": 228,
    "SourceMeasurmentUnit": 230,
    "Unassigned1": 232,
    "Unassigned2": 236,
}

# Fields that are stored as 32-bit integers in the trace header
TH_INT32_FIELDS = {
    "TraceNumWithinLine",
    "TraceNumWithinFile",
    "FieldRecord",
    "TraceNumber",
    "EnergySourcePoint",
    "CDP",
    "CDPTrace",
    "Offset",
    "RecGroupElevation",
    "SourceSurfaceElevation",
    "SourceDepth",
    "RecDatumElevation",
    "SourceDatumElevation",
    "SourceWaterDepth",
    "GroupWaterDepth",
    "SourceX",
    "SourceY",
    "GroupX",
    "GroupY",
    "CDPX",
    "CDPY",
    "Inline3D",
    "Crossline3D",
    "ShotPoint",
    "TransductionConstnatMantissa",
    "SourceEnergyDirectionMantissa",
    "SourceMeasurmentMantissa",
    "Unassigned1",
    "Unassigned2",
}

FH_FIELDS = list(FH_BYTE2SAMPLE.keys())
TH_FIELDS = list(TH_BYTE2SAMPLE.keys())

@dataclass
class BinaryFileHeader:
    """Container for parsed binary file header values."""

    values: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in FH_FIELDS})

    def __getattr__(self, name):
        if name in self.values:
            return self.values[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name == "values" or name not in FH_FIELDS:
            super().__setattr__(name, value)
        else:
            self.values[name] = int(value)

    def __repr__(self):
        fields = ", ".join(f"{k}={self.values[k]}" for k in FH_FIELDS)
        return f"BinaryFileHeader({fields})"

@dataclass
class FileHeader:
    """Combined textual and binary file header."""

    th: bytes = b" " * 3200
    bfh: BinaryFileHeader = field(default_factory=BinaryFileHeader)

@dataclass
class BinaryTraceHeader:
    """Container for parsed binary trace header values."""

    values: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in TH_FIELDS})

    def __getattr__(self, name):
        if name in self.values:
            return self.values[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name == "values" or name not in TH_FIELDS:
            super().__setattr__(name, value)
        else:
            self.values[name] = int(value)

    def __repr__(self):
        fields = " ".join(f"{k}={self.values[k]}" for k in TH_FIELDS[:5])
        return f"BinaryTraceHeader({fields} ...)"

@dataclass
class SeisBlock:
    """In-memory representation of a SEGY dataset."""

    fileheader: FileHeader
    traceheaders: List[BinaryTraceHeader]
    data: List[List[float]]

@dataclass
class BlockScan:
    """Summary information for a contiguous block of traces."""
    file: str
    startbyte: int
    endbyte: int
    summary: Dict[str, List[int]]


@dataclass
class SeisCon:
    """Container for the results of scanning a SEGY file."""
    ns: int
    dsf: int
    blocks: List[BlockScan]
