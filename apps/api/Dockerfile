# EcoTrace API — production-capable image with LibreOffice headless.
# Build from repository root:
#   docker build -f apps/api/Dockerfile -t ecotrace-api:external-test .
#
# LibreOffice: TDF 26.8.0 (aligned with accepted macOS Official SEE engine 26.8.x).
# Debian bookworm libreoffice 7.4.x does NOT pass golden PEE→I/J/K parity.
#
# TDF archive naming (authoritative download.documentfoundation.org index + metalink):
#   Directory token:  deb/{aarch64|x86_64}/
#   Filename token:   Linux_aarch64  |  Linux_x86-64   (hyphen, not underscore)
# Official SEE golden parity evidence remains linux/arm64 acceptance — not GitHub amd64.

FROM python:3.12-slim-bookworm AS base

ARG TARGETARCH
ARG LIBREOFFICE_VERSION=26.8.0
# TDF metalink sha-256 for LibreOffice_26.8.0_Linux_aarch64_deb.tar.gz
ARG LIBREOFFICE_SHA256_AARCH64=f989b73c31e7e16b3f99475bc5befaffdf42af75f83fe882293e1a0258cc9173
# TDF metalink sha-256 for LibreOffice_26.8.0_Linux_x86-64_deb.tar.gz
ARG LIBREOFFICE_SHA256_X86_64=d0a6031a3837e48f9854e6d2da6489b9fadbd814afa4741fa32a197741663a22
# Official SEE template identity (must match TEMPLATE_SHA256 in code).
ARG OFFICIAL_SEE_TEMPLATE_SHA256=83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src \
    LIBREOFFICE_SOFFICE_PATH=/usr/bin/soffice \
    OFFICIAL_SEE_TEMPLATE_PATH=/app/official-see/template.xlsx \
    LIBREOFFICE_RECALC_TIMEOUT_SECONDS=300 \
    TMPDIR=/tmp \
    HOME=/home/ecotrace \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

# Runtime OS deps + fonts/locales (no Debian LibreOffice packages).
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        postgresql-client \
        fonts-dejavu-core \
        fonts-liberation \
        fontconfig \
        locales \
        libxinerama1 \
        libxrender1 \
        libxext6 \
        libx11-6 \
        libsm6 \
        libice6 \
        libcups2 \
        libdbus-1-3 \
        libglib2.0-0 \
        libnss3 \
        libnspr4 \
        libxcb1 \
        libx11-xcb1 \
        libxau6 \
        libxdmcp6 \
        libcairo2 \
        libxslt1.1 \
        libxml2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
    && sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=C.UTF-8 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin ecotrace \
    && mkdir -p /data/attachments /data/knowledge /data/reports /data/backups \
        /tmp/ecotrace-lo \
        /home/ecotrace/.cache/dconf \
        /home/ecotrace/.config \
        /home/ecotrace/.local/share \
    && chown -R ecotrace:ecotrace /data /tmp/ecotrace-lo /home/ecotrace

# Install Document Foundation LibreOffice Calc stack only (aligned with macOS 26.8.x).
# Fail closed on arch/version/checksum mismatch — never silently use Debian LibreOffice 7.4.
RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64) \
        LO_DIR=x86_64; \
        LO_FILE_ARCH=x86-64; \
        EXPECTED_SHA="${LIBREOFFICE_SHA256_X86_64}" ;; \
      arm64) \
        LO_DIR=aarch64; \
        LO_FILE_ARCH=aarch64; \
        EXPECTED_SHA="${LIBREOFFICE_SHA256_AARCH64}" ;; \
      *) echo "Unsupported TARGETARCH=${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    if [ -z "${EXPECTED_SHA}" ]; then \
      echo "Missing pinned SHA-256 for LibreOffice ${LIBREOFFICE_VERSION} / ${LO_FILE_ARCH}" >&2; \
      exit 1; \
    fi; \
    LO_TGZ="LibreOffice_${LIBREOFFICE_VERSION}_Linux_${LO_FILE_ARCH}_deb.tar.gz"; \
    LO_URL="https://download.documentfoundation.org/libreoffice/stable/${LIBREOFFICE_VERSION}/deb/${LO_DIR}/${LO_TGZ}"; \
    curl -fsSL -o /tmp/lo.tar.gz "${LO_URL}"; \
    echo "${EXPECTED_SHA}  /tmp/lo.tar.gz" | sha256sum -c -; \
    mkdir -p /tmp/lo; \
    tar -xzf /tmp/lo.tar.gz -C /tmp/lo; \
    case "${LO_FILE_ARCH}" in \
      aarch64) find /tmp/lo -maxdepth 2 -type d -name "*Linux_aarch64*" | grep -q . ;; \
      x86-64) find /tmp/lo -maxdepth 2 -type d \( -name "*Linux_x86-64*" -o -name "*Linux_x86_64*" \) | grep -q . ;; \
    esac; \
    DEBS_DIR="$(find /tmp/lo -type d -name DEBS | head -1)"; \
    test -n "${DEBS_DIR}"; \
    cd "${DEBS_DIR}"; \
    # Install all TDF-provided debs; dpkg may leave packages unconfigured until apt -f.
    set +e; \
    dpkg -i ./*.deb; \
    DPKG_RC=$?; \
    set -e; \
    apt-get -y -f install --no-install-recommends; \
    if [ "${DPKG_RC}" -ne 0 ] && ! command -v soffice >/dev/null 2>&1 \
       && ! find /opt -path '*/program/soffice' -type f | grep -q .; then \
      echo "LibreOffice dpkg install failed and soffice is missing (dpkg_rc=${DPKG_RC})" >&2; \
      exit 1; \
    fi; \
    rm -rf /tmp/lo /tmp/lo.tar.gz; \
    cd /app; \
    # Refuse Debian bookworm LO 7.4 paths.
    if [ -e /usr/lib/libreoffice/program/soffice ] && [ ! -e /opt/libreoffice26.8/program/soffice ] \
       && ! find /opt -path '*/program/soffice' 2>/dev/null | grep -q .; then \
      echo "Debian LibreOffice fallback detected; refusing image" >&2; \
      exit 1; \
    fi; \
    SOFFICE="$(find /opt -path '*/program/soffice' -type f | head -1)"; \
    test -n "${SOFFICE}"; \
    ln -sfn "${SOFFICE}" /usr/bin/soffice; \
    soffice --version | tee /app/libreoffice-version.txt; \
    grep -E 'LibreOffice 26\.8' /app/libreoffice-version.txt; \
    chown ecotrace:ecotrace /app/libreoffice-version.txt

# Application package (context = repository root).
COPY apps/api/pyproject.toml /app/pyproject.toml
COPY apps/api/VERSION /app/VERSION
COPY apps/api/src /app/src
COPY apps/api/alembic.ini /app/alembic.ini
COPY apps/api/docker-entrypoint.sh /app/docker-entrypoint.sh

# Official SEE template — tracked under apps/api (SHA-256 verified at build).
COPY apps/api/official-see/template.xlsx /app/official-see/template.xlsx
RUN echo "${OFFICIAL_SEE_TEMPLATE_SHA256}  /app/official-see/template.xlsx" | sha256sum -c -

RUN pip install --upgrade pip \
    && pip install --no-cache-dir . \
    && chmod +x /app/docker-entrypoint.sh \
    && chown -R ecotrace:ecotrace /app /data \
    && chmod 750 /data /data/reports /data/attachments /data/knowledge /data/backups

# Drop to non-root for default image metadata; entrypoint may briefly run as root
# to chown mounted volumes, then re-exec as ecotrace.
USER ecotrace

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "ecotrace.main:app", "--host", "0.0.0.0", "--port", "8000"]
