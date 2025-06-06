import os
import django
from django.db import connection

# Configura o Django manualmente
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mcda_project.settings")
django.setup()

def inspect_database(output_file="database_structure.txt"):
    with connection.cursor() as cursor, open(output_file, "w", encoding="utf-8") as f:
        tables = connection.introspection.table_names()
        f.write("\n📄 Database Tables and Fields:\n\n")

        for table in tables:
            f.write(f"🔹 Table: {table}\n")
            cursor.execute(f"PRAGMA table_info('{table}')")
            columns = cursor.fetchall()
            for column in columns:
                col_id, name, col_type, notnull, default, pk = column
                pk_text = "PRIMARY KEY" if pk else ""
                f.write(f"    • {name} ({col_type}) {pk_text}\n")
            f.write("-" * 40 + "\n")

        # Triggers
        f.write("\n🔧 Triggers:\n\n")
        cursor.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type = 'trigger'")
        triggers = cursor.fetchall()
        for name, tbl_name, sql in triggers:
            f.write(f"🔸 Trigger: {name} on Table: {tbl_name}\n")
            f.write(f"{sql}\n")
            f.write("-" * 40 + "\n")

if __name__ == "__main__":
    inspect_database()
