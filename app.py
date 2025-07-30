# app.py

import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

# --- Configuração do App ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua-chave-secreta-muito-segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Configuração da pasta de uploads ---
# Define o caminho para a pasta 'uploads' dentro da pasta 'instance'
UPLOAD_FOLDER = os.path.join(app.instance_path, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Garante que a pasta 'uploads' exista
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# --- Modelos do Banco de Dados ---
class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    descricao = db.Column(db.String(250), nullable=True)
    imagem_url = db.Column(db.String(250), nullable=True)
    produtos = db.relationship('Produto', backref='categoria', lazy=True)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(500), nullable=True)
    imagem_url = db.Column(db.String(250), nullable=True) # Agora armazena o nome do arquivo
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)

# --- Rotas da Aplicação ---

# Página principal (pública) que mostra o cardápio
@app.route('/')
def cliente_cardapio():
    categorias = Categoria.query.all()
    whatsapp_number = "5519986088874"
    return render_template('cliente_cardapio.html', categorias=categorias, whatsapp_number=whatsapp_number)

# Rota para servir as imagens que foram salvas via upload
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Rotas do Painel Administrativo ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'dogao123':
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin/cardapio', methods=['GET', 'POST'])
def admin_cardapio():
    if request.method == 'POST':
        imagem_salva = None
        # Verifica se um arquivo foi enviado no formulário
        if 'productImage' in request.files:
            file = request.files['productImage']
            # Se o arquivo tiver um nome (ou seja, não está vazio)
            if file.filename != '':
                # Garante que o nome do arquivo é seguro
                imagem_salva = secure_filename(file.filename)
                # Salva o arquivo na nossa pasta de uploads
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], imagem_salva))

        novo_produto = Produto(
            nome=request.form['productName'],
            preco=float(request.form['productPrice']),
            descricao=request.form['productDescription'],
            categoria_id=request.form['productCategory'],
            imagem_url=imagem_salva  # Salva o nome do arquivo no banco
        )
        db.session.add(novo_produto)
        db.session.commit()
        flash('Produto adicionado com sucesso!', 'success')
        return redirect(url_for('admin_cardapio'))

    categorias = Categoria.query.all()
    return render_template('admin_cardapio.html', categorias=categorias)

@app.route('/admin/produto/toggle/<int:produto_id>', methods=['POST'])
def toggle_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    produto.ativo = not produto.ativo
    db.session.commit()
    status = "ativado" if produto.ativo else "desativado"
    flash(f'Produto {produto.nome} foi {status}.', 'info')
    return redirect(url_for('admin_cardapio'))

# --- Comando para inicializar o banco de dados ---
@app.cli.command("init-db")
def init_db_command():
    """Cria as tabelas do banco de dados e as categorias iniciais."""
    db.create_all()
    print("Banco de dados inicializado.")

    if Categoria.query.count() == 0:
        categorias_iniciais = [
            {'id': 1, 'nome': 'Lanches', 'descricao': 'Hambúrgueres artesanais e sanduíches especiais', 'imagem_url': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=500&h=300&fit=crop'},
            {'id': 2, 'nome': 'Hot Dog', 'descricao': 'Hot dogs gourmet com ingredientes selecionados', 'imagem_url': 'https://images.unsplash.com/photo-1612392061787-2d078b3f4edb?w=500&h=300&fit=crop'},
            {'id': 3, 'nome': 'Sobremesas', 'descricao': 'Doces e sobremesas para adoçar seu dia', 'imagem_url': 'https://images.unsplash.com/photo-1551024601-bec78aea704b?w=500&h=300&fit=crop'},
            {'id': 4, 'nome': 'Bebidas', 'descricao': 'Refrigerantes, sucos e bebidas geladas', 'imagem_url': 'https://images.unsplash.com/photo-1437418747212-8d9709afab22?w=500&h=300&fit=crop'}
        ]
        for cat_data in categorias_iniciais:
            nova_cat = Categoria(**cat_data)
            db.session.add(nova_cat)
        db.session.commit()
        print("Categorias iniciais criadas.")

if __name__ == '__main__':
    app.run(debug=True)