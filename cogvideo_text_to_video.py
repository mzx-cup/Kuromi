# -*- coding: utf-8 -*-
"""
CogVideoX-2B 文生视频脚本
使用 ModelScope 国内镜像下载模型

使用方法:
1. 先注册 ModelScope: https://www.modelscope.cn
2. 安装依赖: pip install modelscope torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
3. 运行: python cogvideo_text_to_video.py
"""

from modelscope import CogVideoXPipeline
from modelscope.outputs import OutputKeys
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

    # 加载模型（首次会自动从 ModelScope 下载）
    pipe = CogVideoXPipeline('THUDM/CogVideoX-2B', device='cuda:0')
    pipe.to(torch.float16)

    print(f"开始生成视频: {prompt[:50]}...")

    # 生成视频
    output = pipe({
        'text': prompt,
    })

    # 保存视频
    video_key = OutputKeys.OUTPUT_VIDEO
    videos = output[video_key]

    if isinstance(videos, list):
        videos[0].save(output_path)
    else:
        videos.save(output_path)

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
