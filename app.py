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

def load_account_mappings():
    """Load account to group mappings"""
    try:
        # For Streamlit Cloud, use default mappings if file doesn't exist
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
                return json.load(f)
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
    
    # Standardize column names
    if 'Account' in df.columns and 'Account Number' not in df.columns:
        df = df.rename(columns={'Account': 'Account Number'})
    
    # Basic column mappings
    column_mappings = {
        'account': 'Account Number',
        'calls': 'Calls Total',
        'minutes': 'Minutes quantity',
        'messages': 'Messages quantity',
        'transcriptions': 'Transcriptions quantity',
        'askai': 'AskAI quantity',
        'numbers': 'Numbers quantity'
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
    
    # Ensure required columns exist
    required_columns = ['Account Number']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        st.error(f"Missing required columns: {missing_columns}")
        return None
    
    # Convert Account Number to string
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

def create_simple_excel(df, mappings):
    """Create Excel file with billing data"""
    output = io.BytesIO()
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
    
    # Write header
    current_month = datetime.now().strftime('%B %Y')
    worksheet.write(0, 0, f'Client Billing Report - {current_month}', header_format)
    worksheet.merge_range(0, 0, 0, 7, f'Client Billing Report - {current_month}', header_format)
    
    # Column headers
    headers = ['Account', 'Account Name', 'Calls Total', 'Minutes', 'Messages', 'Transcriptions', 'AskAI', 'Numbers']
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
    
    row = 3
    
    # Process each group
    for group_name in ["BTTW GROUP", "BIG BRAND TIRE GROUP", "Sylvan Learning", "Truckfitters", "INDEPENDENTS"]:
        if group_name not in grouped_data:
            continue
            
        accounts = grouped_data[group_name]
        
        # Write group header
        worksheet.write(row, 0, group_name, group_format)
        worksheet.write(row, 1, f'{len(accounts)} accounts', group_format)
        row += 1
        
        # Write individual accounts
        for account in accounts:
            account_number = str(account['Account Number'])
            account_name = account.get('Account Name', 'Unknown')
            
            # Get numeric values with fallbacks
            calls = pd.to_numeric(account.get('Calls Total', 0), errors='coerce') or 0
            minutes = pd.to_numeric(account.get('Minutes quantity', 0), errors='coerce') or 0
            messages = pd.to_numeric(account.get('Messages quantity', 0), errors='coerce') or 0
            transcriptions = pd.to_numeric(account.get('Transcriptions quantity', 0), errors='coerce') or 0
            askai = pd.to_numeric(account.get('AskAI quantity', 0), errors='coerce') or 0
            numbers = pd.to_numeric(account.get('Numbers quantity', 0), errors='coerce') or 0
            
            # Apply BBT multiplier for AskAI
            if group_name == "BIG BRAND TIRE GROUP":
                askai *= 7
            
            worksheet.write(row, 0, account_number)
            worksheet.write(row, 1, account_name)
            worksheet.write(row, 2, int(calls) if calls > 0 else '')
            worksheet.write(row, 3, int(minutes) if minutes > 0 else '')
            worksheet.write(row, 4, int(messages) if messages > 0 else '')
            worksheet.write(row, 5, int(transcriptions) if transcriptions > 0 else '')
            worksheet.write(row, 6, int(askai) if askai > 0 else '')
            worksheet.write(row, 7, int(numbers) if numbers > 0 else '')
            row += 1
        
        row += 1  # Add blank row between groups
    
    # Auto-adjust column widths
    worksheet.set_column(0, 0, 15)  # Account
    worksheet.set_column(1, 1, 25)  # Account Name
    worksheet.set_column(2, 7, 12)  # All other columns
    
    workbook.close()
    output.seek(0)
    return output.getvalue()

def main():
    st.title("📊 Client Billing Manager")
    st.markdown("**Streamlit Cloud Deployment - No Authentication Required**")
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
            
            # Read file based on extension
            if uploaded_file.name.endswith('.csv'):
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, encoding='latin-1')
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
                
        except pd.errors.EmptyDataError:
            st.error("The file appears to be empty or has no columns to parse. Please check your CSV file format.")
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
        st.header("3. Download Report")
        
        if new_accounts:
            st.info("Complete account assignment to enable download")
        else:
            excel_data = create_simple_excel(df, mappings)
            st.download_button(
                label="📥 Download Billing Report",
                data=excel_data,
                file_name=f"billing_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
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
        - **Account Number** (required)
        - **Account Name** (optional)
        - **Calls Total** or **Calls**
        - **Minutes quantity** or **Minutes**
        - **Messages quantity** or **Messages**
        - **Transcriptions quantity** or **Transcriptions**
        - **AskAI quantity** or **AskAI**
        - **Numbers quantity** or **Numbers**
        """)

if __name__ == "__main__":
    main()
