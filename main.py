from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from datetime import datetime
import json
import asyncio
import httpx

app = FastAPI()

# Настройка CORS (разрешаем запросы от фронтенда)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://datagetws.web.app", "https://sloths-clicker.web.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Хранилище заказов
orders = []
order_id_counter = 1

# Клиент для отправки запросов в админку (асинхронный)
admin_api_url = "https://sloths-clicker.web.app/api/admin/orders"


# SSE-стриминг заказов
async def order_event_generator():
    while True:
        await asyncio.sleep(1)  # Задержка для экономии CPU
        yield f"data: {json.dumps(orders)}\n\n"


# Роуты
@app.get("/")
async def home():
    return {"message": "Orders API"}


@app.post("/api/orders")
async def create_order(request: Request):
    global order_id_counter

    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Валидация данных
    if not data or "items" not in data:
        raise HTTPException(status_code=400, detail="Missing items")

    # Создание заказа
    new_order = dict(id=order_id_counter, timestamp=datetime.now().isoformat(), address=data.get("address", ""),
                     items=data["items"], total=sum(item["price"] * item["quantity"] for item in data["items"]),
                     deliveryDetails=data.get("deliveryDetails"))

    orders.append(new_order)
    order_id_counter += 1

    # Отправка в админку (асинхронно)
    async with httpx.AsyncClient() as client:
        try:
            await client.post(admin_api_url, json=new_order)
        except Exception as e:
            print(f"Error sending to admin: {e}")

    return JSONResponse(new_order, status_code=201)


@app.get("/api/orders/stream")
async def stream_orders():
    return StreamingResponse(
        order_event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )

# Запуск: uvicorn main:app --reload --port 5000