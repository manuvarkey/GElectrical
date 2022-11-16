#!/bin/sh

# Build into local repository
flatpak-builder --repo=repo build-dir com.kavilgroup.gelectrical.json --force-clean
# Build bundle
flatpak build-bundle repo gestimator.flatpak com.kavilgroup.gelectrical
