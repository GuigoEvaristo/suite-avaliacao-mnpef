import cv2
import numpy as np
import os

def realizar_recorte_via_coordenadas_ia(caminho_prova, coordinates_normalized):
    """
    Utility para realizar o recorte matemático baseado nas coordenadas
    fornecidas pela Inteligência Artificial.
    Input coords: [ymin, xmin, ymax, xmax] na escala de 0 a 1000.
    """
    try:
        if not os.path.exists(caminho_prova):
            return None

        img = cv2.imread(caminho_prova)
        height, width = img.shape[:2]

        # Extrai as coordenadas normalizadas
        # COORDINATES=[ymin, xmin, ymax, xmax]
        ymin_n, xmin_n, ymax_n, xmax_n = coordinates_normalized

        # Converte de escala normalizada (0-1000) para pixels reais
        y_start = int((ymin_n / 1000) * height)
        x_start = int((xmin_n / 1000) * width)
        y_end = int((ymax_n / 1000) * height)
        x_end = int((xmax_n / 1000) * width)

        # Garante integridade matemática (evita recortes invertidos ou fora da imagem)
        y_start = max(0, y_start)
        x_start = max(0, x_start)
        y_end = min(height, y_end)
        x_end = min(width, x_end)

        if y_end > y_start and x_end > x_start:
            # Realiza o recorte matricial
            recorte = img[y_start:y_end, x_start:x_end]
            caminho_saida = "resultado_recorte_ia.jpg"
            cv2.imwrite(caminho_saida, recorte)
            return caminho_saida
        else:
            print("Erro: Coordenadas de recorte inválidas geradas pela IA.")
            return None

    except Exception as e:
        print(f"Erro no processamento do recorte matemático: {e}")
        return None