# -*- coding: utf-8 -*-
"""
CogVideoX-2B API 服务
适配 8GB 显存以下显卡（使用 CPU 卸载）

启动服务:
    python cogvideo_api.py

API 文档:
    http://localhost:8000/docs
"""

import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video
from PIL import Image
import torch
import tempfile

app = FastAPI(title="CogVideoX-2B API", version="1.0.0")

# 全局模型管道（启动时加载一次）
pipe = None


@app.on_event("startup")
def load_model():
    """启动时加载模型"""
    global pipe
    print("=" * 50)
    print("加载 CogVideoX-2B 模型（首次运行需要下载，请耐心等待）...")

    pipe = CogVideoXPipeline.from_pretrained(
        'THUDM/CogVideoX-2B',
        torch_dtype=torch.float16,
    )

    # 适配 8GB 以下显存：使用 CPU 卸载
    pipe.enable_model_cpu_offload()

    print("模型加载完成!")
    print("=" * 50)


@app.get("/")
def root():
    """根路径"""
    return {"message": "CogVideoX-2B API", "version": "1.0.0"}


@app.get("/health")
def health():
    """健康检查"""
    return {"status": "ok"}


@app.post("/video/text")
async def text_to_video(
    prompt: str = Form(..., description="视频描述"),
    num_frames: int = Form(49, description="帧数（默认49帧约6秒）"),
    guidance_scale: float = Form(7.5, description="引导强度"),
):
    """
    文字生成视频

    Args:
        prompt: 文字描述
        num_frames: 帧数
        guidance_scale: 引导强度

    Returns:
        视频文件
    """
    if pipe is None:
        raise HTTPException(status_code=500, detail="模型未加载")

    print(f"文生视频请求: {prompt[:50]}...")

    try:
        # 生成视频
        output = pipe(
            prompt,
            num_frames=num_frames,
            guidance_scale=guidance_scale,
        )

        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as f:
            temp_path = f.name
            video_frames = output.frames[0]
            export_to_video(video_frames, temp_path, fps=8)

        return FileResponse(temp_path, media_type="video/mp4", filename="output.mp4")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/video/image")
async def image_to_video(
    image: UploadFile = File(..., description="输入图片文件"),
    prompt: str = Form(..., description="视频描述"),
    num_frames: int = Form(49, description="帧数（默认49帧约6秒）"),
    guidance_scale: float = Form(7.5, description="引导强度"),
):
    """
    图片生成视频

    Args:
        image: 输入图片文件
        prompt: 文字描述
        num_frames: 帧数
        guidance_scale: 引导强度

    Returns:
        视频文件
    """
    if pipe is None:
        raise HTTPException(status_code=500, detail="模型未加载")

    print(f"图生视频请求: {prompt[:50]}...")

    try:
        # 读取上传的图片
        init_image = Image.open(image.file).convert("RGB")

        # 生成视频
        output = pipe(
            prompt,
            image=init_image,
            num_frames=num_frames,
            guidance_scale=guidance_scale,
        )

        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as f:
            temp_path = f.name
            video_frames = output.frames[0]
            export_to_video(video_frames, temp_path, fps=8)

        return FileResponse(temp_path, media_type="video/mp4", filename="output.mp4")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
