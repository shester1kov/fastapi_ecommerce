from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger
from uuid import uuid4
from app.routers import category
from app.routers import products
from app.routers import auth
from app.routers import permission
from app.routers import review

app = FastAPI()

logger.add('info.log', format='Log: [{extra[log_id]}:{time} - {level} - {message}]', level="INFO", enqueue=True)


@app.middleware('http')
async def log_middleware(request: Request, call_next):
    log_id = str(uuid4())
    with logger.contextualize(log_id=log_id):
        try:
            response = await call_next(request)
            if response.status_code in range(401, 405):
                logger.warning(f'Request to {request.url.path} failed')
            else:
                logger.info('Successfully accessed ' + request.url.path)
        except Exception as ex:
            logger.error(f'Request to {request.url.path} failed: {ex}')
            response = JSONResponse(content={'success': False}, status_code=500)
        return response


@app.get("/")
async def welcome() -> dict:
    return {"message": "My e-commerce app"}

app.include_router(category.router)
app.include_router(products.router)
app.include_router(auth.router)
app.include_router(permission.router)
app.include_router(review.router)
