import os
import uuid
import json
import fitz
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 1. App Setup
app = FastAPI(title="Account Digest")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# 2. Config and Storage
load_dotenv()
DO_API_TOKEN = os.environ.get("DO_API_TOKEN")
DO_MODEL_ENDPOINT = os.environ.get("DO_MODEL_ENDPOINT")
UPLOAD_DIR = "/tmp/pdf_uploads"
PROMPTS_DIR = "prompts"
os.makedirs(UPLOAD_DIR, exist_ok=True)
job_storage = {}

# 3. Pydantic Models
class AnalyzeRequest(BaseModel):
    file_id: str
    doc_type: str

# 4. Helper Functions
def pdf_extract_text(path: str):
    doc = fitz.open(path)
    text = "".join(page.get_text() for page in doc)
    if not text.strip(): raise ValueError("Could not extract text from PDF.")
    return text

def call_digital_ocean_ai(prompt: str):
    if not DO_API_TOKEN or not DO_MODEL_ENDPOINT:
        raise Exception("DigitalOcean credentials are not set in the .env file.")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DO_API_TOKEN}"
    }
    
    # This payload structure matches the DigitalOcean documentation
    payload = {
        "model": "n/a",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    print("--- Calling DigitalOcean AI Endpoint ---")
    response = requests.post(DO_MODEL_ENDPOINT, headers=headers, json=payload)
    
    if response.status_code != 200:
        raise Exception(f"API request failed with status {response.status_code}: {response.text}")
        
    response_data = response.json()
    generated_text = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return generated_text

def run_analysis_task(job_id: str, file_path: str, doc_type: str):
    try:
        job_storage[job_id] = {"status": "processing", "step": "extracting_text"}
        text = pdf_extract_text(file_path)
        prompt_path = os.path.join(PROMPTS_DIR, f"{doc_type}_summary.md")
        with open(prompt_path) as f:
            prompt_template = f.read()
        final_prompt = f"{prompt_template}\n\n--- DOCUMENT TEXT ---\n\n{text}"
        job_storage[job_id]["step"] = "generating_summary"
        summary = call_digital_ocean_ai(final_prompt)
        result = {"summary_md": summary, "risks": []}
        job_storage[job_id] = {"status": "complete", "result": result}
    except Exception as e:
        job_storage[job_id] = {"status": "failed", "error": str(e)}

# 5. API Endpoints
@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    return {"file_id": file_id}

@app.post("/api/analyze")
async def analyze_document(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    file_path = os.path.join(UPLOAD_DIR, f"{request.file_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    job_id = request.file_id
    job_storage[job_id] = {"status": "pending"}
    background_tasks.add_task(run_analysis_task, job_id, file_path, request.doc_type)
    return {"job_id": job_id}

@app.get("/api/result/{job_id}")
def get_result(job_id: str):
    job = job_storage.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job

# 6. Static Files
app.mount("/", StaticFiles(directory="web", html=True), name="web")
