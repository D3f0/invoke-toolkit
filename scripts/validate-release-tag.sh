#!/usr/bin/env bash
set -euo pipefail

: "${TAG_NAME:?TAG_NAME must be set}"

if [[ ! "$TAG_NAME" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  printf 'Release tag %q is not a canonical lowercase tag in vMAJOR.MINOR.PATCH form.\n' "$TAG_NAME" >&2
  exit 1
fi

git fetch --no-tags origin main

tag_commit=$(git rev-parse "refs/tags/$TAG_NAME^{}")
main_commit=$(git rev-parse FETCH_HEAD)

if [[ "$tag_commit" != "$main_commit" ]]; then
  printf 'Release tag %s (%s) does not point to origin/main (%s).\n' "$TAG_NAME" "$tag_commit" "$main_commit" >&2
  exit 1
fi

{
  printf 'tag=%s\n' "$TAG_NAME"
  printf 'version=%s\n' "${TAG_NAME#v}"
} >> "$GITHUB_OUTPUT"
