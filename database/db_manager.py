import streamlit as st
import hashlib
import pandas as pd
from sqlalchemy import create_engine, text

# ---------------------------------------------------------
# CONEXÃO COM O BANCO DE DADOS EM NUVEM (SUPABASE / POSTGRESQL)
# ---------------------------------------------------------
@st.cache_resource
def iniciar_conexao():
    """
    Cria e mantém a ligação ao Supabase de forma segura e eficiente,
    evitando que o Streamlit abra milhares de conexões a cada clique.
    """
    # A URL está protegida no ficheiro .streamlit/secrets.toml
    db_url = st.secrets["DATABASE_URL"]
    
    # O pool_pre_ping verifica se a ligação ainda está ativa antes de cada comando
    engine = create_engine(db_url, pool_pre_ping=True)
    return engine

engine = iniciar_conexao()

# ---------------------------------------------------------
# INICIALIZAÇÃO DA ESTRUTURA (TABELAS)
# ---------------------------------------------------------
def iniciar_banco():
    """
    Verifica se as tabelas existem no Supabase. Se não existirem (primeira execução),
    ele cria todas automaticamente. Isso elimina a necessidade de configurações manuais.
    """
    try:
        with engine.begin() as conn:
            # Tabela de Usuários (Professores)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    telefone VARCHAR(50),
                    senha VARCHAR(255) NOT NULL,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
        
        # Tabela de Escolas vinculadas ao Usuário
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS escolas (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
                nome VARCHAR(255) NOT NULL,
                UNIQUE(usuario_id, nome)
            );
        """))
        
        # Tabela das Provas criadas pela IA (Aba 1) - Armazena o PDF em formato Binário (BYTEA)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS provas_fabricadas (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
                escola VARCHAR(255) NOT NULL,
                disciplina VARCHAR(100),
                serie VARCHAR(50),
                turma VARCHAR(50),
                etapa VARCHAR(50),
                pdf_arquivo BYTEA,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Tabela do Diário de Classe Digital (Aba 2 e 3)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS historico_correcoes (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
                escola VARCHAR(255),
                turma VARCHAR(50),
                prova VARCHAR(255),
                aluno VARCHAR(255),
                numero INTEGER,
                nota NUMERIC(5,2),
                parecer TEXT,
                homologado BOOLEAN DEFAULT FALSE,
                data_correcao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
    except Exception as e:
        # Silencia silenciosamente os erros de concorrência (race conditions) 
        # que ocorrem quando múltiplos processos tentam verificar as tabelas ao mesmo tempo.
        pass

# ---------------------------------------------------------
# AUTENTICAÇÃO E SEGURANÇA
# ---------------------------------------------------------
def hash_senha(senha):
    """Criptografa a senha para não a salvar em texto puro no banco de dados"""
    return hashlib.sha256(senha.encode()).hexdigest()

def registar_usuario(nome, email, tel, senha):
    try:
        with engine.begin() as conn:
            # Verifica se o e-mail já existe
            result = conn.execute(text("SELECT id FROM usuarios WHERE email = :email"), {"email": email}).fetchone()
            if result:
                return False, "Este e-mail profissional já está cadastrado."
            
            # Insere o novo professor
            conn.execute(text("""
                INSERT INTO usuarios (nome, email, telefone, senha)
                VALUES (:nome, :email, :tel, :senha)
            """), {"nome": nome, "email": email, "tel": tel, "senha": hash_senha(senha)})
        return True, "Conta criada com sucesso! Faça login para começar."
    except Exception as e:
        return False, f"Erro crítico ao criar conta: {e}"

def validar_login(email, senha):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, nome, email FROM usuarios 
            WHERE email = :email AND senha = :senha
        """), {"email": email, "senha": hash_senha(senha)}).mappings().fetchone()
        
        if result:
            return dict(result) # Retorna um dicionário com os dados da sessão
        return None

# ---------------------------------------------------------
# GESTÃO DE CONTEXTO (ESCOLAS)
# ---------------------------------------------------------
def adicionar_escola(usuario_id, nome_escola):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO escolas (usuario_id, nome) 
                VALUES (:u_id, :nome) 
                ON CONFLICT DO NOTHING
            """), {"u_id": usuario_id, "nome": nome_escola})
        return True
    except:
        return False

def buscar_escolas_por_usuario(usuario_id):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT nome FROM escolas WHERE usuario_id = :u_id ORDER BY nome
        """), {"u_id": usuario_id}).fetchall()
        return [row[0] for row in result]

# ---------------------------------------------------------
# ARQUIVO DE AVALIAÇÕES (ABA 1)
# ---------------------------------------------------------
def salvar_prova_fabricada(usuario_id, escola, disciplina, serie, turma, etapa, pdf_bytes):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO provas_fabricadas (usuario_id, escola, disciplina, serie, turma, etapa, pdf_arquivo)
            VALUES (:u_id, :escola, :disciplina, :serie, :turma, :etapa, :pdf)
        """), {
            "u_id": usuario_id, "escola": escola, "disciplina": disciplina, 
            "serie": serie, "turma": turma, "etapa": etapa, "pdf": pdf_bytes
        })

def buscar_provas_por_usuario_e_escola(usuario_id, escola):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, disciplina, serie, turma, etapa, data_criacao 
            FROM provas_fabricadas 
            WHERE usuario_id = :u_id AND escola = :escola
            ORDER BY data_criacao DESC
        """), {"u_id": usuario_id, "escola": escola}).mappings().fetchall()
        return [dict(r) for r in result]

def buscar_pdf_prova(prova_id):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT pdf_arquivo FROM provas_fabricadas WHERE id = :id
        """), {"id": prova_id}).fetchone()
        return result[0] if result else None

# ---------------------------------------------------------
# DIÁRIO DE CLASSE E HISTÓRICO (ABA 2, 3 e 4)
# ---------------------------------------------------------
def salvar_correcao(usuario_id, escola, turma, prova, aluno, numero, nota, parecer):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO historico_correcoes (usuario_id, escola, turma, prova, aluno, numero, nota, parecer)
            VALUES (:u_id, :escola, :turma, :prova, :aluno, :num, :nota, :parecer)
        """), {
            "u_id": usuario_id, "escola": escola, "turma": turma, 
            "prova": prova, "aluno": aluno, "num": numero, 
            "nota": nota, "parecer": parecer
        })

def buscar_historico_por_usuario_e_escola(usuario_id, escola):
    """
    Retorna todo o histórico de um professor numa determinada escola.
    Entrega os dados nativamente em DataFrame do Pandas, perfeito para os Gráficos do Dashboard.
    """
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT turma, prova, aluno, numero, nota, parecer, homologado, data_correcao 
            FROM historico_correcoes 
            WHERE usuario_id = :u_id AND escola = :escola
            ORDER BY data_correcao DESC
        """), {"u_id": usuario_id, "escola": escola})
        
        # Converte diretamente para Pandas
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        return df