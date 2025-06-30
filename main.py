from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
from flask_mail import Mail, Message
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_sqlalchemy import SQLAlchemy
from models import Usuario, Gasto, ReservaMovimentacao, Parcelamento, ContaBancaria # Importe todos os modelos
from db import db
import hashlib

app = Flask(__name__)
app.secret_key = 'finanaças' # Certifique-se de que esta chave seja forte e secreta!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///financeiro.db' # Mudei para financeiro.db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Esta linha estava duplicada e apontando para database.db. Removi a duplicação.
# app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///database.db"
db.init_app(app)


login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Configuração do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.mail.yahoo.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'meuemail@yahoo.com.br'  # Altere para seu email
app.config['MAIL_PASSWORD'] = 'suasenhaapp'    # Altere para a senha de aplicativo do seu email
app.config['MAIL_DEFAULT_SENDER'] = 'meuemail@yahoo.com.br' # Altere para seu email
mail = Mail(app)

# Criador para tokens seguros
s = URLSafeTimedSerializer(app.secret_key)

def hash(txt):
    return hashlib.sha256(txt.encode('utf-8')).hexdigest()

@login_manager.user_loader
def user_loader(id):
    return Usuario.query.get(int(id))


@app.route('/incorretos', methods=['GET', 'POST'])
def incorretos():
    if request.method == 'GET':
        return render_template('incorretos.html')
    if request.method == 'POST':
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: # Se já estiver logado, redireciona para home
        return redirect(url_for('home'))

    if request.method == 'GET':
        return render_template('login.html')
    
    acao = request.form.get('acao')

    if acao == 'log':
        nome = request.form['nomeForm']
        senha = request.form['senhaForm']
        user = Usuario.query.filter_by(nome=nome, senha=hash(senha)).first()
        if not user:
            flash('Nome de usuário ou senha incorretos!', 'error') # Mensagem mais informativa
            return redirect(url_for('incorretos')) # ou render_template('login.html', erro="...")
        login_user(user)
        return redirect(url_for('home'))

    elif acao == 'cad':
        return redirect(url_for('registrar'))

    elif acao == 'rdfSenha':
        return redirect(url_for('redefinirSenha'))

@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'GET':
        return render_template('registrar.html')
    
    nome = request.form['nomeForm']
    senha = request.form['senhaForm']
    confirmForm = request.form['confirmForm']
    email = request.form['emailForm']

    if senha != confirmForm:
        flash("As senhas não conferem!", 'error')
        return render_template('registrar.html', erro="As senhas não conferem!")
    
    if Usuario.query.filter_by(nome=nome).first():
        flash("Nome de usuário já existe.", 'error')
        return render_template('registrar.html', erro="Nome de usuário já existe.")
    
    if Usuario.query.filter_by(email=email).first():
        flash("E-mail já cadastrado.", 'error')
        return render_template('registrar.html', erro="E-mail já cadastrado.")

    novo_usuario = Usuario(nome=nome, senha=hash(senha), email=email)
    db.session.add(novo_usuario)
    db.session.commit()
    
    flash('Cadastro realizado com sucesso! Faça login.', 'success')
    return redirect(url_for('login'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login'))


@app.route('/sucesso', methods=['GET', 'POST'])
def sucesso():
    if request.method == 'GET':
        return render_template('sucesso.html')
    elif request.method == 'POST':
        return redirect(url_for('login'))


@app.route('/redefinirsenha', methods=['GET', 'POST'])
def redefinirSenha():
    if request.method == 'GET':
        return render_template('redefinirSenha.html')
    
    email = request.form['emailForm']
    user = Usuario.query.filter_by(email=email).first()
    if not user:
        flash("E-mail não encontrado!", 'error')
        return render_template('redefinirSenha.html', erro="E-mail não encontrado!")

    token = s.dumps(email, salt='redefinir-senha')
    link = url_for('novasenha_token', token=token, _external=True)

    msg = Message('Redefinição de Senha', recipients=[email])
    msg.body = f''' Olá,

Você solicitou a redefinição da sua senha.
Clique no link abaixo para criar uma nova senha (válido por 1 hora):

{link}

Se você não solicitou, ignore este e-mail.

Equipe FlaskApp'''
    try:
        mail.send(msg)
        flash('E-mail de redefinição enviado com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao enviar e-mail: {e}', 'error')
        print(f"Erro ao enviar e-mail: {e}") # Para depuração no console

    return redirect(url_for('sucesso'))

@app.route('/sucessoSenha', methods=['GET', 'POST'])
def sucessoSenha():
    if request.method == 'GET':
        return render_template('sucessoSenha.html')
    if request.method == 'POST':
        return redirect(url_for('login')) # Redirecionar para login após sucesso na senha


@app.route('/novasenha', methods=['GET', 'POST'])
@login_required # Garante que o usuário esteja logado para acessar esta rota direta
def novasenha():
    if request.method == 'GET':
        return render_template('novasenha.html')

    elif request.method == 'POST':
        senha = request.form.get('senhaForm')
        confirmForm = request.form['confirmForm']

        if senha != confirmForm:
            flash("As senhas não conferem!", 'error')
            return render_template('novasenha.html', erro="As senhas não conferem!")

        # current_user já vem do Flask-Login, então ele é o usuário autenticado
        current_user.senha = hash(senha)
        db.session.commit()
        flash('Senha alterada com sucesso!', 'success')
        return redirect(url_for('sucessoSenha'))


@app.route('/novasenha/<token>', methods=['GET', 'POST'])
def novasenha_token(token):
    try:
        email = s.loads(token, salt='redefinir-senha', max_age=3600)
    except SignatureExpired:
        flash('O link de redefinição expirou.', 'error')
        return redirect(url_for('redefinirSenha'))
    except BadSignature:
        flash('Link de redefinição inválido.', 'error')
        return redirect(url_for('redefinirSenha'))

    # Se o token é válido, o usuário pode estar logado ou não.
    # Se não estiver logado, logamos temporariamente o usuário associado ao email do token.
    user_from_token = Usuario.query.filter_by(email=email).first()
    if not user_from_token:
        flash('Usuário associado ao link não encontrado.', 'error')
        return redirect(url_for('redefinirSenha'))
    
    # Loga o usuário se ele não estiver logado, ou se o usuário logado não for o mesmo do token
    if not current_user.is_authenticated or current_user.id != user_from_token.id:
        login_user(user_from_token)


    if request.method == 'GET':
        return render_template('novasenha.html')

    senha = request.form['senhaForm']
    confirmForm = request.form['confirmForm']

    if senha != confirmForm:
        flash("As senhas não conferem!", 'error')
        return render_template('novasenha.html', erro="As senhas não conferem!")

    # O usuário já está logado ou foi logado acima (user_from_token)
    current_user.senha = hash(senha)
    db.session.commit()
    flash('Senha redefinida com sucesso! Faça login com a nova senha.', 'success')
    logout_user() # Desloga para forçar login com a nova senha
    return redirect(url_for('login'))


# --- Funções Auxiliares para Cálculos e Atualizações (AGORA FILTRADAS POR USUÁRIO) ---
@login_required # Garante que só usuários logados possam chamar essas funções
def calcular_gasto_mes_db():
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    
    total_gasto = 0.0
    # Filtra gastos pelo usuário atual
    gastos_do_mes = Gasto.query.filter_by(usuario_id=current_user.id).all() 
    
    for gasto in gastos_do_mes:
        try:
            data_gasto = datetime.strptime(gasto.data, "%d/%m/%y")
            if data_gasto.month == mes_atual and data_gasto.year == ano_atual:
                total_gasto += gasto.valor
        except ValueError:
            pass 
    return total_gasto

@login_required
def calcular_dinheiro_guardado_db():
    # Filtra movimentações de reserva pelo usuário atual
    total_adicoes = db.session.query(db.func.sum(ReservaMovimentacao.valor)).filter_by(
        tipo='Adição', usuario_id=current_user.id).scalar() or 0.0
    total_subtracoes = db.session.query(db.func.sum(ReservaMovimentacao.valor)).filter_by(
        tipo='Subtração', usuario_id=current_user.id).scalar() or 0.0
    return total_adicoes - total_subtracoes

@login_required
def calcular_parcelamentos_ativos_db():
    # Filtra parcelamentos pelo usuário atual
    return Parcelamento.query.filter(
        Parcelamento.parcelas_pagas < Parcelamento.num_parcelas,
        Parcelamento.usuario_id == current_user.id
    ).count()

@login_required
def get_faturas_db():
    # Filtra contas bancárias pelo usuário atual
    contas = ContaBancaria.query.filter_by(usuario_id=current_user.id).all()
    faturas = {conta.nome: conta.saldo for conta in contas}
    return faturas

@login_required
def get_cartoes_disponiveis_db():
    # Filtra contas bancárias pelo usuário atual
    contas = ContaBancaria.query.filter_by(usuario_id=current_user.id).order_by(ContaBancaria.nome).all()
    return [conta.nome for conta in contas]


# --- Rotas da Aplicação (AGORA USANDO current_user.id) ---

@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST':
        acao = request.form.get('acao')
        if acao == 'addGasto':
            return redirect(url_for('adicionar_gastos'))
        elif acao == 'addReserva':
            return redirect(url_for('reserva'))
        elif acao == 'parcelamentos':
            return redirect(url_for('parcelamentos'))
    
    faturas = get_faturas_db()
    gasto_mes = calcular_gasto_mes_db()
    dinheiro_guardado = calcular_dinheiro_guardado_db()
    # Filtra gastos pelo usuário atual
    movimentacoes_gastos = Gasto.query.filter_by(usuario_id=current_user.id).order_by(Gasto.id.desc()).limit(5).all() 

    todos_parcelamentos = Parcelamento.query.all()

    total_restante = 0

    valor_todas_parcelas = 0


    for p in todos_parcelamentos:
        if p.parcelas_pagas < p.num_parcelas:
            valor_todas_parcelas += p.valor_parcela

    for p in todos_parcelamentos:
        restante = (p.num_parcelas - p.parcelas_pagas) * p.valor_parcela
        total_restante += restante



    return render_template(
        'index.html',
        parcelamentos_ativos=calcular_parcelamentos_ativos_db(),
        faturas=faturas,
        gasto_mes=gasto_mes,
        dinheiro_guardado=dinheiro_guardado,
        valor_todas_parcelas=valor_todas_parcelas,
        total_restante=total_restante,
        movimentacoes_gastos=movimentacoes_gastos
    )


@app.route('/adicionar-gastos', methods=['GET', 'POST'])
@app.route('/editar-gasto/<int:gasto_id>', methods=['GET', 'POST']) 
@login_required
def adicionar_gastos(gasto_id=None):
    gasto_a_editar = None
    if gasto_id:
        # Garante que o gasto pertence ao usuário logado
        gasto_a_editar = Gasto.query.filter_by(id=gasto_id, usuario_id=current_user.id).first_or_404()
        gasto_a_editar.data_formatada_html = datetime.strptime(gasto_a_editar.data, "%d/%m/%y").strftime("%Y-%m-%d")

    data_hoje = datetime.now().strftime("%Y-%m-%d")

    if request.method == 'POST':
        acao = request.form.get('acao')
        
        if acao == 'salvarGasto':
            gasto_id_form = request.form.get('gasto_id')
            descricao = request.form.get('descricao')
            valor_str = request.form.get('valor')
            data_str = request.form.get('data')
            cartao_nome = request.form.get('cartao')

            if descricao and valor_str and data_str and cartao_nome:
                try:
                    valor = float(valor_str)
                    data_obj = datetime.strptime(data_str, "%Y-%m-%d")
                    data_formatada = data_obj.strftime("%d/%m/%y")

                    if gasto_id_form: # É uma EDIÇÃO
                        # Garante que o gasto pertence ao usuário logado
                        gasto_existente = Gasto.query.filter_by(id=int(gasto_id_form), usuario_id=current_user.id).first()
                        if not gasto_existente:
                            flash('Erro: Gasto não encontrado ou você não tem permissão para editá-lo.', 'error')
                            return redirect(url_for('adicionar_gastos'))

                        # Ajustar saldo da conta antiga (se o cartão mudou ou valor mudou)
                        if gasto_existente.cartao != cartao_nome:
                            conta_antiga = ContaBancaria.query.filter_by(nome=gasto_existente.cartao, usuario_id=current_user.id).first()
                            if conta_antiga and conta_antiga.nome not in ["Dinheiro", "Outro", "Fatura Excluída"]:
                                conta_antiga.saldo -= gasto_existente.valor
                        else: # Se o cartão não mudou, mas o valor pode ter mudado
                            conta_antiga = ContaBancaria.query.filter_by(nome=gasto_existente.cartao, usuario_id=current_user.id).first()
                            if conta_antiga and conta_antiga.nome not in ["Dinheiro", "Outro", "Fatura Excluída"]:
                                conta_antiga.saldo -= gasto_existente.valor # Remove o valor antigo para adicionar o novo

                        gasto_existente.descricao = descricao
                        gasto_existente.valor = valor
                        gasto_existente.data = data_formatada
                        gasto_existente.cartao = cartao_nome

                        # Adicionar valor ao saldo da nova conta (ou da mesma conta com novo valor)
                        conta_nova = ContaBancaria.query.filter_by(nome=cartao_nome, usuario_id=current_user.id).first()
                        if conta_nova and conta_nova.nome not in ["Dinheiro", "Outro", "Fatura Excluída"]:
                            conta_nova.saldo += valor
                        
                    else: # É uma NOVA ADIÇÃO
                        novo_gasto = Gasto(descricao=descricao, valor=valor, data=data_formatada, cartao=cartao_nome, usuario_id=current_user.id)
                        db.session.add(novo_gasto)
                        
                        # Atualiza o saldo da conta bancária (fatura) se for um cartão/conta gerenciável
                        conta = ContaBancaria.query.filter_by(nome=cartao_nome, usuario_id=current_user.id).first()
                        if conta and conta.nome not in ["Dinheiro", "Outro", "Fatura Excluída"]:
                            conta.saldo += valor
                    
                    db.session.commit()
                    flash('Gasto salvo com sucesso!', 'success')
                    return redirect(url_for('adicionar_gastos'))
                except ValueError:
                    flash('Erro: Valor inválido para o gasto.', 'error')
                    pass

        elif acao == 'adicionarCartao':
            novo_cartao_nome = request.form.get('novo_cartao_nome')
            if novo_cartao_nome:
                novo_cartao_nome_normalizado = novo_cartao_nome.strip()
                
                nomes_reservados = ["Dinheiro", "Outro", "Fatura Excluída"] 
                if novo_cartao_nome_normalizado in nomes_reservados:
                    flash(f'Erro: O nome "{novo_cartao_nome_normalizado}" é reservado e não pode ser uma fatura.', 'error')
                else:
                    # Verifica se o cartão já existe PARA ESTE USUÁRIO
                    existing_card = ContaBancaria.query.filter_by(
                        nome=novo_cartao_nome_normalizado,
                        usuario_id=current_user.id
                    ).first()
                    
                    if not existing_card:
                        nova_conta = ContaBancaria(nome=novo_cartao_nome_normalizado, saldo=0.00, usuario_id=current_user.id)
                        db.session.add(nova_conta)
                        db.session.commit()
                        flash(f'Fatura "{novo_cartao_nome_normalizado}" adicionada com sucesso!', 'success')
                    else:
                        flash(f'Erro: Fatura "{novo_cartao_nome_normalizado}" já existe para sua conta.', 'error')
            return redirect(url_for('adicionar_gastos'))

    # Filtra gastos e cartões pelo usuário atual
    gastos = Gasto.query.filter_by(usuario_id=current_user.id).order_by(Gasto.id.desc()).all()
    cartoes_disponiveis_db = get_cartoes_disponiveis_db() 
    
    faturas_gerenciaveis_obj = [
        f for f in ContaBancaria.query.filter_by(usuario_id=current_user.id).all() if f.nome not in ["Dinheiro", "Outro", "Fatura Excluída"]
    ]

    cartoes_para_dropdown = cartoes_disponiveis_db[:] 
    
    if "Dinheiro" not in cartoes_para_dropdown:
        cartoes_para_dropdown.append("Dinheiro")
    if "Outro" not in cartoes_para_dropdown:
        cartoes_para_dropdown.append("Outro")
    
    if "Fatura Excluída" in cartoes_para_dropdown:
        cartoes_para_dropdown.remove("Fatura Excluída")

    return render_template(
        'adicionar_gastos.html',
        gastos=gastos,
        cartoes=cartoes_para_dropdown, 
        data_hoje=data_hoje,
        gasto_a_editar=gasto_a_editar,
        faturas_obj=faturas_gerenciaveis_obj, 
        num_faturas_gerenciaveis_backend=len(faturas_gerenciaveis_obj) 
    )

# --- ROTAS DE EXCLUSÃO (AGORA VINCULADAS AO USUÁRIO) ---
@app.route('/excluir-gasto/<int:gasto_id>', methods=['POST'])
@login_required
def excluir_gasto(gasto_id):
    # Garante que o gasto pertence ao usuário logado
    gasto = Gasto.query.filter_by(id=gasto_id, usuario_id=current_user.id).first_or_404()
    
    conta = ContaBancaria.query.filter_by(nome=gasto.cartao, usuario_id=current_user.id).first()
    if conta and conta.nome not in ["Dinheiro", "Outro", "Fatura Excluída"]:
        conta.saldo -= gasto.valor
    
    db.session.delete(gasto)
    db.session.commit()
    flash('Gasto excluído com sucesso!', 'success')
    return redirect(url_for('adicionar_gastos'))


@app.route('/reserva', methods=['GET', 'POST'])
@login_required
def reserva():
    if request.method == 'POST':
        acao = request.form.get('acao')
        valor_str = request.form.get('valor')

        if valor_str:
            try:
                valor = float(valor_str)
                data_atual = datetime.now().strftime("%d/%m/%y")
                
                if acao == 'adicionarReserva':
                    nova_movimentacao = ReservaMovimentacao(tipo='Adição', valor=valor, data=data_atual, usuario_id=current_user.id)
                    db.session.add(nova_movimentacao)
                elif acao == 'subtrairReserva':
                    saldo_atual_reserva = calcular_dinheiro_guardado_db()
                    if saldo_atual_reserva >= valor:
                        nova_movimentacao = ReservaMovimentacao(tipo='Subtração', valor=valor, data=data_atual, usuario_id=current_user.id)
                        db.session.add(nova_movimentacao)
                    else:
                        flash('Erro: Saldo insuficiente na reserva.', 'error')
                        # Não commita se houver erro de saldo
                        return redirect(url_for('reserva')) # Redireciona para exibir a mensagem flash
                
                db.session.commit()
                flash('Movimentação da reserva realizada com sucesso!', 'success')
                return redirect(url_for('reserva'))

            except ValueError:
                flash('Erro: Valor inválido para a reserva.', 'error')
                return redirect(url_for('reserva')) # Redireciona para exibir a mensagem flash

    # Filtra movimentações de reserva pelo usuário atual
    movimentacoes = ReservaMovimentacao.query.filter_by(usuario_id=current_user.id).order_by(ReservaMovimentacao.id.desc()).all()
    dinheiro_guardado = calcular_dinheiro_guardado_db()

    return render_template(
        'reserva.html',
        dinheiro_guardado=dinheiro_guardado,
        movimentacoes=movimentacoes
    )

@app.route('/excluir-reserva-mov/<int:mov_id>', methods=['POST'])
@login_required
def excluir_reserva_mov(mov_id):
    # Garante que a movimentação pertence ao usuário logado
    mov = ReservaMovimentacao.query.filter_by(id=mov_id, usuario_id=current_user.id).first_or_404()
    
    db.session.delete(mov)
    db.session.commit()
    flash('Movimentação da reserva excluída.', 'success')
    return redirect(url_for('reserva'))


@app.route('/parcelamentos', methods=['GET', 'POST'])
@login_required
def parcelamentos():
    if request.method == 'POST':
        acao = request.form.get('acao')

        if acao == 'adicionarParcelamento':
            nome = request.form.get('nome_parcelamento')
            valor_total_str = request.form.get('valor_total')
            valor_parcela_str = request.form.get('valor_parcela')
            numero_parcelas_str = request.form.get('numero_parcelas')

            if nome and valor_total_str and valor_parcela_str and numero_parcelas_str:
                try:
                    valor_total = float(valor_total_str)
                    valor_parcela = float(valor_parcela_str)
                    numero_parcelas = int(numero_parcelas_str)

                    novo_parcelamento = Parcelamento(
                        nome=nome,
                        valor_total=valor_total,
                        valor_parcela=valor_parcela,
                        num_parcelas=numero_parcelas,
                        parcelas_pagas=0,
                        usuario_id=current_user.id # Atribui ao usuário logado
                    )
                    db.session.add(novo_parcelamento)
                    db.session.commit()
                    flash('Parcelamento adicionado com sucesso!', 'success')
                    return redirect(url_for('parcelamentos'))
                except ValueError:
                    flash('Erro: Valores inválidos para o parcelamento.', 'error')
                    pass
        
        elif acao == 'atualizarParcelasPagas':
            parcelamento_id = request.form.get('parcelamento_id')
            parcelas_pagas_str = request.form.get('parcelas_pagas')
            
            if parcelamento_id and parcelas_pagas_str:
                try:
                    p_id = int(parcelamento_id)
                    novas_pagas = int(parcelas_pagas_str)
                    # Garante que o parcelamento pertence ao usuário logado
                    parcelamento_a_atualizar = Parcelamento.query.filter_by(id=p_id, usuario_id=current_user.id).first()
                    if parcelamento_a_atualizar:
                        parcelamento_a_atualizar.parcelas_pagas = novas_pagas
                        db.session.commit()
                        return '', 204 # Retorno de sucesso sem conteúdo
                    else:
                        return 'Parcelamento não encontrado ou não pertence a você.', 403 # Forbidden
                except ValueError:
                    return 'Erro de valor.', 400

    # Filtra parcelamentos pelo usuário atual
    parcelamentos_do_db = Parcelamento.query.filter_by(usuario_id=current_user.id).all()
    return render_template('parcelamentos.html', parcelamentos=parcelamentos_do_db)

@app.route('/excluir-parcelamento/<int:parcelamento_id>', methods=['POST'])
@login_required
def excluir_parcelamento(parcelamento_id):
    # Garante que o parcelamento pertence ao usuário logado
    parcelamento = Parcelamento.query.filter_by(id=parcelamento_id, usuario_id=current_user.id).first_or_404()
    db.session.delete(parcelamento)
    db.session.commit()
    flash('Parcelamento excluído com sucesso!', 'success')
    return redirect(url_for('parcelamentos'))

@app.route('/excluir-fatura/<int:fatura_id>', methods=['POST'])
@login_required
def excluir_fatura(fatura_id):
    # Garante que a fatura pertence ao usuário logado
    fatura = ContaBancaria.query.filter_by(id=fatura_id, usuario_id=current_user.id).first_or_404()
    
    # ATENÇÃO: Gastos associados terão seu cartao alterado para "Fatura Excluída"
    # Filtra gastos pelo usuário atual E pelo nome da fatura
    gastos_associados = Gasto.query.filter_by(cartao=fatura.nome, usuario_id=current_user.id).all()
    for gasto in gastos_associados:
        gasto.cartao = "Fatura Excluída"
       

    db.session.delete(fatura)
    db.session.commit()
    flash(f'Fatura "{fatura.nome}" excluída. Gastos associados marcados como "Fatura Excluída".', 'success')
    return redirect(url_for('adicionar_gastos'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, use_reloader=False, port=9999)
    