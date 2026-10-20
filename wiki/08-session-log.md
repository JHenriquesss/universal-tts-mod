# Session Log

O ledger de evidência do projeto. Cada sessão registra o que foi feito, com a
evidência de testes de cada passo, para que o histórico não dependa da memória
de quem executou.

## Onde vive o estado

| Peça | Papel |
|---|---|
| `sessions/YYYY-MM-DD.md` | Registroappend-only das sessões, uma por dia. |
| `.dv-state.json` | Máquina de fases: fase atual, `trunk_status`, `trunk_evidence` e histórico de fases fechadas. |
| `wiki/03-phases.md` | Resultado de cada fase encerrada, em prosa. |
| `wiki/06-open-threads.md` | Pendências abertas e o que foi resolvido. |

O log de sessão **não** é lixo de histórico: o campo `tests` de cada entrada é a
evidência do ciclo obrigatório de `GEMINI.md` 1.3 ("NÃO DEVE integrar commit que
quebre o pipeline"). Apagá-lo remove a trilha de auditoria do workflow.

## Schema de uma entrada

Um arquivo por dia, com uma entrada por trabalho:

```markdown
# Session 2026-10-19

## 21:31 — Unity plugin build made reproducible
- **phase:** n/a
- **type:** green-code
- **files:** unity_mod/src/KokoroTtsPlugin.csproj, global.json
- **tests:** red:1 green:4 trunk:pass
- **summary:** O que mudou e por que.
- **friction:** O que atrapalhou, e como foi resolvido.
- **next:** O que vem a seguir.
```

| Campo | Conteúdo |
|---|---|
| `## HH:MM — título` | Horário local e um resumo curto do trabalho. |
| `phase` | Fase do `.dv-state.json` em que o trabalho caiu, ou `n/a`. |
| `type` | Natureza da mudança: `green-code`, `refactor`, `analysis`, `fix`, `docs`. |
| `files` | Arquivos tocados, separados por vírgula. |
| `tests` | `red:N` testes vermelhos escritos antes, `green:N` testes verdes depois, `trunk:pass` para a suíte completa. |
| `summary` | O que mudou e por quê, em prosa. |
| `friction` | O que atrapalhou. `none` quando não atrapalhou. |
| `next` | O passo seguinte. |

## Regras

- **Uma entrada por trabalho**, não por commit. Vários commits relacionados
  cabem numa entrada só.
- **`tests` é obrigatório.** Uma entrada sem evidência de testes não registra
  trabalho, registra impressão.
- **`friction` registra o atrito real**, inclusive o atrito com as próprias
  ferramentas. É a parte que mais serve a quem vai retomar o trabalho.
- **O log é append-only.** Entradas antigas não são reescritas; o que mudou de
  entendimento fica em uma entrada nova.
- **A fase só é registrada quando existe.** `n/a` é a resposta correta para
  trabalho que não pertence a uma fase da máquina de fases.

## Cross-Refs

- Arquitetura: [[01-architecture.md#architecture]]
- Árvore de testes: [[02-test-tree.md#test-tree]]
- Fases: [[03-phases.md#phases]]
- Decisões: [[04-decisions.md#decisions]]
- Threads abertas: [[06-open-threads.md#open-threads]]
