# database/db_manager.py
import sqlite3
import datetime
import os

DB_PATH = 'avaliacoes_mnpef.db'

def iniciar_banco():
    """
    Cria o ficheiro do banco de dados e a tabela de histórico, caso não existam.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_correcoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT,
            parecer_ia TEXT,
            coordenadas TEXT
        )
    ''')
    conn.commit()
    conn.close()

def salvar_correcao(parecer, coordenadas):
    """
    Regista uma nova correção na base de dados.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Captura o momento exato da correção
    data_hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Converte a lista de coordenadas para string para ser guardada no SQLite
    coords_str = str(coordenadas) if coordenadas else "Não delimitado"
    
    cursor.execute('''
        INSERT INTO historico_correcoes (data_hora, parecer_ia, coordenadas)
        VALUES (?, ?, ?)
    ''', (data_hora, parecer, coords_str))
    
    conn.commit()
    conn.close()

def buscar_historico():
    """
    Recupera todas as correções guardadas, da mais recente para a mais antiga.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT data_hora, parecer_ia FROM historico_correcoes ORDER BY id DESC')
    registos = cursor.fetchall()
    conn.close()
    return registos
