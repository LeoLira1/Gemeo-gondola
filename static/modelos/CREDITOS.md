# Modelos 3D (.glb)

Convertidos de [nvidia/simready-assets](https://huggingface.co/datasets/nvidia/simready-assets) (NVIDIA SimReady),
licença [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). © NVIDIA Corporation.

| Arquivo | Asset original |
|---|---|
| `vehicle_forklift_blue_a01.glb` | `vehicle_forklift_blue_a01` (empilhadeira patolada elétrica, azul) |
| `vehicle_forklift_orange_a01.glb` | `vehicle_forklift_orange_a01` (empilhadeira patolada elétrica, laranja) |
| `vehicle_forklift_red_b01.glb` | `vehicle_forklift_red_b01` (selecionadora de pedidos, vermelha) |
| `vehicle_forklift_blue_c01.glb` | `vehicle_forklift_blue_c01` (empilhadeira contrabalançada, azul) |
| `vehicle_forklift_red_c01.glb` | `vehicle_forklift_red_c01` (empilhadeira contrabalançada, vermelha) |
| `palletJack_heavyDuty_a01.glb` | `palletJack_heavyDuty_a01` (paleteira manual) |
| `palletJack_lowProfile_a01.glb` | `palletJack_lowProfile_a01` (paleteira manual baixa) |
| `palletJack_scale_a01.glb` | `palletJack_scale_a01` (paleteira com balança) |

**Alterações:** OpenUSD convertido para glTF (Y para cima, metros, origem no chão como no original), só o
material UsdPreviewSurface (cor do OmniPBR onde os dois divergem), texturas UDIM juntadas num atlas e passadas
para WebP, malha simplificada para ~40 mil triângulos. Física, juntas e materiais MDL ficaram de fora.
Gerado por `assets/converter_simready.sh`.

Extensões glTF usadas: `KHR_mesh_quantization`, `EXT_texture_webp` (o GLTFLoader do three r128 lê as duas).
