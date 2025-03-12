from flask import Flask, request, jsonify
import pdfplumber
import pandas as pd
import io
import os
import tempfile
from werkzeug.utils import secure_filename
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Umożliwia zapytania CORS z frontendu

# Uniwersalne mapowanie terminów dla różnych języków
language_mappings = {
    'uk': {  # Amazon UK (English)
        'income': ['Income', 'income', 'Sales', 'Revenue'],
        'expenses': ['Expenses', 'expenses', 'Costs', 'Fees'],
        'tax': ['Tax', 'tax', 'VAT']
    },
    'de': {  # Amazon DE (German)
        'income': ['Einnahmen', 'Umsätze', 'Einnahmen und Erstattungen'],
        'expenses': ['Ausgaben', 'Gebühren', 'Kosten'],
        'tax': ['Steuer', 'MwSt', 'Mehrwertsteuer']
    },
    'es': {  # Amazon ES (Spanish)
        'income': ['Ingresos', 'Ventas', 'Ingresos y reembolsos'],
        'expenses': ['Gastos', 'Tarifas', 'Costes'],
        'tax': ['Impuesto', 'IVA']
    },
    'fr': {  # Amazon FR (French)
        'income': ['Revenus', 'Ventes', 'Chiffre d\'affaires'],
        'expenses': ['Dépenses', 'Frais', 'Coûts'],
        'tax': ['Taxe', 'TVA', 'Impôt']
    },
    'nl': {  # Amazon NL (Dutch)
        'income': ['Inkomsten', 'Verkoop', 'Omzet'],
        'expenses': ['Uitgaven', 'Kosten', 'Vergoedingen'],
        'tax': ['Belasting', 'BTW']
    },
    'it': {  # Amazon IT (Italian)
        'income': ['Entrate', 'Vendite', 'Ricavi'],
        'expenses': ['Spese', 'Costi', 'Commissioni'],
        'tax': ['Tassa', 'IVA', 'Imposta']
    },
    'usa': {  # Amazon USA (English)
        'income': ['Income', 'Sales', 'Revenue'],
        'expenses': ['Expenses', 'Costs', 'Fees'],
        'tax': ['Tax', 'Sales tax']
    }
}

# Waluty dla poszczególnych platform
currency_mapping = {
    'uk': 'GBP',
    'de': 'EUR',
    'es': 'EUR',
    'fr': 'EUR',
    'nl': 'EUR',
    'it': 'EUR',
    'usa': 'USD',
    'ebay': 'GBP',
    'etsy': 'GBP',
    'bandq': 'GBP'
}

def extract_financial_data_from_pdf(file_path, platform):
    """Ekstrakcja danych finansowych z pliku PDF z uwzględnieniem różnych języków."""
    financial_data = {
        'Income': 0,
        'Expenses': 0,
        'Tax': 0
    }
    
    tax_data = {
        'Income': 0,
        'Expenses': 0
    }
    
    # Pobierz mapowanie języka dla wybranej platformy
    language_map = language_mappings.get(platform, language_mappings['uk'])
    
    try:
        # Otwieranie pliku PDF
        with pdfplumber.open(file_path) as pdf:
            text = ""
            # Łączenie tekstu ze wszystkich stron
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            
            # Szukanie wartości dla Income, Expenses i Tax
            lines = text.split('\n')
            
            # 1. Próbujemy znaleźć wartości w podsumowaniu (zwykle na początku lub końcu)
            for line in lines:
                # Szukamy Income
                for income_term in language_map['income']:
                    if income_term in line:
                        # Spróbuj wyodrębnić kwotę (zakładając format liczb z kropką dziesiętną)
                        numbers = [float(s.replace(',', '')) for s in line.split() if s.replace(',', '').replace('.', '').replace('-', '').isdigit()]
                        if numbers:
                            financial_data['Income'] = numbers[0]
                
                # Szukamy Expenses
                for expenses_term in language_map['expenses']:
                    if expenses_term in line:
                        numbers = [float(s.replace(',', '')) for s in line.split() if s.replace(',', '').replace('.', '').replace('-', '').isdigit()]
                        if numbers:
                            # Expenses zwykle są ujemne, jeśli nie są, dodajemy minus
                            expenses_value = numbers[0]
                            if expenses_value > 0:
                                expenses_value = -expenses_value
                            financial_data['Expenses'] = expenses_value
                
                # Szukamy Tax
                for tax_term in language_map['tax']:
                    if tax_term in line and not any(exp_term in line for exp_term in language_map['expenses']):
                        numbers = [float(s.replace(',', '')) for s in line.split() if s.replace(',', '').replace('.', '').replace('-', '').isdigit()]
                        if numbers:
                            tax_data['Income'] = numbers[0]
            
            # 2. Jeśli nie znaleziono, szukamy w całej treści
            if financial_data['Income'] == 0:
                # Poszukiwanie bardziej zaawansowane
                pass  # Tutaj można dodać bardziej złożoną logikę
    
    except Exception as e:
        print(f"Błąd podczas przetwarzania PDF: {e}")
        return None, None
    
    return financial_data, tax_data

def process_excel_file(file_path, platform):
    """Ekstrakcja danych finansowych z pliku Excel."""
    try:
        df = pd.read_excel(file_path)
        
        # Tutaj logika przetwarzania Excela
        # ...
        
        # Przykładowy wynik
        financial_data = {
            'Income': 0,
            'Expenses': 0
        }
        tax_data = {
            'Income': 0,
            'Expenses': 0
        }
        
        return financial_data, tax_data
    except Exception as e:
        print(f"Błąd podczas przetwarzania Excel: {e}")
        return None, None

@app.route('/api/process-file', methods=['POST'])
def process_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Brak pliku'}), 400
    
    file = request.files['file']
    platform = request.form.get('platform', 'uk')
    
    if file.filename == '':
        return jsonify({'error': 'Nie wybrano pliku'}), 400
    
    # Tworzenie tymczasowego pliku
    fd, temp_path = tempfile.mkstemp()
    try:
        file.save(temp_path)
        
        filename = secure_filename(file.filename).lower()
        
        if filename.endswith('.pdf'):
            financial_data, tax_data = extract_financial_data_from_pdf(temp_path, platform)
        elif filename.endswith(('.xlsx', '.xls')):
            financial_data, tax_data = process_excel_file(temp_path, platform)
        else:
            return jsonify({'error': 'Nieobsługiwany format pliku'}), 400
        
        if financial_data is None:
            return jsonify({'error': 'Błąd przetwarzania pliku'}), 500
        
        # W prawdziwej aplikacji tutaj byłoby więcej logiki przetwarzania
        
        result = {
            'platform': platform,
            'currency': currency_mapping.get(platform, 'GBP'),
            'financialData': financial_data,
            'taxData': tax_data
        }
        
        return jsonify(result)
    
    finally:
        os.close(fd)
        os.unlink(temp_path)  # Usuwamy tymczasowy plik

# Funkcja dla testowania (symuluje dane zamiast faktycznego parsowania)
@app.route('/api/test-data', methods=['POST'])
def test_data():
    platform = request.json.get('platform', 'uk')
    
    # Dane testowe dla różnych platform
    test_data = {
        'uk': {
            'financialData': {'Income': 18877.68, 'Expenses': -4681.52},
            'taxData': {'Income': 3775.67, 'Expenses': 0}
        },
        'de': {
            'financialData': {'Income': 1594.42, 'Expenses': -335.12},
            'taxData': {'Income': 0, 'Expenses': 0}
        },
        'es': {
            'financialData': {'Income': 15200.75, 'Expenses': -3250.40},
            'taxData': {'Income': 2860.15, 'Expenses': 0}
        },
        'fr': {
            'financialData': {'Income': 12450.35, 'Expenses': -2890.28},
            'taxData': {'Income': 2245.60, 'Expenses': 0}
        },
        'nl': {
            'financialData': {'Income': 9850.42, 'Expenses': -2120.85},
            'taxData': {'Income': 1680.30, 'Expenses': 0}
        },
        'it': {
            'financialData': {'Income': 11250.65, 'Expenses': -2540.18},
            'taxData': {'Income': 1930.45, 'Expenses': 0}
        },
        'usa': {
            'financialData': {'Income': 25680.92, 'Expenses': -5840.34},
            'taxData': {'Income': 4325.78, 'Expenses': 0}
        },
        'ebay': {
            'financialData': {'Income': 8750.45, 'Expenses': -1980.25},
            'taxData': {'Income': 1485.20, 'Expenses': 0}
        },
        'etsy': {
            'financialData': {'Income': 5680.30, 'Expenses': -1240.55},
            'taxData': {'Income': 935.40, 'Expenses': 0}
        },
        'bandq': {
            'financialData': {'Income': 14580.60, 'Expenses': -3250.45},
            'taxData': {'Income': 2485.35, 'Expenses': 0}
        }
    }
    
    platform_data = test_data.get(platform, test_data['uk'])
    result = {
        'platform': platform,
        'currency': currency_mapping.get(platform, 'GBP'),
        'financialData': platform_data['financialData'],
        'taxData': platform_data['taxData']
    }
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
