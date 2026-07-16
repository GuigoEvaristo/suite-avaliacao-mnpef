import streamlit as st
import os
import re # Biblioteca nativa para Expressões Regulares
from PIL import Image
from fabri_ava import fabricar_prova
from corretor_av import realizar_recorte_via_coordenadas_ia # Import atualizado
from google import genai  # Nova biblioteca oficial

st.set_page_config(page_title="Corretor Inteligente - MNPEF", layout="centered")

st.title("🤖 Ambiente de Gestão de Avaliações")
st.write("Bem-vindo! Escolha uma das opções abaixo para gerenciar as suas avaliações de Física.")

aba_fabricar, aba_corrigir = st.tabs(["📝 Fabricar Prova", "📸 Corrigir Avaliação"])

# ---------------------------------------------------------
# CONTEÚDO DA ABA 1: FABRICAR PROVA (Mantido inalterado)
# ---------------------------------------------------------
with aba_fabricar:
    st.header("Formulário de Elaboração de Prova")
    st.write("Preencha os dados abaixo para gerar o PDF padronizado.")

    colegio = st.selectbox(
        "Para qual colégio será realizada a prova?",
        ["Selecione o colégio...", "Instituto de Educação de Dourados", "Colégio Estadual X", "Escola Particular Y"]
    )
    turma = st.text_input("Qual é a turma?", placeholder="Ex: 3º Ano A")
    num_questoes = st.number_input("Número de questões:", min_value=1, max_value=10, value=1, step=1)

    st.markdown("---")
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
                fabricar_prova(dados_prova, "modelo_av.tex", "prova_gerada_app")
                
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
# CONTEÚDO DA ABA 2: CORRIGIR AVALIAÇÃO (Ajuste de Rota IA)
# ---------------------------------------------------------
with aba_corrigir:
    st.header("Captura e Correção de Respostas")
    st.write("Envie a foto INTEIRA da folha de respostas tirada pelo smartphone.")

    foto_prova = st.file_uploader("Selecione ou tire a foto da prova:", type=["png", "jpg", "jpeg"])

    if foto_prova is not None:
        with open("upload_temp.jpg", "wb") as f:
            f.write(foto_prova.getbuffer())
            
        st.image("upload_temp.jpg", caption="Captura recebida (Visão Inteira)", use_container_width=True)
        
        # Botão unificado de análise
        if st.button("Executar Análise Multimodal (Segmentação Semântica + IA)"):
            with st.spinner("A conectar aos servidores da IA para análise unificada..."):
                try:
                    imagem_ia = Image.open("upload_temp.jpg")
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # PROMPT UNIFICADO DE VANGUARDA
                    # Atua simultaneamente como Professor e Assistente de Visão Computacional
                    prompt_unificado = """
                    Você é um professor de Física construtivista do ensino secundário e especialista em visão computacional.
                    A imagem contém uma folha de prova inteira.

                    Suas tarefas:
                    1. Realize a análise pedagógica completa da caligrafia do aluno presente na área de resposta: transcreva os cálculos que identificar, identifique erros conceptuais e forneça um feedback formativo encorajador que estimule a reflexão, não dando apenas a resposta final.
                    2. Localize visualmente e de forma semântica o bloco de caligrafia do aluno onde está a resolução matemática (os cálculos e explicações).
                    3. Forneça as coordenadas NORMALIZADAS (de 0 a 1000) exatas desse bloco manuscrito.

                    Formate sua resposta em duas partes separadas claramente:
                    [PARECER PEDAGÓGICO] -> Coloque aqui a análise pedagógica em formato Markdown bem formatado.
                    [COORDENADAS] -> Coloque aqui apenas COORDINATES=[ymin, xmin, ymax, xmax].
                    """
                    
                    # Chamada única para a IA processar a imagem inteira
                    resposta = client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=[prompt_unificado, imagem_ia]
                    )
                    
                    # LÓGICA DE CAPTURA E EXIBIÇÃO DA RESPOSTA
                    st.markdown("### 📝 Parecer Pedagógico da IA (Análise da Prova Inteira)")
                    
                    texto_resposta = resposta.text
                    
                    # Tenta extrair a seção pedagógica
                    if "[PARECER PEDAGÓGICO]" in texto_resposta:
                        parecer = texto_resposta.split("[PARECER PEDAGÓGICO]")[1].split("[COORDENADAS]")[0]
                        st.info(parecer)
                    else:
                        st.info(texto_resposta) # Fallback se a IA não separar bem

                    # Tenta extrair as coordenadas usando Expressão Regular
                    coordenadas_extraidas = re.search(r'COORDINATES=\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]', texto_resposta)
                    
                    if coordenadas_extraidas:
                        # Converte os números capturados para uma lista de inteiros
                        ymin, xmin, ymax, xmax = map(int, coordenadas_extraidas.groups())
                        
                        # Chama o utilitário Python para realizar o recorte matemático
                        st.write("---")
                        st.write("🛠️ Visualização da Segmentação Semântica Realizada pela IA:")
                        
                        caminho_recorte = realizar_recorte_via_coordenadas_ia(
                            "upload_temp.jpg", [ymin, xmin, ymax, xmax]
                        )
                        
                        if caminho_recorte:
                            st.image(caminho_recorte, caption="Bloco extraído semanticamente pelo Gemini")
                        else:
                            st.error("Não foi possível gerar a visualização do recorte.")
                    else:
                        st.error("A IA não conseguiu detectar a área de caligrafia para visualização.")
                        
                except Exception as e:
                    st.error(f"Ocorreu um erro de comunicação ou processamento da IA: {e}")