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
