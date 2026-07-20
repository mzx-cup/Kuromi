import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from diffusers import CogVideoXPipeline
import torch

print('开始加载 CogVideoX-2B 模型...')
print('注意: 8GB 显存不足，将使用 CPU 卸载（速度较慢）')

pipe = CogVideoXPipeline.from_pretrained('THUDM/CogVideoX-2B', torch_dtype=torch.float16)
pipe.enable_model_cpu_offload()  # 使用 CPU 卸载节省显存
print('CogVideoX-2B 模型加载成功!')
