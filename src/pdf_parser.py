import re
import pdfplumber
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
import os
from dataclasses import dataclass, asdict
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class MilitaryRank:
    code: str
    abbreviation: str
    full_name: str
    
    @classmethod
    def from_code(cls, code: str) -> 'MilitaryRank':
        """Convert military rank code to human-readable format"""
        # Brazilian Army rank codes
        rank_map = {
            '10': {'abbr': '2º Ten', 'name': '2º Tenente'},
            '11': {'abbr': '1º Ten', 'name': '1º Tenente'},
            '12': {'abbr': 'Cap', 'name': 'Capitão'},
            '13': {'abbr': 'Maj', 'name': 'Major'},
            '14': {'abbr': 'Ten Cel', 'name': 'Tenente-Coronel'},
            '15': {'abbr': 'Cel', 'name': 'Coronel'},
        }
        rank_info = rank_map.get(code, {'abbr': code, 'name': f'Rank {code}'})
        return cls(code=code, **rank_info)


class MilitaryPayslipParser:
    """Specialized parser for Brazilian military payslips"""
    
    def __init__(self, pdf_path: str):
        """Initialize the parser with the path to the PDF file"""
        self.pdf_path = pdf_path
        self.filename = os.path.basename(pdf_path)
        self.text = ""
        self.tables = []
        self.raw_tables = []
        
    def extract_text_and_tables(self) -> bool:
        """Extract text and tables from the PDF"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # Extract text from all pages
                self.text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
                
                # Extract tables from all pages
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if tables:
                        self.raw_tables.extend(tables)
                        
                # Clean and process tables
                self._process_tables()
                
            logger.info(f"Successfully extracted text and tables from {self.filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {self.filename}: {str(e)}")
            return False
    
    def _process_tables(self) -> None:
        """Process and clean extracted tables"""
        for table in self.raw_tables:
            # Remove empty rows and clean cells
            cleaned_table = []
            for row in table:
                cleaned_row = [str(cell).strip() if cell is not None else "" for cell in row]
                # Skip empty rows
                if any(cell for cell in cleaned_row):
                    cleaned_table.append(cleaned_row)
            
            if cleaned_table:
                self.tables.append(cleaned_table)
    
    def parse_employee_info(self) -> Dict[str, Any]:
        """Extract employee information from the military payslip"""
        logger = logging.getLogger(__name__)
        
        # Extract name from the line with PREC-CP NOME OM DE VINCULAÇÃO
        name_match = re.search(r'\d+\s+([^\n]+?)\s+CMDO', self.text)
        
        # Extract CPF (Brazilian ID) - try multiple formats
        cpf = None
        cpf_patterns = [
            # Common formats
            r'CPF[\s:]+(\d{3}\.\d{3}\.\d{3}-\d{2})',  # CPF: 000.000.000-00
            r'(\d{3}\.\d{3}\.\d{3}-\d{2})',  # 000.000.000-00
            r'(\d{3}\.\d{3}\.\d{3}/\d{2})',  # 000.000.000/00
            r'(\d{11})',  # 00000000000
            r'(\d{3}\s\d{3}\s\d{3}\s\d{2})',  # 000 000 000 00
            r'CPF:\s*([\d\.-]+)'  # CPF: 000.000.000-00 (more flexible)
        ]
        
        # Try each pattern until we find a match
        for pattern in cpf_patterns:
            try:
                matches = re.finditer(pattern, self.text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    # Get the first group that matched (should be the CPF)
                    cpf_str = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    # Clean the CPF string
                    clean_cpf = re.sub(r'[^\d]', '', cpf_str)
                    
                    # Validate CPF length (11 digits)
                    if len(clean_cpf) == 11 and clean_cpf.isdigit():
                        # Format as 000.000.000-00 for consistency
                        cpf = f"{clean_cpf[:3]}.{clean_cpf[3:6]}.{clean_cpf[6:9]}-{clean_cpf[9:]}"
                        logger.info(f"Found CPF: {cpf} using pattern: {pattern}")
                        break
                if cpf:
                    break
            except Exception as e:
                logger.debug(f"Error with CPF pattern {pattern}: {str(e)}")
        
        if not cpf:
            # Try a more aggressive search as a last resort
            logger.debug("Trying aggressive CPF search...")
            cpf_matches = re.findall(r'\b(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-/]?\d{2})\b', self.text)
            for match in cpf_matches:
                clean_cpf = re.sub(r'[^\d]', '', match)
                if len(clean_cpf) == 11 and clean_cpf.isdigit():
                    cpf = f"{clean_cpf[:3]}.{clean_cpf[3:6]}.{clean_cpf[6:9]}-{clean_cpf[9:]}"
                    logger.info(f"Found CPF with aggressive search: {cpf}")
                    break
        
        if not cpf:
            logger.warning(f"No valid CPF found in the payslip. Text sample: {self.text[:200]}...")
        else:
            logger.info(f"Successfully extracted CPF: {cpf}")
        
        # Extract rank information - format: "10 (2° TEN)"
        rank_match = re.search(r'P/G REAL[\s:]+(\d+)\s+\([^)]+\)', self.text)
        rank_code = rank_match.group(1) if rank_match else None
        
        payment_rank_match = re.search(r'P/G DE PAGAMENTO[\s:]+(\d+)\s+\([^)]+\)', self.text)
        payment_rank_code = payment_rank_match.group(1) if payment_rank_match else None
        
        # Extract bank information - appears on the same line as CPF
        bank_match = re.search(r'CPF\s+(?:\d{3}\.\d{3}\.\d{3}-\d{2})\s+(\d+)\s+(\d+)\s+(\d+)', self.text)
        bank_info = None
        if bank_match:
            bank_info = f"Banco: {bank_match.group(1)}, Ag: {bank_match.group(2)}, CC: {bank_match.group(3)}"
        
        employee_info = {
            'name': name_match.group(1).strip() if name_match else None,
            'cpf': cpf,
            'rank': MilitaryRank.from_code(rank_code).full_name if rank_code else None,
            'rank_code': rank_code,
            'payment_rank': MilitaryRank.from_code(payment_rank_code).full_name if payment_rank_code else None,
            'payment_rank_code': payment_rank_code,
            'bank': bank_info
        }
        
        return {k: v for k, v in employee_info.items() if v is not None}
    
    def parse_reference_period(self) -> Dict[str, str]:
        """Extract reference period from the payslip.
        
        Handles format where 'MÊS' is on one line and 'MAIO 2024' is on the next line.
        """
        # First try to find the month and year in the text
        # Look for 'MÊS' followed by any whitespace and newline, then capture month and year
        month_year_match = re.search(
            r'(?:M[EÊ]S\s*\n)(?:[^\n]*?)([A-ZÇ]+)\s+(\d{4})', 
            self.text, 
            re.IGNORECASE | re.MULTILINE
        )
        
        if not month_year_match:
            # Alternative pattern in case the first one fails
            month_year_match = re.search(
                r'(JANEIRO|FEVEREIRO|MAR[ÇC]O|ABRIL|MAIO|JUNHO|JULHO|AGOSTO|SETEMBRO|OUTUBRO|NOVEMBRO|DEZEMBRO)\s+(20\d{2})',
                self.text,
                re.IGNORECASE
            )
        
        if month_year_match:
            month = month_year_match.group(1).upper()
            year = month_year_match.group(2)
            
            # Convert Portuguese month name to number
            month_map = {
                'JANEIRO': '01', 'FEVEREIRO': '02', 'MARCO': '03', 'MARÇO': '03', 'ABRIL': '04',
                'MAIO': '05', 'JUNHO': '06', 'JULHO': '07', 'AGOSTO': '08',
                'SETEMBRO': '09', 'OUTUBRO': '10', 'NOVEMBRO': '11', 'DEZEMBRO': '12'
            }
            
            # Normalize month name (handle both with and without accent)
            normalized_month = month.upper()
            if normalized_month == 'MARCO':
                normalized_month = 'MARÇO'
                
            month_num = month_map.get(normalized_month, '00')
            return {
                'month_name': normalized_month.capitalize(),
                'year': year,
                'period': f"{year}-{month_num}",
                'display': f"{normalized_month.capitalize()} {year}"
            }
            
        # If we still can't find it, try to extract from the filename (e.g., Contracheque052025.pdf)
        filename = os.path.basename(self.pdf_path)
        filename_match = re.search(r'(\d{2})(\d{4})\.pdf$', filename)
        if filename_match:
            month_num = filename_match.group(1)
            year = filename_match.group(2)
            month_map = {
                '01': 'Janeiro', '02': 'Fevereiro', '03': 'Março', '04': 'Abril',
                '05': 'Maio', '06': 'Junho', '07': 'Julho', '08': 'Agosto',
                '09': 'Setembro', '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
            }
            month_name = month_map.get(month_num, 'Desconhecido')
            return {
                'month_name': month_name,
                'year': year,
                'period': f"{year}-{month_num}",
                'display': f"{month_name} {year}"
            }
            
        return {}
    
    def parse_earnings_and_deductions(self) -> Tuple[List[Dict], List[Dict], Dict]:
        """Extract earnings and deductions from the military payslip"""
        earnings = []
        deductions = []
        totals = {'gross': 0.0, 'deductions': 0.0, 'net': 0.0}
        
        logger.info(f"Processing {len(self.tables)} tables from PDF")
        
        # Military-specific code mappings with additional context
        code_mapping = {
            'B01': 'SOLDO (Soldado)',
            'B06': 'ADICIONAL DE HABILITAÇÃO', 
            'B20': 'SERVIÇO MILITAR',
            'Z01': 'FUSEX (Fundo de Saúde)',
            'Z02': 'PENSÃO MILITAR',
            'Z35': 'FUNDO DE MONTE PIO',
            'ZQ6': 'ASSISTÊNCIA JURÍDICA',
            'ZRO': 'POUPANÇA MILITAR',
            'BL0': 'AD C DISP MIL (Adicional de Disponibilidade Militar)'
        }
        
        for table_idx, table in enumerate(self.tables, 1):
            logger.info(f"\n=== Processing table {table_idx} of {len(self.tables)} ===")
            logger.info(f"Table has {len(table)} rows")
            if not table or len(table) < 2:
                continue
                
            # Find the header row
            header_row = None
            for i, row in enumerate(table):
                if any('CÓDIGO' in cell.upper() for cell in row):
                    header_row = i
                    break
            
            if header_row is None:
                continue
                
            # Process data rows
            for row in table[header_row + 1:]:
                if len(row) < 6:  # Skip incomplete rows
                    continue
                    
                code = row[0].strip()
                if not code or not code[0].isalnum():
                    continue
                    
                description = row[1].strip()
                additional_info = row[2].strip()
                
                # Extract values, handling different number formats
                def parse_value(val: str, row_idx: int, col_idx: int) -> float:
                    original_val = val
                    if not val or (isinstance(val, str) and val.isspace()):
                        logger.debug(f"Row {row_idx}, Col {col_idx}: Empty value, returning 0")
                        return 0.0
                    
                    # Convert to string if it isn't already
                    if not isinstance(val, str):
                        val = str(val).strip()
                    else:
                        val = val.strip()
                    
                    # Log the raw value before cleaning
                    logger.debug(f"Row {row_idx}, Col {col_idx}: Raw value: '{original_val}'")
                    
                    # Handle empty strings after stripping
                    if not val:
                        return 0.0
                    
                    try:
                        # Handle Brazilian number format (1.234,56)
                        if ',' in val and '.' in val:
                            # If both separators exist, assume comma is decimal and dot is thousand
                            if val.find(',') > val.find('.'):
                                # Format like 1,234.56 -> 1234.56
                                clean_val = val.replace(',', '')
                            else:
                                # Format like 1.234,56 -> 1234.56
                                clean_val = val.replace('.', '').replace(',', '.')
                        elif ',' in val:
                            # Format like 1234,56 -> 1234.56
                            clean_val = val.replace(',', '.')
                        else:
                            # Format like 1234.56 or 1.234.567,00 (with dots as thousand separators)
                            clean_val = val.replace('.', '')
                        
                        # Remove any remaining non-numeric characters except minus and dot
                        clean_val = re.sub(r'[^\d.-]', '', clean_val)
                        
                        # Handle empty result after cleaning
                        if not clean_val:
                            return 0.0
                            
                        # Parse the cleaned value
                        result = float(clean_val)
                        logger.debug(f"Row {row_idx}, Col {col_idx}: Parsed value: {result} from '{original_val}'")
                        return result
                        
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Row {row_idx}, Col {col_idx}: Could not parse '{original_val}' as float: {e}")
                        logger.debug(f"Clean value was: {clean_val if 'clean_val' in locals() else 'N/A'}")
                        return 0.0
                
                # Log the entire row for debugging
                logger.debug(f"\n--- Processing row {i} ---")
                for col_idx, cell in enumerate(row):
                    logger.debug(f"  Col {col_idx}: '{cell}'")  # Added quotes to see whitespace
                    
                # Skip rows that don't have enough columns
                if len(row) < 4:  # Reduced minimum required columns
                    logger.debug(f"Skipping row {i} - not enough columns")
                    continue
                
                # For military payslips, we need to identify the columns containing amounts
                # Let's analyze the row structure
                logger.debug(f"Analyzing row structure for code: {code}")
                
                # Try to find the amount columns by scanning the row
                amount_columns = []
                for col_idx, cell in enumerate(row):
                    cell_str = str(cell).strip()
                    if not cell_str:
                        continue
                        
                    # Check if this looks like a monetary value
                    if re.search(r'\d+[.,]\d{2}', cell_str) or (any(c.isdigit() for c in cell_str) and 
                                                              any(c in cell_str for c in '.,') and 
                                                              len(cell_str) > 2):
                        amount_columns.append(col_idx)
                
                logger.debug(f"Potential amount columns: {amount_columns}")
                
                # For military payslips, we'll use the following strategy:
                # 1. First numeric column after description is usually the amount
                # 2. Last numeric column is usually the total/net
                earnings_col = amount_columns[0] if amount_columns else -1
                deductions_col = amount_columns[1] if len(amount_columns) > 1 else -1
                
                # Try to parse the values with better error handling
                try:
                    earnings_val = parse_value(row[earnings_col], i, earnings_col) if earnings_col >= 0 else 0.0
                    
                    # For deductions, we need to be careful as they might be in a different column
                    if deductions_col > 0 and len(row) > deductions_col:
                        deductions_val = parse_value(row[deductions_col], i, deductions_col)
                        # If this is actually an earnings amount (positive), don't count it as deduction
                        if deductions_val > 0:
                            earnings_val = max(earnings_val, deductions_val)
                            deductions_val = 0.0
                    else:
                        deductions_val = 0.0
                        
                    # Try to get net value from the last column if it looks like a total
                    net_val = 0.0
                    if len(row) > 2:
                        potential_net = row[-1]
                        if isinstance(potential_net, str) and any(c.isdigit() for c in potential_net):
                            net_val = parse_value(potential_net, i, -1)
                            
                except (IndexError, ValueError) as e:
                    logger.warning(f"Error parsing values in row {i}: {e}")
                    logger.debug(f"Row data: {row}")
                    earnings_val = 0.0
                    deductions_val = 0.0
                    net_val = 0.0
                    
                logger.debug(f"Parsed values - Earnings: {earnings_val}, Deductions: {deductions_val}, Net: {net_val}")
                
                # Check for percentage in additional info
                percentage = None
                if '%' in additional_info:
                    pct_match = re.search(r'(\d+,\d+)%', additional_info)
                    if pct_match:
                        percentage = float(pct_match.group(1).replace(',', '.'))
                
                # Add to appropriate list
                item = {
                    'code': code,
                    'description': code_mapping.get(code, description),
                    'original_description': description,
                    'additional_info': additional_info if additional_info else None,
                    'percentage': percentage
                }
                
                if earnings_val > 0:
                    item['amount'] = earnings_val
                    earnings.append(item)
                    totals['gross'] += earnings_val
                elif deductions_val > 0:
                    # Store deductions as negative values
                    item['amount'] = -abs(deductions_val)
                    deductions.append(item)
                    totals['deductions'] += abs(deductions_val)
                
                # Log the processed item for debugging
                logger.debug(f"Processed item: {code} - {item.get('description')} - Amount: {item.get('amount', 0):.2f}")
        
        # Always calculate the net from the stored values
        totals['net'] = totals['gross'] - totals['deductions']
        
        # If we have an explicit net value from the PDF, log any discrepancy
        if net_val and abs(net_val - totals['net']) > 0.01:
            logger.warning(f"Net amount from PDF ({net_val:.2f}) doesn't match calculated net ({totals['net']:.2f})")
        
        # Log the final totals for debugging
        logger.debug(f"Final totals - Gross: {totals['gross']:.2f}, Deductions: {totals['deductions']:.2f}, Net: {totals['net']:.2f}")
        
        return earnings, deductions, totals
    
    def parse_payslip(self) -> Dict[str, Any]:
        """Parse the entire payslip and return structured data"""
        if not self.extract_text_and_tables():
            raise ValueError(f"Failed to extract data from {self.filename}")
        
        employee_info = self.parse_employee_info()
        period_info = self.parse_reference_period()
        earnings, deductions, totals = self.parse_earnings_and_deductions()
        
        # Calculate sum of all earnings and validate against total
        calculated_gross = sum(item.get('amount', 0) for item in earnings)
        gross_discrepancy = abs(calculated_gross - totals.get('gross', 0)) > 0.01
        
        if gross_discrepancy:
            logger.warning(f"Gross amount mismatch: Calculated {calculated_gross:.2f} vs Total {totals.get('gross', 0):.2f}")
            
            # If we have a single earning that's causing the discrepancy, try to fix it
            if len(earnings) > 0 and 'BL0' in [e.get('code', '') for e in earnings]:
                # Calculate what BL0 should be
                other_earnings = sum(e.get('amount', 0) for e in earnings if e.get('code') != 'BL0')
                correct_bl0 = totals.get('gross', 0) - other_earnings
                
                # Update the BL0 amount
                for item in earnings:
                    if item.get('code') == 'BL0':
                        logger.info(f"Adjusting BL0 amount from {item.get('amount', 0):.2f} to {correct_bl0:.2f}")
                        item['amount'] = correct_bl0
                        break
        
        # Prepare final output
        result = {
            'employee': {
                'name': employee_info.get('name'),
                'rank': employee_info.get('rank'),
                'cpf': employee_info.get('cpf'),
                'bank': employee_info.get('bank'),
                # Use CPF as employee_id if available, otherwise use a combination of name and rank
                'employee_id': employee_info.get('employee_id') or f"CPF_{employee_info.get('cpf')}" if employee_info.get('cpf') else None
            },
            'period': period_info.get('period', ''),
            'period_display': period_info.get('display', ''),
            'earnings': [
                {k: v for k, v in item.items() 
                 if k in ['code', 'description', 'amount', 'percentage'] and v is not None}
                for item in earnings
            ],
            'deductions': [
                {k: v for k, v in item.items() 
                 if k in ['code', 'description', 'amount', 'percentage'] and v is not None}
                for item in deductions
            ],
            'totals': totals,
            '_validation': {
                'gross_match': not gross_discrepancy,
                'calculated_gross': calculated_gross
            }
        }
        
        # Validate the results
        self._validate_payslip(result)
        
        return result
    
    def _validate_payslip(self, data: Dict[str, Any]) -> None:
        """Validate the extracted payslip data"""
        if not data.get('employee', {}).get('name'):
            logger.warning("Could not extract employee name from payslip")
        else:
            logger.info(f"Processing payslip for: {data['employee']['name']}")
        
        if not data.get('period'):
            logger.warning("Could not extract reference period from payslip")
        else:
            logger.info(f"Payslip period: {data.get('period_display', data['period'])}")
        
        # Validate totals
        if 'totals' in data:
            logger.info("=== PAYSLIP TOTALS ===")
            logger.info(f"Stored gross: {data['totals'].get('gross', 0):.2f}")
            logger.info(f"Stored deductions: {data['totals'].get('deductions', 0):.2f}")
            logger.info(f"Stored net: {data['totals'].get('net', 0):.2f}")
            
            # Calculate from line items (deductions are already negative in the items)
            calculated_gross = sum(float(item.get('amount', 0)) for item in data.get('earnings', []))
            calculated_deductions = sum(abs(float(item.get('amount', 0))) for item in data.get('deductions', []))
            calculated_net = calculated_gross - calculated_deductions
            
            logger.info("\n=== CALCULATED TOTALS ===")
            logger.info(f"Calculated gross: {calculated_gross:.2f}")
            logger.info(f"Calculated deductions: {calculated_deductions:.2f}")
            logger.info(f"Calculated net: {calculated_net:.2f}")
            
            # Log all earnings and deductions for debugging
            if data.get('earnings'):
                logger.info("\n=== EARNINGS ===")
                for item in data['earnings']:
                    logger.info(f"{item.get('code')} - {item.get('description')}: {item.get('amount', 0):.2f}")
            
            if data.get('deductions'):
                logger.info("\n=== DEDUCTIONS ===")
                for item in data['deductions']:
                    logger.info(f"{item.get('code')} - {item.get('description')}: -{item.get('amount', 0):.2f}")
            
            # Allow small floating point differences
            gross_diff = abs(calculated_gross - data['totals'].get('gross', 0))
            net_diff = abs(calculated_net - data['totals'].get('net', 0))
            
            if gross_diff > 0.01:
                logger.warning(f"Gross amount mismatch: calculated {calculated_gross:.2f} vs {data['totals'].get('gross', 0):.2f} (diff: {gross_diff:.2f})")
            
            if net_diff > 0.01:
                logger.warning(f"Net amount mismatch: calculated {calculated_net:.2f} vs {data['totals'].get('net', 0):.2f} (diff: {net_diff:.2f})")
            
            logger.info("\n")
    
    def _extract_pattern(self, pattern: str, text: str = None, flags: int = re.IGNORECASE) -> Optional[re.Match]:
        """Helper method to extract pattern from text"""
        text = text or self.text
        return re.search(pattern, text, flags)


def process_military_payslip(pdf_path: str) -> Dict[str, Any]:
    """Process a single military payslip PDF file"""
    try:
        parser = MilitaryPayslipParser(pdf_path)
        return parser.parse_payslip()
    except Exception as e:
        logger.error(f"Error processing {os.path.basename(pdf_path)}: {str(e)}")
        raise


# For backward compatibility
class PayslipParser(MilitaryPayslipParser):
    """Legacy parser class for backward compatibility"""
    pass
        
    def extract_text_and_tables(self) -> None:
        """Extract text and tables from the PDF"""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # Extract text from all pages
                self.text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
                
                # Extract tables from all pages
                for page in pdf.pages:
                    self.tables.extend(page.extract_tables())
                    
            logger.info(f"Successfully extracted text and tables from {self.filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {self.filename}: {str(e)}")
            return False
    
    def parse_employee_info(self) -> Dict:
        """Extract employee information from the payslip"""
        logger = logging.getLogger(__name__)
        
        # Try multiple patterns to extract employee ID with various formats
        employee_id_patterns = [
            # Pattern for ID at start of line or after whitespace (e.g., '96 0611145' or 'PREC-CP 96 0611145')
            r'(?:^|\s)(\d{2}\s*\d{7})(?=\s|$)',
            # Pattern for ID after 'PREC-CP' (e.g., 'PREC-CP 96 0611145')
            r'PREC-CP[\s:]+(\d{2}\s*\d{7})',
            # Other common patterns
            r'Employee\s*ID[\s:]+(\d{2}\s*\d{7})',
            r'ID\s*[:\\.\s]+\s*(\d{2}\s*\d{7})\b',
            r'Employee\s*ID[\s:]+(\S+)',
            r'ID\s*[:\\.\s]+\s*(\S+)',
            r'Matr[ií]cula[\s:]+(\S+)',
            r'Registration[\s:]+(\S+)',
            r'PREC-CP[\s:]+(\S+)',
            r'(\d{9})',  # 9-digit ID
            r'(\d{2}\s*\d{3}\s*\d{4})'  # 2-3-4 digit pattern
        ]
        
        employee_id = None
        original_employee_id = None
        for pattern in employee_id_patterns:
            match = re.search(pattern, self.text, re.IGNORECASE | re.MULTILINE)
            if match:
                # Get the first non-None group
                original_employee_id = next((g for g in match.groups() if g), match.group(0)).strip()
                # Clean up the ID (remove spaces and non-alphanumeric characters) for the final output
                employee_id = re.sub(r'[^\w]', '', str(original_employee_id)).strip()
                logger.info(f"Found employee ID using pattern '{pattern}': {original_employee_id} (cleaned: {employee_id})")
                break
        
        # Try to extract name with various patterns
        name = None
        
        # Format 1: PREC-CP\n96 0611145', 'NOME\nRENATO TERRES HELLMANN'
        if not name and employee_id:
            match = re.search(r'NOME\s*\n([A-ZÀ-ÿ\s]+?)(?:\n|$)', self.text, re.IGNORECASE | re.MULTILINE)
            if match:
                name = match.group(1).strip()
                logger.debug(f"Found name after 'NOME' label: {name}")
        
        # Format 2: PREC-CP NOME OM DE VINCULAÇÃO...\n96 0611145 RENATO TERRES HELLMANN CMDO...
        if not name and original_employee_id:
            # First try with the original ID format (with spaces if any)
            id_pattern = re.escape(original_employee_id)
            match = re.search(fr'{id_pattern}\s+([A-ZÀ-ÿ\s]+?)(?:\s+CMDO|\n|$)', self.text)
            if match:
                name = match.group(1).strip()
                logger.debug(f"Found name after original employee ID format: {name}")
            
            # If not found, try with the cleaned ID format as fallback
            if not name and employee_id and employee_id != original_employee_id:
                id_pattern = re.escape(employee_id)
                match = re.search(fr'{id_pattern}\s+([A-ZÀ-ÿ\s]+?)(?:\s+CMDO|\n|$)', self.text)
                if match:
                    name = match.group(1).strip()
                    logger.debug(f"Found name after cleaned employee ID: {name}")
        
        # Format 3: Look for name after PREC-CP and before next all-caps word
        if not name:
            match = re.search(r'PREC-CP[\s\n]+(?:[A-Z0-9\s]+\n)?([A-ZÀ-ÿ][A-ZÀ-ÿ\s]+?)(?:\s+[A-Z]{2,}|\n|$)', self.text)
            if match:
                name = match.group(1).strip()
                logger.debug(f"Found name after PREC-CP: {name}")
        
        # Fallback patterns
        if not name:
            name = (
                # Pattern for name following employee ID (e.g., '96 0611145 RENATO TERRES HELLMANN')
                self._extract_pattern(r'\d{2}[\s\d]{7,}\s+([A-ZÀ-ÿ][A-ZÀ-ÿ\s]+?)(?=\s+[A-Z]{2,}|\d|\n|$)') or
                # Standard patterns
                self._extract_pattern(r'Name[\s:]+([^\n]+)') or
                self._extract_pattern(r'Nome[\s:]+([^\n]+)') or
                self._extract_pattern(r'Employee\s*Name[\s:]+([^\n]+)') or
                self._extract_pattern(r'Funcion[aá]rio[\s:]+([^\n]+)', re.IGNORECASE)
            )
        
        # Clean up the name if found
        if name:
            # Normalize whitespace and preserve uppercase (since military names are all caps)
            name = ' '.join(name.split())
            
        # Extract CPF (Brazilian ID) - try multiple formats
        cpf = None
        cpf_patterns = [
            # Common formats
            r'CPF[\s:]+(\d{3}\.\d{3}\.\d{3}-\d{2})',  # CPF: 000.000.000-00
            r'(\d{3}\.\d{3}\.\d{3}-\d{2})',  # 000.000.000-00
            r'(\d{3}\.\d{3}\.\d{3}/\d{2})',  # 000.000.000/00
            r'(\d{11})',  # 00000000000
            r'(\d{3}\s\d{3}\s\d{3}\s\d{2})',  # 000 000 000 00
            r'CPF:\s*([\d\.-]+)'  # CPF: 000.000.000-00 (more flexible)
        ]
        
        # Try each pattern until we find a match
        for pattern in cpf_patterns:
            try:
                matches = re.finditer(pattern, self.text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    # Get the first group that matched (should be the CPF)
                    cpf_str = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    # Clean the CPF string
                    clean_cpf = re.sub(r'[^\d]', '', cpf_str)
                    
                    # Validate CPF length (11 digits)
                    if len(clean_cpf) == 11 and clean_cpf.isdigit():
                        # Format as 000.000.000-00 for consistency
                        cpf = f"{clean_cpf[:3]}.{clean_cpf[3:6]}.{clean_cpf[6:9]}-{clean_cpf[9:]}"
                        logger.info(f"Found CPF: {cpf} using pattern: {pattern}")
                        break
                if cpf:
                    break
            except Exception as e:
                logger.debug(f"Error with CPF pattern {pattern}: {str(e)}")
        
        if not cpf:
            # Try a more aggressive search as a last resort
            logger.debug("Trying aggressive CPF search...")
            cpf_matches = re.findall(r'\b(\d{3}[.\s]?\d{3}[.\s]?\d{3}[-/]?\d{2})\b', self.text)
            for match in cpf_matches:
                clean_cpf = re.sub(r'[^\d]', '', match)
                if len(clean_cpf) == 11 and clean_cpf.isdigit():
                    cpf = f"{clean_cpf[:3]}.{clean_cpf[3:6]}.{clean_cpf[6:9]}-{clean_cpf[9:]}"
                    logger.info(f"Found CPF with aggressive search: {cpf}")
                    break
        
        if not cpf:
            logger.warning(f"No valid CPF found in the payslip. Text sample: {self.text[:200]}...")
        else:
            logger.info(f"Successfully extracted CPF: {cpf}")
            
        employee_info = {
            'employee_id': employee_id,
            'name': name,
            'cpf': cpf,  # Add CPF to employee info
            'department': self._extract_pattern(r'Department[\s:]+([^\n]+)') or 
                         self._extract_pattern(r'Departamento[\s:]+([^\n]+)') or
                         self._extract_pattern(r'Setor[\s:]+([^\n]+)'),
            'position': self._extract_pattern(r'Position[\s:]+([^\n]+)') or 
                       self._extract_pattern(r'Cargo[\s:]+([^\n]+)') or
                       self._extract_pattern(r'Fun[cç][aã]o[\s:]+([^\n]+)', flags=re.IGNORECASE),
            'email': self._extract_pattern(r'Email[\s:]+([^\s@]+@[^\s@]+\.[^\s@]+)') or
                    self._extract_pattern(r'E-mail[\s:]+([^\s@]+@[^\s@]+\.[^\s@]+)'),
        }
        
        # If we still don't have an ID, try to extract from the filename as a last resort
        if not employee_info.get('employee_id'):
            filename_match = re.search(r'(\d{4,})', self.filename)
            if filename_match:
                employee_info['employee_id'] = filename_match.group(1)
                logger.info(f"Extracted employee ID from filename: {employee_info['employee_id']}")
        
        # Log if we couldn't find an employee ID
        if not employee_info.get('employee_id'):
            logger.warning(f"Could not extract employee ID from {self.filename}")
            logger.debug(f"Text content for debugging (first 1000 chars):\n{self.text[:1000]}...")
        else:
            logger.info(f"Successfully extracted employee info for ID: {employee_info['employee_id']}")
            
        return {k: v for k, v in employee_info.items() if v}
    
    def parse_payment_info(self) -> Dict:
        """Extract payment information from the payslip
        
        Returns:
            Dict containing payment information with:
            - reference_month: Date in YYYY-MM-01 format
            - issue_date: Date in DD/MM/YYYY format (if available)
            - gross_salary: Total gross salary amount
        """
        # Extract reference month in Portuguese format (e.g., 'MAIO 2024')
        reference_month = None
        month_match = re.search(r'(?i)(JANEIRO|FEVEREIRO|MAR[ÇC]O|ABRIL|MAIO|JUNHO|JULHO|AGOSTO|SETEMBRO|OUTUBRO|NOVEMBRO|DEZEMBRO)\s+(\d{4})', self.text)
        if month_match:
            month_pt = month_match.group(1).capitalize()
            year = month_match.group(2)
            # Convert Portuguese month to number (1-12)
            month_map = {
                'Janeiro': '01', 'Fevereiro': '02', 'Março': '03', 'Abril': '04',
                'Maio': '05', 'Junho': '06', 'Julho': '07', 'Agosto': '08',
                'Setembro': '09', 'Outubro': '10', 'Novembro': '11', 'Dezembro': '12'
            }
            month_num = month_map.get(month_pt, '01')
            # Format as YYYY-MM-01 for database Date field
            reference_month = f"{year}-{month_num}-01"
            logger.info(f"Extracted reference month: {reference_month}")
        else:
            logger.warning(f"Could not extract reference month from: {self.text[:200]}...")
        
        # Extract issue date from the bottom of the document
        issue_date = None
        issue_match = re.search(r'Data/Hora da emissão[:\s]+(\d{2}/\d{2}/\d{4})', self.text)
        if issue_match:
            issue_date = issue_match.group(1)
            logger.debug(f"Extracted issue date: {issue_date}")
        
        # Extract gross salary from the table row
        gross_salary = 0.0
        for table in self.tables:
            if not table:
                continue
                
            # Look for a row that matches the total line pattern
            for row in table:
                if len(row) >= 5 and row[4] and 'R$' in str(row[4]):
                    try:
                        # The gross salary is in the 5th column (index 4)
                        gross_str = str(row[4]).replace('R$', '').strip().replace('.', '').replace(',', '.')
                        gross_salary = float(gross_str)
                        logger.info(f"Extracted gross salary from table: {gross_salary}")
                        break
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"Could not parse gross salary from table row: {row}")
            
            if gross_salary > 0:
                break
        
        payment_info = {
            'reference_month': reference_month,
            'issue_date': issue_date,
            'gross_salary': gross_salary if gross_salary > 0 else None
        }
        return {k: v for k, v in payment_info.items() if v is not None}
    
    def parse_earnings_and_deductions(self, gross_salary: float = None) -> Tuple[List[Dict], List[Dict]]:
        """Extract earnings and deductions from the payslip
        
        Args:
            gross_salary: Optional gross salary amount to use for validation
            
        Returns:
            Tuple of (earnings, deductions) where each is a list of dicts
        """
        earnings = []
        self.gross_salary = gross_salary  # Store for use in helper methods
        
        # Find the header row to determine column indices
        header_row = None
        for table in self.tables:
            for row in table:
                if any('Receitas' in str(cell) for cell in row if cell):
                    header_row = row
                    break
            if header_row:
                break
                
        if not header_row:
            logger.warning("No header row with 'Receitas' found in any table")
            return [], []
            
        # Find the index of the 'Receitas' column
        try:
            amount_col = header_row.index('Receitas (R$)')
        except ValueError:
            # Try to find by partial match if exact match fails
            for i, cell in enumerate(header_row):
                if cell and 'Receitas' in str(cell):
                    amount_col = i
                    break
            else:
                return []
        
        # Process data rows
        for row in table[table.index(header_row) + 1:]:  # Start from row after header
            try:
                # Skip empty rows or rows without a code
                if not row or not row[0] or not row[0].strip():
                    continue
                    
                # Get the amount from the 'Receitas' column
                amount_str = str(row[amount_col]).strip()
                if not amount_str or amount_str == '-':
                    continue
                    
                # Handle multi-line amount strings (e.g., 'n HELLMA\n1.566,55')
                if '\n' in amount_str:
                    # Try to find the last line that looks like a number
                    lines = amount_str.split('\n')
                    for line in reversed(lines):
                        if any(c.isdigit() for c in line):
                            amount_str = line.strip()
                            break
                    
                # Special case for 'AD C DISP MIL' where amount is embedded in time string (e.g., '11:45:35747,50')
                if 'AD C DISP MIL' in str(row[1]) and ':' in amount_str and ',' in amount_str:
                    # The format is typically HH:MM:SSSS,DD where SS,DD is the amount
                    # We want to extract everything after the last ':' and keep the decimal part
                    last_colon = amount_str.rfind(':')
                    comma_pos = amount_str.find(',')
                    if last_colon >= 0 and comma_pos > last_colon:
                        # Get the part after the last colon and before the comma (integer part)
                        int_part = amount_str[last_colon + 1:comma_pos]
                        # Get the decimal part after the comma
                        decimal_part = amount_str[comma_pos + 1:comma_pos + 3]  # Take exactly 2 decimal places
                        # Reconstruct the amount string
                        amount_str = f"{int_part}.{decimal_part}"
                        logger.debug(f"Extracted amount for AD C DISP MIL: {amount_str}")
                # Skip if the string looks like a regular time value (e.g., '10:30:52')
                elif re.match(r'^\d{1,2}:\d{2}(?::\d{2})?$', amount_str):
                    logger.debug(f"Skipping time value in amount column: {amount_str}")
                    continue
                    
                # Clean up the amount string (remove any non-numeric characters except , and .)
                amount_str = ''.join(c for c in amount_str if c.isdigit() or c in ',.')
                
                # Skip if we don't have any digits left after cleaning
                if not any(c.isdigit() for c in amount_str):
                    logger.debug(f"No valid number found in amount: {amount_str}")
                    continue
                
                # Convert amount to float (handle Brazilian number format)
                try:
                    # Clean and parse the amount
                    clean_amount_str = amount_str.replace('.', '').replace(',', '.')
                    amount = float(clean_amount_str)
                    
                    # Get code and description
                    code = str(row[0]).strip()
                    description = self._clean_description(row[1]) if len(row) > 1 and row[1] else ''
                    
                    # Special handling for AD C DISP MIL if amount seems too large (common issue with time data)
                    if 'AD C DISP MIL' in description and amount > 10000:  # Unusually high value
                        logger.warning(f"Suspiciously high amount for AD C DISP MIL: {amount}")
                        
                        # Calculate correct amount as total gross minus other earnings
                        if gross_salary is not None and gross_salary > 0:
                            try:
                                # Sum all other earnings except the current one
                                other_earnings_sum = sum(
                                    e['amount'] 
                                    for e in earnings if 'AD C DISP MIL' not in e.get('description', '')
                                )
                                
                                # Calculate the correct amount and round to 2 decimal places for currency
                                correct_amount = round(gross_salary - other_earnings_sum, 2)
                                if correct_amount > 0:  # Sanity check
                                    logger.info(f"Calculated correct amount for AD C DISP MIL: {correct_amount:.2f} "
                                              f"(Total: {gross_salary:.2f} - Other earnings: {other_earnings_sum:.2f})")
                                    amount = correct_amount
                            except (ValueError, AttributeError) as e:
                                logger.warning(f"Error calculating correct AD C DISP MIL amount: {e}", exc_info=True)
                        else:
                            logger.warning("No valid gross_salary provided for AD C DISP MIL correction")
                    
                    # Add to earnings with additional metadata
                    earnings.append({
                        'code': code,
                        'description': description,
                        'amount': amount,
                        'reference': str(row[2]).strip() if len(row) > 2 else None,
                        'original_amount': str(row[amount_col]).strip()  # Keep original for debugging
                    })
                    
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Could not parse amount '{amount_str}' in row: {row}. Error: {e}")
                    continue
                
            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping earnings row due to error: {e}")
                continue
        
        # Parse deductions
        deductions = []
        for table in self.tables:
            deductions.extend(self._parse_deductions_table(table))
                
        return earnings, deductions
    
    def _parse_deductions_table(self, table: List[List]) -> List[Dict]:
        """Parse the deductions table
        
        Handles the format where deductions are in the 'Despesas' column with:
        - Column 0: Code (e.g., 'Z99')
        - Column 1: Description (e.g., 'PENS JUDICIARIA')
        - Column 5: Amount (e.g., '3.166,38')
        """
        deductions = []
        
        # Find the header row to determine column indices
        header_row = None
        for row in table:
            if any('Despesas' in str(cell) for cell in row if cell):
                header_row = row
                break
                
        if not header_row:
            return []
            
        # Find the index of the 'Despesas' column
        try:
            amount_col = header_row.index('Despesas (R$)')
        except ValueError:
            # Try to find by partial match if exact match fails
            for i, cell in enumerate(header_row):
                if cell and 'Despesas' in str(cell):
                    amount_col = i
                    break
            else:
                return []
        
        # Process data rows
        for row in table[table.index(header_row) + 1:]:  # Start from row after header
            try:
                # Skip empty rows or rows without a code
                if not row or not row[0] or not row[0].strip():
                    continue
                    
                # Get the amount from the 'Despesas' column
                amount_str = str(row[amount_col]).strip()
                if not amount_str or amount_str == '-':
                    continue
                    
                # Convert amount to float (handle Brazilian number format)
                amount = float(amount_str.replace('.', '').replace(',', '.'))
                
                # Get code and description
                code = str(row[0]).strip()
                description = self._clean_description(row[1]) if len(row) > 1 and row[1] else ""
                
                # Determine category based on description or code
                category = self._determine_deduction_category(code, description)
                
                deductions.append({
                    'code': code,
                    'description': description,
                    'amount': amount,
                    'reference': str(row[2]).strip() if len(row) > 2 else None,
                    'category': category,
                    'is_tax': category == 'tax',
                    'is_pretax': False
                })
                
            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping row due to error: {e}")
                continue
                
        return deductions
    
    def _determine_deduction_category(self, code: str, description: str) -> str:
        """Determine the category of a deduction based on its code and description.
        
        Args:
            code: The deduction code
            description: The deduction description
            
        Returns:
            str: The determined category (tax, insurance, retirement, loan, advance, or other)
        """
        description = (description or '').lower()
        code = (code or '').lower()
        
        # Check for tax-related deductions
        tax_indicators = ['irrf', 'inss', 'imposto', 'contribuição', 'taxa', 'cprb', 'irpf']
        if any(ind in description or ind in code for ind in tax_indicators):
            return 'tax'
            
        # Check for insurance
        insurance_indicators = ['seguro', 'saúde', 'saude', 'plano', 'assistência', 'assistencia']
        if any(ind in description or ind in code for ind in insurance_indicators):
            return 'insurance'
            
        # Check for retirement
        retirement_indicators = ['previdência', 'previdencia', 'aposentadoria', 'fgts']
        if any(ind in description or ind in code for ind in retirement_indicators):
            return 'retirement'
            
        # Check for loans
        loan_indicators = ['empréstimo', 'emprestimo', 'consignado', 'parcela', 'prestação', 'prestacao']
        if any(ind in description or ind in code for ind in loan_indicators):
            return 'loan'
            
        # Check for advances
        advance_indicators = ['adiantamento', 'adto', 'antecipação', 'antecipacao']
        if any(ind in description or ind in code for ind in advance_indicators):
            return 'advance'
            
        # Default to 'other' if no specific category is determined
        return 'other'
    
    def _extract_pattern(self, pattern: str, text: str = None, flags: int = re.IGNORECASE) -> Optional[str]:
        """Extract a value using a regex pattern
        
        Args:
            pattern: The regex pattern to search for
            text: Optional text to search in (defaults to self.text)
            flags: Regex flags to use (defaults to re.IGNORECASE)
            
        Returns:
            The matched text or None if not found
        """
        text = text or self.text
        match = re.search(pattern, text, flags)
        return match.group(1).strip() if match else None
    
    def _extract_date(self, pattern: str) -> Optional[datetime]:
        """Extract and parse a date using a regex pattern"""
        match = re.search(pattern, self.text)
        if not match:
            return None
            
        date_str = match.group(1)
        try:
            # Try different date formats
            for fmt in ('%d/%m/%Y', '%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
        except Exception as e:
            logger.warning(f"Could not parse date: {date_str} - {str(e)}")
            
        return None
    
    def _extract_currency(self, pattern: str) -> Optional[float]:
        """Extract and parse a currency value"""
        match = re.search(pattern, self.text)
        if not match:
            return None
            
        try:
            # Remove thousands separators and replace decimal comma with dot
            value_str = match.group(1).replace('.', '').replace(',', '.')
            return float(value_str)
        except (ValueError, AttributeError) as e:
            logger.warning(f"Could not parse currency: {match.group(1)} - {str(e)}")
            return None
            
    def _clean_description(self, desc: str) -> str:
        """Clean up description text, handling multi-line cases"""
        if not desc:
            return ''
            
        desc = str(desc).strip()
        if '\n' in desc:
            # Take the last line that contains non-whitespace characters
            lines = [line.strip() for line in desc.split('\n') if line.strip()]
            if lines:
                return lines[-1]
        return desc

    def parse(self) -> Dict:
        """Parse the entire payslip and return structured data"""
        if not self.extract_text_and_tables():
            return None
            
        employee_info = self.parse_employee_info()
        payment_info = self.parse_payment_info()
        # Pass the gross_salary from payment_info to parse_earnings_and_deductions
        earnings, deductions = self.parse_earnings_and_deductions(
            gross_salary=payment_info.get('gross_salary') if payment_info else None
        )
        
        return {
            'filename': self.filename,
            'employee': employee_info,
            'payment': payment_info,
            'earnings': earnings,
            'deductions': deductions,
            'raw_text': self.text[:1000] + '...' if self.text else ''  # Store first 1000 chars for debugging
        }

def process_payslip(pdf_path: str) -> Dict:
    """Process a single payslip PDF file
    
    Args:
        pdf_path: Path to the PDF file to process
        
    Returns:
        Dict containing parsed payslip data or None if an error occurs
    """
    import traceback
    try:
        parser = PayslipParser(pdf_path)
        return parser.parse()
    except Exception as e:
        # Log the full traceback for debugging
        error_trace = traceback.format_exc()
        logger.error(f"Error processing {pdf_path}:\n{error_trace}")
        return None
