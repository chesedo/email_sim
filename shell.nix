# shell.nix
{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python3
    poetry
    docker
    swaks
    libfaketime
  ];

  shellHook = ''
    # Ensure Docker socket is accessible
    export DOCKER_HOST="unix:///var/run/docker.sock"

    # Create Poetry environment if it doesn't exist
    if [ ! -f "poetry.lock" ]; then
      echo "Installing dependencies with Poetry..."
      poetry install
    fi

    # Add Poetry's virtual environment bin directory to PATH
    export PATH="$PWD/.venv/bin:$PATH"

    # Source the virtual environment if it exists (but don't create a subshell)
    if [ -d "$PWD/.venv" ]; then
      export VIRTUAL_ENV="$PWD/.venv"
      export POETRY_ACTIVE=1
    fi

    echo "Python development environment ready!"
    echo "Docker socket at: $DOCKER_HOST"
    echo "Run 'poetry run dst' to start the simulation"
  '';
}
