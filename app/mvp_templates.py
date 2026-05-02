from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from app.task_runner import TaskRunnerError

MVP_TEMPLATE_REGISTRY_VERSION = "v0"


@dataclass(frozen=True, slots=True)
class MVPTemplate:
    template_id: str
    name: str
    kind: str
    description: str
    recommended_backend: str
    recommended_frontend: str
    backend_required: bool
    frontend_required: bool
    default_artifacts: list[str]
    default_task_candidates: list[dict[str, Any]]
    routing_recommendations: list[str]
    safety_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["template_version"] = MVP_TEMPLATE_REGISTRY_VERSION
        return payload


def _candidate(
    candidate_id: str,
    title: str,
    category: str,
    *,
    source: str,
    reason: str,
    execution_mode_recommendation: str = "capsule",
    capsule_recommended: bool = True,
    full_repo_required: bool = False,
    blocked: bool = False,
    priority: int = 1,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "title": title,
        "category": category,
        "source": source,
        "reason": reason,
        "execution_mode_recommendation": execution_mode_recommendation,
        "capsule_recommended": capsule_recommended,
        "full_repo_required": full_repo_required,
        "blocked": blocked,
        "priority": priority,
    }


_TEMPLATES: dict[str, MVPTemplate] = {
    "simple-web-mvp": MVPTemplate(
        template_id="simple-web-mvp",
        name="Simple Web MVP",
        kind="web",
        description="MVP web simples com separação explícita entre backend e frontend desde o primeiro corte.",
        recommended_backend="python-fastapi",
        recommended_frontend="static-html-css",
        backend_required=True,
        frontend_required=True,
        default_artifacts=[
            "docs/first-mvp-project-intake.md",
            "specs/discovery/reuse-first-first-mvp-project-intake-v0.md",
            "specs/prd/first-mvp-project-intake-v0-prd.md",
            "specs/technical-spec/first-mvp-project-intake-v0.md",
            "specs/sprints/060-first-mvp-project-intake-v0.json",
        ],
        default_task_candidates=[
            _candidate(
                "project-discovery",
                "Revisar discovery do projeto",
                "docs_only",
                source="template:simple-web-mvp",
                reason="Discovery e documentação cabem em capsule pequena.",
                priority=1,
            ),
            _candidate(
                "project-prd",
                "Fechar PRD rascunho",
                "docs_only",
                source="template:simple-web-mvp",
                reason="PRD rascunho permanece em docs_only.",
                priority=2,
            ),
            _candidate(
                "project-spec",
                "Fechar SPEC técnica rascunho",
                "docs_only",
                source="template:simple-web-mvp",
                reason="SPEC técnica rascunho permanece em docs_only.",
                priority=3,
            ),
            _candidate(
                "project-sprint-plan",
                "Planejar sprints iniciais",
                "docs_only",
                source="template:simple-web-mvp",
                reason="Sprint plan rascunho permanece em docs_only.",
                priority=4,
            ),
            _candidate(
                "project-scaffold",
                "Preparar scaffold inicial",
                "code_small",
                source="template:simple-web-mvp",
                reason="Scaffold inicial pequeno continua elegível para capsule.",
                priority=5,
            ),
        ],
        routing_recommendations=[
            "Manter as regras críticas no backend.",
            "Não colocar segredo, token ou autorização no frontend.",
            "Separar UI, experiência visual e chamadas ao backend.",
        ],
        safety_notes=[
            "Segredo nunca vai para frontend, log, docs públicos ou report compartilhado.",
            "Auth, pagamento, rate limit, quota e transições de estado ficam no backend.",
            "API paga não é permitida por padrão.",
        ],
    ),
    "landing-page-mvp": MVPTemplate(
        template_id="landing-page-mvp",
        name="Landing Page MVP",
        kind="web",
        description="Landing page orientada a conversão com uma superfície mínima de backend apenas se necessária.",
        recommended_backend="python-fastapi-optional",
        recommended_frontend="static-html-css",
        backend_required=False,
        frontend_required=True,
        default_artifacts=[
            "docs/landing-page-mvp.md",
            "specs/discovery/reuse-first-landing-page-mvp-v0.md",
            "specs/prd/landing-page-mvp-v0-prd.md",
            "specs/technical-spec/landing-page-mvp-v0.md",
            "specs/sprints/065-reusable-mvp-templates-v0.json",
        ],
        default_task_candidates=[
            _candidate(
                "landing-copy",
                "Validar copy e hierarquia visual",
                "docs_only",
                source="template:landing-page-mvp",
                reason="Landing page começa pela mensagem e pelo layout.",
                priority=1,
            ),
            _candidate(
                "landing-layout",
                "Construir scaffold visual",
                "code_small",
                source="template:landing-page-mvp",
                reason="Estrutura inicial é pequena e cabe em capsule.",
                priority=2,
            ),
            _candidate(
                "landing-cta",
                "Ajustar CTA e fluxo de captura",
                "code_small",
                source="template:landing-page-mvp",
                reason="Chamada para ação exige integração mínima e segura.",
                priority=3,
            ),
        ],
        routing_recommendations=[
            "Começar pelo frontend e copy real.",
            "Adicionar backend apenas para captura, analytics ou webhook seguro.",
            "Não colocar regra crítica no cliente.",
        ],
        safety_notes=[
            "Nenhum segredo no bundle, nos assets ou no HTML servido.",
            "Qualquer captura sensível deve ser validada no backend.",
            "Evitar APIs pagas ou integrações externas sem justificativa explícita.",
        ],
    ),
    "dashboard-saas-mvp": MVPTemplate(
        template_id="dashboard-saas-mvp",
        name="Dashboard SaaS MVP",
        kind="web",
        description="Dashboard SaaS com backend e frontend bem separados desde o scaffold inicial.",
        recommended_backend="python-fastapi-sqlite",
        recommended_frontend="react-or-static-admin",
        backend_required=True,
        frontend_required=True,
        default_artifacts=[
            "docs/dashboard-saas-mvp.md",
            "specs/discovery/reuse-first-dashboard-saas-mvp-v0.md",
            "specs/prd/dashboard-saas-mvp-v0-prd.md",
            "specs/technical-spec/dashboard-saas-mvp-v0.md",
            "specs/sprints/066-backend-frontend-scaffold-split-v0.json",
        ],
        default_task_candidates=[
            _candidate(
                "dashboard-auth",
                "Definir auth e sessão seguras",
                "security_review",
                source="template:dashboard-saas-mvp",
                reason="Auth e sessão são regra crítica do backend.",
                execution_mode_recommendation="full_repo_review",
                capsule_recommended=False,
                full_repo_required=True,
                priority=1,
            ),
            _candidate(
                "dashboard-backend",
                "Montar backend do domínio",
                "code_small",
                source="template:dashboard-saas-mvp",
                reason="Backend inicial precisa manter regras e estado no servidor.",
                priority=2,
            ),
            _candidate(
                "dashboard-frontend",
                "Montar frontend do dashboard",
                "code_small",
                source="template:dashboard-saas-mvp",
                reason="Frontend serve apenas a UI e a experiência visual.",
                priority=3,
            ),
        ],
        routing_recommendations=[
            "Separar domínio, persistência e UI desde o primeiro scaffold.",
            "Validar quota, pagamento e permissões apenas no backend.",
            "Criar o painel com foco em leitura e feedback visual.",
        ],
        safety_notes=[
            "Tokens e credenciais nunca devem entrar no frontend.",
            "Rate limit, quota e pagamento ficam no backend.",
            "Sem deploy automático e sem API paga por padrão.",
        ],
    ),
}


def get_template(template_id: str) -> MVPTemplate:
    normalized = str(template_id).strip()
    if not normalized:
        raise TaskRunnerError("template_id não pode ficar vazio.")
    try:
        return _TEMPLATES[normalized]
    except KeyError as exc:
        raise TaskRunnerError(f"template não suportado: {normalized}") from exc


def list_templates() -> list[MVPTemplate]:
    return [template for _, template in sorted(_TEMPLATES.items(), key=lambda item: item[0])]


def template_ids() -> list[str]:
    return [template.template_id for template in list_templates()]


def validate_template(template_id: str) -> dict[str, Any]:
    template = get_template(template_id)
    checks = {
        "template_id_non_empty": bool(template.template_id.strip()),
        "name_non_empty": bool(template.name.strip()),
        "kind_non_empty": bool(template.kind.strip()),
        "description_non_empty": bool(template.description.strip()),
        "recommended_backend_non_empty": bool(template.recommended_backend.strip()),
        "recommended_frontend_non_empty": bool(template.recommended_frontend.strip()),
        "default_artifacts_present": bool(template.default_artifacts),
        "default_task_candidates_present": bool(template.default_task_candidates),
        "routing_recommendations_present": bool(template.routing_recommendations),
        "safety_notes_present": bool(template.safety_notes),
        "frontend_separation_note": any(
            any(keyword in note.lower() for keyword in ("frontend", "bundle", "cliente"))
            for note in template.safety_notes + template.routing_recommendations
        ),
        "backend_separation_note": any("backend" in note.lower() for note in template.safety_notes + template.routing_recommendations),
        "critical_rule_off_frontend": any(
            any(keyword in note.lower() for keyword in ("segredo", "token", "credencial"))
            and any(keyword in note.lower() for keyword in ("frontend", "bundle", "html", "cliente"))
            for note in template.safety_notes
        ),
    }
    issues = [name for name, ok in checks.items() if not ok]
    return {
        "ok": not issues,
        "template_version": MVP_TEMPLATE_REGISTRY_VERSION,
        "template": template.to_dict(),
        "checks": checks,
        "issues": issues,
        "final_decision": "passed" if not issues else "needs_review",
    }
