import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to sys.path so we can import from mnemosyne package
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from mnemosyne.memory.client import MemoryClient
from mnemosyne.memory.schemas import BugFixMemory, MemoryType
from mnemosyne.memory.consolidator import MemoryConsolidator
from mnemosyne.utils.security_scanner import SecurityScanner

app = FastAPI(title="Mnemosyne Web API", version="0.1.0")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper to get client instance
def get_client() -> MemoryClient:
    return MemoryClient(root_dir)

class BugInput(BaseModel):
    file_path: str
    title: str
    root_cause: str
    fix_description: str
    severity: str = "medium"
    tags: List[str] = []

class RecallInput(BaseModel):
    query: str
    file_context: Optional[str] = None
    top_k: int = 5

class SecurityInput(BaseModel):
    file_path: Optional[str] = None
    diff_text: Optional[str] = None

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "version": "0.1.0"}

@app.get("/api/status")
def get_status():
    try:
        client = get_client()
        memories = client.list_memories()
        bugs = [m for m in memories if m.memory_type == MemoryType.BUG_FIX]
        commits = [m for m in memories if m.memory_type == MemoryType.COMMIT]
        rules = client.get_rules()
        
        # Check if Ollama or OpenAI is configured
        llm_active = bool(os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"))
        offline_mode = os.getenv("MNEMOSYNE_OFFLINE") == "1"
        
        return {
            "total_memories": len(memories),
            "bug_fixes": len(bugs),
            "rule_nodes": len(rules),
            "commit_memories": len(commits),
            "cognee_active": client._init_cognee_if_needed(),
            "llm_active": llm_active and not offline_mode,
            "offline_mode": offline_mode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/remember-bug")
def remember_bug(data: BugInput):
    try:
        client = get_client()
        bug = BugFixMemory(
            file_path=data.file_path,
            title=data.title,
            root_cause=data.root_cause,
            fix_description=data.fix_description,
            severity=data.severity,
            tags=data.tags
        )
        rec = client.remember_bug(bug)
        return {"status": "success", "id": rec.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recall")
def recall_memory(data: RecallInput):
    try:
        client = get_client()
        records = client.recall(
            query=data.query,
            file_context=data.file_context,
            top_k=data.top_k
        )
        return {"query": data.query, "results": [r.model_dump() for r in records]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reflect")
def reflect_rules():
    try:
        client = get_client()
        consolidator = MemoryConsolidator(client)
        rules = consolidator.reflect()
        return {"status": "success", "new_rules_count": len(rules)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rules")
def get_rules():
    try:
        client = get_client()
        rules = client.get_rules()
        return {"rules": [r.model_dump() for r in rules]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scan-security")
def scan_security(data: SecurityInput):
    try:
        client = get_client()
        scanner = SecurityScanner(client)
        
        if data.file_path:
            file_path = root_dir / data.file_path
            if not file_path.exists():
                raise HTTPException(status_code=400, detail=f"File {data.file_path} not found")
            issues = scanner.scan_file(file_path)
        elif data.diff_text:
            issues = scanner.scan_diff(data.diff_text)
        else:
            raise HTTPException(status_code=400, detail="Must provide either file_path or diff_text")
            
        return {"issues": [i.model_dump() for i in issues]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/graph-data")
def get_graph_data():
    try:
        client = get_client()
        memories = client.list_memories()
        rules = client.get_rules()
        
        nodes: List[Dict[str, Any]] = []
        links: List[Dict[str, Any]] = []
        seen_nodes = set()
        
        # Add root tenant node
        nodes.append({"id": "tenant_root", "label": "Mnemosyne Memory", "type": "tenant"})
        seen_nodes.add("tenant_root")
        
        # Track file nodes to prevent duplicate file nodes and link them
        file_nodes = set()
        
        for mem in memories:
            if mem.file_path:
                file_id = f"file_{mem.file_path}"
                if file_id not in seen_nodes:
                    nodes.append({
                        "id": file_id,
                        "label": mem.file_path,
                        "type": "file",
                        "details": {"Path": mem.file_path}
                    })
                    seen_nodes.add(file_id)
                    # Link file to tenant root
                    links.append({"source": "tenant_root", "target": file_id, "relation": "CONTAINS"})
                file_nodes.add(file_id)

            # Add memory node
            node_id = mem.id
            if node_id not in seen_nodes:
                details = {
                    "Type": mem.memory_type.value,
                    "Title": mem.title,
                    "Timestamp": mem.timestamp
                }
                if mem.memory_type == MemoryType.BUG_FIX:
                    details["Root Cause"] = mem.metadata.get("root_cause", "")
                    details["Fix Description"] = mem.metadata.get("fix_description", "")
                    details["Severity"] = mem.metadata.get("severity", "medium")
                
                nodes.append({
                    "id": node_id,
                    "label": mem.title,
                    "type": mem.memory_type.value,
                    "details": details
                })
                seen_nodes.add(node_id)
                
                # Link memory node to its file
                if mem.file_path:
                    links.append({"source": f"file_{mem.file_path}", "target": node_id, "relation": "AFFECTS"})
                else:
                    links.append({"source": "tenant_root", "target": node_id, "relation": "CONTAINS"})

        for rule in rules:
            rule_id = rule.id or f"rule_{hash(rule.rule_title)}"
            if rule_id not in seen_nodes:
                nodes.append({
                    "id": rule_id,
                    "label": rule.rule_title,
                    "type": "rule",
                    "details": {
                        "Rule": rule.description,
                        "Domain": rule.domain,
                        "Confidence": f"{rule.confidence * 100:.1f}%"
                    }
                })
                seen_nodes.add(rule_id)
                
                # Link rules to their source bug memories (provenance)
                for bug_id in rule.origin_memory_ids:
                    if bug_id in seen_nodes:
                        links.append({"source": bug_id, "target": rule_id, "relation": "GENERALIZES_TO"})
                        
                # Link rules to files where it applies
                for f_path in rule.provenance_files:
                    f_id = f"file_{f_path}"
                    if f_id in seen_nodes:
                        links.append({"source": rule_id, "target": f_id, "relation": "APPLIES_TO"})
                        
                if not rule.origin_memory_ids and not rule.provenance_files:
                    links.append({"source": "tenant_root", "target": rule_id, "relation": "CONTAINS"})

        return {"nodes": nodes, "links": links}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import HTMLResponse
from fastapi import Response
from api.static_assets import HTML_CONTENT, CSS_CONTENT, JS_CONTENT

@app.get("/", response_class=HTMLResponse)
def get_index():
    try:
        public_index = root_dir / "public" / "index.html"
        if public_index.exists():
            return HTMLResponse(content=public_index.read_text(encoding="utf-8"))
    except Exception:
        pass
    return HTMLResponse(content=HTML_CONTENT)

@app.get("/style.css")
def get_css():
    try:
        public_css = root_dir / "public" / "style.css"
        if public_css.exists():
            return Response(content=public_css.read_text(encoding="utf-8"), media_type="text/css")
    except Exception:
        pass
    return Response(content=CSS_CONTENT, media_type="text/css")

@app.get("/app.js")
def get_js():
    try:
        public_js = root_dir / "public" / "app.js"
        if public_js.exists():
            return Response(content=public_js.read_text(encoding="utf-8"), media_type="application/javascript")
    except Exception:
        pass
    return Response(content=JS_CONTENT, media_type="application/javascript")

