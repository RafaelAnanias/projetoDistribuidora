from app import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Descomente a linha abaixo na primeira vez que executar para criar as tabelas
        # db.create_all()
        print("Tabelas do banco de dados criadas (se não existirem).")
    app.run(debug=True)