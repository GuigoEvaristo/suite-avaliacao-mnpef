# Histórico de Desenvolvimento: Corretor Inteligente (MNPEF)

Este documento registra a evolução cronológica, técnica e as decisões de engenharia de software adotadas no desenvolvimento do Objeto Educacional para a dissertação de Mestrado Profissional em Ensino de Física (MNPEF). O sistema integra geração automatizada de avaliações, visão computacional e interfaces multiplataforma para viabilizar práticas de avaliação formativa.

---

## Caminho Computacional e Marcos do Projeto

### 1. Configuração do Ambiente e Arquitetura Inicial
* **Isolamento de Escopo:** Criação e configuração de um ambiente virtual Python (`.env`) para garantir a reprodutibilidade das dependências do ecossistema de visão computacional.
* **Transição de Paradigma (Word para LaTeX):** Abandono do modelo conceitual baseado em caixas de texto estruturadas no Microsoft Word (`.docx`). A flexibilidade do usuário gerava inconsistências espaciais e quebras de layout imprevisíveis, inviabilizando algoritmos rígidos de segmentação. Adotou-se a automatização tipográfica via LaTeX.

### 2. Geração Programática de Marcadores Fiduciais (`gerar_icones.py`)
* **Padronização Geométrica:** Desenvolvimento de um script em Python utilizando a biblioteca **OpenCV (`cv2`)** e **NumPy** para matrizes numéricas, gerando marcadores padronizados de base pixelizada fixa (50x50 pixels).
* **Definição de Contextos:** Criação de assinaturas visuais discretas para delimitar os ambientes de captura:
    * `icone_questao.jpg` (Círculo centralizado - Identificação de enunciados).
    * `icone_equacao.jpg` (Retângulo preenchido - Delimitação de resoluções matemáticas analíticas).
    * `icone_texto.jpg` (Triângulo preenchido - Delimitação de justificativas conceituais dissertativas).

### 3. O Motor de Fabricação de Avaliações (`fabri_ava.py`)
* **Injeção Dinâmica de Variáveis:** Construção de um pipeline em Python que recebe estruturas de dicionários contendo dados escolares de Dourados-MS (escola, turma, enunciados) e realiza a substituição de strings em um modelo LaTeX de controle (`modelo.tex`).
* **Tags Espaciais de Abertura e Fechamento:** Configuração da lógica estrutural do LaTeX para embutir os marcadores fiduciais nas margens exatas de início e fim dos espaços de escrita manuscrita, usando comandos de espaçamento vertical físico (`\vspace`).
* **Compilação Automatizada (Subprocess):** Implementação da biblioteca nativa `subprocess` do Python para disparar chamadas assíncronas ao CLI do sistema operacional, executando o motor `pdflatex` em modo silencioso (`-interaction=nonstopmode`) para gerar avaliações nativas em formato PDF.

### 4. Simulação de Captura e Processamento de Imagem
* **Rasterização de Controle:** Utilização da ferramenta de terminal `pdftoppm` do Linux para converter o PDF digital em uma imagem PNG em escala de cinza (`pagina_prova-1.png`), simulando com perfeição geométrica a fotografia plana que será realizada pelo smartphone do docente.

### 5. Desenvolvimento do Algoritmo de Visão Computacional (`corretor.py`)
* **Mapeamento por Template Matching:** Implementação do método `cv2.matchTemplate` com normalização de coeficientes de correlação (`cv2.TM_CCOEFF_NORMED`) para varredura matricial e localização das coordenadas $(X, Y)$ dos marcadores na folha.
* **Solução do Erro de Escala (Cálculo de DPI):** Resolução matemática do primeiro gargalo físico do projeto. A divergência de escala entre a imagem do marcador de 50x50px e o render final do LaTeX gerava taxas de semelhança críticas (abaixo de 30%). O alinhamento foi corrigido ao ajustar a rasterização de captura rigorosamente para **254 DPI**, elevando a taxa de confiança de detecção para **96.2%**.
* **Filtro de Supressão Duplicada 2D:** Refinamento do algoritmo de varredura para computar distâncias euclidianas tanto no eixo vertical quanto horizontal. Isso solucionou o descarte incorreto de marcadores adjacentes dispostos na mesma linha de varredura, garantindo a leitura correta do par de âncoras (Início/Fim).
* **Isolamento da Região de Interesse (ROI):** Execução bem-sucedida do fatiamento de matrizes multidimensionais (*slicing* de arrays NumPy) para extrair estritamente os pixels contidos dentro da área delimitada pelos marcadores de cálculo, gerando o arquivo salvo `resultado_recorte_calculo.jpg`.
* **Simulação Sintética:** Utilização da biblioteca `PyMuPDF` para converter PDFs em imagens simulando capturas de smartphone em alta fidelidade no ambiente Windows.

### 6. Governança de Código e Versionamento (Git/GitHub)
* **Políticas de Rastreamento (.gitignore):** Criação de regras restritivas para expurgar arquivos de ambiente local (`.env/`) e subprodutos gerados dinamicamente pelas compilações consecutivas do compilador LaTeX (`.pdf`, `.png`, `.jpg`, `.aux`, `.log`, `.synctex.gz`, `.fls`, `.fdb_latexmk`).
* **Sincronização Segura:** Inicialização do repositório Git local, congelamento de dependências via `requirements.txt` e empacotamento do histórico de desenvolvimento (*Commits*). Migração de infraestrutura de segurança autenticada no GitHub através da substituição de senhas estáticas por Tokens de Acesso Pessoal (PAT).

### 7. Arquitetura Web Multiplataforma (`app.py`)
* **Inicialização do Frontend Dinâmico:** Implementação do framework **Streamlit** para encapsular a lógica de console em uma interface gráfica de navegador web responsiva.
* **Estruturação de Módulos (Tabs):** Separação lógica das visões operacionais do professor entre a elaboração didática da prova (coleta de enunciados e tipologias) e o backend de upload e recepção de imagens de sensores móveis.
* **Integração de Backend:** Refatoração dos algoritmos de visão computacional para remover dependências de interface gráfica do sistema operacional (ex: `cv2.imshow`), permitindo o processamento hermético em servidores sem travamentos.

### 8. Integração com Inteligência Artificial Multimodal (Fase 2)
* **Processamento Cognitivo (Google Gemini):** Integração com a API do Google (modelo `gemini-3.5-flash`) para leitura multimodal (Visão e Texto) de equações e resoluções manuscritas recortadas matematicamente pelo OpenCV.
* **Engenharia de Prompt Pedagógico:** Estruturação das instruções de sistema (*System Prompt*) ancorada em teorias de aprendizagem significativa. A IA foi configurada para atuar como um docente construtivista, focando na identificação de erros conceituais e na formulação de *feedback* formativo autônomo, substituindo a simples correção binária de resultados.
* **Governança de Segredos e Migração de SDK:** Estabelecimento de um cofre de chaves assíncronas utilizando a arquitetura `.streamlit/secrets.toml`. Resolução técnica de obsolescência (*deprecation*) via migração de bibliotecas legadas (`google.generativeai`) para o SDK moderno (`google-genai`), com instanciação explícita de clientes na memória para segurança de acesso.