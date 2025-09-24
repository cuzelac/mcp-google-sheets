#!/usr/bin/env python
"""
Google Spreadsheet MCP Server
A Model Context Protocol (MCP) server built with FastMCP2 for interacting with Google Sheets.

This server supports different transport protocols:
- http: HTTP transport with network access (default, recommended for web services)
- stdio: Standard input/output (for local tools)
- sse: Server-Sent Events with network access (legacy)

Configure via environment variables:
- MCP_TRANSPORT: Transport protocol ('http', 'stdio', or 'sse', default: 'http')
- MCP_HOST: Host to bind to for HTTP/SSE transport (default: '0.0.0.0')
- MCP_PORT: Port to listen on for HTTP/SSE transport (default: 8000)
- FASTMCP_SERVER_AUTH: Set to 'fastmcp.server.auth.providers.google.GoogleProvider' for Google OAuth
- FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID: Your Google OAuth 2.0 Client ID
- FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET: Your Google OAuth 2.0 Client Secret
- FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL: Public URL of your FastMCP server for OAuth callbacks
- FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES: Required Google scopes (comma-separated)
"""

import os
from typing import List, Dict, Any, Optional, Union
import json

# FastMCP2 imports
from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider

# Google API imports
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Constants
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID', '')  # Working directory in Google Drive

# Transport configuration
TRANSPORT = os.environ.get('MCP_TRANSPORT', 'http')

# FastMCP Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get('FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET')
GOOGLE_BASE_URL = os.environ.get('FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL', 'http://localhost:8000')
GOOGLE_SCOPES = os.environ.get('FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES', 'openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive')



# Global Google services (will be initialized on first use)
_sheets_service = None
_drive_service = None
_folder_id = None


def get_google_services():
    """Get or initialize Google services using FastMCP Google OAuth"""
    global _sheets_service, _drive_service, _folder_id
    
    if _sheets_service is None:
        # FastMCP Google OAuth is required
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise Exception("Google OAuth credentials not configured. Please set FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID and FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET")
        
        # Get credentials from FastMCP OAuth token
        try:
            from fastmcp.server.dependencies import get_access_token
            from google.oauth2.credentials import Credentials
            
            # Get the OAuth token from FastMCP
            token = get_access_token()
            
            # The AccessToken object has a 'token' attribute containing the access token
            access_token = token.token
            
            # Create Google credentials from the OAuth token
            creds = Credentials(
                token=access_token,
                refresh_token=None,  # Not needed for OAuth flow
                token_uri="https://oauth2.googleapis.com/token",
                client_id=GOOGLE_CLIENT_ID,
                client_secret=GOOGLE_CLIENT_SECRET,
                scopes=SCOPES
            )
            
            print(f"Successfully authenticated using FastMCP Google OAuth")
            
        except Exception as e:
            raise Exception(f"Failed to authenticate with Google APIs using OAuth token: {e}. Please ensure you are authenticated through the OAuth flow.")
        
        # Build the services
        _sheets_service = build('sheets', 'v4', credentials=creds)
        _drive_service = build('drive', 'v3', credentials=creds)
        _folder_id = DRIVE_FOLDER_ID if DRIVE_FOLDER_ID else None
    
    return _sheets_service, _drive_service, _folder_id

# Initialize the FastMCP2 server with Google OAuth (required)
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    raise Exception("Google OAuth credentials are required. Please set FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID and FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET")

# Parse scopes from environment variable
required_scopes = [scope.strip() for scope in GOOGLE_SCOPES.split(',')]

auth_provider = GoogleProvider(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    base_url=GOOGLE_BASE_URL,
    required_scopes=required_scopes,
    redirect_path="/auth/callback"  # Default callback path
)
print(f"FastMCP Google OAuth configured with base URL: {GOOGLE_BASE_URL}")
print(f"Required scopes: {required_scopes}")

mcp = FastMCP("Google Spreadsheet", auth=auth_provider)


@mcp.tool()
def get_user_info() -> Dict[str, Any]:
    """
    Returns information about the authenticated Google user.
    Only available when using FastMCP Google OAuth authentication.
    
    Returns:
        Dictionary containing user information from Google OAuth token claims
    """
    if not auth_provider:
        return {"error": "Google OAuth not configured. This tool requires FastMCP Google OAuth authentication."}
    
    try:
        from fastmcp.server.dependencies import get_access_token
        token = get_access_token()
        # The GoogleProvider stores user data in token claims
        return {
            "google_id": token.claims.get("sub"),
            "email": token.claims.get("email"),
            "name": token.claims.get("name"),
            "picture": token.claims.get("picture"),
            "locale": token.claims.get("locale"),
            "verified_email": token.claims.get("email_verified")
        }
    except Exception as e:
        return {"error": f"Failed to get user info: {str(e)}"}


@mcp.tool()
def get_sheet_data(spreadsheet_id: str, 
                   sheet: str,
                   range: Optional[str] = None,
                   include_grid_data: bool = False) -> Dict[str, Any]:
    """
    Get data from a specific sheet in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
        sheet: The name of the sheet
        range: Optional cell range in A1 notation (e.g., 'A1:C10'). If not provided, gets all data.
        include_grid_data: If True, includes cell formatting and other metadata in the response.
            Note: Setting this to True will significantly increase the response size and token usage
            when parsing the response, as it includes detailed cell formatting information.
            Default is False (returns values only, more efficient).
    
    Returns:
        Grid data structure with either full metadata or just values from Google Sheets API, depending on include_grid_data parameter
    """
    sheets_service, _, _ = get_google_services()

    # Construct the range - keep original API behavior
    if range:
        full_range = f"{sheet}!{range}"
    else:
        full_range = sheet
    
    if include_grid_data:
        # Use full API to get all grid data including formatting
        result = sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            ranges=[full_range],
            includeGridData=True
        ).execute()
    else:
        # Use values API to get cell values only (more efficient)
        values_result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=full_range
        ).execute()
        
        # Format the response to match expected structure
        result = {
            'spreadsheetId': spreadsheet_id,
            'valueRanges': [{
                'range': full_range,
                'values': values_result.get('values', [])
            }]
        }

    return result

@mcp.tool()
def get_sheet_formulas(spreadsheet_id: str,
                       sheet: str,
                       range: Optional[str] = None) -> List[List[Any]]:
    """
    Get formulas from a specific sheet in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
        sheet: The name of the sheet
        range: Optional cell range in A1 notation (e.g., 'A1:C10'). If not provided, gets all formulas from the sheet.
    
    Returns:
        A 2D array of the sheet formulas.
    """
    sheets_service, _, _ = get_google_services()
    
    # Construct the range
    if range:
        full_range = f"{sheet}!{range}"
    else:
        full_range = sheet  # Get all formulas in the specified sheet
    
    # Call the Sheets API
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=full_range,
        valueRenderOption='FORMULA'  # Request formulas
    ).execute()
    
    # Get the formulas from the response
    formulas = result.get('values', [])
    return formulas

@mcp.tool()
def update_cells(spreadsheet_id: str,
                sheet: str,
                range: str,
                data: List[List[Any]]) -> Dict[str, Any]:
    """
    Update cells in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
        sheet: The name of the sheet
        range: Cell range in A1 notation (e.g., 'A1:C10')
        data: 2D array of values to update
    
    Returns:
        Result of the update operation
    """
    sheets_service, _, _ = get_google_services()
    
    # Construct the range
    full_range = f"{sheet}!{range}"
    
    # Prepare the value range object
    value_range_body = {
        'values': data
    }
    
    # Call the Sheets API to update values
    result = sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=full_range,
        valueInputOption='USER_ENTERED',
        body=value_range_body
    ).execute()
    
    return result


@mcp.tool()
def batch_update_cells(spreadsheet_id: str,
                       sheet: str,
                       ranges: Dict[str, List[List[Any]]]) -> Dict[str, Any]:
    """
    Batch update multiple ranges in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
        sheet: The name of the sheet
        ranges: Dictionary mapping range strings to 2D arrays of values
               e.g., {'A1:B2': [[1, 2], [3, 4]], 'D1:E2': [['a', 'b'], ['c', 'd']]}
    
    Returns:
        Result of the batch update operation
    """
    sheets_service, _, _ = get_google_services()
    
    # Prepare the batch update request
    data = []
    for range_str, values in ranges.items():
        full_range = f"{sheet}!{range_str}"
        data.append({
            'range': full_range,
            'values': values
        })
    
    batch_body = {
        'valueInputOption': 'USER_ENTERED',
        'data': data
    }
    
    # Call the Sheets API to perform batch update
    result = sheets_service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=batch_body
    ).execute()
    
    return result


@mcp.tool()
def add_rows(spreadsheet_id: str,
             sheet: str,
             count: int,
             start_row: Optional[int] = None) -> Dict[str, Any]:
    """
    Add rows to a sheet in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
        sheet: The name of the sheet
        count: Number of rows to add
        start_row: 0-based row index to start adding. If not provided, adds at the beginning.
    
    Returns:
        Result of the operation
    """
    sheets_service, _, _ = get_google_services()
    
    # Get sheet ID
    spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = None
    
    for s in spreadsheet['sheets']:
        if s['properties']['title'] == sheet:
            sheet_id = s['properties']['sheetId']
            break
            
    if sheet_id is None:
        return {"error": f"Sheet '{sheet}' not found"}
    
    # Prepare the insert rows request
    request_body = {
        "requests": [
            {
                "insertDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": start_row if start_row is not None else 0,
                        "endIndex": (start_row if start_row is not None else 0) + count
                    },
                    "inheritFromBefore": start_row is not None and start_row > 0
                }
            }
        ]
    }
    
    # Execute the request
    result = sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=request_body
    ).execute()
    
    return result


@mcp.tool()
def add_columns(spreadsheet_id: str,
                sheet: str,
                count: int,
                start_column: Optional[int] = None) -> Dict[str, Any]:
    """
    Add columns to a sheet in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
        sheet: The name of the sheet
        count: Number of columns to add
        start_column: 0-based column index to start adding. If not provided, adds at the beginning.
    
    Returns:
        Result of the operation
    """
    sheets_service, _, _ = get_google_services()
    
    # Get sheet ID
    spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = None
    
    for s in spreadsheet['sheets']:
        if s['properties']['title'] == sheet:
            sheet_id = s['properties']['sheetId']
            break
            
    if sheet_id is None:
        return {"error": f"Sheet '{sheet}' not found"}
    
    # Prepare the insert columns request
    request_body = {
        "requests": [
            {
                "insertDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": start_column if start_column is not None else 0,
                        "endIndex": (start_column if start_column is not None else 0) + count
                    },
                    "inheritFromBefore": start_column is not None and start_column > 0
                }
            }
        ]
    }
    
    # Execute the request
    result = sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=request_body
    ).execute()
    
    return result


@mcp.tool()
def list_sheets(spreadsheet_id: str) -> List[str]:
    """
    List all sheets in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet (found in the URL)
    
    Returns:
        List of sheet names
    """
    sheets_service, _, _ = get_google_services()
    
    # Get spreadsheet metadata
    spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    
    # Extract sheet names
    sheet_names = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
    
    return sheet_names


@mcp.tool()
def copy_sheet(src_spreadsheet: str,
               src_sheet: str,
               dst_spreadsheet: str,
               dst_sheet: str) -> Dict[str, Any]:
    """
    Copy a sheet from one spreadsheet to another.
    
    Args:
        src_spreadsheet: Source spreadsheet ID
        src_sheet: Source sheet name
        dst_spreadsheet: Destination spreadsheet ID
        dst_sheet: Destination sheet name
    
    Returns:
        Result of the operation
    """
    sheets_service, _, _ = get_google_services()
    
    # Get source sheet ID
    src = sheets_service.spreadsheets().get(spreadsheetId=src_spreadsheet).execute()
    src_sheet_id = None
    
    for s in src['sheets']:
        if s['properties']['title'] == src_sheet:
            src_sheet_id = s['properties']['sheetId']
            break
            
    if src_sheet_id is None:
        return {"error": f"Source sheet '{src_sheet}' not found"}
    
    # Copy the sheet to destination spreadsheet
    copy_result = sheets_service.spreadsheets().sheets().copyTo(
        spreadsheetId=src_spreadsheet,
        sheetId=src_sheet_id,
        body={
            "destinationSpreadsheetId": dst_spreadsheet
        }
    ).execute()
    
    # If destination sheet name is different from the default copied name, rename it
    if 'title' in copy_result and copy_result['title'] != dst_sheet:
        # Get the ID of the newly copied sheet
        copy_sheet_id = copy_result['sheetId']
        
        # Rename the copied sheet
        rename_request = {
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": copy_sheet_id,
                            "title": dst_sheet
                        },
                        "fields": "title"
                    }
                }
            ]
        }
        
        rename_result = sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=dst_spreadsheet,
            body=rename_request
        ).execute()
        
        return {
            "copy": copy_result,
            "rename": rename_result
        }
    
    return {"copy": copy_result}


@mcp.tool()
def rename_sheet(spreadsheet: str,
                 sheet: str,
                 new_name: str) -> Dict[str, Any]:
    """
    Rename a sheet in a Google Spreadsheet.
    
    Args:
        spreadsheet: Spreadsheet ID
        sheet: Current sheet name
        new_name: New sheet name
    
    Returns:
        Result of the operation
    """
    sheets_service, _, _ = get_google_services()
    
    # Get sheet ID
    spreadsheet_data = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet).execute()
    sheet_id = None
    
    for s in spreadsheet_data['sheets']:
        if s['properties']['title'] == sheet:
            sheet_id = s['properties']['sheetId']
            break
            
    if sheet_id is None:
        return {"error": f"Sheet '{sheet}' not found"}
    
    # Prepare the rename request
    request_body = {
        "requests": [
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "title": new_name
                    },
                    "fields": "title"
                }
            }
        ]
    }
    
    # Execute the request
    result = sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet,
        body=request_body
    ).execute()
    
    return result


@mcp.tool()
def get_multiple_sheet_data(queries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Get data from multiple specific ranges in Google Spreadsheets.
    
    Args:
        queries: A list of dictionaries, each specifying a query. 
                 Each dictionary should have 'spreadsheet_id', 'sheet', and 'range' keys.
                 Example: [{'spreadsheet_id': 'abc', 'sheet': 'Sheet1', 'range': 'A1:B5'}, 
                           {'spreadsheet_id': 'xyz', 'sheet': 'Data', 'range': 'C1:C10'}]
    
    Returns:
        A list of dictionaries, each containing the original query parameters 
        and the fetched 'data' or an 'error'.
    """
    sheets_service, _, _ = get_google_services()
    results = []
    
    for query in queries:
        spreadsheet_id = query.get('spreadsheet_id')
        sheet = query.get('sheet')
        range_str = query.get('range')
        
        if not all([spreadsheet_id, sheet, range_str]):
            results.append({**query, 'error': 'Missing required keys (spreadsheet_id, sheet, range)'})
            continue

        try:
            # Construct the range
            full_range = f"{sheet}!{range_str}"
            
            # Call the Sheets API
            result = sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=full_range
            ).execute()
            
            # Get the values from the response
            values = result.get('values', [])
            results.append({**query, 'data': values})

        except Exception as e:
            results.append({**query, 'error': str(e)})
            
    return results


@mcp.tool()
def get_multiple_spreadsheet_summary(spreadsheet_ids: List[str],
                                   rows_to_fetch: int = 5) -> List[Dict[str, Any]]:
    """
    Get a summary of multiple Google Spreadsheets, including sheet names, 
    headers, and the first few rows of data for each sheet.
    
    Args:
        spreadsheet_ids: A list of spreadsheet IDs to summarize.
        rows_to_fetch: The number of rows (including header) to fetch for the summary (default: 5).
    
    Returns:
        A list of dictionaries, each representing a spreadsheet summary. 
        Includes spreadsheet title, sheet summaries (title, headers, first rows), or an error.
    """
    sheets_service, _, _ = get_google_services()
    summaries = []
    
    for spreadsheet_id in spreadsheet_ids:
        summary_data = {
            'spreadsheet_id': spreadsheet_id,
            'title': None,
            'sheets': [],
            'error': None
        }
        try:
            # Get spreadsheet metadata
            spreadsheet = sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id,
                fields='properties.title,sheets(properties(title,sheetId))'
            ).execute()
            
            summary_data['title'] = spreadsheet.get('properties', {}).get('title', 'Unknown Title')
            
            sheet_summaries = []
            for sheet in spreadsheet.get('sheets', []):
                sheet_title = sheet.get('properties', {}).get('title')
                sheet_id = sheet.get('properties', {}).get('sheetId')
                sheet_summary = {
                    'title': sheet_title,
                    'sheet_id': sheet_id,
                    'headers': [],
                    'first_rows': [],
                    'error': None
                }
                
                if not sheet_title:
                    sheet_summary['error'] = 'Sheet title not found'
                    sheet_summaries.append(sheet_summary)
                    continue
                    
                try:
                    # Fetch the first few rows (e.g., A1:Z5)
                    # Adjust range if fewer rows are requested
                    max_row = max(1, rows_to_fetch) # Ensure at least 1 row is fetched
                    range_to_get = f"{sheet_title}!A1:{max_row}" # Fetch all columns up to max_row
                    
                    result = sheets_service.spreadsheets().values().get(
                        spreadsheetId=spreadsheet_id,
                        range=range_to_get
                    ).execute()
                    
                    values = result.get('values', [])
                    
                    if values:
                        sheet_summary['headers'] = values[0]
                        if len(values) > 1:
                            sheet_summary['first_rows'] = values[1:max_row]
                    else:
                        # Handle empty sheets or sheets with less data than requested
                        sheet_summary['headers'] = []
                        sheet_summary['first_rows'] = []

                except Exception as sheet_e:
                    sheet_summary['error'] = f'Error fetching data for sheet {sheet_title}: {sheet_e}'
                
                sheet_summaries.append(sheet_summary)
            
            summary_data['sheets'] = sheet_summaries
            
        except Exception as e:
            summary_data['error'] = f'Error fetching spreadsheet {spreadsheet_id}: {e}'
            
        summaries.append(summary_data)
        
    return summaries


@mcp.resource("spreadsheet://{spreadsheet_id}/info")
def get_spreadsheet_info(spreadsheet_id: str) -> str:
    """
    Get basic information about a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
    
    Returns:
        JSON string with spreadsheet information
    """
    sheets_service, _, _ = get_google_services()
    
    # Get spreadsheet metadata
    spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    
    # Extract relevant information
    info = {
        "title": spreadsheet.get('properties', {}).get('title', 'Unknown'),
        "sheets": [
            {
                "title": sheet['properties']['title'],
                "sheetId": sheet['properties']['sheetId'],
                "gridProperties": sheet['properties'].get('gridProperties', {})
            }
            for sheet in spreadsheet.get('sheets', [])
        ]
    }
    
    return json.dumps(info, indent=2)


@mcp.tool()
def create_spreadsheet(title: str) -> Dict[str, Any]:
    """
    Create a new Google Spreadsheet.
    
    Args:
        title: The title of the new spreadsheet
    
    Returns:
        Information about the newly created spreadsheet including its ID
    """
    _, drive_service, folder_id = get_google_services()

    # Create the spreadsheet
    file_body = {
        'name': title,
        'mimeType': 'application/vnd.google-apps.spreadsheet',
    }
    if folder_id:
        file_body['parents'] = [folder_id]
    
    spreadsheet = drive_service.files().create(
        supportsAllDrives=True,
        body=file_body,
        fields='id, name, parents'
    ).execute()

    spreadsheet_id = spreadsheet.get('id')
    parents = spreadsheet.get('parents')
    print(f"Spreadsheet created with ID: {spreadsheet_id}")

    return {
        'spreadsheetId': spreadsheet_id,
        'title': spreadsheet.get('name', title),
        'folder': parents[0] if parents else 'root',
    }


@mcp.tool()
def create_sheet(spreadsheet_id: str, 
                title: str) -> Dict[str, Any]:
    """
    Create a new sheet tab in an existing Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet
        title: The title for the new sheet
    
    Returns:
        Information about the newly created sheet
    """
    sheets_service, _, _ = get_google_services()
    
    # Define the add sheet request
    request_body = {
        "requests": [
            {
                "addSheet": {
                    "properties": {
                        "title": title
                    }
                }
            }
        ]
    }
    
    # Execute the request
    result = sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=request_body
    ).execute()
    
    # Extract the new sheet information
    new_sheet_props = result['replies'][0]['addSheet']['properties']
    
    return {
        'sheetId': new_sheet_props['sheetId'],
        'title': new_sheet_props['title'],
        'index': new_sheet_props.get('index'),
        'spreadsheetId': spreadsheet_id
    }


@mcp.tool()
def list_spreadsheets() -> List[Dict[str, str]]:
    """
    List all spreadsheets in the configured Google Drive folder.
    If no folder is configured, lists spreadsheets from 'My Drive'.
    
    Returns:
        List of spreadsheets with their ID and title
    """
    _, drive_service, folder_id = get_google_services()
    
    query = "mimeType='application/vnd.google-apps.spreadsheet'"
    
    # If a specific folder is configured, search only in that folder
    if folder_id:
        query += f" and '{folder_id}' in parents"
        print(f"Searching for spreadsheets in folder: {folder_id}")
    else:
        print("Searching for spreadsheets in 'My Drive'")
    
    # List spreadsheets
    results = drive_service.files().list(
        q=query,
        spaces='drive',
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields='files(id, name)',
        orderBy='modifiedTime desc'
    ).execute()
    
    spreadsheets = results.get('files', [])
    
    return [{'id': sheet['id'], 'title': sheet['name']} for sheet in spreadsheets]


@mcp.tool()
def share_spreadsheet(spreadsheet_id: str, 
                      recipients: List[Dict[str, str]],
                      send_notification: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    """
    Share a Google Spreadsheet with multiple users via email, assigning specific roles.
    
    Args:
        spreadsheet_id: The ID of the spreadsheet to share.
        recipients: A list of dictionaries, each containing 'email_address' and 'role'.
                    The role should be one of: 'reader', 'commenter', 'writer'.
                    Example: [
                        {'email_address': 'user1@example.com', 'role': 'writer'},
                        {'email_address': 'user2@example.com', 'role': 'reader'}
                    ]
        send_notification: Whether to send a notification email to the users. Defaults to True.

    Returns:
        A dictionary containing lists of 'successes' and 'failures'. 
        Each item in the lists includes the email address and the outcome.
    """
    _, drive_service, _ = get_google_services()
    successes = []
    failures = []
    
    for recipient in recipients:
        email_address = recipient.get('email_address')
        role = recipient.get('role', 'writer') # Default to writer if role is missing for an entry
        
        if not email_address:
            failures.append({
                'email_address': None,
                'error': 'Missing email_address in recipient entry.'
            })
            continue
            
        if role not in ['reader', 'commenter', 'writer']:
             failures.append({
                'email_address': email_address,
                'error': f"Invalid role '{role}'. Must be 'reader', 'commenter', or 'writer'."
            })
             continue

        permission = {
            'type': 'user',
            'role': role,
            'emailAddress': email_address
        }
        
        try:
            result = drive_service.permissions().create(
                fileId=spreadsheet_id,
                body=permission,
                sendNotificationEmail=send_notification,
                fields='id'
            ).execute()
            successes.append({
                'email_address': email_address, 
                'role': role, 
                'permissionId': result.get('id')
            })
        except Exception as e:
            # Try to provide a more informative error message
            error_details = str(e)
            if hasattr(e, 'content'):
                try:
                    error_content = json.loads(e.content)
                    error_details = error_content.get('error', {}).get('message', error_details)
                except json.JSONDecodeError:
                    pass # Keep the original error string
            failures.append({
                'email_address': email_address,
                'error': f"Failed to share: {error_details}"
            })
            
    return {"successes": successes, "failures": failures}

def main():
    """
    Run the FastMCP2 server.
    
    The server can be configured via environment variables:
    - MCP_TRANSPORT: Transport protocol ('http', 'stdio', or 'sse', default: 'http')
    - MCP_HOST: Host to bind to (default: '0.0.0.0')
    - MCP_PORT: Port to listen on (default: 8000)
    - FASTMCP_LOG_LEVEL: Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
    - FASTMCP_MASK_ERROR_DETAILS: Whether to hide detailed error info (default: False)
    
    Required Google OAuth authentication:
    - FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID: Your Google OAuth 2.0 Client ID (required)
    - FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET: Your Google OAuth 2.0 Client Secret (required)
    - FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL: Public URL of your FastMCP server for OAuth callbacks
    - FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES: Required Google scopes (comma-separated)
    
    Optional configuration:
    - DRIVE_FOLDER_ID: Google Drive folder ID for organizing spreadsheets
    """
    print(f"Starting Google Spreadsheet FastMCP2 Server...")
    print(f"Transport: {TRANSPORT}")
    
    # Show authentication configuration
    print("✅ FastMCP Google OAuth authentication enabled")
    print(f"   Base URL: {GOOGLE_BASE_URL}")
    print(f"   Scopes: {GOOGLE_SCOPES}")
    
    # Get log level from environment
    log_level = os.environ.get('FASTMCP_LOG_LEVEL', 'INFO')
    print(f"Log Level: {log_level}")
    
    # Configure network settings for HTTP/SSE transports
    if TRANSPORT in ['http', 'sse']:
        host = os.environ.get('MCP_HOST', '0.0.0.0')
        port = int(os.environ.get('MCP_PORT', '8000'))
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Server will be accessible at: http://{host}:{port}")
        
        print(f"OAuth callback URL: http://{host}:{port}/auth/callback")
        print("Make sure this URL is configured in your Google OAuth Client settings")
        
        mcp.run(transport=TRANSPORT, host=host, port=port, log_level=log_level)
    else:
        # Use stdio transport
        print("Note: Google OAuth requires HTTP transport. Using stdio transport.")
        mcp.run(transport=TRANSPORT, log_level=log_level)


if __name__ == "__main__":
    main()
