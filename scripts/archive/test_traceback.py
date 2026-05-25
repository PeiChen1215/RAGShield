import asyncio
import sys
sys.path.insert(0, '.')

from src.api.schemas import QueryRequest
from src.api.routers.query import query_detect

async def main():
    req = QueryRequest(query="公司年假有多少天？", kb_id="demo_safe", top_k=1, generate_answer=False)
    try:
        result = await query_detect(req)
        print(f"OK: {result.risk_level} score={result.final_risk_score}")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
