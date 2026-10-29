# Bateria de Reparo — CHASE 2027

**Desenho:** 10 tipos de tela × 3 geradores (Claude, ChatGPT, Gemini) = 30 telas
**Fluxo por tela:** Análise → Correção (Qwen3-Coder, prompt v5 congelado) → Reanálise
**Prompts:** `prompts/bateria_chase2027/` (descrição da tela + sufixo fixo do pipeline, prontos para colar)
**Modo visual:** claro (escuro opcional, se sobrar tempo)

**Prompt neutro em acessibilidade (nível 1):** em relação ao `FIXED_SUFFIX` do `src/pipeline.py` (usado no WebMedia), os prompts da bateria removem as três menções que poderiam induzir o modelo:
- "evaluated by an accessibility pipeline" → "evaluated by a pipeline";
- "and always provide contentDescription" (na regra dos ícones) → removido;
- "Package name: com.accessibility.test" → removido (o pipeline normaliza o pacote em `inject_kotlin`).

As restrições técnicas de compilação continuam iguais. O `FIXED_SUFFIX` do pipeline não foi alterado, para o WebMedia seguir reproduzível. Se alguma tela falhar na compilação por `Icon()` sem `contentDescription` (parâmetro obrigatório no Material 3), registrar na coluna Obs.

## Registro antes de começar

| Item | Valor |
|------|-------|
| Commit do repositório (prompt v5 congelado) | |
| Modelo reparador | `qwen3-coder-30b-a3b-instruct-fp8` |
| Dispositivo | ZF525CZBLD |
| Claude — nome/versão exibido na interface | |
| ChatGPT — nome/versão exibido na interface | |
| Gemini — nome/versão exibido na interface | |
| Datas da geração | |

## Analisadores v2 e calibração (26/10/2026)

O primeiro teste (`01_login_claude`) mostrou 7 apontamentos num Login em que todos os campos têm label e todos os botões têm texto. Os 7 eram falsos positivos do analisador v1:

- **Lint `ComposeTextFieldMissingLabel`:** a regra procurava o argumento `label` como `UNamedExpression`, que o UAST só usa em anotações. Por isso acusava todo `TextField`/`OutlinedTextField`, com ou sem label. A v2 usa o mapeamento argumento → parâmetro da chamada resolvida (`computeArgumentMapping`), com o PSI do Kotlin como reserva. A checagem de `contentDescription` de `Icon`/`Image` também passou a usar esse mapeamento; antes ela só funcionava pela posição do argumento.
- **ST/TT/CT:** eram uma checagem própria que só lia o texto do próprio nó. No Compose, o texto de `Button { Text() }` e a descrição do ícone de um `IconButton` ficam no nó filho, então todo botão virava erro ST. A v2 roda as três checagens da **biblioteca ATF oficial do Google (4.1.1)** sobre a árvore `AccessibilityNodeInfo`. O ATF lê o texto dos filhos não focáveis, como o TalkBack. O alvo de toque passa de 44dp para o padrão do ATF, **48dp**.
- **O que conta:** todo resultado ERROR do ATF. Para CT, conta o resultado de contraste estimado pelo screenshot abaixo do mínimo (`TEXTVIEW_HEURISTIC_CONTRAST_NOT_SUFFICIENT`). O ATF o marca como WARNING porque, no Compose, só consegue estimar a cor do texto. Os avisos "borderline" não contam.

Cada relatório agora traz `meta.analyzer`, e o CSV ganhou as colunas `analisador_antes` e `analisador_depois`. Ao analisar de novo o mesmo teste, a grade e o CSV passam a usar a análise mais recente.

**Antes de seguir a bateria**, no Modo Teste (seção "Telas de validação"):

| Tela | O que mede | Esperado | Obtido |
|------|-----------|----------|--------|
| `CalibracaoLimpaScreen` | Falsos positivos (nada a apontar) | LINT 0 · STATIC 0 · ATF 0 | 0 · 0 · 0 ✔ (26/10) |
| `CalibracaoDefeitosScreen` | Cada defeito plantado é encontrado, e só ele | LINT 2 (1 TF + 1 IN) · STATIC 3 · ATF 4 (ST 2 · TT 1 · CT 1) — v2.1: STATIC 4 · ATF 3 | LINT 2 ✔ · STATIC 3 ✔ · ATF 3: ST 2 ✔ · CT 1 ✔ (1,67:1) · **TT 0 ✘** (26/10) |
| `CalibracaoCoberturaScreen` | Cobertura: cada regra em variações de escrita, com controles, pontos cegos e casos de política (gabarito no cabeçalho da tela) | LINT 7 · STATIC 12 · ATF 9 (ST 7 · CT 2 · TT 0); A3 e T3 "a medir"; pontos cegos X1–X4: 0 | v2.2: ST 1 de 7 ✘ → v2.3: ST 7 ✔ · CT 2 ✔ · TT 5, mas 32 itens por contagem duplicada → **v2.4 (26/10, 20:39): LINT 7 ✔ · STATIC 12 ✔ · ATF 14 ✔ (ST 7 · TT 5 · CT 2) · pontos cegos e controles 0 ✔ — calibrada** |
| `01_login_claude` (código já salvo no relatório) | Refazer o teste 1 com a v2 | perto de 0 | |

A tela de cobertura já achou um defeito antes de rodar: o scanner estático não lia o `contentDescription` passado por posição. Ele relatava `Icon(vetor, null)` como "descrição ausente" e não apontava o IconButton desse ícone. Foi corrigido na v2.2.

**Rodada de cobertura (26/10, v2.2):** o lint e o scanner bateram item por item, e nenhum ponto cego nem controle foi apontado. O ATF perdeu todo o topo da tela: os 6 apontamentos ST esperados nos campos A1/A2 e nos botões B1–B3. Também trouxe dois resultados em elementos cortados na borda depois da rolagem: um ST no controle "Dismiss" e um TT de 42dp. Causa: o teste só se conectava ao serviço de acessibilidade na primeira leitura. O Compose só monta a árvore de acessibilidade depois dessa conexão, então a primeira leitura (o topo) vinha vazia. Nas telas que não rolam isso não aparecia, porque as leituras seguintes viam a mesma tela. Na v2.3, o teste conecta antes, espera a árvore ficar estável, rola em passos lentos e sobrepostos até o fim do conteúdo e ignora elementos cortados pela borda da rolagem. Cada leitura deixa uma linha de diagnóstico em `atf_issues.diagnostics` no relatório. **Os relatórios v2/v2.2 de telas com rolagem subcontam o ST: refazer.**

**Rodada de cobertura (26/10, v2.3):** a primeira leitura passou a funcionar (57 nós), e o ATF achou exatamente os 7 ST plantados, sem apontar nenhum controle. Também achou os 2 CT e nenhum dos pontos cegos. Mas reportou 32 itens para 14 elementos únicos: com leituras sobrepostas, o mesmo elemento aparece em posições diferentes da tela, e a deduplicação usava a posição na tela. Na v2.4, o teste mede quanto o conteúdo rolou entre as leituras e deduplica pela posição no conteúdo. A simulação com as posições desse relatório dá 14 (ST 7 · TT 5 · CT 2). Itens "a medir": o campo só com placeholder (A3) não é apontado pelo ATF. O TT do ATF apontou T2, T3 (×3) e T4, mas não o T1: o Compose amplia a área de toque só até onde os vizinhos deixam. **A v1, que usava rolagens rápidas, também pode ter contado elementos em dobro nas telas que rolam.**

Se uma tela de calibração divergir do esperado, anotar aqui e não seguir a bateria até entender o motivo.

**Divergência TT (26/10):** o `Box` clicável de 24dp (D3) não foi apontado. Os controles corretos (campo com label, IconButton com descrição, Button com texto) não foram apontados, e os outros defeitos plantados foram encontrados nas linhas certas. Explicação mais provável, ainda não confirmada no aparelho: o Compose estende a área de toque de elementos clicáveis pequenos até 48dp e informa esses limites estendidos à árvore de acessibilidade. Assim o ATF mede 48dp. Consequência: com o ATF, o TT praticamente não dispara em telas Compose. O gabarito (ATF TT 1) não foi alterado depois do resultado.

**Decisão (26/10): TT medido no código (v2.1).** A ampliação automática do Compose não deve esconder um alvo de toque declarado abaixo de 48dp. Por isso foi criada a regra estática `ComposeSmallTouchTarget`, que entra na coluna **`TT_static`** do CSV:
- aponta `clickable`/`toggleable`/`selectable`/`combinedClickable` cujo tamanho declarado (`size`, `width`, `height`, também `required*`) fica abaixo de 48dp em alguma dimensão, respeitando a ordem dos modificadores: o tamanho mais externo vale, e o padding entre esse tamanho e o `clickable` reduz a área;
- aponta componentes interativos do Material (IconButton, Button, Checkbox, Switch…) com `modifier` abaixo de 48dp, exceto quando o callback é `null`;
- não aponta tamanhos não literais (variáveis), `fillMax*`, `heightIn(min = …)` nem componentes sem tamanho declarado (os padrões do Material já reservam 48dp);
- conta ocorrências no código. O ATF conta elementos renderizados: um `IconButton` dentro de `repeat(4)` vale 1 aqui e 4 no ATF.

A coluna `TT` (ATF) continua no CSV para registro. Gabarito atualizado da tela de defeitos: STATIC 4 (inclui 1 TT) · ATF 3 (ST 2 · CT 1). Para validar a v2.1, rodar a `CalibracaoDefeitosScreen` mais uma vez.

**Atenção:** os números do WebMedia e do `CORRECTION_LOG.md` foram medidos com a v1. Conferir antes de citá-los no CHASE.

**Validade de um resultado 0 (v2.5, 26/10):** o teste do ATF passou a devolver sempre o diagnóstico de cada leitura, mesmo sem apontamentos. Antes, um 0 não provava que a tela tinha sido lida, e na v2.2 a primeira leitura vinha vazia. Regra: uma análise só vale se a primeira leitura tiver nós do app ("pass 1: N nodes", N > 1). O Modo Teste mostra isso abaixo do resultado, e o CSV traz as colunas `leitura_atf_antes` e `leitura_atf_depois` ("ok" ou "SEM DIAGNÓSTICO"). Login, Registro e Perfil (Claude), analisados na v2.4, devem ser refeitos.

**Analisador v2.6 (26/10, antes de recomeçar a bateria):** a revisão manual do Perfil do Claude, que deu 0 na v2.5, mostrou problemas reais fora das regras. Dois deles já estavam declarados como pontos cegos na tela de cobertura (X1 e X2). Entraram quatro regras estáticas, todas com base em diretrizes:

| Regra | Aponta | Base |
|---|---|---|
| `ComposeMissingHeading` | `Text` com estilo `display*`/`headline*` sem `semantics { heading() }` | WCAG 1.3.1; guia de acessibilidade do Android |
| `ComposeVagueContentDescription` | descrição vazia, com jargão ("placeholder") ou que nomeia o tipo do elemento ("icon", "image", "button"…) | WCAG 1.1.1; o Android desaconselha incluir o tipo do elemento na descrição |
| `ComposeFocusLossOnToggle` | `if/else` cujo botão muda a condição e some da tela, sem `FocusRequester` nem `liveRegion` | WCAG 2.4.3 e 4.1.3 |
| `ComposeDisabledFieldWithValue` | campo desabilitado por um estado, sem `readOnly`, mostrando dados | **além da WCAG** (controles desabilitados são isentos de 1.4.3): coluna `beyond_wcag`, **fora** de `static` e `total` |

Colunas novas no CSV: `heading`, `desc`, `focus`, `beyond_wcag`. Gabarito da tela de cobertura: STATIC 17 (+1 além da WCAG) e ATF 14; as telas limpa e de defeitos continuam com 0 e 4. O prompt de correção v5 continua congelado e não cita essas categorias, então o reparo delas deve ser reportado separado. Continuam fora do instrumento: estado não anunciado (X3), gesto invisível ao TalkBack (X4), descrição redundante com o texto vizinho (X5), propósito dos campos (WCAG 1.3.5, sem API na versão do Compose do projeto) e perda de foco fora do padrão if/else. **A bateria recomeça do zero na v2.6.**

**Contagem dupla numa re-análise (v2.9, 28/10):** a re-análise do `04_user_profile_chatgpt` deu CT 8: os mesmos 4 rótulos contados em duas passadas. O diagnóstico registrou "scrolled 0px" numa passada em que a tela já tinha rolado 446 px. A rolagem era medida numa leitura separada da árvore de acessibilidade, que saiu desatualizada (cache do Android), enquanto o ATF leu a árvore atual. Na v2.9, a rolagem e o fim do conteúdo são medidos na mesma árvore em que o ATF roda. Com as posições daquele relatório, a nova contagem dá 4. Na bateria, só telas com 2 ou mais resultados do ATF podem ser afetadas (os três Perfis). O Perfil do Claude e o do Gemini têm CT 4, um por campo, o que é compatível com contagem correta. A re-análise do Perfil do ChatGPT foi refeita na v2.9.

**Modo claro forçado (v2.8, 27/10):** o `01_login_chatgpt` deu 2 violações de contraste (1,6:1, texto #CAC4D0 sobre #F8F7FC) que não existem no código do ChatGPT. O celular estava no modo escuro. O pré-processador faz o `MaterialTheme` seguir o tema do sistema, então os rótulos ganharam a cor do tema escuro sobre o fundo claro que o ChatGPT fixou. Agora o pipeline põe o celular no modo claro (`adb shell cmd uimode night no`) antes de cada ATF, grava o modo em `atf_issues.ui_mode` e invalida a leitura (Modo Teste e CSV) se o modo não for "claro". A comparação claro × escuro fica como trabalho futuro: o prompt proíbe a IA de definir tema, então o modo escuro mediria a injeção da Melodie, não o código gerado.

**Pré-processador v2 (27/10):** o `01_login_chatgpt` falhou na compilação por culpa da Melodie. O ChatGPT declarou `val backgroundColor = Color(…)`, e a correção automática de Material 2 (`backgroundColor =` → `containerColor =`) renomeou a declaração, deixando `color = backgroundColor` sem definição. Uma falha assim seria atribuída à IA. A auditoria das correções automáticas achou o mesmo risco em mais quatro:
- `disabled =` também renomeava variáveis;
- `Color Gray` → `Color.Gray` alterava textos entre aspas;
- `Text(` recebia `text = ""` mesmo quando já tinha `text =` mais adiante (erro de argumento duplicado);
- `''` → `""` quebrava textos como "Don''t".

Agora as renomeações só valem para argumentos nomeados e nunca quando o próprio código declara aquele nome; as outras correções não tocam em strings. Há 11 testes garantindo que o código válido sai intacto. Regra para a bateria: **se uma tela não compilar, conferir primeiro se a mensagem "fixed …" do pré-processador tem relação com o erro**, antes de atribuir a falha à IA.

**Decisão de método (26/10):** todo `Icon`/`Image` com `contentDescription = null` conta como violação, inclusive o ícone decorativo ao lado de um texto (caso P1 da tela de cobertura). Critério conservador: o analisador não decide se o ícone é decorativo, e todo `null` exige revisão humana. Como as diretrizes do Android aceitam `null` em ícones decorativos, o artigo deve declarar esse critério e, se houver espaço, mostrar o resultado também sem os casos decorativos (análise de sensibilidade).

## Regras de geração (iguais para os 3 modelos)

1. Uma conversa nova por tela, sem histórico.
2. Memória e instruções personalizadas desativadas (ou conta sem personalização).
3. Colar o arquivo de `prompts/bateria_chase2027/` inteiro, sem editar.
4. Usar a **primeira** resposta. Não regenerar nem pedir ajustes de conteúdo.
   **Exceção, falha de compilação (decidido em 27/10):** se a resposta não compilar por erro da IA, colar no **mesmo chat** o prompt de reparo da Melodie (botão "Copiar prompt de reparo" no Modo Teste), até **2 vezes**. É o mesmo texto do `SELF_REPAIR` automático do pipeline (`src/repair_prompt.py`): os erros de compilação e o código que falhou, com a instrução de corrigir só esses erros. A tentativa fica em `meta.repair_attempt` e na coluna `tentativas_reparo` do CSV (0 = compilou de primeira). Após 2 reparos sem compilar, a tela entra como falha de compilação. Antes de usar o reparo, conferir se o erro não veio do pré-processador (ver "Pré-processador v2").
5. Salvar o código como `{NN}_{tela}_{modelo}.kt` (ex.: `01_login_claude.kt`) e guardar a resposta completa.

## Passo a passo na Melodie

1. **Modo Teste** (`/teste`): escolha a tela e a IA (ou clique na célula da grade "Bateria CHASE 2027"). O nome do teste é preenchido sozinho, ex.: `01_login_claude`. Use "Copiar prompt", gere no chat, cole a primeira resposta e clique em **Compilar e analisar**.
2. No resultado, clique em **Corrigir este relatório →**: a Correção abre com esse relatório já selecionado. Rode a correção (Qwen3-Coder no Tech3Lab). Se o token ou a VPN falharem, a tela agora mostra **Erro** em vez de "concluída".
3. A aba **Re-análise** já vem com o arquivo recém-corrigido selecionado (`01_login_claude_corrigido.kt`). Clique em **Iniciar re-análise**.
4. A grade do Modo Teste marca cada etapa (roxo = analisado, rosa = corrigido, verde = re-analisado). **Exportar CSV** gera a tabela com antes, depois, redução % e regressão para as 30 telas.

Arquivos gerados (nada é sobrescrito; repetições ganham `_2`, `_3`):

| Etapa | Arquivo |
|-------|---------|
| Análise | `outputs/reports/report_<nome>_<data>.json` |
| Correção | `outputs/codes/<nome>_corrigido.kt` + `<nome>_corrigido.meta.json` (origem, modelo, versão do prompt, contagens de antes) |
| Re-análise | `outputs/reports/reanalise_<nome>_<data>.json` (aponta para o relatório original e o arquivo corrigido) |

Os arquivos corrigidos podem ser renomeados na aba Re-análise (✎); a ligação com os relatórios é mantida.

## Resultados

**Resultado final (28/10/2026):** dados em `results/bateria_chase2027_final.csv` (export da Melodie). Análises na v2.8; re-análises na v2.8, exceto o Perfil do ChatGPT, refeito na v2.9.

| | Claude | ChatGPT | Gemini | Total |
|---|---|---|---|---|
| Compilou de primeira | 10/10 | 9/10 | 8/10 | 27/30 (3 com 1 reparo) |
| Telas sem violação | 1 | 0 | 2 | 3 |
| Defeitos antes (únicos no código + ATF, 30 telas) | 18 | 34 | 30 | 82 |
| …dos quais ícones/imagens decorativos `null` | 0 | 12 | 12 | 24 |

Correção (Qwen3-Coder, prompt v5) nas 26 telas cujo código corrigido compilou (1 de 27 não compilou: Perfil do Claude):

| | Claude (8) | ChatGPT (10) | Gemini (8) | Total (26) |
|---|---|---|---|---|
| Defeitos únicos + ATF, antes → depois | 11 → 1 (−91%) | 34 → 10 (−71%) | 30 → 9 (−70%) | **75 → 20 (−73%)** |
| Sem os decorativos (sensibilidade) | 11 → 1 (−91%) | 22 → 10 (−55%) | 18 → 9 (−50%) | 51 → 20 (−61%) |
| Total bruto (com dupla contagem) | 12 → 1 | 48 → 10 | 45 → 9 | 105 → 20 (−81%) |
| Telas limpas depois | 7 | 5 | 4 | 16 de 26 |

Resultado por tela: 16 limpas, 9 parciais, 1 sem efeito, 1 falha de build e 3 sem violações. Seis telas ganharam defeito novo com a correção: descrição ruim em 5 (provável influência do exemplo `"Play button"` do prompt v5) e contraste 0 → 4 no Perfil do ChatGPT (o Qwen pôs rótulos dentro de campos desabilitados e não usou `readOnly`). A falha de build do Perfil do Claude veio de `liveRegion = "texto"` (o tipo certo é `LiveRegionMode`), provavelmente induzida pela dica da regra `ComposeFocusLossOnToggle`. Por categoria (antes nas 30 → depois nas 26): título sem heading 25 → 2; descrição ruim 9 → 6; perda de foco 3 → 2; TT estático 3 → 0; TT ATF 3 → 2; CT 8 → 8; ST 0 → 0.

### Tabela por tela (modelo original)

Legenda: ST = SpeakableText · TT = TouchTarget · CT = TextContrast · Lint = regras estáticas A11Y · Static = scanner Compose

| # | Tela | Modelo | Relatório análise | Build | ST | TT | CT | Lint | Static | Relatório reanálise | Build | ST | TT | CT | Lint | Static | Obs. |
|---|------|--------|-------------------|-------|----|----|----|------|--------|---------------------|-------|----|----|----|------|--------|------|
| 1 | 01 Login | Claude | | | | | | | | | | | | | | | |
| 2 | 01 Login | ChatGPT | | | | | | | | | | | | | | | |
| 3 | 01 Login | Gemini | | | | | | | | | | | | | | | |
| 4 | 02 Registration | Claude | | | | | | | | | | | | | | | |
| 5 | 02 Registration | ChatGPT | | | | | | | | | | | | | | | |
| 6 | 02 Registration | Gemini | | | | | | | | | | | | | | | |
| 7 | 03 Product Details | Claude | | | | | | | | | | | | | | | |
| 8 | 03 Product Details | ChatGPT | | | | | | | | | | | | | | | |
| 9 | 03 Product Details | Gemini | | | | | | | | | | | | | | | |
| 10 | 04 User Profile | Claude | | | | | | | | | | | | | | | |
| 11 | 04 User Profile | ChatGPT | | | | | | | | | | | | | | | |
| 12 | 04 User Profile | Gemini | | | | | | | | | | | | | | | |
| 13 | 05 Music Player* | Claude | | | | | | | | | | | | | | | |
| 14 | 05 Music Player* | ChatGPT | | | | | | | | | | | | | | | |
| 15 | 05 Music Player* | Gemini | | | | | | | | | | | | | | | |
| 16 | 06 Navigation Drawer | Claude | | | | | | | | | | | | | | | |
| 17 | 06 Navigation Drawer | ChatGPT | | | | | | | | | | | | | | | |
| 18 | 06 Navigation Drawer | Gemini | | | | | | | | | | | | | | | |
| 19 | 07 Video Player | Claude | | | | | | | | | | | | | | | |
| 20 | 07 Video Player | ChatGPT | | | | | | | | | | | | | | | |
| 21 | 07 Video Player | Gemini | | | | | | | | | | | | | | | |
| 22 | 08 Post Feed | Claude | | | | | | | | | | | | | | | |
| 23 | 08 Post Feed | ChatGPT | | | | | | | | | | | | | | | |
| 24 | 08 Post Feed | Gemini | | | | | | | | | | | | | | | |
| 25 | 09 Banking Home | Claude | | | | | | | | | | | | | | | |
| 26 | 09 Banking Home | ChatGPT | | | | | | | | | | | | | | | |
| 27 | 09 Banking Home | Gemini | | | | | | | | | | | | | | | |
| 28 | 10 Notifications | Claude | | | | | | | | | | | | | | | |
| 29 | 10 Notifications | ChatGPT | | | | | | | | | | | | | | | |
| 30 | 10 Notifications | Gemini | | | | | | | | | | | | | | | |

\* O prompt de reparo v5 foi desenvolvido no Music Player. Reportar essas 3 linhas à parte da métrica principal.

## Validação com TalkBack (amostra)

| Tela | Modelo | Antes: o que o leitor anuncia | Depois: o que o leitor anuncia |
|------|--------|-------------------------------|--------------------------------|
| | | | |
