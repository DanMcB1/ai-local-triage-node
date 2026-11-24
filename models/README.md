The quantized GGUF weights are **not** stored in this repository.

Download them once with:

```bash
./download_model.sh
```

That script fetches `qwen2.5-1.5b-instruct-q4_k_m.gguf` (~1.04 GB) from the official
Hugging Face repo [Qwen/Qwen2.5-1.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF)
and verifies a pinned SHA-256 checksum before the file is used.

The app and the tests still run without this file, in rules-only mode.
