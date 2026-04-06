from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import os

app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

@app.route("/analyse", methods=["POST"])
def analyse():
    data = request.json
    case_text = data.get("caseText", "")

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