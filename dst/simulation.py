import random
from typing import List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from dst.controller import DockerTimeController
from dst.actions import SimulationAction

console = Console()

def run_simulation(actions: List[SimulationAction], steps: int = 100) -> bool:
    console.print(Panel.fit("DST Simulation", style="bold magenta"))

    controller = DockerTimeController()
    success = True

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
                action = random.choice(actions)

                # Create a table for this step
                table = Table(show_header=False, box=None)
                table.add_row(
                    f"[bold cyan]Step {step + 1}/{steps}",
                    f"[blue]Action: {action.__class__.__name__}"
                )
                console.print(table)

                if not action(controller):
                    console.print("[bold red]Simulation failed! ❌")
                    success = False
                    break

                progress.advance(task)

        if success:
            console.print("[bold green]Simulation completed successfully! ✨")

        return success
    finally:
        controller.cleanup()
