import sys
import re
import pdfplumber

def extract_pdf_content(pdf_path):
    print(f"\n=== Analyzing {pdf_path} ===")
    
    with pdfplumber.open(pdf_path) as pdf:
        # Print basic info
        print(f"Number of pages: {len(pdf.pages)}")
        
        # Extract text from first page
        first_page = pdf.pages[0]
        text = first_page.extract_text()
        
        print("\n--- First 1000 characters of text ---")
        print(text[:1000])
        
        # Look for CPF patterns
        print("\n--- Possible CPF patterns found ---")
        cpf_patterns = [
            r'CPF[\s:]+(\d{3}\.\d{3}\.\d{3}-\d{2})',  # CPF: 123.456.789-00
            r'CPF[\s:]+(\d{11})',  # CPF: 12345678900
            r'(\d{3}\.\d{3}\.\d{3}-\d{2})',  # Any CPF format
            r'CPF[\s:]+([^\n]+)'  # Anything after CPF:
        ]
        
        for pattern in cpf_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                print(f"Pattern '{pattern}' matched: {matches}")
        
        # Look for reference period with more context
        print("\n--- Reference period patterns with context ---")
        
        # Print lines containing 'MÊS' with surrounding context
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if 'MÊS' in line.upper() or 'MES' in line.upper():
                print(f"Line {i}: {line.strip()}")
                # Print next few lines for context
                for j in range(1, 4):
                    if i + j < len(lines):
                        print(f"  +{j}: {lines[i+j].strip()}")
        
        # Try different patterns
        period_patterns = [
            (r'M[EÊ]S[\s:]*\n([A-Z]+)\s+(\d{4})', 'MÊS followed by month year on next line'),
            (r'M[EÊ]S[\s:]+([A-Z]+)\s+(\d{4})', 'MÊS followed by month year on same line'),
            (r'REFER[EÊ]NCIA[\s:]+([A-Za-zçÇ]+)\s+(\d{4})', 'REFERENCIA pattern'),
            (r'PER[IÍ]ODO[\s:]+([A-Za-zçÇ]+)\s+(\d{4})', 'PERIODO pattern')
        ]
        
        print("\nTrying period patterns:")
        for pattern, desc in period_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                print(f"Pattern '{pattern}' ({desc}) matched: {matches}")
                
        # Also try to find month and year separately
        months = '|'.join(['JANEIRO', 'FEVEREIRO', 'MARCO', 'MARÇO', 'ABRIL', 'MAIO', 'JUNHO', 
                         'JULHO', 'AGOSTO', 'SETEMBRO', 'OUTUBRO', 'NOVEMBRO', 'DEZEMBRO'])
        year_matches = re.findall(r'\b(20\d{2})\b', text)
        month_matches = re.findall(f'\b({months})\b', text, re.IGNORECASE)
        print(f"\nPossible years found: {sorted(set(year_matches))}")
        print(f"Possible months found: {sorted(set(month_matches))}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_pdf_content.py <path_to_pdf>")
        sys.exit(1)
    
    extract_pdf_content(sys.argv[1])
