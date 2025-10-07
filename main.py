import telnyx
import requests
import os
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request

# ==========================================================
# Cargar variables de entorno (.env)
# ==========================================================
load_dotenv()

# ==========================================================
# Configurar Flask y la API de Telnyx
# ==========================================================
app = Flask(__name__)
telnyx.api_key = os.getenv("TELNYX_API_KEY")

print("✅ Telnyx API Key cargada:", telnyx.api_key[:10] + "..." if telnyx.api_key else "❌ NO CARGADA")
print("✅ Connection ID:", os.getenv("TELNYX_CONNECTION_ID"))
print("✅ Telnyx Number:", os.getenv("TELNYX_NUMBER"))
print("✅ App Port:", os.getenv("TELNYX_APP_PORT"))

# ==========================================================
# Página principal (formulario)
# ==========================================================
@app.route("/")
def home():
    return render_template("messageform.html")


# ==========================================================
# Ruta para llamadas salientes
# ==========================================================
@app.route("/outbound", methods=["POST"])
def outbound():
    number = request.form["to_number"].strip()

    try:
        print("\n📞 Intentando realizar llamada saliente...")
        print(f"   → A: {number}")
        print(f"   → Desde: {os.getenv('TELNYX_NUMBER')}")
        print(f"   → Connection ID: {os.getenv('TELNYX_CONNECTION_ID')}")

        call = telnyx.Call.create(
            connection_id=os.getenv("TELNYX_CONNECTION_ID"),
            to=number,
            from_=os.getenv("TELNYX_NUMBER")
        )

        print("✅ Llamada creada correctamente:", call)
        return render_template("messagesuccess.html")

    except Exception as e:
        print("❌ Telnyx API error:", str(e))
        print("⚠️ Verifica tu .env (API Key, número y Connection ID asignados correctamente).")
        return render_template("messagefailure.html")


# ==========================================================
# Ruta para manejar llamadas entrantes (Call Control)
# ==========================================================
@app.route("/call_control", methods=["POST"])
def inbound():
    try:
        body = json.loads(request.data)
        event = body.get("data", {}).get("event_type")
        payload = body.get("data", {}).get("payload", {})
        call_control_id = payload.get("call_control_id")

        print(f"📲 Evento recibido: {event}")

        if event == "call.initiated":
            call = telnyx.Call(connection_id=os.getenv("TELNYX_CONNECTION_ID"))
            call.call_control_id = call_control_id
            call.answer()

        elif event == "call.answered":
            call = telnyx.Call(connection_id=os.getenv("TELNYX_CONNECTION_ID"))
            call.call_control_id = call_control_id
            call.speak(
                payload="Hello, Telnyx user! Welcome to this call control demonstration.",
                language="en-US",
                voice="female"
            )

        elif event == "call.speak.ended":
            call = telnyx.Call(connection_id=os.getenv("TELNYX_CONNECTION_ID"))
            call.call_control_id = call_control_id
            call.hangup()

        return json.dumps({"success": True}), 200, {"ContentType": "application/json"}

    except Exception as e:
        print("❌ Error manejando evento entrante:", str(e))
        return json.dumps({"success": False}), 500, {"ContentType": "application/json"}


# ==========================================================
# Ejecución principal
# ==========================================================
def main():
    port = int(os.getenv("TELNYX_APP_PORT", 5000))
    print(f"\n🚀 Servidor Flask ejecutándose en http://127.0.0.1:{port}")
    app.run(port=port, debug=True)


if __name__ == "__main__":
    main()
