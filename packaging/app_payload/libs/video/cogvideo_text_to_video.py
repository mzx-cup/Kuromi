# -*- coding: utf-8 -*-
"""
CogVideoX-2B 文生视频脚本
适配 8GB 显存以下显卡（使用 CPU 卸载）

使用方法:
1. 安装依赖: pip install diffusers transformers accelerate sentencepiece
2. 运行: python cogvideo_text_to_video.py --prompt "一个男人在公园里跑步"
"""

import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video
import torch


def generate_video_from_text(
    prompt: str,
    output_path: str = "output.mp4",
    num_frames: int = 49,
    guidance_scale: float = 7.5,
):
    """
    文字生成视频

    Args:
        prompt: 文字描述
        output_path: 输出视频路径
        num_frames: 帧数（默认49帧约6秒）
        guidance_scale: 提示词引导强度

    Returns:
        output_path: 视频保存路径
    """
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

    parser = argparse.ArgumentParser(description="CogVideoX 文生视频")
    parser.add_argument("--prompt", type=str, default="一个男人在公园里跑步，背景是绿树和蓝天", help="视频描述")
    parser.add_argument("--output", type=str, default="test_video.mp4", help="输出路径")
    parser.add_argument("--frames", type=int, default=49, help="帧数")
    parser.add_argument("--guidance", type=float, default=7.5, help="引导强度")

    args = parser.parse_args()

    result = generate_video_from_text(
        prompt=args.prompt,
        output_path=args.output,
        num_frames=args.frames,
        guidance_scale=args.guidance,
    )
    print(f"完成: {result}")
