import os
import json
from dotenv import load_dotenv
from flask import Flask, request, jsonify

load_dotenv()
app = Flask(__name__)

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise Exception("WEBHOOK_URL no definido en .env")

MENU_TEXT = (
    "Hola, gracias por comunicarte con Baby Nova. "
    "Para redirigirte a un asesor presiona 1. "
    "Para terminar la llamada presiona 2. "
    "Para repetir este menú presiona 3."
)

@app.route("/")
def home():
    return "Telnyx Call Control Home"

@app.route("/outbound", methods=["POST"])
def outbound():
    import telnyx
    telnyx.api_key = os.getenv("TELNYX_API_KEY")

    number = request.form.get("to_number")
    try:
        telnyx.Call.create(
            connection_id=os.getenv("TELNYX_CONNECTION_ID"),
            to=number,
            from_=os.getenv("TELNYX_NUMBER")
        )
        return "Call initiated"
    except Exception as e:
        print("Error outbound:", e)
        return "Call failed"

@app.route("/call_control", methods=["POST"])
def call_control():
    body = request.json
    event = body.get("data", {}).get("event_type")
    payload = body.get("data", {}).get("payload", {})
    repeat_flag = payload.get("repeat", 0)

    response_commands = []

    if event == "call.answered":
        # Primer menú
        response_commands.append({
            "type": "speak",
            "payload": MENU_TEXT,
            "voice": "female",
            "language": "es-ES"
        })
        response_commands.append({
            "type": "gather",
            "input": "dtmf",
            "max_digits": 1,
            "timeout": 10,
            "event_url": f"{WEBHOOK_URL}/call_control_gather",
            "payload": json.dumps({"repeat": repeat_flag})
        })

    return jsonify({"commands": response_commands})

@app.route("/call_control_gather", methods=["POST"])
def call_control_gather():
    body = request.json
    payload = body.get("data", {}).get("payload", {})
    digits = payload.get("digits")
    repeat_flag = payload.get("repeat", 0)

    commands = []

    if digits == "1":
        commands.append({
            "type": "speak",
            "payload": "Redirigiéndote a un asesor, por favor espera.",
            "voice": "female",
            "language": "es-ES"
        })
        commands.append({"type": "hangup"})

    elif digits == "2":
        commands.append({
            "type": "speak",
            "payload": "Gracias por comunicarte. Hasta luego.",
            "voice": "female",
            "language": "es-ES"
        })
        commands.append({"type": "hangup"})

    elif digits == "3" and repeat_flag == 0:
        # Repetir menú solo una vez
        commands.append({
            "type": "speak",
            "payload": MENU_TEXT,
            "voice": "female",
            "language": "es-ES"
        })
        commands.append({
            "type": "gather",
            "input": "dtmf",
            "max_digits": 1,
            "timeout": 10,
            "event_url": f"{WEBHOOK_URL}/call_control_gather",
            "payload": json.dumps({"repeat": 1})
        })

    else:
        # Timeout o opción inválida
        if repeat_flag == 0:
            # Repetir menú una vez
            commands.append({
                "type": "speak",
                "payload": MENU_TEXT,
                "voice": "female",
                "language": "es-ES"
            })
            commands.append({
                "type": "gather",
                "input": "dtmf",
                "max_digits": 1,
                "timeout": 10,
                "event_url": f"{WEBHOOK_URL}/call_control_gather",
                "payload": json.dumps({"repeat": 1})
            })
        else:
            # Segunda vez sin respuesta o inválida: colgar
            commands.append({
                "type": "speak",
                "payload": "No se recibió ninguna opción. La llamada será finalizada. Hasta luego.",
                "voice": "female",
                "language": "es-ES"
            })
            commands.append({"type": "hangup"})

    return jsonify({"commands": commands})

def main():
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

if __name__ == "__main__":
    main()
