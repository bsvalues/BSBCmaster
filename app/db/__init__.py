"""
MCP Assessor Agent API Database Package.
"""

# Import database utility functions from db_utils.py
from app.db_utils import (
    execute_parameterized_query,
    parse_for_parameters,
    get_connection_string,
    execute_query_with_explicit_params
)

# Import Supabase client functions
from app.db.supabase_client import (
    get_supabase_client,
    is_connected,
    fetch_properties,
    get_property_by_id,
    create_property,
    update_property,
    delete_property,
    fetch_accounts,
    get_account_by_id,
    fetch_assessments,
    get_assessments_by_property,
    execute_query,
    test_connection
)