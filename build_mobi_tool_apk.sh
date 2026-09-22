#!/usr/bin/env bash
set -euo pipefail

# Build the Nano Mobi Tool Android APK and copy the artifact into dist/.
#
# Unlike the sibling nano project this app has no custom Flutter extension, so
# none of that project's Gradle/desugaring workarounds are needed here. If you
# later add one under extensions/ (e.g. a Kotlin plugin for USB intent-filters),
# re-read build_nano_apk.sh before copying its tricks across.
#
# NOTE on the pub.dev "authorization failed" flake:
# Dart's pub resolver sometimes reports a transient pub.dev hiccup as
# "... which doesn't exist (authorization failed)". It is not a real
# credential problem; retry.

cd "$(dirname "$0")"

uv sync
# uv does not seed pip, but flet build shells out to `<venv python> -m pip`.
uv run python -m ensurepip --upgrade >/dev/null 2>&1 || true

echo "== building APK (retrying once on a pub.dev flake) =="
if ! uv run flet build apk --split-per-abi; then
    echo "== first attempt failed; clearing pub cache and retrying =="
    rm -rf "${PUB_CACHE:-$HOME/.pub-cache}/hosted/pub.dev" 2>/dev/null || true
    uv run flet build apk --split-per-abi
fi

mkdir -p dist
# flet's output directory has moved between releases; find the APKs instead of
# hardcoding a path that may no longer exist.
mapfile -t apks < <(find build -name '*.apk' -newermt '-2 hours' 2>/dev/null)

if [ "${#apks[@]}" -eq 0 ]; then
    echo "ERROR: build reported success but no APK was found under build/" >&2
    exit 1
fi

for apk in "${apks[@]}"; do
    cp -v "$apk" dist/
done

echo
echo "== artifacts in dist/ =="
ls -lh dist/*.apk
