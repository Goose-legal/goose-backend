from flask import Flask, request, jsonify
from flask_cors import CORS
from docx import Document as DocxDocument
from io import BytesIO
from datetime import datetime
import anthropic
import os

app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

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
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": f"""Du ska analysera ett svenskt rattsfall och endast redovisa Hogsta domstolens avgörande.

Viktigt:
- Bygg endast pa det som uttryckligen framgar av texten.
- Sarskild noga mellan bakgrund, rattsfrage, HD:s motivering och prejudikatverkan.
- Ta inte med egna antaganden.
- Om information saknas eller ar osakar, skriv: Framgår inte tydligt av texten.
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
- Max 2 mening per rubrik
- Max 400 ord totalt
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


@app.route("/download", methods=["POST"])
def download():
    data = request.json
    analysis = data.get("analysis", "")

    doc = DocxDocument()

    title = doc.add_heading("Goose - Rattsfall Analys", 0)
    title.alignment = 1

    doc.add_paragraph(f"Genererad: {datetime.now().strftime('%d %B %Y, %H:%M')}")
    doc.add_paragraph("")

    headings = ["HD:S BESLUT", "RÄTTSFRAGA", "DOMSKÄL", "LEGALA PRINCIPER", "SKILJAKTIG MENING", "PREJUDIKAT"]

    lines = analysis.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if any(line.startswith(h) for h in headings):
            doc.add_heading(line, level=2)
        else:
            doc.add_paragraph(line)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return app.response_class(
        buffer.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        headers={'Content-Disposition': 'attachment; filename=goose-analys.docx'}
    )


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