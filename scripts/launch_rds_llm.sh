#!/bin/bash
# launch_rds_llm.sh
# Start one Ollama container for RDS-Review coding, on one or more GPUs.
# Usage:
#   bash launch_rds_llm.sh --gpus 5,6,7,8 --model qwen3.5:122b --port 11450
#   bash launch_rds_llm.sh --gpus 9 --model qwen3.8:27b --port 11451
#   bash launch_rds_llm.sh --stop
# Models are stored in MODELS_DIR, by default $HOME/models.
set -e
GPUS=""
MODEL=""
PORT=""
MODELS_DIR="${MODELS_DIR:-$HOME/models}"
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
NAME="rds_llm_${PORT}"
echo "Starting $MODEL on GPUs $GPUS, port $PORT (container: $NAME)"
docker rm -f "$NAME" 2>/dev/null || true
docker run -d \
    --gpus "\"device=$GPUS\"" \
    -e OLLAMA_KEEP_ALIVE=-1 \
    --shm-size=16g \
    -v "$MODELS_DIR:/root/.ollama/models" \
    -p "$PORT:11434" \
    --name "$NAME" \
    ollama/ollama
sleep 8
docker exec "$NAME" ollama pull "$MODEL"
echo "Loading into VRAM..."
docker exec "$NAME" ollama run "$MODEL" "hi" > /dev/null 2>&1 || true
echo "Ollama version: $(docker exec "$NAME" ollama --version | tail -1)"
curl -s "http://localhost:$PORT/api/tags" | python3 -c "import sys,json; [print('Model:', m['name'], 'digest:', m['digest']) for m in json.load(sys.stdin)['models'] if m['name']=='$MODEL']"
docker exec "$NAME" ollama ps
echo "Ready: http://localhost:$PORT"
