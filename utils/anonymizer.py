import hashlib
import re
import logging
from typing import List, Dict, Any, Tuple, Union

# Set up logging for privacy monitoring
logger = logging.getLogger(__name__)

def anonymize_data(data: Union[List[Dict[str, Any]], Dict[str, Any]], pii_columns: List[str]) -> Tuple[Union[List[Dict[str, Any]], Dict[str, Any]], Dict[str, str]]:
    """
    Anonymize PII columns in a dataset (list of dicts or a single dict).
    Returns the anonymized data and a mapping of {hash: original_value}.
    """
    if not pii_columns:
        return data, {}

    mapping: Dict[str, str] = {}
    item_count = len(data) if isinstance(data, list) else 1
    logger.info(f"Anonymizing PII for {item_count} items. Targeted columns: {pii_columns}")
    
    def get_hash(val: Any) -> str:
        string_val = str(val)
        # Check if we already have a hash for this value
        for h, v in mapping.items():
            if v == string_val:
                return h
        
        # Create a deterministic short hash
        h_obj = hashlib.md5(string_val.encode())
        h_str = h_obj.hexdigest()
        placeholder = f"HIDDEN_{h_str[:10]}"
        mapping[placeholder] = string_val
        return placeholder

    if isinstance(data, list):
        anonymized_data = []
        for row in data:
            new_row = dict(row)
            for col in pii_columns:
                if col in new_row:
                    new_row[col] = get_hash(new_row[col])
            anonymized_data.append(new_row)
        logger.debug(f"Anonymization complete. {len(mapping)} unique PII values hashed.")
        return anonymized_data, mapping
    
    elif isinstance(data, dict):
        new_data = dict(data)
        for col in pii_columns:
            if col in new_data:
                new_data[col] = get_hash(new_data[col])
        logger.debug(f"Anonymization complete. {len(mapping)} unique PII values hashed.")
        return new_data, mapping

    return data, {}

def restore_pii(text: str, mapping: Dict[str, str]) -> str:
    """
    Replace hidden placeholders in text with their original values.
    """
    if not mapping:
        return text
    
    logger.info(f"Restoring PII for {len(mapping)} hashed values in AI response.")
    restored_text: str = str(text)
    replacements_made = 0
    # Sort keys by length descending to avoid partial matches
    sorted_placeholders = sorted(mapping.keys(), key=len, reverse=True)
    
    for placeholder in sorted_placeholders:
        if placeholder in restored_text:
            original_value = mapping[placeholder]
            restored_text = restored_text.replace(placeholder, original_value)
            replacements_made += 1
    
    logger.debug(f"PII restoration complete. {replacements_made} placeholders replaced.")
    return restored_text
