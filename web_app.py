from fastapi import FastAPI, WebSocket, HTTPException, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import os
import json
from config import config
from telethon import TelegramClient
from exporter import TelegramExporter

app = FastAPI(title="Telegram Group Exporter Web UI")

# Mount output directory so we can download or preview directly
os.makedirs(config.OUTPUT_DIR, exist_ok=True)
app.mount("/output", StaticFiles(directory=config.OUTPUT_DIR), name="output")

html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram Group Exporter</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-weight: bold; margin-bottom: 5px; }
        input[type="text"], input[type="number"], textarea { width: 100%; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 20px; background-color: #0088cc; color: white; border: none; cursor: pointer; }
        button:hover { background-color: #006699; }
        .log-box { background: #f4f4f4; padding: 10px; height: 300px; overflow-y: auto; font-family: monospace; white-space: pre-wrap; margin-top: 20px; border: 1px solid #ccc; }
        #download-links { margin-top: 20px; }
        .link-item { margin-bottom: 10px; padding: 10px; background: #e9f7ef; border-left: 4px solid #28b463; }
    </style>
</head>
<body>
    <h1>Telegram Group Exporter</h1>
    
    <div id="config-form">
        <div class="form-group">
            <label>API ID:</label>
            <input type="text" id="api_id" value="{api_id}">
        </div>
        <div class="form-group">
            <label>API Hash:</label>
            <input type="text" id="api_hash" value="{api_hash}">
        </div>
        <div class="form-group">
            <label>Phone Number (with country code):</label>
            <input type="text" id="phone" value="{phone}">
        </div>
        <div class="form-group">
            <label>Start Date (YYYY-MM-DD):</label>
            <input type="text" id="start_date" value="{start_date}">
        </div>
        <div class="form-group">
            <label>Group Links (one per line):</label>
            <textarea id="group_links" rows="5"></textarea>
        </div>
        
        <button id="start-btn" onclick="startExport()">Start Export</button>
        <button id="stop-btn" onclick="stopExport()" style="background-color: #cc0000; display: none;">Stop Export</button>
    </div>

    <div id="login-section" style="display:none; margin-top:20px; padding:15px; border:1px solid #ffcc00; background:#ffffe6;">
        <h3>Login Required</h3>
        <p>A login code has been sent to your Telegram app. Please enter it below:</p>
        <input type="text" id="login_code" placeholder="Enter code here">
        <button onclick="submitCode()">Submit Code</button>
    </div>

    <h3>Execution Logs</h3>
    <div class="log-box" id="log-box"></div>

    <div id="download-links"></div>

    <script>
        let ws;
        let isExporting = false;

        async function checkStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                if (data.is_exporting) {
                    isExporting = true;
                    document.getElementById('start-btn').disabled = true;
                    document.getElementById('start-btn').style.backgroundColor = '#cccccc';
                    document.getElementById('stop-btn').style.display = 'inline-block';
                    connectWebSocket();
                } else {
                    isExporting = false;
                    document.getElementById('start-btn').disabled = false;
                    document.getElementById('start-btn').style.backgroundColor = '#0088cc';
                    document.getElementById('stop-btn').style.display = 'none';
                }
            } catch (e) {
                console.error("Status check failed", e);
            }
        }

        function connectWebSocket() {
            if (ws && ws.readyState === WebSocket.OPEN) return;
            ws = new WebSocket("ws://" + window.location.host + "/ws/export");
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'log') {
                    const logBox = document.getElementById('log-box');
                    logBox.innerHTML += data.message + "\\n";
                    logBox.scrollTop = logBox.scrollHeight;
                } else if (data.type === 'need_code') {
                    document.getElementById('login-section').style.display = 'block';
                } else if (data.type === 'login_success') {
                    document.getElementById('login-section').style.display = 'none';
                } else if (data.type === 'error') {
                    alert('Error: ' + data.message);
                    checkStatus();
                } else if (data.type === 'complete' || data.type === 'stopped') {
                    fetchDownloadLinks();
                    checkStatus();
                }
            };
            ws.onclose = function() {
                if (isExporting) {
                    setTimeout(connectWebSocket, 2000);
                }
            };
        }

        async function startExport() {
            const api_id = document.getElementById('api_id').value;
            const api_hash = document.getElementById('api_hash').value;
            const phone = document.getElementById('phone').value;
            const start_date = document.getElementById('start_date').value;
            const group_links = document.getElementById('group_links').value;

            if (!group_links.trim()) {
                alert("Please provide at least one group link.");
                return;
            }

            document.getElementById('log-box').innerHTML = "";
            document.getElementById('download-links').innerHTML = "";
            
            document.getElementById('start-btn').disabled = true;
            document.getElementById('start-btn').style.backgroundColor = '#cccccc';
            document.getElementById('stop-btn').style.display = 'inline-block';
            
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                connectWebSocket();
            }

            // Small delay to ensure WS is open
            setTimeout(() => {
                ws.send(JSON.stringify({
                    action: 'start',
                    config: { api_id, api_hash, phone, start_date },
                    links: group_links.split('\\n').filter(l => l.trim())
                }));
                setTimeout(checkStatus, 1000);
            }, 500);
        }

        async function stopExport() {
            if (confirm("Are you sure you want to stop the export?")) {
                await fetch('/api/stop', { method: 'POST' });
                document.getElementById('stop-btn').style.display = 'none';
                checkStatus();
            }
        }

        function submitCode() {
            const code = document.getElementById('login_code').value;
            if (code && ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ action: 'submit_code', code: code }));
            }
        }

        async function deleteExport(folderName) {
            if (confirm(`Are you sure you want to delete ${folderName}?`)) {
                await fetch(`/api/exports/${folderName}`, { method: 'DELETE' });
                fetchDownloadLinks();
            }
        }

        async function fetchDownloadLinks() {
            const res = await fetch('/api/exports');
            const data = await res.json();
            const container = document.getElementById('download-links');
            container.innerHTML = "<h3>Available Exports:</h3>";
            
            if (data.exports.length === 0) {
                container.innerHTML += "<p>No exports found.</p>";
                return;
            }

            data.exports.forEach(exp => {
                container.innerHTML += `
                    <div class="link-item">
                        <strong>${exp}</strong><br>
                        <a href="/output/${exp}/index.html" target="_blank">View HTML</a> |
                        <a href="/api/download/${exp}">Download ZIP</a> |
                        <a href="javascript:void(0)" onclick="deleteExport('${exp}')" style="color:red;">Delete</a>
                    </div>
                `;
            });
        }
        
        // Check status and fetch existing exports on load
        checkStatus();
        fetchDownloadLinks();
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_index():
    html = html_template
    html = html.replace("{api_id}", str(config.API_ID or ""))
    html = html.replace("{api_hash}", str(config.API_HASH or ""))
    html = html.replace("{phone}", str(config.PHONE or ""))
    html = html.replace("{start_date}", str(config.START_DATE or "2024-01-01"))
    return html

# Global state for tracking export
export_status = {"is_exporting": False}
current_exporter = None
export_logs = []  # Cache to keep recent logs
active_websockets = set()
auth_code_queue = asyncio.Queue()
export_task_ref = None  # Hold a reference to the task so it isn't garbage collected

async def broadcast_ws(message: dict):
    global active_websockets
    to_remove = set()
    for ws in active_websockets:
        try:
            await ws.send_json(message)
        except Exception:
            to_remove.add(ws)
    for ws in to_remove:
        active_websockets.discard(ws)

async def broadcast_log(msg: str):
    global export_logs
    export_logs.append(msg)
    if len(export_logs) > 200:
        export_logs.pop(0)
    await broadcast_ws({"type": "log", "message": msg})

@app.get("/api/status")
async def get_status():
    return export_status

@app.post("/api/stop")
async def stop_export():
    global current_exporter
    if current_exporter:
        current_exporter.is_cancelled = True
        return {"status": "stopping"}
    return {"status": "not_running"}

@app.get("/api/exports")
async def list_exports():
    try:
        dirs = []
        for d in os.listdir(config.OUTPUT_DIR):
            folder_path = os.path.join(config.OUTPUT_DIR, d)
            if os.path.isdir(folder_path):
                # Check if index.html exists to verify it's a valid export
                if os.path.exists(os.path.join(folder_path, "index.html")):
                    dirs.append(d)
        return {"exports": dirs}
    except Exception:
        return {"exports": []}

@app.delete("/api/exports/{folder_name}")
async def delete_export(folder_name: str):
    import shutil
    folder_path = os.path.join(config.OUTPUT_DIR, folder_name)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
    zip_path = os.path.join(config.OUTPUT_DIR, f"{folder_name}.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    return {"status": "deleted"}

@app.get("/api/download/{folder_name}")
async def download_export(folder_name: str):
    import shutil
    folder_path = os.path.join(config.OUTPUT_DIR, folder_name)
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Export not found")
        
    zip_path = os.path.join(config.OUTPUT_DIR, f"{folder_name}")
    shutil.make_archive(zip_path, 'zip', folder_path)
    
    return FileResponse(f"{zip_path}.zip", filename=f"{folder_name}.zip")


async def run_export_task(cfg, links):
    global export_status, current_exporter
    client = None
    
    try:
        await broadcast_log("Connecting to Telegram...")
        
        client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            await broadcast_log(f"Login required for {config.PHONE}")
            await client.send_code_request(config.PHONE)
            await broadcast_ws({"type": "need_code"})
            
            # Wait for code
            code = await auth_code_queue.get()
            
            try:
                await client.sign_in(config.PHONE, code)
                await broadcast_ws({"type": "login_success"})
                await broadcast_log("Login successful!")
            except Exception as e:
                await broadcast_ws({"type": "error", "message": f"Login failed: {str(e)}"})
                return
                
        await broadcast_log("Starting export process...")
        exporter = TelegramExporter(client)
        current_exporter = exporter
        
        import logging
        class WSHandler(logging.Handler):
            def emit(self, record):
                msg = self.format(record)
                asyncio.create_task(broadcast_log(msg))
                
        logger = logging.getLogger("tg_exporter")
        ws_handler = WSHandler()
        ws_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(ws_handler)
        
        for link in links:
            await broadcast_log(f"Processing link: {link}")
            try:
                info, err = await exporter.export_group(link)
                if err:
                    await broadcast_log(f"Error for {link}: {err}")
                else:
                    await broadcast_log(f"Success for {link}. Exported {info.get('message_count_exported')} messages.")
            except Exception as e:
                await broadcast_log(f"Unhandled error for {link}: {e}")
                
        logger.removeHandler(ws_handler)
        await broadcast_log("Export complete or stopped!")
        if exporter.is_cancelled:
            await broadcast_ws({"type": "stopped"})
        else:
            await broadcast_ws({"type": "complete"})
            
    except Exception as e:
        await broadcast_ws({"type": "error", "message": str(e)})
    finally:
        export_status["is_exporting"] = False
        current_exporter = None
        if client:
            await client.disconnect()

@app.websocket("/ws/export")
async def websocket_endpoint(websocket: WebSocket):
    global export_status, current_exporter, export_logs, active_websockets
    await websocket.accept()
    active_websockets.add(websocket)
    
    # Send cached logs to new connections
    for log_msg in export_logs:
        try:
            await websocket.send_json({"type": "log", "message": log_msg})
        except:
            break
            
    try:
        from starlette.websockets import WebSocketDisconnect
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break
                
            if data.get("action") == "start":
                if export_status["is_exporting"]:
                    await websocket.send_json({"type": "error", "message": "Export already in progress."})
                    continue
                    
                export_status["is_exporting"] = True
                export_logs.clear() # Clear logs on new export
                
                cfg = data.get("config", {})
                links = data.get("links", [])
                
                # Update config temporarily
                config.API_ID = cfg.get("api_id")
                config.API_HASH = cfg.get("api_hash")
                config.PHONE = cfg.get("phone")
                config.START_DATE = cfg.get("start_date")
                config.save()
                
                # Clear queue before starting
                while not auth_code_queue.empty():
                    auth_code_queue.get_nowait()
                    
                global export_task_ref
                export_task_ref = asyncio.create_task(run_export_task(cfg, links))
                
            elif data.get("action") == "submit_code":
                code = data.get("code")
                await auth_code_queue.put(code)
                
    except Exception:
        pass
    finally:
        active_websockets.discard(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
