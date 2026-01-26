# Projeto: Distribuidora de Peças Automotivas (Flask)

## ✨ Funcionalidades
O sistema possui dois níveis de acesso: Cliente, Administrador e Vendedor.

### Cliente
-   ✅ Cadastro e Login de usuários.
-   ✅ Visualização do catálogo completo de peças.
-   ✅ Adição e remoção de itens ao Carrinho de Compras.
-   ✅ Adição e remoção de itens à Lista de Desejos.
-   ✅ Processo de finalização de compra com preenchimento de endereço de entrega.

### Vendedor
-   ✅ Painel Exclusivo: Visualização de pedidos pendentes de pagamento.
-   ✅ Privacidade: Visualiza o cliente e os itens, mas não possui acesso aos valores financeiros do pedido.
-   ✅ Fluxo de Caixa: Confirma o pagamento do pedido.
-   ✅ Automação: Ao confirmar o pagamento, o sistema automaticamente subtrai os itens do estoque e altera o status para Pago.

### Administrador
-   ✅ Acesso a um painel de controle (Dashboard) exclusivo.
-   ✅ Cadastro de novas peças ao catálogo, incluindo nome, descrição, preço, estoque e URL da imagem.
-   ✅ Visualização de todos os pedidos realizados pelos clientes.
-   ✅ Acesso aos detalhes de cada pedido, incluindo itens e endereço de entrega.
-   ✅ Alteração do status de um pedido (Ex: Processando, Enviado, Entregue, Cancelado).

### Regras de Negócio (Lógica de Usuários)
-   1. O Primeiro é o Dono: O código está programado para verificar se o banco está vazio. O primeiríssimo usuário a se registrar recebe a role admin.
-   2. Novos Registros: Todos os usuários que se registrarem após o primeiro serão criados automaticamente como cliente.
-   3. Criação do Vendedor: Por questões de segurança, a role vendedor não pode ser obtida via formulário. Para criar um vendedor:

- Registre um novo usuário normalmente.
- Acesse o banco de dados (phpMyAdmin).
- Na tabela Usuario, altere o campo role de cliente para vendedor.

## Tecnologias Utilizadas
-   **Back-end:** Python 3
-   **Framework:** Flask
-   **Banco de Dados:** MySQL
-   **ORM:** Flask-SQLAlchemy
-   **Autenticação:** Flask-Login
-   **Segurança:** Flask-Bcrypt (para hashing de senhas)
-   **Front-end:** HTML5, CSS3 com Bootstrap 5 via CDN

## Como Executar o Projeto

**1. Clone o Repositório**
```
git clone https://github.com/RafaelAnanias/projetoDistribuidora.git
cd distribuidora-flask
```
**2. Crie e Ative o Ambiente Virtual**

# Criar o ambiente virtual
python -m venv venv

# Ativar o ambiente virtual no Windows
.\venv\Scripts\activate


**3. Instale as Dependências**
Todas as bibliotecas necessárias estão listadas no arquivo `requirements.txt`.

pip install -r requirements.txt


**4. Configure o Banco de Dados**
-   Inicie os módulos **Apache** e **MySQL** no painel de controle do XAMPP.
-   Acesse `http://localhost/phpmyadmin` e crie um novo banco de dados.
-   **Execute o seguinte comando SQL:**

    ```sql
    CREATE DATABASE distribuidora_db
    ```

**5. Configure as Variáveis de Ambiente**
-   Na raiz do projeto, crie um arquivo `.env`.
-   Abra o arquivo `.env` e preencha com as suas credenciais do banco de dados.
    ```
    DB_USER="root"
    DB_PASSWORD=""  # Deixe em branco se seu XAMPP não tiver senha
    DB_HOST="localhost"
    DB_NAME="distribuidora_db"
    SECRET_KEY="chaveSecreta"
    ```

**6. Crie as Tabelas no Banco de Dados**
Este comando irá ler os modelos da aplicação e criar todas as tabelas necessárias.
```bash
# Inicie o shell interativo do Flask
flask shell

# Dentro do shell (>>>), execute os comandos:
from app import db
db.create_all()
exit()
```

**8. Execute a Aplicação**
Finalmente, inicie o servidor de desenvolvimento do Flask.

Para inicar é necessário apenas rodar esse comando: python run.py