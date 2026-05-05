# -*- coding: utf-8 -*-
"""
CogVideoX-2B 图生视频脚本
适配 8GB 显存以下显卡（使用 CPU 卸载）

使用方法:
1. 安装依赖: pip install diffusers transformers accelerate sentencepiece
2. 运行: python cogvideo_image_to_video.py --image input.png --prompt "这个人开始走路"
"""

import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video
from PIL import Image
import torch


def generate_video_from_image(
    image_path: str,
    prompt: str,
    output_path: str = "output.mp4",
    num_frames: int = 49,
    guidance_scale: float = 7.5,
):
    """
    图片生成视频

    Args:
        image_path: 输入图片路径
        prompt: 文字描述（描述图片中会发生什么）
        output_path: 输出视频路径
        num_frames: 帧数（默认49帧约6秒）
        guidance_scale: 提示词引导强度

    Returns:
        output_path: 视频保存路径
    """
    print(f"加载图片: {image_path}")
    init_image = Image.open(image_path).convert("RGB")

    print(f"加载 CogVideoX-2B 模型...")

    # 加载模型（首次会自动从 HuggingFace 下载）
    pipe = CogVideoXPipeline.from_pretrained(
        'THUDM/CogVideoX-2B',
        torch_dtype=torch.float16,
    )

    # 适配 8GB 以下显存：使用 CPU 卸载
    pipe.enable_model_cpu_offload()

    print(f"开始生成视频: {prompt[:50]}...")

    # 生成视频
    output = pipe(
        prompt,
        image=init_image,
        num_frames=num_frames,
        guidance_scale=guidance_scale,
    )

    # 保存视频 - 使用 export_to_video
    video_frames = output.frames[0]
    export_to_video(video_frames, output_path, fps=8)

    print(f"视频已保存: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CogVideoX 图生视频")
    parser.add_argument("--image", type=str, required=True, help="输入图片路径")
    parser.add_argument("--prompt", type=str, default="这个人开始慢慢走路", help="视频描述")
    parser.add_argument("--output", type=str, default="test_video.mp4", help="输出路径")
    parser.add_argument("--frames", type=int, default=49, help="帧数")
    parser.add_argument("--guidance", type=float, default=7.5, help="引导强度")

    args = parser.parse_args()

    result = generate_video_from_image(
        image_path=args.image,
        prompt=args.prompt,
        output_path=args.output,
        num_frames=args.frames,
        guidance_scale=args.guidance,
    )
    print(f"完成: {result}")
