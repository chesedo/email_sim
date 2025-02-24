import random
import shutil
import subprocess
from typing import List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from dst.controller import DockerTimeController
from dst.actions import SimulationAction
from dst.generator import DataGenerator
from pathlib import Path

console = Console()

class SimulationRunner:
    def __init__(self, actions: List[SimulationAction], seed: int, steps: int = 100):
        random.seed(seed)

        weights = [action.weight for action in actions]
        total_weight = sum(weights)

        self.actions = actions
        self.normalized_weights = [w/total_weight for w in weights]
        self.steps = steps
        self.controller = DockerTimeController()
        self.data_generator = DataGenerator(seed)
        self.completed_steps = 0

    def execute_action(self) -> bool:
        """Execute a single action"""
        try:
            # Select action based on weights
            action = random.choices(self.actions, weights=self.normalized_weights, k=1)[0]

            action_name = action.__class__.__name__
            self.completed_steps += 1

            # Log step info
            console.print(f"[bold cyan]Step {self.completed_steps}/{self.steps}[/] [blue]Action: {action_name}[/]")

            # Execute the action
            success = action(self.controller, self.data_generator)
            if not success:
                console.print("[bold red]Action execution failed! ❌")
                return False

            console.print(f"[dim cyan]Completed: {action_name}[/]")
            return True

        except Exception as e:
            console.print(f"[bold red]Error executing action: {e}")
            return False

    def run(self) -> bool:
        """Run the simulation synchronously"""
        console.print(Panel.fit("DST Simulation", style="bold magenta"))
        success = True

        try:
            with Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                TimeElapsedColumn(),
                console=console,
                transient=False
            ) as progress:
                task = progress.add_task("[cyan]Running simulation...", total=self.steps)

                while self.completed_steps < self.steps:
                    if not self.execute_action():
                        success = False
                        break
                    progress.update(task, advance=1)

                if success:
                    console.print("[bold green]Simulation completed successfully! ✨")
                else:
                    console.print("[bold red]Simulation failed!")

            return success
        finally:
            self.controller.cleanup()

def move_tmp_directory(seed: int, steps: int) -> Path:
    """Move tmp directory with seed and steps in name"""
    src = Path("./tmp/mail")
    if not src.exists():
        return None

    dst = Path(f"./tmp/seed{seed}_steps{steps}")
    if dst.exists():
        shutil.rmtree(dst)

    shutil.copytree(src, dst)
    return dst

def compare_runs(dir1: Path, dir2: Path) -> bool:
    """Compare two directories using system diff command"""
    try:
        result = subprocess.run(
            ["diff", "-ru", str(dir1), str(dir2)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            console.print("\n[green]Success: Both runs produced identical results![/]")
            return True
        else:
            console.print("\n[red]Warning: Differences found between runs![/]")
            console.print(result.stdout)
            return False

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error running diff: {e}[/]")
        return False

def run_simulation_with_comparison(actions: List[SimulationAction], seed: int, steps: int = 100) -> bool:
    """Run two identical simulations and compare results"""
    # First run
    console.print("\n[bold magenta]Running first simulation...[/]")
    runner1 = SimulationRunner(actions, seed, steps)
    success1 = runner1.run()
    if not success1:
        return False

    # Move first run results
    dir1 = move_tmp_directory(seed, steps)

    # Second run
    console.print("\n[bold magenta]Running second simulation...[/]")
    runner2 = SimulationRunner(actions, seed, steps)
    success2 = runner2.run()
    if not success2:
        return False

    # Compare results using system diff
    return compare_runs(dir1, Path("./tmp/mail"))

def run_simulation(actions: List[SimulationAction], seed: int, steps: int = 100) -> bool:
    """Main entry point for running a simulation with comparison"""
    return run_simulation_with_comparison(actions, seed, steps)
