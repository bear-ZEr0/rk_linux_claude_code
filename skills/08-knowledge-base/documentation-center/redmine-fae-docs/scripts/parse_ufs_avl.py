#!/usr/bin/env python3
"""
UFS AVL PDF Parser - Rockchip UFS Approved Vendor List Parser

This script parses the Rockchip UFS AVL PDF document and extracts:
1. UFS compatibility table with chip support information
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
    vcc: str  # VCC voltage (V)
    vccq: str  # VCCQ voltage (V)
    vccq2: str  # VCCQ2 voltage (V)
    temp: str  # Temperature range (°C)
    remark: str
    chip_data: Dict[str, str]  # Chip name -> support status mapping
    page_number: int = 0  # Page number this row comes from
    is_separator: bool = False  # True if this is an empty separator row


class UFSAVLParser:
    """Parser for Rockchip UFS Approved Vendor List PDF"""

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
            # Tables start from page 4 (index 3)
            self._extract_tables(pdf)

            # Third pass: assign manufacturers using two-pass backfill
            parts = self._assign_manufacturers()

        return self._build_output(parts)

    def _extract_tables(self, pdf):
        """Extract UFS compatibility tables from all pages"""
        print("Extracting tables...")

        header_row = None
        col_map = None
        chip_col_map = {}  # Current page's chip name -> column index mapping

        # Start from page 4 (index 3) where tables begin
        for page_num, page in enumerate(pdf.pages[3:], start=3):
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
            elif "vcc" in cell_lower and "vccq" not in cell_lower:
                col_map["vcc"] = idx
            elif "vccq2" in cell_lower:
                col_map["vccq2"] = idx
            elif "vccq" in cell_lower and "vccq2" not in cell_lower:
                col_map["vccq"] = idx
            elif "temp" in cell_lower:
                col_map["temp"] = idx
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
        # Find where chip columns start (after temp, before remark)
        chip_start = 10  # Default start after standard columns
        if "temp" in col_map:
            chip_start = col_map["temp"] + 1

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
            # Each column may have multiple chips like "RK3576\nRK3588"
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

        remark = get_field("remark")

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
            vcc=get_field("vcc"),
            vccq=get_field("vccq"),
            vccq2=get_field("vccq2"),
            temp=get_field("temp"),
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
                "version", "package", "pkg", "remark", "none", "null", "temp", "vcc"
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
                "vcc": row.vcc if row.vcc else None,
                "vccq": row.vccq if row.vccq else None,
                "vccq2": row.vccq2 if row.vccq2 else None,
                "temp": row.temp if row.temp else None,
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
        match = re.search(r'[Vv]er(\\d+\\.\\d+)', self.pdf_path)
        if match:
            return match.group(1)
        return "unknown"


def query_part_support(data: Dict, part_number: str) -> Dict:
    """Query which chips support a specific UFS part"""
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
    """Query if a chip supports a specific UFS part"""
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
    # PDF path - look for UFS AVL PDF in current directory first, then script directory
    current_dir = Path.cwd()
    script_dir = Path(__file__).parent

    # Try to find UFS AVL PDF in current directory first
    pdf_files = list(current_dir.glob("Rockchip_UFS_Approved_Vendor_List_Ver*.pdf"))

    if pdf_files:
        pdf_path = pdf_files[0]  # Use the first match
        print(f"Found PDF in current directory: {pdf_path}")
    else:
        # Try to find in fae_doc_* subdirectories
        fae_doc_dirs = list(current_dir.glob("fae_doc_*"))
        found = False
        for fae_doc_dir in fae_doc_dirs:
            if fae_doc_dir.is_dir():
                pdf_files = list(fae_doc_dir.glob("Rockchip_UFS_Approved_Vendor_List_Ver*.pdf"))
                if pdf_files:
                    pdf_path = pdf_files[0]
                    print(f"Found PDF in {fae_doc_dir.name} directory: {pdf_path}")
                    found = True
                    break

        if not found:
            # Fall back to script directory
            pdf_files = list(script_dir.glob("Rockchip_UFS_Approved_Vendor_List_Ver*.pdf"))
            if pdf_files:
                pdf_path = pdf_files[0]
                print(f"Using PDF from script directory: {pdf_path}")
            else:
                print(f"Error: UFS AVL PDF not found in current directory, fae_doc_* subdirectories, or script directory")
                return

    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return

    # Parse PDF
    parser = UFSAVLParser(str(pdf_path))
    data = parser.parse()

    # Save JSON output to current directory
    output_path = current_dir / "ufs_avl_data.json"
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

    # Test 1: KIOXIA THGJFGT2T85BAB5 should be KIOXIA
    kioxia_test = [p for p in data['parts'] if 'THGJFGT2T85BAB5' in p['part_number']]
    if kioxia_test and kioxia_test[0]['manufacturer'] == 'KIOXIA':
        print("[PASS] THGJFGT2T85BAB5 correctly assigned to KIOXIA")
    else:
        print("[FAIL] THGJFGT2T85BAB5 should be KIOXIA, got:", kioxia_test[0]['manufacturer'] if kioxia_test else "Not found")
        validation_passed = False

    # Test 2: MICRON MTFC64GAZAOTD-AIT should be MICRON
    micron_test = [p for p in data['parts'] if 'MTFC64GAZAOTD-AIT' in p['part_number']]
    if micron_test and micron_test[0]['manufacturer'] == 'MICRON':
        print("[PASS] MTFC64GAZAOTD-AIT correctly assigned to MICRON")
    else:
        print("[FAIL] MTFC64GAZAOTD-AIT should be MICRON, got:", micron_test[0]['manufacturer'] if micron_test else "Not found")
        validation_passed = False

    # Test 3: Unknown count should be low
    unknown_parts = [p for p in data['parts'] if p['manufacturer'] == 'Unknown']
    if len(unknown_parts) < 5:
        print(f"[PASS] Unknown manufacturer count: {len(unknown_parts)} (acceptable)")
    else:
        print(f"[FAIL] Too many Unknown manufacturers: {len(unknown_parts)}")
        validation_passed = False

    # Test 4: Reasonable part count (should be 50+)
    if len(data['parts']) > 50:
        print(f"[PASS] Total parts: {len(data['parts'])} (reasonable)")
    else:
        print(f"[WARN] Low part count: {len(data['parts'])}")

    # Test 5: Reasonable chip count (should be 3-15)
    if 3 <= len(data['chips']) <= 15:
        print(f"[PASS] Total chips: {len(data['chips'])} (reasonable)")
    else:
        print(f"[WARN] Unexpected chip count: {len(data['chips'])}")

    # Test 6: UFS-specific fields populated
    sample_parts_with_voltage = [p for p in data['parts'] if p.get('vcc')]
    if len(sample_parts_with_voltage) > len(data['parts']) * 0.8:
        print(f"[PASS] UFS voltage fields populated: {len(sample_parts_with_voltage)}/{len(data['parts'])} parts have VCC data")
    else:
        print(f"[WARN] Low UFS voltage field population: {len(sample_parts_with_voltage)}/{len(data['parts'])}")

    print("\n" + "="*60)
    if validation_passed:
        print("ALL VALIDATION TESTS PASSED!")
    else:
        print("SOME VALIDATION TESTS FAILED - please review")
    print("="*60)

    # Test queries
    if kioxia_test:
        print("\n" + "="*60)
        print("Test Query 1: THGJFGT2T85BAB5")
        print("="*60)
        result = query_part_support(data, "THGJFGT2T85BAB5")
        print(f"Manufacturer: {result['manufacturer']}")
        print(f"Supported chips ({len(result['supported_chips'])}): {', '.join(result['supported_chips'])}")

        # Show UFS-specific fields
        part_details = kioxia_test[0]
        print(f"VCC: {part_details.get('vcc')}")
        print(f"VCCQ: {part_details.get('vccq')}")
        print(f"VCCQ2: {part_details.get('vccq2')}")
        print(f"Temperature: {part_details.get('temp')}")

    if len(data['chips']) > 0 and len(data['parts']) > 0:
        print("\n" + "="*60)
        print(f"Test Query 2: {data['chips'][0]} + {data['parts'][0]['part_number']}")
        print("="*60)
        result = query_chip_compatibility(data, data['chips'][0], data['parts'][0]['part_number'])
        print(f"Supported: {result['supported']}")
        print(f"Status: {result['status']}")


if __name__ == "__main__":
    main()
