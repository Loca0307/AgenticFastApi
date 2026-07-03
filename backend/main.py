from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.agent import router as agent_router
from routes.feedback_agent import router as feedback_agent_router
from routes.items import router as items_router

from mangum import Mangum



load_dotenv()

app = FastAPI(title="fast api test project")

# SQLite setup is intentionally inactive while DynamoDB is the active datastore.
# To reactivate SQLite locally, import database_models/engine and call create_all().


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items_router)
app.include_router(agent_router)
app.include_router(feedback_agent_router)
    

handler = Mangum(app, lifespan="off")
