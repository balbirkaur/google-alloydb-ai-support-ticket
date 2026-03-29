from sqlalchemy import text
from app.db import get_conn


def nl_to_sql(question: str):
    """
    Use LLM to convert NL → SQL (via AlloyDB AI)
    """
    with get_conn() as conn:
        # Generate SQL using AI
        result = conn.execute(text("""
            SELECT ai.generate(
                model_id => 'gemini-2.5-pro',
                prompt => 'Convert this to SQL query on support_tickets table: ' || :q
            )
        """), {"q": question})

        generated_sql = result.scalar()


        try:
            data_result = conn.execute(text(generated_sql))
            rows = [dict(r._mapping) for r in data_result]
        except Exception:
            rows = []

    return {
        "generated_sql": generated_sql,
        "data": rows
    }


def vector_search(query: str):
    """
    Semantic search using embeddings
    """
    with get_conn() as conn:
        result = conn.execute(text("""
            SELECT id, issue_type, description,
                   1 - (
                       embedding <=> embedding('text-embedding-005', :q)::vector
                   ) AS score
            FROM support_tickets
            ORDER BY score DESC
            LIMIT 5
        """), {"q": query})

        rows = [dict(r._mapping) for r in result]

    return rows