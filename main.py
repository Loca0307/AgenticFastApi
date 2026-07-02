from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import database_models
from routes.agent import router as agent_router
from routes.items import router as items_router

app = FastAPI(title="fast api test project")

# to actually create the tables in the database based on the databse_models
database_models.Base.metadata.create_all(bind=engine)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items_router)
app.include_router(agent_router)
    
