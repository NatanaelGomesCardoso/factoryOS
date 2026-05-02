import json
import re
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from typing import Any

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5-coder:3b"

HIGH_RISK_KEYWORDS = [
    "autenticação", "autenticacao", "login", "sessão", "sessao",
    "permissão", "permissao", "admin", "administrador",
    "pagamento", "checkout", "stripe", "mercado pago", "pix",
    "dado sensível", "dados sensíveis", "senha", "token", "segredo",
    "deploy", "produção", "producao", "migração", "migracao",
    "banco de dados", "database", "db/migrations", "segurança", "seguranca"
]

CODE_KEYWORDS = [
    "corrigir bug", "bug", "teste falhando", "implementar",
    "alterar código", "alterar codigo", "backend", "frontend",
    "api", "endpoint", "função", "funcao", "componente",
    "refatorar", "build", "typecheck", "lint"
]

LOCAL_ONLY_KEYWORDS = [
    "readme", "documentação", "documentacao", "checklist",
    "resumo", "organizar texto", "copy", "títulos", "titulos",
    "descrições", "descricoes", "json", "renomear arquivo"
]

@dataclass
class RouteDecision:
    decision: str
    risk: str
    reason: str
    suggested_executor: str
    needs_codex: bool
    source: str
    llm_raw: dict[str, Any] | None = None

def contains_any(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in keywords)

def deterministic_precheck(task: str) -> RouteDecision | None:
    if contains_any(task, HIGH_RISK_KEYWORDS):
        return RouteDecision(
            decision="human_review",
            risk="high",
            reason="A tarefa toca segurança, dados sensíveis, auth, pagamento, banco ou deploy.",
            suggested_executor="chatgpt_review",
            needs_codex=False,
            source="python_precheck",
        )

    return None

def call_ollama(task: str) -> dict[str, Any]:
    prompt = f"""
Você é um classificador local barato para uma fábrica de software.

Responda somente JSON válido.

Formato obrigatório:
{{
  "decision": "local_only|codex_needed|human_review",
  "risk": "low|medium|high",
  "reason": "frase curta",
  "suggested_executor": "python_template|ollama|codex_low|codex_medium|chatgpt_review",
  "needs_codex": false
}}

Regras:
- local_only: documentação, resumo, checklist, JSON, organização simples, copy/texto sem código crítico.
- codex_needed: editar código, rodar teste, corrigir bug, implementar feature pequena ou média.
- human_review: autenticação, autorização, pagamento, dado sensível, migração de banco, deploy ou segurança crítica.
- Se decision = codex_needed, needs_codex = true.
- Se decision = local_only ou human_review, needs_codex = false.

Tarefa:
{task}
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "num_predict": 180
        }
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=90) as resp:
        raw_http = resp.read().decode("utf-8")
        data = json.loads(raw_http)

    response = data.get("response", "").strip()
    if not response:
        raise ValueError("Resposta vazia do Ollama.")

    return json.loads(response)

def normalize(task: str, llm: dict[str, Any]) -> RouteDecision:
    decision = str(llm.get("decision", "")).strip()
    risk = str(llm.get("risk", "")).strip()
    reason = str(llm.get("reason", "")).strip() or "Classificação local."
    suggested_executor = str(llm.get("suggested_executor", "")).strip()

    valid_decisions = {"local_only", "codex_needed", "human_review"}
    valid_risks = {"low", "medium", "high"}

    if decision not in valid_decisions:
        decision = "human_review"
        risk = "medium"
        reason = "Resposta da LLM local veio fora do contrato."

    if risk not in valid_risks:
        risk = "medium"

    # Safety override: regra Python sempre vence para risco alto.
    if contains_any(task, HIGH_RISK_KEYWORDS):
        decision = "human_review"
        risk = "high"
        suggested_executor = "chatgpt_review"
        needs_codex = False
        reason = "Safety override: tarefa toca área crítica."
    elif decision == "codex_needed":
        needs_codex = True
        if suggested_executor not in {"codex_low", "codex_medium"}:
            suggested_executor = "codex_low" if risk == "low" else "codex_medium"
    elif decision == "local_only":
        needs_codex = False
        if suggested_executor not in {"python_template", "ollama"}:
            suggested_executor = "python_template"
    else:
        decision = "human_review"
        needs_codex = False
        risk = "high" if risk == "high" else "medium"
        suggested_executor = "chatgpt_review"

    return RouteDecision(
        decision=decision,
        risk=risk,
        reason=reason,
        suggested_executor=suggested_executor,
        needs_codex=needs_codex,
        source="ollama_normalized",
        llm_raw=llm,
    )

def route_task(task: str) -> RouteDecision:
    precheck = deterministic_precheck(task)
    if precheck:
        return precheck

    try:
        llm = call_ollama(task)
        return normalize(task, llm)
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        # Fallback seguro: se parecer código, manda para Codex; senão revisão humana se incerto.
        if contains_any(task, CODE_KEYWORDS):
            return RouteDecision(
                decision="codex_needed",
                risk="medium",
                reason=f"Fallback sem LLM local; tarefa parece envolver código. Erro: {type(exc).__name__}",
                suggested_executor="codex_medium",
                needs_codex=True,
                source="python_fallback",
            )

        return RouteDecision(
            decision="human_review",
            risk="medium",
            reason=f"Fallback seguro porque a triagem local falhou: {type(exc).__name__}",
            suggested_executor="chatgpt_review",
            needs_codex=False,
            source="python_fallback",
        )

if __name__ == "__main__":
    cases = [
        ("docs_readme", "Atualizar o README com instruções de instalação e comandos de teste. Não alterar código."),
        ("small_bugfix", "Corrigir um bug em uma função de cálculo de total no backend. Há teste falhando."),
        ("auth_security", "Implementar autenticação com login, sessão, permissão de administrador e proteção de rotas."),
        ("frontend_copy", "Melhorar textos de uma landing page, trocar títulos, CTAs e descrições. Não mexer em backend."),
    ]

    for name, task in cases:
        print(f"\n=== {name} ===")
        decision = route_task(task)
        print(json.dumps(asdict(decision), ensure_ascii=False, indent=2))
