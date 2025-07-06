# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository implements Delayed Streams Modeling (DSM) for streaming multimodal sequence-to-sequence learning, with Kyutai Speech-To-Text (STT) and Text-To-Speech (TTS) models. The project provides multiple implementations (PyTorch, Rust, MLX) for different use cases.

## Key Commands

### Development Setup
```bash
# Install pre-commit hooks (choose one)
pip install pre-commit && pre-commit install
uvx pre-commit install
```

### Running STT Models

```bash
# PyTorch STT from file
uv run scripts/stt_from_file_pytorch.py --hf-repo kyutai/stt-2.6b-en --file audio/bria.mp3
python -m moshi.run_inference --hf-repo kyutai/stt-2.6b-en audio/bria.mp3

# PyTorch STT with prompts
uv run scripts/stt_from_file_pytorch_with_prompt.py --hf-repo kyutai/stt-2.6b-en --file bria.mp3 --prompt_text "specific word"

# Rust STT server
cargo install --features cuda moshi-server
moshi-server worker --config configs/config-stt-en-hf.toml  # For English model
moshi-server worker --config configs/config-stt-en_fr-hf.toml  # For English+French model

# Rust standalone STT
cd stt-rs && cargo run --features cuda -r -- ../audio/bria.mp3
```

### Running TTS Models

```bash
# PyTorch TTS
echo "Hello world" | python scripts/tts_pytorch.py - -  # Plays audio immediately
python scripts/tts_pytorch.py input.txt output.wav  # File to file

# Rust TTS server
moshi-server worker --config configs/config-tts.toml
echo "Hello world" | python scripts/tts_rust_server.py - -

# MLX TTS (Apple Silicon)
echo "Hello world" | python scripts/tts_mlx.py - - --quantize 8
```

### Code Quality
```bash
# Pre-commit runs automatically, but can be run manually
pre-commit run --all-files

# Ruff is configured in pre-commit for Python linting/formatting
```

## Architecture & Code Organization

### Core Components

1. **Model Loading**: All scripts support loading models from HuggingFace repos or local files:
   - `--hf-repo`: Load from HuggingFace (e.g., `kyutai/stt-2.6b-en`)
   - `--tokenizer`, `--moshi-weight`, `--mimi-weight`: Load from local files
   - `--config-path`: Use local config file

2. **Script Patterns**: All Python scripts in `/scripts/` use inline dependency declarations compatible with `uv run`, making them self-contained executables.

3. **Configuration**: TOML configs in `/configs/` define model architectures and server settings. Key configs:
   - `config-stt-en-hf.toml`: English STT model
   - `config-stt-en_fr-hf.toml`: English + French STT model
   - `config-tts.toml`: TTS model

4. **Model Variants**:
   - **STT Models**: 
     - `kyutai/stt-1b-en_fr`: 1B params, 0.5s delay, includes semantic VAD
     - `kyutai/stt-2.6b-en`: 2.6B params, 2.5s delay, English only
   - **TTS Model**: Single model supporting multiple voices

### Implementation-Specific Notes

- **PyTorch**: Research-focused, supports streaming inference, word-level timestamps
- **Rust**: Production-ready server with WebSocket support, handles batching (64 streams on L40S)
- **MLX**: Apple Silicon optimized, supports quantization for faster inference

### Key Dependencies

- Python: `moshi` (core ML), `julius` (audio), `librosa`, `soundfile`, `sphn`, `sentencepiece`, `torch`
- Rust: `candle` (ML framework), `moshi`, `kaudio` (audio)
- Hardware acceleration: CUDA, cuDNN, Metal support

## Important Considerations

1. **Licensing**: Python code is MIT licensed, Rust code is Apache licensed, model weights are CC-BY 4.0
2. **Device Support**: Default device is CUDA; use `--device` flag for PyTorch or `--cpu` for Rust
3. **Batch Processing**: H100 can handle 400 STT streams in real-time
4. **Semantic VAD**: Available in the 1B STT model for voice activity detection
5. **Word Timestamps**: STT models return word-level timing information