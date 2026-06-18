#!/usr/bin/env bash
set -euo pipefail

# resolve path
cd "$(dirname "$0")"

# print package info
NAME=$(grep -oP '(?<=^name = ")[^"]+' pyproject.toml)
VERSION_FILE="q/__init__.py"
VERSION=$(grep -oP '(?<=__version__ = ")[^"]+' "${VERSION_FILE}")
printf "Package: \033[33m%s\033[0m\nVersion: \033[33m%s\033[0m\n" "${NAME}" "${VERSION}"

# confirm
read -rp "Publish to PyPI? [y/n] " confirm
[[ "${confirm}" == [yY] ]] || { printf "\033[31mAborted.\033[0m\n"; exit 0; }

# clean previous builds
rm -rf dist/ build/ ./*.egg-info

# build
python3 -m build

# upload
twine upload dist/*
printf "\n\033[32mSuccess\033[0m\n"
