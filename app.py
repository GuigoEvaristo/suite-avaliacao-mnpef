# app.py
import streamlit as st
import os
from fabri_ava import fabricar_prova
from corretor_av import realizar_recorte_via_coordenadas_ia
from services.ia_service import analisar_prova_com_ia 

st.set_page_config(page_title="Corretor Inteligente - MNPEF", layout="centered")

st.title("🤖 Ambiente de Gestão de Avaliações")
st.write("Bem-vindo! Escolha uma das opções abaixo para gerenciar as suas avaliações de Física.")

aba_fabricar, aba_corrigir = st.tabs(["📝 Fabricar Prova", "📸 Corrigir Avaliação"])

# ---------------------------------------------------------
# CONTEÚDO DA ABA 1: FABRICAR PROVA
# ---------------------------------------------------------
with aba_fabricar:
    st.header("Formulário de Elaboração de Prova")
    st.write("Preencha os dados abaixo para gerar o PDF padronizado.")

    colegio = st.selectbox(
        "Para qual colégio será realizada a prova?",
        ["Selecione o colégio...", "Instituto de Educação de Dourados", "Colégio Estadual X", "Escola Particular Y"]
    )
    turma = st.text_input("Qual é a turma?", placeholder="Ex: 3º Ano A").strip()
    num_questoes = st.number_input("Número de questões:", min_value=1, max_value=10, value=1, step=1)

    st.markdown("---")
    questoes_configuradas = []
    
    # Validação de formulário: Verifica se todos os enunciados estão preenchidos.
    todos_enunciados_preenchidos = True
    
    for i in range(int(num_questoes)):
        st.markdown(f"##### **Questão {i+1}**")
        texto_q = st.text_area(f"Enunciado da Questão {i+1}:", key=f"texto_{i}").strip()
        
        if not texto_q:
             todos_enunciados_preenchidos = False
             
        tipo_q = st.radio(
            f"Formato da resposta da Questão {i+1}:",
            options=["calculo", "texto"],
            format_func=lambda x: "Resolução Matemática (Cálculo)" if x == "calculo" else "Justificativa Conceitual (Texto)",
            key=f"tipo_{i}"
        )
        questoes_configuradas.append({"texto": texto_q, "tipo": tipo_q})
        st.markdown(" ")

    if st.button("Salvar e Gerar PDF para Impressão"):
        # QA: Mensagens de erro específicas
        if colegio == "Selecione o colégio...":
            st.warning("⚠️ Atenção: Por favor, selecione um colégio válido na lista.")
        elif not turma:
            st.warning("⚠️ Atenção: O campo 'Turma' não pode estar vazio.")
        elif not todos_enunciados_preenchidos:
            st.warning("⚠️ Atenção: Por favor, preencha o enunciado de todas as questões antes de gerar o PDF.")
        else:
            with st.spinner("A compilar código LaTeX nos bastidores..."):
                try:
                    dados_prova = {"escola": colegio, "turma": turma, "questoes": questoes_configuradas}
                    fabricar_prova(dados_prova, "modelo.tex", "prova_gerada_app")
                    
                    if os.path.exists("prova_gerada_app.pdf"):
                        st.success("✅ Avaliação estruturada com sucesso!")
                        with open("prova_gerada_app.pdf", "rb") as pdf_file:
                            st.download_button(
                                label="📥 Baixar PDF da Prova Pronta",
                                data=pdf_file,
                                file_name=f"Avaliacao_Fisica_{turma.replace(' ', '_')}.pdf",
                                mime="application/pdf"
                            )
                    else:
                        st.error("❌ Ocorreu um erro na compilação do ficheiro LaTeX. Verifique se o seu sistema tem o compilador instalado corretamente.")
                except Exception as latex_err:
                    st.error(f"❌ Falha crítica na geração do PDF: {latex_err}")

# ---------------------------------------------------------
# CONTEÚDO DA ABA 2: CORRIGIR AVALIAÇÃO
# ---------------------------------------------------------
with aba_corrigir:
    st.header("Captura e Correção de Respostas")
    st.write("Envie a foto INTEIRA da folha de respostas tirada pelo smartphone.")

    # Limita estritamente aos formatos de imagem.
    foto_prova = st.file_uploader("Selecione ou tire a foto da prova:", type=["png", "jpg", "jpeg"])

    if foto_prova is not None:
        caminho_temp = "upload_temp.jpg"
        
        # Tratamento seguro para gravação de ficheiros
        try:
             with open(caminho_temp, "wb") as f:
                 f.write(foto_prova.getbuffer())
        except Exception as fs_err:
             st.error(f"❌ Erro ao guardar o ficheiro temporário: {fs_err}")
             st.stop() # Para a execução se não conseguir guardar
            
        st.image(caminho_temp, caption="Captura recebida (Visão Inteira)", use_container_width=True)
        
        if st.button("Executar Análise Multimodal (Segmentação Semântica + IA)"):
            with st.spinner("A conectar aos servidores da IA para análise unificada..."):
                try:
                    # O serviço modular agora devolve erros tipados
                    resultado_ia = analisar_prova_com_ia(caminho_temp)
                    
                    st.markdown("### 📝 Parecer Pedagógico da IA")
                    st.success("✅ Análise concluída.")
                    st.info(resultado_ia["parecer"])

                    if resultado_ia["coordenadas"]:
                        st.write("---")
                        st.write("🛠️ Visualização da Segmentação Semântica Realizada pela IA:")
                        
                        try:
                             caminho_recorte = realizar_recorte_via_coordenadas_ia(
                                 caminho_temp, resultado_ia["coordenadas"]
                             )
                             if caminho_recorte:
                                 st.image(caminho_recorte, caption="Bloco extraído semanticamente pelo Gemini")
                             else:
                                 st.warning("⚠️ Não foi possível gerar a visualização do recorte matemático, mas a análise pedagógica acima continua válida.")
                        except Exception as crop_err:
                             st.error(f"❌ Erro ao tentar cortar a imagem: {crop_err}")
                    else:
                        st.warning("⚠️ A IA forneceu o parecer, mas não conseguiu delimitar visualmente a caligrafia com precisão.")
                        
                # Apanha as nossas exceções específicas para dar feedback claro ao utilizador
                except ValueError as ve:
                    st.error(f"❌ Erro de ficheiro: {ve}")
                except ConnectionError as ce:
                     st.error(f"❌ Erro de Ligação: {ce}")
                except Exception as e:
                    st.error(f"❌ Ocorreu um erro interno na aplicação: {e}")