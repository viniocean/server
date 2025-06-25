from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import random, string
import smtplib
from email.mime.text import MIMEText

cred = credentials.Certificate("firebase_key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)

def gerar_chave():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

def calcular_validade(plano):
    hoje = datetime.now()
    if "mensal" in plano:
        return hoje + timedelta(days=30)
    elif "semestral" in plano:
        return hoje + timedelta(days=180)
    elif "anual" in plano:
        return hoje + timedelta(days=365)
    return hoje + timedelta(days=30)

def enviar_email(destinatario, chave):
    corpo = f"""Olá!

Sua chave de licença do Marcaton é:

🔑 {chave}

Use no aplicativo para ativar sua licença.

Obrigado!
Equipe Marcaton
"""
    msg = MIMEText(corpo)
    msg['Subject'] = 'Sua chave de licença Marcaton'
    msg['From'] = "SEU_EMAIL"
    msg['To'] = destinatario

    with smtplib.SMTP_SSL('smtp.zoho.com', 465) as server:
        server.login("SEU_EMAIL", "SUA_SENHA")
        server.sendmail(msg['From'], [msg['To']], msg.as_string())

@app.route("/")
def home():
    return "Webhook Marcaton online"

@app.route("/webhook-yampi", methods=["POST"])
def webhook():
    data = request.json
    try:
        email = data["customer"]["email"]
        plano = data["cart"]["items"][0]["name"].lower()

        chave = gerar_chave()
        validade = calcular_validade(plano)

        db.collection("licenses").document(chave).set({
            "email": email,
            "plan": plano,
            "key": chave,
            "used": False,
            "created_at": firestore.SERVER_TIMESTAMP,
            "valid_until": validade
        })

        enviar_email(email, chave)

        return jsonify({"status": "ok", "key": chave}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
