#!/usr/bin/env python3
"""
DDR AVL PDF Parser - Rockchip DDR Approved Vendor List Parser

This script parses the Rockchip DDR AVL PDF document and extracts:
1. DDR compatibility table with chip support information
2. Application Notes (footnotes like [26])
3. Abbreviation definitions

Output: Structured JSON file for LLM understanding

Key Challenge: The PDF has merged cells for Manufacturer column, where the 
manufacturer name may appear in the MIDDLE of the merged cell group, not at the top.
Solution: Two-pass algorithm - collect all rows first, then backfill manufacturer names.
"""

import pdfplumber
import json
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


# Abbreviation definitions
ABBREVIATIONS = {
    "T/A": "Tested/Approved (已测试/待批准) - The DDR product has been tested and works",
    "S/A": "Sample Approved (样品验证) - Sample has been approved",
    "N/A": "Not Applicable (不适用) - The chip does not support this DDR type",
    "EOL": "End of Life (停产) - The DDR product has been discontinued",
    "√": "Supported (支持) - The chip supports this DDR product",
    "": "Not tested or no data (未测试或无数据)",
}


@dataclass
class ChipSupport:
    """Represents support status for a specific chip"""
    supported: bool
    status: str  # "√", "T/A", "N/A", "", or with note like "√[26]"
    notes: List[str] = field(default_factory=list)


@dataclass
class RawRow:
    """Raw row data before manufacturer assignment"""
    manufacturer_cell: str  # Original cell value (may be empty)
    part_number: str
    product_status: str
    density: str
    organization: str
    ddr_type: str
    package: str
    chip_data: Dict[str, str]  # Chip name -> support status mapping
    category: str = ""  # Category: Consumer, Industrial&Wide Temperature, Automotive
    page_number: int = 0  # Page number this row comes from
    is_separator: bool = False  # True if this is an empty separator row


class DDRAVLParser:
    """Parser for Rockchip DDR Approved Vendor List PDF"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.chips: List[str] = []
        self.application_notes: Dict[str, str] = {}
        self.raw_rows: List[RawRow] = []
        
    def parse(self) -> Dict[str, Any]:
        """Main parsing method"""
        print(f"Opening PDF: {self.pdf_path}")
        
        with pdfplumber.open(self.pdf_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}")
            
            # First pass: extract Application Notes
            self._extract_application_notes(pdf)
            
            # Second pass: extract tables (collect raw rows)
            self._extract_tables(pdf)
            
            # Third pass: assign manufacturers using two-pass backfill
            parts = self._assign_manufacturers()
        
        return self._build_output(parts)
    
    def _extract_application_notes(self, pdf):
        """Extract Application Notes section from the PDF (pages 4-5 before tables start)"""
        print("Extracting Application Notes...")
        
        notes_text = []
        
        # Process first 6 pages (before table pages which start around page 7)
        # Process first 6 pages (before table pages which start around page 7)
        for page_num, page in enumerate(pdf.pages[:6]):
            text = page.extract_text() or ""
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Skip page headers/footers
                if "Rockchip Solutions DDR SDRAM Approved List" in line:
                    continue
                # Skip isolated page numbers
                if re.match(r'^\d+$', line):
                    continue
                    
                # Collect ALL other lines, not just ones starting with [N]
                # This ensures we get multi-line notes
                notes_text.append(line)
        
        # Parse individual notes
        full_text = '\n'.join(notes_text)
        
        # Pattern to match notes like [1], [2], ..., [32]
        note_pattern = r'\[(\d+)\]([^\[]*?)(?=\[\d+\]|$)'
        matches = re.findall(note_pattern, full_text, re.DOTALL)
        
        for num, content in matches:
            # Clean up the content
            content = re.sub(r'\s+', ' ', content).strip()
            if content:
                self.application_notes[num] = content
        
        print(f"Found {len(self.application_notes)} application notes")
    
    def _extract_tables(self, pdf):
        """Extract DDR compatibility tables from all pages"""
        print("Extracting tables...")
        
        header_row = None
        col_map = None
        chip_col_map = {}  # Current page's chip name -> column index mapping
        current_category = ""  # Track current category: Consumer, Industrial, Automotive
        
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            header_found_on_page = False  # Track if header found on current page
            
            for table in tables:
                if not table:
                    continue
                    
                for row in table:
                    if not row:
                        continue
                    
                    # Clean row data
                    row = [self._clean_cell(cell) for cell in row]
                    
                    # Check if this is a header row
                    if self._is_header_row(row):
                        header_row = row
                        col_map = self._build_column_map(row)
                        # Extract chip names from header and get column mapping
                        chip_col_map = self._extract_chips_from_header(row, col_map)
                        print(f"Found header on page {page_num + 1}: {len(self.chips)} chips, {len(chip_col_map)} columns")
                        header_found_on_page = True
                        continue

                    # Check if this is a category row (appears before header row)
                    # Category rows have the category name in first cell, rest are empty/None
                    # Valid categories: Consumer, Industrial&Wide Temperature, Automotive, etc.
                    # CRITICAL: Only detect categories BEFORE the table header on this page
                    # Otherwise legitimate manufacturer rows might be mistaken for categories (e.g. Hynix on page 9)
                    if not header_found_on_page and row and row[0]:
                        first_cell = row[0].strip()
                        # Check if it's a valid category pattern
                        if first_cell and len(first_cell) < 50:
                            # Check if most other cells are empty (category row pattern)
                            non_empty_count = sum(1 for cell in row[1:] if cell and cell.strip())
                            if non_empty_count == 0:
                                # Exclude known non-category patterns
                                lower_cell = first_cell.lower()
                                excluded_words = ['manufacturer', 'part number', 'revision', 'history', 
                                                 'conducted', 'by the', 'note', 'application']
                                if any(word in lower_cell for word in excluded_words):
                                    continue
                                # Exclude if it looks like a manufacturer name (typically manufacturer names detected earlier)
                                # Category names usually contain broader terms like Consumer, Industrial, Automotive
                                category_keywords = ['consumer', 'industrial', 'temperature', 'automotive', 
                                                    'commercial', 'military', 'wide temp']
                                # Accept if it contains a category keyword OR if it's a standalone capitalized word
                                # that doesn't look like a manufacturer
                                if any(kw in lower_cell for kw in category_keywords):
                                    current_category = first_cell
                                    print(f"Found category on page {page_num + 1}: {current_category}")
                                continue
                    
                    # Check if this is a header row
                    if self._is_header_row(row):
                        header_row = row
                        col_map = self._build_column_map(row)
                        # Extract chip names from header and get column mapping
                        chip_col_map = self._extract_chips_from_header(row, col_map)
                        print(f"Found header on page {page_num + 1}: {len(self.chips)} chips, {len(chip_col_map)} columns")
                        continue
                    
                    # Process data rows after header is found
                    if header_row and col_map:
                        raw_row = self._extract_raw_row(row, col_map, chip_col_map, page_num + 1, current_category)
                        if raw_row:
                            self.raw_rows.append(raw_row)
        
        print(f"Collected {len(self.raw_rows)} raw rows")
    
    def _clean_cell(self, cell) -> str:
        """Clean cell content"""
        if cell is None:
            return ""
        
        # Convert to string and clean
        text = str(cell).strip()
        
        # Handle multi-line cells
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _is_header_row(self, row: List[str]) -> bool:
        """Check if a row is a header row"""
        row_text = ' '.join(row).lower()
        
        # Must contain "part number" and "manufacturer"
        has_part_number = "part number" in row_text or "partnumber" in row_text
        has_manufacturer = "manufacturer" in row_text
        
        return has_part_number and has_manufacturer
    
    def _build_column_map(self, header_row: List[str]) -> Dict[str, int]:
        """Build a mapping from column names to indices"""
        col_map = {}
        
        for idx, cell in enumerate(header_row):
            cell_lower = cell.lower().replace(" ", "")
            
            if "manufacturer" in cell_lower:
                col_map["manufacturer"] = idx
            elif "partnumber" in cell_lower:
                col_map["part_number"] = idx
            elif "productstatus" in cell_lower or cell_lower == "status":
                col_map["product_status"] = idx
            elif "density" in cell_lower:
                col_map["density"] = idx
            elif "organization" in cell_lower:
                col_map["organization"] = idx
            elif "type" in cell_lower and "package" not in cell_lower:
                col_map["type"] = idx
            elif "package" in cell_lower:
                col_map["package"] = idx
        
        return col_map
    
    def _extract_chips_from_header(self, header_row: List[str], col_map: Dict[str, int]) -> Dict[str, int]:
        """
        Extract chip names from header row and return chip-to-column-index mapping.
        Also accumulates chips into self.chips for final output.
        """
        # Find where chip columns start (after package)
        chip_start = max(col_map.values()) + 1 if col_map else 7
        
        # Build mapping of chip name -> column index for this page
        current_page_chip_map = {}  # chip_name -> column_index
        
        for idx in range(chip_start, len(header_row)):
            cell = header_row[idx]
            if not cell:
                continue
            
            # Handle multi-line/multi-chip cells like "RV1108/RK3308/RK3308B-S"
            chip_names = re.split(r'[/\s]+', cell)
            for chip in chip_names:
                chip = chip.strip()
                if chip:
                    # Validate it looks like a chip name
                    if re.match(r'^(RK|RV|PX)\d+', chip, re.IGNORECASE):
                        current_page_chip_map[chip] = idx
                        # Add to global chips list if not present
                        if chip not in self.chips:
                            self.chips.append(chip)
        
        return current_page_chip_map
    
    def _extract_raw_row(self, row: List[str], col_map: Dict[str, int], chip_col_map: Dict[str, int], page_number: int, category: str = "") -> Optional[RawRow]:
        """Extract raw row data, including separator markers for empty rows"""
        if len(row) < 2:
            return None
        
        # Get part number
        part_number = ""
        if "part_number" in col_map:
            idx = col_map["part_number"]
            if idx < len(row):
                part_number = row[idx]
        
        # Skip if part number looks like a header or section title
        if part_number and "part number" in part_number.lower():
            return None
        if part_number and part_number.lower() in ["consumer", "industrial", "automotive"]:
            return None
        
        # Skip invalid part numbers that look like PDF text content
        # Valid part numbers typically have alphanumeric patterns, not long sentences
        if part_number:
            # Skip if too long (most part numbers are < 50 chars)
            if len(part_number) > 50:
                return None
            # Skip if contains common words that indicate it's not a part number
            invalid_words = ["production", "ensure", "product", "test", "note", "application"]
            if any(word in part_number.lower() for word in invalid_words):
                return None
            # Skip if it's mostly whitespace or has too many spaces
            if part_number.count(" ") > 5:
                return None
        
        # Get manufacturer cell (may be empty due to merged cells)
        manufacturer_cell = ""
        if "manufacturer" in col_map:
            idx = col_map["manufacturer"]
            if idx < len(row):
                manufacturer_cell = row[idx]
        
        # Check if this is an empty/separator row - only if BOTH part_number and manufacturer are empty
        # This preserves manufacturer-only rows (like Hynix with no part number on that row)
        is_separator = not part_number and not manufacturer_cell
        
        # Get other fields
        def get_field(field_name):
            if field_name in col_map:
                idx = col_map[field_name]
                if idx < len(row):
                    return row[idx]
            return ""
        
        # Get chip data using the chip column mapping
        chip_data = {}
        for chip_name, col_idx in chip_col_map.items():
            if col_idx < len(row):
                chip_data[chip_name] = row[col_idx]
            else:
                chip_data[chip_name] = ""
        
        return RawRow(
            manufacturer_cell=manufacturer_cell,
            part_number=part_number,
            product_status=get_field("product_status"),
            density=get_field("density"),
            organization=get_field("organization"),
            ddr_type=get_field("type"),
            package=get_field("package"),
            chip_data=chip_data,
            category=category,
            page_number=page_number,
            is_separator=is_separator
        )
    
    def _assign_manufacturers(self) -> List[Dict]:
        """
        Two-pass algorithm to assign manufacturers:
        1. Auto-detect manufacturer names from non-empty manufacturer cells
        2. For each manufacturer, find the group boundaries (marked by separator rows)
        3. Assign manufacturer to all parts in the group
        """
        print("Assigning manufacturers...")
        
        # Step 0: Auto-extract manufacturer names from the data
        # Manufacturer names are in the manufacturer_cell and have specific characteristics:
        # - Not empty
        # - Not a part number (doesn't match DDR part patterns)
        # - Not a header text like "Manufacturer"
        # - Not section headers like "Consumer", "Industrial"
        
        def is_valid_manufacturer(name: str) -> bool:
            """Check if a string looks like a valid manufacturer name"""
            if not name or len(name) < 2:
                return False
            
            name_lower = name.lower().strip()
            
            # Skip header and section texts
            skip_patterns = [
                "manufacturer", "part number", "product", "status", "density",
                "organization", "type", "package", "consumer", "industrial",
                "automotive", "wide temperature", "none", "null"
            ]
            if any(skip in name_lower for skip in skip_patterns):
                return False
            
            # Skip if it looks like a part number (contains too many digits or special patterns)
            digit_count = sum(1 for c in name if c.isdigit())
            if digit_count > 3:  # Part numbers typically have many digits
                return False
            
            # Skip if it matches density patterns like "1G bit", "512M bit"
            if re.match(r'^\d+[GMK]?\s*(bit|byte)', name, re.IGNORECASE):
                return False
            
            # Skip if it matches organization patterns like "128Mx16"
            if re.match(r'^\d+M[x×]\d+', name, re.IGNORECASE):
                return False
            
            # Skip if it's a DDR type
            if name_lower in ["ddr", "ddr2", "ddr3", "ddr4", "ddr5", "lpddr3", "lpddr4", "lpddr4x", "lpddr5"]:
                return False
            
            # Skip ball package patterns
            if re.match(r'^\d+ball', name, re.IGNORECASE):
                return False
            
            return True
        
        # Collect all unique manufacturer names from the data
        detected_manufacturers = set()
        for row in self.raw_rows:
            if row.manufacturer_cell and is_valid_manufacturer(row.manufacturer_cell):
                detected_manufacturers.add(row.manufacturer_cell)
        
        print(f"Auto-detected {len(detected_manufacturers)} unique manufacturers")
        
        # Step 1: Find manufacturer positions (only on non-separator rows)
        manufacturer_positions = []  # (index, manufacturer_name)
        for i, row in enumerate(self.raw_rows):
            if row.is_separator:
                continue
            if row.manufacturer_cell and row.manufacturer_cell in detected_manufacturers:
                manufacturer_positions.append((i, row.manufacturer_cell))
        
        print(f"Found {len(manufacturer_positions)} manufacturer markers")
        
        # Step 2: Expand from each manufacturer marker to fill its group
        # Key insight: manufacturer names are VERTICALLY CENTERED in merged cells
        # So we process in REVERSE order (bottom to top) to let each manufacturer
        # claim the rows ABOVE it first (using symmetry from center)
        
        assigned = {}  # row_index -> manufacturer
        
        # Create a set of all manufacturer marker positions for quick lookup
        marker_positions = {pos: mfr for pos, mfr in manufacturer_positions}
        
        # Sort positions in REVERSE order (bottom to top)
        sorted_positions = sorted(manufacturer_positions, key=lambda x: x[0], reverse=True)
        
        # First pass: assign based on nearest marker, stop at empty rows (natural boundaries)
        for idx, (pos, mfr) in enumerate(sorted_positions):
            # Find upper boundary: stop at empty row OR other manufacturer marker
            upper_bound = pos
            for j in range(pos - 1, -1, -1):
                # Stop at another manufacturer marker
                if j in marker_positions and marker_positions[j] != mfr:
                    break
                # Stop at empty row (natural boundary)
                if self.raw_rows[j].is_separator:
                    break
                upper_bound = j
            
            # Find lower boundary: stop at empty row OR other manufacturer marker
            lower_bound = pos
            for j in range(pos + 1, len(self.raw_rows)):
                # Stop at another manufacturer marker
                if j in marker_positions and marker_positions[j] != mfr:
                    break
                # Stop at empty row (natural boundary)
                if self.raw_rows[j].is_separator:
                    break
                lower_bound = j
            
            # Assign all rows in this range to this manufacturer
            for j in range(upper_bound, lower_bound + 1):
                if not self.raw_rows[j].is_separator:
                    # Don't overwrite if already assigned
                    if j not in assigned:
                        assigned[j] = mfr
        
        # Second pass: fill unassigned rows by looking at neighboring assigned rows
        # This handles internal empty rows within a manufacturer group
        # BUT page boundaries are HARD separators - never cross pages
        changed = True
        while changed:
            changed = False
            for i, row in enumerate(self.raw_rows):
                if row.is_separator or i in assigned:
                    continue
                
                current_page = row.page_number
                
                # Look for nearest assigned row above (MUST be on same page)
                up_mfr = None
                up_dist = float('inf')
                up_has_empty = False
                for j in range(i - 1, -1, -1):
                    # HARD STOP at page boundary
                    if self.raw_rows[j].page_number != current_page:
                        break
                    if self.raw_rows[j].is_separator:
                        up_has_empty = True
                        continue
                    if j in assigned:
                        up_mfr = assigned[j]
                        up_dist = i - j
                        break
                
                # Look for nearest assigned row below (MUST be on same page)
                down_mfr = None
                down_dist = float('inf')
                down_has_empty = False
                for j in range(i + 1, len(self.raw_rows)):
                    # HARD STOP at page boundary
                    if self.raw_rows[j].page_number != current_page:
                        break
                    if self.raw_rows[j].is_separator:
                        down_has_empty = True
                        continue
                    if j in assigned:
                        down_mfr = assigned[j]
                        down_dist = j - i
                        break
                
                # Decision logic: prefer neighbor without empty row barrier
                chosen = None
                if up_mfr and down_mfr:
                    if up_mfr == down_mfr:
                        # Both same - definitely assign
                        chosen = up_mfr
                    elif up_has_empty and not down_has_empty:
                        # Empty row above, clear path below - prefer below
                        chosen = down_mfr
                    elif down_has_empty and not up_has_empty:
                        # Empty row below, clear path above - prefer above
                        chosen = up_mfr
                    elif down_dist < up_dist:
                        # Both have/don't have empty rows, prefer closer
                        chosen = down_mfr
                    else:
                        chosen = up_mfr
                elif up_mfr:
                    chosen = up_mfr
                elif down_mfr:
                    chosen = down_mfr
                
                if chosen:
                    assigned[i] = chosen
                    changed = True
        
        # Step 3: Build parts list
        parts = []
        for i, row in enumerate(self.raw_rows):
            if row.is_separator:
                continue
            
            manufacturer = assigned.get(i, row.manufacturer_cell or "Unknown")
            
            # Build compatibility dict from chip_data (which is now a dict)
            compatibility = {}
            for chip_name, status in row.chip_data.items():
                support = self._parse_support_status(status)
                compatibility[chip_name] = {
                    "supported": support.supported,
                    "status": support.status,
                    "notes": support.notes
                }
            
            parts.append({
                "category": row.category if row.category else "Unknown",
                "manufacturer": manufacturer,
                "part_number": row.part_number,
                "product_status": row.product_status if row.product_status else None,
                "density": row.density if row.density else None,
                "organization": row.organization if row.organization else None,
                "type": row.ddr_type if row.ddr_type else None,
                "package": row.package if row.package else None,
                "compatibility": compatibility
            })
        
        print(f"Assigned manufacturers to {len(parts)} parts")
        return parts
    
    def _parse_support_status(self, status: str) -> ChipSupport:
        """Parse support status string into ChipSupport object"""
        status = status.strip()
        
        # Extract notes like [26]
        notes = re.findall(r'\[(\d+)\]', status)
        
        # Determine support status
        if not status:
            return ChipSupport(supported=False, status="", notes=notes)
        
        if "√" in status or "[PASS]" in status:
            return ChipSupport(supported=True, status="√", notes=notes)
        
        if "T/A" in status.upper():
            return ChipSupport(supported=True, status="T/A", notes=notes)
        
        if "S/A" in status.upper():
            return ChipSupport(supported=True, status="S/A", notes=notes)
        
        if "N/A" in status.upper():
            return ChipSupport(supported=False, status="N/A", notes=notes)
        
        # Any other content might indicate support (could be a checkmark variant)
        if status and status not in ["None", "null"]:
            return ChipSupport(supported=True, status=status, notes=notes)
        
        return ChipSupport(supported=False, status="", notes=notes)
    
    def _build_output(self, parts: List[Dict]) -> Dict[str, Any]:
        """Build the final output dictionary"""
        return {
            "metadata": {
                "source": os.path.basename(self.pdf_path),
                "version": self._extract_version(),
                "total_parts": len(parts),
                "total_chips": len(self.chips),
                "abbreviations": ABBREVIATIONS
            },
            "chips": self.chips,
            "parts": parts,
            "application_notes": self.application_notes
        }
    
    def _extract_version(self) -> str:
        """Extract version from filename"""
        match = re.search(r'ver(\d+\.\d+)', self.pdf_path)
        if match:
            return match.group(1)
        return "unknown"


def query_part_support(data: Dict, part_number: str) -> Dict:
    """Query which chips support a specific DDR part"""
    result = {
        "part_number": part_number,
        "manufacturer": None,
        "supported_chips": [],
        "notes": {}
    }
    
    for part in data["parts"]:
        if part["part_number"] == part_number:
            result["manufacturer"] = part["manufacturer"]
            
            for chip, support in part["compatibility"].items():
                if support["supported"]:
                    result["supported_chips"].append(chip)
                    if support["notes"]:
                        for note_id in support["notes"]:
                            if note_id in data["application_notes"]:
                                result["notes"][note_id] = data["application_notes"][note_id]
            break
    
    return result


def query_chip_compatibility(data: Dict, chip: str, part_number: str) -> Dict:
    """Query if a chip supports a specific DDR part"""
    result = {
        "chip": chip,
        "part_number": part_number,
        "supported": False,
        "status": None,
        "notes": {}
    }
    
    # Try exact match first
    for part in data["parts"]:
        if part["part_number"] == part_number:
            if chip in part["compatibility"]:
                support = part["compatibility"][chip]
                result["supported"] = support["supported"]
                result["status"] = support["status"]
                
                for note_id in support.get("notes", []):
                    if note_id in data["application_notes"]:
                        result["notes"][note_id] = data["application_notes"][note_id]
            break
    
    # If not found, try partial chip name match (e.g., "3588" matches "RK3588")
    if result["status"] is None:
        for part in data["parts"]:
            if part["part_number"] == part_number:
                for chip_name, support in part["compatibility"].items():
                    if chip in chip_name or chip_name in chip:
                        result["supported"] = support["supported"]
                        result["status"] = support["status"]
                        result["chip"] = chip_name  # Return actual chip name
                        
                        for note_id in support.get("notes", []):
                            if note_id in data["application_notes"]:
                                result["notes"][note_id] = data["application_notes"][note_id]
                        break
                break
    
    return result


def list_manufacturer_parts(data: Dict, manufacturer: str) -> List[str]:
    """List all parts from a specific manufacturer"""
    parts = []
    for part in data["parts"]:
        if manufacturer.lower() in part["manufacturer"].lower():
            parts.append(part["part_number"])
    return parts


def main():
    # PDF path - look for DDR AVL PDF in current directory first, then script directory
    current_dir = Path.cwd()
    script_dir = Path(__file__).parent

    # Try to find DDR AVL PDF in current directory first
    pdf_files = list(current_dir.glob("Rockchip_DDR_Approved_Vendor_List_ver*.pdf"))

    if pdf_files:
        pdf_path = pdf_files[0]  # Use the first match
        print(f"Found PDF in current directory: {pdf_path}")
    else:
        # Try to find in fae_doc_49 subdirectory
        fae_doc_dir = current_dir / "fae_doc_49"
        if fae_doc_dir.exists():
            pdf_files = list(fae_doc_dir.glob("Rockchip_DDR_Approved_Vendor_List_ver*.pdf"))
            if pdf_files:
                pdf_path = pdf_files[0]
                print(f"Found PDF in fae_doc_49 directory: {pdf_path}")
            else:
                # Fall back to script directory
                pdf_path = script_dir / "Rockchip_DDR_Approved_Vendor_List_ver3.01.pdf"
                print(f"Using PDF from script directory: {pdf_path}")
        else:
            # Fall back to script directory
            pdf_path = script_dir / "Rockchip_DDR_Approved_Vendor_List_ver3.01.pdf"
            print(f"Using PDF from script directory: {pdf_path}")
    
    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return
    
    # Parse PDF
    parser = DDRAVLParser(str(pdf_path))
    data = parser.parse()
    
    # Save JSON output to current directory
    output_path = current_dir / "ddr_avl_data.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nOutput saved to: {output_path}")
    print(f"Total parts extracted: {data['metadata']['total_parts']}")
    print(f"Total chips: {data['metadata']['total_chips']}")
    print(f"Application notes: {len(data['application_notes'])}")
    
    # Test queries
    print("\n" + "="*60)
    print("Test Query 1: W9751G6KB-25")
    print("="*60)
    result = query_part_support(data, "W9751G6KB-25")
    print(f"Manufacturer: {result['manufacturer']}")
    print(f"Supported chips: {result['supported_chips']}")
    
    print("\n" + "="*60)
    print("Test Query 2: RK3588 + A8XBGH52ABA-PM")
    print("="*60)
    result = query_chip_compatibility(data, "RK3588", "A8XBGH52ABA-PM")
    print(f"Supported: {result['supported']}")
    print(f"Status: {result['status']}")
    if result['notes']:
        print("Notes:")
        for note_id, note_text in result['notes'].items():
            print(f"  [{note_id}] {note_text[:100]}...")
    
    print("\n" + "="*60)
    print("Test Query 3: Winbond parts")
    print("="*60)
    winbond_parts = list_manufacturer_parts(data, "Winbond")
    print(f"Total Winbond parts: {len(winbond_parts)}")
    for part in winbond_parts:
        print(f"  - {part}")
    
    # Expected Winbond parts for validation
    expected_winbond = [
        "W9751G6KB-25", "W9751G6NB-25", "W971GG6SB-18", "W631GG6KB-12",
        "W631GG6MB-12", "W631GU6NB-12", "W631GU6RB-11", "W632GG6KB-15",
        "W632GG6NB-12", "W632GU6NB-09", "W632GU6QB-09", "W632GU6RB-**",
        "W634GU6QB-11", "W634GU6QB-09", "W634GU6RB-**", "W638GU6QB-11I",
        "W638GU6QB-09", "W664GG6RB-06", "W66BL6NBUAFI", "W66DP2RQQA*J"
    ]
    
    print("\n" + "="*60)
    print("Validation: Expected Winbond parts")
    print("="*60)
    found = set(winbond_parts)
    missing = [p for p in expected_winbond if p not in found]
    extra = [p for p in winbond_parts if p not in expected_winbond]
    
    if missing:
        print(f"Missing parts ({len(missing)}):")
        for p in missing:
            print(f"  - {p}")
    else:
        print("All expected parts found!")
    
        print(f"Extra parts ({len(extra)}):") 
        for p in extra:
            print(f"  - {p}")
    
    # Additional validation tests
    print("\n" + "="*60)
    print("Validation: Manufacturer Assignment")
    print("="*60)
    
    validation_passed = True
    
    # Test 1: Samsung K4ABG165WA-MC should be Samsung
    samsung_test = [p for p in data['parts'] if 'K4ABG165WA-MC' in p['part_number']]
    if samsung_test and samsung_test[0]['manufacturer'] == 'Samsung':
        print("[PASS] K4ABG165WA-MC correctly assigned to Samsung")
    else:
        print("[FAIL] K4ABG165WA-MC should be Samsung, got:", samsung_test[0]['manufacturer'] if samsung_test else "Not found")
        validation_passed = False
    
    # Test 2: Hynix H5PS1G63CFP should be Hynix
    hynix_test = [p for p in data['parts'] if 'H5PS1G63CFP' in p['part_number']]
    if hynix_test and hynix_test[0]['manufacturer'] == 'Hynix':
        print("[PASS] H5PS1G63CFP correctly assigned to Hynix")
    else:
        print("[FAIL] H5PS1G63CFP should be Hynix, got:", hynix_test[0]['manufacturer'] if hynix_test else "Not found")
        validation_passed = False
    
    # Test 3: Micron MT40A2G16SKL-062E should be Micron
    micron_test = [p for p in data['parts'] if 'MT40A2G16SKL-062E' in p['part_number']]
    if micron_test and micron_test[0]['manufacturer'] == 'Micron':
        print("[PASS] MT40A2G16SKL-062E correctly assigned to Micron")
    else:
        print("[FAIL] MT40A2G16SKL-062E should be Micron, got:", micron_test[0]['manufacturer'] if micron_test else "Not found")
        validation_passed = False
    
    # Test 4: BIWIN BWSRGX32H2A should be BIWIN
    biwin_test = [p for p in data['parts'] if 'BWSRGX32H2A' in p['part_number']]
    if biwin_test and biwin_test[0]['manufacturer'] == 'BIWIN':
        print("[PASS] BWSRGX32H2A correctly assigned to BIWIN")
    else:
        print("[FAIL] BWSRGX32H2A should be BIWIN, got:", biwin_test[0]['manufacturer'] if biwin_test else "Not found")
        validation_passed = False
    
    # Test 5: Unknown count should be low (< 5)
    unknown_parts = [p for p in data['parts'] if p['manufacturer'] == 'Unknown']
    if len(unknown_parts) < 5:
        print(f"[PASS] Unknown manufacturer count: {len(unknown_parts)} (acceptable)")
    else:
        print(f"[FAIL] Too many Unknown manufacturers: {len(unknown_parts)}")
        validation_passed = False
    
    # Test 6: No invalid part numbers (containing "production", "ensure", etc.)
    invalid_parts = [p for p in data['parts'] if any(word in p['part_number'].lower() 
                     for word in ['production', 'ensure', 'product', 'test', 'note'])]
    if len(invalid_parts) == 0:
        print("[PASS] No invalid part numbers detected")
    else:
        print(f"[FAIL] Invalid part numbers found: {[p['part_number'] for p in invalid_parts]}")
        validation_passed = False
    
    print("\n" + "="*60)
    print("Validation: Category Classification")
    print("="*60)
    
    # Category distribution
    categories = {}
    for p in data['parts']:
        cat = p.get('category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} parts")
    
    # Test 7: All three expected categories should exist
    expected_categories = ['Consumer', 'Industrial&Wide Temperature', 'Automotive']
    for cat in expected_categories:
        if cat in categories:
            print(f"[PASS] Category '{cat}' found")
        else:
            print(f"[FAIL] Category '{cat}' missing")
            validation_passed = False
    
    # Test 8: No "Unknown" category (should all be assigned)
    if 'Unknown' in categories:
        print(f"[FAIL] {categories['Unknown']} parts have Unknown category")
        validation_passed = False
    else:
        print("[PASS] All parts have valid categories")
    
    print("\n" + "="*60)
    if validation_passed:
        print("ALL VALIDATION TESTS PASSED!")
    else:
        print("SOME VALIDATION TESTS FAILED - please review")
    print("="*60)


if __name__ == "__main__":
    main()

