from fastapi import FastAPI
from pydantic import BaseModel
import os
from sqlalchemy import create_engine, text

app = FastAPI()

# ✅ Load env
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")


# ✅ Request model
class QueryRequest(BaseModel):
    query: str


# ✅ Lazy DB connection (IMPORTANT FIX)
def get_engine():
    return create_engine(DATABASE_URL)


# ✅ Root endpoint
@app.get("/")
def root():
    return {"message": "AlloyDB AI App is running 🚀"}


# ✅ Health check
@app.get("/health")
def health():
    return {"status": "ok"}


# ✅ Vector search API
@app.post("/search")
def search(req: QueryRequest):
    print("🔹 Incoming query:", req.query)

    sql = text("""
        SELECT description,
               1 - (embedding <=> embedding('text-embedding-005', :q)::vector) AS score
        FROM support_tickets
        ORDER BY score DESC
        LIMIT 3
    """)

    try:
        engine = get_engine()  # 👈 created at runtime

        with engine.connect() as conn:
            print("✅ Connected to DB")

            result = conn.execute(sql, {"q": req.query})
            rows = [dict(r._mapping) for r in result]

            print("✅ Results:", rows)

        return {"results": rows}

    except Exception as e:
        print("❌ ERROR:", str(e))
        return {"error": str(e)}