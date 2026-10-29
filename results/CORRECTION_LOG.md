# Log de Resultados — Correção de Acessibilidade com LLM

**Projeto:** Melodie A11Y — UFC / GREat  
**Pipeline:** Geração Jetpack Compose → Build → Lint Estático → ATF (dispositivo físico)  
**Dispositivo:** ZF525CZBLD (192.168.2.171)

---

## Experimento 1 — Tela: Music Player

**Prompt utilizado:** `[teste direto de código]` (código gerado externamente via ChatGPT)  
**Data:** 29/09/2026

---

### Análise Inicial

| Campo | Valor |
|-------|-------|
| Relatório | `report_20260929_171451.json` |
| LLM gerador | ChatGPT (código inserido manualmente) |
| Linhas de código | 337 |
| Build | ✅ Sucesso (117.6s) |
| Lint | 98.2s |
| ATF | 134.8s |
| Total | 350.6s |

**Violações detectadas (ATF) — 9 total:**

| Check | Severidade | Localização |
|-------|------------|-------------|
| SpeakableTextPresentCheck | ERROR | View at [76,51][226,201] |
| SpeakableTextPresentCheck | ERROR | View at [995,51][1145,201] |
| SpeakableTextPresentCheck | ERROR | SeekBar at [75,1545][1145,1608] |
| SpeakableTextPresentCheck | ERROR | View at [120,1792][270,1942] |
| SpeakableTextPresentCheck | ERROR | View at [315,1792][465,1942] |
| SpeakableTextPresentCheck | ERROR | View at [510,1766][711,1967] |
| SpeakableTextPresentCheck | ERROR | View at [756,1792][906,1942] |
| SpeakableTextPresentCheck | ERROR | View at [951,1792][1101,1942] |
| SpeakableTextPresentCheck | ERROR | SeekBar at [188,2530][1032,2593] |

---

### Correção 1 — Falha no Build

| Campo | Valor |
|-------|-------|
| Corretor | Qwen3-Coder (Tech3Lab, `qwen3-coder-30b-a3b-instruct-fp8`) |
| Prompt versão | v1 (genérico) |
| Re-análise | `reanalise_20260929_175958.json` |

**Resultado:** ❌ Build FAILED (93.2s)

**Causa raiz:** modelo usou `contentDescription` como parâmetro de construtor — inválido na maioria dos Composables:
```kotlin
Box(contentDescription = "...")  // erro: Cannot find a parameter with this name
```
**Correção correta:** `Modifier.semantics { contentDescription = "..." }`

**Ação tomada:** prompt v2 — exemplos explícitos de API correta por tipo de violação (commit `986665b`).

---

### Correção 2 — Progresso Parcial (ATF −78%, Lint +10 novas)

| Campo | Valor |
|-------|-------|
| Corretor | Qwen3-Coder (Tech3Lab, `qwen3-coder-30b-a3b-instruct-fp8`) |
| Arquivo | `test_corrected.kt` (9.9 KB) |
| Prompt versão | v2 |
| Re-análise | `reanalise_20260929_182358.json` |

**Timings:** Build 135.5s · Lint 113.2s · ATF 136.7s · Total 385.4s

**Resultados:**

| Check | Antes | Depois | Δ |
|-------|-------|--------|---|
| ATF — SpeakableTextPresentCheck | 9 | 2 | −78% ✅ |
| Lint — ComposeIconNullContentDescription | 0 | 5 | +5 ❌ |
| Lint — ComposeIconButtonMissingLabel | 0 | 5 | +5 ❌ |

**Causa raiz das novas violações Lint:** modelo colocou `semantics` no modifier do `IconButton` mas deixou `contentDescription = null` no `Icon()` filho:
```kotlin
// ❌ Gerado pelo modelo:
IconButton(modifier = Modifier.semantics { contentDescription = "Shuffle" }) {
    Icon(contentDescription = null, ...)  // dispara ComposeIconButtonMissingLabel
}
```
**Ação tomada:** prompt v3 — regra crítica: `contentDescription` deve ir no `Icon()`, nunca no modifier do `IconButton` (commit `73550fd`).

---

### Correção 3 — Lint Zerado, ATF Regrediu

| Campo | Valor |
|-------|-------|
| Corretor | Qwen3-Coder (Tech3Lab, `qwen3-coder-30b-a3b-instruct-fp8`) |
| Arquivo | `test_corrected.kt` (9.9 KB) |
| Prompt versão | v3 |
| Re-análise | `reanalise_20260929_203727.json` |

**Timings:** Build 108.5s · Lint 90.0s · ATF 117.2s · Total 315.7s

**Resultados:**

| Check | Correção 2 | Correção 3 | Δ |
|-------|------------|------------|---|
| ATF — SpeakableTextPresentCheck | 2 | 7 | +5 ❌ (regressão) |
| Lint — ComposeIconNullContentDescription | 5 | 0 | −5 ✅ |
| Lint — ComposeIconButtonMissingLabel | 5 | 0 | −5 ✅ |
| Static issues | 10 | 0 | −10 ✅ |

**Análise da regressão ATF:**

O modelo aplicou a regra do Lint corretamente (`contentDescription` no `Icon()`), mas manteve `Modifier.semantics { contentDescription = "..." }` no `IconButton` simultaneamente:
```kotlin
// ❌ Gerado pelo modelo (dupla declaração):
IconButton(modifier = Modifier.semantics { contentDescription = "Shuffle" }) {
    Icon(contentDescription = "Shuffle", ...)
}
```
`Modifier.semantics {}` sem `mergeDescendants = true` cria um **nó semântico opaco** que bloqueia a fusão dos filhos na árvore de acessibilidade em tempo de execução. O Lint não detecta (análise estática), mas o ATF detecta ao inspecionar a árvore real do app no dispositivo.

**Violações ATF na Correção 3:**

| Check | Localização | Mapeamento provável |
|-------|-------------|---------------------|
| SpeakableTextPresentCheck | View at [76,51][226,201] | TopActions — Favorite (persistente) |
| SpeakableTextPresentCheck | View at [995,51][1145,201] | TopActions — Share (persistente) |
| SpeakableTextPresentCheck | View at [120,1792][270,1942] | PlaybackControls — Shuffle |
| SpeakableTextPresentCheck | View at [315,1792][465,1942] | PlaybackControls — Previous |
| SpeakableTextPresentCheck | View at [510,1766][711,1967] | PlaybackControls — Play/Pause |
| SpeakableTextPresentCheck | View at [756,1792][906,1942] | PlaybackControls — Next |
| SpeakableTextPresentCheck | View at [951,1792][1101,1942] | PlaybackControls — Repeat |

**Observação:** As violações dos `SeekBar` (progress e volume) desapareceram — o `Modifier.semantics` nos `Slider` funcionou corretamente pois esses não são `IconButton`.

**Violações persistentes em TopActions** ([76,51] e [995,51]): presentes em todas as 3 correções, mesmo com `contentDescription` correto no `Icon()`. Hipótese: ATF detecta um nó intermediário (o próprio container do `IconButton` ou o toque expandido) separado do `Icon` filho. Requer investigação.

**Ação para próxima correção:**
1. Proibir explicitamente `Modifier.semantics` em `IconButton` no prompt
2. Investigar TopActions — adicionar `Modifier.semantics { mergeDescendants = true }` no `Row` pai pode resolver a detecção dos nós filhos

---

### Correção 4 — Prompt v4 (sem semantics em IconButton) → ATF inalterado

| Campo | Valor |
|-------|-------|
| Corretor | Qwen3-Coder (Tech3Lab, `qwen3-coder-30b-a3b-instruct-fp8`) |
| Prompt versão | v4 |
| Re-análise | `reanalise_20260929_205943.json` |

**Timings:** Build 108.8s · Lint 89.7s · ATF 140.9s · Total 339.3s

**Resultados:**

| Check | Correção 3 | Correção 4 | Δ |
|-------|------------|------------|---|
| ATF — SpeakableTextPresentCheck | 7 | 7 | 0 (sem melhora) |
| Lint — ComposeIconNullContentDescription | 0 | 0 | ✅ mantido |
| Lint — ComposeIconButtonMissingLabel | 0 | 0 | ✅ mantido |
| Static issues | 0 | 0 | ✅ mantido |

**Análise da estagnação ATF:**

O código gerado foi sintaticamente correto:
```kotlin
// ✅ Código v4 — Lint passa, mas ATF ainda falha:
IconButton(onClick = {}) {
    Icon(imageVector = Icons.Filled.Shuffle, contentDescription = "Shuffle", ...)
}
```

A causa raiz é estrutural: o `AccessibilityNodeInfo` que o ATF inspeciona em tempo de execução representa o `IconButton` como um nó separado do `Icon` filho. O ATF vê o nó do `IconButton` sem `contentDescription` e sinaliza `SpeakableTextPresentCheck`. A fusão semântica (mergeDescendants) implícita do `IconButton` não é confiável para o ATF nesse contexto.

**Violações ATF persistentes (todas 7 idênticas à Correção 3):**

| Localização | Composable mapeado |
|-------------|---------------------|
| View at [76,51][226,201] | TopActions — Favorite |
| View at [995,51][1145,201] | TopActions — Share |
| View at [120,1792][270,1942] | PlaybackControls — Shuffle |
| View at [315,1792][465,1942] | PlaybackControls — Previous |
| View at [510,1766][711,1967] | PlaybackControls — Play/Pause |
| View at [756,1792][906,1942] | PlaybackControls — Next |
| View at [951,1792][1101,1942] | PlaybackControls — Repeat |

**Conclusão:** A abordagem de colocar `contentDescription` apenas no `Icon()` filho é insuficiente para o ATF. O ATF inspeciona o nó de acessibilidade do `IconButton` diretamente, e o `contentDescription` do `Icon` filho não é herdado de forma confiável no `AccessibilityNodeInfo` exposto pelo `IconButton`.

**Solução identificada — `Modifier.clearAndSetSemantics`:**

`clearAndSetSemantics` remove TODOS os nós semânticos filhos e define o `contentDescription` diretamente no nível do botão. É o único mecanismo que garante que o ATF veja a descrição no nó que ele inspeciona:

```kotlin
// ✅ CORRETO para Lint + ATF:
IconButton(
    onClick = { ... },
    modifier = Modifier.clearAndSetSemantics { contentDescription = "Shuffle" }
) {
    Icon(imageVector = Icons.Filled.Shuffle, contentDescription = "Shuffle", ...)
}
```

**Ação tomada:** Prompt v5 com `clearAndSetSemantics` como regra obrigatória para todo `IconButton`.

---

### Correção 5 — Prompt v5 (`clearAndSetSemantics`) → ATF, Lint e Static zerados

| Campo | Valor |
|-------|-------|
| Data | 20/10/2026, 19:32:17 |
| Relatório de origem | `report_20260929_171451.json` (mesma análise inicial das correções 1–4) |
| Corretor | Qwen3-Coder (Tech3Lab, `qwen3-coder-30b-a3b-instruct-fp8`) |
| Prompt versão | v5 |
| Re-análise | `reanalise_20261020_193217.json` |
| Linhas de código corrigido | 350 |
| Observação | Token do Tech3Lab foi regenerado após o reset do laboratório (401 com o token antigo) |

**Timings:** Build 40.3s · Lint 36.6s · ATF 76.7s · Total 153.5s

**Resultados:**

| Check | Inicial | Correção 4 | Correção 5 | Δ vs. inicial |
|-------|---------|------------|------------|---------------|
| Build | ✅ | ✅ | ✅ | — |
| ATF — SpeakableTextPresentCheck | 9 | 7 | **0** | −100% ✅ |
| Lint A11Y | 0 | 0 | **0** | mantido ✅ |
| Static issues | 0 | 0 | **0** | mantido ✅ |

**Interpretação:** confirma a hipótese da Correção 4. O ATF inspeciona o nó do `IconButton`, e o Lint inspeciona o `Icon` filho. Com `clearAndSetSemantics` no botão (rótulo no nó que o ATF lê) e `contentDescription` não nulo no `Icon` (o que o Lint exige), os dois checadores ficam satisfeitos ao mesmo tempo. As violações persistentes de TopActions (Favorite e Share), presentes em todas as rodadas anteriores, também foram resolvidas.

**Verificações pendentes antes de usar este resultado no artigo:**
- [ ] Confirmar no JSON que o teste instrumentado do ATF rodou por completo. O ATF levou 76.7s, contra 117–141s nas rodadas anteriores. A queda do build (40s contra ~110s) se explica pelo cache do Gradle.
- [ ] Confirmar no código corrigido que `clearAndSetSemantics` foi aplicado **somente** em `IconButton`, e não em containers (`Row`, `Column`, `Box`) ou na tela inteira, o que zeraria o ATF apagando nós em vez de rotulá-los.
- [ ] Validar com TalkBack que cada botão anuncia o nome correto.
- [ ] Identificar as execuções com ATF = 17 (set/2026) e ATF = 2 (out/2026) que aparecem no gráfico de tendência da interface e não constam neste log.
- [ ] Fazer backup de `outputs/reports/` e `outputs/codes/` fora do container.

---

## Resumo Geral de Progresso

| Métrica | Análise Inicial | Correção 1 | Correção 2 | Correção 3 | Correção 4 | Correção 5 |
|---------|-----------------|------------|------------|------------|------------|------------|
| Build | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |
| ATF violations | 9 | — | 2 | 7 | 7 | **0** |
| Lint A11Y | 0 | — | 5 | **0** | **0** | **0** |
| Static issues | 0 | — | 10 | **0** | **0** | **0** |
| Prompt versão | — | v1 | v2 | v3 | v4 | v5 |

**Melhor resultado:** Correção 5 → **ATF 0, Lint 0, Static 0** (pendente das verificações acima)

---

## Versões do Prompt do Corrector

| Versão | Commit | Mudança principal |
|--------|--------|-------------------|
| v1 | inicial | Genérico — sem exemplos de API |
| v2 | `986665b` | Exemplos WRONG/CORRECT por tipo de check; regra do `Modifier.semantics` |
| v3 | `73550fd` | Regra crítica: `contentDescription` no `Icon()`, não no modifier do `IconButton`; tabela de placement |
| v4 | `e57c30c` | Proibição explícita de `Modifier.semantics` em `IconButton`; `mergeDescendants = true` para Row containers |
| v5 | (código atual de `src/corrector.py`) | `clearAndSetSemantics` como padrão obrigatório para todo `IconButton` — executado na Correção 5: ATF 0, Lint 0 |

---

## Arquivos de Referência

| Arquivo | Descrição |
|---------|-----------|
| `outputs/reports/report_20260929_171451.json` | Análise inicial |
| `outputs/reports/reanalise_20260929_175958.json` | Re-análise 1 — build falhou |
| `outputs/reports/reanalise_20260929_182358.json` | Re-análise 2 — 78% redução ATF, +10 Lint |
| `outputs/reports/reanalise_20260929_203727.json` | Re-análise 3 — Lint zerado, ATF regrediu |
| `outputs/reports/reanalise_20260929_205943.json` | Re-análise 4 — ATF inalterado (7 violações) |
| `outputs/reports/reanalise_20261020_193217.json` | Re-análise 5 — v5: ATF, Lint e Static zerados |
| `outputs/codes/test_corrected.kt` | Último código corrigido |
| `src/corrector.py` | Script de correção (Qwen3-Coder via Tech3Lab) |
| `src/reanalyse.py` | Script de re-análise (build + Lint + ATF) |
