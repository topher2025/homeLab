from fastapi import FastAPI
from database import Database
from pydantic import BaseModel
import os


class Log(BaseModel):
    timestamp: str
    threadname: str | None = None
    level: str
    logger: str
    message: str


DB_DSN = "postgresql://postgres:password@localhost:5432/lab"

app = FastAPI()
db = Database(DB_DSN)

app = FastAPI()

@app.on_event("startup")
async def startup():
    await db.connect()



@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()


@app.get("/migrate")
async def migrate():
    files = sorted(
        f for f in os.listdir("migrations")
        if f.endswith(".sql")
    )
    last_file = files[-1]

    await db.connect()
    
    exists = await db.fetch_val(
        "SELECT 1 FROM migrations WHERE version = :v",
        {"v": last_file}
    )

    if exists:
        return {"status": "skipped", "reason": "already applied"}
    else:

        path = os.path.join("migrations", last_file)

        with open(path, "r") as f:
            sql = f.read()

        statements = [
            s.strip() for s in sql.split(";")
            if s.strip()
        ]

        for stmt in statements:
            await db.execute(stmt)

        # Record migration
        await db.execute(
            "INSERT INTO migrations (version) VALUES (:v)",
            {"v": last_file}
        )

        return {"status": "ok", "applied": last_file}


@app.post("/api/logs/router")
async def router_logs(log: Log):
    await db.connect()
    await db.execute(
        """
        INSERT INTO router_logs (timestamp, thread, level, logger, message)
        VALUES (:tm, :th, :lv, :lg, :msg)
        """,
        {
            "tm": log.timestamp,
            "th": log.threadname,
            "lv": log.level,
            "lg": log.logger,
            "msg": log.message
        }
    )
    return {"status": "ok"}



