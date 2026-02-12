import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from . import db

HISTORY_LIMIT = 5

app = FastAPI()
BASE_DIR = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/img", StaticFiles(directory=os.path.join(BASE_DIR, "img")), name="img")


class RegisterRequest(BaseModel):
	name: str = Field(min_length=2, max_length=120)
	registration: str = Field(min_length=2, max_length=40)


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
	return templates.TemplateResponse(
		"painel.html", {"request": request, "title": "Painel de Chamados"}
	)


@app.get("/recepcao")
def reception(request: Request):
	return templates.TemplateResponse(
		"recepcao.html", {"request": request, "title": "Recepção"}
	)


@app.get("/negociacao")
def negotiation(request: Request):
	return templates.TemplateResponse(
		"negociacao.html", {"request": request, "title": "Negociação"}
	)


@app.get("/api/queue")
def api_queue():
	return db.list_waiting()


@app.get("/api/history")
def api_history():
	return db.list_history(HISTORY_LIMIT)


@app.post("/api/register")
async def api_register(payload: RegisterRequest):
	call_id = db.create_call(payload.name, payload.registration)
	await manager.broadcast({"type": "refresh"})
	return {"id": call_id}


@app.post("/api/edit/{call_id}")
async def api_edit(call_id: int, payload: RegisterRequest):
	updated = db.update_call(call_id, payload.name, payload.registration)
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
	await manager.connect(websocket)
	try:
		while True:
			await websocket.receive_text()
	except WebSocketDisconnect:
		manager.disconnect(websocket)