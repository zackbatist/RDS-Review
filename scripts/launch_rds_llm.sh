#!/bin/bash
# launch_rds_llm.sh
# Start one llama.cpp server for a local language model, on one or more GPUs.
# Usage:
#   bash launch_rds_llm.sh --gpus 5,6,7,8 --model qwen3.5-122b --port 11450
#   bash launch_rds_llm.sh --gpus 9 --model qwen3.8-27b --port 11451
#   bash launch_rds_llm.sh --stop
# Model files are downloaded from Hugging Face at a fixed revision, checked against their SHA-256,
# and stored in MODELS_DIR, by default $HOME/models.
# The llama.cpp build is LLAMACPP_BUILD, by default b12375, so a rerun uses the same server.
# The context length is CTX, by default 16384 tokens.
set -e
GPUS=""
MODEL=""
PORT=""
MODELS_DIR="${MODELS_DIR:-$HOME/models}"
LLAMACPP_BUILD="${LLAMACPP_BUILD:-b12375}"
CTX="${CTX:-16384}"
STOP=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --gpus)  GPUS="$2";  shift 2 ;;
        --model) MODEL="$2"; shift 2 ;;
        --port)  PORT="$2";  shift 2 ;;
        --stop)  STOP=true;  shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done
if [[ "$STOP" == true ]]; then
    docker ps --format '{{.Names}}' | grep '^rds_llm_' | xargs -r docker rm -f
    exit 0
fi
if [[ -z "$GPUS" || -z "$MODEL" || -z "$PORT" ]]; then
    echo "Need --gpus, --model and --port"; exit 1
fi

# Each model: Hugging Face repository, revision, and its files with their SHA-256.
# The server loads the first file; a model split into parts finds the others beside it.
case $MODEL in
    qwen3.5-122b)
        REPO="unsloth/Qwen3.5-122B-A10B-GGUF"
        REVISION="51eab4d59d53f573fb9206cb3ce613f1d0aa392b"
        FILES=(
            "Q4_K_M/Qwen3.5-122B-A10B-Q4_K_M-00001-of-00003.gguf 467c9bd92ea518539cf75bf5a5fbfbd35e9a0b40d766ccaa67bf120e12041df3"
            "Q4_K_M/Qwen3.5-122B-A10B-Q4_K_M-00002-of-00003.gguf 90db14846413aebdac365b57206441437cac5f7e5037d94b325f0167f902e6e7"
            "Q4_K_M/Qwen3.5-122B-A10B-Q4_K_M-00003-of-00003.gguf e3c24b8ebec070bb4f69ea0aca25a16531da7440cd515529953e046882901f97"
        ) ;;
    qwen3.8-27b)
        REPO="unsloth/Qwen3.8-27B-GGUF"
        REVISION="4af51b3542f775b0a8e4b310bfb3f17e01c306c9"
        FILES=(
            "Qwen3.8-27B-UD-Q4_K_M.gguf 1bce504dfecd84153666928a41d8a66706f0158d3a317bc5196b72819d7dc529"
        ) ;;
    *) echo "Unknown model: $MODEL (qwen3.5-122b or qwen3.8-27b)"; exit 1 ;;
esac

DIR="$MODELS_DIR/$REPO/$REVISION"
for entry in "${FILES[@]}"; do
    read -r FILE SHA <<< "$entry"
    mkdir -p "$(dirname "$DIR/$FILE")"
    if [[ -f "$DIR/$FILE" ]]; then
        echo "Checking $FILE"
    else
        echo "Downloading $FILE"
        curl -L --fail -o "$DIR/$FILE.part" "https://huggingface.co/$REPO/resolve/$REVISION/$FILE"
        mv "$DIR/$FILE.part" "$DIR/$FILE"
    fi
    echo "$SHA  $DIR/$FILE" | sha256sum --check --quiet || { echo "Checksum mismatch: $FILE, deleted so the next run downloads it again"; rm -f "$DIR/$FILE"; exit 1; }
done
read -r FIRST _ <<< "${FILES[0]}"

NAME="rds_llm_${PORT}"
IMAGE="ghcr.io/ggml-org/llama.cpp:server-cuda-$LLAMACPP_BUILD"
echo "Starting $MODEL on GPUs $GPUS, port $PORT, llama.cpp $LLAMACPP_BUILD (container: $NAME)"
docker rm -f "$NAME" 2>/dev/null || true
docker run -d \
    --gpus "\"device=$GPUS\"" \
    -v "$DIR:/models:ro" \
    -p "$PORT:8080" \
    --name "$NAME" \
    "$IMAGE" \
    -m "/models/$FIRST" --host 0.0.0.0 --port 8080 \
    --ctx-size "$CTX" --n-gpu-layers 999 --parallel 1 --load-mode none --jinja

echo "Loading into VRAM..."
until curl -sf "http://localhost:$PORT/health" > /dev/null; do
    if ! docker ps --format '{{.Names}}' | grep -q "^$NAME$"; then
        echo "Server stopped. Last log lines:"; docker logs "$NAME" 2>&1 | tail -20; exit 1
    fi
    sleep 10
done
echo "Model: $REPO at revision $REVISION"
for entry in "${FILES[@]}"; do echo "  $entry"; done
echo "Image: $IMAGE, digest $(docker image inspect --format '{{index .RepoDigests 0}}' "$IMAGE")"
curl -s "http://localhost:$PORT/props" | python3 -c "import sys,json; p=json.load(sys.stdin); print('Build:', p.get('build_info', '')); print('Context:', p.get('default_generation_settings', {}).get('n_ctx', ''))"
echo "Ready: http://localhost:$PORT"
