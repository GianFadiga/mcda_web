import sqlite3

# Caminho para o banco de dados SQLite
DB_PATH = "db.sqlite3"
DUMP_FILE = "banco_dump.sql"

def gerar_dump_sqlite(db_path, dump_file):
    # Conectar ao banco de dados SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Abrir o arquivo para escrita
    with open(dump_file, "w", encoding="utf-8") as f:
        # Usar .dump para gerar a estrutura e os dados do banco
        for line in conn.iterdump():
            f.write(f"{line}\n")

    print(f"✅ Dump do banco gerado com sucesso: {dump_file}")
    conn.close()

if __name__ == "__main__":
    gerar_dump_sqlite(DB_PATH, DUMP_FILE)
