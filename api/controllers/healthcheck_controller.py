from api.routes import api_v1_router


@api_v1_router.get("/healthcheck")
async def healthcheck():
    return {"status": "ok"}
