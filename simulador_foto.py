import fitz  # Importa a biblioteca PyMuPDF

def simular_foto_celular(caminho_pdf, nome_saida="teste_captura.png"):
    try:
        # Abre o PDF
        doc = fitz.open(caminho_pdf)
        
        # Carrega a primeira página (índice 0)
        pagina = doc.load_page(0)
        
        # Converte para imagem forçando a resolução de 254 DPI que o OpenCV precisa
        imagem = pagina.get_pixmap(dpi=254)
        
        # Salva o arquivo em alta resolução
        imagem.save(nome_saida)
        print(f"Sucesso! A imagem '{nome_saida}' foi gerada e está pronta para o teste.")
    except Exception as e:
        print(f"Erro ao converter: O arquivo '{caminho_pdf}' não foi encontrado na pasta.")

if __name__ == "__main__":
    simular_foto_celular("prova_gerada_app.pdf")