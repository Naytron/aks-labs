FROM mcr.microsoft.com/devcontainers/base:2-ubuntu-24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        curl \
        dnsutils \
        gettext-base \
        iputils-ping \
        jq \
        netcat-openbsd \
        python3 \
        python-is-python3 \
        python3-pip \
        shellcheck \
        unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY tools.env /tmp/tools.env
COPY install-tools.sh /tmp/install-tools.sh
RUN sed --in-place 's/\r$//' /tmp/install-tools.sh /tmp/tools.env \
    && chmod 0755 /tmp/install-tools.sh \
    && bash /tmp/install-tools.sh \
    && rm -f /tmp/install-tools.sh /tmp/tools.env

USER vscode
