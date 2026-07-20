# fabri_ava.py
import os
import subprocess

def fabricar_prova(dados_prova, caminho_tex, nome_base_saida):
    """
    Gera um ficheiro .tex a partir de metadados dinâmicos e compila para PDF.
    """
    # 1. Extração Segura de Metadados
    escola = dados_prova.get("escola", "Instituição Não Informada")
    endereco = dados_prova.get("endereco", "")
    disciplina = dados_prova.get("disciplina", "Física")
    serie = dados_prova.get("serie", "")
    turma = dados_prova.get("turma", "")
    etapa = dados_prova.get("etapa", "Avaliação")
    prof_nome = dados_prova.get("prof_nome", "")
    prof_email = dados_prova.get("prof_email", "")
    instrucoes = dados_prova.get("instrucoes", "")
    data_prova = dados_prova.get("data", "")
    
    # 2. Construção do Cabeçalho Padrão (Sem dependências externas locais)
    latex = r"""\documentclass[11pt,addpoints]{exam}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[brazil]{babel}
\usepackage{amsmath, amssymb}
\usepackage{graphicx}
\usepackage{geometry}
\geometry{a4paper, margin=2cm}

\pagestyle{headandfoot}
\firstpageheader{}{}{}
\runningheader{\textit{""" + escola + r"""}}{\textit{""" + disciplina + r"""}}{\textit{Página \thepage\ de \numpages}}
\runningfooter{}{}{}

\begin{document}

% --- BLOCO DO CABEÇALHO SUPERIOR ---
\begin{center}
    \textbf{\LARGE """ + escola + r"""} \\
    """
    
    if endereco:
        latex += r"""\vspace{0.1cm} \small """ + endereco + r""" \\"""
        
    latex += r"""
    \vspace{0.2cm}
    \textbf{Prof(a).:} """ + prof_nome + r""" \quad \textbf{E-mail:} """ + prof_email + r""" \\
    \vspace{0.3cm}
    \textbf{\Large """ + etapa + r""" - """ + disciplina + r"""} \\
    \vspace{0.1cm}
    \textbf{Data:} """ + data_prova + r""" \quad \textbf{Série:} """ + serie + r""" \quad \textbf{Turma:} """ + turma + r"""
\end{center}

\vspace{0.2cm}
\noindent\makebox[\linewidth]{\rule{\textwidth}{0.6pt}}
\vspace{0.3cm}

% --- BLOCO DO ALUNO ---
\noindent
\textbf{Aluno(a):} \rule{9cm}{0.4pt} \quad \textbf{Nº/Matrícula:} \rule{3cm}{0.4pt} \\
"""
    
    # 3. Processamento de Instruções Dinâmicas (Se houver)
    if instrucoes.strip():
        latex += r"""
\vspace{0.4cm}
\noindent\textbf{Instruções:}
\begin{itemize}
\setlength\itemsep{0em}
"""
        for linha in instrucoes.split('\n'):
            if linha.strip():
                # Escapa caracteres especiais básicos
                linha_segura = linha.strip().replace('%', '\\%').replace('#', '\\#')
                latex += f"    \\item {linha_segura}\n"
        latex += r"""\end{itemize}
\vspace{0.1cm}
\noindent\makebox[\linewidth]{\rule{\textwidth}{0.4pt}}
\vspace{0.4cm}
"""

    # 4. Abertura do Ambiente de Questões
    latex += r"\begin{questions}" + "\n\n"

    # 5. Iterador de Questões Dinâmicas
    for i, q in enumerate(dados_prova.get("questoes", [])):
        enunciado = q.get("enunciado", "").replace('%', '\\%').replace('\n', '\\\\ ')
        tipo = q.get("tipo", "aberta")
        
        latex += f"\\question {enunciado}\n"
        
        # Módulo de Imagem
        imagem_path = q.get("imagem", None)
        if imagem_path and os.path.exists(imagem_path):
            # Garante que a imagem fica centralizada
            latex += r"""\begin{center}
    \includegraphics[max width=0.7\textwidth]{""" + imagem_path + r"""}
\end{center}
"""
        
        # Estrutura por Tipo de Questão
        if tipo == "aberta":
            estilo = q.get("estilo_espaco", "box") # box ou lines
            tamanho = q.get("tamanho_espaco", "medio")
            
            # Mapeia tamanhos (pequeno, médio, grande) para centímetros
            map_tam = {"pequeno": "3cm", "medio": "6cm", "grande": "12cm"}
            tex_tam = map_tam.get(tamanho, "6cm")
            
            if estilo == "box":
                latex += f"\\begin{{solutionorbox}}[{tex_tam}]\n\\end{{solutionorbox}}\n"
            else:
                latex += f"\\begin{{solutionorlines}}[{tex_tam}]\n\\end{{solutionorlines}}\n"
                
        elif tipo == "multipla":
            latex += "\\begin{choices}\n"
            for alt in q.get("alternativas", []):
                alt_segura = alt.replace('%', '\\%')
                latex += f"    \\choice {alt_segura}\n"
            latex += "\\end{choices}\n"
            
        elif tipo == "vf":
            estilo_vf = q.get("estilo_vf", "classico")
            latex += "\\vspace{0.2cm}\n\\begin{itemize}\n"
            if estilo_vf == "somatoria":
                valor = 1
                for af in q.get("afirmacoes", []):
                    af_seg = af.replace('%', '\\%')
                    latex += f"    \\item[({valor:02d})] {af_seg}\n"
                    valor *= 2
            else:
                for af in q.get("afirmacoes", []):
                    af_seg = af.replace('%', '\\%')
                    latex += f"    \\item[(V) (F)] {af_seg}\n"
            latex += "\\end{itemize}\n"

        latex += "\n"

    # 6. Fechamento do Documento
    latex += r"\end{questions}" + "\n"
    latex += r"\end{document}"

    # Salva o arquivo .tex
    with open(caminho_tex, "w", encoding="utf-8") as f:
        f.write(latex)

    # Compilação
    try:
        nome_arquivo_pdf = f"{nome_base_saida}.pdf"
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", caminho_tex],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Erro ao compilar LaTeX: {e}")