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

sha_var="KUBECONFORM_LINUX_${arch^^}_SHA256"
archive="kubeconform-linux-${arch}.tar.gz"
url="https://github.com/yannh/kubeconform/releases/download/v${KUBECONFORM_VERSION}/${archive}"
curl --fail --silent --show-error --location "$url" --output "/tmp/$archive"
echo "${!sha_var}  /tmp/$archive" | sha256sum --check
tar -xzf "/tmp/$archive" -C /tmp kubeconform
sudo install -m 0755 /tmp/kubeconform /usr/local/bin/kubeconform
rm -f "/tmp/$archive" /tmp/kubeconform
