import random
import time
from typing import List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from dst.controller import DockerTimeController
from dst.actions import SimulationAction, ValidationAction

console = Console()

def run_simulation(actions: List[SimulationAction], steps: int = 100) -> bool:
    console.print(Panel.fit("DST Simulation", style="bold magenta"))

    controller = DockerTimeController()
    success = True
    pending_validations: List[ValidationAction] = []

    try:
        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            console=console,
            transient=False
        ) as progress:
            task = progress.add_task("[cyan]Running simulation...", total=steps)

            for step in range(steps):
                # Process any pending validations
                current_time = controller.get_time()
                still_pending = []

                for validator in pending_validations:
                    time_elapsed = (current_time - validator.start_time).total_seconds()
                    if time_elapsed >= validator.timeout:
                        # Time to validate
                        if not validator.validate(controller):
                            console.print(f"[bold red]Validation failed for {validator.__class__.__name__}! ❌")
                            success = False
                            return False
                    else:
                        still_pending.append(validator)

                pending_validations = still_pending

                # Execute next action
                action = random.choice(actions)
                action_name = action.__class__.__name__

                # Create a table for this step
                table = Table(show_header=False, box=None)
                table.add_row(
                    f"[bold cyan]Step {step + 1}/{steps}",
                    f"[blue]Action: {action_name}"
                )
                console.print(table)

                # Execute the action
                execution_success, validator = action(controller)
                if not execution_success:
                    console.print("[bold red]Action execution failed! ❌")
                    success = False
                    break

                # If validation needed, add to pending list
                if validator:
                    pending_validations.append(validator)

                progress.advance(task)

            # After all steps, wait for remaining validations
            if pending_validations:
                console.print("[yellow]Waiting for pending validations...[/]")
                while pending_validations:
                    current_time = controller.get_time()
                    still_pending = []

                    for validator in pending_validations:
                        time_elapsed = (current_time - validator.start_time).total_seconds()
                        if time_elapsed >= validator.timeout:
                            # Time to validate
                            if not validator.validate(controller):
                                console.print(f"[bold red]Final validation failed for {validator.__class__.__name__}! ❌")
                                success = False
                                return False
                        else:
                            still_pending.append(validator)

                    if still_pending:
                        console.print(f"[yellow]Waiting for {len(still_pending)} validation(s) to timeout...[/]")
                        # Wait a bit before checking again
                        time.sleep(0.5)

                    pending_validations = still_pending

        if success:
            console.print("[bold green]Simulation completed successfully! ✨")

        return success
    finally:
        controller.cleanup()
