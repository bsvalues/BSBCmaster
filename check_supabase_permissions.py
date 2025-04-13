"""
Check Supabase REST API permissions and configuration

This script checks the Supabase REST API permissions and configuration
to diagnose why the REST API can't find tables that exist in the database.
"""

import os
import logging
import json
import requests
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Retrieve the Supabase URL and anon key from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

def check_rest_api_tables():
    """Check which tables are available via REST API."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        logger.error("Supabase credentials not found in environment variables")
        return
    
    logger.info("Checking available tables via REST API")
    
    # List all tables
    try:
        headers = {
            "apikey": SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}"
        }
        
        # Try to list all available tables via the Supabase API introspection
        url = urljoin(SUPABASE_URL, "rest/v1/")
        response = requests.get(url, headers=headers)
        
        logger.info(f"Status code: {response.status_code}")
        logger.info(f"Response headers: {json.dumps(dict(response.headers), indent=2)}")
        
        if response.status_code == 200:
            try:
                logger.info(f"Response body: {json.dumps(response.json(), indent=2)}")
            except:
                logger.info(f"Response body (not JSON): {response.text[:500]}")
        else:
            logger.error(f"Failed to get tables: {response.text}")
    except Exception as e:
        logger.error(f"Exception checking REST API tables: {str(e)}")

def check_permissions():
    """Check permissions for the public schema tables."""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        logger.error("Supabase credentials not found in environment variables")
        return
    
    logger.info("Checking permissions via direct query")
    
    # Use direct SQL to check permissions
    from app.db.direct_sql_client import execute_query
    
    # Check schema and table permissions
    permissions_query = """
    SELECT n.nspname as schema,
           c.relname as table,
           CASE c.relkind WHEN 'r' THEN 'table' WHEN 'v' THEN 'view' END as type,
           pg_catalog.array_to_string(c.relacl, E'\n') as access_privileges
    FROM pg_catalog.pg_class c
    LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind IN ('r', 'v')
      AND n.nspname NOT IN ('pg_catalog', 'information_schema')
      AND pg_catalog.pg_table_is_visible(c.oid)
    ORDER BY 1, 2;
    """
    
    try:
        results = execute_query(permissions_query)
        logger.info(f"Found {len(results)} tables/views with permissions")
        for row in results:
            logger.info(f"Schema: {row['schema']}, Table: {row['table']}, Type: {row['type']}, Access: {row['access_privileges']}")
    except Exception as e:
        logger.error(f"Exception checking permissions: {str(e)}")
    
    # Check if anon role has access to public schema tables
    try:
        # First check if the anon role exists
        role_check_query = "SELECT rolname FROM pg_roles WHERE rolname = 'anon';"
        role_results = execute_query(role_check_query)
        if role_results:
            logger.info("Anon role exists in the database")
            
            anon_permissions_query = """
            SELECT table_schema, table_name,
                   has_table_privilege('anon', table_schema || '.' || table_name, 'SELECT') as anon_select,
                   has_table_privilege('anon', table_schema || '.' || table_name, 'INSERT') as anon_insert,
                   has_table_privilege('anon', table_schema || '.' || table_name, 'UPDATE') as anon_update,
                   has_table_privilege('anon', table_schema || '.' || table_name, 'DELETE') as anon_delete
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_schema, table_name;
            """
            
            results = execute_query(anon_permissions_query)
            logger.info(f"Checking anon role permissions for {len(results)} tables")
            for row in results:
                logger.info(f"Table: {row['table_schema']}.{row['table_name']}, "
                          f"Select: {row['anon_select']}, "
                          f"Insert: {row['anon_insert']}, "
                          f"Update: {row['anon_update']}, "
                          f"Delete: {row['anon_delete']}")
        else:
            logger.warning("Anon role does not exist in the database")
            
            # Check for authenticated role
            auth_role_check_query = "SELECT rolname FROM pg_roles WHERE rolname = 'authenticated';"
            auth_role_results = execute_query(auth_role_check_query)
            if auth_role_results:
                logger.info("Authenticated role exists in the database")
                
                # Check authenticated role permissions
                auth_permissions_query = """
                SELECT table_schema, table_name,
                       has_table_privilege('authenticated', table_schema || '.' || table_name, 'SELECT') as auth_select,
                       has_table_privilege('authenticated', table_schema || '.' || table_name, 'INSERT') as auth_insert,
                       has_table_privilege('authenticated', table_schema || '.' || table_name, 'UPDATE') as auth_update,
                       has_table_privilege('authenticated', table_schema || '.' || table_name, 'DELETE') as auth_delete
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_schema, table_name;
                """
                
                auth_results = execute_query(auth_permissions_query)
                logger.info(f"Checking authenticated role permissions for {len(auth_results)} tables")
                for row in auth_results:
                    logger.info(f"Table: {row['table_schema']}.{row['table_name']}, "
                              f"Select: {row['auth_select']}, "
                              f"Insert: {row['auth_insert']}, "
                              f"Update: {row['auth_update']}, "
                              f"Delete: {row['auth_delete']}")
            else:
                logger.warning("Authenticated role does not exist in the database")
                
            # Check service_role permissions
            service_role_check_query = "SELECT rolname FROM pg_roles WHERE rolname = 'service_role';"
            service_role_results = execute_query(service_role_check_query)
            if service_role_results:
                logger.info("Service_role exists in the database")
                
                # Check service_role permissions
                service_permissions_query = """
                SELECT table_schema, table_name,
                       has_table_privilege('service_role', table_schema || '.' || table_name, 'SELECT') as service_select,
                       has_table_privilege('service_role', table_schema || '.' || table_name, 'INSERT') as service_insert,
                       has_table_privilege('service_role', table_schema || '.' || table_name, 'UPDATE') as service_update,
                       has_table_privilege('service_role', table_schema || '.' || table_name, 'DELETE') as service_delete
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_schema, table_name;
                """
                
                service_results = execute_query(service_permissions_query)
                logger.info(f"Checking service_role permissions for {len(service_results)} tables")
                for row in service_results:
                    logger.info(f"Table: {row['table_schema']}.{row['table_name']}, "
                              f"Select: {row['service_select']}, "
                              f"Insert: {row['service_insert']}, "
                              f"Update: {row['service_update']}, "
                              f"Delete: {row['service_delete']}")
            else:
                logger.warning("Service_role does not exist in the database")
            
            # List all available roles
            roles_query = "SELECT rolname FROM pg_roles ORDER BY rolname;"
            roles_results = execute_query(roles_query)
            logger.info("Available roles in the database:")
            for row in roles_results:
                logger.info(f"  - {row['rolname']}")
                
    except Exception as e:
        logger.error(f"Exception checking role permissions: {str(e)}")

def main():
    """Main function to check Supabase REST API permissions."""
    logger.info("Checking Supabase REST API permissions")
    
    # Check if Supabase credentials are available
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        logger.error("Supabase credentials not found in environment variables")
        return
    
    # Print the first few characters of the URL and key for verification
    logger.info(f"SUPABASE_URL: {SUPABASE_URL[:25]}...")
    logger.info(f"SUPABASE_ANON_KEY (first 10 chars): {SUPABASE_ANON_KEY[:10]}...")
    
    # Check for tables available via REST API
    check_rest_api_tables()
    
    # Check for permissions on database tables
    check_permissions()

if __name__ == "__main__":
    main()