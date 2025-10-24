from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime

# O user_loader é usado pelo Flask-Login para recarregar o objeto do usuário a partir do ID do usuário armazenado na sessão.
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(128), nullable=False)
    # 'cliente', 'admin' ou 'vendedor'
    role = db.Column(db.String(20), nullable=False, default='cliente')

    # Relacionamentos
    pedidos = db.relationship('Pedido', backref='comprador', lazy=True)
    carrinho = db.relationship('ItemCarrinho', backref='usuario', lazy=True, cascade="all, delete-orphan")
    lista_desejos = db.relationship('ItemListaDesejos', backref='usuario', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"Usuario('{self.nome}', '{self.email}')"

class Peca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    preco = db.Column(db.Float, nullable=False)
    estoque = db.Column(db.Integer, nullable=False)
    imagem_url = db.Column(db.String(500), nullable=False, default='https://placehold.co/600x400?text=Sem+Imagem')

    def __repr__(self):
        return f"Peca('{self.nome}', Preço: {self.preco})"

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data_pedido = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # --- ALTERAÇÃO AQUI ---
    # O valor padrão foi alterado de 'Processando' para 'Aguardando Pagamento'
    status = db.Column(db.String(30), nullable=False, default='Aguardando Pagamento') 
    # --- FIM DA ALTERAÇÃO ---

    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    # Campos de endereço
    cep = db.Column(db.String(9), nullable=False)
    rua = db.Column(db.String(200), nullable=False)
    numero = db.Column(db.String(20), nullable=False)
    bairro = db.Column(db.String(100), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    
    # Relacionamento com os itens do pedido
    itens = db.relationship('ItemPedido', backref='pedido', lazy=True, cascade="all, delete-orphan")

class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)  # Preço no momento da compra
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    peca_id = db.Column(db.Integer, db.ForeignKey('peca.id'), nullable=False)
    peca = db.relationship('Peca')

class ItemCarrinho(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantidade = db.Column(db.Integer, nullable=False, default=1)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    peca_id = db.Column(db.Integer, db.ForeignKey('peca.id'), nullable=False)
    peca = db.relationship('Peca')

class ItemListaDesejos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    peca_id = db.Column(db.Integer, db.ForeignKey('peca.id'), nullable=False)
    peca = db.relationship('Peca')
