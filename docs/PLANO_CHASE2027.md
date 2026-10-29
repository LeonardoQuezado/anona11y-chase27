# Melodie A11Y — Estado do Projeto e Plano para o CHASE 2027

> Documento de trabalho para escrever o artigo antes de os dados da bateria de reparo existirem.
> Tudo marcado **[DADO PENDENTE]** só pode ser escrito depois da bateria no laboratório.
> Fonte dos números do piloto: `results/CORRECTION_LOG.md`. Fonte dos números de detecção: artigo WebMedia 2026 (`article/`).

**Atualizado em:** 19/10/2026
**Autores previstos:** Leonardo Quezado, Windson Viana, François (HEC / Tech3Lab, Axis 2) — confirmação e ORCID pendentes
**Alvo:** CHASE 2027, extended abstract (5 páginas contando referências)

---

## Sumário

1. [Resumo executivo](#1-resumo-executivo)
2. [O que é a Melodie](#2-o-que-é-a-melodie)
3. [O que já foi publicado (WebMedia 2026)](#3-o-que-já-foi-publicado-webmedia-2026)
4. [O módulo de reparo](#4-o-módulo-de-reparo)
5. [Resultados do piloto de reparo](#5-resultados-do-piloto-de-reparo)
6. [Contribuição nova em relação ao WebMedia](#6-contribuição-nova-em-relação-ao-webmedia)
7. [O ângulo humano (por que o CHASE)](#7-o-ângulo-humano-por-que-o-chase)
8. [Plano experimental da bateria de reparo](#8-plano-experimental-da-bateria-de-reparo)
9. [Pré-requisitos técnicos antes da bateria](#9-pré-requisitos-técnicos-antes-da-bateria)
10. [Ameaças à validade](#10-ameaças-à-validade)
11. [Estrutura do artigo](#11-estrutura-do-artigo)
12. [Resumo submetido (versão genérica)](#12-resumo-submetido-versão-genérica)
13. [Logística de submissão](#13-logística-de-submissão)
14. [Plano B e venues alternativas](#14-plano-b-e-venues-alternativas)
15. [Cronograma](#15-cronograma)
16. [Decisões em aberto](#16-decisões-em-aberto)

---

## 1. Resumo executivo

- **Detecção:** pronta e publicada (WebMedia 2026, candidato a best paper). 48 execuções, 3 LLMs, 100% de compilação, 409 ocorrências.
- **Reparo:** código completo (`src/corrector.py`, `src/reanalyse.py`). Piloto em 1 tela com 4 rodadas e 4 versões de prompt. A versão v5 do prompt (`clearAndSetSemantics`) foi executada em 20/10/2026 e **zerou ATF, Lint e Static** no piloto (verificações pendentes no `CORRECTION_LOG.md`).
- **Achado principal do piloto:** regressão cruzada entre análise estática (Lint) e dinâmica (ATF). Corrigir para um checador piorou o outro.
- **Estado atual:** laboratório de volta; token do Tech3Lab regenerado. Próximo passo: bateria de 30 telas (10 tipos × 3 geradores).
- **O que decide entre CHASE e ICSME:** a execução da v5 e da bateria ampla.

---

## 2. O que é a Melodie

Pipeline automatizado que avalia, e agora também repara, a acessibilidade de telas Android em Jetpack Compose geradas por LLMs, com intervenção humana mínima.

### 2.1 Estágios

| # | Estágio | Implementação | Arquivo |
|---|---------|---------------|---------|
| 1 | Base de prompts e orquestração | Prompt de tela + sufixo fixo de restrições; zero-shot ou few-shot; N execuções (`N_RUNS`, 1–10) | `src/pipeline.py`, `prompts/` |
| 2 | Geração | Clientes de API para vários provedores, mais Ollama local | `src/llm_client.py` |
| 3 | Extração e correção de compilação | Extração do código + 55 regras determinísticas de compatibilidade; *self-repair* opcional de erros de compilação (`SELF_REPAIR`, até 2 tentativas) | `src/code_extractor.py`, `src/pipeline.py` |
| 4 | Compilação | Template Android (`com.accessibility.test`), Gradle `assembleDebug`, Docker headless | `dockerfile`, `src/pipeline.py` |
| 5a | Análise estática | Android Lint + regras customizadas + scanner Compose próprio (6 checks) | `src/compose_a11y_scanner.py` |
| 5b | Análise dinâmica | ATF em dispositivo físico via ADB Wi-Fi, modo claro e escuro, com rolagem | `src/pipeline.py` |
| 6 | Relatório | JSON + HTML comparativo | `src/report_generator.py` |
| 7 | **Reparo de acessibilidade (novo)** | Violações → prompt de reparo → Qwen3-Coder (Tech3Lab) → `*_corrected.kt` | `src/corrector.py` |
| 8 | **Reanálise (novo)** | Build + Lint + ATF no código reparado | `src/reanalyse.py` |

### 2.2 Checks de acessibilidade

**Estáticos** (scanner Compose, `src/compose_a11y_scanner.py`):

| Check | O que detecta |
|-------|---------------|
| `ComposeImageContentDescription` | `Image()` sem `contentDescription` |
| `ComposeImageNullContentDescription` | `Image()` com `contentDescription = null` |
| `ComposeIconContentDescription` | `Icon()` sem `contentDescription` |
| `ComposeIconNullContentDescription` | `Icon()` com `contentDescription = null` |
| `ComposeTextFieldMissingLabel` | `TextField`/`OutlinedTextField` sem `label` |
| `ComposeIconButtonMissingLabel` | `IconButton` cujo `Icon` filho tem descrição nula |

> No WebMedia só foram reportadas duas regras customizadas (IN e TF). O scanner atual tem 6 checks. Se a bateria usar os 6, isso precisa estar explícito no artigo, porque muda a comparabilidade com os 45 achados de Lint do WebMedia.

**Dinâmicos** (ATF): `SpeakableTextPresentCheck` (ST), `TouchTargetSizeCheck` (TT), `TextContrastCheck` (CT).

### 2.3 Interface web

Aplicação FastAPI com SPA própria (`src/web_server.py`, `templates/`, `src/static/js/router.js`). Páginas: Análise, Correção, Fix em lote, Scan, Relatórios, Documentação, Dashboard e Log. Endpoints de reparo: `/api/correct` (usa `corrector.py`) e `/api/correct-general` (prompt simplificado, ver seção 9).

> A interface **não é contribuição do artigo**. Fica congelada até a submissão.

### 2.4 Testes automatizados

151 casos em `tests/test_pipeline_fixes.py` e `tests/test_compose_scanner.py`, cobrindo as regras de compatibilidade e o scanner. Rodam sem dependências pesadas (clientes LLM com *stubs*).

---

## 3. O que já foi publicado (WebMedia 2026)

**Título:** *Pipeline Automatizado para Avaliação de Acessibilidade de Interfaces Android Geradas por LLMs* (Quezado, Viana). Candidato a best paper.

### 3.1 Perguntas de pesquisa

- **RQ1:** eficácia do pipeline em compilar Compose sem intervenção manual.
- **RQ2:** diferenças entre Claude, ChatGPT e Gemini na acessibilidade gerada.
- **RQ3:** correspondência com avaliação manual (TalkBack e Accessibility Scanner).

### 3.2 Desenho

- 8 tipos de tela: Login, Configurações, Dashboard, Chat, Galeria, Music Player, E-Commerce, Social Feed.
- 3 LLMs: Claude Sonnet 4.6, ChatGPT 5.5, Gemini 3.1 Pro.
- Zero-shot, temperatura 1,0, *self-repair* desligado.
- 48 execuções (8 telas × 3 modelos × 2 modos visuais), dispositivo físico Android 16, maio de 2026.
- Média de 5,8 min por execução (mín. 5,2, máx. 7,2), 4,6 h no total.

### 3.3 Resultados

| Métrica | Valor |
|---------|-------|
| Compilação | 48/48 (100%) |
| Lint nativo | 0 |
| Lint customizado | 45 (31 TF + 14 IN) |
| ATF | 364 (327 ST + 12 TT + 25 CT) |
| **Total** | **409** |
| Por modelo | Claude 156 · Gemini 130 · ChatGPT 123 |
| Validação sintética | Lint bateu com o *ground truth* nas 3 telas; ATF achou 4 extras na Galeria (`Modifier.size` quebrando a propagação) |

### 3.4 Limitações declaradas no WebMedia

Execução única por configuração; validação manual restrita a um modelo; contagens brutas; preservação semântica das regras de compilação não verificada.

### 3.5 Trabalho futuro declarado no WebMedia

"Estudar a estabilidade dos modelos com mais repetições" e "**a capacidade de correção de problemas de acessibilidade**". O CHASE é a continuação direta desse segundo item.

### 3.6 Atenção: "autocorreção" no WebMedia ≠ reparo de acessibilidade

O WebMedia já usa os termos "autocorreção" e "self-repair", mas **apenas para erros de compilação**. O artigo novo precisa deixar isso explícito na introdução. Caso contrário, um revisor pode entender que o reparo já foi publicado.

---

## 4. O módulo de reparo

### 4.1 Fluxo

```
relatório JSON (violações Lint + ATF)
        │
        ▼
corrector.py ── formata violações + SYSTEM_PROMPT (regras de reparo)
        │        └─ chama Qwen3-Coder (qwen3-coder-30b-a3b-instruct-fp8) no Tech3Lab
        │           retry com backoff exponencial (3 tentativas), remove fences markdown
        ▼
outputs/codes/{llm}_corrected.kt
        │
        ▼
reanalyse.py ── reutiliza process_llm(): Build + Lint + ATF
        │
        ▼
outputs/reports/reanalise_*.json
```

Hoje o ciclo é **manual**: roda-se `corrector.py` e depois `reanalyse.py`. Não há loop automático que repare de novo se ainda houver violações.

### 4.2 Por que um modelo local

O reparo usa um modelo de código hospedado no laboratório (Qwen3-Coder via Tech3Lab), separado dos LLMs geradores. Isso evita que o mesmo modelo avalie e corrija o próprio código, e mantém o custo e a reprodutibilidade sob controle.

### 4.3 Regras do prompt de reparo (v5, atual)

| Violação | Regra |
|----------|-------|
| `SpeakableTextPresentCheck` em `Box`/`Row`/`Column`/`Card` clicáveis | `Modifier.semantics { contentDescription = "..." }` |
| `Icon()` isolado | `contentDescription` como parâmetro |
| `Slider`/`SeekBar` | `Modifier.semantics { contentDescription = "..." }` |
| `TouchTargetSizeCheck` | `Modifier.minimumInteractiveComponentSize()` ou `Modifier.size(48.dp)` |
| `TextContrastCheck` | ajustar cores para 4,5:1 (WCAG AA) |
| **`IconButton`** (regra central) | `Modifier.clearAndSetSemantics { contentDescription = "..." }` no botão **e** `contentDescription` não nulo no `Icon` filho, em **todos** os `IconButton` do arquivo |
| `ComposeTextFieldMissingLabel` | `label = { Text("...") }` |

### 4.4 Evolução do prompt

| Versão | Commit | Mudança principal |
|--------|--------|-------------------|
| v1 | inicial | Genérico, sem exemplos de API |
| v2 | `986665b` | Exemplos WRONG/CORRECT por check; regra do `Modifier.semantics` |
| v3 | `73550fd` | `contentDescription` no `Icon()`, não no modifier do `IconButton` |
| v4 | `e57c30c` | Proibição de `Modifier.semantics` em `IconButton`; `mergeDescendants = true` em `Row` |
| v5 | código atual | `clearAndSetSemantics` obrigatório em todo `IconButton` — executado na R5: ATF 0, Lint 0 |

---

## 5. Resultados do piloto de reparo

**Tela:** Music Player · **Gerador:** ChatGPT (código inserido manualmente, 337 linhas) · **Reparador:** Qwen3-Coder · **Data:** 29/09/2026 · **Dispositivo:** ZF525CZBLD

### 5.1 Progressão

| Métrica | Inicial | R1 (v1) | R2 (v2) | R3 (v3) | R4 (v4) | R5 (v5) |
|---------|---------|---------|---------|---------|---------|---------|
| Build | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| ATF (ST) | 9 | — | 2 | 7 | 7 | **0** |
| Lint A11Y | 0 | — | 10 | 0 | 0 | **0** |
| Tempo total | 350,6 s | — | 385,4 s | 315,7 s | 339,3 s | 153,5 s |

### 5.2 O que aconteceu em cada rodada

- **R1 (v1):** o build falhou. O modelo usou `contentDescription` como parâmetro de `Box(...)`, que não existe.
- **R2 (v2):** ATF caiu de 9 para 2 (−78%). Mas o modelo pôs `semantics` no `IconButton` e deixou `contentDescription = null` no `Icon` filho, o que gerou 10 ocorrências estáticas (5 `IconNullContentDescription` + 5 `IconButtonMissingLabel`).
- **R3 (v3):** Lint zerou. ATF voltou para 7. O modelo manteve `semantics` no `IconButton` **e** acrescentou descrição no `Icon` (declaração dupla). Os dois `Slider` foram resolvidos.
- **R4 (v4):** sem `semantics` no `IconButton`, só descrição no `Icon`. Lint continuou zerado e ATF continuou em 7. As 7 violações foram idênticas às da R3.

### 5.3 Interpretação (importante para o artigo)

O log permite uma leitura mais precisa do que "semantics sem `mergeDescendants`":

- **Na R2**, a descrição estava no **nó clicável** (`IconButton`) → o ATF passou, o Lint falhou.
- **Na R4**, a descrição estava só no **filho** (`Icon`) → o Lint passou, o ATF falhou.

Ou seja, **os dois checadores esperam o rótulo em lugares diferentes**. O Lint verifica o `Icon` filho; o ATF inspeciona o `AccessibilityNodeInfo` do `IconButton`. Corrigir para um quebra o outro. A explicação por nó opaco (`semantics` sem `mergeDescendants`) se aplica à R3, mas a R4 mostra que tirar o `semantics` não basta.

A v5 resolve os dois ao mesmo tempo: rótulo no botão via `clearAndSetSemantics` (satisfaz o ATF) e descrição não nula no `Icon` (satisfaz o Lint). **Confirmado na R5 (20/10/2026): ATF 0, Lint 0, Static 0**, incluindo Favorite e Share. Pendente: conferir que `clearAndSetSemantics` só foi aplicado em `IconButton` e validar com TalkBack.

> **Alerta de honestidade metodológica:** as regras `ComposeIconNullContentDescription` e `ComposeIconButtonMissingLabel` são **nossas**. Um revisor pode argumentar que parte do conflito vem do desenho das nossas regras. O artigo deve reconhecer isso e argumentar por que as regras são razoáveis (seguem a orientação oficial de Compose de não deixar ícones significativos com descrição nula) e por que o conflito é relevante mesmo assim (desenvolvedores reais usam checadores estáticos com essa lógica).

### 5.4 Elementos persistentes

`TopActions — Favorite` `[76,51][226,201]` e `TopActions — Share` `[995,51][1145,201]` falharam em **todas** as rodadas, inclusive na R2. A estrutura deles difere dos controles de reprodução. Se a v5 não os resolver, a próxima hipótese é aplicar `clearAndSetSemantics` ou `mergeDescendants = true` no `Row` pai.

---

## 6. Contribuição nova em relação ao WebMedia

| | WebMedia 2026 | CHASE 2027 |
|---|---|---|
| Pergunta | As telas geradas por LLMs são acessíveis? | Dá para repará-las automaticamente, e o que dá errado nisso? |
| Pipeline | Detectar | Detectar → **reparar** → **reanalisar** |
| "Correção" | Só erros de compilação | **Violações de acessibilidade** |
| Nível | Código-fonte (detecção) | **Reparo no código-fonte, antes da compilação** |
| Lint × ATF | Complementares na detecção | **Em conflito no reparo** (regressão cruzada) |
| Conhecimento | — | 5 iterações de prompt mostram que o reparo exige expertise rara de semântica Compose |
| Modelos | 3 geradores | 3 comerciais + 1 local como geradores; 1 local como reparador |

### 6.1 Contribuições (para a introdução)

1. **Um ciclo detectar–reparar–reanalisar** para telas Compose geradas por LLMs, que opera no código-fonte antes da compilação. *(já existe)*
2. **Uma avaliação empírica** do reparo em telas de 10 tipos e 4 modelos geradores. **[DADO PENDENTE]**
3. **A caracterização da regressão cruzada** entre análise estática e dinâmica: os checadores esperam o rótulo em nós diferentes, e satisfazer um pode quebrar o outro. *(piloto existe; frequência na bateria é [DADO PENDENTE])*
4. **Implicações para desenvolvedores** que delegam UI a LLMs e usam checadores automáticos como garantia de inclusão. *(argumentativa)*

### 6.2 Posicionamento frente ao A11yArgus (CHASE 2026)

A11yArgus (Ferreira et al.) detecta 13 tipos de problema em **apps existentes**, com DroidBot e UI Automator, em 200 apps, com 91,9% de precisão e 97,8% de recall. A Melodie trabalha em **código gerado por LLM**, e não só detecta como **repara no fonte**. Os trabalhos são complementares: A11yArgus olha o produto; a Melodie intervém no momento em que o código nasce.

---

## 7. O ângulo humano (por que o CHASE)

O CHASE publica sobre pessoas fazendo software. A ferramenta é o meio; o argumento é humano.

1. **Delegação e exclusão invisível.** O desenvolvedor pede a tela, o código compila e a tela parece correta. Quem paga é o usuário de leitor de tela, que não participou da conversa. O WebMedia já mostrou com TalkBack que botões sem rótulo são anunciados sem ação e ícones com descrição nula desaparecem.
2. **Falsa garantia e excesso de confiança.** A regressão cruzada mostra que "zero warnings no Lint" não significa acessível. Isso se conecta à literatura de *overreliance* em IA e em ferramentas automáticas, eixo "SE, AI and humans" da chamada.
3. **Expertise escassa.** Foram 5 iterações para chegar ao `clearAndSetSemantics`. Nem os LLMs geradores nem um desenvolvedor sem especialização chegariam lá sozinhos. O reparo codifica conhecimento de especialista e o torna reutilizável, o que se conecta ao eixo de diversidade e inclusão.
4. **Prompt engineering como prática humana.** A evolução v1→v5 é, em si, um registro de como um humano negocia com um modelo para obter código acessível.

### 7.1 Ponto fraco: não há participantes humanos

Revisores do CHASE podem perguntar "onde estão as pessoas?". Mitigação viável nesta semana: **validar com TalkBack algumas telas reparadas**, como no WebMedia, mostrando que o reparo melhora o que o leitor de tela anuncia, e não só os números do ATF. Estudo com usuários fica para o ICSME ou um trabalho posterior.

---

## 8. Plano experimental da bateria de reparo

### 8.1 Perguntas de pesquisa propostas

- **RQ1 (eficácia):** quanto o reparo automático reduz as violações estáticas e dinâmicas em telas Compose geradas por LLMs?
- **RQ2 (regressões):** com que frequência o reparo introduz novas violações, e em que direção (estática → dinâmica ou o contrário)?
- **RQ3 (efeito percebido):** as telas reparadas são de fato mais acessíveis para um usuário de leitor de tela? (validação com TalkBack em amostra)

### 8.2 Desenho

| Fator | Níveis |
|-------|--------|
| Tipos de tela | 10 (`prompts/01`–`10`): Login, Registration, Product Details, User Profile, Music Player, Navigation Drawer, Video Player, Post Feed, Banking Home, Notifications |
| Geradores | Claude, GPT, Gemini (comerciais) + modelo local do laboratório |
| Estratégia | Zero-shot (comparável ao WebMedia) |
| Modo visual | Claro e escuro (se o tempo permitir; senão só claro, declarado) |
| Reparador | Qwen3-Coder, prompt v5 **congelado** |
| Rodadas de reparo | 1 rodada fixa (recomendado). Uma segunda rodada só como análise exploratória separada |

**Tamanho:** 10 telas × 4 geradores = **40 telas**. Com claro e escuro, 80 execuções de detecção + 80 de reanálise.

> **Os tipos de tela mudaram em relação ao WebMedia** (8 tipos diferentes). Isso é aceitável, mas precisa ser dito. A vantagem: a bateria nova também serve como replicação da detecção com outras telas.

### 8.3 Estimativa de tempo

~6 min por execução no dispositivo (média do WebMedia: 5,8 min).

| Cenário | Execuções | Tempo de máquina |
|---------|-----------|------------------|
| Só claro | 40 detecção + 40 reanálise | ~8 h |
| Claro + escuro | 80 + 80 | ~16 h |

Mais o tempo de chamada ao reparador. **Recomendação:** começar só com o modo claro; acrescentar o escuro se sobrar tempo.

### 8.4 Protocolo, passo a passo

1. **Fazer backup** dos outputs do piloto (seção 9).
2. **Validar a v5 no piloto:** reparar o relatório `report_20260929_171451.json` com a v5 e reanalisar.
   - ATF = 0 e Lint = 0 → congelar a v5 e seguir.
   - Persistem só Favorite/Share → testar a hipótese do `Row` pai em **uma** iteração (v6); congelar e seguir.
   - Regressão nova → registrar no log, decidir com o Windson entre seguir com o achado ou ir para o ICSME.
3. **Congelar** o prompt de reparo, os IDs de modelo e as versões de Kotlin/AGP/BOM. Registrar o commit.
4. **Detecção:** rodar as 40 telas e salvar todos os JSONs.
5. **Reparo:** rodar `corrector.py` em cada relatório.
6. **Reanálise:** rodar `reanalyse.py` em cada arquivo reparado.
7. **Validação com TalkBack:** amostra de 3 a 5 telas, antes e depois, anotando o que o leitor anuncia.
8. **Consolidar** em uma planilha (seção 8.5) e versionar no repositório.

### 8.5 Métricas

Por tela, antes e depois do reparo:

| Métrica | Definição |
|---------|-----------|
| Build após reparo | o código reparado compila? |
| Violações por check | contagem de ST, TT, CT (ATF) e de cada regra estática |
| Redução | (antes − depois) / antes, por analisador e no total |
| Tela resolvida | build OK, ATF = 0 e estático = 0 |
| Regressão | qualquer check com mais violações depois do que antes |
| Regressão cruzada | um analisador melhora e o outro piora |
| Tamanho da mudança | linhas alteradas no diff (proxy de preservação do código) |
| Tempo | tempo de reparo + tempo de reanálise |

Tabelas e figuras previstas: tabela antes × depois por gerador; gráfico de barras empilhadas por check; contagem de telas resolvidas, melhoradas, inalteradas e com regressão.

---

## 9. Pré-requisitos técnicos antes da bateria

| # | Item | Por que importa | Esforço |
|---|------|-----------------|---------|
| 1 | **Backup dos outputs do piloto** (`outputs/reports/`, `outputs/codes/`) para fora do container | São a única evidência da regressão cruzada e não estão no git | 5 min |
| 2 | **Conferir os IDs de modelo** em `src/llm_client.py` | O código tem `gpt-4.5` e `gemini-2.5-pro`; o WebMedia reporta ChatGPT 5.5 e Gemini 3.1 Pro. O artigo precisa dos IDs exatos usados | 15 min |
| 3 | **Decidir se o modelo local também gera telas** | Define se são 3 ou 4 geradores (30 ou 40 telas) | decisão |
| 4 | **Alinhar o prompt de `/api/correct-general`** (`src/web_server.py`) com o v5, ou não usar esse endpoint na bateria | Hoje ele não tem a regra de `clearAndSetSemantics` e reproduziria as regressões v1–v4 | 20 min |
| 5 | **Registrar a v5 no `CORRECTION_LOG.md`** com o commit | Rastreabilidade | 5 min |
| 6 | (Opcional) Script que encadeia detecção → reparo → reanálise para as 40 telas | Hoje é manual, tela por tela | 1–2 h |
| 7 | (Opcional) Checar compilação do arquivo reparado antes de gravar | Hoje só se descobre a falha na reanálise | 30 min |

---

## 10. Ameaças à validade

**Internas**
- **Ajuste do prompt no conjunto de teste:** o prompt v5 foi desenvolvido no Music Player, que também é um dos 10 tipos da bateria. Reportar o Music Player à parte ou excluí-lo da métrica principal.
- **Não determinismo:** temperatura 1,0 na geração e uma execução por configuração. Declarar.
- **Regras próprias:** parte das regras estáticas é nossa (ver 5.3).

**De construto**
- Contagem de violações ≠ acessibilidade real. Mitigação: validação com TalkBack.
- O reparo pode remover violações mudando o comportamento da tela. Mitigação: build, tamanho do diff e inspeção de amostra.
- Um mesmo defeito pode aparecer no Lint e no ATF (contagens brutas, como no WebMedia).

**Externas**
- Só Jetpack Compose, só Android, um dispositivo físico, um reparador.
- Telas isoladas, não apps completos.

---

## 11. Estrutura do artigo

Formato: IEEEtran conference 10pt, 5 páginas **contando referências**. Orçamento aproximado:

| Seção | Páginas | O que dá para escrever **agora** | O que espera dados |
|-------|---------|-----------------------------------|--------------------|
| Abstract | — | versão genérica (seção 12) | números |
| 1. Introdução | 0,75 | problema humano, lacuna, contribuições 1, 3 e 4 | contribuição 2 |
| 2. Background e trabalhos relacionados | 0,5 | semântica Compose, ATF, LLMs e UI, A11yArgus, AccessGuru | — |
| 3. Abordagem | 1,0 | pipeline (citando o trabalho anterior em 3ª pessoa), módulo de reparo, prompt v5, figura do ciclo | — |
| 4. Estudo piloto | 0,5 | tudo da seção 5 deste documento | — |
| 5. Avaliação | 1,0 | RQs, desenho, protocolo, métricas | resultados |
| 6. Discussão | 0,5 | falsa garantia, expertise escassa, implicações para desenvolvedores e ferramentas | evidência da bateria |
| 7. Ameaças à validade | 0,25 | seção 10 | — |
| 8. Conclusão e trabalho futuro | 0,25 | estudo com usuários, mais reparadores, loop iterativo | — |
| Referências | 0,75 | — | — |

**Figuras previstas:** (1) ciclo detectar–reparar–reanalisar; (2) trecho de código R2 × R4 × v5 mostrando onde fica o rótulo; (3) resultado antes × depois. **[DADO PENDENTE]**

**Regra para escrever sem dados:** onde precisar de número, escrever `\todo{X}` em vez de estimar. Nenhum número entra no artigo sem estar em um JSON versionado.

---

## 12. Resumo submetido (versão genérica)

Registrado no HotCRP sem números, para atualizar até 23/10 (orientação do Windson):

> Developers increasingly delegate user interface implementation to Large Language Models (LLMs), yet the generated code routinely excludes users who rely on screen readers. Prior work showed that LLM-generated Jetpack Compose interfaces compile successfully but exhibit widespread accessibility violations, and that static and dynamic analyses detect complementary defects. This paper extends an automated evaluation pipeline into a detect–repair–reanalyse loop that repairs accessibility violations at the source-code level, before compilation, by feeding violations reported by custom Android Lint rules and the Accessibility Test Framework (ATF) to a locally hosted code LLM. We evaluate the approach on screens covering common mobile interface types generated by multiple LLMs. Our results show that automated repair can substantially reduce accessibility violations, but also expose cross-regressions between static and dynamic analysis: repairs that satisfy static rules can create opaque nodes in the runtime accessibility tree, reintroducing barriers for screen-reader users. Reaching a stable repair strategy required iteratively encoding specialized Compose semantics knowledge into the repair prompt. These findings suggest that passing one automated check can give developers a false sense of accessibility compliance, and emphasize the need for repair tools that encode scarce accessibility expertise for developers who rely on LLMs and automated checkers as a proxy for inclusion.

**Ajustes na versão final:**
- "can substantially reduce" → manter só se a redução for grande; senão, "can reduce".
- "Reaching a stable repair strategy" → manter só se a v5 funcionar; senão, "Repair quality depended on iteratively encoding…".
- Considerar trocar "create opaque nodes" por "place labels on nodes the runtime checker does not inspect", que descreve melhor a R4 (seção 5.3).
- Inserir: número de telas, modelos, % de redução, telas resolvidas e telas com regressão.

---

## 13. Logística de submissão

| Item | Detalhe |
|------|---------|
| Conferência | CHASE 2027 — 20th Int. Conf. on Cooperative and Human Aspects of SE, com o ICSE 2027, Dublin, 26–27/04/2027 |
| Submissão | https://chase27.hotcrp.com/ |
| Prazos (AoE) | Resumo 16/10/2026 · Paper **23/10/2026** · Notificação 18/12/2026 · Camera-ready 29/01/2027 |
| Formato | IEEEtran 10pt conference; extended abstract de 5 páginas contando referências (aceita resultados preliminares) |
| Revisão | Duplo-anônima: sem nomes, sem "Melodie", sem link deste repositório. Usar repositório anônimo (ex.: anonymous.4open.science) |
| Autocitação | O WebMedia 2026 deve ser citado em 3ª pessoa ("Prior work [X] proposed…") |
| PDF | Acessível (tags, texto alternativo nas figuras, ordem de leitura) |
| Autores | ORCID de todos |
| Uso de IA | Declaração nos agradecimentos |
| Referências | Todas verificadas; referência inventada dá rejeição sumária |
| Conflito | Declarar Anderson Uchôa (UFC), membro do comitê |
| Coautoria | François (HEC/Tech3Lab) convidado; pendente: confirmação, ORCID e decisão sobre incluir ou só informar o Constantinos |

---

## 14. Plano B e venues alternativas

| Venue | Prazo | Formato | Observação |
|-------|-------|---------|------------|
| **ICSME 2027** (Toronto) | março de 2027 | full paper | Indicada pelo Windson. Mesma linha, resultados mais maduros. Usar o feedback do CHASE |
| SE4All 2027 (workshop do ICSE) | 13/11/2026 | short 5 p. ou regular 8 p. | Sem Qualis. **Não pode ser submetido ao mesmo tempo que o CHASE** |
| W4A 2027 (Dublin) | ~janeiro de 2027 | — | Foco em acessibilidade web |
| CHI 2027 Posters | 21/01/2027 | poster | Visibilidade em HCI |

**Para o ICSME, acrescentar:** várias rodadas de reparo (loop), mais de um reparador, várias execuções por configuração, estudo com usuários de leitor de tela, e comparação com um baseline (ex.: reparo pelo próprio LLM gerador).

---

## 15. Cronograma

| Data | Atividade | Status |
|------|-----------|--------|
| 16/10 | Resumo genérico no HotCRP | confirmar |
| 19–20/10 | Escrever seções 1–4 e 7 sem dados; resolver os pré-requisitos 1–5 da seção 9 | em andamento |
| Laboratório online | Validar a v5 no piloto (~15 min de máquina) | pendente |
| +1 dia | Bateria: detecção + reparo + reanálise (~8 h de máquina, só modo claro) | pendente |
| 21/10 | Rascunho completo para o Windson e o François | pendente |
| 22/10 | Incorporar revisões; atualizar o resumo no HotCRP com os números | pendente |
| 23/10 | Submeter | pendente |

**Ponto de decisão:** se até 21/10 a v5 não tiver rodado, ou se a bateria não couber, conversar com o Windson sobre submeter só com o piloto (extended abstract aceita preliminares) ou mover para o ICSME.

---

## 16. Decisões em aberto

1. O modelo local também é gerador? (3 ou 4 geradores)
2. Modo escuro entra na bateria?
3. Uma rodada de reparo fixa ou loop até convergir?
4. O Music Player entra na métrica principal ou é reportado à parte?
5. Quais IDs exatos de modelo foram e serão usados?
6. O Constantinos entra como coautor?
7. Full paper ou extended abstract? (depende do resultado da bateria; padrão: extended abstract)
8. Registro de propriedade intelectual no INPI ainda é desejado? (precisa ser protocolado antes da publicação)
