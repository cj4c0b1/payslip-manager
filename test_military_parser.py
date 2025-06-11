import os
import json
import argparse
from src.pdf_parser import process_military_payslip

def main():
    parser = argparse.ArgumentParser(description='Test Brazilian Military Payslip Parser')
    parser.add_argument('pdf_path', help='Path to the PDF file to parse')
    parser.add_argument('--output', '-o', help='Output JSON file path (optional)')
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"Error: File not found: {args.pdf_path}")
        return
    
    try:
        print(f"Processing {os.path.basename(args.pdf_path)}...")
        result = process_military_payslip(args.pdf_path)
        
        # Print summary
        print("\n=== Parser Results ===")
        print(f"Employee: {result['employee']['name']}")
        print(f"Rank: {result['employee']['rank']}")
        print(f"CPF: {result['employee']['cpf']}")
        print(f"Period: {result.get('period_display', 'N/A')}")
        
        print("\nEarnings:")
        for item in result['earnings']:
            print(f"  {item['code']}: {item['description']} - R$ {item['amount']:,.2f}")
            
        print("\nDeductions:")
        for item in result['deductions']:
            pct = f" ({item['percentage']}%)" if 'percentage' in item else ""
            print(f"  {item['code']}: {item['description']}{pct} - R$ {item['amount']:,.2f}")
            
        print("\nTotals:")
        print(f"  Gross: R$ {result['totals']['gross']:,.2f}")
        print(f"  Deductions: R$ {result['totals']['deductions']:,.2f}")
        print(f"  Net: R$ {result['totals']['net']:,.2f}")
        
        # Save full output if requested
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\nFull output saved to {args.output}")
            
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise

if __name__ == "__main__":
    main()
