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
| **Bosses** | Contagem regressiva dos bosses do Abismo (Nahma, Executores, Vigia Kaira), do Cerco de Artefato e da Fenda. |
| | Timer de respawn dos bosses de campo (Immortal Gartua, Lagta, Dartan, Kashapa, Danar): marque quando o boss morreu. |
| | **Alerta com som e notificação do Windows 5 minutos antes** (ajustável). Ligado por padrão para Nahma, Executores, Vigia Kaira e Immortal Gartua. |
| **Personagens** | Cole o link do perfil no Shugo.GG ou no AION2 Index. O app lê Combat Power, Gear score / Item level, classe e nível. |
| | Gráfico de evolução de CP e de equipamento, com o ganho desde a primeira leitura. Atualiza sozinho a cada 6 horas (ajustável). |
| **Ajustes** | Antecedência do alerta, som, notificação, sempre no topo, fechar para a bandeja e relógio da região. |

Ao fechar a janela, o app fica no **ícone da bandeja** (perto do relógio) e os alertas continuam funcionando. Para sair de vez: clique com o botão direito no ícone → **Sair**.

### Links de perfil aceitos

```
https://shugo.gg/character/global/la-siel/SeuNome
https://aion2index.com/c/la/siel/SeuNome
```

O Shugo.GG mostra **Gear score** e o AION2 Index mostra **Item level**. São métricas diferentes: use sempre o mesmo site para o mesmo personagem.

### Horários

Os eventos do Abismo seguem o relógio do servidor. Na América Latina, isso é o horário de Brasília. Nahma e Vigia Kaira estão marcados como **não confirmados**, porque os guias da comunidade divergem; se o aviso do jogo disser outro horário, vale o jogo. Bosses de campo não têm horário fixo: eles renascem um tempo depois de morrer, por isso o timer depende de alguém marcar a morte.

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

1. Atualize `__version__` em `daeva/__init__.py` (ex.: `1.1.0`).
2. Na primeira vez, preencha `GITHUB_REPO` no mesmo arquivo com `seu-usuario/diario-de-daeva`, para o app avisar os amigos quando sair versão nova.
3. Commit e tag:
   ```bash
   git commit -am "Versão 1.1.0"
   git tag v1.1.0
   git push && git push origin v1.1.0
   ```
4. O GitHub Actions roda os testes, gera o `DiarioDeDaeva.exe` e publica na Release. Leva uns 5 minutos.

### Onde mexer

| Arquivo | Conteúdo |
|---|---|
| `daeva/schedule.py` | Horários dos bosses e eventos, bosses de campo e tempos de respawn |
| `daeva/profiles.py` | Leitura dos perfis no Shugo.GG e no AION2 Index |
| `daeva/store.py` | Dados salvos e ajustes padrão |
| `daeva/main_window.py` | Interface, alertas e bandeja |
| `tools/gerar_assets.py` | Gera o som de alerta e o ícone |

Se um dos sites mudar o formato da página, o leitor em `profiles.py` é o lugar a ajustar; os testes em `tests/test_core.py` têm exemplos das páginas.

*Projeto de fã, sem ligação com a NCSOFT, o Shugo.GG ou o AION2 Index.*
