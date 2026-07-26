# app.py
import streamlit as st
import pandas as pd
import os
import datetime
from PIL import Image
from services.ia_service import extrair_dados_cabecalho
from fabri_ava import fabricar_prova
from corretor_av import realizar_recorte_via_coordenadas_ia
from services.ia_service import analisar_prova_com_ia
from database.db_manager import (
    iniciar_banco, registar_usuario, validar_login, 
    adicionar_escola, buscar_escolas_por_usuario,
    salvar_correcao, buscar_historico_por_usuario_e_escola,
    salvar_prova_fabricada, buscar_provas_por_usuario_e_escola, buscar_pdf_prova
)

# 1. CONFIGURAÇÃO DA PÁGINA (Substituiu a sua linha antiga, agora com layout="wide")
st.set_page_config(
    page_title="Suíte de Avaliação para Professores - MNPEF", 
    layout="wide", 
    page_icon="📝",
    initial_sidebar_state="expanded"
)

# 2. INJEÇÃO DE CSS (Acessibilidade Visual para os Professores)
st.markdown("""
    <style>
        /* Aumenta a fonte base de todo o aplicativo */
        html, body, [class*="css"] {
            font-size: 18px !important;
        }
        /* Aumenta os textos dos menus, caixas de edição e botões */
        .stTextInput label, .stSelectbox label, .stTextArea label, .stCheckbox label {
            font-size: 18px !important;
            font-weight: 500;
        }
        .stButton>button {
            font-size: 18px !important;
            padding: 10px 20px;
        }
    </style>
""", unsafe_allow_html=True)

# 3. INICIALIZAÇÃO DO BANCO (Mantida no lugar correto)
iniciar_banco()

# =========================================================
# ESTADO DA SESSÃO E CALLBACKS (VETOR DINÂMICO DE QUESTÕES)
# =========================================================
if "autenticado" not in st.session_state: st.session_state["autenticado"] = False
if "usuario_logado" not in st.session_state: st.session_state["usuario_logado"] = None
if "escola_ativa" not in st.session_state: st.session_state["escola_ativa"] = None
if "lista_questoes" not in st.session_state: st.session_state["lista_questoes"] = []
if "modo_preview" not in st.session_state: st.session_state["modo_preview"] = False

# Funções de Manipulação do Vetor (Callbacks)
def adicionar_questao():
    st.session_state["lista_questoes"].append({
        "enunciado": "", "tipo": "aberta", "estilo_espaco": "box", "tamanho_espaco": "medio",
        "alternativas": "", "estilo_vf": "classico", "afirmacoes": "", "imagem_temp": None
    })

def mover_cima(index):
    if index > 0:
        lista = st.session_state["lista_questoes"]
        lista[index - 1], lista[index] = lista[index], lista[index - 1]

def mover_baixo(index):
    lista = st.session_state["lista_questoes"]
    if index < len(lista) - 1:
        lista[index + 1], lista[index] = lista[index], lista[index + 1]

def remover_questao(index):
    st.session_state["lista_questoes"].pop(index)

# =========================================================
# PORTAS DE ACESSO (MANTIDAS)
# =========================================================
if not st.session_state["autenticado"]:
    st.title("Bem-vindo à Suíte de Avaliação para Professores")
    st.subheader("🔒 Acesso Restrito ao Projeto")
    senha_digitada = st.text_input("Senha Global:", type="password")
    if st.button("Entrar no Sistema"):
        if senha_digitada == st.secrets["SENHA_ACESSO"]:
            st.session_state["autenticado"] = True
            st.rerun()
        else: st.error("Senha global incorreta.")
    st.stop()

if st.session_state["autenticado"] and st.session_state["usuario_logado"] is None:
    st.title("Bem-vindo ao Corretor Inteligente")
    aba_login, aba_registo = st.tabs(["🔑 Fazer Login", "📝 Criar Nova Conta"])
    with aba_login:
        email_login = st.text_input("E-mail:")
        senha_login = st.text_input("Senha Pessoal:", type="password")
        if st.button("Entrar"):
            usuario = validar_login(email_login, senha_login)
            if usuario:
                st.session_state["usuario_logado"] = usuario
                st.rerun()
            else: st.error("E-mail ou senha incorretos.")
    with aba_registo:
        nome_reg = st.text_input("Nome Completo:")
        email_reg = st.text_input("E-mail Profissional:")
        tel_reg = st.text_input("Telefone (Opcional):")
        senha_reg = st.text_input("Crie uma Senha Pessoal:", type="password")
        senha_conf = st.text_input("Confirme a Senha:", type="password")
        if st.button("Registar Conta"):
            if not (nome_reg and email_reg and senha_reg): st.warning("Preencha nome, e-mail e senha.")
            elif senha_reg != senha_conf: st.error("As senhas não coincidem.")
            else:
                sucesso, msg = registar_usuario(nome_reg, email_reg, tel_reg, senha_reg)
                if sucesso: st.success(msg)
                else: st.error(msg)
    st.stop()

# =========================================================
# CABEÇALHO PRINCIPAL E CONTEXTO DE ESCOLA
# =========================================================
nome_prof = st.session_state["usuario_logado"]["nome"]
email_prof = st.session_state["usuario_logado"]["email"]
usuario_id = st.session_state["usuario_logado"]["id"]

col1, col2 = st.columns([0.8, 0.2])
with col1: st.title(f"Olá, Prof. {nome_prof} 👋")
with col2: 
    st.write("")
    if st.button("🚪 Sair"):
        st.session_state.clear() # Limpa toda a memória
        st.rerun()

escolas_do_prof = buscar_escolas_por_usuario(usuario_id)
if not escolas_do_prof:
    st.warning("Você ainda não possui escolas cadastradas.")
    nova_escola = st.text_input("Nome da Escola/Colégio:")
    if st.button("Cadastrar Primeira Escola"):
        if nova_escola: adicionar_escola(usuario_id, nova_escola.strip()); st.rerun()
    st.stop()
else:
    col_escola, col_nova = st.columns([0.7, 0.3])
    with col_escola:
        st.session_state["escola_ativa"] = st.selectbox("🏫 Atuando agora em:", escolas_do_prof)
    with col_nova:
        with st.expander("+ Nova Escola"):
            extra_escola = st.text_input("Nome:")
            if st.button("Adicionar"):
                if extra_escola: adicionar_escola(usuario_id, extra_escola.strip()); st.rerun()

st.markdown("---")

# Função para colorir as linhas baseadas no status do aluno
def colorir_status(row):
    situacao = row.get('Situação', '')
    
    # Cores em tons pastéis (suaves)
    if situacao == 'Transferido':
        cor = 'background-color: #ffcccc' # Vermelho suave
    elif situacao == 'Faltou':
        cor = 'background-color: #fff3cd' # Amarelo suave
    elif situacao == 'Presente':
        cor = 'background-color: #d4edda' # Verde suave
    else:
        cor = ''
        
    return [cor] * len(row)

# =========================================================
# ABAS DO SISTEMA
# =========================================================
aba_fabricar, aba_corrigir, aba_historico, aba_dashboard = st.tabs([
    "📝 Fabricar Prova", "📸 Corrigir Avaliação", "📊 Histórico", "📈 Desempenho"
])

# ---------------------------------------------------------
# ABA 1: FABRICAR PROVA (MOTOR DINÂMICO)
# ---------------------------------------------------------
with aba_fabricar:
    st.header("1. Metadados da Avaliação")
    
    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        disciplina = st.text_input("Disciplina:", value="Física")
        serie = st.selectbox("Série/Ano:", ["1º Ano", "2º Ano", "3º Ano", "Outro"])
        turma = st.text_input("Turma:", placeholder="Ex: A, B, Única")
    with col_meta2:
        etapa = st.selectbox("Etapa/Tipo:", ["1ª Avaliação", "2ª Avaliação", "Recuperação", "Simulado", "Trabalho"])
        data_prova = st.text_input("Data da Aplicação:", value=datetime.datetime.now().strftime("%d/%m/%Y"))
        logo_upload = st.file_uploader("Logo da Escola (Opcional):", type=["png", "jpg", "jpeg"], key="logo_img")

    instrucoes = st.text_area("Instruções aos Alunos (Opcional):", placeholder="Cada linha será um marcador (bullet point) na prova.\nEx: Não é permitido o uso de calculadora.\nA nota total é 10,0.")

    st.markdown("---")
    st.header("2. Construção das Questões")

    # --- 🤖 ESTÚDIO DE CRIAÇÃO COM IA ---
    with st.expander("✨ Estúdio de Criação (Gerar Questões com IA)", expanded=False):
        st.info("Descreva o tema e deixe a Inteligência Artificial formular as questões para você. Após a geração, você poderá editar os textos livremente abaixo.")
        
        col_ia1, col_ia2, col_ia3 = st.columns([2, 1, 1])
        with col_ia1:
            tema_ia = st.text_input("Tema/Conteúdo:", placeholder="Ex: Leis de Newton aplicadas ao cotidiano")
        with col_ia2:
            qtd_ia = st.number_input("Quantidade:", min_value=1, max_value=10, value=3)
        with col_ia3:
            tipo_ia = st.selectbox("Formato predominante:", ["Múltipla Escolha", "Dissertativa", "Misto"])
            
        if st.button("🪄 Gerar Questões com IA", type="primary", use_container_width=True):
            if not tema_ia:
                st.warning("Por favor, digite um tema para a IA trabalhar.")
            else:
                with st.spinner(f"A Inteligência Artificial está a redigir {qtd_ia} questão(ões) sobre '{tema_ia}'..."):
                    # Aqui, futuramente, chamaremos a função real do ia_service.py
                    # Por enquanto, simulamos o comportamento injetando questões no vetor
                    import time
                    time.sleep(2) # Simula o tempo de resposta da IA
                    
                    for i in range(qtd_ia):
                        if tipo_ia == "Múltipla Escolha" or (tipo_ia == "Misto" and i % 2 == 0):
                            st.session_state["lista_questoes"].append({
                                "enunciado": f"(Gerada por IA) Questão sobre {tema_ia}. Analise a situação e assinale a correta:", 
                                "tipo": "multipla", 
                                "estilo_espaco": "box", "tamanho_espaco": "medio",
                                "alternativas": "A) Alternativa gerada 1\nB) Alternativa gerada 2\nC) Alternativa gerada 3\nD) Alternativa gerada 4", 
                                "estilo_vf": "classico", "afirmacoes": "", "imagem_temp": None
                            })
                        else:
                            st.session_state["lista_questoes"].append({
                                "enunciado": f"(Gerada por IA) Descreva com as suas palavras o conceito central de {tema_ia}.", 
                                "tipo": "aberta", 
                                "estilo_espaco": "lines", "tamanho_espaco": "medio",
                                "alternativas": "", 
                                "estilo_vf": "classico", "afirmacoes": "", "imagem_temp": None
                            })
                    st.success("✨ Questões geradas com sucesso! Você pode revisá-las e editá-las abaixo.")
                    st.rerun()

    # --- GUIA RÁPIDO DE FORMATAÇÃO E FÓRMULAS ---
    with st.expander("💡 Guia Rápido de Formatação e Fórmulas Matemáticas"):
        st.markdown(r"""
        O sistema reconhece comandos nativos de formatação científica. Para ativar a matemática, envolva a equação com **$** (cifrões).

        **Formatação de Texto**
        * **Negrito:** Digite `\textbf{seu texto}` 
        * **Itálico:** Digite `\textit{seu texto}` 
        * **Sublinhado:** Digite `\underline{seu texto}`

        **Símbolos e Equações (Física e Matemática)**
        * **Índices (Subscrito):** Use `_` ➔ `v_0` resulta em $v_0$
        * **Potências (Sobrescrito):** Use `^` ➔ `m^2` resulta em $m^2$
        * **Frações:** Use `\frac{cima}{baixo}` ➔ `\frac{\Delta s}{\Delta t}` resulta em $\frac{\Delta s}{\Delta t}$
        * **Raiz Quadrada:** Use `\sqrt{número}` ➔ `\sqrt{129}` resulta em $\sqrt{129}$
        * **Letras Gregas:** Use a barra invertida ➔ `\alpha, \beta, \Delta, \Omega, \mu` resulta em $\alpha, \beta, \Delta, \Omega, \mu$
        * **Multiplicação (Ponto):** Use `\cdot` ➔ `F = m \cdot a` resulta em $F = m \cdot a$

        **Exemplo prático no enunciado:**
        > "A equação da velocidade é dada por $v = v_0 + a \cdot t$. Calcule..."
        """)
    # --------------------------------------------

    # Renderiza o Vetor de Questões
    for i, q in enumerate(st.session_state["lista_questoes"]):
        with st.container():
            st.markdown(f"### Questão {i+1}")
            
            # Botões de Reordenação
            col_b1, col_b2, col_b3, col_b4 = st.columns([0.1, 0.1, 0.1, 0.7])
            with col_b1: st.button("↑", key=f"up_{i}", on_click=mover_cima, args=(i,))
            with col_b2: st.button("↓", key=f"down_{i}", on_click=mover_baixo, args=(i,))
            with col_b3: st.button("🗑️", key=f"del_{i}", on_click=remover_questao, args=(i,))
            
            # Campos da Questão
            q["enunciado"] = st.text_area(f"Enunciado:", value=q["enunciado"], key=f"enunciado_{i}")
            
            # Anexo de Imagem por questão
            q["imagem_temp"] = st.file_uploader("Anexar Imagem (Opcional)", type=["png", "jpg"], key=f"img_q_{i}")
            
            q["tipo"] = st.radio("Tipo de Questão:", ["aberta", "multipla", "vf"], format_func=lambda x: "Dissertativa/Cálculo" if x == "aberta" else "Múltipla Escolha" if x == "multipla" else "Verdadeiro ou Falso", horizontal=True, key=f"tipo_{i}")
            
            if q["tipo"] == "aberta":
                col_ab1, col_ab2 = st.columns(2)
                with col_ab1: q["estilo_espaco"] = st.selectbox("Estilo do Espaço:", ["box", "lines"], format_func=lambda x: "Caixa (Box)" if x == "box" else "Linhas", key=f"estilo_{i}")
                with col_ab2: q["tamanho_espaco"] = st.selectbox("Tamanho do Espaço:", ["pequeno", "medio", "grande"], index=1, key=f"tam_{i}")
            
            elif q["tipo"] == "multipla":
                q["alternativas"] = st.text_area("Alternativas (uma por linha):", value=q["alternativas"], key=f"alt_{i}", placeholder="A) Primeira opção\nB) Segunda opção")
            
            elif q["tipo"] == "vf":
                q["estilo_vf"] = st.radio("Estilo de Numeração:", ["classico", "somatoria"], format_func=lambda x: "(V) ou (F)" if x == "classico" else "Somatória (01, 02, 04...)", horizontal=True, key=f"estilovf_{i}")
                q["afirmacoes"] = st.text_area("Afirmações (uma por linha):", value=q["afirmacoes"], key=f"afirm_{i}")
            
            st.markdown("---")

    st.button("➕ Adicionar Questão", on_click=adicionar_questao)

    # 3. Finalização e Processamento
    if len(st.session_state["lista_questoes"]) > 0:
        st.markdown("### 3. Conclusão")
        
        # Toggle para Preview
        if st.button("🔍 Pré-visualizar Rascunho"):
            st.session_state["modo_preview"] = not st.session_state["modo_preview"]
            
        if st.session_state["modo_preview"]:
            st.info("RASCUNHO VISUAL (O PDF final terá o design oficial do Colégio)")
            st.write(f"**Cabeçalho:** {st.session_state['escola_ativa']} | {disciplina} | {serie} {turma} | {etapa}")
            for idx, q_prev in enumerate(st.session_state["lista_questoes"]):
                st.write(f"**{idx+1}.** {q_prev['enunciado']}")
                if q_prev['tipo'] == 'multipla': st.write(f"*(Alternativas: {len(q_prev['alternativas'].strip().split(chr(10)))} opções)*")
                elif q_prev['tipo'] == 'vf': st.write(f"*(V/F: {len(q_prev['afirmacoes'].strip().split(chr(10)))} afirmações)*")
                else: st.write(f"*(Espaço para resolução: {q_prev['tamanho_espaco']})*")

        if st.button("✅ Finalizar Criação de Avaliação", type="primary"):
            if not turma: st.warning("Por favor, preencha a Turma.")
            else:
                with st.spinner("Processando imagens, compilando LaTeX e guardando no Arquivo..."):
                    try:
                        # Preparação dos dados para o motor LaTeX
                        questoes_formatadas = []
                        imagens_para_limpar = [] # Garbage Collector
                        
                        # Salva o Logo temporariamente se existir
                        caminho_logo = None
                        if logo_upload:
                            caminho_logo = "temp_logo.jpg"
                            with open(caminho_logo, "wb") as f: f.write(logo_upload.getbuffer())
                            imagens_para_limpar.append(caminho_logo)

                        for idx_q, q_raw in enumerate(st.session_state["lista_questoes"]):
                            q_limpa = {
                                "enunciado": q_raw["enunciado"],
                                "tipo": q_raw["tipo"],
                                "estilo_espaco": q_raw["estilo_espaco"],
                                "tamanho_espaco": q_raw["tamanho_espaco"],
                            }
                            if q_raw["tipo"] == "multipla":
                                q_limpa["alternativas"] = [alt for alt in q_raw["alternativas"].split('\n') if alt.strip()]
                            elif q_raw["tipo"] == "vf":
                                q_limpa["estilo_vf"] = q_raw["estilo_vf"]
                                q_limpa["afirmacoes"] = [af for af in q_raw["afirmacoes"].split('\n') if af.strip()]
                            
                            # Salva imagem da questão temporariamente
                            if q_raw["imagem_temp"]:
                                cam_img = f"temp_img_q{idx_q}.jpg"
                                with open(cam_img, "wb") as f: f.write(q_raw["imagem_temp"].getbuffer())
                                q_limpa["imagem"] = cam_img
                                imagens_para_limpar.append(cam_img)
                                
                            questoes_formatadas.append(q_limpa)

                        dados_prova = {
                            "escola": st.session_state["escola_ativa"],
                            "disciplina": disciplina,
                            "serie": serie,
                            "turma": turma,
                            "etapa": etapa,
                            "prof_nome": nome_prof,
                            "prof_email": email_prof,
                            "instrucoes": instrucoes,
                            "data": data_prova,
                            "logo": caminho_logo,
                            "questoes": questoes_formatadas
                        }

                        # Geração do PDF
                        nome_pdf = "prova_gerada_app"
                        fabricar_prova(dados_prova, "modelo.tex", nome_pdf)
                        
                        # Guardar em Banco de Dados (BLOB)
                        if os.path.exists(f"{nome_pdf}.pdf"):
                            with open(f"{nome_pdf}.pdf", "rb") as pdf_file:
                                pdf_bytes = pdf_file.read()
                                
                            salvar_prova_fabricada(
                                usuario_id, st.session_state["escola_ativa"], 
                                disciplina, serie, turma, etapa, pdf_bytes
                            )
                            
                            st.success("✅ Avaliação criada e guardada no seu Histórico com sucesso!")
                            st.download_button("📥 Descarregar PDF Agora", data=pdf_bytes, file_name=f"Avaliacao_{serie}_{turma}.pdf", mime="application/pdf")
                            
                            # Limpeza de Memória (Garbage Collection)
                            st.session_state["lista_questoes"] = [] # Reseta o formulário
                            st.session_state["modo_preview"] = False
                            
                            for img_path in imagens_para_limpar:
                                if os.path.exists(img_path): os.remove(img_path)
                            if os.path.exists("modelo.tex"): os.remove("modelo.tex")
                            if os.path.exists(f"{nome_pdf}.pdf"): os.remove(f"{nome_pdf}.pdf")
                            
                        else: st.error("❌ Ocorreu um erro na compilação do ficheiro LaTeX.")
                    except Exception as e: st.error(f"❌ Falha crítica no sistema: {e}")

# ---------------------------------------------------------
# ABA 2: CORRIGIR (LABORATÓRIO DE AVALIAÇÃO MULTIMODAL)
# ---------------------------------------------------------
with aba_corrigir:
    st.header("1. Origem e Referencial da Avaliação")
    st.write("Indique ao sistema qual avaliação será corrigida para que a IA tenha o gabarito correto.")
    
    modo_prova = st.radio(
        "Qual é a origem desta avaliação?",
        ["Prova criada neste sistema (Aba 1)", "Prova Externa (Arquivo pessoal do professor)"],
        horizontal=True
    )
    
    if modo_prova == "Prova Externa (Arquivo pessoal do professor)":
        st.info("💡 **Modo Externo Ativado:** Como esta prova não foi gerada pelo sistema, forneça o referencial para guiar a correção.")
        
        nome_prova_externa = st.text_input(
            "Nome da Avaliação (Para salvar no Histórico):", 
            placeholder="Ex: 1ª Prova de Dinâmica - Turma 2026"
        )
        
        col_gab_texto, col_gab_arq = st.columns(2)
        with col_gab_texto:
            gabarito_texto = st.text_area(
                "Gabarito, Pontuação ou Observações:", 
                placeholder="Ex: Questão 1 vale 2 pontos. Resposta esperada: 50 N. Considere correto se o aluno errou apenas a conversão de unidades...",
                height=130
            )
        with col_gab_arq:
            gabarito_arquivo = st.file_uploader(
                "Anexe a Prova em Branco ou o Gabarito (PDF/Foto):", 
                type=["pdf", "png", "jpg", "jpeg"]
            )
    else:
        st.info("O sistema resgatará automaticamente o gabarito da prova selecionada.")
        prova_selecionada = st.selectbox(
            "Selecione a Prova do Banco de Dados:", 
            ["[Em breve] Conexão com o banco de provas da Aba 1..."]
        )

    st.markdown("---")
    st.header("2. Intencionalidade Pedagógica")
    st.write("Configure as lentes teóricas e metodológicas que guiarão a Inteligência Artificial na correção.")
    
    col_teo, col_met = st.columns(2)
    with col_teo:
        teorico = st.selectbox(
            "Lente Teórica (O 'Como' o aluno aprende):", 
            ["David Ausubel (Aprendizagem Significativa)", "Edgar Morin (Pensamento Complexo)", "Paulo Freire (Leitura de Mundo)", "Jean Piaget (Construtivismo)", "Lev Vygotsky (Sociointeracionismo)", "B.F. Skinner (Behaviorismo)", "Carl Rogers (Humanismo)"]
        )
    with col_met:
        metodologia = st.selectbox(
            "Metodologia Aplicada (O 'Como' foi ensinado):", 
            ["Resolução de Problemas (PBL)", "Abordagem STEAM", "Aula Expositiva Dialogada", "Sala de Aula Invertida", "Instrução por Pares (Peer Instruction)"]
        )
        
    with st.expander("⚙️ Opções Avançadas de Correção"):
        peso_correcao = st.slider(
            "Balanço da Avaliação (Rigor vs. Conceito):", 
            0, 100, 50, format="%d%%", 
            help="0% = Foco total na exatidão matemática. 100% = Foco total na construção do conceito."
        )
        chk_caligrafia = st.checkbox("Avaliar Caligrafia, Capricho e Organização Espacial", value=True)
        chk_inter = st.checkbox("Valorizar Conexões Interdisciplinares")
        chk_estrutura = st.checkbox("Exigir estruturação lógica (ex: listar os dados antes da equação)")

    nome_teorico = teorico.split(" (")[0]
    nome_metodologia = metodologia.split(" (")[0]
    
    prompt_base = f"Atue como um professor avaliador de Física. A sua análise deve basear-se na teoria de {nome_teorico}. Considere que o conteúdo foi ministrado via {nome_metodologia}. Durante a correção, o seu peso de avaliação é de {peso_correcao}% focado na construção conceitual e {100-peso_correcao}% no rigor matemático. "
    
    if chk_caligrafia: prompt_base += "Avalie o capricho do aluno e a organização espacial. "
    if chk_inter: prompt_base += "Valorize conexões interdisciplinares. "
    if chk_estrutura: prompt_base += "Verifique estruturação lógica dos dados. "
        
    prompt_base += "Formule um feedback formativo que incite o aluno a refletir sobre a falha, sem entregar a resposta pronta."

    st.markdown("### Homologação do Comando")
    prompt_final = st.text_area(
        "Edite o prompt pedagógico se necessário:", 
        value=prompt_base, 
        height=120,
        label_visibility="collapsed"
    )
    homologado = st.checkbox("✅ **Confirmo e homologo este prompt pedagógico para a correção.**")

    st.markdown("---")
    st.header("3. Captura e Triagem em Lote")
    st.info("Fotografe as avaliações dos alunos preferencialmente na ordem da chamada da turma.")
    
    fotos_provas = st.file_uploader(
        "Envie as fotos das provas resolvidas pelos alunos:", 
        type=["png", "jpg", "jpeg"], 
        accept_multiple_files=True
    )
    
    if fotos_provas:
        st.success(f"📸 {len(fotos_provas)} imagens de alunos carregadas.")
        
        if homologado:
            if st.button("🔍 Extrair Nomes e Números (Visão Computacional)"):
                with st.spinner("A analisar a caligrafia dos cabeçalhos..."):
                    lista_alunos = []
                    barra = st.progress(0)
                    
                    for i, foto_upload in enumerate(fotos_provas):
                        imagem_pil = Image.open(foto_upload)
                        dados = extrair_dados_cabecalho(imagem_pil)
                        
                        num_lido = dados.get("numero") if dados.get("numero") is not None else i + 1 
                        nome_lido = dados.get("nome", "Não identificado")
                        
                        lista_alunos.append({
                            "Nº": num_lido,
                            "Nome Lido (OCR)": nome_lido,
                            "E-mail (Feedback)": "",
                            "Situação": "Presente",
                            "Verificado ✅": False
                        })
                        barra.progress((i + 1) / len(fotos_provas))
                    
                    st.session_state["df_triagem"] = pd.DataFrame(lista_alunos)
                    st.success("Leitura concluída! Por favor, revise a tabela abaixo.")

            if "df_triagem" in st.session_state:
                st.markdown("### 📋 Tabela de Triagem e Homologação")
                
                df_editado = st.data_editor(
                    st.session_state["df_triagem"],
                    column_config={
                        "Nº": st.column_config.NumberColumn("Nº", min_value=1, step=1, width="small"),
                        "Nome Lido (OCR)": st.column_config.TextColumn("Nome do Aluno", width="medium"),
                        "E-mail (Feedback)": st.column_config.TextColumn("E-mail", width="medium"),
                        "Situação": st.column_config.SelectboxColumn(
                            "Situação", options=["Presente", "Transferido", "Faltou"], required=True, width="small"
                        ),
                        "Verificado ✅": st.column_config.CheckboxColumn("Verificado ✅", default=False, width="small")
                    },
                    hide_index=True,
                    use_container_width=True
                )

                st.markdown("---")
                alunos_validados = df_editado[df_editado["Verificado ✅"] == True]
                
                if st.button("🚀 Iniciar Correção Pedagógica (Motor de IA)", type="primary"):
                    if alunos_validados.empty:
                        st.error("⚠️ Você precisa marcar pelo menos um aluno como 'Verificado ✅' na tabela.")
                    else:
                        st.success(f"🔥 Iniciando a correção para {len(alunos_validados)} aluno(s) validado(s)...")
                        # O motor chamará a IA enviando o prompt_final + fotos_provas + gabarito (se houver)
        else:
            st.error("⚠️ Confirme a homologação do prompt pedagógico (caixa de seleção acima) para liberar a triagem.")

# ---------------------------------------------------------
# ABA 3: HISTÓRICO (DIÁRIO DE CLASSE DIGITAL)
# ---------------------------------------------------------
with aba_historico:
    st.header("📚 Histórico de Avaliações")
    st.write("Consulte o arquivo de provas, revise os pareceres da IA e realize a comunicação oficial.")
    
    col_escola, col_turma, col_prova = st.columns(3)
    with col_escola:
        filtro_escola = st.selectbox("Escola/Colégio:", ["Colégio Estadual Padrão", "Instituto Federal", "Escola Particular Exemplo"])
    with col_turma:
        filtro_turma = st.selectbox("Turma:", ["1º Ano A", "2º Ano B", "3º Ano C"])
    with col_prova:
        filtro_prova = st.selectbox("Avaliação:", ["1ª Avaliação - Cinemática", "2ª Avaliação - Dinâmica"])

    st.markdown("---")
    st.subheader(f"Diário de Correção: {filtro_turma} | {filtro_prova}")
    
    if "df_historico_mock_v2" not in st.session_state:
        st.session_state["df_historico_mock_v2"] = pd.DataFrame({
            "Nº": [1, 2, 3, 4],
            "Nome": ["Ana Clara", "Gabriel Souza", "João Pedro", "Mariana Silva"],
            "E-mail": ["ana@escola.com", "", "joao@escola.com", "mari@escola.com"],
            "Situação": ["Presente", "Transferido", "Presente", "Faltou"],
            "Homologado": [False, False, False, False],
            "Parecer_Texto": [
                "Você compreendeu bem a cinemática, mas cometeu um erro na aplicação da Equação de Torricelli. Revise a conversão de km/h para m/s.",
                "",
                "Excelente organização lógica dos dados! No entanto, o conceito de inércia precisa ser mais bem fundamentado.",
                "Prezado(a) aluno(a), você não compareceu à avaliação. Procure a coordenação pedagógica para agendar a 2ª chamada."
            ]
        })
        
    df_principal = st.session_state["df_historico_mock_v2"]
    df_visual = df_principal.drop(columns=["Parecer_Texto"])
    tabela_colorida = df_visual.style.apply(colorir_status, axis=1)
    
    st.write("Dê um duplo clique na caixa 'Homologado ✅' para aprovar rapidamente, ou use a Revisão Individual abaixo para editar o texto.")
    
    df_editado = st.data_editor(
        tabela_colorida, 
        hide_index=True, 
        use_container_width=True,
        disabled=["Nº", "Nome", "E-mail", "Situação"], 
        column_config={
            "Homologado": st.column_config.CheckboxColumn("Homologado ✅", width="small")
        }
    )
    
    st.session_state["df_historico_mock_v2"]["Homologado"] = df_editado["Homologado"]
    df_principal = st.session_state["df_historico_mock_v2"]

    # Aviso Estratégico (O gancho visual que você sugeriu)
    st.info("💡 **Dica de Fluxo:** Após homologar todos os alunos na tabela acima ou na revisão abaixo, o botão de **Disparo em Lote** será ativado no final da página.")

    st.markdown("---")
    
    # --- BLOCO 1: REVISÃO INDIVIDUAL ---
    st.markdown("### 🔍 Revisão Individual")
    st.write("Leia, altere o que a IA escreveu e aprove o feedback final aluno por aluno.")
    
    alunos_avaliados = df_principal[df_principal["Situação"].isin(["Presente", "Faltou"])]
    
    col_sel_aluno, col_vazia = st.columns([1, 1])
    with col_sel_aluno:
        aluno_selecionado = st.selectbox(
            "Selecione o aluno:", 
            alunos_avaliados["Nome"],
            label_visibility="collapsed"
        )
    
    idx_aluno = df_principal[df_principal["Nome"] == aluno_selecionado].index[0]
    texto_atual = df_principal.at[idx_aluno, "Parecer_Texto"]
    
    texto_editado = st.text_area("Feedback do Aluno (Editável):", value=texto_atual, height=180)
    
    botoes_acao1, botoes_acao2, _ = st.columns([1, 1, 2])
    
    with botoes_acao1:
        if st.button("💾 Salvar e Homologar", use_container_width=True):
            st.session_state["df_historico_mock_v2"].at[idx_aluno, "Parecer_Texto"] = texto_editado
            st.session_state["df_historico_mock_v2"].at[idx_aluno, "Homologado"] = True
            st.rerun() 
            
    with botoes_acao2:
        if st.button("📧 Enviar Individual", use_container_width=True):
            st.success(f"📩 Feedback enviado para {aluno_selecionado}!")

    st.markdown("---")
    
    # --- BLOCO 2: DISPARO EM LOTE (Fundo da página) ---
    st.markdown("### 📤 Comunicação em Massa (Disparo em Lote)")
    
    todos_homologados = alunos_avaliados["Homologado"].all()
    faltam = len(alunos_avaliados) - alunos_avaliados["Homologado"].sum()
    
    if todos_homologados:
        st.success("✅ Excelente! Todos os pareceres foram lidos e homologados.")
        st.write("Clique abaixo para enviar os e-mails para toda a turma de uma só vez.")
        
        # Botão centralizado e largo para destacar no final da página
        _, col_botao_lote, _ = st.columns([1, 2, 1])
        with col_botao_lote:
            if st.button("🚀 ENVIAR FEEDBACKS PARA TODA A TURMA", type="primary", use_container_width=True):
                st.balloons()
                st.success("Disparo em lote realizado com sucesso para todos os alunos!")
    else:
        st.warning(f"⚠️ Faltam homologar **{faltam} parecer(es)**.")
        st.info("Aguardando revisão de todos os alunos para liberar o envio em massa.")
        
        _, col_botao_lote, _ = st.columns([1, 2, 1])
        with col_botao_lote:
            st.button("🚀 ENVIAR FEEDBACKS PARA TODA A TURMA", type="primary", use_container_width=True, disabled=True)

# ---------------------------------------------------------
# ABA 4: DESEMPENHO (DASHBOARD ANALÍTICO)
# ---------------------------------------------------------
with aba_dashboard:
    st.header("📈 Painel de Gestão Estratégica")
    st.write("Analise o rendimento da turma e identifique lacunas de aprendizagem.")
    
    col_dash_escola, col_dash_turma, col_dash_prova = st.columns(3)
    with col_dash_escola:
        st.selectbox("Filtrar Escola:", ["Colégio Estadual Padrão", "Instituto Federal", "Escola Particular Exemplo"], key="dash_escola")
    with col_dash_turma:
        st.selectbox("Filtrar Turma:", ["1º Ano A", "2º Ano B", "3º Ano C"], key="dash_turma")
    with col_dash_prova:
        st.selectbox("Filtrar Avaliação:", ["Visão Geral da Turma", "1ª Avaliação - Cinemática", "2ª Avaliação - Dinâmica"], key="dash_prova")

    st.markdown("---")
    
    # --- MÉTRICAS PRINCIPAIS (KPIs) ---
    st.subheader("Métricas da Turma")
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    
    with col_kpi1:
        st.metric(label="Média da Turma", value="7.2", delta="0.5 pontos (vs. Prova anterior)")
    with col_kpi2:
        st.metric(label="Taxa de Presença", value="92%", delta="-2% (Faltas)", delta_color="inverse")
    with col_kpi3:
        st.metric(label="Taxa de Acerto (Geral)", value="68%")
    with col_kpi4:
        st.metric(label="Conceito Crítico", value="Inércia", help="Conceito com maior índice de erros relatados pela IA.")

    st.markdown("---")
    
    # --- GRÁFICOS DE ANÁLISE ---
    col_grafico1, col_grafico2 = st.columns(2)
    
    with col_grafico1:
        st.markdown("### 📊 Desempenho por Questão")
        st.info("Percentual de acertos da turma em cada questão da prova.")
        dados_questoes = pd.DataFrame({
            "Questão": ["Q1 (Teoria)", "Q2 (Cálculo)", "Q3 (Aplicação)", "Q4 (Gráfico)"],
            "Acertos (%)": [85, 45, 60, 90]
        }).set_index("Questão")
        st.bar_chart(dados_questoes)

    with col_grafico2:
        st.markdown("### 🧠 Diagnóstico da Inteligência Artificial")
        st.info("Mapeamento das principais dificuldades e deficiências metodológicas.")
        
        st.error("📉 **Alerta Crítico:** 55% dos alunos erraram a conversão de unidades na Questão 2 (km/h para m/s).")
        st.warning("⚠️ **Atenção Conceitual:** Confusão generalizada entre os conceitos de Massa e Peso na Questão 3.")
        
        st.markdown("**Recomendação Padrão:**")
        st.write("> *Sugere-se uma breve revisão focada em Análise Dimensional.*")
        
        # --- NOVA FUNCIONALIDADE: ESTRATÉGIA INTEGRADA ---
        with st.expander("✨ Estratégia Pedagógica Integrada (Sem atrasar o calendário)"):
            st.write("Forneça o próximo conteúdo do seu plano de ensino para a IA criar uma estratégia que remedeie as lacunas sem interromper o fluxo das aulas.")
            prox_conteudo = st.text_input("Próximo conteúdo a ser ministrado:", placeholder="Ex: Força de Atrito")
            
            if st.button("Gerar Integração Pedagógica", use_container_width=True):
                if prox_conteudo:
                    st.success("✅ **Estratégia Gerada:**")
                    st.write(f"> *Ao iniciar a aula sobre **{prox_conteudo}**, inicie com um problema-desafio que exija o cálculo da Força Normal (onde o Peso importa) e peça para calcularem a velocidade final em m/s. Isso forçará a revisão da conversão de unidades (lacuna atual) como um degrau necessário para compreender o novo conceito de Atrito, criando uma ancoragem natural sem dedicar uma aula exclusiva a revisões.*")
                else:
                    st.warning("Por favor, digite o próximo conteúdo.")

    st.markdown("---")
    
    # --- NOVA FUNCIONALIDADE: DESEMPENHO INDIVIDUAL ---
    st.markdown("### 👤 Raio-X Individual (Micro-Dashboard)")
    st.write("Analise o perfil de aprendizagem de um aluno específico para conselhos de classe ou tutoria.")
    
    # Aqui, no mundo real, puxaríamos a lista de alunos do banco de dados (Aba 3)
    aluno_selecionado = st.selectbox(
        "Selecione o Aluno:", 
        ["Ana Clara", "Gabriel Souza", "João Pedro", "Mariana Silva"],
        label_visibility="collapsed"
    )
    
    # Cartão de informações do aluno simuladas
    col_ind1, col_ind2, col_ind3 = st.columns([1, 2, 1])
    with col_ind1:
        st.metric(label="Nota Final", value="8.5", delta="Acima da Média")
    with col_ind2:
        st.markdown("**🔍 Perfil Cognitivo Detectado:**")
        st.write("Excelente raciocínio lógico-matemático (100% de acerto nos cálculos), mas apresenta ligeira dificuldade na interpretação de enunciados longos.")
    with col_ind3:
        st.markdown("**🎯 Foco de Melhoria:**")
        st.write("Leitura e abstração de problemas.")

    st.markdown("---")
    
    # --- EXPORTAÇÃO ---
    st.markdown("### 🖨️ Relatórios e Exportação")
    col_relatorio1, col_relatorio2, _ = st.columns([1, 1, 2])
    with col_relatorio1:
        st.button("📥 Baixar Relatório (PDF)", use_container_width=True)
    with col_relatorio2:
        st.button("📊 Exportar Notas (Excel)", use_container_width=True)