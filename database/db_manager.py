# database/db_manager.py
import sqlite3
import datetime
import hashlib
import os

DB_PATH = 'avaliacoes_mnpef.db'

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def iniciar_banco():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Utilizadores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            telefone TEXT,
            senha_hash TEXT NOT NULL,
            data_cadastro TEXT
        )
    ''')
    
    # 2. Escolas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS escolas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nome TEXT NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')
    
    # 3. Histórico de Correções
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_correcoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            escola_nome TEXT,
            data_hora TEXT,
            parecer_ia TEXT,
            coordenadas TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')

    # 4. NOVA: Histórico de Provas Fabricadas (Com armazenamento do PDF em BLOB)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS provas_fabricadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            escola_nome TEXT,
            disciplina TEXT,
            serie TEXT,
            turma TEXT,
            etapa TEXT,
            data_criacao TEXT,
            pdf_arquivo BLOB,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# --- GESTÃO DE UTILIZADORES E ESCOLAS ---

def registar_usuario(nome, email, telefone, senha):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        data_cadastro = datetime.datetime.now().strftime("%d/%m/%Y")
        senha_criptografada = hash_senha(senha)
        
        cursor.execute('''
            INSERT INTO usuarios (nome, email, telefone, senha_hash, data_cadastro)
            VALUES (?, ?, ?, ?, ?)
        ''', (nome, email, telefone, senha_criptografada, data_cadastro))
        
        conn.commit()
        conn.close()
        return True, "Utilizador registado com sucesso!"
    except sqlite3.IntegrityError:
        return False, "Este e-mail já está registado no sistema."
    except Exception as e:
        return False, f"Erro ao registar: {e}"

def validar_login(email, senha):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    senha_criptografada = hash_senha(senha)
    cursor.execute('SELECT id, nome, email FROM usuarios WHERE email = ? AND senha_hash = ?', (email, senha_criptografada))
    usuario = cursor.fetchone()
    conn.close()
    if usuario:
        return {"id": usuario[0], "nome": usuario[1], "email": usuario[2]}
    return None

def adicionar_escola(usuario_id, nome_escola):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO escolas (usuario_id, nome) VALUES (?, ?)', (usuario_id, nome_escola))
    conn.commit()
    conn.close()

def buscar_escolas_por_usuario(usuario_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT nome FROM escolas WHERE usuario_id = ? ORDER BY nome', (usuario_id,))
    escolas = [row[0] for row in cursor.fetchall()]
    conn.close()
    return escolas

# --- GESTÃO DE CORREÇÕES (Aba 2) ---

def salvar_correcao(usuario_id, escola_nome, parecer, coordenadas):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    data_hora = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    coords_str = str(coordenadas) if coordenadas else "Não delimitado"
    cursor.execute('''
        INSERT INTO historico_correcoes (usuario_id, escola_nome, data_hora, parecer_ia, coordenadas)
        VALUES (?, ?, ?, ?, ?)
    ''', (usuario_id, escola_nome, data_hora, parecer, coords_str))
    conn.commit()
    conn.close()

def buscar_historico_por_usuario_e_escola(usuario_id, escola_nome):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT data_hora, parecer_ia FROM historico_correcoes 
        WHERE usuario_id = ? AND escola_nome = ?
        ORDER BY id DESC
    ''', (usuario_id, escola_nome))
    registos = cursor.fetchall()
    conn.close()
    return registos

# --- NOVA: GESTÃO DE PROVAS FABRICADAS (Aba 1) ---

def salvar_prova_fabricada(usuario_id, escola_nome, disciplina, serie, turma, etapa, pdf_bytes):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    data_criacao = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    cursor.execute('''
        INSERT INTO provas_fabricadas 
        (usuario_id, escola_nome, disciplina, serie, turma, etapa, data_criacao, pdf_arquivo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (usuario_id, escola_nome, disciplina, serie, turma, etapa, data_criacao, pdf_bytes))
    
    conn.commit()
    conn.close()

def buscar_provas_por_usuario_e_escola(usuario_id, escola_nome):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Trazemos os metadados da prova para listar no histórico, e o ID para download
    cursor.execute('''
        SELECT id, disciplina, serie, turma, etapa, data_criacao 
        FROM provas_fabricadas 
        WHERE usuario_id = ? AND escola_nome = ?
        ORDER BY id DESC
    ''', (usuario_id, escola_nome))
    provas = cursor.fetchall()
    conn.close()
    return provas

def buscar_pdf_prova(prova_id):
    """Busca o ficheiro binário do PDF guardado para realizar o download posterior"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT pdf_arquivo, disciplina, turma, etapa FROM provas_fabricadas WHERE id = ?', (prova_id,))
    resultado = cursor.fetchone()
    conn.close()
    return resultado