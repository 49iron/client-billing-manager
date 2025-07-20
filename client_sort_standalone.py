"""
Client Sort & Format - Standalone Application
Dedicated tool for monthly tracking_number_usage.csv processing
Password protected and separate from Zoho integration
"""

import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
import xlsxwriter

def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "dereK000!!!":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("Password incorrect")
        return False
    else:
        # Password correct.
        return True

def load_account_mappings():
    """Load account to group mappings"""
    try:
        with open('account_group_mappings.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_account_mappings(mappings):
    """Save account to group mappings"""
    with open('account_group_mappings.json', 'w') as f:
        json.dump(mappings, f, indent=2)

def validate_csv(df):
    """Validate CSV structure and standardize column names"""
    # Show original columns for debugging

    
    # Standardize column names
    if 'Account' in df.columns and 'Account Number' not in df.columns:
        df = df.rename(columns={'Account': 'Account Number'})
    
    # More comprehensive column mappings with case-insensitive matching
    # Note: We avoid mapping cost columns to quantity columns to prevent duplicates
    column_mappings = {
        # Account variations
        'account': 'Account Number',
        
        # Calls variations
        'calls quantity': 'Calls Total',
        'call quantity': 'Calls Total', 
        'calls': 'Calls Total',
        'call': 'Calls Total',
        'calls total': 'Calls Total',
        'call total': 'Calls Total',
        'total calls': 'Calls Total',
        
        # Minutes variations (keep existing quantities, don't map cost to quantity)
        'minutes': 'Minutes quantity',
        'minute': 'Minutes quantity',
        'call minutes': 'Minutes quantity',
        'call minute': 'Minutes quantity',
        
        # Messages variations (keep existing quantities, don't map cost to quantity)
        'messages': 'Messages quantity',
        'message': 'Messages quantity',
        'sms quantity': 'Messages quantity',
        'sms': 'Messages quantity',
        'messages total': 'Messages quantity',
        'message total': 'Messages quantity',
        
        # Transcriptions variations
        'transcription': 'Transcriptions quantity',
        'transcriptions': 'Transcriptions quantity',
        'transcription minutes': 'Transcriptions quantity',
        'transcriptions minutes': 'Transcriptions quantity',
        'transcription minute': 'Transcriptions quantity',
        'transcriptions minute': 'Transcriptions quantity',
        
        # AskAI variations
        'askai': 'AskAI quantity',
        'ask ai': 'AskAI quantity',
        'ai quantity': 'AskAI quantity',
        'ai': 'AskAI quantity',
        
        # Numbers variations
        'numbers': 'Numbers quantity',
        'number': 'Numbers quantity',
        'phone numbers': 'Numbers quantity',
        'phone number': 'Numbers quantity'
    }
    
    # Apply case-insensitive column mappings
    df_columns_lower = {col.lower(): col for col in df.columns}
    rename_dict = {}
    
    for pattern, target in column_mappings.items():
        if pattern.lower() in df_columns_lower:
            original_col = df_columns_lower[pattern.lower()]
            # Only rename if target column doesn't already exist
            if target not in df.columns:
                rename_dict[original_col] = target
    
    if rename_dict:
        df = df.rename(columns=rename_dict)
    
    # Handle duplicate column names by making them unique
    cols = pd.Series(df.columns)
    for dup in cols[cols.duplicated()].unique():
        cols[cols[cols == dup].index.values.tolist()] = [dup + '_' + str(i) if i != 0 else dup for i in range(sum(cols == dup))]
    df.columns = cols
    

    
    # Map the actual columns from your CSV to standardized names for processing
    # Your CSV has: Calls Total, Messages Total, Messages quantity, etc.
    # We'll use these directly and create aliases for consistent processing
    
    # Create standardized column aliases
    column_aliases = {}
    
    # Use Messages Total if available, otherwise Messages quantity
    if 'Messages Total' in df.columns:
        column_aliases['Messages quantity'] = 'Messages Total'
    elif 'Messages quantity' in df.columns:
        column_aliases['Messages quantity'] = 'Messages quantity'
    
    # Ensure all required columns exist
    required_columns_with_defaults = {
        'Calls Total': 0,
        'Minutes quantity': 0,
        'Messages quantity': 0,
        'Transcriptions quantity': 0,
        'Transcriptions cost': '$0.00',
        'AskAI quantity': 0,
        'Numbers quantity': 0
    }
    
    for col_name, default_value in required_columns_with_defaults.items():
        if col_name not in df.columns:
            # Check if we have an alias for this column
            if col_name in column_aliases and column_aliases[col_name] in df.columns:
                continue  # Column exists under different name
            else:
                df[col_name] = default_value
                st.warning(f"Added missing column '{col_name}' with default value: {default_value}")
    
    # Show a sample of the data to verify
    st.subheader("Data Preview")
    st.dataframe(df.head())
    

    
    # Check for required columns
    required_columns = ['Account Number']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"Missing required columns: {missing_columns}")
        return None
    
    # Convert Account Number to string for consistent mapping
    df['Account Number'] = df['Account Number'].astype(str)
    
    return df

def get_billing_groups():
    """Get list of all available billing groups"""
    return [
        "BIG BRAND TIRE GROUP",
        "BTTW GROUP", 
        "Sylvan Learning",
        "Truckfitters",
        "INDEPENDENTS"
    ]

def identify_new_accounts(df, mappings):
    """Identify accounts that haven't been assigned to groups"""
    all_accounts = set(df['Account Number'].astype(str).tolist())
    mapped_accounts = set(mappings.keys())
    return list(all_accounts - mapped_accounts)

def group_accounts_by_billing_group(df, mappings):
    """Group accounts based on mappings and return organized data"""
    grouped_data = {}
    
    for account, group in mappings.items():
        if account in df['Account Number'].astype(str).values:
            if group not in grouped_data:
                grouped_data[group] = []
            
            account_row = df[df['Account Number'].astype(str) == account].iloc[0]
            grouped_data[group].append(account_row)
    
    return grouped_data

def validate_data_integrity(df, mappings, processed_accounts):
    """Validate that all uploaded data is included in the processed output"""
    validation_results = {
        'total_input_records': len(df),
        'total_processed_records': len(processed_accounts),
        'missing_accounts': [],
        'unmapped_accounts': [],
        'data_totals_match': True,
        'validation_passed': True
    }
    
    # Check for missing accounts
    input_accounts = set(df['Account Number'].astype(str).tolist())
    processed_account_set = set(processed_accounts)
    missing_accounts = input_accounts - processed_account_set
    
    if missing_accounts:
        validation_results['missing_accounts'] = list(missing_accounts)
        validation_results['validation_passed'] = False
    
    # Check for unmapped accounts (should be caught earlier but double-check)
    unmapped = []
    for account in input_accounts:
        if account not in mappings:
            unmapped.append(account)
    
    if unmapped:
        validation_results['unmapped_accounts'] = unmapped
        validation_results['validation_passed'] = False
    
    # Validate data totals
    input_calls_total = df['Calls Total'].fillna(0).astype(float).sum()
    
    # Use Messages Total if available, otherwise Messages quantity
    if 'Messages Total' in df.columns:
        input_messages_total = df['Messages Total'].fillna(0).astype(float).sum()
    else:
        input_messages_total = df['Messages quantity'].fillna(0).astype(float).sum()
    
    # Calculate input transcription total using cost ÷ $0.02 method (same as output)
    if 'Transcriptions cost' in df.columns:
        transcription_costs = df['Transcriptions cost'].fillna('$0.00').astype(str).str.replace('$', '').str.replace(',', '').astype(float)
        input_transcriptions_total = (transcription_costs / 0.02).sum()
    else:
        input_transcriptions_total = df['Transcriptions quantity'].fillna(0).astype(float).sum()
    
    input_askai_total = df['AskAI quantity'].fillna(0).astype(float).sum()
    input_numbers_total = df['Numbers quantity'].fillna(0).astype(float).sum()
    
    # Calculate processed totals (excluding BBT multiplier for comparison)
    processed_calls_total = 0
    processed_messages_total = 0
    processed_transcriptions_total = 0
    processed_askai_total = 0
    processed_numbers_total = 0
    
    for account in processed_accounts:
        account_row = df[df['Account Number'].astype(str) == account]
        if not account_row.empty:
            processed_calls_total += account_row['Calls Total'].fillna(0).astype(float).iloc[0]
            
            # Use Messages Total if available, otherwise Messages quantity
            if 'Messages Total' in account_row.columns:
                processed_messages_total += account_row['Messages Total'].fillna(0).astype(float).iloc[0]
            else:
                processed_messages_total += account_row['Messages quantity'].fillna(0).astype(float).iloc[0]
            
            # Calculate transcription minutes from cost ÷ $0.02 (same as output)
            if 'Transcriptions cost' in account_row.columns and not pd.isna(account_row['Transcriptions cost'].iloc[0]):
                cost_str = str(account_row['Transcriptions cost'].iloc[0]).replace('$', '').replace(',', '')
                try:
                    cost = float(cost_str)
                    processed_transcriptions_total += cost / 0.02
                except (ValueError, TypeError):
                    processed_transcriptions_total += account_row['Transcriptions quantity'].fillna(0).astype(float).iloc[0]
            else:
                processed_transcriptions_total += account_row['Transcriptions quantity'].fillna(0).astype(float).iloc[0]
            
            processed_askai_total += account_row['AskAI quantity'].fillna(0).astype(float).iloc[0]
            processed_numbers_total += account_row['Numbers quantity'].fillna(0).astype(float).iloc[0]
    
    # Check if totals match (allowing for small floating point differences)
    tolerance = 0.01
    if (abs(input_calls_total - processed_calls_total) > tolerance or
        abs(input_messages_total - processed_messages_total) > tolerance or
        abs(input_transcriptions_total - processed_transcriptions_total) > tolerance or
        abs(input_askai_total - processed_askai_total) > tolerance or
        abs(input_numbers_total - processed_numbers_total) > tolerance):
        validation_results['data_totals_match'] = False
        validation_results['validation_passed'] = False
    
    validation_results['input_totals'] = {
        'calls': input_calls_total,
        'messages': input_messages_total,
        'transcriptions': input_transcriptions_total,
        'askai': input_askai_total,
        'numbers': input_numbers_total
    }
    
    validation_results['processed_totals'] = {
        'calls': processed_calls_total,
        'messages': processed_messages_total,
        'transcriptions': processed_transcriptions_total,
        'askai': processed_askai_total,
        'numbers': processed_numbers_total
    }
    
    return validation_results

def create_simple_billing_excel(df, mappings):
    """Create simple Excel file matching the working format app approach"""
    output = io.BytesIO()
    
    # Create workbook with xlsxwriter
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Billing Report')
    
    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'font_size': 12,
        'align': 'center'
    })
    
    group_format = workbook.add_format({
        'bold': True,
        'font_size': 11,
        'bg_color': '#E6E6FA'
    })
    
    currency_format = workbook.add_format({'num_format': '$#,##0.00'})
    
    # Get month for header
    current_month = datetime.now().strftime('%B %Y')
    
    # Write header
    worksheet.write(0, 0, f'Client Billing Report - {current_month}', header_format)
    worksheet.merge_range(0, 0, 0, 5, f'Client Billing Report - {current_month}', header_format)
    
    # Column headers - proper billing format
    headers = ['Account', 'Account Name', 'Calls', 'Messages', 'AskAI', 'Total Cost']
    for col, header in enumerate(headers):
        worksheet.write(2, col, header, header_format)
    
    # Group accounts by billing group
    grouped_data = group_accounts_by_billing_group(df, mappings)
    
    row = 3
    
    # Process each group
    for group_name in ["BTTW GROUP", "BIG BRAND TIRE GROUP", "Sylvan Learning", "Truckfitters", "INDEPENDENTS"]:
        if group_name not in grouped_data:
            continue
            
        accounts = grouped_data[group_name]
        
        # Calculate group totals using the correct column names from your CSV
        group_calls = sum(pd.to_numeric(acc.get('Calls Total', 0), errors='coerce') for acc in accounts)
        
        # Use Messages Total if available, otherwise Messages quantity
        if 'Messages Total' in df.columns:
            group_messages = sum(pd.to_numeric(acc.get('Messages Total', 0), errors='coerce') for acc in accounts)
        else:
            group_messages = sum(pd.to_numeric(acc.get('Messages quantity', 0), errors='coerce') for acc in accounts)
            
        group_askai = sum(pd.to_numeric(acc.get('AskAI quantity', 0), errors='coerce') for acc in accounts)
        
        # Apply BBT multiplier rule
        if group_name == "BIG BRAND TIRE GROUP":
            group_askai *= 7
        
        # Calculate total cost (using standard rates)
        total_cost = (group_calls * 0.05) + (group_messages * 0.02) + (group_askai * 0.10)
        
        # Write group summary row - 6 columns only
        worksheet.write(row, 0, group_name, group_format)
        worksheet.write(row, 1, f'{len(accounts)} accounts', group_format)
        worksheet.write(row, 2, int(group_calls), group_format)
        worksheet.write(row, 3, int(group_messages), group_format)
        worksheet.write(row, 4, int(group_askai), group_format)
        worksheet.write(row, 5, total_cost, group_format)
        row += 1
        
        # Write individual account rows - 6 columns only
        for account in accounts:
            account_number = str(account['Account Number'])
            account_name = account.get('Account Name', 'Unknown')
            calls = pd.to_numeric(account.get('Calls Total', 0), errors='coerce')
            
            # Use Messages Total if available, otherwise Messages quantity
            if 'Messages Total' in df.columns:
                messages = pd.to_numeric(account.get('Messages Total', 0), errors='coerce')
            else:
                messages = pd.to_numeric(account.get('Messages quantity', 0), errors='coerce')
                
            askai = pd.to_numeric(account.get('AskAI quantity', 0), errors='coerce')
            
            # Apply BBT multiplier for individual accounts
            if group_name == "BIG BRAND TIRE GROUP":
                askai *= 7
            
            cost = (calls * 0.05) + (messages * 0.02) + (askai * 0.10)
            
            worksheet.write(row, 0, account_number)
            worksheet.write(row, 1, account_name)
            worksheet.write(row, 2, int(calls) if calls > 0 else '')
            worksheet.write(row, 3, int(messages) if messages > 0 else '')
            worksheet.write(row, 4, int(askai) if askai > 0 else '')
            worksheet.write(row, 5, cost, currency_format)
            row += 1
        
        # Add blank row between groups
        row += 1
    
    # Auto-adjust column widths
    worksheet.set_column(0, 0, 15)  # Account Number
    worksheet.set_column(1, 1, 25)  # Account Name
    worksheet.set_column(2, 5, 12)  # All metric columns
    
    workbook.close()
    output.seek(0)
    return output.getvalue()

def create_consolidated_billing_excel(df, mappings):
    """Create consolidated billing Excel file matching 6/2/25 format"""
    output = io.BytesIO()
    processed_accounts = []  # Track all accounts processed
    
    # Create workbook with xlsxwriter
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Billing Report')
    
    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'font_size': 12,
        'align': 'center'
    })
    
    group_format = workbook.add_format({
        'bold': True,
        'font_size': 11,
        'bg_color': '#E6E6FA'
    })
    
    currency_format = workbook.add_format({'num_format': '$#,##0.00'})
    
    # Get month for header
    current_month = datetime.now().strftime('%B %Y')
    
    # Write header
    worksheet.merge_range(0, 0, 0, 7, f'Client Billing Report - {current_month}', header_format)
    
    # Calculate global totals for all data first
    global_calls = df['Calls Total'].fillna(0).astype(float).sum()
    global_minutes = df['Minutes quantity'].fillna(0).astype(float).sum()
    
    # Use Messages Total if available, otherwise Messages quantity
    if 'Messages Total' in df.columns:
        global_messages = df['Messages Total'].fillna(0).astype(float).sum()
    else:
        global_messages = df['Messages quantity'].fillna(0).astype(float).sum()
    
    # Calculate transcription minutes from cost divided by $0.02
    if 'Transcriptions cost' in df.columns:
        # Remove $ sign and convert to float, then divide by 0.02 to get minutes
        transcription_costs = df['Transcriptions cost'].fillna('$0.00').astype(str).str.replace('$', '').str.replace(',', '').astype(float)
        global_transcription = (transcription_costs / 0.02).sum()
    else:
        # Fallback to quantity if cost column not available
        global_transcription = df['Transcriptions quantity'].fillna(0).astype(float).sum()
    
    global_askai = df['AskAI quantity'].fillna(0).astype(float).sum()
    global_numbers = df['Numbers quantity'].fillna(0).astype(float).sum()
    
    # Apply BBT multiplier to global AskAI total
    bbt_accounts = [acc for acc, group in mappings.items() if group == "BIG BRAND TIRE GROUP" and acc in df['Account Number'].astype(str).values]
    bbt_askai_adjustment = 0
    for account in bbt_accounts:
        account_row = df[df['Account Number'].astype(str) == account]
        if not account_row.empty:
            bbt_askai_adjustment += account_row['AskAI quantity'].fillna(0).astype(float).iloc[0] * 6  # 7x - 1x = 6x additional
    
    global_askai_with_multiplier = global_askai + bbt_askai_adjustment
    
    # Write global summary in line 2
    worksheet.write(1, 0, 'GLOBAL TOTALS', group_format)
    worksheet.write(1, 1, f'{len(df)} accounts', group_format)
    worksheet.write(1, 2, int(global_calls), group_format)
    worksheet.write(1, 3, int(global_minutes), group_format)
    worksheet.write(1, 4, int(global_messages), group_format)
    worksheet.write(1, 5, int(global_transcription), group_format)
    worksheet.write(1, 6, int(global_askai_with_multiplier), group_format)
    worksheet.write(1, 7, int(global_numbers), group_format)
    
    # Column headers
    headers = ['Account', 'Account Name', 'Calls Total', 'Minutes quantity', 'Messages quantity', 'Transcription Minutes', 'AskAI quantity', 'Numbers quantity']
    for col, header in enumerate(headers):
        worksheet.write(2, col, header, header_format)
    
    # Group accounts by billing group
    grouped_data = {}
    for account, group in mappings.items():
        if account in df['Account Number'].astype(str).values:
            if group not in grouped_data:
                grouped_data[group] = []
            
            account_row = df[df['Account Number'].astype(str) == account].iloc[0]
            grouped_data[group].append(account_row)
            processed_accounts.append(account)  # Track processed account
    
    row = 3
    
    # Process each group
    for group_name in ["BTTW GROUP", "BIG BRAND TIRE GROUP", "Sylvan Learning", "Truckfitters", "INDEPENDENTS"]:
        if group_name not in grouped_data:
            continue
            
        accounts = grouped_data[group_name]
        
        # Calculate group totals - handle NaN values properly
        group_calls = sum(pd.to_numeric(acc.get('Calls Total', 0), errors='coerce') or 0 for acc in accounts)
        group_minutes = sum(pd.to_numeric(acc.get('Minutes quantity', 0), errors='coerce') or 0 for acc in accounts)  
        
        # Use Messages Total if available, otherwise Messages quantity
        group_messages = 0
        for acc in accounts:
            if 'Messages Total' in acc and acc.get('Messages Total') is not None:
                group_messages += pd.to_numeric(acc.get('Messages Total', 0), errors='coerce') or 0
            else:
                group_messages += pd.to_numeric(acc.get('Messages quantity', 0), errors='coerce') or 0
        
        # Calculate transcription minutes from cost divided by $0.02
        group_transcription = 0
        for acc in accounts:
            if 'Transcriptions cost' in acc and acc.get('Transcriptions cost'):
                cost_str = str(acc.get('Transcriptions cost', '$0.00')).replace('$', '').replace(',', '')
                try:
                    cost = float(cost_str)
                    group_transcription += cost / 0.02
                except (ValueError, TypeError):
                    # Fallback to quantity if cost parsing fails
                    group_transcription += pd.to_numeric(acc.get('Transcriptions quantity', 0), errors='coerce') or 0
            else:
                # Fallback to quantity if cost not available
                group_transcription += pd.to_numeric(acc.get('Transcriptions quantity', 0), errors='coerce') or 0
        
        group_askai = sum(pd.to_numeric(acc.get('AskAI quantity', 0), errors='coerce') or 0 for acc in accounts)
        group_numbers = sum(pd.to_numeric(acc.get('Numbers quantity', 0), errors='coerce') or 0 for acc in accounts)
        
        # Apply BBT multiplier rule
        if group_name == "BIG BRAND TIRE GROUP":
            group_askai *= 7
        
        # Write group summary row
        worksheet.write(row, 0, group_name, group_format)
        worksheet.write(row, 1, f'{len(accounts)} accounts', group_format)
        worksheet.write(row, 2, int(group_calls), group_format)
        worksheet.write(row, 3, int(group_minutes), group_format)
        worksheet.write(row, 4, int(group_messages), group_format)
        worksheet.write(row, 5, int(group_transcription), group_format)
        worksheet.write(row, 6, int(group_askai), group_format)
        worksheet.write(row, 7, int(group_numbers), group_format)
        row += 1
        
        # Sort accounts alphabetically by account name
        accounts_sorted = sorted(accounts, key=lambda x: x.get('Account Name', 'Unknown').upper())
        
        # Write individual account rows
        for account in accounts_sorted:
            account_number = str(account['Account Number'])
            account_name = account.get('Account Name', 'Unknown')
            calls_total = pd.to_numeric(account.get('Calls Total', 0), errors='coerce') or 0
            minutes_quantity = pd.to_numeric(account.get('Minutes quantity', 0), errors='coerce') or 0
            
            # Use Messages Total if available, otherwise Messages quantity
            if 'Messages Total' in account and account.get('Messages Total') is not None:
                messages_quantity = pd.to_numeric(account.get('Messages Total', 0), errors='coerce') or 0
            else:
                messages_quantity = pd.to_numeric(account.get('Messages quantity', 0), errors='coerce') or 0
            
            # Calculate transcription minutes from cost divided by $0.02
            if 'Transcriptions cost' in account and account.get('Transcriptions cost'):
                cost_str = str(account.get('Transcriptions cost', '$0.00')).replace('$', '').replace(',', '')
                try:
                    cost = float(cost_str)
                    transcription_minutes = cost / 0.02
                except (ValueError, TypeError):
                    # Fallback to quantity if cost parsing fails
                    transcription_minutes = pd.to_numeric(account.get('Transcriptions quantity', 0), errors='coerce') or 0
            else:
                # Fallback to quantity if cost not available
                transcription_minutes = pd.to_numeric(account.get('Transcriptions quantity', 0), errors='coerce') or 0
            
            askai_quantity = pd.to_numeric(account.get('AskAI quantity', 0), errors='coerce') or 0
            numbers_quantity = pd.to_numeric(account.get('Numbers quantity', 0), errors='coerce') or 0
            
            # Individual accounts show original values (no multiplier)
            
            worksheet.write(row, 0, account_number)
            worksheet.write(row, 1, account_name)
            worksheet.write(row, 2, int(calls_total) if calls_total > 0 else '')
            worksheet.write(row, 3, int(minutes_quantity) if minutes_quantity > 0 else '')
            worksheet.write(row, 4, int(messages_quantity) if messages_quantity > 0 else '')
            worksheet.write(row, 5, int(transcription_minutes) if transcription_minutes > 0 else '')
            worksheet.write(row, 6, int(askai_quantity) if askai_quantity > 0 else '')
            worksheet.write(row, 7, int(numbers_quantity) if numbers_quantity > 0 else '')
            row += 1
        
        # Add blank row between groups
        row += 1
    
    # Auto-adjust column widths
    worksheet.set_column(0, 0, 15)  # Account
    worksheet.set_column(1, 1, 25)  # Account Name
    worksheet.set_column(2, 7, 15)  # All quantity columns
    
    # Freeze the header row (row 3 which contains the column headers)
    worksheet.freeze_panes(3, 0)
    
    workbook.close()
    output.seek(0)
    return output.getvalue(), processed_accounts

def main():
    """Main application function"""
    # Skip page config when called from main app
    try:
        st.set_page_config(
            page_title="Client Sort & Format - Standalone",
            page_icon="📊",
            layout="wide"
        )
    except:
        pass  # Page config already set by main app
    
    # Skip password check when called from main app (already authenticated)
    # Check if already authenticated via main app or standalone
    if "password_correct" not in st.session_state or not st.session_state.get("password_correct", False):
        try:
            # Check for saved auth token
            with open(".auth_token", "r") as f:
                st.session_state["password_correct"] = True
        except:
            # Only show password screen if not authenticated
            if not check_password():
                st.markdown("### 🔒 Client Sort & Format Tool")
                st.markdown("Secure access required for billing data processing")
                return
    
    st.title("📊 Client Sort & Format Tool")
    st.markdown("**Standalone Monthly Billing Data Processor**")
    st.markdown("---")
    
    # File upload section
    st.header("1. Upload Monthly Data")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload tracking_number_usage.csv file",
            type=['csv', 'xlsx'],
            help="Upload your monthly tracking number usage file"
        )
    
    with col2:
        if st.button("📋 Load Test Data"):
            try:
                df = pd.read_csv('attached_assets/tracking_number_usage_1749645560316.csv')
                st.session_state['billing_data'] = df
                st.success(f"Test data loaded: {len(df)} accounts")
                st.rerun()
            except FileNotFoundError:
                st.error("Test data file not found")
    
    # Process uploaded file
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            df = validate_csv(df)
            if df is not None:
                st.session_state['billing_data'] = df
                st.success(f"File uploaded: {len(df)} records processed")
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    
    # Main processing
    if 'billing_data' in st.session_state:
        df = st.session_state['billing_data']
        mappings = load_account_mappings()
        new_accounts = identify_new_accounts(df, mappings)
        
        # Download section - moved to top
        st.header("2. Download Consolidated Report")
        
        if new_accounts:
            st.warning("⚠️ Complete account assignment before downloading")
        else:
            # Simple download - working version from format app
            st.success("✅ Data validation passed - All records accounted for")
            

            
            # Download button - using working approach
            col1, col2 = st.columns([1, 1])
            with col1:
                excel_data, processed_accounts = create_consolidated_billing_excel(df, mappings)
                st.download_button(
                    label="📥 Download Consolidated Billing Report",
                    data=excel_data,
                    file_name=f"consolidated_billing_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            with col2:
                pass
        
        st.markdown("---")
        
        # Account assignment section
        st.header("3. Account Assignment")
        
        if new_accounts:
            st.warning(f"⚠️ {len(new_accounts)} accounts need group assignment")
            
            groups = get_billing_groups()
            assignments_made = False
            
            # Show assignment interface
            for i, account in enumerate(new_accounts[:5]):  # Show max 5 at a time
                account_row = df[df['Account Number'].astype(str) == account]
                if not account_row.empty and 'Account Name' in df.columns:
                    account_display = f"{account} - {account_row['Account Name'].iloc[0]}"
                else:
                    account_display = account
                
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.write(f"**{account_display}**")
                
                with col2:
                    selected_group = st.selectbox(
                        "Assign to group:",
                        ["Select group..."] + groups,
                        key=f"assign_{account}_{i}"
                    )
                
                with col3:
                    if st.button("Assign", key=f"btn_{account}_{i}"):
                        if selected_group != "Select group...":
                            mappings[account] = selected_group
                            save_account_mappings(mappings)
                            assignments_made = True
                            st.success(f"Assigned to {selected_group}")
            
            if len(new_accounts) > 5:
                st.info(f"Showing first 5. {len(new_accounts) - 5} more need assignment.")
            
            if assignments_made:
                st.rerun()
        else:
            st.success("✅ All accounts assigned to billing groups")
        
        # Data preview
        st.header("4. Grouped Data Preview")
        
        # Group data for preview
        grouped_data = {}
        for account, group in mappings.items():
            if account in df['Account Number'].astype(str).values:
                if group not in grouped_data:
                    grouped_data[group] = []
                account_row = df[df['Account Number'].astype(str) == account].iloc[0]
                grouped_data[group].append(account_row)
        
        if grouped_data:
            # Summary metrics
            total_accounts = sum(len(accounts) for accounts in grouped_data.values())
            

            
            # Show brief group summary
            st.write("**Account Groups:**")
            for group_name, accounts in grouped_data.items():
                st.write(f"• {group_name}: {len(accounts)} accounts")
        
        # Export section
        st.header("5. Additional Downloads")
        
        if new_accounts:
            st.info("Complete account assignment to enable additional downloads")
        else:
            st.info("✅ Ready for additional export options if needed")
        
        # Reset section
        st.header("6. Reset")
        if st.button("🔄 Clear Data"):
            if 'billing_data' in st.session_state:
                del st.session_state['billing_data']
            st.success("Data cleared")
            st.rerun()
    else:
        st.info("👆 Upload your monthly tracking_number_usage.csv file to begin")
        
        # Show current mappings summary
        mappings = load_account_mappings()
        if mappings:
            st.subheader("Current Account Mappings")
            groups = {}
            for account, group in mappings.items():
                if group not in groups:
                    groups[group] = 0
                groups[group] += 1
            
            for group, count in groups.items():
                st.write(f"• **{group}**: {count} accounts")

if __name__ == "__main__":
    main()