#!/usr/bin/env python3

import sys
import argparse
import random
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dst.simulation import run_simulation
from dst.actions import get_available_actions

console = Console()

def main():
    parser = argparse.ArgumentParser(description='Run time simulation')
    parser.add_argument('--seed', type=int, help='Seed for random time generation')
    parser.add_argument('--steps', type=int, default=2, help='Number of simulation steps')
    args = parser.parse_args()

    if args.seed is None:
        args.seed = random.randint(1, 1_000_000)

    # Display initial configuration
    console.print(Panel.fit(
        f"[cyan]Random Seed:[/] [yellow]{args.seed}[/]\n"
        f"[cyan]Simulation Steps:[/] [yellow]{args.steps}[/]",
        title="DST Configuration",
        border_style="blue"
    ))

    # Get all registered actions and instantiate them
    action_classes = get_available_actions()

    # Instantiate actions to get their weights
    actions = [cls() for cls in action_classes.values()]

    # Calculate total weight for normalization
    total_weight = sum(action.weight for action in actions)

    # Display available actions in a table with weights
    table = Table(title="Available Actions", border_style="blue")
    table.add_column("Action", style="green")
    table.add_column("Weight", style="yellow")
    table.add_column("Normalized Weight", style="cyan")

    for i, action in enumerate(actions):
        action_name = action.__class__.__name__
        normalized_weight = action.weight / total_weight
        table.add_row(
            action_name,
            f"{action.weight:.2f}",
            f"{normalized_weight:.4f}"
        )

    console.print(table)
    console.print()

    success = run_simulation(actions, args.seed, args.steps)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
