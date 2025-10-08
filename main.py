import telnyx
import os
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request

load_dotenv()
app = Flask(__name__)
telnyx.api_key = os.getenv("TELNYX_API_KEY")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise Exception("WEBHOOK_URL no definido en .env")

@app.route("/")
def home():
    return render_template("messageform.html")

@app.route("/outbound", methods=["POST"])
def outbound():
    number = request.form["to_number"]
    try:
        telnyx.Call.create(
            connection_id=os.getenv("TELNYX_CONNECTION_ID"),
            to=number,
            from_=os.getenv("TELNYX_NUMBER")
        )
        return render_template("messagesuccess.html")
    except Exception as e:
        print("Error outbound:", e)
        return render_template("messagefailure.html")

@app.route("/call_control", methods=["POST"])
def inbound():
    body = json.loads(request.data)
    event = body.get("data", {}).get("event_type")

    try:
        call_control_id = body.get("data", {}).get("payload", {}).get("call_control_id")
        call = telnyx.Call(connection_id=os.getenv("TELNYX_CONNECTION_ID"))
        call.call_control_id = call_control_id

        # Quitar call.answer() en llamadas outbound
        if event == "call.answered":
            menu_text = "Hola, gracias por comunicarte con Baby Nova. Para redirigirte a un asesor presiona 1. Para terminar la llamada presiona 2. Para repetir este menú presiona 3."
            call.speak(payload=menu_text, language="es-ES", voice="female")
            call.gather(
                input="dtmf",
                max_digits=1,
                timeout=10,
                event_url=f"{WEBHOOK_URL}/call_control_gather",
                payload=json.dumps({"repeat": 0})
            )

    except Exception as e:
        print("Error call_control:", e)
        return json.dumps({"success": False}), 500, {"ContentType": "application/json"}

    return json.dumps({"success": True}), 200, {"ContentType": "application/json"}

@app.route("/call_control_gather", methods=["POST"])
def gather():
    body = json.loads(request.data)
    payload = body.get("data", {}).get("payload", {})
    digits = payload.get("digits")
    call_control_id = payload.get("call_control_id")
    repeat_flag = payload.get("repeat", 0)

    call = telnyx.Call(connection_id=os.getenv("TELNYX_CONNECTION_ID"))
    call.call_control_id = call_control_id

    menu_text = "Para redirigirte a un asesor presiona 1. Para terminar la llamada presiona 2. Para repetir este menú presiona 3."

    if digits == "1":
        call.speak(payload="Redirigiéndote a un asesor, por favor espera.", language="es-ES", voice="female")
        call.hangup()  # por ahora colgamos
    elif digits == "2":
        call.speak(payload="Gracias por comunicarte. Hasta luego.", language="es-ES", voice="female")
        call.hangup()
    elif digits == "3" and repeat_flag == 0:
        call.speak(payload=menu_text, language="es-ES", voice="female")
        call.gather(
            input="dtmf",
            max_digits=1,
            timeout=10,
            event_url=f"{WEBHOOK_URL}/call_control_gather",
            payload=json.dumps({"repeat": 1})
        )
    else:
        # Si no marca nada o opción inválida
        if repeat_flag == 0:
            call.speak(payload=menu_text, language="es-ES", voice="female")
            call.gather(
                input="dtmf",
                max_digits=1,
                timeout=10,
                event_url=f"{WEBHOOK_URL}/call_control_gather",
                payload=json.dumps({"repeat": 1})
            )
        else:
            call.speak(payload="No se recibió ninguna opción. La llamada será finalizada. Hasta luego.", language="es-ES", voice="female")
            call.hangup()

    return json.dumps({"success": True}), 200, {"ContentType": "application/json"}

def main():
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

if __name__ == "__main__":
    main()
