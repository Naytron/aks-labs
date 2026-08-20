#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$script_dir/../.devcontainer/tools.env"

case "$(uname -m)" in
  x86_64) arch=amd64 ;;
  aarch64|arm64) arch=arm64 ;;
  *) echo "Unsupported architecture" >&2; exit 1 ;;
esac

sha_var="HELM3_LINUX_${arch^^}_SHA256"
archive="helm-${HELM3_VERSION}-linux-${arch}.tar.gz"
url="https://get.helm.sh/${archive}"
workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

curl --fail --silent --show-error --location "$url" --output "$workdir/$archive"
echo "${!sha_var}  $workdir/$archive" | sha256sum --check
tar -xzf "$workdir/$archive" -C "$workdir"
sudo install -m 0755 "$workdir/linux-${arch}/helm" /usr/local/bin/helm3
