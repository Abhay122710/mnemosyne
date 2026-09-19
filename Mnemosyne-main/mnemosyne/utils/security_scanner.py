import os
import re
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from mnemosyne.memory.client import MemoryClient
from mnemosyne.memory.schemas import MemoryRecord, MemoryType

class SecurityIssue(BaseModel):
    file_path: str
    line_number: Optional[int] = None
    severity: str = "medium"  # low, medium, high, critical
    vulnerability_type: str
    description: str
    proposed_fix: str
    matching_memory_id: Optional[str] = None

class SecurityScanner:
    def __init__(self, client: MemoryClient):
        self.client = client

    def scan_file(self, file_path: Path) -> List[SecurityIssue]:
        """Scan a file for security vulnerabilities using local heuristics and optional LLM analysis."""
        if not file_path.exists():
            return []
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        # Run heuristic scanning first
        issues = self._run_heuristic_scan(content, str(file_path))

        # Fetch security-related memories and rules
        security_memories = self._fetch_security_memories(content, str(file_path))

        # Run LLM scanning if LLM/Cognee is configured and not offline
        if os.getenv("MNEMOSYNE_OFFLINE") != "1" and self._is_llm_available():
            llm_issues = self._run_llm_scan(content, str(file_path), security_memories)
            issues.extend(llm_issues)

        # Merge matching memory links based on content overlaps if not already linked
        for issue in issues:
            if not issue.matching_memory_id and security_memories:
                # Link to the most relevant security memory
                issue.matching_memory_id = security_memories[0].id

        return issues

    def scan_diff(self, diff_text: str) -> List[SecurityIssue]:
        """Scan a git diff for security vulnerabilities."""
        if not diff_text.strip():
            return []

        issues = self._run_heuristic_scan(diff_text, "staged changes")

        security_memories = self._fetch_security_memories(diff_text, "staged changes")

        if os.getenv("MNEMOSYNE_OFFLINE") != "1" and self._is_llm_available():
            llm_issues = self._run_llm_scan(diff_text, "staged changes", security_memories)
            issues.extend(llm_issues)

        for issue in issues:
            if not issue.matching_memory_id and security_memories:
                issue.matching_memory_id = security_memories[0].id

        return issues

    def _fetch_security_memories(self, content: str, context: str) -> List[MemoryRecord]:
        """Query memory client for security-related bug fixes or rules."""
        # 1. Gather all memories that have security keywords/tags
        security_keywords = {"security", "vulnerability", "leak", "secret", "password", "key", "auth", "token", "injection", "cryptography", "sanitize"}
        all_bugs = self.client.list_memories(MemoryType.BUG_FIX)
        all_rules = self.client.get_rules()

        matched_memories = []

        # Filter local bugs
        for bug in all_bugs:
            bug_text = (bug.title + " " + bug.content).lower()
            tags = [t.lower() for t in bug.metadata.get("tags", [])]
            if any(kw in bug_text or kw in tags for kw in security_keywords):
                matched_memories.append(bug)

        # Filter local rules
        for rule in all_rules:
            meta = rule.metadata or {}
            rule_title = meta.get("rule_title", rule.title)
            description = meta.get("description", rule.content)
            domain = meta.get("domain", "general")

            rule_text = (rule_title + " " + description + " " + domain).lower()
            if any(kw in rule_text for kw in security_keywords):
                # Convert to MemoryRecord structure
                matched_memories.append(MemoryRecord(
                    id=rule.id,
                    memory_type=MemoryType.RULE,
                    title=rule_title,
                    content=description,
                    metadata={"domain": domain}
                ))

        return matched_memories[:5]

    def _run_heuristic_scan(self, content: str, file_path: str) -> List[SecurityIssue]:
        """Local static heuristics to detect common vulnerabilities offline."""
        issues: List[SecurityIssue] = []
        lines = content.splitlines()

        # 1. Regex for hardcoded secrets / API keys
        # Look for patterns like api_key = "abc", password = "xyz" but ignore short dummy values
        secret_patterns = [
            (re.compile(r'(?i)\b\w*(api[_-]?key|secret|password|passwd|token|auth[_-]?key)\w*\s*[:=]\s*["\']([a-zA-Z0-9_\-\.]{12,})["\']'), "Hardcoded Secret / API Key"),
            (re.compile(r'(?i)\b\w*(aws[_-]?key|client[_-]?secret|private[_-]?key|ssh[_-]?key)\w*\s*[:=]\s*["\']([^"\']+)["\']'), "Sensitive Credentials / Key"),
        ]

        # 2. Regex for SQL Injection Risk
        sql_injection_pattern = re.compile(r'(?i)\b(SELECT|INSERT|UPDATE|DELETE)\b.*(\{.*\}|%.+|format\()')

        # 3. Dangerous functions
        dangerous_functions = [
            (re.compile(r'\beval\('), "eval() Execution", "Avoid using eval() as it allows arbitrary code execution. Use safe JSON parsers or literal evaluation instead."),
            (re.compile(r'\bexec\('), "exec() Execution", "Avoid using exec() as it allows arbitrary code execution."),
            (re.compile(r'subprocess\.(Popen|run|call)\(.*shell\s*=\s*True'), "subprocess with shell=True", "Using shell=True with subprocess can lead to shell injection vulnerabilities. Pass arguments as a list and set shell=False."),
        ]

        # 4. Insecure Protocols
        insecure_protocol_pattern = re.compile(r'["\']http://[a-zA-Z0-9_\-\.]')

        for idx, line in enumerate(lines):
            line_num = idx + 1

            # Check secrets
            for pattern, vuln_type in secret_patterns:
                match = pattern.search(line)
                if match:
                    # Ignore common fake/template placeholder strings
                    val = match.group(2).lower()
                    if not any(placeholder in val for placeholder in ["placeholder", "example", "template", "test_key", "dummy"]):
                        issues.append(SecurityIssue(
                            file_path=file_path,
                            line_number=line_num,
                            severity="high",
                            vulnerability_type=vuln_type,
                            description=f"Detected a potential hardcoded credential assignment on line {line_num}.",
                            proposed_fix="Move the credential to environment variables (.env) or a secure secret store (e.g. AWS Secrets Manager)."
                        ))

            # Check SQL Injection
            if sql_injection_pattern.search(line):
                issues.append(SecurityIssue(
                    file_path=file_path,
                    line_number=line_num,
                    severity="critical",
                    vulnerability_type="SQL Injection Risk",
                    description=f"Raw SQL query string interpolation detected on line {line_num}.",
                    proposed_fix="Use parameterized queries / prepared statements (e.g., execute('SELECT * FROM users WHERE id = %s', (user_id,))) to neutralize SQL injection."
                ))

            # Check dangerous functions
            for pattern, vuln_type, fix in dangerous_functions:
                if pattern.search(line):
                    issues.append(SecurityIssue(
                        file_path=file_path,
                        line_number=line_num,
                        severity="high",
                        vulnerability_type=vuln_type,
                        description=f"Detected dangerous execution function call on line {line_num}.",
                        proposed_fix=fix
                    ))

            # Check insecure protocols
            if insecure_protocol_pattern.search(line):
                # Ignore localhost
                if "localhost" not in line and "127.0.0.1" not in line:
                    issues.append(SecurityIssue(
                        file_path=file_path,
                        line_number=line_num,
                        severity="medium",
                        vulnerability_type="Insecure Protocol (HTTP)",
                        description=f"Detected insecure http:// protocol on line {line_num}.",
                        proposed_fix="Use secure https:// protocol to encrypt communications in transit."
                    ))

        return issues

    def _is_llm_available(self) -> bool:
        """Check if LLM keys are configured."""
        return bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))

    def _run_llm_scan(self, content: str, file_path: str, memories: List[MemoryRecord]) -> List[SecurityIssue]:
        """Perform LLM security analysis using past security memories as context."""
        try:
            import openai
            from mnemosyne.config import configure_llm_env
            configure_llm_env()

            model = os.getenv("MNEMOSYNE_LLM_MODEL", "gpt-4o-mini")
            client = openai.OpenAI()

            # Compile reference memory context
            memory_context = ""
            if memories:
                memory_context = "Past security issues and rules in this codebase:\n"
                for idx, mem in enumerate(memories):
                    memory_context += f"Memory #{idx+1} ({mem.id}): {mem.title}\n{mem.content}\n\n"

            prompt = (
                f"You are the Mnemosyne Security Agent. Scan the following code/diff for security vulnerabilities.\n"
                f"Use the past memory context to check if this code makes the same mistakes as before.\n\n"
                f"--- Scanned Context ({file_path}) ---\n"
                f"{content[:4000]}\n\n"
                f"--- Reference Memory Context ---\n"
                f"{memory_context}\n"
                f"Evaluate issues carefully. Return a JSON object with a single key 'issues' containing a list of objects. "
                f"Each object must have: line_number (integer or null), severity (critical, high, medium, low), "
                f"vulnerability_type (string), description (string), proposed_fix (string), matching_memory_id (string or null matching the Reference Memory ID if related).\n\n"
                f"Format output as strict JSON: {{\"issues\": [...]}}"
            )

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a software security scanner. Always respond in valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            data = json.loads(response.choices[0].message.content)
            issues = []
            for item in data.get("issues", []):
                # Ensure correct keys and defaults
                issues.append(SecurityIssue(
                    file_path=file_path,
                    line_number=item.get("line_number"),
                    severity=item.get("severity", "medium"),
                    vulnerability_type=item.get("vulnerability_type", "Vulnerability"),
                    description=item.get("description", ""),
                    proposed_fix=item.get("proposed_fix", ""),
                    matching_memory_id=item.get("matching_memory_id")
                ))
            return issues
        except Exception:
            return []
