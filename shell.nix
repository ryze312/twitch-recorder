{ mkShell, python3, uv, mypy, ruff, ffmpeg }:

mkShell {
  packages = [
    python3

    uv
    mypy
    ruff

    ffmpeg
  ];
}
