# fabri_ava.py
import os
import subprocess

def fabricar_prova(dados, caminho_template, caminho_saida="prova_final"):
    with open(caminho_template, 'r', encoding='utf-8') as file:
        template = file.read()

    template = template.replace('<<NOME_ESCOLA>>', dados['escola'])
    template = template.replace('<<TURMA>>', dados['turma'])

    bloco_questoes = ""
    for i, questao in enumerate(dados['questoes']):
        numero = i + 1
        
        # LINHA DA QUESTÃO
        bloco_questoes += "\\vspace{0.5cm}\n"
        bloco_questoes += f"\\noindent\\includegraphics[width=0.5cm]{{icone_questao.jpg}} \\textbf{{Questão {numero}:}} {questao['texto']} \\hfill \\includegraphics[width=0.5cm]{{icone_questao.jpg}}\n\n"
        
        # BLOCO DE CÁLCULOS (Abertura no topo esquerdo, fechamento no rodapé direito)
        if questao['tipo'] == 'calculo':
            bloco_questoes += "\\vspace{0.2cm}\n"
            bloco_questoes += f"\\noindent\\includegraphics[width=0.5cm]{{icone_equacao.jpg}} \\textit{{Resolução matemática:}}\n\n"
            bloco_questoes += "\\vspace{5cm}\n\n" # Espaço vazio para o aluno escrever
            bloco_questoes += f"\\noindent\\hfill \\includegraphics[width=0.5cm]{{icone_equacao.jpg}}\n\n"
            
        # BLOCO DE TEXTO (Abertura no topo esquerdo, fechamento no rodapé direito)
        if questao['tipo'] == 'texto':
            bloco_questoes += "\\vspace{0.2cm}\n"
            bloco_questoes += f"\\noindent\\includegraphics[width=0.5cm]{{icone_texto.jpg}} \\textit{{Justificativa teórica:}}\n\n"
            bloco_questoes += "\\vspace{3cm}\n\n" # Espaço vazio para o aluno escrever
            bloco_questoes += f"\\noindent\\hfill \\includegraphics[width=0.5cm]{{icone_texto.jpg}}\n\n"

    template = template.replace('<<BLOCO_QUESTOES>>', bloco_questoes)

    nome_arquivo_tex = f"{caminho_saida}.tex"
    with open(nome_arquivo_tex, 'w', encoding='utf-8') as file:
        file.write(template)

    print("Compilando o PDF via pdflatex...")
    try:
        subprocess.run(["pdflatex", "-interaction=nonstopmode", nome_arquivo_tex], check=True, stdout=subprocess.DEVNULL)
        print(f"Sucesso! Arquivo gerado: {caminho_saida}.pdf")
    except subprocess.CalledProcessError:
        print("Erro na compilação do LaTeX.")

dados_teste = {
    "escola": "Instituto de Educação de Dourados",
    "turma": "3º Ano A",
    "questoes": [
        {"texto": "Determine a força resultante sobre o condutor elétrico.", "tipo": "calculo"},
        {"texto": "Discorra sobre o efeito Joule observado no circuito.", "tipo": "texto"}
    ]
}

if __name__ == "__main__":
    fabricar_prova(dados_teste, "modelo_av.tex", "prova_teste")