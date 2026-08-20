#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
source /tmp/tools.env

case "$(uname -m)" in
  x86_64) arch=amd64 ;;
  aarch64|arm64) arch=arm64 ;;
  *)
    echo "Unsupported architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

download_verified() {
  local url="$1"
  local sha256="$2"
  local output="$3"
  curl --fail --silent --show-error --location "$url" --output "$output"
  echo "${sha256}  ${output}" | sha256sum --check --status
}

install_binary() {
  local url="$1"
  local sha256="$2"
  local name="$3"
  download_verified "$url" "$sha256" "$workdir/$name"
  install -m 0755 "$workdir/$name" "/usr/local/bin/$name"
}

kubectl_url="https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${arch}/kubectl"
curl --fail --silent --show-error --location "${kubectl_url}.sha256" --output "$workdir/kubectl.sha256"
curl --fail --silent --show-error --location "$kubectl_url" --output "$workdir/kubectl"
echo "$(cat "$workdir/kubectl.sha256")  $workdir/kubectl" | sha256sum --check --status
install -m 0755 "$workdir/kubectl" /usr/local/bin/kubectl

helm_archive="helm-${HELM_VERSION}-linux-${arch}.tar.gz"
curl --fail --silent --show-error --location "https://get.helm.sh/${helm_archive}.sha256sum" --output "$workdir/helm.sha256"
curl --fail --silent --show-error --location "https://get.helm.sh/${helm_archive}" --output "$workdir/$helm_archive"
(cd "$workdir" && sha256sum --check helm.sha256)
tar -xzf "$workdir/$helm_archive" -C "$workdir"
install -m 0755 "$workdir/linux-${arch}/helm" /usr/local/bin/helm

helm3_sha_var="HELM3_LINUX_${arch^^}_SHA256"
helm3_archive="helm-${HELM3_VERSION}-linux-${arch}.tar.gz"
download_verified \
  "https://get.helm.sh/${helm3_archive}" \
  "${!helm3_sha_var}" \
  "$workdir/$helm3_archive"
tar -xzf "$workdir/$helm3_archive" -C "$workdir"
install -m 0755 "$workdir/linux-${arch}/helm" /usr/local/bin/helm3

kind_sha_var="KIND_LINUX_${arch^^}_SHA256"
install_binary \
  "https://github.com/kubernetes-sigs/kind/releases/download/${KIND_VERSION}/kind-linux-${arch}" \
  "${!kind_sha_var}" \
  kind

flux_sha_var="FLUX_LINUX_${arch^^}_SHA256"
flux_archive="flux_${FLUX_VERSION}_linux_${arch}.tar.gz"
download_verified \
  "https://github.com/fluxcd/flux2/releases/download/v${FLUX_VERSION}/${flux_archive}" \
  "${!flux_sha_var}" \
  "$workdir/$flux_archive"
tar -xzf "$workdir/$flux_archive" -C "$workdir" flux
install -m 0755 "$workdir/flux" /usr/local/bin/flux

kubelogin_sha_var="KUBELOGIN_LINUX_${arch^^}_SHA256"
kubelogin_archive="kubelogin-linux-${arch}.zip"
download_verified \
  "https://github.com/Azure/kubelogin/releases/download/v${KUBELOGIN_VERSION}/${kubelogin_archive}" \
  "${!kubelogin_sha_var}" \
  "$workdir/$kubelogin_archive"
unzip -j "$workdir/$kubelogin_archive" "bin/linux_${arch}/kubelogin" -d "$workdir"
install -m 0755 "$workdir/kubelogin" /usr/local/bin/kubelogin

kubeconform_sha_var="KUBECONFORM_LINUX_${arch^^}_SHA256"
kubeconform_archive="kubeconform-linux-${arch}.tar.gz"
download_verified \
  "https://github.com/yannh/kubeconform/releases/download/v${KUBECONFORM_VERSION}/${kubeconform_archive}" \
  "${!kubeconform_sha_var}" \
  "$workdir/$kubeconform_archive"
tar -xzf "$workdir/$kubeconform_archive" -C "$workdir" kubeconform
install -m 0755 "$workdir/kubeconform" /usr/local/bin/kubeconform

kustomize_sha_var="KUSTOMIZE_LINUX_${arch^^}_SHA256"
kustomize_archive="kustomize_v${KUSTOMIZE_VERSION}_linux_${arch}.tar.gz"
download_verified \
  "https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize/v${KUSTOMIZE_VERSION}/${kustomize_archive}" \
  "${!kustomize_sha_var}" \
  "$workdir/$kustomize_archive"
tar -xzf "$workdir/$kustomize_archive" -C "$workdir" kustomize
install -m 0755 "$workdir/kustomize" /usr/local/bin/kustomize
