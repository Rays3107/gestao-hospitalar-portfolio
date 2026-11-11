from flask import Flask, jsonify, request, send_from_directory
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "database" / "gestao.db"
FRONT = ROOT / "frontend"

app = Flask(__name__)

def conectar():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def iniciar_banco():
    DB.parent.mkdir(exist_ok=True)
    with conectar() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS orcamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE NOT NULL,
                paciente TEXT NOT NULL,
                procedimento TEXT NOT NULL,
                valor REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pendente',
                data TEXT NOT NULL DEFAULT CURRENT_DATE
            )
        """)

@app.get("/")
def inicio():
    return send_from_directory(FRONT, "index.html")

@app.get("/api/orcamentos")
def listar():
    with conectar() as con:
        dados = con.execute(
            "SELECT * FROM orcamentos ORDER BY id DESC"
        ).fetchall()
    return jsonify([dict(x) for x in dados])

@app.post("/api/orcamentos")
def cadastrar():
    dados = request.get_json(silent=True) or {}
    campos = ["numero", "paciente", "procedimento", "valor"]
    if any(not str(dados.get(c, "")).strip() for c in campos):
        return jsonify({"erro": "Preencha todos os campos."}), 400
    try:
        valor = float(dados["valor"])
        if valor <= 0:
            raise ValueError()
        with conectar() as con:
            con.execute("""
                INSERT INTO orcamentos
                (numero, paciente, procedimento, valor)
                VALUES (?, ?, ?, ?)
            """, (
                dados["numero"].strip(),
                dados["paciente"].strip(),
                dados["procedimento"].strip(),
                valor
            ))
        return jsonify({"mensagem": "Orçamento cadastrado."}), 201
    except ValueError:
        return jsonify({"erro": "Valor inválido."}), 400
    except sqlite3.IntegrityError:
        return jsonify({"erro": "Número de orçamento já cadastrado."}), 409

@app.patch("/api/orcamentos/<int:identificador>")
def atualizar_status(identificador):
    dados = request.get_json(silent=True) or {}
    status = dados.get("status")
    permitidos = ["Pendente", "Aprovado", "Recusado"]
    if status not in permitidos:
        return jsonify({"erro": "Status inválido."}), 400
    with conectar() as con:
        cursor = con.execute(
            "UPDATE orcamentos SET status=? WHERE id=?",
            (status, identificador)
        )
    if cursor.rowcount == 0:
        return jsonify({"erro": "Orçamento não encontrado."}), 404
    return jsonify({"mensagem": "Status atualizado."})

@app.get("/api/resumo")
def resumo():
    with conectar() as con:
        total = con.execute(
            "SELECT COUNT(*) FROM orcamentos"
        ).fetchone()[0]
        valor = con.execute(
            "SELECT COALESCE(SUM(valor),0) FROM orcamentos"
        ).fetchone()[0]
        status = con.execute("""
            SELECT status, COUNT(*) AS quantidade
            FROM orcamentos GROUP BY status
        """).fetchall()
    return jsonify({
        "total": total,
        "valor_total": valor,
        "status": [dict(x) for x in status]
    })

if __name__ == "__main__":
    iniciar_banco()
    app.run(host="127.0.0.1", port=5000, debug=True)
