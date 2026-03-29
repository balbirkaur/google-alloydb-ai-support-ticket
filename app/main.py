import os, json, asyncio, logging
from contextlib import asynccontextmanager

from google.cloud.alloydb.connector import AsyncConnector, IPTypes
from sqlalchemy.ext.asyncio import create_async_engine
import sqlalchemy

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import google.generativeai as genai
import uvicorn

# -------------------- LOGGING --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- ENV --------------------
INSTANCE_URI   = os.environ.get("ALLOYDB_INSTANCE_URI")
DB_USER        = os.environ.get("DB_USER", "postgres")
DB_PASSWORD    = os.environ.get("DB_PASSWORD")
DB_NAME        = os.environ.get("DB_NAME", "postgres")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set")

genai.configure(api_key=GEMINI_API_KEY)
gemini = genai.GenerativeModel("gemini-3-flash-preview")

# -------------------- GLOBALS --------------------
connector = None
engine = None

# -------------------- DB CONNECTION --------------------
async def get_conn():
    # Helper for SQLAlchemy to use the AlloyDB Connector with ASYNCPG
    return await connector.connect(
        INSTANCE_URI,
        "asyncpg", 
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        ip_type=IPTypes.PUBLIC,
    )

# -------------------- LIFESPAN (STOPS NONETYPE ERROR) --------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global connector, engine
    logger.info("🚀 Starting up... connecting to AlloyDB via asyncpg")

    try:
        if not INSTANCE_URI:
            raise ValueError("ALLOYDB_INSTANCE_URI is not set!")

        connector = AsyncConnector()
        # 💡 FIX: Using postgresql+asyncpg:// protocol
        engine = create_async_engine(
            "postgresql+asyncpg://",
            async_creator=get_conn,
        )

        # 💡 THE "LOUD" TEST: Force a connection immediately.
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        
        logger.info("✅ AlloyDB connection verified!")
    except Exception as e:
        logger.error(f"❌ CRITICAL DATABASE ERROR: {e}")
        # Crashing here prevents the app from starting in a broken state
        raise e 

    yield

    if engine:
        await engine.dispose()
    if connector:
        await connector.close()

# -------------------- APP --------------------
app = FastAPI(title="AlloyDB AI App", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- MODELS --------------------
class QueryRequest(BaseModel):
    query: str

# -------------------- UTILS --------------------
async def summarise(question, rows):
    if not rows:
        return "No matching results found."
    prompt = f"User asked: '{question}'\nResults: {json.dumps(rows[:10], default=str)}\nSummary (2-3 sentences):"
    response = await asyncio.to_thread(gemini.generate_content, prompt)
    return response.text.strip()

# -------------------- ROUTES --------------------

@app.get("/")
async def root():
    return {"message": "AlloyDB AI App is live 🚀"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/search")
async def search(req: QueryRequest):
    sql = sqlalchemy.text("""
        SELECT description, issue_type, status, priority,
               1 - (embedding <=> embedding('text-embedding-004', :q)::vector) AS score
        FROM support_tickets
        ORDER BY score DESC
        LIMIT 3
    """)

    try:
        async with engine.connect() as conn:
            result = await conn.execute(sql, {"q": req.query})
            rows = [dict(r._mapping) for r in result.fetchall()]
        
        summary = await summarise(req.query, rows)
        return {"results": rows, "summary": summary}
    except Exception as e:
        logger.error(f"❌ Search Error: {e}")
        raise HTTPException(500, str(e))

# -------------------- MAIN --------------------
if __name__ == "__main__":
    # 💡 FIX: Standardize on Port 8080 for Cloud Run
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)