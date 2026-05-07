from app import create_app
from app.db.database import engine, Base
from app.db.models import Equipment, Material

Base.metadata.create_all(bind=engine)

app = create_app()
