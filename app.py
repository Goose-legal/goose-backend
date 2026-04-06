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

    if license_key not in valid_licenses or not valid_licenses[license_key]:
        return jsonify({"error": "Ogiltig licensnyckel"}), 403

    if not case_text:
        return jsonify({"error": "Ingen text skickades"}), 400

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": f"""Du ska analysera ett svenskt rättsfall och endast redovisa Högsta domstolens avgörande.

Viktigt:
- Bygg endast på det som uttryckligen framgår av texten.
- Särskilj noga mellan bakgrund, rättsfråga, HD:s motivering och prejudikatverkan.
- Ta inte med egna antaganden.
- Om information saknas eller är osäker, skriv: "Framgår inte tydligt av texten".

Svara med följande rubriker och inget annat:

HD:S BESLUT
Beskriv kort vad HD kom fram till och hur målet avgjordes.

RÄTTSFRÅGA
Förklara vilken rättslig huvudfråga HD prövade och varför frågan var juridiskt viktig eller svår.

DOMSKÄL
Beskriv steg för steg hur HD resonerade för att nå sitt avgörande. Fokusera på argumentkedjan.

LEGALA PRINCIPER
Ange vilka rättsregler, tolkningsprinciper eller vägledande uttalanden som HD slog fast eller förtydligade.

SKILJAKTIG MENING
Ange om någon ledamot var skiljaktig. Om ja, förklara kort vad den skiljaktiga meningen gick ut på.

PREJUDIKAT
Förklara vilket vägledande värde avgörandet kan få för framtida liknande mål.

Krav:
- Max 4 meningar per rubrik
- Max 500 ord totalt
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