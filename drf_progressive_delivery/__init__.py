"""
Django PartStream Package

Transform slow Django APIs into fast, progressive experiences by streaming data in parts.

A package for progressive delivery of large JSON responses in Django REST Framework.
"""

__version__ = "1.0.0"  # Bumped version for simplified API

# Core utilities that don't require Django settings
from .cursors import CursorManager
from .exceptions import ProgressiveDeliveryError

# Legacy API (for backward compatibility)
from .mixins import ProgressiveDeliveryMixin

# Lazy imports for DRF-dependent components to avoid settings issues
def _get_simplified_api():
    """Lazy import of simplified API to avoid Django settings requirement."""
    try:
        from .simple_views import ProgressiveView, lazy, safe_call, cached_for, with_timeout
        return ProgressiveView, lazy, safe_call, cached_for, with_timeout
    except ImportError:
        # Return None values if DRF is not available or Django not configured
        return None, None, None, None, None

def _get_advanced_api():
    """Lazy import of advanced API components."""
    try:
        from .mixins_v2 import (
            ProgressiveDeliveryMixinV2,
            RegistryProgressiveView,
            MethodProgressiveView,
            DecoratorProgressiveView
        )
        from .parts import (
            ProgressivePartsRegistry,
            ProgressivePart,
            FunctionPart,
            ModelPart,
            StaticPart,
            ComputedPart,
            progressive_part,
            progressive_meta,
            progressive_data
        )
        return (
            ProgressiveDeliveryMixinV2,
            RegistryProgressiveView,
            MethodProgressiveView,
            DecoratorProgressiveView,
            ProgressivePartsRegistry,
            ProgressivePart,
            FunctionPart,
            ModelPart,
            StaticPart,
            ComputedPart,
            progressive_part,
            progressive_meta,
            progressive_data
        )
    except ImportError:
        return tuple([None] * 13)

# Make simplified API available at module level using lazy imports
def __getattr__(name):
    """Lazy loading of API components to avoid Django settings issues."""
    simplified_names = ['ProgressiveView', 'lazy', 'safe_call', 'cached_for', 'with_timeout']
    advanced_names = [
        'ProgressiveDeliveryMixinV2',
        'RegistryProgressiveView',
        'MethodProgressiveView', 
        'DecoratorProgressiveView',
        'ProgressivePartsRegistry',
        'ProgressivePart',
        'FunctionPart',
        'ModelPart',
        'StaticPart',
        'ComputedPart',
        'progressive_part',
        'progressive_meta',
        'progressive_data'
    ]
    
    if name in simplified_names:
        components = _get_simplified_api()
        mapping = dict(zip(simplified_names, components))
        if mapping[name] is None:
            raise ImportError(f"Cannot import {name}. Make sure Django is properly configured.")
        return mapping[name]
    
    elif name in advanced_names:
        components = _get_advanced_api()
        mapping = dict(zip(advanced_names, components))
        if mapping[name] is None:
            raise ImportError(f"Cannot import {name}. Make sure Django is properly configured.")
        return mapping[name]
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# Main exports for most users
__all__ = [
    # PRIMARY: Simplified API (80% of users)
    "ProgressiveView",
    "lazy",
    "safe_call",
    "cached_for",
    "with_timeout",
    
    # LEGACY: For backward compatibility
    "ProgressiveDeliveryMixin",
    
    # ADVANCED: For power users (20% of users)
    "ProgressiveDeliveryMixinV2",
    "RegistryProgressiveView", 
    "MethodProgressiveView",
    "DecoratorProgressiveView",
    "ProgressivePartsRegistry",
    "ProgressivePart",
    "FunctionPart",
    "ModelPart", 
    "StaticPart",
    "ComputedPart",
    "progressive_part",
    "progressive_meta",
    "progressive_data",
    
    # CORE: Always available
    "CursorManager", 
    "ProgressiveDeliveryError"
] 