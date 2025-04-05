"""
This module provides export functionality for the MCP Assessor Agent API.
It allows exporting assessment data to various formats including CSV and Excel.
"""

import os
import csv
import json
import logging
import tempfile
from datetime import datetime
from io import StringIO, BytesIO
from flask import send_file, make_response, render_template

import pandas as pd

from app_setup import app, db
from models import Parcel, Property, Sale, Account, PropertyImage

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
    Export account data to the specified format.
    
    Args:
        format: Export format ('csv' or 'excel')
        limit: Maximum number of records to export
        
    Returns:
        Flask response with file attachment
    """
    with app.app_context():
        try:
            query = Account.query.limit(limit)
            
            if format == 'csv':
                return export_as_csv(query, f"account_export_{datetime.now().strftime('%Y-%m-%d')}.csv")
            elif format == 'excel':
                return export_as_excel(query, f"account_export_{datetime.now().strftime('%Y-%m-%d')}.xlsx", 'Accounts')
            else:
                return make_response("Unsupported format. Use 'csv' or 'excel'.", 400)
        except Exception as e:
            logger.error(f"Error exporting accounts: {str(e)}")
            return make_response(f"Error exporting data: {str(e)}", 500)

def export_improvements(format='csv', limit=1000):
    """
    Export improvement data to the specified format.
    
    Args:
        format: Export format ('csv' or 'excel')
        limit: Maximum number of records to export
        
    Returns:
        Flask response with file attachment
    """
    with app.app_context():
        try:
            # Query the improvements table directly with SQLAlchemy
            from sqlalchemy import text
            result = db.session.execute(text(f"SELECT * FROM improvements LIMIT {limit}"))
            
            # Convert the result to a list of dictionaries
            data = [dict(row._mapping) for row in result]
            
            if format == 'csv':
                return export_as_csv(data, f"improvements_export_{datetime.now().strftime('%Y-%m-%d')}.csv")
            elif format == 'excel':
                return export_as_excel(data, f"improvements_export_{datetime.now().strftime('%Y-%m-%d')}.xlsx", 'Improvements')
            else:
                return make_response("Unsupported format. Use 'csv' or 'excel'.", 400)
        except Exception as e:
            logger.error(f"Error exporting improvements: {str(e)}")
            return make_response(f"Error exporting data: {str(e)}", 500)

def export_property_images(format='csv', limit=1000):
    """
    Export property image data to the specified format.
    
    Args:
        format: Export format ('csv' or 'excel')
        limit: Maximum number of records to export
        
    Returns:
        Flask response with file attachment
    """
    with app.app_context():
        try:
            query = PropertyImage.query.limit(limit)
            
            if format == 'csv':
                return export_as_csv(query, f"property_images_export_{datetime.now().strftime('%Y-%m-%d')}.csv")
            elif format == 'excel':
                return export_as_excel(query, f"property_images_export_{datetime.now().strftime('%Y-%m-%d')}.xlsx", 'Property Images')
            else:
                return make_response("Unsupported format. Use 'csv' or 'excel'.", 400)
        except Exception as e:
            logger.error(f"Error exporting property images: {str(e)}")
            return make_response(f"Error exporting data: {str(e)}", 500)