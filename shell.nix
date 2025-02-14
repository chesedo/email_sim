# shell.nix
{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python3
    python3Packages.pytest
    python3Packages.docker
    python3Packages.python-on-whales
    python3Packages.requests
    python3Packages.pip
    pyright
    docker
  ];

  shellHook = ''
    # Ensure Docker socket is accessible
    export DOCKER_HOST="unix:///var/run/docker.sock"

    # Create a virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
      python -m venv venv
    fi

    # Activate the virtual environment
    source venv/bin/activate

    echo "Python development environment ready!"
    echo "Docker socket at: $DOCKER_HOST"
  '';
}
