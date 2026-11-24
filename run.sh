#!/usr/bin/env bash
# Start the Local Quantized Triage Node UI. No API key required.
set -euo pipefail
cd "$(dirname "$0")"

STREAMLIT_PORT="${TRIAGE_UI_PORT:-8518}"
DATA="$(pwd)/data"
mkdir -p "$DATA"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

MODEL_FILE="models/qwen2.5-1.5b-instruct-q4_k_m.gguf"
if [[ -f "$MODEL_FILE" ]]; then
  if ! python -c "import llama_cpp" >/dev/null 2>&1; then
    echo "Installing optional llama-cpp-python (CPU wheel) so the local GGUF can run…"
    pip install -q -r requirements-llm.txt
  fi
  echo "Local model found: $MODEL_FILE"
  echo "This machine has no GPU requirement; the model will run on CPU."
  echo "In production this node would typically use one GPU."
else
  echo
  echo "=============================================================="
  echo " No local GGUF found. The UI will start in rules-only mode."
  echo " Tests and CI also use this path — they do not need the model."
  echo " To enable the 1.5B Q4 model (free, one-time, ~1.04 GB):"
  echo "   ./download_model.sh"
  echo "=============================================================="
  echo
fi

echo "Local Quantized Triage Node UI: http://127.0.0.1:${STREAMLIT_PORT}"
echo "CLI:  .venv/bin/python -m triage once --id svc-brakes"
echo "Eval: .venv/bin/python -m triage eval --backend rules"
exec streamlit run app.py --server.headless true --server.port "$STREAMLIT_PORT" --server.address 127.0.0.1
