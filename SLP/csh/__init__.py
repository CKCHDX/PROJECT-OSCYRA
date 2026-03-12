"""
Central Server Hub (CSH) Module

Manages service orchestration, lifecycle, and web interfaces.
Functions as the control center for the SL Protocol ecosystem.
"""

__version__ = "1.0.0"
__author__ = "CKCHDX"
__module_name__ = "CSH - Central Server Hub"

# Module initialization - lazy load to avoid circular imports

from .csh import CentralServerHub

__all__ = [
    "CentralServerHub",
]
