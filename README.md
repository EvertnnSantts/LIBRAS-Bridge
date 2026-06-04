# 🤝 LIBRAS Bridge — Comunicação Hospitalar Acessível

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8%2B-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10%2B-FF6F00?style=for-the-badge&logo=google&logoColor=white)
![License](https://img.shields.io/badge/Licença-MIT-00C9A7?style=for-the-badge)
![Accessibility](https://img.shields.io/badge/Acessibilidade-LIBRAS-0F1B2D?style=for-the-badge)

**Sistema desktop de comunicação bidirecional entre médicos e pacientes surdos**
*utilizando Visão Computacional, MediaPipe e o ecossistema VLibras*

[Sobre o Projeto](#-sobre-o-projeto) • [Arquitetura](#-arquitetura) • [Pré-requisitos](#-pré-requisitos) • [Instalação](#-instalação-passo-a-passo) • [Uso](#-como-usar) • [Treinar Modelo](#-treinar-o-modelo-de-reconhecimento) • [Estrutura](#-estrutura-do-projeto)

</div>

---

## 📋 Sobre o Projeto

O **LIBRAS Bridge** é uma aplicação desktop desenvolvida em Python que elimina a barreira de comunicação entre profissionais de saúde e pacientes surdos em ambientes hospitalares. A aplicação opera em dois módulos complementares:

### Módulo Paciente — LIBRAS → Texto e Áudio

O paciente se posiciona diante de uma webcam e realiza sinais em **LIBRAS (Língua Brasileira de Sinais)**. A aplicação usa **MediaPipe Hands** para detectar em tempo real os 21 pontos-chave (landmarks) de cada mão e um **modelo de Machine Learning** para classificar os gestos e convertê-los em palavras escritas. Cada palavra reconhecida é acumulada na tela formando uma frase e, simultaneamente, sintetizada em voz via **Text-to-Speech** para que o médico possa ouvir.

### Módulo Médico — Texto → LIBRAS

O médico digita diagnósticos, perguntas ou instruções em um campo de texto. O texto é enviado ao **VLibras** — plataforma de código aberto do Governo Federal Brasileiro — que renderiza um avatar 3D executando a tradução completa para LIBRAS. O avatar pode ser visualizado diretamente na interface da aplicação (via WebView embutido) ou no navegador padrão do sistema.

### Pipeline de Reconhecimento

```
Frame de Vídeo (640×480 @ 30fps)
        ↓
 MediaPipe Hands
 (21 landmarks por mão: x, y, z)
        ↓
 Pré-processamento
 (Normalização por pulso + escala)
        ↓
 Classificador ML
 (Random Forest / MLP / SVM)
        ↓
 Confirmação Temporal
 (N frames consecutivos com o mesmo sinal)
        ↓
 Palavra Confirmada → Texto na Tela + TTS (Áudio)
```

---

## 🏗 Arquitetura

O projeto segue o padrão **MVC (Model-View-Controller)** com **Clean Architecture**:

```
libras_bridge/
│
├── main.py                         ← Ponto de entrada (Controller raiz)
│
├── src/
│   ├── core/                       ← Regras de negócio (Model)
│   │   ├── camera_capture.py       ← Gerenciamento da câmera (OpenCV)
│   │   ├── sign_recognizer.py      ← Pipeline MediaPipe + Classificador ML
│   │   └── tts_engine.py           ← Síntese de fala (pyttsx3)
│   │
│   ├── modules/                    ← Casos de uso (Controller por módulo)
│   │   ├── patient/
│   │   │   └── patient_module.py   ← Orquestra: câmera → reconhecimento → TTS
│   │   └── doctor/
│   │       └── doctor_module.py    ← Orquestra: texto → VLibras
│   │
│   ├── ui/                         ← Interface gráfica (View)
│   │   └── main_window.py          ← Janela principal Tkinter (dois painéis)
│   │
│   └── utils/                      ← Infraestrutura compartilhada
│       ├── config.py               ← Configurações globais (AppConfig)
│       └── logger.py               ← Sistema de logging rotativo
│
├── scripts/
│   └── train_model.py              ← Coleta de dados + treinamento do modelo
│
├── tests/
│   └── test_core.py                ← Testes unitários (pytest + unittest.mock)
│
├── models/                         ← Modelos treinados (.pkl) — criado ao treinar
├── data/training/                  ← Dados de treinamento — criado ao coletar
├── logs/                           ← Logs rotativos — criado em execução
│
├── requirements.txt
├── setup.cfg
└── .env.example
```

**Padrões aplicados:**
- **Injeção de Dependências**: módulos recebem `config` e `logger` via construtor
- **Observer (Callbacks)**: módulos notificam a GUI via funções de callback
- **Thread Safety**: captura de câmera e TTS em threads dedicadas com `Lock`
- **Single Responsibility**: cada classe tem uma única responsabilidade bem definida

---

## ✅ Pré-requisitos

### Sistema Operacional

| SO | Suporte | Observações |
|---|---|---|
| **Windows 10/11** | ✅ Completo | TTS usa SAPI5 (vozes nativas em PT-BR) |
| **Ubuntu 22.04+** | ✅ Completo | Instalar espeak: `sudo apt install espeak` |
| **macOS 12+** | ✅ Completo | TTS usa NSSpeechSynthesizer nativo |

### Python

- **Python 3.10 ou superior** (3.11 recomendado)
- Verificar versão: `python --version`
- Download: https://www.python.org/downloads/

### Hardware

- **Webcam** (integrada ou USB) com resolução mínima de 640×480
- **Microfone** não é necessário — apenas câmera e alto-falantes
- **Processador**: qualquer CPU moderna (MediaPipe roda em CPU sem GPU)
- **RAM**: mínimo 4 GB (8 GB recomendado para conforto)

### Conectividade

- **Internet**: necessária apenas para o módulo VLibras (carrega o avatar do servidor do governo)
- O módulo Paciente (câmera + reconhecimento + TTS) funciona **100% offline**

---

## 🚀 Instalação — Passo a Passo

Siga cada etapa na ordem apresentada. Todos os comandos devem ser executados no terminal (Prompt de Comando no Windows, Terminal no macOS/Linux).

### Passo 1 — Clone ou Baixe o Projeto

**Opção A — Via Git (recomendado):**
```bash
git clone https://github.com/seu-usuario/libras-bridge.git
cd libras-bridge
```

**Opção B — Download direto:**
1. Baixe o ZIP do projeto
2. Extraia para uma pasta de sua preferência
3. Abra o terminal **dentro da pasta extraída**

---

### Passo 2 — Crie o Ambiente Virtual (venv)

O ambiente virtual isola as dependências do projeto do restante do seu sistema Python, evitando conflitos de versões entre projetos diferentes.

**No Windows (Prompt de Comando ou PowerShell):**
```cmd
python -m venv venv
```

**No macOS / Linux:**
```bash
python3 -m venv venv
```

> **O que acontece:** Python cria uma pasta `venv/` com um interpretador Python isolado e um diretório `lib/` para instalar pacotes exclusivos deste projeto.

---

### Passo 3 — Ative o Ambiente Virtual

**IMPORTANTE:** O ambiente virtual deve ser ativado a cada nova sessão do terminal.

**No Windows (Prompt de Comando):**
```cmd
venv\Scripts\activate.bat
```

**No Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

> Se receber erro de permissão no PowerShell, execute:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

**No macOS / Linux:**
```bash
source venv/bin/activate
```

**Verificação:** Após ativar, o nome `(venv)` deve aparecer no início da linha do terminal:
```
(venv) C:\Users\seu-usuario\libras-bridge>
```

---

### Passo 4 — Instale as Dependências

Com o ambiente virtual ativo, instale todas as bibliotecas listadas em `requirements.txt`:

```bash
pip install -r requirements.txt
```

> **Tempo estimado:** 2–5 minutos (dependendo da velocidade da internet). O MediaPipe (~50 MB) e o scikit-learn são os maiores downloads.

**Verificar instalação:**
```bash
pip list
```
Você deve ver `opencv-python`, `mediapipe`, `pyttsx3`, `scikit-learn`, `Pillow` e `numpy` na lista.

---

### Passo 5 — Instale o WebView Embutido (Opcional, mas Recomendado)

O `tkinterweb` permite que o avatar VLibras seja renderizado **dentro** da janela da aplicação. Sem ele, o VLibras abre no navegador padrão.

```bash
pip install tkinterweb
```

---

### Passo 6 — Instale o eSpeak no Linux (somente Linux)

No Linux, o `pyttsx3` depende do `espeak` para síntese de fala:

```bash
sudo apt update && sudo apt install espeak espeak-data libespeak-dev -y
```

---

### Passo 7 — Configure as Variáveis de Ambiente

```bash
# Copia o arquivo de exemplo
cp .env.example .env
```

Abra o arquivo `.env` em qualquer editor de texto. As configurações padrão já funcionam sem alteração para a maioria dos casos.

---

### Passo 8 — Crie os Diretórios Necessários

```bash
mkdir -p logs models data/training assets
```

---

### Passo 9 — Verifique a Câmera

Execute este comando rápido para testar se a câmera está acessível:

```bash
python -c "import cv2; cap=cv2.VideoCapture(0); print('Câmera OK' if cap.isOpened() else 'ERRO: câmera não encontrada'); cap.release()"
```

Se aparecer `ERRO`, verifique se a câmera está conectada e não está em uso por outro programa.

---

## ▶️ Como Usar

### Iniciar a Aplicação

Com o ambiente virtual ativo:

```bash
python main.py
```

A janela principal abrirá com os dois módulos lado a lado.

---

### Módulo Paciente (painel esquerdo)

1. **Clique em "▶ Iniciar Câmera"** — a webcam será aberta e o feed aparecerá na tela
2. **O paciente posiciona as mãos** na frente da câmera e realiza sinais em LIBRAS
3. **Os landmarks** (pontos das mãos) aparecerão desenhados em tempo real no feed
4. **Palavras reconhecidas** aparecerão na área "FRASE RECONHECIDA" e serão faladas em voz alta para o médico
5. **"🔊 Falar Frase"** — repete toda a frase acumulada em voz alta
6. **"🗑 Limpar"** — limpa a frase para iniciar uma nova comunicação
7. Para parar a câmera, clique em **"⏹ Parar Câmera"**

> **Modo Demo:** Se o modelo de ML não estiver treinado (`models/sign_classifier.pkl` não existe), a aplicação funciona em modo demonstração com detecções simuladas. Isso permite testar a interface sem necessidade de um modelo real.

---

### Módulo Médico (painel direito)

1. **Digite o texto** no campo de entrada (diagnóstico, pergunta, instrução)
2. **Clique em "🤟 Traduzir para LIBRAS"** ou pressione **Ctrl+Enter**
3. O avatar VLibras executará a tradução em LIBRAS:
   - **Com tkinterweb instalado:** o avatar aparece diretamente na janela
   - **Sem tkinterweb:** use "🌐 Abrir no Navegador" para ver no Chrome/Firefox
4. **Histórico:** as últimas traduções aparecem na lista inferior — dê duplo clique para reusar um texto anterior
5. **"🗑 Limpar"** — limpa o campo de texto

---

## 🧠 Treinar o Modelo de Reconhecimento

O modelo de demonstração é suficiente para testar a interface. Para reconhecimento real de sinais LIBRAS, siga este processo de treinamento:

### Etapa 1 — Coletar Dados por Sinal

Execute o script de coleta para cada sinal que deseja reconhecer:

```bash
# Coleta 200 amostras do sinal "OI"
python scripts/train_model.py --collect --sign OI --samples 200

# Coleta 200 amostras do sinal "DOR"
python scripts/train_model.py --collect --sign DOR --samples 200

# Continue para cada sinal desejado...
python scripts/train_model.py --collect --sign SIM --samples 200
python scripts/train_model.py --collect --sign NAO --samples 200
python scripts/train_model.py --collect --sign AJUDA --samples 200
```

**Instruções durante a coleta:**
- Uma janela com o feed da câmera será aberta
- Posicione sua mão fazendo o sinal correto
- Pressione **[ESPAÇO]** para iniciar a gravação
- Pressione **[ESPAÇO]** novamente para pausar
- Pressione **[Q]** para encerrar quando atingir o número de amostras

**Dicas para boa coleta:**
- Varie levemente a posição e ângulo da mão para cada amostra (mais generalização)
- Colete em diferentes condições de iluminação se possível
- Mínimo recomendado: 100 amostras por sinal; 200+ para melhor precisão

### Etapa 2 — Treinar o Modelo

Após coletar dados de pelo menos 2 sinais diferentes:

```bash
python scripts/train_model.py --train
```

O script irá:
1. Carregar todos os dados de `data/training/`
2. Treinar e comparar 3 algoritmos (Random Forest, MLP, SVM)
3. Exibir métricas de precisão, recall e F1-score
4. Salvar o melhor modelo em `models/sign_classifier.pkl`

### Etapa 3 — Testar o Modelo

Reinicie a aplicação. Se o arquivo `models/sign_classifier.pkl` existir, será carregado automaticamente. O indicador no canto superior do feed da câmera mostrará `MODELO: REAL` em verde.

### Sinais Sugeridos para Contexto Hospitalar

| Sinal | Uso |
|-------|-----|
| `OI` / `TCHAU` | Cumprimentos |
| `SIM` / `NAO` | Respostas básicas |
| `OBRIGADO` | Gratidão |
| `AJUDA` | Solicitação de auxílio |
| `DOR` | Sintoma principal |
| `CABECA` | Localização da dor |
| `BARRIGA` | Localização da dor |
| `FEBRE` | Sintoma |
| `REMEDIO` | Medicamento |
| `AGUA` | Necessidade básica |
| `MEDICO` | Profissional de saúde |
| `BOM` / `MAL` | Estado geral |
| `ONDE` / `QUANDO` | Perguntas |

---

## 🧪 Executar os Testes

### Executar todos os testes:
```bash
pytest tests/ -v
```

### Executar com relatório de cobertura de código:
```bash
pip install pytest-cov
pytest tests/ -v --cov=src --cov-report=html
# Abre o relatório em: htmlcov/index.html
```

### Executar um teste específico:
```bash
pytest tests/test_core.py::TestDoctorModule -v
```

---

## 🔧 Solução de Problemas

### ❌ "Não foi possível abrir a câmera"

**Causas comuns:**
- Webcam em uso por outro programa (feche Zoom, Teams, OBS, etc.)
- Driver da câmera não instalado (Windows: verificar Gerenciador de Dispositivos)
- Permissão de câmera negada (macOS: Preferências do Sistema → Privacidade → Câmera)

**Solução:**
```bash
# Teste qual índice de câmera funciona (tente 0, 1, 2):
python -c "import cv2; cap=cv2.VideoCapture(1); print(cap.isOpened()); cap.release()"
```
Se funcionar com índice 1, altere `CAMERA_INDEX=1` no arquivo `.env`.

---

### ❌ "Erro ao inicializar TTS" / Sem áudio

**No Windows:** Verifique se há vozes em PT-BR instaladas:
- Painel de Controle → Fala → Texto em Fala → vozes disponíveis
- Para instalar voz em PT-BR: Configurações → Hora e Idioma → Fala → Adicionar voz

**No Linux:**
```bash
sudo apt install espeak espeak-data -y
# Teste:
espeak "Olá, teste de voz"
```

**No macOS:** Preferências do Sistema → Acessibilidade → Fala → Voz do Sistema → selecione voz em Português.

---

### ❌ VLibras não carrega / Avatar não aparece

1. **Verifique a conexão com a internet** — o VLibras carrega o avatar do servidor do governo
2. **Use "🌐 Abrir no Navegador"** como alternativa imediata
3. Se usar proxy corporativo, o domínio `vlibras.gov.br` pode estar bloqueado — solicite liberação ao TI
4. Instale o tkinterweb se ainda não instalou: `pip install tkinterweb`

---

### ❌ MediaPipe não detecta as mãos

- **Iluminação insuficiente**: certifique-se de que as mãos estão bem iluminadas
- **Fundo muito complexo**: prefira um fundo neutro (parede branca/cinza)
- **Distância**: mantenha as mãos a 30–80 cm da câmera
- **Óculos de sol**: reflexo em vidros pode interferir
- Ajuste `MP_DETECTION_CONFIDENCE` para um valor menor (ex: `0.5`) no `config.py`

---

### ❌ ImportError ao iniciar

```bash
# Certifique-se de que o ambiente virtual está ativo:
# Windows:
venv\Scripts\activate.bat
# Linux/macOS:
source venv/bin/activate

# Reinstale as dependências:
pip install -r requirements.txt
```

---

## 📦 Dependências Principais

| Biblioteca | Versão | Finalidade |
|---|---|---|
| `opencv-python` | ≥ 4.8 | Captura de câmera e processamento de frames |
| `mediapipe` | ≥ 0.10 | Detecção de landmarks de mãos em tempo real |
| `numpy` | ≥ 1.24 | Operações matemáticas em arrays |
| `Pillow` | ≥ 10.0 | Conversão de frames para exibição no Tkinter |
| `pyttsx3` | ≥ 2.90 | Síntese de fala offline (Text-to-Speech) |
| `scikit-learn` | ≥ 1.3 | Treinamento e inferência do classificador |
| `tkinterweb` | ≥ 3.23 | WebView embutido para o avatar VLibras (opcional) |
| `requests` | ≥ 2.31 | Requisições HTTP para APIs REST (uso futuro) |

---

## 🌐 Sobre o VLibras

O **VLibras** é um conjunto de ferramentas de código aberto desenvolvido pelo **Laboratório de Aplicações de Vídeo Digital (LAVID)** da **UFPB** em parceria com o **Ministério da Gestão e da Inovação em Serviços Públicos** do Governo Federal Brasileiro.

- Site oficial: https://vlibras.gov.br/
- Repositório: https://github.com/spbr/vlibras-player
- Documentação da API: https://vlibras.gov.br/doc/

O uso do VLibras é **gratuito e de código aberto**, conforme a [Licença Pública Geral GNU v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

---

## 📜 Licença

Este projeto está licenciado sob a **Licença MIT**. Veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Faça um **fork** do repositório
2. Crie uma branch para sua feature: `git checkout -b feature/novo-sinal`
3. Faça seus commits seguindo o padrão: `git commit -m "feat: adiciona reconhecimento do sinal X"`
4. Envie para o fork: `git push origin feature/novo-sinal`
5. Abra um **Pull Request** descrevendo as alterações

**Áreas prioritárias para contribuição:**
- Expansão do dicionário de sinais LIBRAS reconhecidos
- Melhoria do modelo de classificação (arquiteturas de deep learning)
- Suporte a expressões faciais e corporais (além das mãos)
- Testes de usabilidade com usuários surdos reais
- Versão mobile (Kivy/BeeWare)

---

## 📞 Contato e Suporte

Para dúvidas, sugestões ou relatos de bugs, abra uma **Issue** no repositório do projeto.

---

<div align="center">

Desenvolvido com ❤️ para promover **acessibilidade** e **inclusão** em ambientes de saúde.

*"A comunicação é um direito de todos."*

</div>

</div>
