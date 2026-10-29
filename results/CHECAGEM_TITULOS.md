# Checagem manual dos 25 títulos apontados (`ComposeMissingHeading`)

Gerado a partir dos 30 relatórios de análise do CSV final. Pergunta para cada linha: **o texto é um título de tela/seção que um usuário de leitor de tela gostaria de alcançar pela navegação por títulos?**

For each item, decide whether the text is a **section/screen title** (a heading a screen-reader user would want to jump to). Mark `Sim` (is a heading), `Não` (not a heading) or `?` (unsure). The code context is the `Text(...)` call as generated.

| # | Screen | Generator | Line | Text | Style | Enclosing element | Pré-avaliação (confirme ou corrija) |
|---|---|---|---|---|---|---|---|
| 1 | 01_login | ChatGPT | 81 | `"Welcome Back!"` | headlineLarge | Column | Sim |
| 2 | 01_login | Claude | 78 | `"Welcome Back"` | headlineLarge | Column | Sim |
| 3 | 01_login | Gemini | 77 | `"Welcome Back"` | headlineLarge | Column | Sim |
| 4 | 02_registration | ChatGPT | 85 | `"Create Account"` | headlineMedium | Column | Sim |
| 5 | 02_registration | Claude | 86 | `"Create Account"` | headlineMedium | Column | Sim |
| 6 | 02_registration | Gemini | 96 | `"Create Account"` | headlineLarge | Column | Sim |
| 7 | 03_product_details | ChatGPT | 171 | `productName` | headlineSmall | Column | Sim (nome do produto como título da página) |
| 8 | 03_product_details | Claude | 85 | `"Aurora Wireless Headphones"` | headlineMedium | Box | Sim (nome do produto como título da página) |
| 9 | 03_product_details | Gemini | 99 | `"Wireless Noise-Canceling Headphones"` | headlineMedium | Row | Sim (nome do produto como título da página) |
| 10 | 04_user_profile | ChatGPT | 100 | `"My Profile"` | headlineMedium | Column | Sim |
| 11 | 04_user_profile | Claude | 86 | `"My Profile"` | headlineMedium | Column | Sim |
| 12 | 04_user_profile | Gemini | 92 | `"User Profile"` | headlineMedium | Column | Sim |
| 13 | 05_music_player | ChatGPT | 194 | `currentTrack.title` | headlineSmall | Column | ? (título da faixa: conteúdo principal, não título de seção) |
| 14 | 05_music_player | Claude | 135 | `currentTrack.title` | headlineSmall | — | ? (título da faixa: conteúdo principal, não título de seção) |
| 15 | 05_music_player | Gemini | 123 | `currentTrack.title` | headlineMedium | — | ? (título da faixa: conteúdo principal, não título de seção) |
| 16 | 06_navigation_drawer | ChatGPT | 275 | `"Welcome to My Store"` | headlineSmall | Column | Sim |
| 17 | 06_navigation_drawer | ChatGPT | 310 | `selectedItem` | headlineMedium | text | Sim (título da área principal: item selecionado no menu) |
| 18 | 06_navigation_drawer | Claude | 155 | `selectedItem` | headlineMedium | Column | Sim (título da área principal: item selecionado no menu) |
| 19 | 06_navigation_drawer | Gemini | 205 | `"Current Screen: $selectedItem"` | headlineMedium | Box | Sim (título da área principal: item selecionado no menu) |
| 20 | 07_video_player | Claude | 90 | `"Video Player"` | headlineMedium | Column | Sim |
| 21 | 08_post_feed | ChatGPT | 587 | `title` | headlineSmall | — | Sim? (título da aba vazia, abaixo do ícone) |
| 22 | 09_banking_home | ChatGPT | 519 | `if (balanceVisible) "$12` | headlineLarge | — | Não (é o valor do saldo, não um título) |
| 23 | 09_banking_home | Claude | 239 | `if (balanceVisible) "$ 12` | headlineLarge | — | Não (é o valor do saldo, não um título) |
| 24 | 09_banking_home | Gemini | 255 | `if (isBalanceVisible) "$12` | headlineLarge | — | Não (é o valor do saldo, não um título) |
| 25 | 10_notifications | ChatGPT | 185 | `"Notifications"` | headlineSmall | Column | Sim |

Total flagged: 25


## Impacto nos números (pela pré-avaliação)

| Cenário | Títulos verdadeiros | Precisão da regra | Defeitos antes (30 telas) | Pareado (26) antes → depois | Redução |
|---|---|---|---|---|---|
| Como está no artigo (25 contam) | 25 | — | 82 | 75 → 20 | −73% |
| A: tirar os 3 saldos (22–24) | 22 | 88% | 79 | 72 → 19 | −74% |
| B: tirar também os 3 títulos de faixa (13–15) | 19 | 76% | 76 | 69 → 18 | −74% |

Os 2 títulos que sobraram depois da correção (Music Player do Gemini e Banking do Claude) são justamente um título de faixa e um saldo. A conclusão do artigo (redução de ~73%, títulos como defeito mais frequente) não muda em nenhum cenário. A frase muda para algo como: "a manual check confirmed 22 (or 19) of the 25 flagged headings; the others were a balance amount and track titles styled as headlines".
