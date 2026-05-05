# OFS Response Parser - parses T24 MULTIVAL format to JSON
import re
from typing import Dict, Any, Optional

class OFSParser:
    """Parses T24 OFS response strings into structured dicts."""

    # Field separator
    FIELD_SEP = ';'
    # Multi-value marker
    MV_MARKER = '<'
    # Sub-value marker
    SV_MARKER = ':'

    @staticmethod
    def parse_response(ofsm_response: str) -> Dict[str, Any]:
        """
        Parse OFS response into dict.
        Handles @ID, @RECORD, @ERROR.CODE, @ERROR.TEXT fields.
        """
        result = {}
        # Split by FIELD_SEP
        fields = ofs_response.split(OFSParser.FIELD_SEP)

        for field in fields:
            field = field.strip()
            if not field:
                continue

            # Check if field has name=value or just name
            if '=' in field:
                name, value = field.split('=', 1)
                result[name.strip()] = OFSParser._parse_value(value.strip())
            else:
                # Might be a field with only name (like @ID)
                result[field] = None

        return result

    @staticmethod
    def _parse_value(value: str) -> Any:
        """Parse a field value, handling multi-values and sub-values."""
        if OFSParser.MV_MARKER in value:
            # Multi-value field
            parts = value.split(OFSParser.MV_MARKER)
            # First part might be the field name or value
            if '=' in parts[0]:
                # Actually this is a nested field
                return OFSParser._parse_nested(parts)
            return [p.strip() for p in parts if p.strip()]
        return value

    @staticmethod
    def _parse_nested(parts: list) -> Dict[str, Any]:
        """Parse nested multi-value fields."""
        result = {}
        for part in parts:
            if '=' in part:
                k, v = part.split('=', 1)
                result[k.strip()] = v.strip()
            else:
                # This is a value continuation
                pass
        return result

    @staticmethod
    def parse_record(record_str: str) -> Dict[str, Any]:
        """
        Parse @RECORD field specifically.
        Format: NAME<first<last;EMAIL<email;...
        """
        fields = {}
        if not record_str:
            return fields

        # Split by FIELD_SEP
        field_parts = record_str.split(OFSParser.FIELD_SEP)

        for part in field_parts:
            if OFSParser.MV_MARKER in part:
                # Field with multi-values: NAME<FIRST<LAST
                name, values_str = part.split(OFSParser.MV_MARKER, 1)
                values = values_str.split(OFSParser.MV_MARKER)
                fields[name.strip()] = [v.strip() for v in values]
            elif '=' in part:
                name, value = part.split('=', 1)
                fields[name.strip()] = value.strip()
            else:
                # Just a field name perhaps
                fields[part.strip()] = None

        return fields

    @staticmethod
    def parse_ofs_enquiry_response(ofsm_response: str) -> Dict[str, Any]:
        """
        Parse OFS enquiry response into structured JSON.
        Returns: { "@ID": ..., "@RECORD": {...}, "@ERROR": ... }
        """
        result = {}
        parsed = OFSParser.parse_response(ofsm_response)

        # Extract key fields
        if '@ID' in parsed:
            result['@ID'] = parsed['@ID']
        if '@RECORD' in parsed:
            result['@RECORD'] = OFSParser.parse_record(parsed['@RECORD'])
        if '@ERROR.CODE' in parsed:
            result['@ERROR'] = {
                'code': parsed['@ERROR.CODE'],
                'text': parsed.get('@ERROR.TEXT', '')
            }
        if '@STATUS' in parsed:
            result['@STATUS'] = parsed['@STATUS']

        return result

    @staticmethod
    def parse_ofs_transaction_response(ofsm_response: str) -> Dict[str, Any]:
        """
        Parse OFS transaction response.
        Returns: { "transaction_id": ..., "status": ..., "error": ... }
        """
        parsed = OFSParser.parse_response(ofsm_response)

        result = {}
        if '@ID' in parsed:
            result['transaction_id'] = parsed['@ID']
        if '@STATUS' in parsed:
            result['status'] = parsed['@STATUS']
        if '@ERROR.CODE' in parsed:
            result['error'] = {
                'code': parsed['@ERROR.CODE'],
                'text': parsed.get('@ERROR.TEXT', '')
            }

        return result
