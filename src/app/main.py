import asyncio
import os
import shutil
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fontbro import Font

app = FastAPI()

FONT_DIR = "/data/fonts"
DOWNLOAD_DIR = "/data/download"


class BuildData(BaseModel):
    content: str | None = None
    font_file: str


@app.get("/")
def root():
    return {"Hello": "Fonts API"}


# 生成 woff2 文件
def font_to_woff2(content: str, font_file: str, save_file: str):
    saved_path = ''

    try:
        font = Font(font_file)

        if content:
            font.subset(text=content)

        saved_path = font.save_as_woff2(
            filepath=save_file,
            overwrite=True
        )
    except Exception as err:
        print(f"{font_file} => {save_file}, Error {err=}")
    else:
        font.close()

    return saved_path


# 构建字体文件并返回字体链接
@app.post("/build/")
def build(data: BuildData):
    directory = uuid.uuid4().hex
    directory_path = os.path.join(DOWNLOAD_DIR, directory)
    os.makedirs(directory_path, exist_ok=True)

    font_file = os.path.join(FONT_DIR, data.font_file)
    save_file = os.path.join(directory_path, "font.woff2")

    saved_path = font_to_woff2(data.content, font_file, save_file)

    if not saved_path:
        shutil.rmtree(directory_path, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Font build failed")

    return {
        "url": f"/download/{directory}/font.woff2"
    }


# 10分钟后自动删除目录
async def delete_directory(directory: str):
    await asyncio.sleep(600)
    shutil.rmtree(directory, ignore_errors=True)


# 下载生成的 woff2 文件
@app.get("/download/{directory}/{filename}")
async def download(directory: str, filename: str):
    if not directory.isalnum():
        raise HTTPException(status_code=400, detail="Invalid directory")

    if os.path.basename(filename) != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    directory_path = os.path.join(DOWNLOAD_DIR, directory)
    file_path = os.path.join(directory_path, filename)

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    asyncio.create_task(delete_directory(directory_path))

    return FileResponse(
        file_path,
        filename=filename,
        media_type="font/woff2"
    )