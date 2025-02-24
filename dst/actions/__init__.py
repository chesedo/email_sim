from typing import Dict, Type
from dst.controller import DockerTimeController
from dst.generator import DataGenerator

class SimulationAction:
    """Base class for simulation actions"""

    @property
    def weight(self) -> float:
        """
        Weight of this action being selected. Default is 1.0.
        Override this property to change the likelihood of the action being selected.
        """
        return 1.0

    def __call__(self, controller: DockerTimeController, data_generator: DataGenerator) -> bool:
        """
        Execute the action and optionally return a validator

        Returns: Whether the execution was successful
        """
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
    from . import email  # Import modules containing actions to register them
    return dict(_action_registry)
