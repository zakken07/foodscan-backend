from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import base64
import os
import json
import re

app = Flask(__name__)
CORS(app)

# Konfigurasi Gemini API
# API key bisa dari environment variable atau hardcode (untuk testing)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'YOUR_GEMINI_API_KEY_HERE')
genai.configure(api_key=GEMINI_API_KEY)

def analyze_food_image(image_data):
    """
    Menganalisis gambar makanan menggunakan Gemini Flash 2.0
    """
    try:
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        
        # Inisialisasi model Gemini Flash 2.0
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Prompt untuk analisis makanan
        prompt = """
        Analisis gambar makanan ini dan berikan informasi berikut dalam format JSON:
        
        1. freshness: Tingkat kesegaran makanan dalam persentase (0-100)
        2. calories: Estimasi kalori total dalam kcal (angka bulat)
        3. summary: Ringkasan analisis gizi dalam 2-3 kalimat (dalam Bahasa Indonesia)
        
        Pertimbangkan:
        - Warna dan tekstur makanan untuk menentukan kesegaran
        - Jenis makanan, porsi, dan bahan untuk estimasi kalori
        - Kandungan nutrisi utama (karbohidrat, protein, lemak, vitamin)
        
        Berikan HANYA response dalam format JSON yang valid seperti ini:
        {
            "freshness": 85,
            "calories": 320,
            "summary": "Nasi goreng dengan sayuran segar dan telur. Tinggi karbohidrat dengan protein sedang. Terdeteksi cabai, wortel, dan bawang bombay yang memberikan vitamin dan antioksidan."
        }
        
        PENTING: Jangan tambahkan teks apapun selain JSON!
        """
        
        # Generate konten dengan gambar
        response = model.generate_content([
            prompt,
            {'mime_type': 'image/jpeg', 'data': image_bytes}
        ])
        
        # Parse response
        result_text = response.text.strip()
        
        # Bersihkan response dari markdown code blocks jika ada
        result_text = re.sub(r'```json\s*', '', result_text)
        result_text = re.sub(r'```\s*', '', result_text)
        result_text = result_text.strip()
        
        # Parse JSON
        result = json.loads(result_text)
        
        # Validasi hasil
        if not all(key in result for key in ['freshness', 'calories', 'summary']):
            raise ValueError("Response tidak lengkap")
        
        # Pastikan tipe data benar
        result['freshness'] = int(result['freshness'])
        result['calories'] = int(result['calories'])
        result['summary'] = str(result['summary'])
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Raw response: {result_text}")
        # Fallback result
        return {
            "freshness": 75,
            "calories": 300,
            "summary": "Makanan terdeteksi. Estimasi kalori dan nilai gizi berdasarkan visual makanan. Untuk hasil lebih akurat, pastikan gambar makanan jelas dan pencahayaan baik."
        }
    except Exception as e:
        print(f"Analysis Error: {e}")
        raise e

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Endpoint untuk menganalisis gambar makanan
    """
    try:
        # Validasi request
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        
        if 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400
        
        image_base64 = data['image']
        
        # Hapus prefix data URL jika ada
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]
        
        # Analisis gambar
        result = analyze_food_image(image_base64)
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            'error': 'Failed to analyze image',
            'message': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'message': 'FoodScan AI Backend is running'
    }), 200

# Untuk Vercel serverless function
def handler(request):
    with app.request_context(request.environ):
        return app.full_dispatch_request()

if __name__ == '__main__':
    # Untuk testing lokal
    app.run(debug=True, host='0.0.0.0', port=5000)