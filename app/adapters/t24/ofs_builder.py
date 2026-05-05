# OFS Message Builder - creates OFS messages from templates
import re
from typing import Dict, Any, Optional

class OFSBuilder:
    """Builds OFS messages from templates with variable substitution."""

    @staticmethod
    def build_ofs_message(
        template: str,
        variables: Dict[str, str],
        username: str,
        password: str
    ) -> str:
        """
        Build OFS message from template.
        Replaces {{VARIABLE}} placeholders with values from variables dict.
        Automatically replaces {{T24_USER}} and {{T24_PASS}} with credentials.
        """
        ofs_message = template

        # Replace credentials
        ofs_message = ofs_message.replace("{{T24_USER}}", username)
        ofs_message = ofs_message.replace("{{T24_PASS}}", password)

        # Replace all variable placeholders
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in ofs_message:
                ofs_message = ofs_message.replace(placeholder, str(value))

        # Validate: no unresolved placeholders
        unresolved = re.findall(r"\{\{(\w+)\}\}", ofs_message)
        if unresolved:
            raise ValueError(f"Unresolved OFS template variables: {unresolved}")

        return ofs_message

    @staticmethod
    def build_enquiry_ofs(
        enquiry_name: str,
        username: str,
        password: str,
        t24_version: str = "0",
        selection_criteria: str = ""
    ) -> str:
        """Build a simple enquiry OFS message."""
        return f"ENQ.{enquiry_name},CUSTOMER,{t24_version}/{username}/{password},,{selection_criteria}"

    @staticmethod
    def build_transaction_ofs(
        application: str,
        username: str,
        password: str,
        t24_version: str = "0",
        fields: Optional[Dict[str, str]] = None
    ) -> str:
        """Build a transaction OFS message."""
        field_str = ""
        if fields:
            field_parts = [f"{k}={v}" for k, v in fields.items()]
            field_str = "," + ".".join(field_parts)
        return f"{application},{application},INPUT/{username}/{password},{field_str}"
