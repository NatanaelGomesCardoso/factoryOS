from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re


@dataclass
class ReuseFirstDiscovery:
    idea: str
    created_at: str

    def to_markdown(self) -> str:
        return f"""# Reuse First Discovery

## Ideia

{self.idea}

## Criado em

{self.created_at}

## Objetivo desta etapa

Antes de criar arquitetura, PRD, SPEC, Sprint JSON ou prompt para Codex, o ChatGPT deve pesquisar soluções maduras existentes para evitar reinventar a roda.

## Responsabilidade

- ChatGPT: pesquisar, comparar, decidir e gerar a recomendação.
- FactoryOS: registrar o discovery e organizar o fluxo.
- Codex: não deve fazer pesquisa ampla; deve executar somente depois da decisão.

## O que pesquisar

- bibliotecas maduras;
- frameworks;
- SDKs;
- templates;
- ferramentas open source;
- projetos/repositórios validados;
- plugins/extensões;
- padrões consolidados.

## Critérios de avaliação

Para cada opção encontrada, avaliar:

- maturidade;
- licença;
- manutenção;
- segurança;
- custo;
- dependência de API paga;
- simplicidade;
- compatibilidade com WSL/local;
- integração com Codex/harness;
- esforço de adaptação.

## Tabela de análise

| Opção | Tipo | Licença | Maturidade | Custo | Risco | Decisão |
|---|---|---|---|---|---|---|
| A preencher pelo ChatGPT |  |  |  |  |  |  |

## Decisão final

Escolher uma opção:

- [ ] usar pronto;
- [ ] adaptar;
- [ ] usar como referência;
- [ ] criar pequeno customizado;
- [ ] adiar.

## Justificativa

A preencher pelo ChatGPT.

## Impacto no PRD/SPEC

A preencher pelo ChatGPT.

## Próximo passo

Depois deste discovery preenchido, gerar:

1. PRD;
2. SPEC;
3. Sprint JSON;
4. prompt fechado para Codex, se necessário.
"""


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9áàâãéèêíïóôõöúçñ\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = text.replace("ç", "c")
    text = text.replace("ã", "a").replace("á", "a").replace("à", "a").replace("â", "a")
    text = text.replace("é", "e").replace("ê", "e")
    text = text.replace("í", "i")
    text = text.replace("ó", "o").replace("ô", "o").replace("õ", "o")
    text = text.replace("ú", "u")
    text = re.sub(r"-+", "-", text)
    return text[:80].strip("-") or "reuse-first-discovery"


def build_discovery(idea: str) -> ReuseFirstDiscovery:
    return ReuseFirstDiscovery(
        idea=idea.strip(),
        created_at=datetime.now().isoformat(timespec="seconds"),
    )


def default_discovery_path(idea: str) -> Path:
    return Path("specs/discovery") / f"{slugify(idea)}.md"


def write_discovery(idea: str, out: str | None = None) -> Path:
    discovery = build_discovery(idea)
    out_path = Path(out) if out else default_discovery_path(idea)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(discovery.to_markdown(), encoding="utf-8")
    return out_path
