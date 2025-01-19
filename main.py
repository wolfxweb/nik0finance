from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Verifica se o banco de dados existe, se não, cria
db_path = 'nik0finance.db'
if not os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Crie a tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            senha TEXT NOT NULL
        )
    ''')

    # Crie a tabela de transações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origem TEXT,
            descricao TEXT,
            tipo TEXT CHECK (tipo IN ('Fixo', 'Variável')),
            valor REAL,
            modelo TEXT CHECK (modelo IN ('Renda', 'Custo')),
            data DATE NOT NULL
        )
    ''')

@app.route('/')

#página principal
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    # Conecta ao banco gde dados SQLite
    conn = sqlite3.connect('nik0finance.db')
    cursor = conn.cursor()

    # Obtém o hash da senha do banco de dados
    cursor.execute('SELECT * FROM usuarios WHERE username=?', (username,))
    user = cursor.fetchone()

    # Fecha a conexão
    conn.close()

    if user and check_password_hash(user[2], password):
        # Lógica de autenticação bem-sucedida, pode ser expandida conforme necessário
        session['user_id'] = user[0]
        return redirect(url_for('dashboard'))
    else:
        # Lógica de autenticação falhou, redireciona de volta para a página de login
        flash('error', 'Usuário ou Senha Inválidos')
        return redirect(url_for('index'))

@app.route('/cadastro', methods=['GET','POST'])
def cadastro():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirmPassword']

        # Verifica se as senhas coincidem
        if password != confirm_password:
            flash('error', 'As senhas não coincidem. Por favor, insira senhas iguais.')
            return redirect(url_for('cadastro'))

        # Hash da senha antes de armazenar no banco de dados
        hashed_password = generate_password_hash(password)

        try:
            # Conectar ao banco de dados SQLite
            conn = sqlite3.connect('nik0finance.db')
            cursor = conn.cursor()

            # Verifica se o usuário já existe
            cursor.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
            existing_user = cursor.fetchone()

            if existing_user:
                flash('error', 'Este usuário já existe. Por favor, escolha um nome de usuário diferente.')
                return redirect(url_for('cadastro'))

            # Insere o novo usuário no banco de dados
            cursor.execute("INSERT INTO usuarios (username, senha) VALUES (?, ?)", (username, hashed_password))
            conn.commit()

            flash('success', 'Cadastro realizado com sucesso! Faça o login para acessar sua conta.')
            return redirect(url_for('index'))

        except Exception as e:
            flash('error', f"Erro ao cadastrar usuário: {str(e)}")
            return redirect(url_for('cadastro'))

        finally:
            # Fechar a conexão com o banco de dados
            conn.close()

    return render_template('cadastro.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('error', 'Você não está autenticado.' )
        return redirect(url_for('index'))
    try:
        # Conectar ao banco de dados SQLite
        conn = sqlite3.connect('nik0finance.db')
        cursor = conn.cursor()

        # Obtenha os parâmetros de filtro da solicitação
        filtro_ano = request.args.get('filtro_ano')
        filtro_mes = request.args.get('filtro_mes')

        # Construa a consulta SQL com base nos filtros
        sql_renda = "SELECT id, origem, descricao, tipo, valor, strftime('%d/%m/%Y', data),modelo FROM transacoes WHERE 1=1"
        sql_custo = "SELECT id, origem, descricao, tipo, valor, strftime('%d/%m/%Y', data),modelo FROM transacoes WHERE modelo='Custo'"

        if filtro_ano and filtro_mes:
            sql_renda += f" AND strftime('%Y-%m', data) = '{filtro_ano}-{filtro_mes}'"
            sql_custo += f" AND strftime('%Y-%m', data) = '{filtro_ano}-{filtro_mes}'"

        # Execute as consultas SQL
        cursor.execute(sql_renda)
        transacoes_renda = cursor.fetchall()

        cursor.execute(sql_custo)
        transacoes_custo = cursor.fetchall()

         # Calcular totais de Renda
        renda_fixa_total = sum(transacao[4] for transacao in transacoes_renda if transacao[3] == 'Fixo')
        renda_variavel_total = sum(transacao[4] for transacao in transacoes_renda if transacao[3] == 'Variável')
        renda_total = sum(transacao[4] for transacao in transacoes_renda)

        # Calcular totais de custos
        custo_fixo_total = sum(transacao[4] for transacao in transacoes_custo if transacao[3] == 'Fixo')
        custo_variavel_total = sum(transacao[4] for transacao in transacoes_custo if transacao[3] == 'Variável')
        custo_total = sum(transacao[4] for transacao in transacoes_custo)

        # Calcular o valor Renda - Custos diretamente
        renda_minus_custos = renda_total - custo_total

        # Formatando os totais de Renda
        renda_fixa_total = 'R${:,.2f}'.format(renda_fixa_total).replace(',', '@').replace('.', ',').replace('@', '.')
        renda_variavel_total = 'R${:,.2f}'.format(renda_variavel_total).replace(',', '@').replace('.', ',').replace('@', '.')
        renda_total = 'R${:,.2f}'.format(renda_total).replace(',', '@').replace('.', ',').replace('@', '.')

        # Formatando os totais de custos
        custo_fixo_total = 'R${:,.2f}'.format(custo_fixo_total).replace(',', '@').replace('.', ',').replace('@', '.')
        custo_variavel_total = 'R${:,.2f}'.format(custo_variavel_total).replace(',', '@').replace('.', ',').replace('@', '.')
        custo_total = 'R${:,.2f}'.format(custo_total).replace(',', '@').replace('.', ',').replace('@', '.')

        # Formatando o resultado
        renda_minus_custos = 'R${:,.2f}'.format(renda_minus_custos).replace(',', '@').replace('.', ',').replace('@', '.')

        # Fechar a conexão com o banco de dados
        conn.close()
        print(transacoes_renda)
        return render_template('dashboard.html', 
        transacoes_renda=transacoes_renda, 
        renda_fixa_total=renda_fixa_total, 
        renda_variavel_total=renda_variavel_total, 
        renda_total=renda_total, 
        transacoes_custo=transacoes_custo, 
        custo_fixo_total=custo_fixo_total,
        custo_variavel_total=custo_variavel_total,
        custo_total=custo_total, 
        renda_minus_custos=renda_minus_custos)

    except Exception as e:
        # Adicione algum código aqui para lidar com a exceção
        flash('error', f"Erro ao carregar transações: {str(e)}")
        return redirect(url_for('index'))

@app.route('/gestao_usuarios')
def gestao_usuarios():
    try:
        # Conectar ao banco de dados SQLite
        conn = sqlite3.connect('nik0finance.db')
        cursor = conn.cursor()

        # Consulta para obter todos os usuários
        cursor.execute('SELECT * FROM usuarios')
        users = cursor.fetchall()

        # Fechar a conexão com o banco de dados
        conn.close()

        return render_template('gestao_usuarios.html', users=users)

    except Exception as e:
        # Trate a exceção conforme necessário
        return f"Erro ao carregar usuários: {str(e)}"

@app.route('/excluir_usuario/<int:user_id>', methods=['POST'])
def excluir_usuario(user_id):
    try:
        # Conectar ao banco de dados SQLite
        conn = sqlite3.connect('nik0finance.db')
        cursor = conn.cursor()

        # Verificar se o usuário está excluindo a própria conta
        if 'user_id' in session and session['user_id'] == user_id:
            # Limpar a sessão (logout) se o usuário estiver excluindo sua própria conta
            session.clear()

        # Excluir o usuário com base no ID
        cursor.execute('DELETE FROM usuarios WHERE id=?', (user_id,))

        # Commit e fechar a conexão
        conn.commit()
        conn.close()

        flash('success', 'Usuário excluído com sucesso!')

        # Redirecionar para a página de login se o usuário excluiu sua própria conta
        if 'user_id' not in session:
            return redirect(url_for('index'))
        else:
            return redirect(url_for('gestao_usuarios'))

    except Exception as e:
        flash('error', f"Erro ao excluir usuário: {str(e)}")
        return redirect(url_for('gestao_usuarios'))

@app.route('/obter_dados_transacao/<int:transacao_id>', methods=['GET'])
def obter_dados_transacao(transacao_id):
    # Lógica para obter os dados da transação com base no ID
    conn = sqlite3.connect('nik0finance.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM transacoes WHERE id = ?', (transacao_id,))
    transacao = cursor.fetchone()

    conn.close()

    if transacao:
        # Retorne um JSON com nomes de campo
        return jsonify({
            'origem': transacao[1],
            'descricao': transacao[2],
            'tipo': transacao[3],
            'valor': transacao[4],
            'modelo': transacao[5],
            'data': transacao[6]
        })
    else:
        return jsonify({'error': 'Transação não encontrada'}), 404

@app.route('/adicionar_transacao', methods=['POST'])
def adicionar_transacao():
    transacao_id = request.form.get('transacao_id')

    origem = request.form['origem']
    descricao = request.form['descricao']
    tipo = request.form['tipo']
    valor = request.form['valor']
    modelo = request.form['modelo']
    data = request.form['data']

    try:
        conn = sqlite3.connect('nik0finance.db')
        cursor = conn.cursor()

        if transacao_id:
            # Atualiza a transação existente no banco de dados
            cursor.execute('''
                UPDATE transacoes
                SET origem=?, descricao=?, tipo=?, valor=?, modelo=?, data=?
                WHERE id=?
            ''', (origem, descricao, tipo, valor, modelo, data, transacao_id))
        else:
            # Insere uma nova transação no banco de dados
            cursor.execute('INSERT INTO transacoes (origem, descricao, tipo, valor, modelo, data) VALUES (?, ?, ?, ?, ?, ?)',
                        (origem, descricao, tipo, valor, modelo, data))

        # Commit e fecha a conexão
        conn.commit()
        conn.close()

        # Redireciona de volta para o dashboard
        return redirect(url_for('dashboard'))

    except Exception as e:
        flash('error', f"Erro ao adicionar/editar transação: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route('/excluir_transacao/<int:transacao_id>', methods=['POST'])
def excluir_transacao(transacao_id):
    if 'user_id' not in session:
        flash('error', 'Você não está autenticado.')
        return redirect(url_for('index'))

    try:
        # Conectar ao banco de dados SQLite
        conn = sqlite3.connect('nik0finance.db')
        cursor = conn.cursor()

        # Exclui a transação com base no ID
        cursor.execute('DELETE FROM transacoes WHERE id=?', (transacao_id,))

        # Commit e fecha a conexão
        conn.commit()
        conn.close()

        # Retorna uma resposta JSON, você pode personalizar conforme necessário
        return redirect(url_for('dashboard'))

    except Exception as e:
        flash('error', f"Erro ao excluir transação: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route('/logout', methods=['POST'])
def logout():
    # Limpa a sessão e redireciona para a página de login
    session.clear()
    return redirect(url_for('index'))


@app.route('/dashboardcopy')
def dashboardcopy():
    if 'user_id' not in session:
        flash('error', 'Você não está autenticado.' )
        return redirect(url_for('index'))
    try:
        # Conectar ao banco de dados SQLite
        conn = sqlite3.connect('nik0finance.db')
        cursor = conn.cursor()

        # Obtenha os parâmetros de filtro da solicitação
        filtro_ano = request.args.get('filtro_ano')
        filtro_mes = request.args.get('filtro_mes')

        # Construa a consulta SQL com base nos filtros
        sql_renda = "SELECT id, origem, descricao, tipo, valor, strftime('%d/%m/%Y', data),modelo FROM transacoes WHERE 1=1'"
        sql_custo = "SELECT id, origem, descricao, tipo, valor, strftime('%d/%m/%Y', data),modelo FROM transacoes WHERE 1=1"

        if filtro_ano and filtro_mes:
            sql_renda += f" AND strftime('%Y-%m', data) = '{filtro_ano}-{filtro_mes}'"
            sql_custo += f" AND strftime('%Y-%m', data) = '{filtro_ano}-{filtro_mes}'"

        # Execute as consultas SQL
        cursor.execute(sql_renda)
        transacoes_renda = cursor.fetchall()

        cursor.execute(sql_custo)
        transacoes_custo = cursor.fetchall()

         # Calcular totais de Renda
        renda_fixa_total = sum(transacao[4] for transacao in transacoes_renda if transacao[3] == 'Fixo')
        renda_variavel_total = sum(transacao[4] for transacao in transacoes_renda if transacao[3] == 'Variável')
        renda_total = sum(transacao[4] for transacao in transacoes_renda)

        # Calcular totais de custos
        custo_fixo_total = sum(transacao[4] for transacao in transacoes_custo if transacao[3] == 'Fixo')
        custo_variavel_total = sum(transacao[4] for transacao in transacoes_custo if transacao[3] == 'Variável')
        custo_total = sum(transacao[4] for transacao in transacoes_custo)

        # Calcular o valor Renda - Custos diretamente
        renda_minus_custos = renda_total - custo_total

        # Formatando os totais de Renda
        renda_fixa_total = 'R${:,.2f}'.format(renda_fixa_total).replace(',', '@').replace('.', ',').replace('@', '.')
        renda_variavel_total = 'R${:,.2f}'.format(renda_variavel_total).replace(',', '@').replace('.', ',').replace('@', '.')
        renda_total = 'R${:,.2f}'.format(renda_total).replace(',', '@').replace('.', ',').replace('@', '.')

        # Formatando os totais de custos
        custo_fixo_total = 'R${:,.2f}'.format(custo_fixo_total).replace(',', '@').replace('.', ',').replace('@', '.')
        custo_variavel_total = 'R${:,.2f}'.format(custo_variavel_total).replace(',', '@').replace('.', ',').replace('@', '.')
        custo_total = 'R${:,.2f}'.format(custo_total).replace(',', '@').replace('.', ',').replace('@', '.')

        # Formatando o resultado
        renda_minus_custos = 'R${:,.2f}'.format(renda_minus_custos).replace(',', '@').replace('.', ',').replace('@', '.')

        # Fechar a conexão com o banco de dados
        conn.close()
   
        return render_template('dashboardcopy.html', 
        transacoes_renda=transacoes_renda, 
        renda_fixa_total=renda_fixa_total, 
        renda_variavel_total=renda_variavel_total, 
        renda_total=renda_total, 
        transacoes_custo=transacoes_custo, 
        custo_fixo_total=custo_fixo_total,
        custo_variavel_total=custo_variavel_total,
        custo_total=custo_total, 
        renda_minus_custos=renda_minus_custos)

    except Exception as e:
        # Adicione algum código aqui para lidar com a exceção
        flash('error', f"Erro ao carregar transações: {str(e)}")
        return redirect(url_for('index'))
    
if __name__ == '__main__':
    app.run(debug=True)
