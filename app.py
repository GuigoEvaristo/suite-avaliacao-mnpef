# app.py
import streamlit as st
import os
from fabri_ava import fabricar_prova
from corretor_av import realizar_recorte_via_coordenadas_ia
from services.ia_service import analisar_prova_com_ia
from database.db_manager import (
    iniciar_banco, registar_usuario, validar_login, 
    adicionar_escola, buscar_escolas_por_usuario,
    salvar_correcao, buscar_historico_por_usuario_e_escola
)

st.set_page_config(page_title="Corretor Inteligente - MNPEF", layout="centered")
iniciar_banco()

# =========================================================
# ESTADO DA SESSÃO
# =========================================================
if "autenticado" not in st.session_state: st.session_state["autenticado"] = False
if "usuario_logado" not in st.session_state: st.session_state["usuario_logado"] = None
if "escola_ativa" not in st.session_state: st.session_state["escola_ativa"] = None

# =========================================================
# PORTA 1: SENHA GLOBAL
# =========================================================
if not st.session_state["autenticado"]:
    st.title("🔒 Acesso Restrito ao Projeto")
    st.write("Insira a senha global do MNPEF para acessar o ambiente.")
    senha_digitada = st.text_input("Senha Global:", type="password")
    if st.button("Entrar no Sistema"):
        if senha_digitada == st.secrets["SENHA_ACESSO"]:
            st.session_state["autenticado"] = True
            st.rerun()
        else: st.error("Senha global incorreta.")
    st.stop()

# =========================================================
# PORTA 2: LOGIN / REGISTO DO PROFESSOR (Sem escola fixa)
# =========================================================
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
            if not (nome_reg and email_reg and senha_reg):
                st.warning("Preencha nome, e-mail e senha.")
            elif senha_reg != senha_conf:
                st.error("As senhas não coincidem.")
            else:
                sucesso, msg = registar_usuario(nome_reg, email_reg, tel_reg, senha_reg)
                if sucesso: st.success(f"{msg} Vá para a aba 'Fazer Login'.")
                else: st.error(msg)
    st.stop()

# =========================================================
# O APLICATIVO PRINCIPAL (Com Contexto de Escola)
# =========================================================
nome_prof = st.session_state["usuario_logado"]["nome"]
usuario_id = st.session_state["usuario_logado"]["id"]

col1, col2 = st.columns([0.8, 0.2])
with col1: st.title(f"Olá, Prof. {nome_prof} 👋")
with col2: 
    st.write("")
    if st.button("🚪 Sair"):
        st.session_state["usuario_logado"] = None
        st.session_state["escola_ativa"] = None
        st.rerun()

st.markdown("---")

# --- SELETOR DE CONTEXTO (AS ESCOLAS DO PROFESSOR) ---
st.subheader("🏫 Ambiente de Trabalho")
escolas_do_prof = buscar_escolas_por_usuario(usuario_id)

if not escolas_do_prof:
    st.warning("Você ainda não possui escolas cadastradas.")
    nova_escola = st.text_input("Nome da Escola/Colégio:")
    if st.button("Cadastrar Primeira Escola"):
        if nova_escola:
            adicionar_escola(usuario_id, nova_escola.strip())
            st.rerun()
    st.stop() # Bloqueia o sistema até ter pelo menos uma escola

else:
    col_escola, col_nova = st.columns([0.7, 0.3])
    with col_escola:
        escola_selecionada = st.selectbox("Atuando agora em:", escolas_do_prof)
        st.session_state["escola_ativa"] = escola_selecionada
    with col_nova:
        with st.expander("+ Nova Escola"):
            extra_escola = st.text_input("Nome:")
            if st.button("Adicionar"):
                if extra_escola:
                    adicionar_escola(usuario_id, extra_escola.strip())
                    st.rerun()

st.markdown("---")

# =========================================================
# ABAS DO SISTEMA (Filtradas pela escola_ativa)
# =========================================================
aba_fabricar, aba_corrigir, aba_historico = st.tabs([
    "📝 Fabricar Prova", "📸 Corrigir Avaliação", "📊 Histórico"
])

# ABA 1: FABRICAR PROVA (Usa a escola automaticamente)
with aba_fabricar:
    st.header(f"Elaboração de Prova - {st.session_state['escola_ativa']}")
    turma = st.text_input("Qual é a turma?", placeholder="Ex: 3º Ano A").strip()
    num_questoes = st.number_input("Número de questões:", min_value=1, max_value=10, value=1)
    
    questoes_configuradas = []
    todos_enunciados_preenchidos = True
    for i in range(int(num_questoes)):
        texto_q = st.text_area(f"Enunciado da Questão {i+1}:", key=f"texto_{i}").strip()
        if not texto_q: todos_enunciados_preenchidos = False
        tipo_q = st.radio(f"Formato da Questão {i+1}:", ["calculo", "texto"], key=f"tipo_{i}")
        questoes_configuradas.append({"texto": texto_q, "tipo": tipo_q})

    if st.button("Gerar PDF"):
        if not turma: st.warning("O campo 'Turma' não pode estar vazio.")
        elif not todos_enunciados_preenchidos: st.warning("Preencha todos os enunciados.")
        else:
            with st.spinner("Compilando..."):
                try:
                    # Injeta a escola ativa automaticamente
                    dados_prova = {"escola": st.session_state["escola_ativa"], "turma": turma, "questoes": questoes_configuradas}
                    fabricar_prova(dados_prova, "modelo.tex", "prova_gerada_app")
                    if os.path.exists("prova_gerada_app.pdf"):
                        st.success("✅ Avaliação estruturada!")
                        with open("prova_gerada_app.pdf", "rb") as pdf_file:
                            st.download_button("📥 Baixar PDF", data=pdf_file, file_name=f"Prova_{turma.replace(' ', '_')}.pdf", mime="application/pdf")
                    else: st.error("❌ Erro na compilação do LaTeX.")
                except Exception as e: st.error(f"❌ Falha crítica: {e}")

# ABA 2: CORRIGIR (Tratamento de Exceções Totalmente Restaurado)
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
                    
                    # Salva usando o ID do professor E a Escola Ativa
                    salvar_correcao(usuario_id, st.session_state["escola_ativa"], resultado_ia["parecer"], resultado_ia["coordenadas"])
                    
                    st.success("✅ Análise guardada no Histórico!")
                    st.info(resultado_ia["parecer"])

                    if resultado_ia["coordenadas"]:
                        try:
                             caminho_recorte = realizar_recorte_via_coordenadas_ia(caminho_temp, resultado_ia["coordenadas"])
                             if caminho_recorte: st.image(caminho_recorte, caption="Bloco extraído")
                        except Exception as crop_err: st.error(f"❌ Erro ao cortar imagem: {crop_err}")
                
                # QA RIGOROSO RESTAURADO
                except ValueError as ve: st.error(f"❌ Erro de ficheiro: {ve}")
                except ConnectionError as ce: st.error(f"❌ Erro de Ligação/Google: {ce}")
                except Exception as e: st.error(f"❌ Erro interno: {e}")

# ABA 3: HISTÓRICO (Filtrado por Prof + Escola)
with aba_historico:
    st.header(f"Arquivo Pedagógico: {st.session_state['escola_ativa']}")
    
    if st.button("🔄 Atualizar"): st.rerun()
        
    registos = buscar_historico_por_usuario_e_escola(usuario_id, st.session_state["escola_ativa"])
    
    if not registos:
        st.info("Nenhuma correção encontrada para esta escola.")
    else:
        for reg in registos:
            with st.expander(f"Data: {reg[0]}"):
                st.markdown(reg[1])