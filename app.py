# app.py
import streamlit as st
import os
import datetime
from fabri_ava import fabricar_prova
from corretor_av import realizar_recorte_via_coordenadas_ia
from services.ia_service import analisar_prova_com_ia
from database.db_manager import (
    iniciar_banco, registar_usuario, validar_login, 
    adicionar_escola, buscar_escolas_por_usuario,
    salvar_correcao, buscar_historico_por_usuario_e_escola,
    salvar_prova_fabricada, buscar_provas_por_usuario_e_escola, buscar_pdf_prova
)

st.set_page_config(page_title="Suíte de Avaliação para Professores - MNPEF", layout="centered", page_icon="📝")
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

# =========================================================
# ABAS DO SISTEMA
# =========================================================
aba_fabricar, aba_corrigir, aba_historico = st.tabs([
    "📝 Fabricar Prova", "📸 Corrigir Avaliação", "📊 Histórico"
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

    # --- GUIA RÁPIDO DE FORMATAÇÃO E FÓRMULAS ---
    with st.expander("💡 Guia Rápido de Formatação e Fórmulas Matemáticas"):
        st.markdown("""
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
# ABA 2: CORRIGIR (MANTIDA INTACTA)
# ---------------------------------------------------------
with aba_corrigir:
    st.header("Captura e Correção")
    foto_prova = st.file_uploader("Envie a foto da prova:", type=["png", "jpg", "jpeg"])
    if foto_prova:
        caminho_temp = "upload_temp.jpg"
        try:
             with open(caminho_temp, "wb") as f: f.write(foto_prova.getbuffer())
        except Exception as fs_err:
             st.error(f"❌ Erro ao guardar ficheiro temporário: {fs_err}"); st.stop()
        st.image(caminho_temp, caption="Visão Inteira", use_container_width=True)
        if st.button("Executar Análise Multimodal"):
            with st.spinner("Processando e guardando no arquivo da escola..."):
                try:
                    resultado_ia = analisar_prova_com_ia(caminho_temp)
                    salvar_correcao(usuario_id, st.session_state["escola_ativa"], resultado_ia["parecer"], resultado_ia["coordenadas"])
                    st.success("✅ Análise guardada no Histórico!")
                    st.info(resultado_ia["parecer"])
                    if resultado_ia["coordenadas"]:
                        try:
                             caminho_recorte = realizar_recorte_via_coordenadas_ia(caminho_temp, resultado_ia["coordenadas"])
                             if caminho_recorte: st.image(caminho_recorte, caption="Bloco extraído")
                        except Exception as crop_err: st.error(f"❌ Erro ao cortar imagem: {crop_err}")
                except Exception as e: st.error(f"❌ Erro: {e}")

                # QA RIGOROSO RESTAURADO
                except ValueError as ve: 
                    st.error(f"❌ Erro de ficheiro: {ve}")
                except ConnectionError as ce: 
                    st.error(f"❌ Erro de Ligação/Google: {ce}")
                except Exception as e: 
                    st.error(f"❌ Erro interno: {e}")

# ---------------------------------------------------------
# ABA 3: HISTÓRICO (AGORA DIVIDIDO)
# ---------------------------------------------------------
with aba_historico:
    st.header(f"Arquivo Pedagógico: {st.session_state['escola_ativa']}")
    
    sub_aba_provas, sub_aba_correcoes = st.tabs(["📄 Provas Fabricadas", "📝 Correções Realizadas"])
    
    with sub_aba_provas:
        st.write("Baixe novamente os PDFs das avaliações que você já criou.")
        provas_salvas = buscar_provas_por_usuario_e_escola(usuario_id, st.session_state["escola_ativa"])
        if not provas_salvas:
            st.info("Nenhuma prova fabricada para esta escola ainda.")
        else:
            for p in provas_salvas:
                # p = (id, disciplina, serie, turma, etapa, data_criacao)
                col_info, col_btn = st.columns([0.8, 0.2])
                with col_info:
                    st.markdown(f"**{p[4]} - {p[1]}** | {p[2]} {p[3]} *(Criada em {p[5]})*")
                with col_btn:
                    if st.button("Recuperar PDF", key=f"recuperar_pdf_{p[0]}"):
                        dados_pdf = buscar_pdf_prova(p[0])
                        if dados_pdf:
                            st.download_button(
                                label="📥 Baixar",
                                data=dados_pdf[0],
                                file_name=f"{dados_pdf[3]}_{dados_pdf[1]}_{dados_pdf[2]}.pdf",
                                mime="application/pdf",
                                key=f"down_pdf_{p[0]}"
                            )
                st.markdown("---")
                
    with sub_aba_correcoes:
        registos = buscar_historico_por_usuario_e_escola(usuario_id, st.session_state["escola_ativa"])
        if not registos:
            st.info("Nenhuma correção encontrada para esta escola.")
        else:
            for reg in registos:
                with st.expander(f"Correção em: {reg[0]}"):
                    st.markdown(reg[1])