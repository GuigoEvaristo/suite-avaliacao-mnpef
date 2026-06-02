import streamlit as st
import os
from PIL import Image
from fabri_ava import fabricar_prova
from corretor_av import testar_recorte_contexto
from google import genai  # Nova biblioteca oficial

st.set_page_config(page_title="Corretor Inteligente - MNPEF", layout="centered")

st.title("🤖 Ambiente de Gestão de Avaliações")
st.write("Bem-vindo! Escolha uma das opções abaixo para gerenciar as suas avaliações de Física.")

aba_fabricar, aba_corrigir = st.tabs(["📝 Fabricar Prova", "📸 Corrigir Avaliação"])

# ---------------------------------------------------------
# CONTEÚDO DA ABA 1: FABRICAR PROVA
# ---------------------------------------------------------
with aba_fabricar:
    st.header("Formulário de Elaboração de Prova")
    st.write("Preencha os dados abaixo para gerar o PDF padronizado com os marcadores de IA.")

    colegio = st.selectbox(
        "Para qual colégio será realizada a prova?",
        ["Selecione o colégio...", "Instituto de Educação de Dourados", "Colégio Estadual X", "Escola Particular Y"]
    )
    turma = st.text_input("Qual é a turma?", placeholder="Ex: 3º Ano A")
    num_questoes = st.number_input("Número de questões:", min_value=1, max_value=10, value=1, step=1)

    st.markdown("---")
    st.subheader("Configuração das Questões")
    
    questoes_configuradas = []
    for i in range(int(num_questoes)):
        st.markdown(f"##### **Questão {i+1}**")
        texto_q = st.text_area(f"Enunciado da Questão {i+1}:", key=f"texto_{i}")
        tipo_q = st.radio(
            f"Formato da resposta da Questão {i+1}:",
            options=["calculo", "texto"],
            format_func=lambda x: "Resolução Matemática (Cálculo)" if x == "calculo" else "Justificativa Conceitual (Texto)",
            key=f"tipo_{i}"
        )
        questoes_configuradas.append({"texto": texto_q, "tipo": tipo_q})
        st.markdown(" ")

    if st.button("Salvar e Gerar PDF para Impressão"):
        if colegio == "Selecione o colégio..." or not turma:
            st.error("Por favor, preencha os dados de cabeçalho (Colégio e Turma) antes de continuar.")
        else:
            with st.spinner("A compilar código LaTeX nos bastidores..."):
                dados_prova = {"escola": colegio, "turma": turma, "questoes": questoes_configuradas}
                fabricar_prova(dados_prova, "modelo.tex", "prova_gerada_app")
                
                if os.path.exists("prova_gerada_app.pdf"):
                    st.success("Avaliação estruturada com sucesso!")
                    with open("prova_gerada_app.pdf", "rb") as pdf_file:
                        st.download_button(
                            label="📥 Baixar PDF da Prova Pronta",
                            data=pdf_file,
                            file_name=f"Avaliacao_Fisica_{turma}.pdf",
                            mime="application/pdf"
                        )
                else:
                    st.error("Ocorreu um erro na compilação do ficheiro LaTeX.")

# ---------------------------------------------------------
# CONTEÚDO DA ABA 2: CORRIGIR AVALIAÇÃO
# ---------------------------------------------------------
with aba_corrigir:
    st.header("Captura e Correção de Respostas")
    st.write("Envie a foto da folha de respostas para processamento da Inteligência Artificial.")

    foto_prova = st.file_uploader("Selecione ou tire a foto da prova:", type=["png", "jpg", "jpeg"])

    if foto_prova is not None:
        with open("upload_temp.jpg", "wb") as f:
            f.write(foto_prova.getbuffer())
            
        st.image("upload_temp.jpg", caption="Captura recebida", use_container_width=True)
        
        if st.button("Executar Algoritmo de Recorte e Análise (IA)"):
            with st.spinner("Passo 1: A isolar a região de cálculo (OpenCV)..."):
                caminho_recorte = testar_recorte_contexto("upload_temp.jpg", "icone_equacao.jpg")
                
            if caminho_recorte:
                st.success("Limites isolados com sucesso! A iniciar a leitura cognitiva...")
                st.image(caminho_recorte, caption="Bloco Matemático Extraído")
                
                with st.spinner("Passo 2: A analisar a resolução física (Gemini 3.5 Flash)..."):
                    try:
                        imagem_ia = Image.open(caminho_recorte)
                        
                        # Nova sintaxe de inicialização do cliente
                        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                        
                        prompt_pedagogico = """
                        Atua como um professor de Física construtivista do ensino secundário.
                        A imagem em anexo contém a resolução manuscrita de um aluno para um problema de física.
                        
                        Por favor, realiza as seguintes tarefas:
                        1. Transcreve o cálculo principal que conseguires identificar.
                        2. Identifica se existem erros conceptuais (e não apenas matemáticos) na passagem das equações.
                        3. Fornece um feedback formativo (direcionado ao aluno) que estimule a reflexão sobre o fenómeno físico envolvido, promovendo uma aprendizagem significativa, em vez de simplesmente lhe dar o valor final correto.
                        
                        Formata a tua resposta de forma clara e encorajadora.
                        """
                        
                        # Chamada atualizada com o modelo correto e nova sintaxe
                        resposta = client.models.generate_content(
                            model='gemini-3.5-flash',
                            contents=[prompt_pedagogico, imagem_ia]
                        )
                        
                        st.markdown("### 📝 Parecer Pedagógico da IA")
                        st.info(resposta.text)
                        
                    except Exception as e:
                        st.error(f"Ocorreu um erro de comunicação com os servidores da IA: {e}")
            else:
                st.error("Erro na Visão Computacional: Não foi possível localizar os marcadores na imagem fornecida.")