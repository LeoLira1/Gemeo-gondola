"""Baixa as empilhadeiras e paleteiras do dataset nvidia/simready-assets.

Uso: pip install huggingface_hub && python assets/baixar_simready.py
Os arquivos (~590 MB, formato OpenUSD) vão para assets/simready/, que é ignorada pelo git.
"""
from pathlib import Path

from huggingface_hub import snapshot_download

PASTAS = [
    "vehicle_forklift_blue_a01",
    "vehicle_forklift_blue_c01",
    "vehicle_forklift_orange_a01",
    "vehicle_forklift_red_b01",
    "vehicle_forklift_red_c01",
    "palletJack_heavyDuty_a01",
    "palletJack_lowProfile_a01",
    "palletJack_scale_a01",
]

if __name__ == "__main__":
    destino = Path(__file__).resolve().parent / "simready"
    snapshot_download(
        "nvidia/simready-assets",
        repo_type="dataset",
        allow_patterns=[f"{p}/*" for p in PASTAS],
        local_dir=destino,
        max_workers=8,
    )
    print(f"Assets em {destino}")
