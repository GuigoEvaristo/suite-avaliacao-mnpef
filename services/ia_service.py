# services/ia_service.py
import re
import streamlit as st
from google import genai
from PIL import Image

def analisar_prova_com_ia(caminho_imagem):
    """
    Comunica com o Gemini 3.5 Flash para realizar a Segmentação Semântica
    e a Análise Pedagógica unificadas, com tratamento de exceções robusto.
    """
    try:
        # 1. Tenta abrir a imagem. Se falhar, o ficheiro está corrompido.
        try:
            imagem_ia = Image.open(caminho_imagem)
        except Exception as img_err:
             raise ValueError("O arquivo de imagem parece estar corrompido ou num formato não suportado.")

        # 2. Verifica a existência da chave API.
        if "GEMINI_API_KEY" not in st.secrets or not st.secrets["GEMINI_API_KEY"]:
            raise ConnectionError("Chave da API da Google não encontrada. Por favor, verifique o ficheiro secrets.toml.")

        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        
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
        
        # 3. Tenta fazer a requisição à Google. Falhas aqui são problemas de rede ou do servidor.
        try:
             resposta = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=[prompt_unificado, imagem_ia]
             )
        except Exception as api_err:
             raise ConnectionError(f"Falha na comunicação com a Inteligência Artificial: {api_err}. Verifique a sua ligação à internet.")
        
        texto_resposta = resposta.text
        resultado = {"parecer": "", "coordenadas": None}
        
        # 4. Extrai a seção pedagógica com fallback caso a IA não siga a formatação exata.
        if "[PARECER PEDAGÓGICO]" in texto_resposta:
            try:
                # Tenta dividir de forma limpa
                resultado["parecer"] = texto_resposta.split("[PARECER PEDAGÓGICO]")[1].split("[COORDENADAS]")[0].strip()
            except IndexError:
                 # Se a string existir, mas não na estrutura esperada, devolve o texto inteiro.
                 resultado["parecer"] = texto_resposta.strip()
        else:
            resultado["parecer"] = texto_resposta.strip() 
            
        # 5. Extrai as coordenadas usando Expressão Regular
        match_coords = re.search(r'COORDINATES=\[(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\]', texto_resposta)
        if match_coords:
            resultado["coordenadas"] = list(map(int, match_coords.groups()))
            
        return resultado
        
    except ValueError as ve:
        raise ValueError(ve) # Re-lança erros de ficheiro
    except ConnectionError as ce:
        raise ConnectionError(ce) # Re-lança erros de ligação/API
    except Exception as e:
        raise Exception(f"Ocorreu um erro interno inesperado durante a análise: {e}")