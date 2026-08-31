from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import create_database
from fastapi import UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import SessionLocal
from .ingestion import import_csv
from .routes import router

app = FastAPI(
    title="Intain Loan Data Verification Copilot",
    description="A traceable loan-data verification and review platform.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup():
    create_database()


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Intain Loan Data Verification Copilot",
    }
@app.post("/import")
async def upload_loan_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected."
        )

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported."
        )

    try:
        content = await file.read()

        result = import_csv(
            db=db,
            filename=file.filename,
            file_content=content,
        )

        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:
        import traceback

        db.rollback()

        print("\n========== IMPORT ERROR ==========")
        print(f"ERROR: {error}")
        traceback.print_exc()
        print("==================================\n")

        raise HTTPException(
            status_code=500,
            detail=f"Import failed: {str(error)}"
        )