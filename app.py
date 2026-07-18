# app.py
import streamlit as st
import os
from fabri_ava import fabricar_prova
from corretor_av import realizar_recorte_via_coordenadas_ia
from services.ia_service import analisar_prova_com_ia
from database.db_manager import iniciar_banco, salvar_correcao, buscar_historico

st.set_page_config(page_title="Corretor Inteligente - MNPEF", layout="centered")

# =========================================================
# SISTEMA DE AUTENTICAÇÃO (TELA DE SENHA)
# =========================================================
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🔒 Acesso Restrito")
    st.write("Por favor, insira a senha de acesso para utilizar o sistema de correção.")
    
    senha_digitada = st.text_input("Senha:", type="password")
    
    if st.button("Entrar"):
        if senha_digitada == st.secrets["SENHA_ACESSO"]:
            st.session_state["autenticado"] = True
            st.rerun() # Recarrega a página agora com acesso liberado
        else:
            st.error("Senha incorreta. Tente novamente.")
            
    st.stop() # Esta linha é crucial: impede que o resto do código rode se não houver senha

# =========================================================
# O CÓDIGO ABAIXO SÓ RODA SE A SENHA FOR CORRETA
# =========================================================

# Inicializa o banco de dados
iniciar_banco()

st.title("🤖 Ambiente de Gestão de Avaliações")
st.write("Bem-vindo! Escolha uma das opções abaixo para gerenciar as suas avaliações de Física.")

aba_fabricar, aba_corrigir, aba_historico = st.tabs([
    "📝 Fabricar Prova", 
    "📸 Corrigir Avaliação", 
    "📊 Histórico de Correções"
])

# ---------------------------------------------------------
# CONTEÚDO DA ABA 1: FABRICAR PROVA
# ---------------------------------------------------------
with aba_fabricar:
    st.header("Formulário de Elaboração de Prova")
    colegio = st.selectbox(
        "Para qual colégio será realizada a prova?",
        ["Selecione o colégio...", "Instituto de Educação de Dourados", "Colégio Estadual X", "Escola Particular Y"]
    )
    turma = st.text_input("Qual é a turma?", placeholder="Ex: 3º Ano A").strip()
    num_questoes = st.number_input("Número de questões:", min_value=1, max_value=10, value=1, step=1)

    st.markdown("---")
    questoes_configuradas = []
    todos_enunciados_preenchidos = True
    
    for i in range(int(num_questoes)):
        st.markdown(f"##### **Questão {i+1}**")
        texto_q = st.text_area(f"Enunciado da Questão {i+1}:", key=f"texto_{i}").strip()
        if not texto_q: todos_enunciados_preenchidos = False
             
        tipo_q = st.radio(
            f"Formato da resposta da Questão {i+1}:",
            options=["calculo", "texto"],
            format_func=lambda x: "Resolução Matemática (Cálculo)" if x == "calculo" else "Justificativa Conceitual (Texto)",
            key=f"tipo_{i}"
        )
        questoes_configuradas.append({"texto": texto_q, "tipo": tipo_q})

    if st.button("Salvar e Gerar PDF para Impressão"):
        if colegio == "Selecione o colégio...":
            st.warning("⚠️ Atenção: Por favor, selecione um colégio válido na lista.")
        elif not turma:
            st.warning("⚠️ Atenção: O campo 'Turma' não pode estar vazio.")
        elif not todos_enunciados_preenchidos:
            st.warning("⚠️ Atenção: Por favor, preencha o enunciado de todas as questões.")
        else:
            with st.spinner("A compilar código LaTeX..."):
                try:
                    dados_prova = {"escola": colegio, "turma": turma, "questoes": questoes_configuradas}
                    fabricar_prova(dados_prova, "modelo.tex", "prova_gerada_app")
                    if os.path.exists("prova_gerada_app.pdf"):
                        st.success("✅ Avaliação estruturada com sucesso!")
                        with open("prova_gerada_app.pdf", "rb") as pdf_file:
                            st.download_button("📥 Baixar PDF da Prova Pronta", data=pdf_file, file_name=f"Avaliacao_Fisica_{turma.replace(' ', '_')}.pdf", mime="application/pdf")
                    else:
                        st.error("❌ Ocorreu um erro na compilação do ficheiro LaTeX. Verifique a instalação do compilador.")
                except Exception as latex_err:
                    st.error(f"❌ Falha crítica na geração do PDF: {latex_err}")

# ---------------------------------------------------------
# CONTEÚDO DA ABA 2: CORRIGIR AVALIAÇÃO
# ---------------------------------------------------------
with aba_corrigir:
    st.header("Captura e Correção de Respostas")
    foto_prova = st.file_uploader("Selecione ou tire a foto da prova:", type=["png", "jpg", "jpeg"])

    if foto_prova is not None:
        caminho_temp = "upload_temp.jpg"
        try:
             with open(caminho_temp, "wb") as f:
                 f.write(foto_prova.getbuffer())
        except Exception as fs_err:
             st.error(f"❌ Erro ao guardar o ficheiro temporário: {fs_err}")
             st.stop()
            
        st.image(caminho_temp, caption="Captura recebida (Visão Inteira)", use_container_width=True)
        
        if st.button("Executar Análise Multimodal (Segmentação Semântica + IA)"):
            with st.spinner("A processar e a guardar os resultados na base de dados..."):
                try:
                    resultado_ia = analisar_prova_com_ia(caminho_temp)
                    
                    salvar_correcao(resultado_ia["parecer"], resultado_ia["coordenadas"])
                    
                    st.success("✅ Análise concluída e guardada no Histórico!")
                    st.markdown("### 📝 Parecer Pedagógico da IA")
                    st.info(resultado_ia["parecer"])

                    if resultado_ia["coordenadas"]:
                        st.write("---")
                        try:
                             caminho_recorte = realizar_recorte_via_coordenadas_ia(caminho_temp, resultado_ia["coordenadas"])
                             if caminho_recorte: st.image(caminho_recorte, caption="Bloco extraído semanticamente pelo Gemini")
                             else: st.warning("⚠️ Não foi possível gerar a visualização do recorte matemático, mas a análise pedagógica acima continua válida.")
                        except Exception as crop_err:
                             st.error(f"❌ Erro ao cortar a imagem: {crop_err}")
                    else:
                         st.warning("⚠️ A IA forneceu o parecer, mas não conseguiu delimitar visualmente a caligrafia com precisão.")
                
                except ValueError as ve:
                    st.error(f"❌ Erro de ficheiro: {ve}")
                except ConnectionError as ce:
                     st.error(f"❌ Erro de Ligação: {ce}")
                except Exception as e:
                    st.error(f"❌ Ocorreu um erro interno na aplicação: {e}")

# ---------------------------------------------------------
# CONTEÚDO DA ABA 3: HISTÓRICO DE AVALIAÇÕES
# ---------------------------------------------------------
with aba_historico:
    st.header("Auditoria e Rastreabilidade")
    st.write("Consulte aqui todos os pareceres pedagógicos emitidos anteriormente pelo sistema.")
    
    if st.button("🔄 Atualizar Histórico"):
        st.rerun()
        
    registos = buscar_historico()
    
    if len(registos) == 0:
        st.info("A base de dados está vazia. Realize a correção de uma prova para preencher o histórico.")
    else:
        for registo in registos:
            data_hora = registo[0]
            parecer_salvo = registo[1]
            
            with st.expander(f"Correção realizada em: {data_hora}"):
                st.markdown(parecer_salvo)