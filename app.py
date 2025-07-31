# app.py

import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime

# --- Configuração do App ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-forte-e-dificil-de-adivinhar'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Configuração da pasta de uploads ---
UPLOAD_FOLDER = os.path.join(app.instance_path, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
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
    imagem_url = db.Column(db.String(250), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)

# === NOVOS MODELOS PARA HISTÓRICO DE PEDIDOS ===
class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    tipo_entrega = db.Column(db.String(100), nullable=False)
    taxa_entrega = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False)
    itens = db.relationship('ItemPedido', backref='pedido', lazy='joined', cascade="all, delete-orphan")

class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    nome_produto = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)

# === FIM DOS NOVOS MODELOS ===


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Por favor, faça o login para acessar esta página.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_categorias_ordenadas():
    ordem_desejada = ["Hot Dog", "Lanches", "Bebidas", "Sobremesas"]
    todas_categorias = Categoria.query.all()
    categorias_dict = {cat.nome: cat for cat in todas_categorias}
    categorias_ordenadas = [categorias_dict[nome] for nome in ordem_desejada if nome in categorias_dict]
    return categorias_ordenadas

# --- Rotas Públicas e API ---

@app.route('/')
def cliente_cardapio():
    categorias = get_categorias_ordenadas()
    whatsapp_number = "5519986088874"
    return render_template('cliente_cardapio.html', categorias=categorias, whatsapp_number=whatsapp_number)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# === NOVA ROTA DE API PARA SALVAR O PEDIDO ===
@app.route('/api/save_order', methods=['POST'])
def save_order():
    data = request.get_json()
    if not data or 'cart' not in data or 'delivery' not in data:
        return jsonify({'success': False, 'message': 'Dados inválidos'}), 400

    try:
        # Cria o pedido principal
        novo_pedido = Pedido(
            tipo_entrega=data['delivery']['label'],
            taxa_entrega=data['delivery']['fee'],
            total=data['total']
        )
        db.session.add(novo_pedido)
        
        # Adiciona os itens ao pedido
        for nome, item_data in data['cart'].items():
            item_pedido = ItemPedido(
                pedido=novo_pedido,
                nome_produto=nome,
                quantidade=item_data['quantity'],
                preco_unitario=item_data['price']
            )
            db.session.add(item_pedido)
            
        db.session.commit()
        return jsonify({'success': True, 'order_id': novo_pedido.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# --- Rotas do Painel Administrativo ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'dogao123':
            session['logged_in'] = True
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# === NOVAS ROTAS PARA HISTÓRICO DE PEDIDOS ===

@app.route('/admin/historico')
@login_required
def historico_pedidos():
    pedidos = Pedido.query.order_by(Pedido.timestamp.desc()).all()
    return render_template('historico_pedidos.html', pedidos=pedidos)

@app.route('/admin/pedido/deletar/<int:pedido_id>', methods=['POST'])
@login_required
def deletar_pedido(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    db.session.delete(pedido)
    db.session.commit()
    flash(f'Pedido #{pedido_id} deletado com sucesso.', 'success')
    return redirect(url_for('historico_pedidos'))

@app.route('/admin/pedido/imprimir/<int:pedido_id>')
@login_required
def imprimir_pedido(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    return render_template('imprimir_pedido.html', pedido=pedido)

# (Rotas de gerenciar produtos e categorias continuam as mesmas, com @login_required)
# ... (código anterior das rotas de admin_cardapio, editar_produto, etc.) ...
@app.route('/admin/cardapio', methods=['GET', 'POST'])
@login_required
def admin_cardapio():
    if request.method == 'POST':
        imagem_salva = None
        if 'productImage' in request.files:
            file = request.files['productImage']
            if file.filename != '':
                imagem_salva = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], imagem_salva))
        novo_produto = Produto(nome=request.form['productName'],preco=float(request.form['productPrice']),descricao=request.form['productDescription'],categoria_id=request.form['productCategory'],imagem_url=imagem_salva)
        db.session.add(novo_produto)
        db.session.commit()
        flash('Produto adicionado com sucesso!', 'success')
        return redirect(url_for('admin_cardapio'))
    categorias = get_categorias_ordenadas()
    return render_template('admin_cardapio.html', categorias=categorias)

@app.route('/admin/produto/editar/<int:produto_id>', methods=['GET', 'POST'])
@login_required
def editar_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    categorias = Categoria.query.all()
    if request.method == 'POST':
        produto.nome = request.form['productName']
        produto.preco = float(request.form['productPrice'])
        produto.descricao = request.form['productDescription']
        produto.categoria_id = request.form['productCategory']
        if 'productImage' in request.files:
            file = request.files['productImage']
            if file.filename != '':
                imagem_salva = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], imagem_salva))
                produto.imagem_url = imagem_salva
        db.session.commit()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('admin_cardapio'))
    return render_template('editar_produto.html', produto=produto, categorias=categorias)

@app.route('/admin/produto/toggle/<int:produto_id>', methods=['POST'])
@login_required
def toggle_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    produto.ativo = not produto.ativo
    db.session.commit()
    status = "ativado" if produto.ativo else "desativado"
    flash(f'Produto {produto.nome} foi {status}.', 'info')
    return redirect(url_for('admin_cardapio'))

@app.route('/admin/categorias')
@login_required
def admin_categorias():
    categorias = get_categorias_ordenadas()
    return render_template('admin_categorias.html', categorias=categorias)

@app.route('/admin/categoria/update_image/<int:categoria_id>', methods=['POST'])
@login_required
def update_categoria_image(categoria_id):
    categoria = Categoria.query.get_or_404(categoria_id)
    if 'categoryImage' in request.files:
        file = request.files['categoryImage']
        if file.filename != '':
            if categoria.imagem_url and 'http' not in categoria.imagem_url:
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], categoria.imagem_url)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            imagem_salva = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], imagem_salva))
            categoria.imagem_url = imagem_salva
            db.session.commit()
            flash(f'Imagem da categoria "{categoria.nome}" atualizada com sucesso!', 'success')
        else:
            flash('Nenhum arquivo selecionado.', 'danger')
    return redirect(url_for('admin_categorias'))


@app.cli.command("init-db")
def init_db_command():
    db.create_all()
    print("Banco de dados e tabelas criados com sucesso.")