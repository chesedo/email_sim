#!/usr/bin/env python3

import sys
import argparse
import random
from dst.simulation import run_simulation
from dst.actions import get_available_actions

def main():
    parser = argparse.ArgumentParser(description='Run time simulation')
    parser.add_argument('--seed', type=int, help='Seed for random time generation')
    parser.add_argument('--steps', type=int, default=2, help='Number of simulation steps')
    args = parser.parse_args()

    if args.seed is None:
        args.seed = random.randint(1, 1_000_000)

    print(f"Using seed {args.seed}")
    random.seed(args.seed)

    # Get all registered actions and instantiate them
    action_classes = get_available_actions()

    print(f"Available actions: {', '.join(action_classes.keys())}")

    actions = [cls() for cls in action_classes.values()]

    success = run_simulation(actions, args.steps)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
