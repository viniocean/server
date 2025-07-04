from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import random, string
import smtplib
from email.mime.text import MIMEText
import traceback
import os

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
    print("Recebido webhook:", data)  # DEBUG para ver o payload no log
    try:
        resource = data.get("resource", {})
        customer_data = resource.get("customer", {}).get("data", {})
        items_data = resource.get("items", {}).get("data", [])

        email = customer_data.get("email")
        if not email:
            raise ValueError("Email do cliente não encontrado no payload")

        if not items_data:
            raise ValueError("Itens do pedido não encontrados no payload")

        primeiro_item = items_data[0]
        sku_data = primeiro_item.get("sku", {}).get("data", {})
        plano = sku_data.get("title", "").lower()

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

        enviar_email(email, chave)  # Comente esta linha se quiser testar sem enviar email

        return jsonify({"status": "ok", "key": chave}), 200
    except Exception as e:
        print("❌ Erro durante o webhook:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
