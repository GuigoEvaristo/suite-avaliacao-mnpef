# corretor.py
import cv2
import numpy as np

def testar_recorte_contexto(caminho_prova, caminho_simbolo):
    imagem_prova = cv2.imread(caminho_prova, cv2.IMREAD_GRAYSCALE)
    imagem_colorida = cv2.imread(caminho_prova)
    template = cv2.imread(caminho_simbolo, cv2.IMREAD_GRAYSCALE)
    w, h = template.shape[::-1]

    resultado = cv2.matchTemplate(imagem_prova, template, cv2.TM_CCOEFF_NORMED)
    
    # Filtro de confiança seguro baseado no seu diagnóstico bem-sucedido
    threshold = 0.9
    loc = np.where(resultado >= threshold)
    pontos_encontrados = list(zip(*loc[::-1]))
    pontos_unicos = []

    # NOVA FILTRAGEM 2D: Só descarta se o ponto sobrepuser o outro em X E Y ao mesmo tempo
    for pt in pontos_encontrados:
        duplicado = False
        for p_salvo in pontos_unicos:
            if abs(pt[0] - p_salvo[0]) < w and abs(pt[1] - p_salvo[1]) < h:
                duplicado = True
                break
        if not duplicado:
            pontos_unicos.append(pt)

    # Ordena os símbolos de cima para baixo na página
    pontos_unicos = sorted(pontos_unicos, key=lambda p: p[1])
    print(f"Símbolos detectados com a nova limpeza: {len(pontos_unicos)}")

    if len(pontos_unicos) >= 2:
        # O primeiro símbolo encontrado (Índice 0) é o de Abertura (topo do espaço)
        # O segundo símbolo encontrado (Índice 1) é o de Fechamento (fim do espaço)
        simbolo_inicio = pontos_unicos[0]
        simbolo_fim = pontos_unicos[1]

        y_inicio = simbolo_inicio[1] + h
        y_fim = simbolo_fim[1]
        largura_pagina = imagem_prova.shape[1]
        
        # Realiza o recorte exato do espaço em branco
        recorte = imagem_colorida[y_inicio:y_fim, 0:largura_pagina]
        
        cv2.imwrite("resultado_recorte_calculo.jpg", recorte)
        print("Sucesso absoluto! O bloco de cálculo foi isolado em 'resultado_recorte_calculo.jpg'")
        
        cv2.imshow("Espaço de Cálculo Isolado", recorte)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("Erro: Não foi possível encontrar o par de abertura e fechamento.")

if __name__ == "__main__":
    testar_recorte_contexto("pagina_prova-1.png", "icone_equacao.jpg")