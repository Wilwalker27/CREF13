import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

try:
    from . import db
except ImportError:
    import db

HISTORY_LIMIT = 5
DESTINATIONS = [
	"Recursos Humanos",
	"Auditório",
	"Retornar para recepção",
	"Sala de negociação",
]

app = FastAPI()
BASE_DIR = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/img", StaticFiles(directory=os.path.join(BASE_DIR, "img")), name="img")


def render_page(request: Request, template_name: str, title: str):
	asset_files = {
		"styles": "styles.css",
		"common": "common.js",
		"panel": "panel.js",
		"reception": "reception.js",
		"negotiation": "negotiation.js",
	}
	asset_versions = {
		key: int(os.path.getmtime(os.path.join(BASE_DIR, "static", file_name)))
		for key, file_name in asset_files.items()
	}
	return templates.TemplateResponse(
		template_name,
		{"request": request, "title": title, "asset_versions": asset_versions},
	)


class RegisterRequest(BaseModel):
	name: str = Field(min_length=2, max_length=120)
	registration: str = Field(min_length=2, max_length=40)
	priority: bool = False


class DispatchRequest(BaseModel):
	destination: str = Field(min_length=2, max_length=80)


class ConnectionManager:
	def __init__(self):
		self.active = set()

	async def connect(self, websocket: WebSocket):
		await websocket.accept()
		self.active.add(websocket)

	def disconnect(self, websocket: WebSocket):
		self.active.discard(websocket)

	async def broadcast(self, message: dict):
		for connection in list(self.active):
			try:
				await connection.send_json(message)
			except Exception:
				self.disconnect(connection)


manager = ConnectionManager()


@app.on_event("startup")
def startup():
	db.init_db()


@app.get("/")
def root():
	return RedirectResponse(url="/painel")


@app.get("/painel")
def panel(request: Request):
	return render_page(request, "painel.html", "Painel de Chamados")


@app.get("/recepcao")
def reception(request: Request):
	return render_page(request, "recepcao.html", "Recepção")


@app.get("/atendimento")
def negotiation(request: Request):
	return render_page(request, "atendimento.html", "Atendimento")


@app.get("/negociacao")
def negotiation_redirect():
	return RedirectResponse(url="/atendimento")


@app.get("/api/queue")
def api_queue():
	return db.list_waiting()


@app.get("/api/history")
def api_history():
	return db.list_history(HISTORY_LIMIT)


@app.get("/api/destinations")
def api_destinations():
	return DESTINATIONS


@app.post("/api/register")
async def api_register(payload: RegisterRequest):
	call_id = db.create_call(payload.name, payload.registration, payload.priority)
	await manager.broadcast({"type": "refresh"})
	return {"id": call_id}


@app.post("/api/edit/{call_id}")
async def api_edit(call_id: int, payload: RegisterRequest):
	updated = db.update_call(call_id, payload.name, payload.registration, payload.priority)
	if updated == 0:
		raise HTTPException(status_code=404, detail="Registro não encontrado")
	await manager.broadcast({"type": "refresh"})
	return {"status": "ok"}


@app.post("/api/dispatch/{call_id}")
async def api_dispatch(call_id: int, payload: DispatchRequest):
	updated = db.dispatch_call(call_id, payload.destination)
	if updated == 0:
		raise HTTPException(status_code=404, detail="Registro não encontrado")
	await manager.broadcast({"type": "refresh"})
	return {"status": "ok"}


@app.delete("/api/queue/{call_id}")
async def api_delete_waiting(call_id: int):
	deleted = db.delete_waiting_call(call_id)
	if deleted == 0:
		raise HTTPException(status_code=404, detail="Registro não encontrado")
	await manager.broadcast({"type": "refresh"})
	return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
	await manager.connect(websocket)
	try:
		while True:
			await websocket.receive_text()
	except WebSocketDisconnect:
		manager.disconnect(websocket)