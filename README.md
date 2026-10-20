# Diário de Daeva

Companheiro de **AION 2** para PC: acompanha o Combat Power e o equipamento dos seus personagens e avisa com som antes dos bosses.

Feito para a galera que joga junto em **Siel (América Latina)**, mas funciona em qualquer servidor Global.

## Baixar

1. Vá em **[Releases](../../releases/latest)** e baixe o `DiarioDeDaeva.exe`.
2. Abra o arquivo. Não precisa instalar.
3. Na primeira vez, o Windows pode mostrar **“O Windows protegeu o computador”**, porque o app não tem assinatura digital paga. Clique em **Mais informações → Executar assim mesmo**.

## O que ele faz

| Aba | Recurso |
|---|---|
| **Hoje** | O próximo boss com contagem grande e trilha pontilhada (com **Morreu agora** e **Quanto falta** ali mesmo), CP e gear score, energia Odyle, a fila dos próximos eventos e o título alvo. |
| **Bosses** | Contagem regressiva dos bosses do Abismo (Nahma, Executores, Vigia Kaira), do Cerco de Artefato e da Fenda. |
| | Timer de respawn dos bosses de campo (Eternal Gartua, Immortal Gartua, Lagta, Dartan, Kashapa, Danar): use **Quanto falta…** com a contagem do mapa do jogo (Exploração → Field Boss), ou **Morreu agora**. |
| | **Festival Shugo** (toda hora cheia) e **Invasão Dimensional** (toda hora e meia), com contador de chaves por personagem: Shugo +3 por dia até 12 (21 com Membership), Invasão +1 por dia até 7. Também reset diário e semanal. |
| | **Alerta com som e notificação do Windows** 5 minutos antes dos bosses e 2 minutos antes de Shugo e Invasão (ajustável), com **Não perturbe** das 00:00 às 08:00 só para os eventos de toda hora. |
| **Personagens** | Cole o link do perfil no Shugo.GG ou no AION2 Index. O app lê Combat Power, Gear score / Item level, classe e nível. |
| | Gráfico de evolução de CP e de equipamento, com o ganho desde a primeira leitura. Atualiza sozinho a cada 6 horas (ajustável). |
| **Personagens** | Resumo do equipamento (com refino) e das skills ativas, passivas e stigmas. |
| | **Energia Odyle** por personagem: informe o valor uma vez e o app conta 5 por hora até 560 (840 com Membership, que vale para a conta toda). A lista de todos os personagens mostra a energia de cada alt e quando enche. |
| **BiS** | Reconhece a classe do personagem e compara com a build da classe no [Atreia Lens](https://atreialens.hartmannlab.xyz): nível de cada skill, stigmas, tipo e refino das arcanas, os 5 substatus de cada peça de equipamento, asas, títulos e notas da build. |
| **Títulos** | As 192 conquistas que dão título, com os bônus de cada um, filtradas pela sua facção. Sugere os melhores títulos que faltam conforme a prioridade (Ataque PvE, Ataque PvP ou Defesa) e acompanha o progresso do título que você escolher como alvo. |
| **Ajustes** | **8 temas** (Elyos, Asmodiano, Pixel, Madrugada, OLED, Terminal, Gótico e Sumi claro ou escuro), tamanho do texto, modo compacto e cor de destaque. **Som próprio** (WAV ou MP3) para cada tipo de aviso, com volume. Antecedência dos alertas, notificação, sempre no topo, fechar para a bandeja e relógio da região. |
| **Grupo** | Com o bot do Discord, a morte do Gartua marcada por qualquer amigo (no app ou com `/gartua`) aparece para todos, e o bot avisa no canal. Veja [docs/BOT.md](docs/BOT.md). |

Ao fechar a janela, o app fica no **ícone da bandeja** (perto do relógio) e os alertas continuam funcionando. Para sair de vez: clique com o botão direito no ícone → **Sair**.

### Links de perfil aceitos

```
https://shugo.gg/character/global/la-siel/SeuNome
https://aion2index.com/c/la/siel/SeuNome
```

O Shugo.GG mostra **Gear score** e o AION2 Index mostra **Item level**. São métricas diferentes: use sempre o mesmo site para o mesmo personagem.

### Horários

Os eventos do Abismo seguem o relógio do servidor. Na América Latina, isso é o horário de Brasília. Nahma e Vigia Kaira estão marcados como **não confirmados**, porque os guias da comunidade divergem; se o aviso do jogo disser outro horário, vale o jogo. Bosses de campo não têm horário fixo: eles renascem um tempo depois de morrer. O jeito mais preciso é copiar a contagem que o mapa do jogo mostra em Exploração → Field Boss.

## É seguro para a conta?

O app **não toca no jogo**: não lê memória, não captura pacotes, não injeta nada e não pede login. Ele só abre a página pública do personagem no Shugo.GG ou no AION2 Index, como um navegador faria, no máximo uma vez a cada poucas horas. Os dados ficam no seu PC, em `%APPDATA%\DiarioDeDaeva\dados.json`.

---

## Para quem mantém o projeto

Rodar a partir do código (Windows, Python 3.12+):

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt pytest
python -m pytest
python app.py
```

### Publicar uma versão nova

1. Troque `__version__` em `daeva/__init__.py` (ex.: `1.2.0`).
2. Envie para a `main`. O GitHub Actions roda os testes, gera o `DiarioDeDaeva.exe` e cria a Release `v1.2.0` sozinho, em uns 3 minutos.
3. O app de quem já tem uma versão anterior mostra o botão "Versão 1.2.0 disponível".

Mudanças só no bot (`bot/`) ou na documentação não geram `.exe` novo.

### Onde mexer

| Arquivo | Conteúdo |
|---|---|
| `daeva/schedule.py` | Horários dos bosses e eventos, bosses de campo e tempos de respawn |
| `daeva/profiles.py` | Leitura dos perfis no Shugo.GG e no AION2 Index |
| `daeva/store.py` | Dados salvos e ajustes padrão |
| `daeva/main_window.py` | Interface, alertas e bandeja |
| `daeva/theme.py`, `daeva/widgets.py` | Temas (cores e fontes), moldura de grimório e trilhas pontilhadas |
| `daeva/progress.py` | Energia Odyle e chaves do Shugo e da Invasão |
| `daeva/bis.py`, `daeva/bis_tab.py` | Comparação com a build da classe e a aba BiS |
| `daeva/data/bis.json` | Builds das 8 classes (gerado por `tools/gerar_bis.py` a partir das páginas do Atreia Lens em `tools/bis_fontes/paginas/`) |
| `assets/fonts/` | Fontes dos temas (Google Fonts, licença OFL) |
| `daeva/titles.py`, `daeva/titles_tab.py` | Conquistas com título, leitura dos bônus e a aba Títulos |
| `daeva/data/conquistas_titulos.json` | Lista das 192 conquistas (gerada por `tools/gerar_conquistas.py`) |
| `daeva/group.py` | Conversa do app com o bot do grupo |
| `bot/` | Bot do Discord e a API que o app usa (instalação em [docs/BOT.md](docs/BOT.md)) |
| `tools/gerar_assets.py` | Gera o som de alerta e o ícone |

Se um dos sites mudar o formato da página, o leitor em `profiles.py` é o lugar a ajustar; os testes em `tests/test_core.py` têm exemplos das páginas.

### Dados de terceiros

- Combat Power, gear score e equipamento: páginas públicas do [Shugo.GG](https://shugo.gg).
- Item level, skills e contagem de títulos: páginas públicas do [AION2 Index](https://aion2index.com).
- Builds da aba BiS: [Atreia Lens](https://atreialens.hartmannlab.xyz) (atreialens.hartmannlab.xyz), feito pela comunidade. Para atualizar uma classe, copie a página dela inteira (Ctrl+A, Ctrl+C) para `tools/bis_fontes/paginas/<classe>.txt` e rode `python tools/gerar_bis.py`.
- Conquistas e títulos: [MetaBot.GG](https://metabot.gg/en/aion-2/achievements), que permite o reaproveitamento com crédito e link para a fonte ([metabot.gg/en/ai](https://metabot.gg/en/ai)). O app mostra esse link em cada título e lê os bônus devagar (1 página por segundo), uma vez a cada 14 dias.

O jogo não informa a ninguém de fora quais títulos você tem nem o progresso das conquistas. Por isso essa parte é marcada à mão, olhando o diário de conquistas do jogo.

*Projeto de fã, sem ligação com a NCSOFT, o Shugo.GG, o AION2 Index, a MetaBot.GG ou o Atreia Lens.*
