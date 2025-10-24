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

# Decorator para rotas de cliente
def client_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'cliente':
            flash('Acesso negado. Esta funcionalidade é apenas para clientes.', 'warning')
            return redirect(url_for('routes.admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- ADIÇÃO ---
# Decorator para rotas de vendedor
def vendedor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'vendedor':
            flash('Acesso negado. Esta área é apenas para vendedores.', 'danger')
            return redirect(url_for('routes.index'))
        return f(*args, **kwargs)
    return decorated_function
# --- FIM DA ADIÇÃO ---

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
        # Por padrão, novos registros são 'cliente'. O admin ou vendedor deve ser setado manualmente no BD.
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
        if current_user.role == 'admin':
            return redirect(url_for('routes.admin_dashboard'))
        # --- ALTERAÇÃO ---
        if current_user.role == 'vendedor':
            return redirect(url_for('routes.vendedor_dashboard'))
        # --- FIM DA ALTERAÇÃO ---
        return redirect(url_for('routes.index'))
    
    if request.method == 'POST':
        usuario = Usuario.query.filter_by(email=request.form.get('email')).first()
        if usuario and bcrypt.check_password_hash(usuario.senha_hash, request.form.get('senha')):
            login_user(usuario, remember=True)
            next_page = request.args.get('next')
            flash('Login bem-sucedido!', 'success')
            
            if current_user.role == 'admin':
                return redirect(url_for('routes.admin_dashboard'))
            # --- ALTERAÇÃO ---
            if current_user.role == 'vendedor':
                return redirect(url_for('routes.vendedor_dashboard'))
            # --- FIM DA ALTERAÇÃO ---
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
@client_required
def carrinho():
    itens_carrinho = ItemCarrinho.query.filter_by(usuario_id=current_user.id).all()
    total = sum(item.peca.preco * item.quantidade for item in itens_carrinho)
    return render_template('cliente/carrinho.html', title='Carrinho', itens_carrinho=itens_carrinho, total=total)

@bp.route("/adicionar_carrinho/<int:peca_id>", methods=['POST'])
@login_required
@client_required
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
@client_required
def remover_carrinho(item_id):
    item = ItemCarrinho.query.get_or_404(item_id)
    if item.usuario_id != current_user.id:
        return redirect(url_for('routes.carrinho'))
    db.session.delete(item)
    db.session.commit()
    flash('Item removido do carrinho.', 'success')
    return redirect(url_for('routes.carrinho'))

@bp.route("/lista_desejos")
@login_required
@client_required
def lista_desejos():
    itens = ItemListaDesejos.query.filter_by(usuario_id=current_user.id).all()
    return render_template('cliente/lista_desejos.html', title='Lista de Desejos', itens=itens)

@bp.route("/adicionar_desejo/<int:peca_id>", methods=['POST'])
@login_required
@client_required
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
@client_required
def remover_desejo(item_id):
    item = ItemListaDesejos.query.get_or_404(item_id)
    if item.usuario_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
        flash('Item removido da lista de desejos.', 'success')
    return redirect(url_for('routes.lista_desejos'))

# --- ADIÇÃO ---
@bp.route("/meus_pedidos")
@login_required
@client_required
def meus_pedidos():
    pedidos = Pedido.query.filter_by(usuario_id=current_user.id).order_by(Pedido.data_pedido.desc()).all()
    return render_template('cliente/meus_pedidos.html', title='Meus Pedidos', pedidos=pedidos)
# --- FIM DA ADIÇÃO ---

@bp.route("/finalizar-compra/endereco", methods=['GET', 'POST'])
@login_required
@client_required
def endereco_entrega():
    itens_carrinho = ItemCarrinho.query.filter_by(usuario_id=current_user.id).all()
    if not itens_carrinho:
        flash('Seu carrinho está vazio. Adicione itens antes de prosseguir.', 'info')
        return redirect(url_for('routes.index'))

    if request.method == 'POST':
        # Pega os dados do endereço do formulário
        cep = request.form.get('cep')
        rua = request.form.get('rua')
        numero = request.form.get('numero')
        bairro = request.form.get('bairro')
        cidade = request.form.get('cidade')

        # Cria o novo pedido com todos os dados de endereço
        novo_pedido = Pedido(
            usuario_id=current_user.id,
            cep=cep,
            rua=rua,
            numero=numero,
            bairro=bairro,
            cidade=cidade
        )
        db.session.add(novo_pedido)

        # Move os itens do carrinho para o pedido
        for item in itens_carrinho:
            # Mantém a verificação de estoque, mas não subtrai
            if item.peca.estoque < item.quantidade:
                flash(f'Estoque insuficiente para {item.peca.nome}. Pedido não finalizado.', 'danger')
                db.session.rollback()
                return redirect(url_for('routes.carrinho'))
            
            item_pedido = ItemPedido(
                pedido=novo_pedido,
                peca_id=item.peca_id,
                quantidade=item.quantidade,
                preco_unitario=item.peca.preco
            )
            db.session.add(item_pedido)
            
            # --- ALTERAÇÃO: LINHA REMOVIDA ---
            # item.peca.estoque -= item.quantidade
            
            db.session.delete(item)

        db.session.commit()
        
        # --- ALTERAÇÃO: MENSAGEM FLASH ---
        flash('Pedido recebido! Aguardando confirmação de pagamento.', 'success')
        return redirect(url_for('routes.index'))

    # Se o método for GET, exibe a página do formulário
    return render_template('cliente/endereco_entrega.html', title='Endereço de Entrega')

# --- ROTAS DO VENDEDOR --- (NOVA SEÇÃO)

@bp.route("/vendedor")
@login_required
@vendedor_required
def vendedor_dashboard():
    # Busca apenas pedidos que estão aguardando pagamento
    pedidos = Pedido.query.filter_by(status='Aguardando Pagamento').order_by(Pedido.data_pedido.asc()).all()
    return render_template('vendedor/dashboard.html', title='Painel do Vendedor', pedidos=pedidos)

@bp.route("/vendedor/confirmar_pagamento/<int:pedido_id>", methods=['POST'])
@login_required
@vendedor_required
def confirmar_pagamento(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    
    # Verifica se o pedido realmente está aguardando pagamento
    if pedido.status != 'Aguardando Pagamento':
        flash('Este pedido não está aguardando pagamento.', 'warning')
        return redirect(url_for('routes.vendedor_dashboard'))

    # --- LÓGICA DE ESTOQUE MOVIDA PARA CÁ ---
    # 1. Verificar estoque ANTES de confirmar
    for item in pedido.itens:
        if item.peca.estoque < item.quantidade:
            flash(f'Pagamento NÃO confirmado. Estoque insuficiente para {item.peca.nome}.', 'danger')
            return redirect(url_for('routes.vendedor_dashboard'))

    # 2. Se o estoque estiver OK, subtrair
    for item in pedido.itens:
        item.peca.estoque -= item.quantidade
    
    # 3. Alterar status do pedido
    pedido.status = 'Pago' # Admin agora verá este status
    
    db.session.commit()
    
    flash(f'Pagamento do Pedido #{pedido.id} confirmado com sucesso. Estoque atualizado.', 'success')
    return redirect(url_for('routes.vendedor_dashboard'))

# --- FIM DAS ROTAS DO VENDEDOR ---


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

# --- ALTERAÇÃO: ROTA REMOVIDA (COMENTADA) ---
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
# --- FIM DA ROTA REMOVIDA ---


@bp.route("/admin/adicionar_peca", methods=['GET', 'POST'])
@login_required
@admin_required
def admin_adicionar_peca():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        preco = float(request.form.get('preco'))
        estoque = int(request.form.get('estoque'))
        imagem_url = request.form.get('imagem_url') 
        dados_nova_peca = {
            'nome': nome,
            'descricao': descricao,
            'preco': preco,
            'estoque': estoque
        }

        if imagem_url:
            dados_nova_peca['imagem_url'] = imagem_url
        
        nova_peca = Peca(**dados_nova_peca)
        db.session.add(nova_peca)
        db.session.commit()
        flash(f'A peça "{nome}" foi adicionada com sucesso!', 'success')
        return redirect(url_for('routes.admin_dashboard'))
    return render_template('admin/adicionar_peca.html', title='Adicionar Nova Peça')