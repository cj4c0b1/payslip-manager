import sys
import json
from src.pdf_parser import process_military_payslip

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_parser_direct.py <pdf_path> [output_json]")
        return
    
    pdf_path = sys.argv[1]
    output_json = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        print(f"Processing {pdf_path}...")
        result = process_military_payslip(pdf_path)
        
        # Print summary
        print("\n=== Parser Results ===")
        print(f"Employee: {result['employee']['name']}")
        print(f"Rank: {result['employee']['rank']}")
        print(f"CPF: {result['employee']['cpf']}")
        print(f"Period: {result.get('period_display', 'N/A')}")
        
        print("\nEarnings (Top 5):")
        for item in result['earnings'][:5]:
            print(f"  {item['code']}: {item['description']} - R$ {item['amount']:,.2f}")
        if len(result['earnings']) > 5:
            print(f"  ... and {len(result['earnings']) - 5} more")
            
        print("\nDeductions (Top 5):")
        for item in result['deductions'][:5]:
            pct = f" ({item['percentage']}%)" if 'percentage' in item else ""
            print(f"  {item['code']}: {item['description']}{pct} - R$ {item['amount']:,.2f}")
        if len(result['deductions']) > 5:
            print(f"  ... and {len(result['deductions']) - 5} more")
            
        print("\nTotals:")
        print(f"  Gross: R$ {result['totals']['gross']:,.2f}")
        print(f"  Deductions: R$ {result['totals']['deductions']:,.2f}")
        print(f"  Net: R$ {result['totals']['net']:,.2f}")
        
        # Save full output if requested
        if output_json:
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\nFull output saved to {output_json}")
            
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise

if __name__ == "__main__":
    main()
