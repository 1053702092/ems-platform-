#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for Week 11 RL scripts."""

from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np

try:
    import torch
except ImportError:  # pragma: no cover - only for environments without torch
    torch = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"


def configure_console() -> None:
    """Avoid Windows console encoding crashes for math symbols and Chinese text."""

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def ensure_results_dir(output_dir: str | Path | None = None) -> Path:
    """Return a writable output directory for generated figures."""

    path = Path(output_dir) if output_dir is not None else RESULTS_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def set_seed(seed: int) -> None:
    """Make numpy/random/torch experiments easier to reproduce."""

    random.seed(seed)
    np.random.seed(seed)
    if torch is not None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)


def configure_matplotlib() -> None:
    """Configure matplotlib for Chinese labels on Windows and headless export."""

    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    installed = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in (
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ):
        if candidate in installed:
            plt.rcParams["font.family"] = candidate
            break
    plt.rcParams["axes.unicode_minus"] = False


configure_console()
