"""Competing Mechanism Generator (V3 P3) — package facade.

Re-exports the public entry point so that the historical flat-module
import path keeps working::

    from psf_reasoner.reasoning.mechanism_generator import MechanismGenerator
"""

from __future__ import annotations

from psf_reasoner.reasoning.mechanism_generator.generator import MechanismGenerator

__all__ = ["MechanismGenerator"]
