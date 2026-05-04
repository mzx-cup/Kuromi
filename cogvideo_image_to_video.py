# -*- coding: utf-8 -*-
"""
CogVideoX-2B 图生视频脚本
使用 ModelScope 国内镜像下载模型

使用方法:
1. 先注册 ModelScope: https://www.modelscope.cn
2. 安装依赖: pip install modelscope torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
3. 运行: python cogvideo_image_to_video.py --image input.png --prompt "这个人开始走路"
"""

from modelscope import CogVideoXPipeline
from modelscope.outputs import OutputKeys
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

    # 加载模型（首次会自动从 ModelScope 下载）
    pipe = CogVideoXPipeline('THUDM/CogVideoX-2B', device='cuda:0')
    pipe.to(torch.float16)

    print(f"开始生成视频: {prompt[:50]}...")

    # 生成视频
    output = pipe({
        'text': prompt,
        'image': init_image
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
