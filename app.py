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

# === INÍCIO DA ALTERAÇÃO ===
# 1. Função ajudante para ordenar as categorias na ordem desejada
def get_categorias_ordenadas():
    ordem_desejada = ["Hot Dog", "Lanches", "Bebidas", "Sobremesas"]
    todas_categorias = Categoria.query.all()
    
    # Cria um dicionário para fácil acesso: {'Lanches': <Objeto Lanches>, ...}
    categorias_dict = {cat.nome: cat for cat in todas_categorias}
    
    # Monta a lista final na ordem correta
    categorias_ordenadas = [categorias_dict[nome] for nome in ordem_desejada if nome in categorias_dict]
    
    return categorias_ordenadas
# === FIM DA ALTERAÇÃO ===


# --- Rotas da Aplicação ---

@app.route('/')
def cliente_cardapio():
    # 2. Usa a nova função para buscar as categorias na ordem certa
    categorias = get_categorias_ordenadas()
    whatsapp_number = "5519986088874"
    return render_template('cliente_cardapio.html', categorias=categorias, whatsapp_number=whatsapp_number)

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
        if 'productImage' in request.files:
            file = request.files['productImage']
            if file.filename != '':
                imagem_salva = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], imagem_salva))

        novo_produto = Produto(
            nome=request.form['productName'],
            preco=float(request.form['productPrice']),
            descricao=request.form['productDescription'],
            categoria_id=request.form['productCategory'],
            imagem_url=imagem_salva
        )
        db.session.add(novo_produto)
        db.session.commit()
        flash('Produto adicionado com sucesso!', 'success')
        return redirect(url_for('admin_cardapio'))
    
    # 3. Usa a função aqui também para manter a consistência no painel
    categorias = get_categorias_ordenadas()
    return render_template('admin_cardapio.html', categorias=categorias)

@app.route('/admin/produto/editar/<int:produto_id>', methods=['GET', 'POST'])
def editar_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    categorias = Categoria.query.all() # A ordem no dropdown de edição não importa tanto

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
def toggle_produto(produto_id):
    produto = Produto.query.get_or_404(produto_id)
    produto.ativo = not produto.ativo
    db.session.commit()
    status = "ativado" if produto.ativo else "desativado"
    flash(f'Produto {produto.nome} foi {status}.', 'info')
    return redirect(url_for('admin_cardapio'))

@app.route('/admin/categorias')
def admin_categorias():
    # 4. E finalmente aqui, para a página de gerenciamento de categorias
    categorias = get_categorias_ordenadas()
    return render_template('admin_categorias.html', categorias=categorias)

@app.route('/admin/categoria/update_image/<int:categoria_id>', methods=['POST'])
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

# --- Comando para inicializar o banco de dados ---
@app.cli.command("init-db")
def init_db_command():
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