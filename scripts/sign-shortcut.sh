#!/bin/sh
# Sign the Nespresso Log Shortcut from a release, ready to import and share.
#
#   scripts/sign-shortcut.sh [--upload] [--local] [TAG]
#
# Downloads Nespresso-Log-unsigned.shortcut from TAG (default: the latest release), signs
# it for anyone, and writes "Nespresso Log.shortcut" here; open it to import. --upload
# also attaches the signed file to the release. --local builds from this checkout instead
# of downloading. Needs macOS logged into iCloud, and gh for anything but --local.
set -eu

upload='' local='' tag=''
for arg in "$@"; do
  case "$arg" in
    --upload) upload=1 ;;
    --local) local=1 ;;
    -h | --help) sed -n '2,9s/^# \{0,1\}//p' "$0"; exit 0 ;;
    -*) echo "unknown option: $arg" >&2; exit 2 ;;
    *) tag=$arg ;;
  esac
done
if [ -n "$upload" ] && [ -n "$local" ]; then
  echo "--upload needs a release build, not --local" >&2
  exit 2
fi

unsigned_name=Nespresso-Log-unsigned.shortcut
# Shortcuts names an import after its file. GitHub turns spaces in asset names into dots,
# so the uploaded copy uses a hyphen.
signed="Nespresso Log.shortcut"
asset_name=Nespresso-Log.shortcut

# Run from anywhere: uv and gh act on this checkout, the signed file lands here.
repo=$(cd "$(dirname "$0")/.." && pwd)
gh_repo() { (cd "$repo" && gh "$@"); }

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

if [ -n "$local" ]; then
  uv run --project "$repo" capsule-caffeine shortcut -o "$work/$unsigned_name"
else
  tag=${tag:-$(gh_repo release view --json tagName --jq .tagName)}
  echo "Downloading $unsigned_name from $tag"
  if ! gh_repo release download "$tag" --pattern "$unsigned_name" --dir "$work"; then
    echo "$tag has no $unsigned_name (releases before 2.1.0 don't); try --local" >&2
    exit 1
  fi
fi

# Signing goes through Apple's servers, which sometimes answer with an error.
if ! shortcuts sign --mode anyone --input "$work/$unsigned_name" --output "$signed"; then
  echo "Signing failed; it needs iCloud and Apple's servers, so try again shortly" >&2
  exit 1
fi
echo "Signed: $signed (open it to import)"

if [ -n "$upload" ]; then
  cp "$signed" "$work/$asset_name"
  gh_repo release upload "$tag" "$work/$asset_name" --clobber
  echo "Uploaded $asset_name to $tag"
fi
