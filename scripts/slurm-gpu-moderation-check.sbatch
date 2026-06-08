#!/usr/bin/env bash
#SBATCH --job-name=big-brother-gpu-moderation
#SBATCH --partition=batch
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=slurm-gpu-moderation-%j.out
#SBATCH --error=slurm-gpu-moderation-%j.err

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"
mkdir -p .omo/ulw-loop/evidence
root_stdout="slurm-gpu-moderation-${SLURM_JOB_ID}.out"
root_stderr="slurm-gpu-moderation-${SLURM_JOB_ID}.err"
evidence_stdout=".omo/ulw-loop/evidence/slurm-gpu-moderation-${SLURM_JOB_ID}.out"
evidence_stderr=".omo/ulw-loop/evidence/slurm-gpu-moderation-${SLURM_JOB_ID}.err"
exec > >(tee "${evidence_stdout}") 2> >(tee "${evidence_stderr}" >&2)
export HF_HOME="${BIG_BROTHER_HF_HOME:-${PWD}/.omo/ulw-loop/huggingface-cache}"
export HF_HUB_DISABLE_TELEMETRY=1
export TRANSFORMERS_CACHE="${HF_HOME}/transformers"
mkdir -p "${HF_HOME}" "${TRANSFORMERS_CACHE}"

image_path_one="$(mktemp --suffix=.png)"
image_path_two="$(mktemp --suffix=.png)"
cleanup() {
  rm -f "${image_path_one}" "${image_path_two}"
  rm -f "${root_stdout}" "${root_stderr}"
}
trap cleanup EXIT

uv run --no-dev --with pillow python - "${image_path_one}" "${image_path_two}" <<'PY'
from pathlib import Path
from sys import argv

from PIL import Image

colors = ((32, 96, 160), (160, 96, 32))
for path, color in zip(argv[1:], colors, strict=True):
    image = Image.new("RGB", (224, 224), color=color)
    image.save(Path(path))
PY

nvidia-smi
uv run --no-dev --group gpu python -m big_brother.models.moderation_check \
  --config configs/model-inference.yaml \
  --image "${image_path_one}" \
  --image "${image_path_two}" \
  --coalesce-requests \
  --require-cuda
