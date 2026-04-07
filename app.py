from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import stripe
import os
import secrets

app = Flask(__name__)
import threading
import urllib.request

def keep_alive():
    while True:
        try:
            urllib.request.urlopen('https://web-production-cd6e5.up.railway.app/health')
        except:
            pass
        threading.Event().wait(300)

@app.route("/health")
def health():
    return "ok"
CORS(app)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

valid_licenses = {}

@app.route("/create-checkout", methods=["POST"])
def create_checkout():
    license_key = secrets.token_urlsafe(16)
    
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": os.environ.get("STRIPE_PRICE_ID"),
            "quantity": 1
        }],
        mode="payment",
        success_url=f"https://web-production-cd6e5.up.railway.app/success?license={license_key}",
        cancel_url="https://web-production-cd6e5.up.railway.app/cancel",
        metadata={"license_key": license_key}
    )
    
    valid_licenses[license_key] = False
    return jsonify({"url": session.url})

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ.get("STRIPE_WEBHOOK_SECRET")
        )
    except Exception:
        return jsonify({"error": "Ogiltig webhook"}), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        license_key = session["metadata"]["license_key"]
        valid_licenses[license_key] = True

    return jsonify({"status": "ok"})

@app.route("/success")
def success():
    license_key = request.args.get("license")
    if license_key in valid_licenses:
        valid_licenses[license_key] = True
    return f"""
    <html>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>Tack för ditt köp! 🪿</h1>
        <p>Din licensnyckel:</p>
        <h2 style="background: #f0f0f0; padding: 20px; border-radius: 8px;">{license_key}</h2>
        <p>Klistra in den i Goose för att aktivera.</p>
    </body>
    </html>
    """

@app.route("/cancel")
def cancel():
    return """
    <html>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1>Betalning avbruten</h1>
        <p>Du kan försöka igen när du vill.</p>
    </body>
    </html>
    """

@app.route("/privacy")
def privacy():
    return """
    <html>
    <head><title>Goose - Integritetspolicy</title></head>
    <body style="font-family: Arial; max-width: 800px; margin: 40px auto; padding: 20px;">
        <h1>Integritetspolicy för Goose</h1>
        <p>Senast uppdaterad: 6 april 2026</p>
        <h2>Vilken information samlar vi in?</h2>
        <p>Goose samlar inte in personuppgifter. Den text du analyserar skickas till Anthropics API för behandling och lagras inte av oss.</p>
        <h2>Hur använder vi informationen?</h2>
        <p>Texten du skickar in används enbart för att generera en analys via Anthropic Claude AI.</p>
        <h2>Kontakt</h2>
        <p>Frågor? Kontakta oss på: alastaircs@gmail.com</p>
    </body>
    </html>
    """

@app.route("/verify-license", methods=["POST"])
def verify_license():
    data = request.json
    license_key = data.get("licenseKey", "")
    
    if license_key in valid_licenses and valid_licenses[license_key]:
        return jsonify({"valid": True})
    return jsonify({"valid": False})

@app.route("/analyse", methods=["POST"])
def analyse():
    data = request.json
    case_text = data.get("caseText", "")
    license_key = data.get("licenseKey", "")

    # Tillfälligt gratis — ta bort detta när du vill börja ta betalt
    pass

    if not case_text:
        return jsonify({"error": "Ingen text skickades"}), 400

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": f"""Du ska analysera ett svenskt rattsfall och endast redovisa Hogsta domstolens avgörande.

Viktigt:
- Bygg endast pa det som uttryckligen framgar av texten.
- Sarskild noga mellan bakgrund, rattsfrage, HD:s motivering och prejudikatverkan.
- Ta inte med egna antaganden.
- Om information saknas eller ar osakar, skriv: "Framgar inte tydligt av texten".
- Efter varje pastand, citera det relevanta stycket fran rattsfallet inom citationstecken.

Svara med foljande rubriker och inget annat:

HD:S BESLUT
Beskriv kort vad HD kom fram till och hur malet avgjordes. Citera relevanta delar.

RATTSFRAGE
Forklara vilken rattslig huvudfraga HD provade och varfor fragan var juridiskt viktig eller svar. Citera relevanta delar.

DOMSKÄL
Beskriv steg for steg hur HD resonerade for att na sitt avgörande. Citera relevanta delar.

LEGALA PRINCIPER
Ange vilka rattregler, tolkningsprinciper eller vagledande uttalanden som HD slog fast. Citera relevanta delar.

SKILJAKTIG MENING
Ange om nagon ledamot var skiljaktig. Om ja, forklara kort och citera relevanta delar.

PREJUDIKAT
Forklara vilket vagledande varde avgörandet kan fa for framtida liknande mal.

Krav:
- Max 4 meningar per rubrik
- Max 600 ord totalt
- Enkel och tydlig svenska
- Inga punktlistor
- Ingen markdown

Text:
<rattsfall>
{case_text}
</rattsfall>"""
        }]
    )

    return jsonify({"result": message.content[0].text})

if __name__ == "__main__":
    app.run(debug=True)