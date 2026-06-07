from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_slurm_script_requests_gpu_and_runs_moderation_check() -> None:
    script = (ROOT / "scripts" / "slurm-gpu-moderation-check.sbatch").read_text(
        encoding="utf-8",
    )

    assert "#SBATCH --gres=gpu:1" in script
    assert "uv run --no-dev --group gpu python -m big_brother.models.moderation_check" in script
    assert "--require-cuda" in script
    assert "export HF_HOME=" in script
    assert "#SBATCH --output=slurm-gpu-moderation-%j.out" in script
    assert (
        'evidence_stdout=".omo/ulw-loop/evidence/slurm-gpu-moderation-${SLURM_JOB_ID}.out"'
        in script
    )
    assert 'tee "${evidence_stdout}"' in script


def test_default_model_inference_yaml_exposes_inference_hyperparameters() -> None:
    config = (ROOT / "configs" / "model-inference.yaml").read_text(encoding="utf-8")

    assert "model_name:" in config
    assert "device: cuda" in config
    assert "top_k:" in config
    assert "threshold:" in config
    assert "function_to_apply:" in config
    assert "explicit_labels:" in config
