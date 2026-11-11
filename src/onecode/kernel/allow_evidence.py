"""Compatibility import. Implementation lives in onecode.experimental.allow_evidence."""

from onecode.experimental.allow_evidence import (
    complete_allow_evidence,
    _complete_write,
    _complete_patch,
    _read_workspace_text,
    _write_content,
    _clean_content,
    _relative_paths,
    _accepts,
    _clean_token,
    _deny,
)

__all__ = ['complete_allow_evidence', '_complete_write', '_complete_patch', '_read_workspace_text', '_write_content', '_clean_content', '_relative_paths', '_accepts', '_clean_token', '_deny']
