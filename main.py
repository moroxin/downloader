from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from subprocess import Popen, PIPE
from urllib.parse import quote
import subprocess, os, json, tempfile

app = FastAPI()

# 🔓 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📁 Setup download directory
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 🗂️ Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_home():
    return FileResponse("static/index.html")

# 🔍 Preview with sorted formats, sizes, and labels
@app.get("/preview")
def get_preview(url: str = Query(...)):
    try:
        cmd = ["yt-dlp", "--dump-json", "--skip-download", url]
        output = subprocess.check_output(cmd).decode()
        data = json.loads(output)

        formats = []
        for f in data.get("formats", []):
            if not f.get("format_id") or not f.get("url"):
                continue
            height = f.get("height") or 0
            ext = f.get("ext") or "mp4"
            size = f.get("filesize") or f.get("filesize_approx")
            size_str = f"{round(size / 1024 / 1024, 1)}MB" if size else "?"
            label = f"{height}p - {ext} [{size_str}]"
            formats.append({
                "format_id": f["format_id"],
                "label": label,
                "height": height
            })

        formats.sort(key=lambda x: x["height"], reverse=True)

        return {
            "title": data.get("title", "No Title"),
            "thumbnail": data.get("thumbnail", ""),
            "formats": [{"format_id": f["format_id"], "label": f["label"]} for f in formats]
        }

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


# 📥 YouTube
@app.get("/download/youtube")
def download_youtube(youtube_url: str = Query(...), quality: str = Query("best")):
    try:
        if '+' in quality:
            # Merge required
            output_path = os.path.join(tempfile.gettempdir(), "merged_video.mp4")
            cmd = ["yt-dlp", "-f", quality, "-o", output_path, youtube_url]
            subprocess.run(cmd, check=True)
            return FileResponse(output_path, filename="youtube_video.mp4", media_type="video/mp4")
        else:
            # Stream directly
            cmd = ["yt-dlp", "-f", quality, "-o", "-", youtube_url]
            process = Popen(cmd, stdout=PIPE)
            headers = {
                "Content-Disposition": f'attachment; filename="{quote("youtube_video.mp4")}"',
                "Content-Type": "video/mp4"
            }
            return StreamingResponse(process.stdout, headers=headers, media_type="video/mp4")

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# 📥 Instagram
@app.get("/download/instagram")
def download_instagram(instagram_url: str = Query(...), quality: str = Query("best")):
    try:
        cmd = [
            "yt-dlp",
            "-f", quality,
            "-o", "-", instagram_url
        ]
        process = Popen(cmd, stdout=PIPE)
        headers = {
            "Content-Disposition": f'attachment; filename="{quote("instagram_video.mp4")}"',
            "Content-Type": "video/mp4"
        }
        return StreamingResponse(process.stdout, headers=headers, media_type="video/mp4")

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
