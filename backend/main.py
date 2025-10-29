from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from utils.socket_utils import connection_manager
from api.v1 import api_v1_router
import uvicorn

app = FastAPI()
port = 5600

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api")
def home():
    return "Hello, World!"
app.include_router(api_v1_router, prefix="/api/v1")

# Websocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await connection_manager.broadcast(f"Message text was: {data}")
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        await connection_manager.broadcast("A client just disconnected.")


# Serve the Vue app in production mode
try:
    print(Path(__file__).resolve().parent)
    # Directory where Vue app build output is located
    build_dir = Path(__file__).resolve().parent / "dist"
    print(build_dir)
    index_path = build_dir / "index.html"

    # Serve assets files from the build directory
    app.mount("/assets", StaticFiles(directory=build_dir / "assets"), name="assets")

    # Catch-all route for SPA
    @app.get("/{catchall:path}")
    async def serve_spa(catchall: str):
        # If the requested file exists, serve it, else serve index.html
        path = build_dir / catchall
        if path.is_file():
            return FileResponse(path)
        return FileResponse(index_path)

except RuntimeError:
    # The build directory does not exist
    print("No build directory found. Running in development mode.")

if __name__ == "__main__":
    uvicorn.run(app, host='127.0.0.1', port=port)