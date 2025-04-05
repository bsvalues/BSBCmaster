"""
This module provides export functionality for the MCP Assessor Agent API.
It allows exporting assessment data to various formats including CSV and Excel,
with support for filtering and customizing the exported data.
"""

import os
import csv
import json
import logging
import tempfile
from datetime import datetime
from io import StringIO, BytesIO
from flask import send_file, make_response, render_template, request

import pandas as pd

from app_setup import app, db
from models import Parcel, Property, Sale, Account, PropertyImage
from sqlalchemy import text, and_, or_, func

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def export_as_csv(query_results, filename=None):
    """
    Export query results as a CSV file.
    
    Args:
        query_results: List of dictionaries or SQLAlchemy query results
        filename: Name of the file to download (default: data_export_YYYY-MM-DD.csv)
        
    Returns:
        Flask response with CSV file attachment
    """
    if not filename:
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"data_export_{date_str}.csv"
    
    # Convert SQLAlchemy results to dict if needed
    if hasattr(query_results, 'all'):
        results = [row.__dict__ for row in query_results.all()]
        # Remove SQLAlchemy internal attributes
        for result in results:
            if '_sa_instance_state' in result:
                del result['_sa_instance_state']
    else:
        results = query_results
    
    # Handle empty results
    if not results:
        return make_response("No data found", 404)
    
    # Create CSV in memory
    si = StringIO()
    writer = csv.DictWriter(si, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)
    
    # Create response
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
    output.headers["Content-type"] = "text/csv"
    
    return output

def export_as_excel(query_results, filename=None, sheet_name='Data Export'):
    """
    Export query results as an Excel file.
    
    Args:
        query_results: List of dictionaries or SQLAlchemy query results
        filename: Name of the file to download (default: data_export_YYYY-MM-DD.xlsx)
        sheet_name: Name of the Excel sheet (default: 'Data Export')
        
    Returns:
        Flask response with Excel file attachment
    """
    if not filename:
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"data_export_{date_str}.xlsx"
    
    # Convert SQLAlchemy results to dict if needed
    if hasattr(query_results, 'all'):
        results = [row.__dict__ for row in query_results.all()]
        # Remove SQLAlchemy internal attributes
        for result in results:
            if '_sa_instance_state' in result:
                del result['_sa_instance_state']
    else:
        results = query_results
    
    # Handle empty results
    if not results:
        return make_response("No data found", 404)
    
    # Create Excel file in memory
    output = BytesIO()
    df = pd.DataFrame(results)
    
    # Create a Pandas Excel writer using XlsxWriter as the engine
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        
        # Add a header format with bold and color
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # Write the column headers with the defined format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            # Set column width based on the length of the column name
            col_width = max(len(str(value)) * 1.2, 10)
            worksheet.set_column(col_num, col_num, col_width)
    
    # Set the file pointer to the beginning
    output.seek(0)
    
    # Create response
    response = send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    
    return response

def export_accounts(format='csv', limit=1000):
    """
    Export account data to the specified format with enhanced filtering capabilities.
    
    Args:
        format: Export format ('csv' or 'excel')
        limit: Maximum number of records to export
        
    Returns:
        Flask response with file attachment
    """
    with app.app_context():
        try:
            # Get enhanced filter parameters from the request
            owner_name = request.args.get('owner_name', '')
            property_city = request.args.get('property_city', '')
            property_address = request.args.get('property_address', '')
            legal_description = request.args.get('legal_description', '')
            min_value = request.args.get('min_value')
            max_value = request.args.get('max_value')
            min_tax = request.args.get('min_tax')
            max_tax = request.args.get('max_tax')
            assessment_year = request.args.get('assessment_year')
            tax_status = request.args.get('tax_status', '')
            mailing_city = request.args.get('mailing_city', '')
            mailing_state = request.args.get('mailing_state', '')
            mailing_zip = request.args.get('mailing_zip', '')
            sort_by = request.args.get('sort_by', 'account_id')
            sort_order = request.args.get('sort_order', 'asc')
            
            # Build query with enhanced filters
            query = Account.query
            
            # Apply text-based filters with ILIKE for case-insensitive partial matching
            if owner_name:
                query = query.filter(Account.owner_name.ilike(f"%{owner_name}%"))
            if property_city:
                query = query.filter(Account.property_city.ilike(f"%{property_city}%"))
            if property_address:
                query = query.filter(Account.property_address.ilike(f"%{property_address}%"))
            if legal_description:
                query = query.filter(Account.legal_description.ilike(f"%{legal_description}%"))
            if tax_status:
                query = query.filter(Account.tax_status.ilike(f"%{tax_status}%"))
            if mailing_city:
                query = query.filter(Account.mailing_city.ilike(f"%{mailing_city}%"))
            if mailing_state:
                query = query.filter(Account.mailing_state.ilike(f"%{mailing_state}%"))
            if mailing_zip:
                query = query.filter(Account.mailing_zip.ilike(f"%{mailing_zip}%"))
            
            # Apply numeric range filters
            if min_value:
                query = query.filter(Account.assessed_value >= float(min_value))
            if max_value:
                query = query.filter(Account.assessed_value <= float(max_value))
            if min_tax:
                query = query.filter(Account.tax_amount >= float(min_tax))
            if max_tax:
                query = query.filter(Account.tax_amount <= float(max_tax))
            if assessment_year:
                query = query.filter(Account.assessment_year == int(assessment_year))
            
            # Apply sorting
            if sort_by in [column.key for column in Account.__table__.columns]:
                sort_column = getattr(Account, sort_by)
                if sort_order.lower() == 'desc':
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
            
            # Apply limit
            query = query.limit(limit)
            
            # Add a filter description to the filename
            filter_suffix = ""
            if owner_name:
                filter_suffix += f"_owner-{owner_name.replace(' ', '_')}"
            if property_city:
                filter_suffix += f"_city-{property_city.replace(' ', '_')}"
            if assessment_year:
                filter_suffix += f"_year-{assessment_year}"
            
            # Generate date string for filename
            date_str = datetime.now().strftime('%Y-%m-%d')
            
            # Handle export based on format
            if format == 'csv':
                filename = f"account_export{filter_suffix}_{date_str}.csv"
                return export_as_csv(query, filename)
            elif format == 'excel':
                filename = f"account_export{filter_suffix}_{date_str}.xlsx"
                return export_as_excel(query, filename, 'Accounts')
            else:
                return make_response("Unsupported format. Use 'csv' or 'excel'.", 400)
        except Exception as e:
            logger.error(f"Error exporting accounts: {str(e)}")
            return make_response(f"Error exporting data: {str(e)}", 500)

def export_improvements(format='csv', limit=1000):
    """
    Export improvement data to the specified format with enhanced filtering capabilities.
    
    Args:
        format: Export format ('csv' or 'excel')
        limit: Maximum number of records to export
        
    Returns:
        Flask response with file attachment
    """
    with app.app_context():
        try:
            # Get enhanced filter parameters from the request
            account_id = request.args.get('account_id', '')
            property_id = request.args.get('property_id', '')
            improvement_id = request.args.get('improvement_id', '')
            improvement_type = request.args.get('improvement_type', '')
            description = request.args.get('description', '')
            primary_use = request.args.get('primary_use', '')
            min_value = request.args.get('min_value')
            max_value = request.args.get('max_value')
            min_living_area = request.args.get('min_living_area')
            max_living_area = request.args.get('max_living_area')
            min_year_built = request.args.get('min_year_built')
            max_year_built = request.args.get('max_year_built')
            year_built = request.args.get('year_built')
            min_stories = request.args.get('min_stories')
            max_stories = request.args.get('max_stories')
            sort_by = request.args.get('sort_by', 'improvement_id')
            sort_order = request.args.get('sort_order', 'asc')
            
            # Build the SQL query with filters
            sql_query = "SELECT * FROM improvements WHERE 1=1"
            params = {}
            
            # Add text-based filters to the query with case-insensitive matching
            if account_id:
                sql_query += " AND account_id LIKE :account_id"
                params['account_id'] = f"%{account_id}%"
            
            if property_id:
                sql_query += " AND property_id LIKE :property_id"
                params['property_id'] = f"%{property_id}%"
            
            if improvement_id:
                sql_query += " AND improvement_id LIKE :improvement_id"
                params['improvement_id'] = f"%{improvement_id}%"
            
            if improvement_type:
                sql_query += " AND improvement_type LIKE :improvement_type"
                params['improvement_type'] = f"%{improvement_type}%"
            
            if description:
                sql_query += " AND description LIKE :description"
                params['description'] = f"%{description}%"
            
            if primary_use:
                sql_query += " AND primary_use LIKE :primary_use"
                params['primary_use'] = f"%{primary_use}%"
            
            # Add numeric range filters
            if min_value:
                sql_query += " AND value >= :min_value"
                params['min_value'] = float(min_value)
            
            if max_value:
                sql_query += " AND value <= :max_value"
                params['max_value'] = float(max_value)
            
            if min_living_area:
                sql_query += " AND living_area >= :min_living_area"
                params['min_living_area'] = float(min_living_area)
            
            if max_living_area:
                sql_query += " AND living_area <= :max_living_area"
                params['max_living_area'] = float(max_living_area)
            
            # Year built filters (exact or range)
            if year_built:
                sql_query += " AND year_built = :year_built"
                params['year_built'] = int(year_built)
            else:
                if min_year_built:
                    sql_query += " AND year_built >= :min_year_built"
                    params['min_year_built'] = int(min_year_built)
                
                if max_year_built:
                    sql_query += " AND year_built <= :max_year_built"
                    params['max_year_built'] = int(max_year_built)
            
            if min_stories:
                sql_query += " AND stories >= :min_stories"
                params['min_stories'] = float(min_stories)
            
            if max_stories:
                sql_query += " AND stories <= :max_stories"
                params['max_stories'] = float(max_stories)
            
            # Add sorting to the query
            valid_sort_columns = ['improvement_id', 'account_id', 'property_id', 'value', 'year_built', 'living_area', 'stories']
            if sort_by in valid_sort_columns:
                sql_query += f" ORDER BY {sort_by}"
                if sort_order.lower() == 'desc':
                    sql_query += " DESC"
                else:
                    sql_query += " ASC"
            
            # Add limit to the query
            sql_query += f" LIMIT {limit}"
            
            # Execute the query with parameters
            result = db.session.execute(text(sql_query), params)
            
            # Convert the result to a list of dictionaries
            data = [dict(row._mapping) for row in result]
            
            # Add a filter description to the filename
            filter_suffix = ""
            if account_id:
                filter_suffix += f"_acct-{account_id}"
            if improvement_type:
                filter_suffix += f"_type-{improvement_type.replace(' ', '_')}"
            if year_built:
                filter_suffix += f"_year-{year_built}"
            elif min_year_built and max_year_built:
                filter_suffix += f"_years-{min_year_built}-{max_year_built}"
            
            # Generate date string for filename
            date_str = datetime.now().strftime('%Y-%m-%d')
            
            # Handle export based on format
            if format == 'csv':
                filename = f"improvements_export{filter_suffix}_{date_str}.csv"
                return export_as_csv(data, filename)
            elif format == 'excel':
                filename = f"improvements_export{filter_suffix}_{date_str}.xlsx"
                return export_as_excel(data, filename, 'Improvements')
            else:
                return make_response("Unsupported format. Use 'csv' or 'excel'.", 400)
        except Exception as e:
            logger.error(f"Error exporting improvements: {str(e)}")
            return make_response(f"Error exporting data: {str(e)}", 500)

def export_property_images(format='csv', limit=1000):
    """
    Export property image data to the specified format with enhanced filtering capabilities.
    
    Args:
        format: Export format ('csv' or 'excel')
        limit: Maximum number of records to export
        
    Returns:
        Flask response with file attachment
    """
    with app.app_context():
        try:
            # Get enhanced filter parameters from the request
            property_id = request.args.get('property_id', '')
            account_id = request.args.get('account_id', '')
            image_type = request.args.get('image_type', '')
            image_path = request.args.get('image_path', '')
            image_url = request.args.get('image_url', '')
            capture_date_start = request.args.get('capture_date_start', '')
            capture_date_end = request.args.get('capture_date_end', '')
            min_width = request.args.get('min_width')
            min_height = request.args.get('min_height')
            max_width = request.args.get('max_width')
            max_height = request.args.get('max_height')
            format_type = request.args.get('format_type', '')
            sort_by = request.args.get('sort_by', 'id')
            sort_order = request.args.get('sort_order', 'asc')
            
            # Build query with enhanced filters
            query = PropertyImage.query
            
            # Apply text-based filters with ILIKE for case-insensitive partial matching
            if property_id:
                query = query.filter(PropertyImage.property_id.ilike(f"%{property_id}%"))
            if account_id:
                query = query.filter(PropertyImage.account_id.ilike(f"%{account_id}%"))
            if image_type:
                query = query.filter(PropertyImage.image_type.ilike(f"%{image_type}%"))
            if image_path:
                query = query.filter(PropertyImage.image_path.ilike(f"%{image_path}%"))
            if image_url:
                query = query.filter(PropertyImage.image_url.ilike(f"%{image_url}%"))
            if format_type:
                query = query.filter(PropertyImage.format.ilike(f"%{format_type}%"))
            
            # Apply date range filters if the column exists
            if hasattr(PropertyImage, 'capture_date'):
                if capture_date_start:
                    try:
                        start_date = datetime.strptime(capture_date_start, '%Y-%m-%d')
                        query = query.filter(PropertyImage.capture_date >= start_date)
                    except ValueError:
                        logger.warning(f"Invalid capture_date_start format: {capture_date_start}")
                
                if capture_date_end:
                    try:
                        end_date = datetime.strptime(capture_date_end, '%Y-%m-%d')
                        query = query.filter(PropertyImage.capture_date <= end_date)
                    except ValueError:
                        logger.warning(f"Invalid capture_date_end format: {capture_date_end}")
            
            # Apply numeric range filters
            if min_width:
                query = query.filter(PropertyImage.width >= int(min_width))
            if max_width:
                query = query.filter(PropertyImage.width <= int(max_width))
            if min_height:
                query = query.filter(PropertyImage.height >= int(min_height))
            if max_height:
                query = query.filter(PropertyImage.height <= int(max_height))
            
            # Apply sorting
            if sort_by in [column.key for column in PropertyImage.__table__.columns]:
                sort_column = getattr(PropertyImage, sort_by)
                if sort_order.lower() == 'desc':
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
            
            # Apply limit
            query = query.limit(limit)
            
            # Add a filter description to the filename
            filter_suffix = ""
            if property_id:
                filter_suffix += f"_prop-{property_id}"
            if image_type:
                filter_suffix += f"_type-{image_type}"
            if min_width or min_height:
                size_filter = ""
                if min_width:
                    size_filter += f"w{min_width}"
                if min_height:
                    size_filter += f"h{min_height}"
                filter_suffix += f"_min-{size_filter}"
            
            # Generate date string for filename
            date_str = datetime.now().strftime('%Y-%m-%d')
            
            # Handle export based on format
            if format == 'csv':
                filename = f"property_images_export{filter_suffix}_{date_str}.csv"
                return export_as_csv(query, filename)
            elif format == 'excel':
                filename = f"property_images_export{filter_suffix}_{date_str}.xlsx"
                return export_as_excel(query, filename, 'Property Images')
            else:
                return make_response("Unsupported format. Use 'csv' or 'excel'.", 400)
        except Exception as e:
            logger.error(f"Error exporting property images: {str(e)}")
            return make_response(f"Error exporting data: {str(e)}", 500)


def export_combined_data(format='excel', limit=1000):
    """
    Export combined data from multiple tables with account data as the base,
    with enhanced filtering capabilities.
    
    Args:
        format: Export format ('csv' or 'excel')
        limit: Maximum number of records to export
        
    Returns:
        Flask response with file attachment
    """
    with app.app_context():
        try:
            # Get enhanced filter parameters from the request
            account_id = request.args.get('account_id', '')
            owner_name = request.args.get('owner_name', '')
            property_city = request.args.get('property_city', '')
            property_address = request.args.get('property_address', '')
            legal_description = request.args.get('legal_description', '')
            min_value = request.args.get('min_value')
            max_value = request.args.get('max_value')
            min_tax = request.args.get('min_tax')
            max_tax = request.args.get('max_tax')
            assessment_year = request.args.get('assessment_year')
            tax_status = request.args.get('tax_status', '')
            mailing_city = request.args.get('mailing_city', '')
            mailing_state = request.args.get('mailing_state', '')
            mailing_zip = request.args.get('mailing_zip', '')
            
            # Improvement filters
            improvement_type = request.args.get('improvement_type', '')
            min_year_built = request.args.get('min_year_built')
            max_year_built = request.args.get('max_year_built')
            min_living_area = request.args.get('min_living_area')
            
            # Image filters
            image_type = request.args.get('image_type', '')
            min_width = request.args.get('min_width')
            min_height = request.args.get('min_height')
            
            # Inclusion flags
            include_improvements = request.args.get('include_improvements', 'true').lower() == 'true'
            include_images = request.args.get('include_images', 'true').lower() == 'true'
            
            # Sorting
            sort_by = request.args.get('sort_by', 'account_id')
            sort_order = request.args.get('sort_order', 'asc')
            
            # Start with base accounts query
            accounts_query = """
                SELECT a.* FROM accounts a
                WHERE 1=1
            """
            params = {}
            
            # Add text-based filters with case-insensitive matching
            if account_id:
                accounts_query += " AND a.account_id LIKE :account_id"
                params['account_id'] = f"%{account_id}%"
            
            if owner_name:
                accounts_query += " AND a.owner_name LIKE :owner_name"
                params['owner_name'] = f"%{owner_name}%"
            
            if property_city:
                accounts_query += " AND a.property_city LIKE :property_city"
                params['property_city'] = f"%{property_city}%"
                
            if property_address:
                accounts_query += " AND a.property_address LIKE :property_address"
                params['property_address'] = f"%{property_address}%"
                
            if legal_description:
                accounts_query += " AND a.legal_description LIKE :legal_description"
                params['legal_description'] = f"%{legal_description}%"
                
            if tax_status:
                accounts_query += " AND a.tax_status LIKE :tax_status"
                params['tax_status'] = f"%{tax_status}%"
                
            if mailing_city:
                accounts_query += " AND a.mailing_city LIKE :mailing_city"
                params['mailing_city'] = f"%{mailing_city}%"
                
            if mailing_state:
                accounts_query += " AND a.mailing_state LIKE :mailing_state"
                params['mailing_state'] = f"%{mailing_state}%"
                
            if mailing_zip:
                accounts_query += " AND a.mailing_zip LIKE :mailing_zip"
                params['mailing_zip'] = f"%{mailing_zip}%"
            
            # Add numeric range filters
            if min_value:
                accounts_query += " AND a.assessed_value >= :min_value"
                params['min_value'] = float(min_value)
            
            if max_value:
                accounts_query += " AND a.assessed_value <= :max_value"
                params['max_value'] = float(max_value)
                
            if min_tax:
                accounts_query += " AND a.tax_amount >= :min_tax"
                params['min_tax'] = float(min_tax)
                
            if max_tax:
                accounts_query += " AND a.tax_amount <= :max_tax"
                params['max_tax'] = float(max_tax)
                
            if assessment_year:
                accounts_query += " AND a.assessment_year = :assessment_year"
                params['assessment_year'] = int(assessment_year)
            
            # Add sorting
            valid_sort_columns = ['account_id', 'owner_name', 'property_address', 'property_city', 
                                 'assessed_value', 'tax_amount', 'assessment_year']
            if sort_by in valid_sort_columns:
                accounts_query += f" ORDER BY a.{sort_by}"
                if sort_order.lower() == 'desc':
                    accounts_query += " DESC"
                else:
                    accounts_query += " ASC"
            
            # Apply limit
            accounts_query += f" LIMIT {limit}"
            
            # Get the accounts data
            accounts_result = db.session.execute(text(accounts_query), params)
            accounts_data = [dict(row._mapping) for row in accounts_result]
            
            # If no accounts found, return empty result
            if not accounts_data:
                return make_response("No accounts found with the specified filters", 404)
            
            # Create a dictionary to store combined data
            combined_data = {
                "accounts": accounts_data,
                "improvements": [],
                "property_images": []
            }
            
            # Get account IDs for related data queries
            account_ids = [account['account_id'] for account in accounts_data]
            account_ids_str = ', '.join([f"'{account_id}'" for account_id in account_ids])
            
            # Get improvements data if requested
            if include_improvements and account_ids:
                improvements_query = f"""
                    SELECT * FROM improvements 
                    WHERE account_id IN ({account_ids_str})
                """
                
                # Add improvement-specific filters
                if improvement_type:
                    improvements_query += f" AND improvement_type LIKE '%{improvement_type}%'"
                    
                if min_year_built:
                    improvements_query += f" AND year_built >= {int(min_year_built)}"
                    
                if max_year_built:
                    improvements_query += f" AND year_built <= {int(max_year_built)}"
                    
                if min_living_area:
                    improvements_query += f" AND living_area >= {float(min_living_area)}"
                
                improvements_query += " LIMIT 5000"
                improvements_result = db.session.execute(text(improvements_query))
                combined_data["improvements"] = [dict(row._mapping) for row in improvements_result]
            
            # Get property images data if requested
            if include_images and account_ids:
                images_query = f"""
                    SELECT * FROM property_images 
                    WHERE account_id IN ({account_ids_str})
                """
                
                # Add image-specific filters
                if image_type:
                    images_query += f" AND image_type LIKE '%{image_type}%'"
                    
                if min_width:
                    images_query += f" AND width >= {int(min_width)}"
                    
                if min_height:
                    images_query += f" AND height >= {int(min_height)}"
                
                images_query += " LIMIT 5000"
                images_result = db.session.execute(text(images_query))
                combined_data["property_images"] = [dict(row._mapping) for row in images_result]
            
            # Generate filename with filter info
            filter_suffix = ""
            if account_id:
                filter_suffix += f"_acct-{account_id}"
            if property_city:
                filter_suffix += f"_city-{property_city.replace(' ', '_')}"
            
            date_str = datetime.now().strftime('%Y-%m-%d')
            
            # For Excel format, create a workbook with multiple sheets
            if format == 'excel':
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Create Accounts sheet
                    if accounts_data:
                        df_accounts = pd.DataFrame(accounts_data)
                        df_accounts.to_excel(writer, sheet_name='Accounts', index=False)
                        format_excel_sheet(writer, df_accounts, 'Accounts')
                    
                    # Create Improvements sheet
                    if include_improvements and combined_data["improvements"]:
                        df_improvements = pd.DataFrame(combined_data["improvements"])
                        df_improvements.to_excel(writer, sheet_name='Improvements', index=False)
                        format_excel_sheet(writer, df_improvements, 'Improvements')
                    
                    # Create Property Images sheet
                    if include_images and combined_data["property_images"]:
                        df_images = pd.DataFrame(combined_data["property_images"])
                        df_images.to_excel(writer, sheet_name='Property Images', index=False)
                        format_excel_sheet(writer, df_images, 'Property Images')
                
                # Set the file pointer to the beginning
                output.seek(0)
                
                # Create response
                filename = f"combined_export{filter_suffix}_{date_str}.xlsx"
                response = send_file(
                    output,
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                return response
            
            # For CSV format, return just the accounts data (or we could zip multiple CSVs)
            elif format == 'csv':
                filename = f"accounts_export{filter_suffix}_{date_str}.csv"
                return export_as_csv(accounts_data, filename)
            else:
                return make_response("Unsupported format. Use 'csv' or 'excel'.", 400)
        
        except Exception as e:
            logger.error(f"Error exporting combined data: {str(e)}")
            return make_response(f"Error exporting data: {str(e)}", 500)


def format_excel_sheet(writer, df, sheet_name):
    """
    Format an Excel sheet with headers and column widths.
    
    Args:
        writer: Excel writer object
        df: DataFrame to format
        sheet_name: Name of the sheet
    """
    # Get the xlsxwriter workbook and worksheet objects
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    
    # Add a header format with bold and color
    header_format = workbook.add_format({
        'bold': True,
        'text_wrap': True,
        'valign': 'top',
        'fg_color': '#D7E4BC',
        'border': 1
    })
    
    # Write the column headers with the defined format
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)
        # Set column width based on the length of the column name
        col_width = max(len(str(value)) * 1.2, 10)
        worksheet.set_column(col_num, col_num, col_width)