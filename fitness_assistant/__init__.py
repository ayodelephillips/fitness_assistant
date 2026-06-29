"""fitness assistant package"""

from importlib.metadata import version

__version__ = version("fitness_assistant")

# prevent flake 8 imported but not used error
__all__ = [
    "__version__",
]
