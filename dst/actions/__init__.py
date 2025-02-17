from typing import Dict, Type, Optional
from datetime import datetime
from dst.controller import DockerTimeController
from dst.generator import DataGenerator

class ValidationAction:
    """Base class for validation actions"""

    def __init__(self, start_time: datetime):
        self.start_time = start_time

    @property
    def timeout(self) -> float:
        """Number of seconds to wait before timing out validation"""
        return 5.0

    def validate(self, controller: DockerTimeController) -> bool:
        """
        Validate the result of an action

        Returns:
            bool: Whether validation was successful
        """
        raise NotImplementedError

class SimulationAction:
    """Base class for simulation actions"""

    def __call__(self, controller: DockerTimeController, data_generator: DataGenerator) -> tuple[bool, Optional[ValidationAction]]:
        """
        Execute the action and optionally return a validator

        Returns:
            tuple containing:
            - bool: Whether the execution was successful
            - Optional[ValidationAction]: Validator if one is needed
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
