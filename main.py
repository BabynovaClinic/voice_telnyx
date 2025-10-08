import telnyx
import requests
import os
import json
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, request, make_response

# Load environment
load_dotenv()

# Run flask app and set telnyx API Key
app = Flask(__name__)
telnyx.api_key = os.getenv("TELNYX_API_KEY")

# Homepage that allows user to enter a number to call
@app.route("/")
def home():
    return render_template("messageform.html")

# Endpoint that can be posted to so users can send a call
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
    except:
        print("An error occurred")
        return render_template("messagefailure.html")

# Call Control endpoint
@app.route("/call_control", methods=["POST"])
def inbound():
    body = json.loads(request.data)
    event = body.get("data").get("event_type")

    try:
        call_control_id = body.get("data").get("payload").get("call_control_id")
        call = telnyx.Call(connection_id=os.getenv("TELNYX_CONNECTION_ID"))
        call.call_control_id = call_control_id

        # Evento cuando se inicia la llamada
        if event == "call.initiated":
            call.answer()

        # Evento cuando se contesta la llamada
        elif event == "call.answered":
            # Reproducir menú inicial
            menu_text = "Hola, gracias por comunicarte con Baby Nova. Para redirigirte a un asesor presiona 1. Para terminar la llamada presiona 2. Para repetir este menú presiona 3."
            call.speak(
                payload=menu_text,
                language="es-ES",
                voice="female"
            )
            # Recolectar opción del usuario
            call.gather(
                input="dtmf",
                max_digits=1,
                timeout=10,  # 10 segundos para marcar
                event_url=os.getenv("WEBHOOK_URL") + "/call_control_gather",
                # enviamos repeat=0 para indicar que aún no se repitió
                payload=json.dumps({"repeat": 0})
            )

        # Evento cuando termina de reproducir el mensaje
        elif event == "call.speak.ended":
            # No colgamos aún, esperamos la opción del usuario
            pass

    except Exception as e:
        print("Error:", e)
        return json.dumps({"success": False}), 500, {"ContentType": "application/json"}

    return json.dumps({"success": True}), 200, {"ContentType": "application/json"}

# Endpoint para manejar la opción marcada por el usuario
@app.route("/call_control_gather", methods=["POST"])
def gather():
    body = json.loads(request.data)
    payload = body.get("data").get("payload")
    digits = payload.get("digits")
    call_control_id = payload.get("call_control_id")
    repeat_flag = payload.get("repeat", 0)  # 0 si no se ha repetido aún

    call = telnyx.Call(connection_id=os.getenv("TELNYX_CONNECTION_ID"))
    call.call_control_id = call_control_id

    menu_text = "Para redirigirte a un asesor presiona 1. Para terminar la llamada presiona 2. Para repetir este menú presiona 3."

    if digits == "1":
        call.speak(
            payload="Redirigiéndote a un asesor, por favor espera.",
            language="es-ES",
            voice="female"
        )
        # Por ahora colgamos después del mensaje
        call.hangup()
    elif digits == "2":
        call.speak(
            payload="Gracias por comunicarte. Hasta luego.",
            language="es-ES",
            voice="female"
        )
        call.hangup()
    elif digits == "3":
        # Repetir menú
        call.speak(payload=menu_text, language="es-ES", voice="female")
        call.gather(
            input="dtmf",
            max_digits=1,
            timeout=10,
            event_url=os.getenv("WEBHOOK_URL") + "/call_control_gather",
            payload=json.dumps({"repeat": 1})  # ya se repitió
        )
    else:
        # Si no marca nada
        if repeat_flag == 0:
            # Repetimos el menú una vez
            call.speak(payload=menu_text, language="es-ES", voice="female")
            call.gather(
                input="dtmf",
                max_digits=1,
                timeout=10,
                event_url=os.getenv("WEBHOOK_URL") + "/call_control_gather",
                payload=json.dumps({"repeat": 1})
            )
        else:
            # Segunda vez sin respuesta: colgar
            call.speak(
                payload="No se recibió ninguna opción. La llamada será finalizada. Hasta luego.",
                language="es-ES",
                voice="female"
            )
            call.hangup()

    return json.dumps({"success": True}), 200, {"ContentType": "application/json"}


# Main program execution
def main():
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


if __name__ == "__main__":
    main()
