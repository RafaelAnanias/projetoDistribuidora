from flask import render_template, url_for, flash, redirect, request, Blueprint
from app import db, bcrypt
from app.models import Usuario, Peca, ItemCarrinho, ItemListaDesejos, Pedido, ItemPedido
from flask_login import login_user, current_user, logout_user, login_required
from functools import wraps

bp = Blueprint('routes', __name__)

# Decorator para rotas de admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Acesso negado. Esta área é apenas para administradores.', 'danger')
            return redirect(url_for('routes.index'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS GERAIS E DE AUTENTICAÇÃO ---

@bp.route("/")
@bp.route("/index")
def index():
    pecas = Peca.query.all()
    return render_template('index.html', pecas=pecas, title="Página Inicial")

@bp.route("/registrar", methods=['GET', 'POST'])
def registrar():
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    if request.method == 'POST':
        senha_hash = bcrypt.generate_password_hash(request.form.get('senha')).decode('utf-8')
        # Garante que o primeiro usuário seja admin, ou defina como preferir.
        role = 'admin' if Usuario.query.count() == 0 else 'cliente'
        usuario = Usuario(nome=request.form.get('nome'), email=request.form.get('email'), senha_hash=senha_hash, role=role)
        db.session.add(usuario)
        db.session.commit()
        flash(f'Conta criada para {request.form.get("nome")}! Você já pode fazer login.', 'success')
        return redirect(url_for('routes.login'))
    return render_template('auth/registrar.html', title='Registrar')

@bp.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))
    if request.method == 'POST':
        usuario = Usuario.query.filter_by(email=request.form.get('email')).first()
        if usuario and bcrypt.check_password_hash(usuario.senha_hash, request.form.get('senha')):
            login_user(usuario, remember=True)
            next_page = request.args.get('next')
            flash('Login bem-sucedido!', 'success')
            if current_user.role == 'admin':
                return redirect(url_for('routes.admin_dashboard'))
            return redirect(next_page) if next_page else redirect(url_for('routes.index'))
        else:
            flash('Login falhou. Verifique o e-mail e a senha.', 'danger')
    return render_template('auth/login.html', title='Login')

@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('routes.index'))

@bp.route("/peca/<int:peca_id>")
def peca(peca_id):
    peca = Peca.query.get_or_404(peca_id)
    return render_template('cliente/peca.html', title=peca.nome, peca=peca)


# --- ROTAS DO CLIENTE ---

@bp.route("/carrinho")
@login_required
def carrinho():
    itens_carrinho = ItemCarrinho.query.filter_by(usuario_id=current_user.id).all()
    total = sum(item.peca.preco * item.quantidade for item in itens_carrinho)
    return render_template('cliente/carrinho.html', title='Carrinho', itens_carrinho=itens_carrinho, total=total)

@bp.route("/adicionar_carrinho/<int:peca_id>", methods=['POST'])
@login_required
def adicionar_carrinho(peca_id):
    peca = Peca.query.get_or_404(peca_id)
    item_existente = ItemCarrinho.query.filter_by(usuario_id=current_user.id, peca_id=peca.id).first()
    
    if item_existente:
        item_existente.quantidade += 1
    else:
        novo_item = ItemCarrinho(usuario_id=current_user.id, peca_id=peca.id)
        db.session.add(novo_item)
    
    db.session.commit()
    flash(f'{peca.nome} foi adicionado ao seu carrinho!', 'success')
    return redirect(url_for('routes.carrinho'))

@bp.route("/remover_carrinho/<int:item_id>", methods=['POST'])
@login_required
def remover_carrinho(item_id):
    item = ItemCarrinho.query.get_or_404(item_id)
    if item.usuario_id != current_user.id:
        # Abortar se o item não pertence ao usuário atual
        return redirect(url_for('routes.carrinho'))
    db.session.delete(item)
    db.session.commit()
    flash('Item removido do carrinho.', 'success')
    return redirect(url_for('routes.carrinho'))

@bp.route("/lista_desejos")
@login_required
def lista_desejos():
    itens = ItemListaDesejos.query.filter_by(usuario_id=current_user.id).all()
    return render_template('cliente/lista_desejos.html', title='Lista de Desejos', itens=itens)

@bp.route("/adicionar_desejo/<int:peca_id>", methods=['POST'])
@login_required
def adicionar_desejo(peca_id):
    peca = Peca.query.get_or_404(peca_id)
    item_existente = ItemListaDesejos.query.filter_by(usuario_id=current_user.id, peca_id=peca.id).first()
    if not item_existente:
        novo_item = ItemListaDesejos(usuario_id=current_user.id, peca_id=peca.id)
        db.session.add(novo_item)
        db.session.commit()
        flash(f'{peca.nome} adicionado à sua lista de desejos!', 'success')
    else:
        flash(f'{peca.nome} já está na sua lista de desejos.', 'info')
    return redirect(request.referrer or url_for('routes.index'))


@bp.route("/remover_desejo/<int:item_id>", methods=['POST'])
@login_required
def remover_desejo(item_id):
    item = ItemListaDesejos.query.get_or_404(item_id)
    if item.usuario_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
        flash('Item removido da lista de desejos.', 'success')
    return redirect(url_for('routes.lista_desejos'))

@bp.route("/finalizar_compra", methods=['POST'])
@login_required
def finalizar_compra():
    itens_carrinho = ItemCarrinho.query.filter_by(usuario_id=current_user.id).all()
    if not itens_carrinho:
        flash('Seu carrinho está vazio.', 'info')
        return redirect(url_for('routes.carrinho'))

    # Criar um novo pedido
    novo_pedido = Pedido(usuario_id=current_user.id)
    db.session.add(novo_pedido)

    # Mover itens do carrinho para itens de pedido e atualizar estoque
    for item in itens_carrinho:
        if item.peca.estoque < item.quantidade:
            flash(f'Estoque insuficiente para {item.peca.nome}.', 'danger')
            return redirect(url_for('routes.carrinho'))
        
        item_pedido = ItemPedido(
            pedido=novo_pedido,
            peca_id=item.peca_id,
            quantidade=item.quantidade,
            preco_unitario=item.peca.preco
        )
        db.session.add(item_pedido)
        item.peca.estoque -= item.quantidade
        db.session.delete(item)

    db.session.commit()
    flash('Compra finalizada com sucesso! Seu pedido está sendo processado.', 'success')
    return redirect(url_for('routes.index'))

# --- ROTAS DO ADMINISTRADOR ---

@bp.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    return render_template('admin/dashboard.html', title='Dashboard Admin')

@bp.route("/admin/pedidos")
@login_required
@admin_required
def admin_pedidos():
    pedidos = Pedido.query.order_by(Pedido.data_pedido.desc()).all()
    return render_template('admin/pedidos.html', title='Gerenciar Pedidos', pedidos=pedidos)

@bp.route("/admin/pedido/<int:pedido_id>/status", methods=['POST'])
@login_required
@admin_required
def atualizar_status_pedido(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    novo_status = request.form.get('status')
    if novo_status in ['Processando', 'Enviado', 'Entregue', 'Cancelado']:
        pedido.status = novo_status
        db.session.commit()
        flash(f'Status do pedido {pedido.id} atualizado para {novo_status}.', 'success')
    else:
        flash('Status inválido.', 'danger')
    return redirect(url_for('routes.admin_pedidos'))


# <<< ROTA MODIFICADA ABAIXO
@bp.route("/admin/adicionar_peca", methods=['GET', 'POST'])
@login_required
@admin_required
def admin_adicionar_peca():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        preco = float(request.form.get('preco'))
        estoque = int(request.form.get('estoque'))
        imagem_url = request.form.get('imagem_url') # Pega a URL do formulário

        # Cria um dicionário para os dados da nova peça
        dados_nova_peca = {
            'nome': nome,
            'descricao': descricao,
            'preco': preco,
            'estoque': estoque
        }

        # Adiciona a URL somente se o campo não estiver vazio
        # Se estiver vazio, o 'default' do model será usado
        if imagem_url:
            dados_nova_peca['imagem_url'] = imagem_url
        
        nova_peca = Peca(**dados_nova_peca)
        db.session.add(nova_peca)
        db.session.commit()
        flash(f'A peça "{nome}" foi adicionada com sucesso!', 'success')
        return redirect(url_for('routes.admin_dashboard'))
    return render_template('admin/adicionar_peca.html', title='Adicionar Nova Peça')




















# from flask import render_template, url_for, flash, redirect, request, Blueprint
# from app import db, bcrypt
# from app.models import Usuario, Peca, ItemCarrinho, ItemListaDesejos, Pedido, ItemPedido
# from flask_login import login_user, current_user, logout_user, login_required
# from functools import wraps

# bp = Blueprint('routes', __name__)

# # Decorator para rotas de admin
# def admin_required(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if not current_user.is_authenticated or current_user.role != 'admin':
#             flash('Acesso negado. Esta área é apenas para administradores.', 'danger')
#             return redirect(url_for('routes.index'))
#         return f(*args, **kwargs)
#     return decorated_function

# # --- ROTAS GERAIS E DE AUTENTICAÇÃO ---

# @bp.route("/")
# @bp.route("/index")
# def index():
#     pecas = Peca.query.all()
#     return render_template('index.html', pecas=pecas, title="Página Inicial")

# @bp.route("/registrar", methods=['GET', 'POST'])
# def registrar():
#     if current_user.is_authenticated:
#         return redirect(url_for('routes.index'))
#     if request.method == 'POST':
#         senha_hash = bcrypt.generate_password_hash(request.form.get('senha')).decode('utf-8')
#         # Garante que o primeiro usuário seja admin, ou defina como preferir.
#         role = 'admin' if Usuario.query.count() == 0 else 'cliente'
#         usuario = Usuario(nome=request.form.get('nome'), email=request.form.get('email'), senha_hash=senha_hash, role=role)
#         db.session.add(usuario)
#         db.session.commit()
#         flash(f'Conta criada para {request.form.get("nome")}! Você já pode fazer login.', 'success')
#         return redirect(url_for('routes.login'))
#     return render_template('auth/registrar.html', title='Registrar')

# @bp.route("/login", methods=['GET', 'POST'])
# def login():
#     if current_user.is_authenticated:
#         return redirect(url_for('routes.index'))
#     if request.method == 'POST':
#         usuario = Usuario.query.filter_by(email=request.form.get('email')).first()
#         if usuario and bcrypt.check_password_hash(usuario.senha_hash, request.form.get('senha')):
#             login_user(usuario, remember=True)
#             next_page = request.args.get('next')
#             flash('Login bem-sucedido!', 'success')
#             if current_user.role == 'admin':
#                 return redirect(url_for('routes.admin_dashboard'))
#             return redirect(next_page) if next_page else redirect(url_for('routes.index'))
#         else:
#             flash('Login falhou. Verifique o e-mail e a senha.', 'danger')
#     return render_template('auth/login.html', title='Login')

# @bp.route("/logout")
# def logout():
#     logout_user()
#     return redirect(url_for('routes.index'))

# @bp.route("/peca/<int:peca_id>")
# def peca(peca_id):
#     peca = Peca.query.get_or_404(peca_id)
#     return render_template('cliente/peca.html', title=peca.nome, peca=peca)


# # --- ROTAS DO CLIENTE ---

# @bp.route("/carrinho")
# @login_required
# def carrinho():
#     itens_carrinho = ItemCarrinho.query.filter_by(usuario_id=current_user.id).all()
#     total = sum(item.peca.preco * item.quantidade for item in itens_carrinho)
#     return render_template('cliente/carrinho.html', title='Carrinho', itens_carrinho=itens_carrinho, total=total)

# @bp.route("/adicionar_carrinho/<int:peca_id>", methods=['POST'])
# @login_required
# def adicionar_carrinho(peca_id):
#     peca = Peca.query.get_or_404(peca_id)
#     item_existente = ItemCarrinho.query.filter_by(usuario_id=current_user.id, peca_id=peca.id).first()
    
#     if item_existente:
#         item_existente.quantidade += 1
#     else:
#         novo_item = ItemCarrinho(usuario_id=current_user.id, peca_id=peca.id)
#         db.session.add(novo_item)
    
#     db.session.commit()
#     flash(f'{peca.nome} foi adicionado ao seu carrinho!', 'success')
#     return redirect(url_for('routes.carrinho'))

# @bp.route("/remover_carrinho/<int:item_id>", methods=['POST'])
# @login_required
# def remover_carrinho(item_id):
#     item = ItemCarrinho.query.get_or_404(item_id)
#     if item.usuario_id != current_user.id:
#         # Abortar se o item não pertence ao usuário atual
#         return redirect(url_for('routes.carrinho'))
#     db.session.delete(item)
#     db.session.commit()
#     flash('Item removido do carrinho.', 'success')
#     return redirect(url_for('routes.carrinho'))

# @bp.route("/lista_desejos")
# @login_required
# def lista_desejos():
#     itens = ItemListaDesejos.query.filter_by(usuario_id=current_user.id).all()
#     return render_template('cliente/lista_desejos.html', title='Lista de Desejos', itens=itens)

# @bp.route("/adicionar_desejo/<int:peca_id>", methods=['POST'])
# @login_required
# def adicionar_desejo(peca_id):
#     peca = Peca.query.get_or_404(peca_id)
#     item_existente = ItemListaDesejos.query.filter_by(usuario_id=current_user.id, peca_id=peca.id).first()
#     if not item_existente:
#         novo_item = ItemListaDesejos(usuario_id=current_user.id, peca_id=peca.id)
#         db.session.add(novo_item)
#         db.session.commit()
#         flash(f'{peca.nome} adicionado à sua lista de desejos!', 'success')
#     else:
#         flash(f'{peca.nome} já está na sua lista de desejos.', 'info')
#     return redirect(request.referrer or url_for('routes.index'))


# @bp.route("/remover_desejo/<int:item_id>", methods=['POST'])
# @login_required
# def remover_desejo(item_id):
#     item = ItemListaDesejos.query.get_or_404(item_id)
#     if item.usuario_id == current_user.id:
#         db.session.delete(item)
#         db.session.commit()
#         flash('Item removido da lista de desejos.', 'success')
#     return redirect(url_for('routes.lista_desejos'))

# @bp.route("/finalizar_compra", methods=['POST'])
# @login_required
# def finalizar_compra():
#     itens_carrinho = ItemCarrinho.query.filter_by(usuario_id=current_user.id).all()
#     if not itens_carrinho:
#         flash('Seu carrinho está vazio.', 'info')
#         return redirect(url_for('routes.carrinho'))

#     # Criar um novo pedido
#     novo_pedido = Pedido(usuario_id=current_user.id)
#     db.session.add(novo_pedido)

#     # Mover itens do carrinho para itens de pedido e atualizar estoque
#     for item in itens_carrinho:
#         if item.peca.estoque < item.quantidade:
#             flash(f'Estoque insuficiente para {item.peca.nome}.', 'danger')
#             return redirect(url_for('routes.carrinho'))
        
#         item_pedido = ItemPedido(
#             pedido=novo_pedido,
#             peca_id=item.peca_id,
#             quantidade=item.quantidade,
#             preco_unitario=item.peca.preco
#         )
#         db.session.add(item_pedido)
#         item.peca.estoque -= item.quantidade
#         db.session.delete(item)

#     db.session.commit()
#     flash('Compra finalizada com sucesso! Seu pedido está sendo processado.', 'success')
#     return redirect(url_for('routes.index'))

# # --- ROTAS DO ADMINISTRADOR ---

# @bp.route("/admin")
# @login_required
# @admin_required
# def admin_dashboard():
#     return render_template('admin/dashboard.html', title='Dashboard Admin')

# @bp.route("/admin/pedidos")
# @login_required
# @admin_required
# def admin_pedidos():
#     pedidos = Pedido.query.order_by(Pedido.data_pedido.desc()).all()
#     return render_template('admin/pedidos.html', title='Gerenciar Pedidos', pedidos=pedidos)

# @bp.route("/admin/pedido/<int:pedido_id>/status", methods=['POST'])
# @login_required
# @admin_required
# def atualizar_status_pedido(pedido_id):
#     pedido = Pedido.query.get_or_404(pedido_id)
#     novo_status = request.form.get('status')
#     if novo_status in ['Processando', 'Enviado', 'Entregue', 'Cancelado']:
#         pedido.status = novo_status
#         db.session.commit()
#         flash(f'Status do pedido {pedido.id} atualizado para {novo_status}.', 'success')
#     else:
#         flash('Status inválido.', 'danger')
#     return redirect(url_for('routes.admin_pedidos'))


# @bp.route("/admin/adicionar_peca", methods=['GET', 'POST'])
# @login_required
# @admin_required
# def admin_adicionar_peca():
#     if request.method == 'POST':
#         nome = request.form.get('nome')
#         descricao = request.form.get('descricao')
#         preco = float(request.form.get('preco'))
#         estoque = int(request.form.get('estoque'))
#         nova_peca = Peca(nome=nome, descricao=descricao, preco=preco, estoque=estoque)
#         db.session.add(nova_peca)
#         db.session.commit()
#         flash(f'A peça "{nome}" foi adicionada com sucesso!', 'success')
#         return redirect(url_for('routes.admin_dashboard'))
#     return render_template('admin/adicionar_peca.html', title='Adicionar Nova Peça')