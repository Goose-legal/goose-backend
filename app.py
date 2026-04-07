from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import stripe
import os
import secrets


app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

valid_licenses = {}

@app.route("/health")
def health():
    return "ok"

@app.route("/analyse", methods=["POST"])
def analyse():
    data = request.json
    case_text = data.get("caseText", "")

    if not case_text:
        return jsonify({"error": "Ingen text skickades"}), 400

    def generate():
        with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{
                "role": "user",
                "content": f"""Du ska analysera ett svenskt rattsfall och endast redovisa Hogsta domstolens avgörande.

Viktigt:
- Bygg endast pa det som uttryckligen framgar av texten.
- Sarskild noga mellan bakgrund, rattsfrage, HD:s motivering och prejudikatverkan.
- Ta inte med egna antaganden.
- Om information saknas eller ar osakar, skriv: Framgar inte tydligt av texten.
- Efter varje pastand, citera det relevanta stycket fran rattsfallet inom citationstecken.

Svara med foljande rubriker och inget annat:

HD:S BESLUT
Beskriv kort vad HD kom fram till och hur malet avgjordes.

RÄTTSFRAGA
Forklara vilken rattslig huvudfraga HD provade och varfor fragan var juridiskt viktig.

DOMSKÄL
Beskriv steg for steg hur HD resonerade for att na sitt avgörande.

LEGALA PRINCIPER
Ange vilka rattregler eller principer som HD slog fast.

SKILJAKTIG MENING
Ange om nagon ledamot var skiljaktig och vad de ansag.

PREJUDIKAT
Forklara vilket vagledande varde avgörandet kan fa.

Krav:
- Max 1 mening per rubrik
- Max 200 ord totalt
- Enkel och tydlig svenska
- Inga punktlistor
- Ingen markdown

Text:
<rattsfall>
{case_text}
</rattsfall>"""
            }]
        ) as stream:
            for text in stream.text_stream:
                yield text

    return app.response_class(generate(), mimetype='text/plain')

@app.route("/success")
def success():
    license_key = request.args.get("license")
    if license_key in valid_licenses:
        valid_licenses[license_key] = True
    return f"""
    <html>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>Tack for ditt kop!</h1>
        <p>Din licensnyckel:</p>
        <h2 style="background: #f0f0f0; padding: 20px; border-radius: 8px;">{license_key}</h2>
        <p>Klistra in den i Goose for att aktivera.</p>
    </body>
    </html>
    """

@app.route("/cancel")
def cancel():
    return """
    <html>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>Betalning avbruten</h1>
        <p>Du kan forsoka igen nar du vill.</p>
    </body>
    </html>
    """

@app.route("/privacy")
def privacy():
    return """
    <html>
    <head><title>Goose - Integritetspolicy</title></head>
    <body style="font-family: Arial; max-width: 800px; margin: 40px auto; padding: 20px;">
        <h1>Integritetspolicy for Goose</h1>
        <p>Senast uppdaterad: 6 april 2026</p>
        <h2>Vilken information samlar vi in?</h2>
        <p>Goose samlar inte in personuppgifter. Den text du analyserar skickas till Anthropics API for behandling och lagras inte av oss.</p>
        <h2>Hur anvander vi informationen?</h2>
        <p>Texten du skickar in anvands enbart for att generera en analys via Anthropic Claude AI.</p>
        <h2>Kontakt</h2>
        <p>Fragor? Kontakta oss pa: alastaircs@gmail.com</p>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)