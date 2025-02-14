from typing import Dict, Type
from dst.controller import DockerTimeController

class SimulationAction:
    """Base class for simulation actions"""
    def __call__(self, controller: DockerTimeController) -> bool:
        raise NotImplementedError

# Registry of available actions
_action_registry: Dict[str, Type[SimulationAction]] = {}

def register_action(cls: Type[SimulationAction]):
    """Decorator to register a simulation action"""
    _action_registry[cls.__name__] = cls
    return cls

def get_available_actions() -> Dict[str, Type[SimulationAction]]:
    """Get all registered actions"""
    from . import time  # Import modules containing actions to register them
    return dict(_action_registry)
