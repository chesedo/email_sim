#!/usr/bin/env python3

import sys
import argparse
import random
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dst.simulation import run_simulation
from dst.actions import get_available_actions
from dst.generator import DataGenerator

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

    # Display available actions in a table
    table = Table(show_header=False, title="Available Actions", border_style="blue")
    for action_name in action_classes.keys():
        table.add_row(f"[green]•[/] {action_name}")
    console.print(table)
    console.print()

    actions = [cls() for cls in action_classes.values()]

    success = run_simulation(actions, args.seed, args.steps)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
