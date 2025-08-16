import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
import xlsxwriter

# Set page configuration
st.set_page_config(
    page_title="Client Billing Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Authentication
def check_password():
    """Returns `True` if the user had the correct password."""
    
    # Check if we've stored the authentication in a file-based token
    try:
        with open(".auth_token", "r") as f:
            return True
    except:
        pass
    
    # Initialize session state variables if they don't exist
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    
    # If password is already correct, return True immediately
    if st.session_state["password_correct"]:
        try:
            with open(".auth_token", "w") as f:
                f.write("authenticated")
        except:
            pass
        return True
    
    # Otherwise, show the login page
    st.title("🔐 Client Billing Manager")
    st.markdown("### Please enter your password to access the billing system")
    
    # Create password input
    password = st.text_input("Password", type="password", key="password_input")
    
    if st.button("Login", use_container_width=True):
        if password == "dereK000!!!":
            st.session_state["password_correct"] = True
            try:
                with open(".auth_token", "w") as f:
                    f.write("authenticated")
            except:
                pass
            st.success("✅ Access granted! Redirecting...")
            st.rerun()
        else:
            st.error("❌ Incorrect password")
    
    return False

def load_account_mappings():
    """Load account to group mappings"""
    try:
        # Default mappings for common accounts
        default_mappings = {
            "8053332893": "BTTW GROUP",
            "8053332894": "BIG BRAND TIRE GROUP", 
            "8053332895": "Sylvan Learning",
            "8053332896": "Truckfitters",
            "8053332897": "INDEPENDENTS"
        }
        
        # Try to load from file, fallback to defaults
        try:
            with open('account_group_mappings.json', 'r') as f:
                mappings = json.load(f)
                # Merge with defaults to ensure we have base mappings
                default_mappings.update(mappings)
                return default_mappings
        except (FileNotFoundError, json.JSONDecodeError):
            return default_mappings
    except Exception:
        return {}

def save_account_mappings(mappings):
    """Save account to group mappings"""
    try:
        with open('account_group_mappings.json', 'w') as f:
            json.dump(mappings, f, indent=2)
    except Exception as e:
        st.warning(f"Could not save mappings: {e}")

def validate_csv(df):
    """Validate CSV structure and standardize column names"""
    if df.empty:
        st.error("The uploaded file contains no data.")
        return None
    
    # Show original columns for debugging
    st.info(f"Columns found: {list(df.columns)}")
    
    # Standardize column names - handle the 'Account' vs 'Account Number' issue
    if 'Account' in df.columns and 'Account Number' not in df.columns:
        df = df.rename(columns={'Account': 'Account Number'})
    
    # Enhanced column mappings to handle various naming conventions
    column_mappings = {
        'account': 'Account Number',
        'account number': 'Account Number',
        'calls': 'Calls Total',
        'calls total': 'Calls Total',
        'minutes': 'Minutes quantity',
        'minutes quantity': 'Minutes quantity',
        'messages': 'Messages quantity', 
        'messages quantity': 'Messages quantity',
        'messages total': 'Messages Total',
        'transcriptions': 'Transcriptions quantity',
        'transcriptions quantity': 'Transcriptions quantity',
        'askai': 'AskAI quantity',
        'askai quantity': 'AskAI quantity',
        'numbers': 'Numbers quantity',
        'numbers quantity': 'Numbers quantity'
    }
    
    # Apply case-insensitive column mappings
    df_columns_lower = {col.lower(): col for col in df.columns}
    rename_dict = {}
    
    for pattern, target in column_mappings.items():
        if pattern.lower() in df_columns_lower:
            original_col = df_columns_lower[pattern.lower()]
            if target not in df.columns:
                rename_dict[original_col] = target
    
    if rename_dict:
        df = df.rename(columns=rename_dict)
        st.success(f"Renamed columns: {rename_dict}")
    
    # Ensure required columns exist
    required_columns = ['Account Number']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"Missing required columns: {missing_columns}")
        st.info("Available columns: " + ", ".join(df.columns))
        return None
    
    # Convert Account Number to string
    df['Account Number'] = df['Account Number'].astype(str)
    
    st.success(f"✅ CSV validated successfully - {len(df)} records ready for processing")
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

def create_consolidated_billing_excel(df, mappings):
    """Create comprehensive Excel file with billing data"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Consolidated Billing')
    
    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'font_size': 12,
        'align': 'center',
        'bg_color': '#4472C4',
        'font_color': 'white'
    })
    
    group_format = workbook.add_format({
        'bold': True,
        'font_size': 11,
        'bg_color': '#E6E6FA',
        'align': 'center'
    })
    
    account_format = workbook.add_format({
        'font_size': 10,
        'align': 'left'
    })
    
    # Write main header
    current_month = datetime.now().strftime('%B %Y')
    worksheet.write(0, 0, f'Consolidated Client Billing Report - {current_month}', header_format)
    worksheet.merge_range(0, 0, 0, 7, f'Consolidated Client Billing Report - {current_month}', header_format)
    
    # Calculate global totals
    processed_accounts = []
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
            processed_accounts.append(account)
    
    row = 3
    
    # Process each group in specific order
    for group_name in ["BTTW GROUP", "BIG BRAND TIRE GROUP", "Sylvan Learning", "Truckfitters", "INDEPENDENTS"]:
        if group_name not in grouped_data:
            continue
            
        accounts = grouped_data[group_name]
        
        # Calculate group totals
        group_calls = sum(pd.to_numeric(acc.get('Calls Total', 0), errors='coerce') or 0 for acc in accounts)
        group_minutes = sum(pd.to_numeric(acc.get('Minutes quantity', 0), errors='coerce') or 0 for acc in accounts)  
        
        # Use Messages Total if available, otherwise Messages quantity
        group_messages = 0
        for acc in accounts:
            if 'Messages Total' in acc and acc.get('Messages Total') is not None:
                group_messages += pd.to_numeric(acc.get('Messages Total', 0), errors='coerce') or 0
            else:
                group_messages += pd.to_numeric(acc.get('Messages quantity', 0), errors='coerce') or 0
        
        # Calculate transcription minutes from cost
        group_transcription = 0
        for acc in accounts:
            if 'Transcriptions cost' in acc and acc.get('Transcriptions cost'):
                cost_str = str(acc.get('Transcriptions cost', '$0.00')).replace('$', '').replace(',', '')
                try:
                    cost = float(cost_str)
                    group_transcription += cost / 0.02
                except (ValueError, TypeError):
                    group_transcription += pd.to_numeric(acc.get('Transcriptions quantity', 0), errors='coerce') or 0
            else:
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
            
            # Calculate transcription minutes from cost
            if 'Transcriptions cost' in account and account.get('Transcriptions cost'):
                cost_str = str(account.get('Transcriptions cost', '$0.00')).replace('$', '').replace(',', '')
                try:
                    cost = float(cost_str)
                    transcription_minutes = cost / 0.02
                except (ValueError, TypeError):
                    transcription_minutes = pd.to_numeric(account.get('Transcriptions quantity', 0), errors='coerce') or 0
            else:
                transcription_minutes = pd.to_numeric(account.get('Transcriptions quantity', 0), errors='coerce') or 0
            
            askai_quantity = pd.to_numeric(account.get('AskAI quantity', 0), errors='coerce') or 0
            numbers_quantity = pd.to_numeric(account.get('Numbers quantity', 0), errors='coerce') or 0
            
            # Individual accounts show original values (no multiplier applied)
            worksheet.write(row, 0, account_number, account_format)
            worksheet.write(row, 1, account_name, account_format)
            worksheet.write(row, 2, int(calls_total) if calls_total > 0 else '', account_format)
            worksheet.write(row, 3, int(minutes_quantity) if minutes_quantity > 0 else '', account_format)
            worksheet.write(row, 4, int(messages_quantity) if messages_quantity > 0 else '', account_format)
            worksheet.write(row, 5, int(transcription_minutes) if transcription_minutes > 0 else '', account_format)
            worksheet.write(row, 6, int(askai_quantity) if askai_quantity > 0 else '', account_format)
            worksheet.write(row, 7, int(numbers_quantity) if numbers_quantity > 0 else '', account_format)
            row += 1
        
        # Add blank row between groups
        row += 1
    
    # Auto-adjust column widths
    worksheet.set_column(0, 0, 15)  # Account
    worksheet.set_column(1, 1, 25)  # Account Name
    worksheet.set_column(2, 7, 15)  # All quantity columns
    
    # Freeze the header row
    worksheet.freeze_panes(3, 0)
    
    workbook.close()
    output.seek(0)
    return output.getvalue(), processed_accounts

def main():
    # Check password first
    if not check_password():
        return
    
    st.title("📊 Client Billing Manager")
    st.markdown("**Secure Password-Protected Billing System**")
    st.markdown("---")
    
    # File upload section
    st.header("1. Upload Monthly Data")
    
    uploaded_file = st.file_uploader(
        "Upload your CSV or Excel file",
        type=['csv', 'xlsx'],
        help="Upload your monthly tracking number usage file"
    )
    
    # Process uploaded file
    if uploaded_file:
        try:
            # Check if file is empty
            if uploaded_file.size == 0:
                st.error("The uploaded file is empty. Please upload a valid CSV or Excel file.")
                st.stop()
            
            # Reset file pointer
            uploaded_file.seek(0)
            
            # Read file based on extension with improved error handling
            if uploaded_file.name.endswith('.csv'):
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding='latin-1')
                except pd.errors.EmptyDataError:
                    st.error("The CSV file appears to be empty or has no columns to parse.")
                    st.stop()
            else:
                df = pd.read_excel(uploaded_file)
            
            # Check if dataframe is empty
            if df.empty:
                st.error("The uploaded file contains no data. Please check your file and try again.")
                st.stop()
            
            # Validate and process
            df = validate_csv(df)
            if df is not None:
                st.session_state['billing_data'] = df
                st.success(f"✅ File uploaded successfully: {len(df)} records processed")
            else:
                st.error("File validation failed. Please check the file format.")
                
        except pd.errors.ParserError as e:
            st.error(f"CSV parsing error: {str(e)}. Please check if your file is properly formatted.")
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.error("Please ensure your file is a valid CSV or Excel file.")
    
    # Main processing
    if 'billing_data' in st.session_state:
        df = st.session_state['billing_data']
        mappings = load_account_mappings()
        new_accounts = identify_new_accounts(df, mappings)
        
        # Account assignment
        st.header("2. Account Assignment")
        
        if new_accounts:
            st.warning(f"⚠️ {len(new_accounts)} accounts need group assignment")
            
            groups = get_billing_groups()
            
            # Show assignment interface for first 5 accounts
            for i, account in enumerate(new_accounts[:5]):
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
                            st.success(f"Assigned to {selected_group}")
                            st.rerun()
            
            if len(new_accounts) > 5:
                st.info(f"Showing first 5 accounts. {len(new_accounts) - 5} more need assignment.")
        else:
            st.success("✅ All accounts assigned to billing groups")
        
        # Download section
        st.header("3. Download Consolidated Report")
        
        if new_accounts:
            st.info("Complete account assignment to enable download")
        else:
            excel_data, processed_accounts = create_consolidated_billing_excel(df, mappings)
            st.download_button(
                label="📥 Download Consolidated Billing Report",
                data=excel_data,
                file_name=f"consolidated_billing_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # Data preview
        st.header("4. Data Preview")
        
        # Group summary
        grouped_data = {}
        for account, group in mappings.items():
            if account in df['Account Number'].astype(str).values:
                if group not in grouped_data:
                    grouped_data[group] = 0
                grouped_data[group] += 1
        
        if grouped_data:
            st.write("**Account Groups:**")
            for group_name, count in grouped_data.items():
                st.write(f"• {group_name}: {count} accounts")
        
        # Reset section
        st.header("5. Reset")
        if st.button("🔄 Clear Data"):
            if 'billing_data' in st.session_state:
                del st.session_state['billing_data']
            st.success("Data cleared")
            st.rerun()
    
    else:
        st.info("👆 Upload your monthly data file to begin processing")
        
        # Show sample format
        st.header("Expected File Format")
        st.markdown("""
        Your CSV/Excel file should contain these columns:
        - **Account Number** or **Account** (required)
        - **Account Name** (optional)
        - **Calls Total** 
        - **Minutes quantity**
        - **Messages quantity** or **Messages Total**
        - **Transcriptions quantity** or **Transcriptions cost**
        - **AskAI quantity**
        - **Numbers quantity**
        """)

if __name__ == "__main__":
    main()
