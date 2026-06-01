# gerar_icones.py
import cv2
import numpy as np

# Cria imagens base quadradas de 50x50 pixels
def criar_marcador(nome, tipo_forma):
    img = np.ones((50, 50, 3), dtype=np.uint8) * 255
    # Desenha uma borda preta espessa
    cv2.rectangle(img, (0, 0), (49, 49), (0, 0, 0), 5)
    
    if tipo_forma == "circulo":
        cv2.circle(img, (25, 25), 10, (0, 0, 0), -1)
    elif tipo_forma == "retangulo":
        cv2.rectangle(img, (15, 15), (35, 35), (0, 0, 0), -1)
    elif tipo_forma == "triangulo":
        pts = np.array([[25, 10], [10, 38], [40, 38]], np.int32)
        cv2.fillPoly(img, [pts], (0, 0, 0))
        
    cv2.imwrite(nome, img)

criar_marcador("icone_questao.jpg", "circulo")
criar_marcador("icone_equacao.jpg", "retangulo")
criar_marcador("icone_texto.jpg", "triangulo")
print("Ícones de teste gerados com sucesso!")