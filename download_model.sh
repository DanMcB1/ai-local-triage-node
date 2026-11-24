#!/usr/bin/env bash
# Download the pinned Qwen2.5-1.5B Instruct Q4_K_M GGUF and verify its checksum.
# The weights are not part of the git repo.
set -euo pipefail
cd "$(dirname "$0")"

MODEL_DIR="models"
MODEL_FILE="qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODEL_PATH="$MODEL_DIR/$MODEL_FILE"
URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/$MODEL_FILE"
EXPECTED_SHA256="6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"
EXPECTED_SIZE="1117320736"

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "Need sha256sum or shasum to verify the model download." >&2
    exit 1
  fi
}

file_size() {
  if stat -c%s "$1" >/dev/null 2>&1; then
    stat -c%s "$1"
  else
    stat -f%z "$1"
  fi
}

mkdir -p "$MODEL_DIR"

if [[ -f "$MODEL_PATH" ]]; then
  got="$(sha256_of "$MODEL_PATH")"
  if [[ "$got" == "$EXPECTED_SHA256" ]]; then
    echo "Model already present and checksum matches:"
    echo "  $MODEL_PATH"
    echo "Install the optional Python binding with:  .venv/bin/pip install -r requirements-llm.txt"
    exit 0
  fi
  echo "Existing file failed the checksum; re-downloading." >&2
  rm -f "$MODEL_PATH"
fi

echo "Downloading $MODEL_FILE (~1.04 GB) from Hugging Face…"
echo "  $URL"
tmp="$MODEL_PATH.part"
curl -L --retry 5 --retry-delay 3 -C - \
  -A "ai-local-triage-node/1.0 (portfolio demo)" \
  -o "$tmp" "$URL"

got_size="$(file_size "$tmp")"
if [[ "$got_size" != "$EXPECTED_SIZE" ]]; then
  echo "Unexpected file size: $got_size (expected $EXPECTED_SIZE)." >&2
  exit 1
fi

got="$(sha256_of "$tmp")"
if [[ "$got" != "$EXPECTED_SHA256" ]]; then
  echo "Checksum mismatch." >&2
  echo "  expected: $EXPECTED_SHA256" >&2
  echo "  got:      $got" >&2
  rm -f "$tmp"
  exit 1
fi

mv "$tmp" "$MODEL_PATH"
echo "Verified SHA-256 and saved to $MODEL_PATH"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
if ! python -c "import llama_cpp" >/dev/null 2>&1; then
  echo "Installing llama-cpp-python from the CPU wheel index…"
  pip install -q -r requirements-llm.txt
fi
echo
echo "Ready. Start the UI with ./run.sh"
echo "The model runs on CPU in this demo. In production this node would typically use one GPU."
