from flask import Flask, request, jsonify
from nlp_service import analyze_activity_text
import os

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    text = data.get('text', '')
    
    print(f"DEBUG: AI Service received text: {text}")
    
    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        result = analyze_activity_text(text)
        return jsonify(result)
    except Exception as e:
        print(f"AI Service Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run on port 5000 inside the container
    app.run(host='0.0.0.0', port=5000)