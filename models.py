from db import db
from flask_login import UserMixin


class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(30), unique=True)
    senha = db.Column(db.String())
    email = db.Column(db.String(), unique=True)

    # Relacionamentos com os dados financeiros do usuário
    gastos = db.relationship('Gasto', backref='usuario', lazy=True)
    reservas = db.relationship('ReservaMovimentacao', backref='usuario', lazy=True)
    parcelamentos = db.relationship('Parcelamento', backref='usuario', lazy=True)
    contas_bancarias = db.relationship('ContaBancaria', backref='usuario', lazy=True)


class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.String(10), nullable=False)
    cartao = db.Column(db.String(50), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    def __repr__(self):
        return f'<Gasto {self.descricao} - R${self.valor}>'

class ReservaMovimentacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False) # 'Adição' ou 'Subtração'
    valor = db.Column(db.Float, nullable=False)
    data = db.Column(db.String(10), nullable=False) # Armazenar como string "dd/mm/yy"
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False) # Novo campo

    def __repr__(self):
        return f'<Reserva {self.tipo} - R${self.valor}>'

class Parcelamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    valor_total = db.Column(db.Float, nullable=False)
    num_parcelas = db.Column(db.Integer, nullable=False)
    parcelas_pagas = db.Column(db.Integer, default=0, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False) # Novo campo

    def __repr__(self):
        return f'<Parcelamento {self.nome} - {self.parcelas_pagas}/{self.num_parcelas}>'

class ContaBancaria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False) # Removido unique=True, agora é unique por usuário
    saldo = db.Column(db.Float, default=0.00, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False) # Novo campo

    # Garante que a combinação nome da conta + usuario_id seja única
    __table_args__ = (db.UniqueConstraint('nome', 'usuario_id', name='_nome_usuario_uc'),)

    def __repr__(self):
        return f'<Conta {self.nome} - R${self.saldo}>'
