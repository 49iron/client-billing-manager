import streamlit as st
import pandas as pd
import os

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

def main():
    if not check_password():
        return
    
    # App selection interface
    st.title("Client Billing Applications")
    st.markdown("Choose which application to use:")
    
    app_choice = st.radio(
        "Select Application:",
        ["Standalone Sort Tool", "Client Sort Spreadsheet (Original)", "Advanced Billing Manager"],
        horizontal=True
    )
    
    if app_choice == "Standalone Sort Tool":
        try:
            from client_sort_standalone import main
            main()
        except ImportError as e:
            st.error(f"Standalone tool not available: {e}")
    
    elif app_choice == "Client Sort Spreadsheet (Original)":
        try:
            from client_sort_app import render_main_interface
            render_main_interface()
        except ImportError as e:
            st.error(f"Client Sort app not available: {e}")
    
    elif app_choice == "Advanced Billing Manager":
        # Main workflow options
        workflow_option = st.radio(
            "Workflow:",
            ["Quick Billing", "Advanced Tools", "Account Management"],
            horizontal=True
        )
        
        if workflow_option == "Quick Billing":
            try:
                from simple_billing_workflow import render_simple_workflow
                render_simple_workflow()
            except ImportError as e:
                st.error(f"Workflow not available: {e}")
        
        elif workflow_option == "Advanced Tools":
            # Create tabs for advanced features
            adv_tab1, adv_tab2, adv_tab3 = st.tabs(["Automated Billing", "Invoice Templates", "Validation"])
            
            with adv_tab1:
                try:
                    from automated_billing_interface import render_automated_billing_tab
                    render_automated_billing_tab()
                except ImportError:
                    st.error("Automated billing interface not available")
            
            with adv_tab2:
                try:
                    from client_invoice_templates import ClientInvoiceTemplates
                    template_manager = ClientInvoiceTemplates()
                    template_manager.render_template_manager()
                except ImportError:
                    st.error("Invoice templates not available")
            
            with adv_tab3:
                st.info("Invoice validation tools will be available here")
        
        elif workflow_option == "Account Management":
            # Create tabs for account management
            mgmt_tab1, mgmt_tab2, mgmt_tab3 = st.tabs(["Groups", "Billing Rules", "Export"])
            
            with mgmt_tab1:
                try:
                    from group_mappings import load_group_mappings, save_group_mappings
                    st.subheader("Account Group Mappings")
                    mappings = load_group_mappings()
                    st.write(f"Managing {len(mappings)} account mappings")
                    if st.button("View All Mappings"):
                        st.json(mappings)
                except ImportError:
                    st.error("Group management not available")
            
            with mgmt_tab2:
                try:
                    from billing_rules_manager import render_billing_rules_manager
                    render_billing_rules_manager()
                except ImportError:
                    st.error("Billing rules manager not available")
            
            with mgmt_tab3:
                st.info("Export tools will be available here")
    
    # Simple footer
    if st.button("Reset Session"):
        for key in list(st.session_state.keys()):
            if key != "password_correct":
                del st.session_state[key]
        st.success("Session cleared")
        st.rerun()

if __name__ == "__main__":
    main()