#!/usr/bin/env python3
"""
eMMC AVL PDF Parser - Rockchip eMMC Approved Vendor List Parser

This script parses the Rockchip eMMC AVL PDF document and extracts:
1. eMMC compatibility table with chip support information
2. Symbol definitions (√, T/A, S/A, D/A, N/A)

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


# Symbol definitions
SYMBOLS = {
    "√": "Fully Tested, Applicable and Mass Production (已测试/批准生产)",
    "T/A": "Fully Tested, Applicable and Ready for Mass Production (已测试/待批准生产)",
    "S/A": "The Samples have Passed the Reliability Test. However, the Platform Compatibility Test was also required before Mass Production (样品验证)",
    "D/A": "Datasheet Applicable, Need Sample to Test (数据表适用，需要样品测试)",
    "N/A": "Not Applicable (不适用)",
    "": "Not tested or no data (未测试或无数据)",
}


@dataclass
class ChipSupport:
    """Represents support status for a specific chip"""
    supported: bool
    status: str  # "√", "T/A", "S/A", "D/A", "N/A", or ""


@dataclass
class RawRow:
    """Raw row data before manufacturer assignment"""
    manufacturer_cell: str  # Original cell value (may be empty)
    part_number: str
    device_size: str
    byte_size: str
    process: str
    version: str
    pkg_size: str
    remark: str
    chip_data: Dict[str, str]  # Chip name -> support status mapping
    page_number: int = 0  # Page number this row comes from
    is_separator: bool = False  # True if this is an empty separator row


class EMMCAVLParser:
    """Parser for Rockchip eMMC Approved Vendor List PDF"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.chips: List[str] = []
        self.symbols: Dict[str, str] = SYMBOLS.copy()
        self.raw_rows: List[RawRow] = []
        
    def parse(self) -> Dict[str, Any]:
        """Main parsing method"""
        print(f"Opening PDF: {self.pdf_path}")
        
        with pdfplumber.open(self.pdf_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}")
            
            # First pass: extract symbol definitions (optional, we have defaults)
            # Skip for now as symbols are well-defined
            
            # Second pass: extract tables (collect raw rows)
            # Tables start from page 8 (index 7)
            self._extract_tables(pdf)
            
            # Third pass: assign manufacturers using two-pass backfill
            parts = self._assign_manufacturers()
        
        return self._build_output(parts)
    
    def _extract_tables(self, pdf):
        """Extract eMMC compatibility tables from all pages"""
        print("Extracting tables...")
        
        header_row = None
        col_map = None
        chip_col_map = {}  # Current page's chip name -> column index mapping
        
        # Start from page 8 (index 7) where tables begin
        for page_num, page in enumerate(pdf.pages[7:], start=7):
            tables = page.extract_tables()
            
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
                        print(f"Found header on page {page_num + 1}: {len(self.chips)} total chips, {len(chip_col_map)} columns on this page")
                        continue
                    
                    # Process data rows after header is found
                    if header_row and col_map:
                        raw_row = self._extract_raw_row(row, col_map, chip_col_map, page_num + 1)
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
            cell_lower = cell.lower().replace(" ", "").replace("\n", "")
            
            if "manufacturer" in cell_lower:
                col_map["manufacturer"] = idx
            elif "partnumber" in cell_lower:
                col_map["part_number"] = idx
            elif "devicesize" in cell_lower or "device" in cell_lower and "bits" in cell_lower:
                col_map["device_size"] = idx
            elif "bytesize" in cell_lower or (cell_lower == "byte" or "byte" in cell_lower and "size" in cell_lower):
                col_map["byte_size"] = idx
            elif "process" in cell_lower:
                col_map["process"] = idx
            elif "version" in cell_lower:
                col_map["version"] = idx
            elif "pkgsize" in cell_lower or "pkg" in cell_lower:
                col_map["pkg_size"] = idx
            elif "remark" in cell_lower:
                col_map["remark"] = idx
        
        return col_map
    
    def _extract_chips_from_header(self, header_row: List[str], col_map: Dict[str, int]) -> Dict[str, int]:
        """
        Extract chip names from header row and return chip-to-column-index mapping.
        Also accumulates chips into self.chips for final output.
        
        Note: Each chip column may contain multiple chip names separated by newlines.
        We extract the FIRST (primary) chip name from each column for the mapping,
        but add ALL chip names to self.chips list.
        """
        # Find where chip columns start (after pkg_size, before remark)
        chip_start = 7  # Default start after standard columns
        if "pkg_size" in col_map:
            chip_start = col_map["pkg_size"] + 1
        
        # Find where chip columns end (before remark or at end)
        chip_end = len(header_row)
        if "remark" in col_map:
            chip_end = col_map["remark"]
        
        # Build mapping of chip name -> column index for this page
        current_page_chip_map = {}  # chip_name -> column_index
        
        for idx in range(chip_start, chip_end):
            if idx >= len(header_row):
                break
                
            cell = header_row[idx]
            if not cell:
                continue
            
            # Skip None or empty cells
            if cell == "None" or not cell.strip():
                continue
            
            # Handle multi-line chip names (newlines in cell)
            # Each column may have multiple chips like "RV1126\nRV1109\nRV1126B"
            chip_names = [name.strip() for name in cell.split('\n') if name.strip()]
            
            if not chip_names:
                continue
            
            # Use the FIRST chip name as the primary identifier for this column
            primary_chip = chip_names[0]
            
            # Add ALL chip names to global list and validate they look like chip names
            for chip in chip_names:
                # Validate it looks like a chip name (RK*, RV*, PX*)
                # Also handle RK3399/RK3399PRO format
                chip_parts = re.split(r'[/]', chip)
                for chip_part in chip_parts:
                    chip_part = chip_part.strip()
                    if re.match(r'^(RK|RV|RKPX|PX)\d+', chip_part, re.IGNORECASE):
                        if chip_part not in self.chips:
                            self.chips.append(chip_part)
            
            # Map the primary chip to this column index
            if re.match(r'^(RK|RV|RKPX|PX)\d+', primary_chip, re.IGNORECASE):
                current_page_chip_map[primary_chip] = idx
        
        return current_page_chip_map
    
    def _extract_raw_row(self, row: List[str], col_map: Dict[str, int], chip_col_map: Dict[str, int], page_number: int) -> Optional[RawRow]:
        """Extract raw row data, including separator markers for empty rows"""
        if len(row) < 2:
            return None
        
        # Get part number
        part_number = ""
        if "part_number" in col_map:
            idx = col_map["part_number"]
            if idx < len(row):
                part_number = row[idx]
        
        # Skip if part number looks like a header
        if part_number and "part number" in part_number.lower():
            return None
        
        # Skip invalid part numbers that are too long or contain common words
        if part_number:
            if len(part_number) > 100:
                return None
            invalid_words = ["production", "test", "note", "applicable", "version"]
            if any(word in part_number.lower() for word in invalid_words):
                return None
        
        # Get manufacturer cell (may be empty due to merged cells)
        manufacturer_cell = ""
        if "manufacturer" in col_map:
            idx = col_map["manufacturer"]
            if idx < len(row):
                manufacturer_cell = row[idx]
        
        # Check if this is an empty/separator row
        is_separator = not part_number and not manufacturer_cell
        
        # Get other fields
        def get_field(field_name):
            if field_name in col_map:
                idx = col_map[field_name]
                if idx < len(row):
                    return row[idx]
            return ""
        
        # Get remark field - merge Col 22 (remark) and Col 23 (additional info) if both exist
        remark = get_field("remark")
        # Col 23 is the last column (after remark), check if it has content
        if "remark" in col_map:
            remark_idx = col_map["remark"]
            # Check if there's a column after remark (Col 23)
            if remark_idx + 1 < len(row):
                additional_info = row[remark_idx + 1]
                if additional_info and additional_info.strip() and additional_info.strip() not in ["", "None", "null", "-"]:
                    # Merge with remark
                    if remark and remark.strip():
                        remark = f"{remark}; {additional_info.strip()}"
                    else:
                        remark = additional_info.strip()
        
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
            device_size=get_field("device_size"),
            byte_size=get_field("byte_size"),
            process=get_field("process"),
            version=get_field("version"),
            pkg_size=get_field("pkg_size"),
            remark=remark,
            chip_data=chip_data,
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
        
        def is_valid_manufacturer(name: str) -> bool:
            """Check if a string looks like a valid manufacturer name"""
            if not name or len(name) < 2:
                return False
            
            name_lower = name.lower().strip()
            
            # Skip header texts
            skip_patterns = [
                "manufacturer", "part number", "device", "size", "process",
                "version", "package", "pkg", "remark", "none", "null"
            ]
            if any(skip in name_lower for skip in skip_patterns):
                return False
            
            # Skip if it looks like a part number (contains too many digits)
            digit_count = sum(1 for c in name if c.isdigit())
            if digit_count > 3:
                return False
            
            # Skip if it matches size patterns
            if re.match(r'^\d+[GMK]?[Bb]', name):
                return False
            
            return True
        
        # Collect all unique manufacturer names from the data
        detected_manufacturers = set()
        for row in self.raw_rows:
            if row.manufacturer_cell and is_valid_manufacturer(row.manufacturer_cell):
                detected_manufacturers.add(row.manufacturer_cell)
        
        print(f"Auto-detected {len(detected_manufacturers)} unique manufacturers")
        
        # Find manufacturer positions
        manufacturer_positions = []
        for i, row in enumerate(self.raw_rows):
            if row.is_separator:
                continue
            if row.manufacturer_cell and row.manufacturer_cell in detected_manufacturers:
                manufacturer_positions.append((i, row.manufacturer_cell))
        
        print(f"Found {len(manufacturer_positions)} manufacturer markers")
        
        # Assign manufacturers using two-pass algorithm
        assigned = {}  # row_index -> manufacturer
        
        marker_positions = {pos: mfr for pos, mfr in manufacturer_positions}
        sorted_positions = sorted(manufacturer_positions, key=lambda x: x[0], reverse=True)
        
        # First pass: assign based on nearest marker, stop at empty rows
        for idx, (pos, mfr) in enumerate(sorted_positions):
            # Find upper boundary
            upper_bound = pos
            for j in range(pos - 1, -1, -1):
                if j in marker_positions and marker_positions[j] != mfr:
                    break
                if self.raw_rows[j].is_separator:
                    break
                upper_bound = j
            
            # Find lower boundary
            lower_bound = pos
            for j in range(pos + 1, len(self.raw_rows)):
                if j in marker_positions and marker_positions[j] != mfr:
                    break
                if self.raw_rows[j].is_separator:
                    break
                lower_bound = j
            
            # Assign all rows in this range
            for j in range(upper_bound, lower_bound + 1):
                if not self.raw_rows[j].is_separator:
                    if j not in assigned:
                        assigned[j] = mfr
        
        # Second pass: fill unassigned rows by looking at neighbors (same page only)
        changed = True
        while changed:
            changed = False
            for i, row in enumerate(self.raw_rows):
                if row.is_separator or i in assigned:
                    continue
                
                current_page = row.page_number
                
                # Look up
                up_mfr = None
                for j in range(i - 1, -1, -1):
                    if self.raw_rows[j].page_number != current_page:
                        break
                    if j in assigned:
                        up_mfr = assigned[j]
                        break
                
                # Look down
                down_mfr = None
                for j in range(i + 1, len(self.raw_rows)):
                    if self.raw_rows[j].page_number != current_page:
                        break
                    if j in assigned:
                        down_mfr = assigned[j]
                        break
                
                # Assign if neighbors agree
                if up_mfr and down_mfr and up_mfr == down_mfr:
                    assigned[i] = up_mfr
                    changed = True
                elif up_mfr and not down_mfr:
                    assigned[i] = up_mfr
                    changed = True
                elif down_mfr and not up_mfr:
                    assigned[i] = down_mfr
                    changed = True
        
        # Build parts list
        parts = []
        for i, row in enumerate(self.raw_rows):
            if row.is_separator:
                continue
            
            manufacturer = assigned.get(i, row.manufacturer_cell or "Unknown")
            
            # Build compatibility dict from chip_data
            compatibility = {}
            for chip_name, status in row.chip_data.items():
                support = self._parse_support_status(status)
                compatibility[chip_name] = {
                    "supported": support.supported,
                    "status": support.status
                }
            
            parts.append({
                "manufacturer": manufacturer,
                "part_number": row.part_number,
                "device_size": row.device_size if row.device_size else None,
                "byte_size": row.byte_size if row.byte_size else None,
                "process": row.process if row.process else None,
                "version": row.version if row.version else None,
                "pkg_size": row.pkg_size if row.pkg_size else None,
                "remark": row.remark if row.remark else None,
                "compatibility": compatibility
            })
        
        print(f"Assigned manufacturers to {len(parts)} parts")
        return parts
    
    def _parse_support_status(self, status: str) -> ChipSupport:
        """Parse support status string into ChipSupport object"""
        status = status.strip()
        
        # Determine support status
        if not status:
            return ChipSupport(supported=False, status="")
        
        if "√" in status:
            return ChipSupport(supported=True, status="√")
        
        if "T/A" in status.upper():
            return ChipSupport(supported=True, status="T/A")
        
        if "S/A" in status.upper():
            return ChipSupport(supported=True, status="S/A")
        
        if "D/A" in status.upper():
            return ChipSupport(supported=True, status="D/A")
        
        if "N/A" in status.upper():
            return ChipSupport(supported=False, status="N/A")
        
        # Any other content might indicate support
        if status and status not in ["None", "null"]:
            return ChipSupport(supported=True, status=status)
        
        return ChipSupport(supported=False, status="")
    
    def _build_output(self, parts: List[Dict]) -> Dict[str, Any]:
        """Build the final output dictionary"""
        return {
            "metadata": {
                "source": os.path.basename(self.pdf_path),
                "version": self._extract_version(),
                "total_parts": len(parts),
                "total_chips": len(self.chips),
                "symbols": self.symbols
            },
            "chips": self.chips,
            "parts": parts
        }
    
    def _extract_version(self) -> str:
        """Extract version from filename"""
        match = re.search(r'[Vv]er(\d+\.\d+)', self.pdf_path)
        if match:
            return match.group(1)
        return "unknown"


def query_part_support(data: Dict, part_number: str) -> Dict:
    """Query which chips support a specific eMMC part"""
    result = {
        "part_number": part_number,
        "manufacturer": None,
        "supported_chips": []
    }
    
    for part in data["parts"]:
        if part["part_number"] == part_number:
            result["manufacturer"] = part["manufacturer"]
            
            for chip, support in part["compatibility"].items():
                if support["supported"]:
                    result["supported_chips"].append(chip)
            break
    
    return result


def query_chip_compatibility(data: Dict, chip: str, part_number: str) -> Dict:
    """Query if a chip supports a specific eMMC part"""
    result = {
        "chip": chip,
        "part_number": part_number,
        "supported": False,
        "status": None
    }
    
    # Try exact match first
    for part in data["parts"]:
        if part["part_number"] == part_number:
            if chip in part["compatibility"]:
                support = part["compatibility"][chip]
                result["supported"] = support["supported"]
                result["status"] = support["status"]
            break
    
    # If not found, try partial chip name match
    if result["status"] is None:
        for part in data["parts"]:
            if part["part_number"] == part_number:
                for chip_name, support in part["compatibility"].items():
                    if chip in chip_name or chip_name in chip:
                        result["supported"] = support["supported"]
                        result["status"] = support["status"]
                        result["chip"] = chip_name
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
    # PDF path
    pdf_path = Path(__file__).parent / "Rockchip_EMMC_Approved_Vendor_List_Ver1.93.pdf"
    
    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return
    
    # Parse PDF
    parser = EMMCAVLParser(str(pdf_path))
    data = parser.parse()
    
    # Save JSON output
    output_path = pdf_path.parent / "emmc_avl_data.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\nOutput saved to: {output_path}")
    print(f"Total parts extracted: {data['metadata']['total_parts']}")
    print(f"Total chips: {data['metadata']['total_chips']}")
    print(f"Chips: {', '.join(data['chips'])}")
    
    # Validation tests
    print("\n" + "="*60)
    print("Validation: Manufacturer Assignment")
    print("="*60)
    
    validation_passed = True
    
    # Test 1: Micron MTFC16GAPALBH-IT should be Micron
    micron_test = [p for p in data['parts'] if 'MTFC16GAPALBH-IT' in p['part_number']]
    if micron_test and micron_test[0]['manufacturer'] == 'Micron':
        print("[PASS] MTFC16GAPALBH-IT correctly assigned to Micron")
    else:
        print("[FAIL] MTFC16GAPALBH-IT should be Micron, got:", micron_test[0]['manufacturer'] if micron_test else "Not found")
        validation_passed = False
    
    # Test 2: KIOXIA THGBMHG6C1LBAIL should be KIOXIA
    kioxia_test = [p for p in data['parts'] if 'THGBMHG6C1LBAIL' in p['part_number']]
    if kioxia_test and kioxia_test[0]['manufacturer'] == 'KIOXIA':
        print("[PASS] THGBMHG6C1LBAIL correctly assigned to KIOXIA")
    else:
        print("[FAIL] THGBMHG6C1LBAIL should be KIOXIA, got:", kioxia_test[0]['manufacturer'] if kioxia_test else "Not found")
        validation_passed = False
    
    # Test 3: SanDisk SDINBDG4-8GB should be SanDisk / WD
    sandisk_test = [p for p in data['parts'] if 'SDINBDG4-8GB' in p['part_number']]
    if sandisk_test and 'SanDisk' in sandisk_test[0]['manufacturer']:
        print(f"[PASS] SDINBDG4-8GB correctly assigned to {sandisk_test[0]['manufacturer']}")
    else:
        print("[FAIL] SDINBDG4-8GB should be SanDisk/WD, got:", sandisk_test[0]['manufacturer'] if sandisk_test else "Not found")
        validation_passed = False
    
    # Test 4: Unknown count should be low
    unknown_parts = [p for p in data['parts'] if p['manufacturer'] == 'Unknown']
    if len(unknown_parts) < 5:
        print(f"[PASS] Unknown manufacturer count: {len(unknown_parts)} (acceptable)")
    else:
        print(f"[FAIL] Too many Unknown manufacturers: {len(unknown_parts)}")
        validation_passed = False
    
    # Test 5: Reasonable part count (should be 200+)
    if len(data['parts']) > 200:
        print(f"[PASS] Total parts: {len(data['parts'])} (reasonable)")
    else:
        print(f"[WARN] Low part count: {len(data['parts'])}")
    
    # Test 6: Reasonable chip count (should be 15-20)
    if 10 <= len(data['chips']) <= 25:
        print(f"[PASS] Total chips: {len(data['chips'])} (reasonable)")
    else:
        print(f"[WARN] Unexpected chip count: {len(data['chips'])}")
    
    print("\n" + "="*60)
    if validation_passed:
        print("ALL VALIDATION TESTS PASSED!")
    else:
        print("SOME VALIDATION TESTS FAILED - please review")
    print("="*60)
    
    # Test queries
    print("\n" + "="*60)
    print("Test Query 1: MTFC16GAPALBH-IT")
    print("="*60)
    result = query_part_support(data, "MTFC16GAPALBH-IT")
    print(f"Manufacturer: {result['manufacturer']}")
    print(f"Supported chips ({len(result['supported_chips'])}): {', '.join(result['supported_chips'][:5])}...")
    
    print("\n" + "="*60)
    print("Test Query 2: RK3588 + SDINBDG4-32GB")
    print("="*60)
    result = query_chip_compatibility(data, "RK3588", "SDINBDG4-32GB")
    print(f"Supported: {result['supported']}")
    print(f"Status: {result['status']}")


if __name__ == "__main__":
    main()
