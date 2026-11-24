"""Shared settings for the Lakeside Auto Group triage demo."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPANY = "Lakeside Auto Group (sample)"
STORE_DEFAULT = "Lakeside Honda"

UI_PORT = int(os.environ.get("TRIAGE_UI_PORT", "8518"))

MODEL_REPO = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
MODEL_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODEL_NAME = "Qwen2.5-1.5B-Instruct Q4_K_M"
MODEL_PARAMS = "1.5B"
MODEL_QUANT = "Q4_K_M"
MODEL_SHA256 = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"
MODEL_SIZE_BYTES = 1_117_320_736
MODEL_URL = (
    "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/"
    + MODEL_FILENAME
)
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / MODEL_FILENAME

CATEGORIES = ("sales", "service", "fi", "legal", "billing", "general")
URGENCIES = ("critical", "high", "normal", "low")
ROUTES = (
    "sales_manager",
    "service_advisor",
    "fi_manager",
    "legal_compliance",
    "controller",
    "bdc",
)

CATEGORY_LABELS = {
    "sales": "Sales",
    "service": "Service",
    "fi": "F&I",
    "legal": "Legal",
    "billing": "Billing",
    "general": "General",
}

URGENCY_LABELS = {
    "critical": "Critical",
    "high": "High",
    "normal": "Normal",
    "low": "Low",
}

ROUTE_LABELS = {
    "sales_manager": "Sales manager",
    "service_advisor": "Service advisor",
    "fi_manager": "F&I manager",
    "legal_compliance": "Legal / compliance",
    "controller": "Controller",
    "bdc": "BDC",
}

CATEGORY_TO_ROUTE = {
    "sales": "sales_manager",
    "service": "service_advisor",
    "fi": "fi_manager",
    "legal": "legal_compliance",
    "billing": "controller",
    "general": "bdc",
}

BACKENDS = ("hybrid", "model", "rules")
DEFAULT_BACKEND = "hybrid"
